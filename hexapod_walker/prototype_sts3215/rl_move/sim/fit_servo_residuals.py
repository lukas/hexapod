"""Identify gait-independent Hexapod-2 servo residuals from telemetry.

This is deliberately an *offline* actuator-identification tool.  It uses the
four ``split=fit`` traces in :mod:`hexapod2_replay_matrix.json`, freezes the
existing per-axis loaded-servo profile, and estimates only small per-servo
corrections:

* command latency;
* velocity-ceiling scale;
* logical zero offset; and
* a rate-independent reversal deadband (mechanical play).

All remaining manifest traces are evaluated exactly once as holdouts.  A
correction is applied only when fit-trace excitation, cross-family support,
and loss sensitivity support it.  Otherwise its applied value is
the neutral value and the report explains why.  Servo current is never used
as a gain or fitting input: this model describes the commanded/encoder path,
not motor torque.

The input CSVs remain outside Git.  A normal invocation is::

    uv run python -m rl_move.sim.fit_servo_residuals \
      --data-dir /tmp/hexapod2-replay-matrix-20260912 \
      --out /tmp/hexapod2-servo-residual-fit.json
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import time
from typing import Iterable, Sequence

import numpy as np

from .replay_trace import RL_ACC_UNITS, RL_SPEED_DEG_S, load_trace
from .servo_model import (
    ACC_UNIT_DEG_S2,
    AXES,
    LOADED_MODEL_PATH,
    SimServoParams,
)


MANIFEST_PATH = Path(__file__).with_name("hexapod2_replay_matrix.json")
DEFAULT_REPORT_PATH = Path("/tmp/hexapod2-servo-residual-fit.json")
PARAMETER_NAMES = (
    "latency_ms",
    "velocity_scale",
    "zero_offset_deg",
    "reversal_deadband_deg",
)


@dataclass(frozen=True)
class NominalAxisProfile:
    """Frozen global profile inherited by every servo on one axis."""

    latency_ms: float
    velocity_deg_s: float
    acceleration_deg_s2: float
    tracking_deadband_deg: float


@dataclass(frozen=True)
class ServoResidual:
    """Absolute latency plus neutral-relative corrections for one servo."""

    latency_ms: float
    velocity_scale: float = 1.0
    zero_offset_deg: float = 0.0
    reversal_deadband_deg: float = 0.0


@dataclass(frozen=True)
class Trace1D:
    """One physical actuator coordinate from one hardware trace."""

    name: str
    family: str
    t_s: np.ndarray
    command_deg: np.ndarray
    measured_deg: np.ndarray


def robot_abs_to_actuator_deg(q_deg: np.ndarray) -> np.ndarray:
    """Public robot-absolute angles -> the 18 physical hinge coordinates."""
    out = np.asarray(q_deg, dtype=float).copy()
    if out.shape[-1] != 18:
        raise ValueError("joint array must end in 18 coordinates")
    out[..., 2::3] -= out[..., 1::3]
    return out


def actuator_to_robot_abs_deg(q_deg: np.ndarray) -> np.ndarray:
    """The 18 physical hinge coordinates -> public robot-absolute angles."""
    out = np.asarray(q_deg, dtype=float).copy()
    if out.shape[-1] != 18:
        raise ValueError("joint array must end in 18 coordinates")
    out[..., 2::3] += out[..., 1::3]
    return out


def nominal_profiles(path: Path | str = LOADED_MODEL_PATH) -> dict[str, NominalAxisProfile]:
    """Load, but do not refit, the project's loaded per-axis servo profile."""
    params = SimServoParams.load(path)
    acceleration = RL_ACC_UNITS * ACC_UNIT_DEG_S2
    return {
        axis: NominalAxisProfile(
            latency_ms=float(values.latency_ms),
            # The replay sends the deployed 400-count/s speed.  The lower of
            # that write and the fitted servo ceiling is the actual nominal.
            velocity_deg_s=min(
                float(values.vel_max_deg_s), float(RL_SPEED_DEG_S)),
            acceleration_deg_s2=float(acceleration),
            tracking_deadband_deg=float(values.deadband_deg),
        )
        for axis, values in params.axes.items()
    }


def _play_operator(command_deg: np.ndarray, initial_deg: float,
                   half_width_deg: float) -> np.ndarray:
    """Apply a symmetric mechanical-play operator to a desired coordinate.

    Its state stays inside ``[command-half_width, command+half_width]``.
    Reversing direction must therefore traverse twice ``half_width`` before
    the opposite flank carries load.  Zero width is exactly the identity.
    """
    command = np.asarray(command_deg, dtype=float)
    width = float(half_width_deg)
    if width < 0.0 or not math.isfinite(width):
        raise ValueError("reversal deadband must be finite and >= 0")
    if width == 0.0:
        return command.copy()
    out = np.empty_like(command)
    state = float(initial_deg)
    for i, value in enumerate(command):
        lower, upper = float(value) - width, float(value) + width
        state = min(max(state, lower), upper)
        out[i] = state
    return out


def predict_servo(trace: Trace1D, nominal: NominalAxisProfile,
                  residual: ServoResidual, *, max_step_s: float = 0.005) -> np.ndarray:
    """Predict one encoder coordinate at the trace's exact sample times.

    Commands are linearly interpolated between logger ticks because the
    post-safety target itself is a slew-limited continuous path.  The first
    command remains queued behind latency; unknown pre-trace history is the
    measured initial coordinate, which avoids inventing motion at ``t=0``.
    """
    t = np.asarray(trace.t_s, dtype=float)
    cmd = np.asarray(trace.command_deg, dtype=float)
    measured = np.asarray(trace.measured_deg, dtype=float)
    if (t.ndim != 1 or cmd.shape != t.shape or measured.shape != t.shape
            or t.size < 2 or np.any(np.diff(t) <= 0.0)):
        raise ValueError("trace arrays must be equal, 1-D, and strictly timed")
    if not (math.isfinite(max_step_s) and max_step_s > 0.0):
        raise ValueError("max_step_s must be finite and > 0")

    latency_s = float(residual.latency_ms) / 1000.0
    velocity = nominal.velocity_deg_s * float(residual.velocity_scale)
    acceleration = nominal.acceleration_deg_s2
    if not (0.0 <= latency_s <= 1.0 and velocity > 0.0
            and math.isfinite(velocity)):
        raise ValueError("invalid latency or velocity correction")

    # Include every logger time exactly and insert only as many profile steps
    # as needed for stable acceleration integration.
    pieces: list[float] = [float(t[0])]
    sample_indices = np.empty(t.size, dtype=int)
    sample_indices[0] = 0
    for i, dt in enumerate(np.diff(t)):
        n = max(1, int(math.ceil(float(dt) / max_step_s)))
        start = float(t[i])
        pieces.extend(start + float(dt) * k / n for k in range(1, n + 1))
        sample_indices[i + 1] = len(pieces) - 1
    grid = np.asarray(pieces, dtype=float)

    desired = np.interp(
        grid - latency_s,
        t,
        cmd + float(residual.zero_offset_deg),
        left=float(measured[0]),
        right=float(cmd[-1] + residual.zero_offset_deg),
    )
    goal = _play_operator(
        desired, float(measured[0]), float(residual.reversal_deadband_deg))

    target = float(measured[0])
    profile_velocity = 0.0
    profile = np.empty(grid.size, dtype=float)
    profile[0] = target
    deadband = float(nominal.tracking_deadband_deg)
    for i in range(1, grid.size):
        dt = float(grid[i] - grid[i - 1])
        error = float(goal[i]) - target
        if abs(error) <= deadband:
            profile_velocity = 0.0
            profile[i] = target
            continue
        direction = math.copysign(1.0, error)
        stopping_distance = profile_velocity * profile_velocity / (
            2.0 * max(acceleration, 1e-9))
        moving_toward = profile_velocity * direction > 0.0
        if moving_toward and stopping_distance >= abs(error):
            dv = -math.copysign(acceleration * dt, profile_velocity)
        else:
            dv = direction * acceleration * dt
        profile_velocity = float(np.clip(
            profile_velocity + dv, -velocity, velocity))
        step = profile_velocity * dt
        if abs(step) >= abs(error):
            target = float(goal[i])
            profile_velocity = 0.0
        else:
            target += step
        profile[i] = target
    return profile[sample_indices]


def _score_mask(trace: Trace1D, warmup_s: float = 0.4) -> np.ndarray:
    mask = trace.t_s >= min(float(trace.t_s[-1]), warmup_s)
    if np.count_nonzero(mask) < 10:
        return np.ones(trace.t_s.shape, dtype=bool)
    return mask


def _weighted_residual(traces: Sequence[Trace1D],
                       nominal: NominalAxisProfile,
                       values: Sequence[float], *,
                       max_step_s: float = 0.01) -> np.ndarray:
    residual = ServoResidual(*map(float, values))
    chunks = []
    for trace in traces:
        mask = _score_mask(trace)
        error = predict_servo(
            trace, nominal, residual, max_step_s=max_step_s)[mask] \
            - trace.measured_deg[mask]
        # Each gait contributes equal squared-error weight despite logger-rate
        # differences (25/50/100 Hz).
        chunks.append(error / math.sqrt(max(1, error.size)))
    return np.concatenate(chunks)


def _rmse(traces: Sequence[Trace1D], nominal: NominalAxisProfile,
          residual: ServoResidual) -> float:
    errors = []
    for trace in traces:
        mask = _score_mask(trace)
        errors.append(
            predict_servo(trace, nominal, residual)[mask]
            - trace.measured_deg[mask])
    return float(np.sqrt(np.mean(np.concatenate(errors) ** 2)))


def _fit_candidate(traces: Sequence[Trace1D], nominal: NominalAxisProfile,
                   *, free: Sequence[bool] = (True, True, True, True),
                   initial: ServoResidual | None = None,
                   max_nfev: int = 100,
                   multiple_starts: bool = True) -> ServoResidual:
    """Bounded deterministic least-squares fit for one physical servo."""
    from scipy.optimize import least_squares

    neutral = np.array([nominal.latency_ms, 1.0, 0.0, 0.0], dtype=float)
    lo = np.array([0.0, 0.35, -6.0, 0.0], dtype=float)
    hi = np.array([500.0, 1.8, 6.0, 4.0], dtype=float)
    free_mask = np.asarray(free, dtype=bool)
    if free_mask.shape != (4,):
        raise ValueError("free must contain four booleans")
    base = neutral.copy() if initial is None else np.array(
        [getattr(initial, name) for name in PARAMETER_NAMES], dtype=float)
    base = np.clip(base, lo, hi)
    if not np.any(free_mask):
        return ServoResidual(*map(float, neutral))

    def unpack(x: np.ndarray) -> np.ndarray:
        values = neutral.copy()
        values[free_mask] = x
        return values

    def fun(x: np.ndarray) -> np.ndarray:
        return _weighted_residual(traces, nominal, unpack(x))

    # Multiple fixed starts make the non-smooth play operator deterministic
    # without a random/global optimizer.
    starts = [base]
    if multiple_starts:
        starts.extend((
            np.array([180.0, 0.75, 0.0, 0.5]),
            np.array([280.0, 1.10, 0.0, 1.25]),
        ))
    best = None
    scale = np.array([100.0, 0.25, 1.0, 0.5])[free_mask]
    for start in starts:
        result = least_squares(
            fun,
            np.clip(start, lo, hi)[free_mask],
            bounds=(lo[free_mask], hi[free_mask]),
            x_scale=scale,
            loss="soft_l1",
            f_scale=1.0,
            max_nfev=max_nfev,
        )
        values = unpack(result.x)
        loss = float(np.dot(fun(result.x), fun(result.x)))
        if best is None or loss < best[0]:
            best = (loss, values)
    assert best is not None
    return ServoResidual(*map(float, best[1]))


def _meaningful_reversals(traces: Sequence[Trace1D], threshold_deg: float = 0.15) -> int:
    count = 0
    for trace in traces:
        delta = np.diff(trace.command_deg)
        sign = np.sign(delta[np.abs(delta) >= threshold_deg])
        if sign.size > 1:
            count += int(np.count_nonzero(sign[1:] != sign[:-1]))
    return count


def _excitation(traces: Sequence[Trace1D]) -> dict[str, float | int]:
    ranges = [float(np.ptp(trace.command_deg)) for trace in traces]
    travel = [float(np.sum(np.abs(np.diff(trace.command_deg)))) for trace in traces]
    return {
        "excited_trace_count": int(sum(value >= 4.0 for value in ranges)),
        "minimum_range_deg": float(min(ranges)),
        "maximum_range_deg": float(max(ranges)),
        "total_command_travel_deg": float(sum(travel)),
        "meaningful_reversals": _meaningful_reversals(traces),
    }


def _parameter_decisions(candidate: ServoResidual,
                         traces: Sequence[Trace1D],
                         nominal: NominalAxisProfile) -> dict[str, dict]:
    """Gate every correction independently; unsupported values go neutral."""
    neutral = ServoResidual(nominal.latency_ms)
    base_values = np.array(
        [getattr(candidate, name) for name in PARAMETER_NAMES])
    neutral_values = np.array(
        [getattr(neutral, name) for name in PARAMETER_NAMES])
    full_error = _weighted_residual(traces, nominal, base_values)
    full_sse = float(np.dot(full_error, full_error))
    excitation = _excitation(traces)
    thresholds = {
        "latency_ms": (10.0, 0.003),
        "velocity_scale": (0.04, 0.003),
        "zero_offset_deg": (0.10, 0.002),
        "reversal_deadband_deg": (0.15, 0.005),
    }
    decisions: dict[str, dict] = {}
    for index, name in enumerate(PARAMETER_NAMES):
        ablated = base_values.copy()
        ablated[index] = neutral_values[index]
        error = _weighted_residual(traces, nominal, ablated)
        ablation_sse = float(np.dot(error, error))
        relative = max(0.0, (ablation_sse - full_sse) / max(full_sse, 1e-12))
        # Require the correction to help every one of the four distinct gait
        # families, not merely the pooled loss.  This deliberately strict,
        # cheaper test of gait independence than repeatedly optimizing on
        # nearly identical leave-one-out subsets.
        family_support = []
        family_relative = []
        for trace in traces:
            fit_e = _weighted_residual(
                [trace], nominal, base_values)
            ablated_e = _weighted_residual(
                [trace], nominal, ablated)
            fit_trace_sse = float(np.dot(fit_e, fit_e))
            ablated_trace_sse = float(np.dot(ablated_e, ablated_e))
            trace_relative = ((ablated_trace_sse - fit_trace_sse)
                              / max(fit_trace_sse, 1e-12))
            family_relative.append(float(trace_relative))
            family_support.append(bool(trace_relative > 0.0))
        support_count = int(sum(family_support))
        effect = float(abs(base_values[index] - neutral_values[index]))
        effect_min, sensitivity_min = thresholds[name]
        reasons: list[str] = []
        if excitation["excited_trace_count"] < 3:
            reasons.append("fewer than three fit traces excite this servo by 4 deg")
        if effect < effect_min:
            reasons.append("candidate correction is practically neutral")
        if support_count < len(traces):
            reasons.append("correction does not improve every fit gait family")
        if relative < sensitivity_min:
            reasons.append("fit loss is insensitive to this correction")
        if (name == "reversal_deadband_deg"
                and excitation["meaningful_reversals"] < 12):
            reasons.append("fewer than 12 meaningful direction reversals")
        accepted = not reasons
        decisions[name] = {
            "status": "fitted" if accepted else "neutral_unidentified",
            "candidate": float(base_values[index]),
            "applied": (float(base_values[index]) if accepted
                        else float(neutral_values[index])),
            "neutral": float(neutral_values[index]),
            "fit_family_support_count": support_count,
            "fit_family_relative_sse": family_relative,
            "ablation_relative_sse": relative,
            "reason": "supported by fit traces" if accepted else "; ".join(reasons),
        }
    decisions["excitation"] = excitation
    return decisions


def fit_one_servo(traces: Sequence[Trace1D], nominal: NominalAxisProfile,
                  *, max_nfev: int = 100) -> tuple[ServoResidual, dict]:
    """Fit and identifiability-gate one servo using fit traces only."""
    if len(traces) < 3:
        raise ValueError("at least three independent fit traces are required")
    candidate = _fit_candidate(traces, nominal, max_nfev=max_nfev)
    decisions = _parameter_decisions(candidate, traces, nominal)
    free = [decisions[name]["status"] == "fitted"
            for name in PARAMETER_NAMES]
    initial_values = [decisions[name]["applied"] for name in PARAMETER_NAMES]
    final = _fit_candidate(
        traces, nominal, free=free,
        initial=ServoResidual(*initial_values), max_nfev=max_nfev,
        multiple_starts=False)
    # A fixed parameter is always exactly neutral, even if the optimizer's
    # full candidate was an attractive but unidentifiable value.
    final_values = np.array([getattr(final, name) for name in PARAMETER_NAMES])
    neutral_values = np.array(
        [nominal.latency_ms, 1.0, 0.0, 0.0], dtype=float)
    final_values[~np.asarray(free)] = neutral_values[~np.asarray(free)]
    final = ServoResidual(*map(float, final_values))
    baseline = ServoResidual(nominal.latency_ms)
    details = {
        "candidate": asdict(candidate),
        "applied": asdict(final),
        "baseline_fit_rmse_deg": _rmse(traces, nominal, baseline),
        "candidate_fit_rmse_deg": _rmse(traces, nominal, candidate),
        "applied_fit_rmse_deg": _rmse(traces, nominal, final),
        "parameters": decisions,
    }
    return final, details


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_manifest_traces(manifest_path: Path, data_dir: Path) -> tuple[list[dict], list[dict]]:
    """Load and hash-check the canonical four-fit/twenty-one-holdout split."""
    blob = json.loads(manifest_path.read_text())
    if int(blob.get("schema_version", 0)) != 1:
        raise ValueError("unsupported replay-matrix schema")
    loaded = []
    for entry in blob.get("entries", []):
        if entry.get("split") not in {"fit", "holdout"}:
            raise ValueError(f"invalid split for {entry.get('artifact')}")
        path = data_dir / entry["artifact"]
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = _sha256(path)
        if actual != entry["sha256"]:
            raise ValueError(f"SHA-256 mismatch for {path}")
        trace = load_trace(path)
        loaded.append({"entry": entry, "trace": trace})
    fit = [item for item in loaded if item["entry"]["split"] == "fit"]
    holdout = [item for item in loaded if item["entry"]["split"] == "holdout"]
    if len(fit) != 4 or len(holdout) != 21:
        raise ValueError(
            f"canonical split must contain 4 fit and 21 holdout traces; "
            f"found {len(fit)} and {len(holdout)}")
    if len({item["entry"]["family"] for item in fit}) != 4:
        raise ValueError("the four fit traces must represent four gait families")
    return fit, holdout


def _trace1d(items: Sequence[dict], servo: int) -> list[Trace1D]:
    out = []
    for item in items:
        trace = item["trace"]
        commands = robot_abs_to_actuator_deg(trace["cmd"])
        measured = robot_abs_to_actuator_deg(trace["q"])
        out.append(Trace1D(
            name=item["entry"]["artifact"],
            family=item["entry"]["family"],
            t_s=np.asarray(trace["t"], dtype=float),
            command_deg=commands[:, servo],
            measured_deg=measured[:, servo],
        ))
    return out


def _predict_joint_matrix(item: dict, profiles: dict[str, NominalAxisProfile],
                          residuals: Sequence[ServoResidual]) -> np.ndarray:
    trace = item["trace"]
    command = robot_abs_to_actuator_deg(trace["cmd"])
    measured = robot_abs_to_actuator_deg(trace["q"])
    actuator_pred = np.empty_like(command)
    for servo in range(18):
        one = Trace1D(
            name=item["entry"]["artifact"],
            family=item["entry"]["family"],
            t_s=np.asarray(trace["t"], dtype=float),
            command_deg=command[:, servo],
            measured_deg=measured[:, servo],
        )
        actuator_pred[:, servo] = predict_servo(
            one, profiles[AXES[servo % 3]], residuals[servo])
    return actuator_to_robot_abs_deg(actuator_pred)


def _run_metric(item: dict, profiles: dict[str, NominalAxisProfile],
                residuals: Sequence[ServoResidual], *,
                predicted: np.ndarray | None = None) -> dict:
    trace = item["trace"]
    if predicted is None:
        predicted = _predict_joint_matrix(item, profiles, residuals)
    error = predicted - trace["q"]
    moving = np.ptp(trace["cmd"], axis=0) >= 4.0
    axis_rmse = {}
    for axis_index, axis in enumerate(AXES):
        use = moving & (np.arange(18) % 3 == axis_index)
        axis_rmse[axis] = (float(np.sqrt(np.mean(error[:, use] ** 2)))
                           if np.any(use) else None)
    return {
        "run_id": item["entry"]["run_id"],
        "artifact": item["entry"]["artifact"],
        "family": item["entry"]["family"],
        "command": item["entry"].get("command", ""),
        "samples": int(error.shape[0]),
        "moving_servos": int(np.count_nonzero(moving)),
        "all_joint_rmse_deg": float(np.sqrt(np.mean(error ** 2))),
        "moving_joint_rmse_deg": (float(np.sqrt(np.mean(error[:, moving] ** 2)))
                                  if np.any(moving) else None),
        "axis_moving_rmse_deg": axis_rmse,
    }


def _aggregate_run_metrics(rows: Sequence[dict]) -> dict:
    values = np.asarray([
        row["moving_joint_rmse_deg"] for row in rows
        if row["moving_joint_rmse_deg"] is not None
    ], dtype=float)
    return {
        "run_count": len(rows),
        "median_run_moving_joint_rmse_deg": float(np.median(values)),
        "mean_run_moving_joint_rmse_deg": float(np.mean(values)),
        "worst_run_moving_joint_rmse_deg": float(np.max(values)),
    }


def _paired_comparison(baseline: Sequence[dict], fitted: Sequence[dict]) -> dict:
    """Paired run-level deltas; negative means the fitted model is better."""
    if len(baseline) != len(fitted):
        raise ValueError("baseline/fitted run counts differ")
    before = np.asarray(
        [row["moving_joint_rmse_deg"] for row in baseline], dtype=float)
    after = np.asarray(
        [row["moving_joint_rmse_deg"] for row in fitted], dtype=float)
    delta = after - before
    relative = delta / np.maximum(before, 1e-12)
    return {
        "improved_runs": int(np.count_nonzero(delta < -1e-9)),
        "worsened_runs": int(np.count_nonzero(delta > 1e-9)),
        "unchanged_runs": int(np.count_nonzero(np.abs(delta) <= 1e-9)),
        "mean_delta_deg": float(np.mean(delta)),
        "median_delta_deg": float(np.median(delta)),
        "median_relative_delta_pct": float(100.0 * np.median(relative)),
    }


def _servo_holdout_validation(items: Sequence[dict],
                              baseline_predictions: Sequence[np.ndarray],
                              fitted_predictions: Sequence[np.ndarray],
                              servo: int) -> dict:
    """Validate one fitted physical-servo bundle on excited holdout runs."""
    rows = []
    for item, before_robot, after_robot in zip(
            items, baseline_predictions, fitted_predictions, strict=True):
        command = robot_abs_to_actuator_deg(item["trace"]["cmd"])
        if float(np.ptp(command[:, servo])) < 4.0:
            continue
        measured = robot_abs_to_actuator_deg(item["trace"]["q"])[:, servo]
        before = robot_abs_to_actuator_deg(before_robot)[:, servo]
        after = robot_abs_to_actuator_deg(after_robot)[:, servo]
        mask = np.asarray(item["trace"]["t"]) >= min(
            float(item["trace"]["t"][-1]), 0.4)
        base_rmse = float(np.sqrt(np.mean((before[mask] - measured[mask]) ** 2)))
        fit_rmse = float(np.sqrt(np.mean((after[mask] - measured[mask]) ** 2)))
        rows.append({
            "family": item["entry"]["family"],
            "artifact": item["entry"]["artifact"],
            "baseline_rmse_deg": base_rmse,
            "fitted_rmse_deg": fit_rmse,
            "delta_deg": fit_rmse - base_rmse,
        })
    delta = np.asarray([row["delta_deg"] for row in rows])
    families = {}
    for family in sorted({row["family"] for row in rows}):
        values = [row["delta_deg"] for row in rows if row["family"] == family]
        families[family] = float(np.mean(values))
    universal = bool(
        rows and np.all(delta <= 0.0)
        and all(value <= 0.0 for value in families.values()))
    return {
        "excited_run_count": len(rows),
        "improved_runs": int(np.count_nonzero(delta < -1e-9)),
        "worsened_runs": int(np.count_nonzero(delta > 1e-9)),
        "mean_delta_deg": float(np.mean(delta)) if rows else None,
        "median_delta_deg": float(np.median(delta)) if rows else None,
        "family_mean_delta_deg": families,
        "universal": universal,
        "verdict": ("generalizes across excited holdouts" if universal else
                    "not a gait-independent holdout improvement"),
        "runs": rows,
    }


def identify(manifest_path: Path, data_dir: Path, *, max_nfev: int = 100) -> dict:
    """Fit four traces, freeze the result, and evaluate every holdout."""
    fit_items, holdout_items = load_manifest_traces(manifest_path, data_dir)
    profiles = nominal_profiles()
    baseline_residuals = [
        ServoResidual(profiles[AXES[j % 3]].latency_ms) for j in range(18)
    ]
    fitted_residuals: list[ServoResidual] = []
    servo_reports = []
    for servo in range(18):
        axis = AXES[servo % 3]
        residual, detail = fit_one_servo(
            _trace1d(fit_items, servo), profiles[axis],
            max_nfev=max_nfev)
        fitted_residuals.append(residual)
        servo_reports.append({
            "servo": servo,
            "leg": servo // 3,
            "axis": axis,
            **detail,
        })

    baseline_fit_predictions = [
        _predict_joint_matrix(item, profiles, baseline_residuals)
        for item in fit_items]
    fitted_fit_predictions = [
        _predict_joint_matrix(item, profiles, fitted_residuals)
        for item in fit_items]
    baseline_holdout_predictions = [
        _predict_joint_matrix(item, profiles, baseline_residuals)
        for item in holdout_items]
    fitted_holdout_predictions = [
        _predict_joint_matrix(item, profiles, fitted_residuals)
        for item in holdout_items]
    baseline_fit = [
        _run_metric(item, profiles, baseline_residuals, predicted=predicted)
        for item, predicted in zip(fit_items, baseline_fit_predictions,
                                   strict=True)]
    fitted_fit = [
        _run_metric(item, profiles, fitted_residuals, predicted=predicted)
        for item, predicted in zip(fit_items, fitted_fit_predictions,
                                   strict=True)]
    baseline_holdout = [
        _run_metric(item, profiles, baseline_residuals, predicted=predicted)
        for item, predicted in zip(holdout_items,
                                   baseline_holdout_predictions, strict=True)]
    fitted_holdout = [
        _run_metric(item, profiles, fitted_residuals, predicted=predicted)
        for item, predicted in zip(holdout_items,
                                   fitted_holdout_predictions, strict=True)]
    for servo, report in enumerate(servo_reports):
        report["holdout_validation"] = _servo_holdout_validation(
            holdout_items, baseline_holdout_predictions,
            fitted_holdout_predictions, servo)
        has_residual = any(
            report["parameters"][name]["status"] == "fitted"
            for name in PARAMETER_NAMES)
        report["holdout_validation"]["has_fit_supported_residual"] = has_residual
        if not has_residual:
            report["holdout_validation"]["universal"] = None
            report["holdout_validation"]["verdict"] = (
                "neutral: no fit-supported residual to validate")
    families = sorted({row["family"] for row in baseline_holdout})
    family_summary = {}
    for family in families:
        before = [row for row in baseline_holdout if row["family"] == family]
        after = [row for row in fitted_holdout if row["family"] == family]
        family_summary[family] = {
            "baseline": _aggregate_run_metrics(before),
            "fitted": _aggregate_run_metrics(after),
            "paired": _paired_comparison(before, after),
        }
    paired_holdout = _paired_comparison(baseline_holdout, fitted_holdout)
    improved_families = sum(
        values["paired"]["mean_delta_deg"] < 0.0
        for values in family_summary.values())
    safe_to_integrate = bool(
        paired_holdout["median_delta_deg"] < 0.0
        and improved_families == len(family_summary)
        and paired_holdout["worsened_runs"] == 0)
    return {
        "schema_version": 1,
        "created_unix_s": time.time(),
        "method": {
            "fit_split": "exactly the four manifest split=fit traces",
            "holdout_split": "all twenty-one manifest split=holdout traces",
            "joint_coordinate_fit": "physical servo hinge; metrics are robot_abs_tibia_v2",
            "nominal_profile": str(LOADED_MODEL_PATH),
            "servo_current_usage": "not used in fitting or as a kp proxy",
            "parameter_gate": "fit excitation + improvement in every fit gait family + ablation sensitivity",
        },
        "nominal_axes": {axis: asdict(profile)
                         for axis, profile in profiles.items()},
        "servos": servo_reports,
        "fit": {
            "baseline_runs": baseline_fit,
            "fitted_runs": fitted_fit,
            "baseline_summary": _aggregate_run_metrics(baseline_fit),
            "fitted_summary": _aggregate_run_metrics(fitted_fit),
            "paired": _paired_comparison(baseline_fit, fitted_fit),
        },
        "holdout": {
            "baseline_runs": baseline_holdout,
            "fitted_runs": fitted_holdout,
            "baseline_summary": _aggregate_run_metrics(baseline_holdout),
            "fitted_summary": _aggregate_run_metrics(fitted_holdout),
            "paired": paired_holdout,
            "by_family": family_summary,
        },
        "integration": {
            "status": "diagnostic_only",
            "safe_to_integrate": safe_to_integrate,
            "verdict": (
                "held-out improvement is universal; eligible for explicit review"
                if safe_to_integrate else
                "fixed residuals do not improve every held-out run and gait family; keep disabled"
            ),
            "surface": (
                "Add an optional per_joint_residuals array at the input of "
                "ServoProfile/TickParams only after holdout improvement and "
                "hardware provenance are reviewed; leave config default off."
            ),
            # Fail closed at the integration boundary: the fit-supported
            # candidates are preserved for diagnosis, while the actual
            # integration payload remains the neutral global-axis model.
            "applied_residuals": [asdict(value)
                                  for value in baseline_residuals],
            "diagnostic_fit_residuals": [asdict(value)
                                         for value in fitted_residuals],
        },
    }


def _print_summary(report: dict) -> None:
    fit0 = report["fit"]["baseline_summary"]
    fit1 = report["fit"]["fitted_summary"]
    hold0 = report["holdout"]["baseline_summary"]
    hold1 = report["holdout"]["fitted_summary"]
    print(
        "fit median moving-joint RMSE: "
        f"{fit0['median_run_moving_joint_rmse_deg']:.3f} -> "
        f"{fit1['median_run_moving_joint_rmse_deg']:.3f} deg")
    print(
        "holdout median moving-joint RMSE: "
        f"{hold0['median_run_moving_joint_rmse_deg']:.3f} -> "
        f"{hold1['median_run_moving_joint_rmse_deg']:.3f} deg")
    counts = {"fitted": 0, "neutral_unidentified": 0}
    for servo in report["servos"]:
        for name in PARAMETER_NAMES:
            counts[servo["parameters"][name]["status"]] += 1
    print("parameter decisions:", counts)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--data-dir", type=Path, required=True,
                        help="directory containing the manifest's csv/ paths")
    parser.add_argument("--out", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--max-nfev", type=int, default=100,
                        help="bounded optimizer evaluations per start")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.max_nfev < 20:
        parser.error("--max-nfev must be >= 20")
    report = identify(args.manifest, args.data_dir,
                      max_nfev=args.max_nfev)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    _print_summary(report)
    print(f"report: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
