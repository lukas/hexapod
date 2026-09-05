"""On-robot RL policy runner: STAND UP / LOWER / WALK buttons (web UI).

Runs v2 robot-absolute raw-joint PPO policies exported to plain numpy
weights by ``rl_move/sim/export_policy_np.py`` (no torch on the board).
``rl_policy_weights.json`` and ``rl_walk_weights.json`` are runtime slots,
created only when the operator selects a validated v2 artifact. Walk files may be
obs 74 = obs 72 + [sin, cos] of a phase clock the runner keeps
(advances at meta["phase_hz"] while velocity is commanded, frozen at
zero command — the sim's goal.walk_phase_obs=1 contract; the
cw-arch-noslipphase1 no-slip line). Phase policies run naked: no
rot-60 / mirror (they train all headings, no wedge). AMP walk files use
obs 93 = obs 74 + yaw-rate command + 18 fault-health entries; hardware
currently feeds an all-healthy fault vector.

- policy loop runs at the selected policy's declared meta["training_hz"];
  obs = build_obs(q, qd, tilt-rel-to-start, gyro, prev_action(18), goal(9))
  with q_nom = the pose read at arm time.
  The runner may stream interpolated servo targets faster between policy
  decisions, but the learned brain still sees exactly the trained
  cadence.
- action in [-1,1]^18 -> absolute joint targets via the AXIS_LIMITS_DEG
  center/half-range map (same as sim joint_task.action_to_q_rad).
- goal height ramps mirror the training GoalGenerator. The shape
  (hold_s / ramp_s / target_m / total_s) comes from the weight file's
  OWN meta["profile"] (export_policy_np.py --extra-meta). Missing or
  partial profiles are rejected instead of borrowing parameters from a
  different historical policy.
- every command goes through rl_move.safety.SafetyLayer: 1.5 deg/tick
  rate clamp, joint limits, relative-tilt trip (10 deg for stand/lower,
  25 deg for walk — see WALK_MAX_TILT_DEG), sustained 2.5 A trip,
  temp/load trips. Trip => immediate limp (do not fight a fall).

Post-2026-08-06 rules baked in: NO motion unless every preflight gate
passes — all 18 servo IDs answering, IMU ok, tilt < 12 deg, and the
present pose near the expected start (flat/belly for stand, captured
plant for lower). The operator must be watching; the web button is the
explicit order.
"""
from __future__ import annotations

import csv
import json
import math
import sys
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

# rl_move + hexapod_core live one level above linux_control on the robot
# bundle and in the repo; make them importable under direct execution.
_HERE = Path(__file__).resolve().parent
for _p in (_HERE.parent, _HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from rl_move.config import cfg_get, load_config            # noqa: E402
from rl_move.env import TaskGoal, build_obs                # noqa: E402
from hexapod_core.joint_frame import (                     # noqa: E402
    FRAME_ROBOT_ABS, JOINT_CONTRACT, require_robot_abs_joint_frame,
)
from rl_move.robot_state import (                          # noqa: E402
    DEG2RAD, N_JOINTS, RAD2DEG, RobotState, RobotStateEstimator,
)
from rl_move.safety import AXIS_LIMITS_DEG, SafetyLayer    # noqa: E402
from async_bus_guard import (                            # noqa: E402
    AsyncSamplerCleanupError, clear_bus_quarantine, quarantine_bus,
    require_bus_available,
)

# Rot-60 canonicalizer (08-11, RL_PLAN queue 2.1 deploy-side port).
# numpy-only module, shipped by deploy_adb.sh. The wrapper is an exact
# no-op (k=0) for commands within the trained +/-30 deg forward wedge,
# and covers the FULL CIRCLE of headings by the robot's exact hexagonal
# symmetry (rl_move/sim/rot60.py docstring; proved by test_rot60.py).
# If the module is missing on the board, walk falls back to refusing
# any command outside the trained wedge instead of running a heading
# the naked policy is known to freeze/degenerate on.
try:
    from rl_move.sim.rot60 import Rot60Policy              # noqa: E402
    _ROT60_OK = True
except Exception:                                          # pragma: no cover
    Rot60Policy = None
    _ROT60_OK = False

# Sagittal-mirror chirality selection (08-12, TURN.md deploy port).
# Every walk-lineage champion carries a command-invariant ~+0.09 rad/s
# LEFT yaw drift baked into its gait chirality; reflecting the policy
# (mirror.MirrorPolicy, numpy-only like rot60) produces a RIGHT-drifter
# with the same gait competence — sim-proven PASS 08-11
# (probe_mirror_turn: drift flips sign, travel matched, heading-hold
# 2-4 deg vs 38 deg naked drift over 12 s). Selecting naked-vs-mirrored
# by desired turn sign = commanded ARC turning (~2 deg/s, slow);
# alternating on the accumulated heading = drive straight. If the
# module is missing on-board, turn requests are refused (the default
# turn=None walk never needs it).
try:
    from rl_move.sim.mirror import MirrorPolicy            # noqa: E402
    _MIRROR_OK = True
except Exception:                                          # pragma: no cover
    MirrorPolicy = None
    _MIRROR_OK = False

WEIGHTS_PATH = _HERE / "rl_policy_weights.json"        # stance (obs 68)
WALK_WEIGHTS_PATH = _HERE / "rl_walk_weights.json"     # walk (obs 72)
# Backward-compatible module constants for offline helpers/tests. Hardware
# episodes use each policy's required meta["training_hz"] below.
DEFAULT_TRAINING_HZ = 25.0
LEGACY_POLICY_HZ = DEFAULT_TRAINING_HZ
try:
    _RUNNER_CFG = load_config(str(_HERE.parent / "rl_move" / "config.yaml"))
except Exception:                                          # pragma: no cover
    _RUNNER_CFG = {}
HZ = float(cfg_get(_RUNNER_CFG, "control", "hz",
                   default=LEGACY_POLICY_HZ) or LEGACY_POLICY_HZ)
DT = 1.0 / HZ
MAX_INNER_STEPS = 8

# Timing trips are relative to each policy's declared tick budget. Tiny
# scheduler slips are counted but tolerated; repeated or large misses are
# treated as a controller fault and the runner stops commanding motion.
TIMING_LATE_GRACE_MIN_S = 0.002
TIMING_LATE_GRACE_FRAC = 0.10
TIMING_HARD_LAG_FRAC = 0.50
TIMING_MAX_CONSECUTIVE_LATE = 3
TIMING_WALK_STARTUP_GRACE_TICKS = 3
TIMING_WALK_HARD_LAG_S = 0.05
DRIVE_TIMING_STARTUP_GRACE_TICKS = 3
DRIVE_ASYNC_SNAPSHOT_HZ = 10.0
# A 250 ms cached state let several 100 Hz policy decisions run after the
# IMU/servo sample had stopped advancing.  Keep one normal 10 Hz sample
# interval plus a small UART/scheduler margin, but never a quarter-second of
# blind learned motion.
DRIVE_ASYNC_STATE_MAX_AGE_S = 0.15
ASYNC_READY_GOOD_SAMPLES = 3
ASYNC_READY_TIMEOUT_S = 1.0
DRIVE_BUS_WRITE_MAX_HZ = 50.0
DRIVE_TIMING_HARD_LAG_S = 0.05
DRIVE_TIMING_CRITICAL_LAG_S = 0.20
DRIVE_TIMING_HARD_LAG_CONSECUTIVE = 2
DRIVE_TIMING_MAX_CONSECUTIVE_LATE = 12

_TIMING_KEYS = (
    "service_s", "obs_s", "policy_s", "safety_s", "write_s", "read_s",
    "lag_s",
)


class AsyncReadinessFailure(str):
    """JSON-compatible typed async readiness failure."""

    def __new__(cls, message: str, *, kind: str, reason: str,
                detail: str = ""):
        obj = str.__new__(cls, message)
        obj.kind = str(kind)
        obj.reason = str(reason)
        obj.detail = str(detail)
        return obj

    @property
    def confirmed_physical(self) -> bool:
        return self.kind == "physical_health"


def _async_readiness_requires_limp(error) -> bool:
    return (isinstance(error, AsyncReadinessFailure)
            and error.confirmed_physical)

# Interactive learned-stand runs should release to joystick control once the
# trained height ramp has produced a calm upright pose. Full-profile holds are
# still available by disabling stand_handoff or by requesting extra_hold_s.
STAND_HANDOFF_STABLE_S = 0.75
STAND_HANDOFF_SETTLE_S = 0.25
STAND_HANDOFF_MAX_TILT_DEG = 7.0
STAND_HANDOFF_MAX_CURRENT_A = 2.2


def policy_control_hz_error(meta: dict, name: str = "policy") -> str | None:
    """Compatibility hook: playback now adapts instead of rejecting."""
    _ = (meta, name)
    return None

def policy_profile(policy: "NumpyPolicy", mode: str) -> dict:
    """Return the exact training profile declared by a v2 policy."""
    prof = (policy.meta.get("profile") or {}).get(mode)
    required = {"hold_s", "ramp_s", "target_m", "total_s"}
    if not isinstance(prof, dict) or not required.issubset(prof):
        missing = sorted(required - set(prof or {}))
        raise ValueError(
            f"policy profile {mode!r} is incomplete; missing {missing}")
    return {key: float(prof[key]) for key in sorted(required)}


def policy_joint_frame(policy: "NumpyPolicy", cfg: dict | None = None) -> str:
    """Validate the repository-wide robot-absolute policy contract."""
    del cfg
    source = policy.meta.get("name") or policy.meta.get("source") or "policy"
    return require_robot_abs_joint_frame(policy.meta, source=str(source))


def _state_for_policy_frame(state, joint_frame: str):
    """Return robot state after rejecting any non-canonical frame."""
    if joint_frame != FRAME_ROBOT_ABS:
        raise ValueError(f"unsupported policy joint frame {joint_frame!r}")
    return state


def _finite_float(value, default: float) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float(default)
    return out if math.isfinite(out) else float(default)


def _positive_float(value, default: float) -> float:
    out = _finite_float(value, default)
    return out if out > 0.0 else float(default)


def _clamped_int(value, default: int, lo: int, hi: int) -> int:
    try:
        out = int(round(float(value)))
    except (TypeError, ValueError):
        out = int(default)
    return max(lo, min(hi, out))


@dataclass(frozen=True)
class PolicyTiming:
    """Per-episode timing chosen from the selected policy's contract."""

    policy_hz: float
    policy_dt: float
    trained_control_hz: float
    trained_control_hz_explicit: bool
    runner_config_hz: float

    @property
    def adapted(self) -> bool:
        return abs(self.policy_hz - self.runner_config_hz) > 1e-6


@dataclass(frozen=True)
class DriveWriteCadence:
    """Servo-bus write cadence for live joystick drive."""

    requested_hz: float
    write_hz: float
    write_dt: float
    write_every_ticks: int


def policy_training_hz(policy: "NumpyPolicy") -> float:
    """The control rate this policy was trained at.

    This is a hard deployment contract: qd filters, action-delta costs,
    phase clocks, and the observed plant dynamics are all tick-rate
    conditioned. A 25 Hz policy should not silently run at 50/100 Hz.
    """
    meta = policy.meta or {}
    if "training_hz" not in meta:
        src = meta.get("name") or meta.get("source") or "policy"
        raise ValueError(f"{src}: missing meta.training_hz")
    try:
        hz = float(meta["training_hz"])
    except (TypeError, ValueError) as exc:
        raise ValueError("meta.training_hz must be numeric") from exc
    if not math.isfinite(hz) or hz < 1.0 or hz > 200.0:
        raise ValueError(
            f"meta.training_hz must be finite and in [1, 200], got {hz!r}")
    return hz


def _policy_control_hz(policy: "NumpyPolicy") -> tuple[float, bool]:
    """Return the required trained policy decision Hz."""
    return policy_training_hz(policy), True


def _policy_timing(policy: "NumpyPolicy") -> PolicyTiming:
    trained_hz, explicit = _policy_control_hz(policy)
    policy_hz = _positive_float(trained_hz, LEGACY_POLICY_HZ)
    return PolicyTiming(
        policy_hz=policy_hz,
        policy_dt=1.0 / policy_hz,
        trained_control_hz=trained_hz,
        trained_control_hz_explicit=explicit,
        runner_config_hz=HZ,
    )


def _check_policy_control_hz(policy: "NumpyPolicy", role: str) -> str | None:
    """Compatibility hook: playback now adapts instead of rejecting."""
    _ = role
    _policy_timing(policy)
    return None


def _timing_late_grace(dt: float) -> float:
    return max(TIMING_LATE_GRACE_MIN_S, dt * TIMING_LATE_GRACE_FRAC)


def _timing_trip_reason(mode: str, tick: int, hz: float, late_s: float,
                        consecutive_late: int) -> str | None:
    dt = 1.0 / hz
    # The first MCU stream write can pay cache/transport setup costs that are
    # not representative of the steady 100 Hz loop.  Count that jitter in the
    # timing report, but do not turn one startup bubble into a torque cut.
    if mode == "walk" and tick < TIMING_WALK_STARTUP_GRACE_TICKS:
        return None
    grace = _timing_late_grace(dt)
    if late_s <= grace:
        return None
    hard_lag_s = (TIMING_WALK_HARD_LAG_S if mode == "walk"
                  else dt * TIMING_HARD_LAG_FRAC)
    if late_s >= hard_lag_s:
        return (f"{mode} timing overrun: tick {tick} missed the "
                f"{hz:g} Hz deadline by {late_s * 1000.0:.1f} ms")
    if consecutive_late >= TIMING_MAX_CONSECUTIVE_LATE:
        return (f"{mode} timing overrun: {consecutive_late} consecutive "
                f"ticks missed the {hz:g} Hz deadline")
    return None


def _ms_stats(values: list[float]) -> dict:
    if not values:
        return {"samples": 0}
    arr = np.asarray(values, dtype=float) * 1000.0
    return {
        "samples": int(arr.size),
        "mean_ms": round(float(np.mean(arr)), 3),
        "p50_ms": round(float(np.percentile(arr, 50)), 3),
        "p95_ms": round(float(np.percentile(arr, 95)), 3),
        "max_ms": round(float(np.max(arr)), 3),
    }


class _TimingStats:
    def __init__(self):
        self.count = 0
        self.maxes = {k: 0.0 for k in _TIMING_KEYS}
        self.totals = {k: 0.0 for k in _TIMING_KEYS}

    def add(self, timing: dict) -> None:
        self.count += 1
        for k in _TIMING_KEYS:
            v = float(timing.get(k) or 0.0)
            self.totals[k] += v
            self.maxes[k] = max(self.maxes[k], v)

    def summary(self) -> dict:
        if self.count <= 0:
            return {"ticks": 0}
        out = {"ticks": self.count}
        for k in _TIMING_KEYS:
            name = k[:-2] + "_ms"
            out["mean_" + name] = round(
                self.totals[k] * 1000.0 / self.count, 3)
            out["max_" + name] = round(self.maxes[k] * 1000.0, 3)
        return out


def _policy_bus_profile(policy: "NumpyPolicy", cfg: dict) -> tuple[int, int]:
    """Bus profile requested by policy metadata, with config fallback."""
    meta = policy.meta or {}
    speed = meta.get("bus_write_speed",
                     cfg_get(cfg, "bus", "write_speed", default=400))
    acc = meta.get("bus_write_acc",
                   cfg_get(cfg, "bus", "write_acc", default=20))
    return (_clamped_int(speed, 400, 0, 4095),
            _clamped_int(acc, 20, 0, 254))


def _policy_safety_max_delta_q_deg(policy: "NumpyPolicy", cfg: dict,
                                   policy_hz: float) -> tuple[float, bool]:
    """Policy-tick joint slew, preserving old policies under new config.

    A metadata value is a trained per-policy-tick cap and wins. Without
    metadata, convert the config's per-tick cap at config control.hz into
    the same deg/s envelope at the selected policy cadence; this maps the
    current 100 Hz 0.375 deg/tick config back to 1.5 deg/tick for 25 Hz
    legacy policies.
    """
    cfg_dq = _positive_float(
        cfg_get(cfg, "safety", "max_delta_q_deg", default=1.5), 1.5)
    cfg_hz = _positive_float(
        cfg_get(cfg, "control", "hz", default=HZ), HZ)
    fallback = cfg_dq * cfg_hz / _positive_float(
        policy_hz, LEGACY_POLICY_HZ)
    meta = policy.meta or {}
    for key in ("safety_max_delta_q_deg", "max_delta_q_deg"):
        if key in meta:
            return _positive_float(meta[key], fallback), True
    safety = meta.get("safety")
    if isinstance(safety, dict) and "max_delta_q_deg" in safety:
        return _positive_float(safety["max_delta_q_deg"], fallback), True
    return fallback, False


def _apply_policy_safety_timing(safety: SafetyLayer, policy: "NumpyPolicy",
                                cfg: dict, timing: PolicyTiming
                                ) -> tuple[float, bool]:
    max_dq_deg, explicit = _policy_safety_max_delta_q_deg(
        policy, cfg, timing.policy_hz)
    safety.max_dq = math.radians(max_dq_deg)
    safety._hz = timing.policy_hz
    trip_s = _positive_float(
        cfg_get(cfg, "safety", "over_current_trip_s", default=0.8), 0.8)
    safety._over_current_trip_ticks = max(
        1, int(round(trip_s * timing.policy_hz)))
    return max_dq_deg, explicit


def _inner_stream_plan(policy: "NumpyPolicy", cfg: dict,
                       policy_hz: float | None = None
                       ) -> tuple[int, float, float]:
    """How to split one policy target into servo-stream substeps."""
    base_hz = _positive_float(policy_hz if policy_hz is not None else HZ, HZ)
    base_dt = 1.0 / base_hz
    meta = policy.meta or {}
    raw_hz = None
    for key in ("inner_stream_hz", "servo_inner_hz", "inner_hz"):
        if key in meta:
            raw_hz = meta[key]
            break
    if raw_hz is None:
        raw_hz = cfg_get(cfg, "control", "inner_hz", default=base_hz)
    requested_hz = _positive_float(raw_hz, base_hz)
    if requested_hz <= base_hz:
        return 1, base_hz, base_dt
    steps = max(1, min(MAX_INNER_STEPS, int(round(requested_hz / base_hz))))
    actual_hz = base_hz * steps
    return steps, actual_hz, 1.0 / actual_hz


def _drive_write_plan(policy: "NumpyPolicy", cfg: dict,
                      policy_hz: float | None = None) -> DriveWriteCadence:
    """Choose hardware write cadence without changing policy cadence.

    Learned obs/action/phase/safety still run at ``policy_hz``. The servo bus
    can be commanded at a lower divisor cadence when live traces show the
    transport cannot reliably complete one all-joint write per policy tick.
    """
    base_hz = _positive_float(policy_hz if policy_hz is not None else HZ, HZ)
    fallback_hz = min(base_hz, DRIVE_BUS_WRITE_MAX_HZ)
    meta = policy.meta or {}
    raw_hz = None
    for key in ("drive_write_hz", "bus_write_hz", "servo_write_hz"):
        if key in meta:
            raw_hz = meta[key]
            break
    if raw_hz is None:
        raw_hz = cfg_get(cfg, "control", "drive_write_hz",
                         default=fallback_hz)
    requested_hz = min(base_hz, _positive_float(raw_hz, fallback_hz))
    if requested_hz >= base_hz * 0.99:
        write_every = 1
    else:
        write_every = max(1, int(math.ceil(base_hz / requested_hz)))
    write_hz = base_hz / write_every
    return DriveWriteCadence(
        requested_hz=requested_hz,
        write_hz=write_hz,
        write_dt=1.0 / write_hz,
        write_every_ticks=write_every,
    )


def _policy_move_uses_async(mode: str, policy_hz: float) -> bool:
    """Use the bounded async transport only where the direct loop cannot fit.

    Legacy 25/50 Hz stance playback and the existing timed-walk path stay on
    their established transport.  The new 100 Hz stand/lower checkpoints use
    a 50 Hz write divisor while policy/obs/safety continue at trained cadence.
    """
    return (mode in ("stand", "lower")
            and float(policy_hz) > DRIVE_BUS_WRITE_MAX_HZ + 1e-6)


def _apply_async_safety_feedback_timing(
        safety: SafetyLayer, cfg: dict, snapshot_hz: float) -> float:
    """Express sustained-current debounce in fresh feedback samples.

    Async policy ticks may consume the same physical snapshot repeatedly.
    Health values are therefore exposed to ``SafetyLayer`` only once per
    actual full-feedback read.  Convert its current trip count from policy
    ticks to that physical feedback cadence so the configured duration does
    not silently become 10x longer (or one cached spike 10x stronger).
    """
    configured_hz = _positive_float(
        cfg_get(cfg, "sensing", "full_feedback_hz", default=snapshot_hz),
        snapshot_hz)
    feedback_hz = min(_positive_float(snapshot_hz, 1.0), configured_hz)
    trip_s = _positive_float(
        cfg_get(cfg, "safety", "over_current_trip_s", default=0.8), 0.8)
    safety._over_current_trip_ticks = max(  # noqa: SLF001
        1, int(round(trip_s * feedback_hz)))
    return feedback_hz


def _state_for_async_safety(state):
    """Hide replayed servo-health values from tick-counting safety checks.

    Position/IMU state remains available at every policy tick.  Current,
    load, and temperature remain cached on the state for logging, but only a
    newly delivered physical full-feedback read is allowed to advance or
    clear their debounces.
    """
    timing = dict(getattr(state, "timing", {}) or {})
    if timing.get("async_sample_seq") is None:
        return state
    if bool(timing.get("async_feedback_fresh",
                       timing.get("async_health_fresh"))):
        return state
    return replace(
        state,
        servo_load=None,
        servo_current=None,
        servo_temperature=None,
    )


def _u16_seq_advanced(current: int, previous: int) -> bool:
    """True only for forward movement of a wrapping uint16 sequence."""
    delta = (int(current) - int(previous)) & 0xFFFF
    return 0 < delta < 0x8000


def _probe_async_transport(bus, *, samples: int = 3,
                           max_age_s: float = DRIVE_ASYNC_STATE_MAX_AGE_S,
                           sample_gap_s: float = 0.01) -> dict:
    """Read-only proof that sequenced snapshot transport is advancing."""
    out: dict = {
        "source": "read_snapshot",
        "requested_samples": max(2, int(samples)),
        "snapshot_count": 0,
        "seq_first": None,
        "seq_last": None,
        "seq_advance_count": 0,
        "max_pos_age_ms": None,
        "max_imu_age_ms": None,
        "async_capable": False,
    }
    read_snapshot = getattr(bus, "read_snapshot", None)
    if not callable(read_snapshot):
        out.update(source="unsupported",
                   error="read_snapshot unavailable")
        return out
    if getattr(bus, "has_stream", None) is False:
        out.update(source="legacy_read",
                   error="MCU sequenced snapshot mode unavailable")
        return out

    seqs: list[int] = []
    pos_ages: list[float] = []
    imu_ages: list[float] = []
    error = ""
    for index in range(out["requested_samples"]):
        try:
            snap = read_snapshot()
        except Exception as exc:
            error = f"read_snapshot failed: {exc}"
            break
        if not isinstance(snap, dict):
            error = "read_snapshot returned no data"
            break
        try:
            seq = int(snap["seq"]) & 0xFFFF
            pos_age = float(snap["pos_age_ms"])
            imu_age = float(snap["imu_age_ms"])
        except (KeyError, TypeError, ValueError) as exc:
            error = f"invalid snapshot metadata: {exc}"
            break
        if (not math.isfinite(pos_age) or pos_age < 0.0
                or not math.isfinite(imu_age) or imu_age < 0.0):
            error = "snapshot ages are invalid"
            break
        seqs.append(seq)
        pos_ages.append(pos_age)
        imu_ages.append(imu_age)
        if index + 1 < out["requested_samples"] and sample_gap_s > 0.0:
            time.sleep(float(sample_gap_s))

    out["snapshot_count"] = len(seqs)
    if seqs:
        out["seq_first"] = seqs[0]
        out["seq_last"] = seqs[-1]
        out["seq_advance_count"] = sum(
            _u16_seq_advanced(cur, prev)
            for prev, cur in zip(seqs, seqs[1:]))
        out["max_pos_age_ms"] = round(max(pos_ages), 3)
        out["max_imu_age_ms"] = round(max(imu_ages), 3)
    max_age_ms = float(max_age_s) * 1000.0
    all_advanced = (len(seqs) == out["requested_samples"]
                    and out["seq_advance_count"] == len(seqs) - 1)
    ages_ok = bool(pos_ages and imu_ages
                   and max(pos_ages) <= max_age_ms
                   and max(imu_ages) <= max_age_ms)
    out["async_capable"] = bool(not error and all_advanced and ages_ok)
    if error:
        out["error"] = error
    elif not all_advanced:
        out["error"] = "snapshot sequence did not advance on every sample"
    elif not ages_ok:
        out["error"] = f"snapshot source age exceeds {max_age_ms:.1f} ms"
    return out


def _stream_state_is_stale(state) -> bool:
    timing = getattr(state, "timing", {}) or {}
    return bool(timing.get("stale_feedback"))


def _stale_stream_state(last_good_state, stale_ticks: int, q_cmd=None,
                        diag: dict | None = None):
    """Return a last-known-good RobotState marked as stale feedback."""
    if last_good_state is None:
        return None
    timing = dict(getattr(last_good_state, "timing", {}) or {})
    timing.update({
        "stale_feedback": True,
        "stale_ticks": int(stale_ticks),
    })
    if diag:
        timing["stale_diag"] = _json_safe(diag)
    kwargs = {
        "timestamp": time.monotonic(),
        "bus_ok": True,
        "timing": timing,
    }
    if q_cmd is not None and hasattr(last_good_state, "commanded_position"):
        kwargs["commanded_position"] = np.asarray(
            q_cmd, dtype=float).copy()
    return replace(last_good_state, **kwargs)


def _stream_target(bus, est: RobotStateEstimator,
                   q_from_robot: np.ndarray, q_to_robot: np.ndarray, *,
                   t_next: float, inner_steps: int, inner_dt: float,
                   write_speed: int, write_acc: int,
                   abort_check, last_good_state=None,
                   stale_ticks: int = 0,
                   max_stale_ticks: int = 0
                   ) -> tuple[object | None, float, int, str, int, int, dict]:
    """Write interpolated servo targets up to q_to_robot.

    The caller still runs the policy once per selected policy tick. This
    helper only smooths the command sent to the MCU/bus and returns the
    latest sampled robot state at the end of that policy tick.
    """
    state_robot = last_good_state
    overruns = 0
    stale_samples = 0
    stream_t0 = time.monotonic()
    write_s = 0.0
    read_s = 0.0
    lag_s = 0.0
    stale_ticks = max(0, int(stale_ticks))
    max_stale_ticks = max(0, int(max_stale_ticks))
    q_from = np.asarray(q_from_robot, dtype=float)
    q_to = np.asarray(q_to_robot, dtype=float)
    steps = max(1, int(inner_steps))
    step_all = getattr(bus, "step_all", None)
    can_step_all = callable(step_all)
    stream_firmware = bool(getattr(bus, "has_stream", False))
    last_diag: dict | None = None

    def stream_timing() -> dict:
        return {
            "stream_s": time.monotonic() - stream_t0,
            "write_s": write_s,
            "read_s": read_s,
            "lag_s": lag_s,
        }

    for sub in range(1, steps + 1):
        if abort_check():
            return (
                state_robot, t_next, overruns, "aborted", stale_ticks,
                stale_samples, stream_timing())
        alpha = sub / steps
        q_cmd = q_to if sub == steps else q_from + (q_to - q_from) * alpha
        est.set_commanded(q_cmd)
        q_cmd_deg = (q_cmd * RAD2DEG).tolist()
        state_robot = None
        step_all_attempted = False
        diag = {
            "transport": "legacy_write_read",
            "substep": sub,
            "inner_steps": steps,
            "stale_ticks_before": stale_ticks,
            "stream_firmware": stream_firmware,
            "step_all_available": can_step_all,
            "write_speed": int(write_speed),
            "write_acc": int(write_acc),
        }
        if can_step_all:
            step_all_attempted = True
            diag["transport"] = "step_all"
            op_t = time.monotonic()
            try:
                snap = step_all(q_cmd_deg, speed=write_speed,
                                acc=write_acc)
            except Exception as e:
                diag["transport_error"] = repr(e)
                snap = None
            write_s += time.monotonic() - op_t
            if snap is not None:
                diag["snapshot_seq"] = snap.get("seq")
                diag["pos_age_ms"] = snap.get("pos_age_ms")
                diag["imu_age_ms"] = snap.get("imu_age_ms")
                update_from_snapshot = getattr(est, "update_from_snapshot",
                                               None)
                if callable(update_from_snapshot):
                    state_robot = update_from_snapshot(snap)
                else:
                    diag["snapshot_consumer"] = "est.update_fallback"
                    state_robot = est.update()
            elif not stream_firmware:
                diag["step_all_none"] = True
                diag["fallback"] = "legacy_write_read"
                step_all_attempted = False
            else:
                diag["step_all_none"] = True
                diag["fallback_suppressed"] = "stream_firmware"
        if not step_all_attempted:
            diag["transport"] = "legacy_write_read"
            op_t = time.monotonic()
            bus.write_all(q_cmd_deg, speed=write_speed, acc=write_acc)
            write_s += time.monotonic() - op_t

        t_next += inner_dt
        lag = time.monotonic() - t_next
        if lag > 0:
            overruns += 1
            diag["overrun_lag_ms"] = round(float(lag) * 1000.0, 3)
            lag_s = max(lag_s, float(lag))
            t_next = time.monotonic()
        else:
            time.sleep(-lag)

        if state_robot is None and not step_all_attempted:
            op_t = time.monotonic()
            try:
                state_robot = est.update()
            except Exception as e:
                diag["est_update_error"] = repr(e)
                state_robot = None
            read_s += time.monotonic() - op_t
        if state_robot is not None:
            timing = dict(getattr(state_robot, "timing", {}) or {})
            diag["state_source"] = timing.get("source")
            diag["state_bus_ok"] = bool(getattr(state_robot, "bus_ok", False))
            diag["state_imu_ok"] = bool(getattr(state_robot, "imu_ok", False))
            diag["state_t_total_ms"] = round(
                float(timing.get("t_total") or 0.0) * 1000.0, 3)
            if timing.get("snapshot_seq") is not None:
                diag["state_snapshot_seq"] = timing.get("snapshot_seq")
            if timing.get("pos_age_ms") is not None:
                diag["state_pos_age_ms"] = timing.get("pos_age_ms")
            if timing.get("imu_age_ms") is not None:
                diag["state_imu_age_ms"] = timing.get("imu_age_ms")
        if last_good_state is not None:
            good_timing = dict(getattr(last_good_state, "timing", {}) or {})
            diag["last_good_age_ms"] = round(
                max(0.0, time.monotonic()
                    - float(getattr(last_good_state, "timestamp", 0.0)))
                * 1000.0, 1)
            diag["last_good_source"] = good_timing.get("source")
            if good_timing.get("snapshot_seq") is not None:
                diag["last_good_snapshot_seq"] = good_timing.get("snapshot_seq")
            if good_timing.get("pos_age_ms") is not None:
                diag["last_good_pos_age_ms"] = good_timing.get("pos_age_ms")
            if good_timing.get("imu_age_ms") is not None:
                diag["last_good_imu_age_ms"] = good_timing.get("imu_age_ms")
        last_diag = diag
        if state_robot is None or not state_robot.bus_ok:
            stale_ticks += 1
            stale_samples += 1
            diag["stale_ticks_after"] = stale_ticks
            diag["stale_samples_total"] = stale_samples
            diag["max_stale_ticks"] = max_stale_ticks
            if last_good_state is not None:
                state_robot = _stale_stream_state(
                    last_good_state, stale_ticks, q_cmd=q_cmd,
                    diag=diag)
            if (last_good_state is not None
                    and stale_ticks <= max_stale_ticks):
                continue
            return (state_robot, t_next, overruns,
                    "feedback stale during stream", stale_ticks,
                    stale_samples, stream_timing())
        if getattr(state_robot, "timing", None) is not None:
            state_robot.timing["stream_diag"] = _json_safe(last_diag or diag)
        last_good_state = state_robot
        stale_ticks = 0
    return (state_robot, t_next, overruns, "", stale_ticks, stale_samples,
            stream_timing())


_ASYNC_SAMPLER_GUARD = threading.local()


def _register_async_sampler(sampler) -> None:
    active = getattr(_ASYNC_SAMPLER_GUARD, "active", None)
    if active is None:
        active = []
        _ASYNC_SAMPLER_GUARD.active = active
    if sampler not in active:
        active.append(sampler)


def _unregister_async_sampler(sampler) -> None:
    active = getattr(_ASYNC_SAMPLER_GUARD, "active", None)
    if active is not None and sampler in active:
        active.remove(sampler)


def _stop_active_async_samplers() -> None:
    """Exception guard for worker-owned background sampler threads."""
    active = list(getattr(_ASYNC_SAMPLER_GUARD, "active", ()) or ())
    failures: list[str] = []
    for sampler in reversed(active):
        try:
            sampler.stop()
        except Exception as exc:
            failures.append(str(exc))
    if failures:
        raise AsyncSamplerCleanupError(
            "async sampler cleanup failed; bus use remains blocked: "
            + "; ".join(failures))


class _AsyncSnapshotSampler:
    """Background state reader for high-rate learned-policy playback.

    The MCU already free-runs the expensive servo/IMU acquisition. This
    thread only copies those caches over the host link at a lower rate so
    the 100 Hz policy loop can keep its hot path to write-only commands.

    ``latest()`` assigns a host-side sequence to each completed acquisition
    and delivers its freshness marker exactly once.  The RobotState (including
    cached current/load/temperature) may be reused between acquisitions, but
    ``timing.full_feedback``/``async_health_fresh`` may never be replayed: the
    safety layer's consecutive-sample debounces depend on that distinction.
    """

    def __init__(self, bus, cfg: dict, *, initial_state=None,
                 hz: float = DRIVE_ASYNC_SNAPSHOT_HZ,
                 max_age_s: float = DRIVE_ASYNC_STATE_MAX_AGE_S):
        self.cfg = cfg
        self.bus = bus
        self.est = RobotStateEstimator(bus, cfg)
        self.interval_s = 1.0 / max(1.0, float(hz))
        requested_age_s = _positive_float(
            max_age_s, DRIVE_ASYNC_STATE_MAX_AGE_S)
        self.max_age_s = min(requested_age_s,
                             DRIVE_ASYNC_STATE_MAX_AGE_S)
        self._latest = None
        self._latest_good = None
        self._sample_seq = 0
        self._delivered_seq: int | None = None
        self._last_mcu_snapshot_seq: int | None = None
        self._health_timestamp: float | None = None
        self._motion_ready = False
        self._stop_failed = False
        if initial_state is not None:
            initial_timing = dict(
                getattr(initial_state, "timing", {}) or {})
            # If preflight itself came from the MCU stream, the first
            # background sample must advance beyond it.  Otherwise a frozen
            # cache could be counted once merely because the host sampler is
            # new (the remaining readiness samples would still reject it,
            # but no accepted stream sample should be physically duplicate).
            if initial_timing.get("snapshot_seq") is not None:
                try:
                    self._last_mcu_snapshot_seq = (
                        int(initial_timing["snapshot_seq"]) & 0xFFFF)
                except (TypeError, ValueError):
                    pass
            initial_timing.update({
                "async_sample_seq": 0,
                "async_source_full_feedback": (
                    self._source_full_feedback_complete(initial_state)),
            })
            tagged_initial = replace(initial_state, timing=initial_timing)
            self._latest = tagged_initial
            if getattr(tagged_initial, "bus_ok", False):
                self._latest_good = tagged_initial
                if self._source_full_feedback_complete(tagged_initial):
                    self._health_timestamp = float(
                        getattr(tagged_initial, "timestamp", time.monotonic()))
        self._cmd = (np.asarray(getattr(initial_state, "commanded_position",
                                        np.zeros(N_JOINTS)), dtype=float)
                     .reshape(N_JOINTS).copy())
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.samples = 0
        self.good_samples = 0
        self.errors = 0
        self.physical_rejects = 0
        self.last_error = ""
        self.update_times: list[float] = []

    def start(self, *, delay_s: float = 0.0) -> None:
        require_bus_available(self.bus)
        if self._stop_failed or self._stop.is_set():
            raise RuntimeError("async snapshot sampler cannot be restarted")
        if self._thread is not None:
            return
        _register_async_sampler(self)
        self._thread = threading.Thread(
            target=self._run, args=(max(0.0, float(delay_s)),),
            name="rl-drive-snapshot",
            daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        with self._lock:
            self._motion_ready = False
        thread = self._thread
        if thread is not None and thread.is_alive():
            # Bound this join, not the whole serial transaction: its staged
            # reads/lock wait may take longer. A live reader quarantines the
            # bus across worker threads until a later successful join.
            thread.join(timeout=max(2.5, self.interval_s * 2.0))
        if thread is not None and thread.is_alive():
            with self._lock:
                self._stop_failed = True
                self.last_error = "async snapshot sampler failed to stop"
            # Deliberately retain both the live thread handle and registry
            # entry. Callers must not start foreground bus recovery now.
            quarantine_bus(self.bus, self, self.last_error)
            raise AsyncSamplerCleanupError(self.last_error)
        clear_bus_quarantine(self.bus, self)
        self._thread = None
        _unregister_async_sampler(self)

    def set_commanded(self, q_rad: np.ndarray) -> None:
        with self._lock:
            self._cmd = np.asarray(q_rad, dtype=float).reshape(
                N_JOINTS).copy()

    def mark_motion_ready(self) -> None:
        with self._lock:
            self._motion_ready = True

    @property
    def motion_ready(self) -> bool:
        with self._lock:
            return self._motion_ready

    def latest(self) -> tuple[object | None, float | None, dict]:
        with self._lock:
            state = self._latest_good
            now = time.monotonic()
            if state is None:
                return None, None, self._stats_locked(now)
            timing = dict(getattr(state, "timing", {}) or {})
            seq = int(timing.get("async_sample_seq", 0))
            sample_fresh = seq != self._delivered_seq
            if sample_fresh:
                self._delivered_seq = seq
            source_full_feedback = bool(
                timing.get("async_source_full_feedback",
                           timing.get("full_feedback")))
            health_fresh = sample_fresh and source_full_feedback
            source_feedback_sample = bool(
                timing.get("feedback_sample_fresh",
                           timing.get("full_feedback_attempted")))
            feedback_sample_fresh = sample_fresh and source_feedback_sample
            host_age_s = max(
                0.0, now - float(getattr(state, "timestamp", 0.0)))
            mcu_age_s = 0.0
            if timing.get("snapshot_seq") is not None:
                mcu_age_s = max(
                    float(timing.get("pos_age_ms") or 0.0),
                    float(timing.get("imu_age_ms") or 0.0)) / 1000.0
            # Firmware age is already present when the host acquires the
            # cache; add subsequent host residence rather than considering
            # only the most recent Python timestamp.
            age_s = host_age_s + mcu_age_s
            health_age_s = (None if self._health_timestamp is None else
                            max(0.0, now - self._health_timestamp))
            health_ok = (self._has_servo_health(state)
                         and health_age_s is not None
                         and health_age_s <= self.max_age_s)
            timing.update({
                "async_sample_fresh": sample_fresh,
                "async_health_fresh": health_fresh,
                "async_feedback_fresh": feedback_sample_fresh,
                "async_health_ok": health_ok,
                "async_health_age_ms": (
                    round(health_age_s * 1000.0, 3)
                    if health_age_s is not None else None),
                "async_host_age_ms": round(host_age_s * 1000.0, 3),
                "async_mcu_age_ms": round(mcu_age_s * 1000.0, 3),
                # SafetyLayer uses this exact key for its fresh-temperature
                # debounce.  Never let a cached state replay it.
                "full_feedback": health_fresh,
                "full_feedback_attempted": feedback_sample_fresh,
                "feedback_sample_fresh": feedback_sample_fresh,
            })
            delivered = replace(state, timing=timing)
            return delivered, age_s, self._stats_locked(now)

    def stats(self) -> dict:
        with self._lock:
            return self._stats_locked(time.monotonic())

    @staticmethod
    def _has_servo_health(state) -> bool:
        for key in ("servo_load", "servo_current", "servo_temperature"):
            value = getattr(state, key, None)
            if value is None:
                return False
            try:
                arr = np.asarray(value, dtype=float).reshape(N_JOINTS)
            except (TypeError, ValueError):
                return False
            if not np.all(np.isfinite(arr)):
                return False
        return True

    @classmethod
    def _source_full_feedback_complete(cls, state) -> bool:
        timing = dict(getattr(state, "timing", {}) or {})
        try:
            count = int(timing.get("full_feedback_count", -1))
            ids = sorted(int(value) for value in
                         timing.get("full_feedback_ids", ()))
        except (TypeError, ValueError):
            return False
        return bool(
            timing.get("full_feedback")
            and timing.get("full_feedback_complete")
            and count == N_JOINTS
            and ids == list(range(N_JOINTS))
            and cls._has_servo_health(state))

    def _stats_locked(self, now: float) -> dict:
        health_age_s = (None if self._health_timestamp is None else
                        max(0.0, now - self._health_timestamp))
        return {
            "snapshot_hz": round(1.0 / self.interval_s, 3),
            "max_age_ms": round(self.max_age_s * 1000.0, 1),
            "samples": int(self.samples),
            "good_samples": int(self.good_samples),
            "latest_sample_seq": int(self._sample_seq),
            "delivered_sample_seq": self._delivered_seq,
            "motion_ready": self._motion_ready,
            "stop_failed": self._stop_failed,
            "thread_alive": bool(
                self._thread is not None and self._thread.is_alive()),
            "health_age_ms": (round(health_age_s * 1000.0, 3)
                              if health_age_s is not None else None),
            "errors": int(self.errors),
            "physical_rejects": int(self.physical_rejects),
            "last_error": self.last_error or None,
            "update": _ms_stats(self.update_times[-128:]),
        }

    def _physical_timing_error_locked(self, timing: dict) -> str:
        """Validate MCU cache metadata before any stateful filtering."""
        timing = dict(timing or {})
        source = str(timing.get("source") or "")
        raw_seq = timing.get("snapshot_seq")
        stream_state = raw_seq is not None or source in {
            "read_snapshot", "step_all"}
        if not stream_state:
            if source == "legacy_read":
                # ASCII IMUR carries only seven values: it has no MCU sample
                # sequence or age. A host transaction/timestamp therefore
                # cannot distinguish a live stationary IMU from a frozen
                # bridge/cache. Async learned motion requires the sequenced
                # snapshot protocol rather than guessing from value changes.
                return "legacy feedback has no physical freshness proof"
            # Synthetic/simulation estimators without MCU cache metadata use
            # a new host acquisition sequence. The real legacy hardware path
            # is explicitly rejected above.
            return ""
        if raw_seq is None:
            return "stream snapshot missing snapshot_seq"
        try:
            seq = int(raw_seq) & 0xFFFF
        except (TypeError, ValueError):
            return f"invalid snapshot_seq {raw_seq!r}"
        max_age_ms = self.max_age_s * 1000.0
        for key in ("pos_age_ms", "imu_age_ms"):
            try:
                age_ms = float(timing[key])
            except (KeyError, TypeError, ValueError):
                return f"stream snapshot missing/invalid {key}"
            if (not math.isfinite(age_ms) or age_ms < 0.0
                    or age_ms > max_age_ms):
                return (f"stream snapshot {key} {age_ms!r} exceeds "
                        f"{max_age_ms:.1f} ms")
        previous = self._last_mcu_snapshot_seq
        if previous is not None and not _u16_seq_advanced(seq, previous):
            return (f"stream snapshot_seq did not advance "
                    f"({previous} -> {seq})")
        self._last_mcu_snapshot_seq = seq
        return ""

    def _physical_state_error_locked(self, state) -> str:
        """Compatibility wrapper for tests/diagnostics with RobotState."""
        return self._physical_timing_error_locked(
            dict(getattr(state, "timing", {}) or {}))

    def _run(self, delay_s: float) -> None:
        if delay_s and self._stop.wait(delay_s):
            return
        next_t = time.monotonic()
        while not self._stop.is_set():
            with self._lock:
                q_cmd = self._cmd.copy()
            self.est.set_commanded(q_cmd)
            t0 = time.perf_counter()
            physical_error = ""
            try:
                # Async hardware motion has no legacy fallback. Validate the
                # raw firmware sequence/ages before update_from_snapshot can
                # mutate the velocity or attitude filters.
                read_snapshot = getattr(self.bus, "read_snapshot", None)
                if not callable(read_snapshot):
                    snap = None
                    physical_error = (
                        "sequenced snapshot transport is unavailable")
                else:
                    snap = read_snapshot()
                    if not isinstance(snap, dict):
                        physical_error = (
                            "sequenced snapshot transport returned no data")
                    else:
                        physical_error = self._physical_timing_error_locked({
                            "source": "read_snapshot",
                            "snapshot_seq": snap.get("seq"),
                            "pos_age_ms": snap.get("pos_age_ms"),
                            "imu_age_ms": snap.get("imu_age_ms"),
                        })
                if physical_error or self._stop.is_set():
                    state = None
                else:
                    state = self.est.update_from_snapshot(
                        snap, want_full_feedback=False,
                        source="read_snapshot")
                    if state is None:
                        physical_error = "snapshot state conversion failed"
                    elif self._stop.is_set():
                        state = None
                    else:
                        # Force one health acquisition per sampler tick, but
                        # check cancellation between the bounded snapshot and
                        # feedback transactions. This avoids a 0.5+1.5 s
                        # uninterruptible fallback chain during shutdown.
                        state = self.est.update_feedback(state)
                err = ""
            except Exception as e:
                state = None
                err = repr(e)
            elapsed = time.perf_counter() - t0
            if self._stop.is_set():
                return
            with self._lock:
                self.samples += 1
                self.update_times.append(elapsed)
                if len(self.update_times) > 256:
                    del self.update_times[:-128]
                if physical_error:
                    self.errors += 1
                    self.physical_rejects += 1
                    self.last_error = physical_error
                if state is not None and not physical_error:
                    self._sample_seq += 1
                    timing = dict(getattr(state, "timing", {}) or {})
                    source_full_feedback = (
                        self._source_full_feedback_complete(state))
                    timing.update({
                        "async_sample_seq": self._sample_seq,
                        "async_source_full_feedback": source_full_feedback,
                    })
                    tagged = replace(state, timing=timing)
                    self._latest = tagged
                    if getattr(state, "bus_ok", False):
                        self._latest_good = tagged
                        self.good_samples += 1
                        if (source_full_feedback
                                and self._has_servo_health(tagged)):
                            self._health_timestamp = float(
                                getattr(tagged, "timestamp",
                                        time.monotonic()))
                        self.last_error = ""
                    else:
                        self.errors += 1
                        self.last_error = "snapshot bus not ok"
                elif state is None and not physical_error:
                    self.errors += 1
                    self.last_error = err or "snapshot unavailable"
            next_t = max(next_t + self.interval_s, time.monotonic())
            wait_s = max(0.0, next_t - time.monotonic())
            if wait_s and self._stop.wait(wait_s):
                return


def _async_health_safety_error(safety: SafetyLayer, state) -> str:
    """Immediate screening gate using SafetyLayer's health semantics."""
    timing = dict(getattr(state, "timing", {}) or {})
    gate = SafetyLayer(safety.cfg)
    gate.max_temp = safety.max_temp
    gate.max_current = safety.max_current
    gate.max_load = safety.max_load
    gate._over_temp_trip_ticks = 1  # noqa: SLF001
    gate._over_current_trip_ticks = 1  # noqa: SLF001
    status = gate.check_servo_health(state)
    if status is not None and status.reason in {
            "over_temp", "over_current", "over_load"}:
        suffix = f" ({status.detail})" if status.detail else ""
        return f"{status.reason}{suffix}"
    if not timing.get("async_feedback_fresh",
                      timing.get("async_health_fresh")):
        return "servo feedback is not fresh"
    if not _AsyncSnapshotSampler._source_full_feedback_complete(state):
        count = timing.get(
            "feedback_valid_count", timing.get("full_feedback_count"))
        return f"servo feedback is incomplete ({count}/{N_JOINTS})"
    return ""


def _readiness_health_gate(safety: SafetyLayer) -> SafetyLayer:
    """Independent debounce state for motionless readiness probation."""
    gate = SafetyLayer(safety.cfg)
    gate.max_temp = safety.max_temp
    gate.max_current = safety.max_current
    gate.max_load = safety.max_load
    gate._over_temp_trip_ticks = safety._over_temp_trip_ticks  # noqa: SLF001
    gate._over_current_trip_ticks = (  # noqa: SLF001
        safety._over_current_trip_ticks)  # noqa: SLF001
    gate._incomplete_feedback_trip_ticks = (  # noqa: SLF001
        safety._incomplete_feedback_trip_ticks)  # noqa: SLF001
    return gate


def _await_async_sampler_ready(
        sampler: _AsyncSnapshotSampler, abort_check, *,
        min_good_samples: int = ASYNC_READY_GOOD_SAMPLES,
        timeout_s: float | None = None,
        health_safety: SafetyLayer | None = None,
        ) -> tuple[object | None, dict, str]:
    """Require consecutive advancing, complete, safe health samples."""
    needed = max(1, int(min_good_samples))
    health_safety = health_safety or SafetyLayer(sampler.cfg)
    health_gate = _readiness_health_gate(health_safety)
    if timeout_s is None:
        # Motion remains inhibited throughout probation. Give real 10 Hz
        # health reads enough time to confirm the configured sustained trip;
        # a one-second timeout otherwise hid a two-second current fault as
        # an ordinary freshness failure, leaving the unsafe hold energized.
        confirmation_samples = max(
            needed, health_gate._over_current_trip_ticks,  # noqa: SLF001
            health_gate._over_temp_trip_ticks,  # noqa: SLF001
            health_gate._incomplete_feedback_trip_ticks)  # noqa: SLF001
        timeout_s = max(ASYNC_READY_TIMEOUT_S,
                        (confirmation_samples + 2) * sampler.interval_s)
    deadline = time.monotonic() + max(0.05, float(timeout_s))
    seen: set[int] = set()
    consecutive_good = 0
    last_seq: int | None = None
    last_error_count = 0
    last_health_error = "no fresh background sample"
    last_state = None
    last_age_s = None
    last_stats: dict = {}
    while time.monotonic() < deadline:
        if abort_check():
            return last_state, {
                "good_sequences": len(seen),
                "consecutive_healthy": consecutive_good,
                "last_health_error": last_health_error,
                "sampler": last_stats,
            }, "aborted"
        state, age_s, stats = sampler.latest()
        last_state, last_age_s, last_stats = state, age_s, stats
        timing = dict(getattr(state, "timing", {}) or {}) \
            if state is not None else {}
        seq = timing.get("async_sample_seq")
        error_count = int(stats.get("errors") or 0)
        if error_count > last_error_count:
            consecutive_good = 0
            last_health_error = str(
                stats.get("last_error") or "background sampler error")
        last_error_count = error_count
        base_healthy = bool(
            state is not None
            and getattr(state, "bus_ok", False)
            and getattr(state, "imu_ok", False)
            and age_s is not None
            and age_s <= sampler.max_age_s
            and timing.get("async_health_ok"))
        # Sequence zero is the foreground initial state, not proof that the
        # background estimator has advanced.
        if (timing.get("async_sample_fresh") and seq is not None
                and int(seq) > 0 and int(seq) != last_seq):
            last_seq = int(seq)
            seen.add(last_seq)
            health_status = health_gate.check_servo_health(state)
            if (health_status is not None
                    and health_status.reason in {
                        "over_temp", "over_current", "over_load",
                        "incomplete_feedback"}):
                detail = health_status.detail or health_status.reason
                failure = AsyncReadinessFailure(
                    f"async physical health trip: {health_status.reason} "
                    f"({detail})",
                    kind="physical_health", reason=health_status.reason,
                    detail=detail)
                return state, {
                    "good_sequences": len(seen),
                    "consecutive_healthy": 0,
                    "fresh_health": False,
                    "last_health_error": str(failure),
                    "state_age_ms": (round(float(age_s) * 1000.0, 3)
                                     if age_s is not None else None),
                    "sampler": sampler.stats(),
                }, failure
            health_error = _async_health_safety_error(
                health_safety, state)
            last_health_error = (
                health_error
                or ("" if base_healthy
                    else "state/bus/IMU/health age invalid"))
            if base_healthy and not last_health_error:
                consecutive_good += 1
            else:
                consecutive_good = 0
        if base_healthy and consecutive_good >= needed:
            sampler.mark_motion_ready()
            return state, {
                "good_sequences": len(seen),
                "consecutive_healthy": consecutive_good,
                "fresh_health": True,
                "last_health_error": None,
                "state_age_ms": round(float(age_s) * 1000.0, 3),
                "sampler": sampler.stats(),
            }, ""
        time.sleep(min(0.01, sampler.interval_s / 4.0))
    return last_state, {
        "good_sequences": len(seen),
        "consecutive_healthy": consecutive_good,
        "fresh_health": False,
        "last_health_error": last_health_error,
        "state_age_ms": (round(float(last_age_s) * 1000.0, 3)
                         if last_age_s is not None else None),
        "sampler": last_stats,
    }, AsyncReadinessFailure(
        f"async feedback not ready: {last_health_error}",
        kind="freshness", reason="feedback_not_ready",
        detail=last_health_error)


def _latest_async_tail_state(
        sampler: _AsyncSnapshotSampler) -> tuple[object | None, dict]:
    """Return a tail sample only while it remains under the hard age cap."""
    state, age_s, stats = sampler.latest()
    if (state is None
            or not getattr(state, "bus_ok", False)
            or not getattr(state, "imu_ok", False)
            or age_s is None
            or age_s > sampler.max_age_s):
        return None, stats
    return state, stats


def _stream_target_async(bus, sampler: _AsyncSnapshotSampler,
                         q_from_robot: np.ndarray,
                         q_to_robot: np.ndarray, *,
                         t_next: float, inner_steps: int, inner_dt: float,
                         write_speed: int, write_acc: int,
                         abort_check, last_good_state=None,
                         stale_ticks: int = 0,
                         max_stale_ticks: int = 0,
                         write_target: bool = True
                         ) -> tuple[object | None, float, int, str,
                                    int, int, dict]:
    """Advance one async policy tick without commanding past stale state.

    Freshness is checked *before* the optional bus write.  Once the hard age
    cap is crossed the existing goal remains held by the servos and this call
    reports a framework stop; it never sends one more learned target first.
    """
    state_robot = last_good_state
    overruns = 0
    stale_samples = 0
    stream_t0 = time.monotonic()
    write_s = 0.0
    lag_s = 0.0
    stale_ticks = max(0, int(stale_ticks))
    max_stale_ticks = max(0, int(max_stale_ticks))
    q_from = np.asarray(q_from_robot, dtype=float)
    q_to = np.asarray(q_to_robot, dtype=float)
    steps = max(1, int(inner_steps))
    last_diag: dict | None = None

    def stream_timing() -> dict:
        return {
            "stream_s": time.monotonic() - stream_t0,
            "write_s": write_s,
            "read_s": 0.0,
            "lag_s": lag_s,
        }

    if abort_check():
        return (state_robot, t_next, overruns, "aborted", stale_ticks,
                stale_samples, stream_timing())

    sampled, age_s, sampler_stats = sampler.latest()
    sample_timing = dict(getattr(sampled, "timing", {}) or {}) \
        if sampled is not None else {}
    async_tagged = sample_timing.get("async_sample_seq") is not None
    motion_ready = bool(getattr(sampler, "motion_ready", True))
    sample_usable = bool(
        motion_ready
        and sampled is not None
        and getattr(sampled, "bus_ok", False)
        and getattr(sampled, "imu_ok", False)
        and age_s is not None
        and age_s <= sampler.max_age_s
        and (not async_tagged or sample_timing.get("async_health_ok")))
    pre_diag = {
        "transport": ("async_write_snapshot" if write_target
                      else "async_skip_write_snapshot"),
        "stale_ticks_before": stale_ticks,
        "write_speed": int(write_speed),
        "write_acc": int(write_acc),
        "write_target": bool(write_target),
        "sampler": sampler_stats,
        "async_age_ms": (round(float(age_s) * 1000.0, 1)
                         if age_s is not None else None),
        "async_sample_seq": sample_timing.get("async_sample_seq"),
        "async_sample_fresh": sample_timing.get("async_sample_fresh"),
        "async_health_fresh": sample_timing.get("async_health_fresh"),
        "async_health_ok": sample_timing.get("async_health_ok"),
        "async_health_age_ms": sample_timing.get("async_health_age_ms"),
        "motion_ready": motion_ready,
    }
    if not sample_usable:
        stale_ticks += 1
        stale_samples += 1
        pre_diag["stale_ticks_after"] = stale_ticks
        pre_diag["max_stale_ticks"] = max_stale_ticks
        if last_good_state is not None:
            state_robot = _stale_stream_state(
                last_good_state, stale_ticks, q_cmd=q_from,
                diag=pre_diag)
        elif sampled is not None:
            state_robot = sampled
        return (state_robot, t_next, overruns,
                "feedback stale during stream", stale_ticks,
                stale_samples, stream_timing())

    state_robot = sampled
    for sub in range(1, steps + 1):
        if abort_check():
            return (
                state_robot, t_next, overruns, "aborted", stale_ticks,
                stale_samples, stream_timing())
        alpha = sub / steps
        q_cmd = q_to if sub == steps else q_from + (q_to - q_from) * alpha
        sampler.set_commanded(q_cmd)
        q_cmd_deg = (q_cmd * RAD2DEG).tolist()
        diag = {
            **pre_diag,
            "substep": sub,
            "inner_steps": steps,
        }
        if write_target:
            op_t = time.monotonic()
            try:
                bus.write_all(q_cmd_deg, speed=write_speed, acc=write_acc)
            except Exception as e:
                diag["write_error"] = repr(e)
                last_diag = diag
                return (
                    state_robot, t_next, overruns,
                    f"stream write failed: {e}", stale_ticks,
                    stale_samples, stream_timing())
            write_s += time.monotonic() - op_t

        t_next += inner_dt
        lag = time.monotonic() - t_next
        if lag > 0:
            overruns += 1
            diag["overrun_lag_ms"] = round(float(lag) * 1000.0, 3)
            lag_s = max(lag_s, float(lag))
            t_next = time.monotonic()
        else:
            time.sleep(-lag)
        last_diag = diag

    diag = dict(last_diag or {})
    delivered_timing = dict(getattr(state_robot, "timing", {}) or {})
    delivered_timing["async_age_ms"] = diag.get("async_age_ms")
    delivered_timing["stream_diag"] = _json_safe(diag)
    state_robot = replace(state_robot, timing=delivered_timing)
    return state_robot, t_next, overruns, "", 0, 0, stream_timing()



def _set_weight_bearing_torque(bus) -> None:
    """Best-effort full torque limit + torque-enable for RL body support."""
    if bus is None:
        return
    try:
        from feetech_bus import joint_to_servo_id as _sid_for_joint
    except Exception:  # pragma: no cover - deployed buses use feetech_bus
        _sid_for_joint = lambda j: j + 2
    pkt = getattr(bus, "pkt", None)
    if pkt is not None:
        for joint in range(N_JOINTS):
            try:
                pkt.write2ByteTxRx(
                    _sid_for_joint(joint), ADDR_TORQUE_LIMIT,
                    RL_HOLD_TORQUE_LIMIT)
            except Exception:
                pass
    try:
        bus.enable_all_torque(True)
    except Exception:
        pass


PREFLIGHT_MAX_TILT_DEG = 12.0
# Start-pose gates (max per-joint |delta| from the expected pose).
STAND_START_TOL_DEG = 30.0   # near flat belly pose (logical zero-ish)
LOWER_START_TOL_DEG = 25.0   # near the sim-default walk-ready stance

# Walk mode (exported obs 72/74/93 policies). The current repo default is
# the full-mesh all-heading MLP walk policy; the old dep-vref obs-72
# deployment-contract policy remains selectable as a conservative fallback.
# Still an operator-supervised experiment, tightly bounded:
# - starts from the sim-default walk-ready stance. Stand Up owns the
#   STEP -> walk-start settle; Start Driving never hides it.
# - command ramps 0 -> v over 1 s after a 1 s settle (training profile),
#   holds, then ramps back to 0 for the last second and HOLDS the pose;
# - speed clamped to the trained band; duration clamped to 20 s;
# - the 4 base walk obs dims are [vx_ref, vy_ref, vx_meas, vy_meas]/0.15,
#   with meas := ref exactly as in training (contract-exact);
# - obs-72 legacy policies get full-circle headings via the rot-60
#   exact-equivariance canonicalizer; obs-74/93 policies train all headings
#   directly and run naked.
WALK_VEL_SCALE = 0.15
WALK_YAW_SCALE = 0.5         # sim walk_task.WZ_SCALE
WALK_OBS_DIMS = (72, 74, 93)
WALK_PHASE_OBS_DIMS = (74, 93)
WALK_SPEED_MIN = 0.05        # fallback for legacy dep-vref policy exports
WALK_SPEED_MAX = 0.06        # fallback trained command band for old exports
WALK_HOLD_S = 1.0
WALK_RAMP_S = 1.0
WALK_MAX_TOTAL_S = 20.0
WALK_START_TOL_DEG = 25.0    # near the sim-default walk-ready stance
WALK_STEP_START_TOL_DEG = 35.0  # explicit compatibility hook only
DRIVE_HOLD_REFRESH_S = 0.25     # low-rate active refresh for joint-hold
RL_HOLD_TORQUE_LIMIT = 1000     # weight-bearing hold torque limit
ADDR_TORQUE_LIMIT = 48          # STS3215 SRAM max torque/current register
DRIVE_START_REFRESH_S = 0.45    # re-hold sim walk start through drive arming
DRIVE_START_REFRESH_SPEED = 260
DRIVE_START_REFRESH_ACC = 35
DRIVE_START_DRIFT_TOL_DEG = 8.0  # refuse instead of latching a sagged pose
# Walk-mode relative-tilt trip. A WORKING gait rocks +-10-20 deg in roll
# and pitch (operator-measured, scripted gait, 08-09 night); the config's
# 10 deg trip would terminate exactly the weight transfer a real gait
# needs. Walk-mode arms train AND deploy with a 25 deg envelope
# (cw-dep-vref1-r1: --cfg-set safety.max_roll_deg=25 / max_pitch_deg=25).
# Stand/lower keep the config's 10 deg trip — the stance champion
# (stance_dr10) trained with it, and its episodes should sit at +-1 deg.
WALK_MAX_TILT_DEG = 25.0
TAIL_FALL_TILT_DEG = 35.0
TAIL_FALL_RECOVERY_DEG = 25.0
TAIL_FALL_RECOVERY_SAMPLES = 3

# Chirality selection (turn= on walk moves). The naked champion drifts
# LEFT (+wz, probe_mirror_turn 08-11); the mirrored policy drifts right
# at the same rate. If a future champion drifts right, flip this sign —
# the selector and the left/right mapping both key off it.
NAKED_DRIFT_SIGN = +1
# Heading-hold bang-bang hysteresis: the sim probe's 4 deg. Below it
# the selector keeps the current chirality, so it cannot chatter.
TURN_HYST_RAD = math.radians(4.0)


class ChiralitySelector:
    """naked/mirror selection for a walk episode (TURN.md deploy port).

    turn="left"/"right": constant chirality — the one whose drift turns
    the commanded way. turn="hold": bang-bang on the accumulated
    heading (integrated gyro z, rad) with TURN_HYST_RAD hysteresis —
    veered too far one way -> run the chirality that drifts back.
    Mirrors probe_mirror_turn.rollout's selector exactly; locked by
    tests/test_mirror_runner.py.
    """

    def __init__(self, turn: str, drift_sign: int = NAKED_DRIFT_SIGN):
        assert turn in ("left", "right", "hold")
        self.turn = turn
        self.drift_sign = +1 if drift_sign >= 0 else -1
        left = "naked" if self.drift_sign > 0 else "mirror"
        right = "mirror" if self.drift_sign > 0 else "naked"
        self.active = {"left": left, "right": right,
                       "hold": "naked"}[turn]
        self.switches = 0
        self.heading = 0.0

    def update(self, gyro_z: float, dt: float) -> str:
        """Integrate heading, return the chirality for this tick."""
        self.heading += float(gyro_z) * dt
        if self.turn != "hold":
            return self.active
        want = self.active
        if self.heading > TURN_HYST_RAD:
            want = "mirror" if self.drift_sign > 0 else "naked"
        elif self.heading < -TURN_HYST_RAD:
            want = "naked" if self.drift_sign > 0 else "mirror"
        if want != self.active:
            self.active = want
            self.switches += 1
        return self.active

# Drive session (MuJoCo-viewer-style held-key driving, operator 08-11).
# The browser holds arrow keys -> POST /api/rl/drive/cmd heartbeats carry
# the live (vx, vy); release -> (0, 0) -> the hold path. The loop NEVER
# trusts a stale command: refs decay to zero unless a heartbeat younger
# than DRIVE_CMD_TIMEOUT_S says otherwise, so a closed tab / dropped
# WiFi degrades to "stand still and hold", not "keep walking". With no
# learned hold policy installed, "hold" is a direct joint hold of the last
# safe commanded pose. It must not run the walk policy at zero command:
# several good walking policies were never trained to be still at vx=vy=0.
DRIVE_CMD_TIMEOUT_S = 0.6    # heartbeats at ~5 Hz; 3 misses = stop
DRIVE_IDLE_END_S = 120.0     # no heartbeat at all -> end session (hold)
DRIVE_MAX_SESSION_S = 300.0  # hard cap per session (decel + hold)
DRIVE_HOLD_SWITCH_S = 1.5    # zero-cmd dwell before flipping to the
                             # hold model (quick taps stay on walk)
DRIVE_WALK_ENGAGE_S = 0.0    # first real held direction engages gait now
DRIVE_WALK_ACTION_RAMP_S = 1.5  # blend first learned targets from stance
DRIVE_STREAM_STALE_TICKS = 10  # tolerate ~100 ms snapshot gaps at 100 Hz
DRIVE_MOVE_EPS_MPS = 1e-4
DRIVE_YAW_EPS_RAD_S = 1e-4

# Live body-height nudges (gamepad D-pad up/down, operator 08-25). Only a
# LEARNED obs-68 stance hold policy tracks goal height refs, so the drive
# session honors dh only while HOLDING with one assigned (role "hold");
# the built-in joint hold and walk-as-hold policies ignore it. The ref
# integrates at DRIVE_HEIGHT_RATE_MPS — inside the trained stand/lower
# ramp rates (50 mm / 4 s rise = 12.5 mm/s, 45 mm / 5 s lower = 9 mm/s) —
# and clamps to the trained envelope from a plant start (goal config:
# lower target -45 mm, raise canary +10..30 mm). Walk champions trained
# at height_ref 0, so a move command first ramps the height back to the
# walk anchor and the gait engages only once |ref| < DRIVE_HEIGHT_EPS_M.
DRIVE_HEIGHT_RATE_MPS = 0.010
DRIVE_HEIGHT_MIN_M = -0.045
DRIVE_HEIGHT_MAX_M = 0.030
DRIVE_HEIGHT_EPS_M = 0.003


def _policy_walk_speed_band(policy: "NumpyPolicy") -> tuple[float, float]:
    """Policy-specific nonzero command band, with legacy fallback."""
    meta = policy.meta or {}
    lo = _positive_float(meta.get("walk_speed_min_m_s"), WALK_SPEED_MIN)
    hi = _positive_float(meta.get("walk_speed_max_m_s"), WALK_SPEED_MAX)
    if hi < lo:
        hi = lo
    return lo, hi


def _drive_clamp_translation(vx: float, vy: float,
                             speed_min: float = WALK_SPEED_MIN,
                             speed_max: float = WALK_SPEED_MAX,
                             ) -> tuple[float, float]:
    """Clamp nonzero hardware-drive translation into the trained band."""
    spd = math.hypot(vx, vy)
    if spd <= DRIVE_MOVE_EPS_MPS:
        return 0.0, 0.0
    lo = _positive_float(speed_min, WALK_SPEED_MIN)
    hi = max(lo, _positive_float(speed_max, WALK_SPEED_MAX))
    want = max(lo, min(hi, spd))
    s = want / spd
    return vx * s, vy * s


def _drive_command_is_moving(vx_target: float, vy_target: float,
                             wz_target: float, walk_obs: int = 72) -> bool:
    """Whether the live drive session should engage the walk policy."""
    if math.hypot(vx_target, vy_target) > DRIVE_MOVE_EPS_MPS:
        return True
    # Only AMP/yaw-command policies understand yaw-only drive. Legacy obs-72
    # policies ignore wz, so yaw-only at zero translation must stay in hold.
    return walk_obs == 93 and abs(wz_target) > DRIVE_YAW_EPS_RAD_S


def _drive_zero_dwell(active: str, moving_requested: bool,
                      zero_since: float | None,
                      t: float) -> tuple[bool, float | None]:
    """Keep a just-walking robot inside the gait through brief neutral input."""
    if moving_requested or active != "walk":
        return False, None
    if zero_since is None:
        zero_since = t
    return (t - zero_since) < DRIVE_HOLD_SWITCH_S, zero_since


def _drive_uses_learned_policy(active: str, hold_policy) -> bool:
    """False for the built-in neutral joint hold fallback."""
    return active == "walk" or hold_policy is not None


def _drive_should_run_learned_policy(active: str, hold_policy, *,
                                     walk_has_engaged: bool) -> bool:
    """Choose whether this tick should execute a neural policy.

    A learned hold model is useful after an actual gait handoff, but running
    it from tick zero makes a no-command drive session look like a broken walk.
    Before the first real walk command, keep the robot on a quiet direct
    joint-hold target and let the UI report that it is waiting for input.
    """
    if active == "walk":
        return True
    if hold_policy is None:
        return False
    return bool(walk_has_engaged)


def _drive_timing_trip_reason(active: str, hold_policy, tick: int,
                              timing: PolicyTiming, late_s: float,
                              consecutive_late: int, *,
                              uses_policy: bool | None = None,
                              label: str = "drive") -> str | None:
    """Only persistent learned-policy timing misses make drive fatal.

    Hardware joystick drive shares one host UART with snapshot reads, so a
    single 10-20 ms scheduling bubble is observable but not an immediate
    reason to limp. State freshness/current/tilt gates cover safety; timing
    trips are reserved for sustained controller overload or a large stall.
    """
    if uses_policy is None:
        uses_policy = _drive_uses_learned_policy(active, hold_policy)
    if not uses_policy:
        return None
    if active == "walk" and tick < DRIVE_TIMING_STARTUP_GRACE_TICKS:
        return None
    if late_s <= _timing_late_grace(timing.policy_dt):
        return None
    if late_s >= DRIVE_TIMING_CRITICAL_LAG_S:
        return (f"{label} timing overrun: tick {tick} missed the "
                f"{timing.policy_hz:g} Hz deadline by "
                f"{late_s * 1000.0:.1f} ms")
    if (late_s >= DRIVE_TIMING_HARD_LAG_S
            and consecutive_late >= DRIVE_TIMING_HARD_LAG_CONSECUTIVE):
        return (f"{label} timing overrun: {consecutive_late} consecutive "
                f"hard misses of the {timing.policy_hz:g} Hz deadline "
                f"(latest {late_s * 1000.0:.1f} ms late)")
    if consecutive_late >= DRIVE_TIMING_MAX_CONSECUTIVE_LATE:
        return (f"{label} timing overrun: {consecutive_late} consecutive "
                f"ticks missed the {timing.policy_hz:g} Hz deadline")
    return None


class DriveCommand:
    """Thread-safe live command mailbox: HTTP handler -> drive loop.

    ``set()`` is called from web request threads (must never touch the
    bus); the 25 Hz loop reads with ``get()`` and publishes a UI
    snapshot via ``live``.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._vx = 0.0
        self._vy = 0.0
        self._wz = 0.0
        self._dh = 0.0
        # Counts as a heartbeat so the idle-end clock starts at session
        # birth instead of firing instantly (refs are zero until the
        # browser actually sends commands).
        self._t_cmd = time.monotonic()
        self._stop = False
        self._live: dict = {}

    def set(self, vx: float, vy: float, wz: float = 0.0,
            dh: float = 0.0) -> None:
        wz = max(-WALK_YAW_SCALE, min(WALK_YAW_SCALE, float(wz)))
        dh = max(-1.0, min(1.0, float(dh)))
        with self._lock:
            self._vx, self._vy, self._wz = float(vx), float(vy), float(wz)
            self._dh = dh
            self._t_cmd = time.monotonic()

    def request_stop(self) -> None:
        with self._lock:
            self._stop = True

    def get(self) -> tuple[float, float, float, float, float, bool]:
        """(vx, vy, wz, dh, seconds_since_heartbeat, stop_requested)."""
        with self._lock:
            return (self._vx, self._vy, self._wz, self._dh,
                    time.monotonic() - self._t_cmd, self._stop)

    @property
    def live(self) -> dict:
        with self._lock:
            return dict(self._live)

    def publish(self, snap: dict) -> None:
        with self._lock:
            self._live = snap

_CENTER_RAD = np.array([
    (AXIS_LIMITS_DEG[j % 3][0] + AXIS_LIMITS_DEG[j % 3][1]) * 0.5 * DEG2RAD
    for j in range(N_JOINTS)])
_HALF_RAD = np.array([
    (AXIS_LIMITS_DEG[j % 3][1] - AXIS_LIMITS_DEG[j % 3][0]) * 0.5 * DEG2RAD
    for j in range(N_JOINTS)])


class NumpyPolicy:
    """Deterministic SB3 MlpPolicy actor: tanh MLP + linear head."""

    def __init__(self, path: Path = WEIGHTS_PATH):
        d = json.loads(Path(path).read_text())
        self.meta = d["meta"]
        require_robot_abs_joint_frame(self.meta, source=str(path))
        self.W1 = np.array(d["W1"]); self.b1 = np.array(d["b1"])
        self.W2 = np.array(d["W2"]); self.b2 = np.array(d["b2"])
        self.Wo = np.array(d["Wout"]); self.bo = np.array(d["bout"])

    def act(self, obs: np.ndarray) -> np.ndarray:
        h = np.tanh(self.W1 @ obs + self.b1)
        h = np.tanh(self.W2 @ h + self.b2)
        return np.clip(self.Wo @ h + self.bo, -1.0, 1.0)


class _Rot60ModelShim:
    """Adapts NumpyPolicy.act to the SB3 ``predict()`` Rot60Policy calls.

    NumpyPolicy is deterministic; the flag is accepted and ignored.
    """

    def __init__(self, policy: NumpyPolicy):
        self._policy = policy

    def predict(self, obs, deterministic: bool = True, **_kw):
        return self._policy.act(np.asarray(obs, dtype=float)), None


def make_walk_canonicalizer(policy: NumpyPolicy, cfg: dict):
    """Rot-60 wrapper EXACTLY as the walk loop uses it (None if absent).

    Single source of truth: this wraps rl_move.sim.rot60.Rot60Policy
    itself (no ported copy to drift). It reads vx/vy_ref straight from
    obs indices 68:70 — the same contract the sim evals run — and keeps
    per-episode sector state with hysteresis + zero-command hold.
    tests/test_rot60_runner.py locks this path against rot60.py.
    """
    if not _ROT60_OK:
        return None
    ts = float(cfg_get(cfg, "obs", "tilt_scale", default=0.2))
    return Rot60Policy(_Rot60ModelShim(policy), tilt_scale=ts)


def make_walk_mirror(policy: NumpyPolicy, cfg: dict, *, rot60: bool):
    """Reflected stack for chirality selection (None if mirror absent).

    Mirror OUTERMOST: reflect the world's obs, run the SAME shipped
    stack (rot60 canonicalizer + policy — its own instance, so its
    sector hysteresis state never sees the other chirality's frames),
    reflect the action back. Wrapping outside rot60 keeps the
    composition correct for any heading: the reflected command selects
    the reflected sector by construction. numpy-only end to end.
    """
    if not _MIRROR_OK:
        return None
    inner = (make_walk_canonicalizer(policy, cfg) if rot60 and _ROT60_OK
             else _Rot60ModelShim(policy))
    return MirrorPolicy(inner, walk=True,
                        obs_dim=int(policy.meta.get("obs_dim", 72)))


def heading_in_trained_wedge(vx: float, vy: float,
                             wedge_deg: float = 30.0) -> bool:
    """True if the commanded heading is inside the trained +/-30 deg
    forward wedge (zero command counts as inside)."""
    if math.hypot(vx, vy) < 1e-6:
        return True
    return abs(math.degrees(math.atan2(vy, vx))) <= wedge_deg


def _height_ref(prof: dict, t: float) -> float:
    """Height reference at time t for a stand/lower goal profile:
    hold 0 for hold_s, ramp to target_m over ramp_s, then hold."""
    if t < prof["hold_s"]:
        return 0.0
    f = min(1.0, (t - prof["hold_s"]) / prof["ramp_s"])
    return f * prof["target_m"]


def _walk_vel_ref(t: float, total_s: float,
                  vx: float, vy: float) -> tuple[float, float]:
    """Training-shaped command: settle, 1 s ramp in, hold, 1 s ramp out."""
    if t < WALK_HOLD_S:
        f = 0.0
    elif t < WALK_HOLD_S + WALK_RAMP_S:
        f = (t - WALK_HOLD_S) / WALK_RAMP_S
    elif t > total_s - WALK_RAMP_S:
        f = max(0.0, (total_s - t) / WALK_RAMP_S)
    else:
        f = 1.0
    return f * vx, f * vy


def _walk_obs_tail(walk_obs: int, vx_r: float, vy_r: float, phase: float,
                   wz_r: float = 0.0) -> np.ndarray:
    """The deploy-side tail for sim walk observations."""
    tail = [vx_r / WALK_VEL_SCALE, vy_r / WALK_VEL_SCALE,
            vx_r / WALK_VEL_SCALE, vy_r / WALK_VEL_SCALE]
    if walk_obs in WALK_PHASE_OBS_DIMS:
        tail.extend([math.sin(phase), math.cos(phase)])
    if walk_obs == 93:
        tail.append(wz_r / WALK_YAW_SCALE)
        tail.extend([1.0] * N_JOINTS)
    return np.asarray(tail, dtype=np.float32)


def _walk_phase_runs(walk_obs: int, vx_r: float, vy_r: float,
                     wz_r: float = 0.0, *, phase_run_on_yaw: bool = False
                     ) -> bool:
    if walk_obs not in WALK_PHASE_OBS_DIMS:
        return False
    if math.hypot(vx_r, vy_r) > 1e-3:
        return True
    return phase_run_on_yaw and abs(wz_r) > 1e-3


def _json_safe(value):
    """Best-effort JSON conversion for numpy-heavy live-run diagnostics."""
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def _tail_tilt_summary(samples_deg) -> dict:
    """Classify a post-motion tilt excursion without trusting one peak.

    A real tip remains down.  The Uno IMU can instead report a large filtered
    jump for several samples and then snap back while the body never moved.
    Keep the raw peak for diagnosis, but clear the fall label only after three
    consecutive samples return inside the active walk safety envelope.  A
    late or persistent excursion remains a fall, including a one-sample spike
    at the end of the observation window.
    """
    values = [abs(float(value)) for value in samples_deg]
    peak = max(values, default=0.0)
    high_indices = [
        index for index, value in enumerate(values)
        if value > TAIL_FALL_TILT_DEG
    ]
    recovered = False
    if high_indices:
        after_last_high = values[high_indices[-1] + 1:]
        recovered = (
            len(after_last_high) >= TAIL_FALL_RECOVERY_SAMPLES
            and all(
                value <= TAIL_FALL_RECOVERY_DEG
                for value in after_last_high[-TAIL_FALL_RECOVERY_SAMPLES:]
            )
        )
    return {
        "tail_tilt_max_deg": round(peak, 1),
        "tail_tilt_end_deg": round(values[-1], 1) if values else None,
        "tail_tilt_high_samples": len(high_indices),
        "tail_tilt_recovered": recovered,
        "tail_fell": bool(high_indices and not recovered),
    }


def _state_debug(state, *, q_cmd_rad=None, target_robot=None) -> dict:
    if state is None:
        return {"state": None}
    timing = dict(getattr(state, "timing", {}) or {})
    q = np.asarray(state.joint_position, dtype=float)
    out = {
        "joint_frame": FRAME_ROBOT_ABS,
        "joint_contract": JOINT_CONTRACT,
        "bus_ok": bool(getattr(state, "bus_ok", False)),
        "imu_ok": bool(getattr(state, "imu_ok", False)),
        "roll_deg": round(float(state.imu_roll) * RAD2DEG, 2),
        "pitch_deg": round(float(state.imu_pitch) * RAD2DEG, 2),
        "gyro_dps": [round(float(x) * RAD2DEG, 2)
                     for x in np.asarray(state.imu_gyro, dtype=float)],
        "q_deg": [round(float(x) * RAD2DEG, 2) for x in q],
        "stale_feedback": bool(timing.get("stale_feedback")),
        "stale_ticks": timing.get("stale_ticks"),
        "fallback": timing.get("fallback"),
        "timing_ms": {
            "pos": round(float(timing.get("t_pos") or 0.0) * 1000.0, 2),
            "imu": round(float(timing.get("t_imu") or 0.0) * 1000.0, 2),
            "fb": round(float(timing.get("t_fb") or 0.0) * 1000.0, 2),
            "total": round(float(timing.get("t_total") or 0.0)
                           * 1000.0, 2),
            "full_feedback": bool(timing.get("full_feedback")),
        },
    }
    if timing.get("source") is not None:
        out["state_source"] = timing.get("source")
    if timing.get("snapshot_seq") is not None:
        out["snapshot_seq"] = timing.get("snapshot_seq")
    if timing.get("pos_age_ms") is not None:
        out["pos_age_ms"] = timing.get("pos_age_ms")
    if timing.get("imu_age_ms") is not None:
        out["imu_age_ms"] = timing.get("imu_age_ms")
    if timing.get("stale_diag") is not None:
        out["stale_diag"] = timing.get("stale_diag")
    if timing.get("stream_diag") is not None:
        out["stream_diag"] = timing.get("stream_diag")
    if q_cmd_rad is not None:
        cmd = np.asarray(q_cmd_rad, dtype=float)
        dq = np.abs(q - cmd) * RAD2DEG
        j = int(np.argmax(dq)) if len(dq) else 0
        out["cmd_err_max_deg"] = round(float(dq[j]) if len(dq) else 0.0, 2)
        out["cmd_err_joint"] = j
    if target_robot is not None:
        target = np.asarray(target_robot, dtype=float)
        dq = np.abs(q - target) * RAD2DEG
        j = int(np.argmax(dq)) if len(dq) else 0
        out["target_err_max_deg"] = round(float(dq[j]) if len(dq) else 0.0, 2)
        out["target_err_joint"] = j
    cur = getattr(state, "servo_current", None)
    if cur is not None:
        cur_arr = np.asarray(cur, dtype=float)
        j = int(np.argmax(np.abs(cur_arr))) if len(cur_arr) else 0
        out["current_peak_a"] = round(float(abs(cur_arr[j])), 3)
        out["current_peak_joint"] = j
    return out


class _RunDebug:
    """JSONL flight recorder for live RL attempts, including early failures."""

    def __init__(self, mode: str, context: dict | None = None):
        stamp = time.strftime("%Y%m%d_%H%M%S")
        d = _HERE / "logs"
        d.mkdir(exist_ok=True)
        self.mode = mode
        self.path = d / f"rl_{mode}_{stamp}_debug.jsonl"
        self.name = self.path.name
        self._t0 = time.monotonic()
        self._f = self.path.open("w")
        self._closed = False
        self.event("debug_start", context=context or {})

    def event(self, name: str, *, publish: bool = True,
              flush: bool = True, **data) -> None:
        if self._closed:
            return
        rec = {
            "event": name,
            "t_s": round(time.monotonic() - self._t0, 4),
            "mono": round(time.monotonic(), 6),
            "mode": self.mode,
        }
        rec.update(_json_safe(data))
        try:
            self._f.write(json.dumps(rec, separators=(",", ":")) + "\n")
            if flush:
                self._f.flush()
        except Exception:
            pass
        if not publish:
            return
        try:
            from event_log import emit
            emit("rl_debug", f"{self.mode}: {name}", src="rl_policy",
                 data={"debug_log": self.name, **_json_safe(data)})
        except Exception:
            pass

    def attach(self, result: dict) -> dict:
        result.setdefault("debug_log", self.name)
        return result

    def close(self, result: dict | None = None) -> None:
        if self._closed:
            return
        if result is not None:
            self.event("debug_end", result=result)
        self._closed = True
        try:
            self._f.close()
        except Exception:
            pass


def _finish_debug(debug: _RunDebug | None, result: dict) -> dict:
    if debug is not None:
        debug.attach(result)
        debug.close(result)
    return result


class _EpisodeLog:
    """Every RL episode leaves a full local trace in ``logs/``.

    ``rl_<mode>_<stamp>.csv``  — one row per policy-rate tick: attitude,
    gyro, goal refs, measured q (18), commanded q (18), raw action (18),
    per-servo current when full feedback is available, and runner timing.
    ``rl_<mode>_<stamp>_summary.json`` — params + final result.
    Start/end also land in events.jsonl (kind ``rl_episode``).
    Pull with receive_robot_logs.py / scp for offline analysis.
    """

    def __init__(self, mode: str, params: dict, obs_dim: int = 0,
                 debug: _RunDebug | None = None):
        stamp = time.strftime("%Y%m%d_%H%M%S")
        d = _HERE / "logs"
        d.mkdir(exist_ok=True)
        self.mode = mode
        self.params = params
        self.obs_dim = int(obs_dim)
        self.debug = debug
        self.csv_path = d / f"rl_{mode}_{stamp}.csv"
        self.sum_path = d / f"rl_{mode}_{stamp}_summary.json"
        self.started_iso = time.strftime("%Y-%m-%dT%H:%M:%S")
        self._started_mono = time.monotonic()
        self._n = 0
        self._f = self.csv_path.open("w", newline="")
        self._w = csv.writer(self._f)
        # ``phase`` and obs columns added 08-10 after the dep-tip1 fall
        # debug: the robot tipped AFTER "walk done" (episode ends
        # holding the last stance) with zero data past the last tick,
        # and without the obs vector there was no way to tell "policy
        # saw the roll and didn't act" from "obs pipeline fed it
        # garbage". phase=run rows carry everything; phase=tail rows
        # (post-episode, ~3 s at 10 Hz, no commands sent) carry
        # attitude/gyro/q/currents only. Logged obs lets the exact
        # policy be replayed offline: action mismatch = obs/weights
        # bug, action match = behavior/contact story.
        self._w.writerow(
            ["t_s", "phase", "roll_deg", "pitch_deg",
             "gyro_x_dps", "gyro_y_dps", "gyro_z_dps",
             "height_ref_mm", "vx_ref_mps", "vy_ref_mps", "max_cur_a"]
            + [f"q{j}_deg" for j in range(N_JOINTS)]
            + [f"cmd{j}_deg" for j in range(N_JOINTS)]
            + [f"act{j}" for j in range(N_JOINTS)]
            + [f"cur{j}_a" for j in range(N_JOINTS)]
            + [f"obs{k}" for k in range(self.obs_dim)]
            # appended LAST so all prior column indices stay stable for
            # existing offline parsers. Walk mode: rot-60 sector index
            # (obs columns hold the REAL-frame obs; replaying them
            # through make_walk_canonicalizer must reproduce act* —
            # the offline replay-parity contract).
            # "mirror": 1 when the mirrored chirality drove this tick
            # (turn= walk moves), 0 naked, "" no selector. Appended
            # after rot60_k for the same index-stability reason.
            + ["rot60_k", "mirror",
               "bus_ok", "imu_ok", "stale_feedback", "stale_ticks",
               "t_pos_ms", "t_imu_ms", "t_fb_ms", "t_total_ms",
               "service_ms", "obs_ms", "policy_ms", "safety_ms",
               "write_ms", "read_ms", "lag_ms",
               "q_cmd_err_max_deg", "q_cmd_err_joint", "action_abs_max",
               "mono_s", "wall_elapsed_s", "unix_s", "walk_engaged",
               "learned_policy_active", "state_age_ms", "position_age_ms",
               "imu_age_ms", "bus_write_due", "snapshot_seq"])
        try:
            from event_log import emit
            emit("rl_episode", f"{mode} started ({self.csv_path.name})",
                 src="rl_policy", data=params)
        except Exception:
            pass
        if self.debug is not None:
            self.debug.event("episode_csv_started",
                             csv=self.csv_path.name,
                             summary=self.sum_path.name,
                             params=params)

    def tick(self, t: float, state, action, q_cmd_rad, goal,
             vx_r: float, vy_r: float, max_cur: float,
             obs=None, phase: str = "run", rot60_k=None,
             mirror_on=None, runner_timing: dict | None = None,
             walk_engaged: bool = False, learned_policy_active: bool = False,
             bus_write_due: bool = False) -> None:
        cur = (state.servo_current.tolist()
               if state.servo_current is not None else [None] * N_JOINTS)
        timing = dict(getattr(state, "timing", {}) or {})
        now_mono = time.monotonic()
        host_age_ms = max(0.0, now_mono - state.timestamp) * 1000.0

        def sensor_age_ms(key: str):
            value = timing.get(key)
            if value is None:
                return ""
            value = float(value)
            return (round(host_age_ms + value, 3)
                    if math.isfinite(value) and value >= 0.0 else "")

        pos_age_ms = sensor_age_ms("pos_age_ms")
        imu_age_ms = sensor_age_ms("imu_age_ms")
        state_age_ms = round(max(
            [host_age_ms] + [age for age in (pos_age_ms, imu_age_ms)
                             if age != ""]), 3)
        obs_cols = ([round(float(o), 4) for o in obs]
                    if obs is not None else [""] * self.obs_dim)
        if q_cmd_rad is not None:
            q_err = np.abs(np.asarray(state.joint_position, dtype=float)
                           - np.asarray(q_cmd_rad, dtype=float)) * RAD2DEG
            q_err_j = int(np.argmax(q_err)) if len(q_err) else 0
            q_err_max = round(float(q_err[q_err_j]) if len(q_err) else 0.0, 2)
        else:
            q_err_j = ""
            q_err_max = ""
        act_abs = (round(float(np.max(np.abs(action))), 4)
                   if action is not None else "")
        def r_ms(key: str):
            if not runner_timing or runner_timing.get(key) is None:
                return ""
            return round(float(runner_timing[key]) * 1000.0, 3)

        self._w.writerow(
            [round(t, 3), phase,
             round(state.imu_roll * RAD2DEG, 2),
             round(state.imu_pitch * RAD2DEG, 2)]
            + [round(float(g) * RAD2DEG, 2) for g in state.imu_gyro]
            + [round(goal.height_ref * 1000, 1) if goal is not None
               else "",
               round(vx_r, 4), round(vy_r, 4), round(max_cur, 3)]
            + [round(float(q) * RAD2DEG, 2) for q in state.joint_position]
            + ([round(float(q) * RAD2DEG, 2) for q in q_cmd_rad]
               if q_cmd_rad is not None else [""] * N_JOINTS)
            + ([round(float(a), 4) for a in action]
               if action is not None else [""] * N_JOINTS)
            + ["" if c is None else round(float(c), 3) for c in cur]
            + obs_cols
            + ["" if rot60_k is None else int(rot60_k),
               "" if mirror_on is None else int(mirror_on),
               int(bool(getattr(state, "bus_ok", False))),
               int(bool(getattr(state, "imu_ok", False))),
               int(bool(timing.get("stale_feedback"))),
               timing.get("stale_ticks", ""),
               round(float(timing.get("t_pos") or 0.0) * 1000.0, 3),
               round(float(timing.get("t_imu") or 0.0) * 1000.0, 3),
               round(float(timing.get("t_fb") or 0.0) * 1000.0, 3),
               round(float(timing.get("t_total") or 0.0) * 1000.0, 3),
               r_ms("service_s"),
               r_ms("obs_s"),
               r_ms("policy_s"),
               r_ms("safety_s"),
               r_ms("write_s"),
               r_ms("read_s"),
               r_ms("lag_s"),
               q_err_max, q_err_j, act_abs,
               round(now_mono, 6), round(now_mono - self._started_mono, 6),
               round(time.time(), 6), int(walk_engaged),
               int(learned_policy_active), state_age_ms, pos_age_ms,
               imu_age_ms, int(bus_write_due), timing.get("snapshot_seq", "")])
        self._n += 1
        if self._n % 25 == 0:      # survive a mid-run kill: flush each ~1 s
            self._f.flush()

    def close(self, result: dict) -> str:
        try:
            self._f.close()
        except Exception:
            pass
        try:
            self.sum_path.write_text(json.dumps(
                {"started": self.started_iso, "csv": self.csv_path.name,
                 "debug_log": self.debug.name if self.debug else None,
                 "ticks_logged": self._n, "params": self.params,
                 "result": result}, indent=1))
        except Exception:
            pass
        try:
            from event_log import emit
            emit("rl_episode",
                 f"{self.mode} " + ("done" if result.get("ok")
                                    else f"FAILED: {result.get('error')}"),
                 src="rl_policy",
                 level="info" if result.get("ok") else "warn",
                 data={"csv": self.csv_path.name, **result})
        except Exception:
            pass
        return self.csv_path.name


def _read_q_deg(bus) -> tuple[np.ndarray | None, str]:
    vals: list[float | None] = [None] * N_JOINTS
    errors: list[str] = []
    try:
        pos = bus.read_all_positions()
    except Exception as e:
        pos = None
        errors.append(str(e))
    if isinstance(pos, dict):
        for j, v in pos.items():
            jj = int(j)
            if 0 <= jj < N_JOINTS:
                vals[jj] = float(v)
    for j in range(N_JOINTS):
        if vals[j] is not None:
            continue
        try:
            v = bus.read_position_deg(j)
        except Exception as e:
            errors.append(f"j{j}: {e}")
            v = None
        if v is not None:
            vals[j] = float(v)
    missing = [j for j, v in enumerate(vals) if v is None]
    if missing:
        suffix = f" ({'; '.join(errors[:3])})" if errors else ""
        return None, f"servo IDs not answering: joints {missing}{suffix}"
    return np.array([float(v) for v in vals], dtype=float), ""


def _step_stand_final_deg() -> np.ndarray | None:
    try:
        data = json.loads((_HERE / "standup_modes.json").read_text())
        q = data["modes"]["step"]["keyframes"][-1]["q_deg"]
        if len(q) != N_JOINTS:
            return None
        return np.asarray(q, dtype=float)
    except Exception:
        return None


def _expected_start_options_deg(
        mode: str, *, allow_step_stand: bool = False
        ) -> tuple[list[tuple[str, np.ndarray, float]] | None, str]:
    if mode == "stand":
        # Rise training starts belly-down at logical zero (legs straight
        # out). Partial curls were also trained, so the gate is loose.
        return [("logical_zero", np.zeros(N_JOINTS),
                 STAND_START_TOL_DEG)], ""
    # Lower and normal walk start from the simulator's normal walk reset pose,
    # not from plant_pose.json. The saved plant is a calibration artifact;
    # letting it redefine q_nom made the hardware drive into a too-low stance.
    options: list[tuple[str, np.ndarray, float]] = []
    try:
        from rl_walk_start import walk_start_pose_degrees
        options.append(("sim_walk_start",
                        np.asarray(walk_start_pose_degrees(), dtype=float),
                        WALK_START_TOL_DEG if mode == "walk"
                        else LOWER_START_TOL_DEG))
    except Exception as e:  # pragma: no cover
        return None, f"sim walk start unavailable: {e}"
    if mode == "walk" and allow_step_stand:
        step = _step_stand_final_deg()
        if step is not None:
            options.append(("step_stand", step, WALK_STEP_START_TOL_DEG))
    return options, ""


def preflight(bus, mode: str, *, allow_step_stand: bool = False
              ) -> tuple[bool, str, dict]:
    """All checks are read-only. Returns (ok, reason, details)."""
    q_deg, err = _read_q_deg(bus)
    if q_deg is None:
        return False, err, {}
    try:
        imu = bus.read_imu(apply_calib=True)
    except Exception:
        imu = None
    if not isinstance(imu, dict) or "ax_g" not in imu:
        return False, "IMU not answering", {}
    mag = math.sqrt(imu["ax_g"] ** 2 + imu["ay_g"] ** 2
                    + imu["az_g"] ** 2)
    if not 0.5 <= mag <= 1.5:
        # A dead/asleep MPU reads zeros; atan2(0,0)=0 would false-pass
        # the tilt gate. At rest |accel| must be ~1 g.
        return False, f"IMU reading implausible (|g|={mag:.2f})", {}
    roll = math.degrees(math.atan2(imu["ay_g"], imu["az_g"]))
    pitch = math.degrees(math.atan2(-imu["ax_g"],
                                    math.hypot(imu["ay_g"], imu["az_g"])))
    options, err = _expected_start_options_deg(
        mode, allow_step_stand=allow_step_stand)
    if options is None:
        return False, err, {}
    checks = []
    for name, exp, tol_i in options:
        dq_i = np.abs(q_deg - exp)
        checks.append((float(np.max(dq_i)), int(np.argmax(dq_i)),
                       name, float(tol_i), dq_i))
    best_delta, best_joint, best_name, best_tol, best_dq = min(
        checks, key=lambda x: x[0])
    details = {
        "roll_deg": round(roll, 1), "pitch_deg": round(pitch, 1),
        "max_pose_delta_deg": round(best_delta, 1),
        "pose_tol_deg": best_tol,
        "start_pose": best_name,
    }
    if mode in ("stand", "walk") and (abs(roll) > PREFLIGHT_MAX_TILT_DEG
                                      or abs(pitch) > PREFLIGHT_MAX_TILT_DEG):
        # Name the 08-11 failure mode when it is the likely cause: a
        # tipped body over a folded knee. safe_zero knows how to untrap
        # (low-torque fold) — pointing there beats a bare refusal that
        # scripts answer by retrying stand/walk against the pin.
        hint = ""
        try:
            from pinned_tip import classify_pinned_tip
            v = classify_pinned_tip([float(x) for x in q_deg], roll, pitch)
            details["pinned_tip"] = v
            if v.get("pinned"):
                hint = (" — pinned-leg tip suspected "
                        f"({', '.join(c['name'] for c in v['candidates'])});"
                        " run safe_zero, it untraps first")
        except Exception:
            pass
        return False, (f"tilt too high for start "
                       f"(roll {roll:+.1f} pitch {pitch:+.1f}){hint}"
                       ), details
    if best_delta > best_tol:
        worst = best_joint
        want = ("belly-down, legs straight out (logical zero)"
                if mode == "stand" else
                "an upright sim walk start (or STEP stand)"
                if allow_step_stand and mode == "walk"
                else "the sim walk-ready start")
        return False, (f"pose is not {want}: joint {worst} is "
                       f"{best_dq[worst]:.0f} deg from expected "
                       f"(tol {best_tol:.0f})"
                       ), details
    return True, "", details


def _preflight_start_target_deg(
        mode: str, details: dict, *,
        allow_step_stand: bool = False
        ) -> tuple[np.ndarray | None, str]:
    """Return the exact pose that the accepted preflight matched."""
    start_pose = str(details.get("start_pose") or "")
    options, err = _expected_start_options_deg(
        mode, allow_step_stand=allow_step_stand)
    if options is None:
        return None, err
    for name, expected, _tol in options:
        if name == start_pose:
            return expected.copy(), ""
    return None, f"preflight start pose {start_pose!r} no longer available"


def _max_pose_delta_deg(q_robot_rad: np.ndarray,
                        target_robot_rad: np.ndarray
                        ) -> tuple[float, int]:
    dq = np.abs((np.asarray(q_robot_rad, dtype=float)
                 - np.asarray(target_robot_rad, dtype=float)) * RAD2DEG)
    worst = int(np.argmax(dq)) if len(dq) else 0
    return float(dq[worst]) if len(dq) else 0.0, worst


def _direct_start_state(bus, target_robot: np.ndarray,
                        refresh: dict) -> RobotState | None:
    """Build a start RobotState from direct reads when stream snapshots stall."""
    q_deg, err = _read_q_deg(bus)
    if q_deg is None:
        refresh["fallback_error"] = err
        return None
    try:
        imu = bus.read_imu(apply_calib=True)
    except Exception as e:
        imu = None
        refresh["fallback_imu_error"] = str(e)
    imu_ok = isinstance(imu, dict) and "ax_g" in imu
    if imu_ok:
        ax = float(imu.get("ax_g", 0.0))
        ay = float(imu.get("ay_g", 0.0))
        az = float(imu.get("az_g", 0.0))
        roll = math.atan2(ay, az)
        pitch = math.atan2(-ax, math.hypot(ay, az))
        gyro = np.array([
            float(imu.get("gx_dps", 0.0)) * DEG2RAD,
            float(imu.get("gy_dps", 0.0)) * DEG2RAD,
            float(imu.get("gz_dps", 0.0)) * DEG2RAD,
        ], dtype=float)
        accel = np.array([ax * 9.80665, ay * 9.80665, az * 9.80665],
                         dtype=float)
    else:
        roll = pitch = 0.0
        gyro = np.zeros(3, dtype=float)
        accel = np.zeros(3, dtype=float)
    refresh["fallback"] = "direct_position_read"
    return RobotState(
        timestamp=time.monotonic(),
        joint_position=np.asarray(q_deg, dtype=float) * DEG2RAD,
        joint_velocity=np.zeros(N_JOINTS, dtype=float),
        imu_roll=float(roll),
        imu_pitch=float(pitch),
        imu_yaw=0.0,
        imu_gyro=gyro,
        imu_accel=accel,
        commanded_position=np.asarray(target_robot, dtype=float).copy(),
        bus_ok=True,
        imu_ok=bool(imu_ok),
        dt=0.0,
        timing={"fallback": "direct_position_read",
                "stale_feedback": True},
    )


def _refresh_verified_start_pose(
        bus, est: RobotStateEstimator, target_deg: np.ndarray, *,
        timing, write_speed: int, write_acc: int, abort_check,
        label: str, debug: _RunDebug | None = None
        ) -> tuple[object | None, dict, str]:
    """Actively re-hold the accepted start pose and refuse if it sags away."""
    target_deg = np.asarray(target_deg, dtype=float)
    target_robot = target_deg * DEG2RAD
    refresh = {
        "pose": label,
        "target_deg": [round(float(x), 2) for x in target_deg],
    }
    speed = min(int(write_speed), DRIVE_START_REFRESH_SPEED)
    acc = min(int(write_acc), DRIVE_START_REFRESH_ACC)
    state_robot = None
    if debug is not None:
        debug.event("start_refresh_begin", pose=label, speed=speed,
                    acc=acc, target_deg=target_deg.tolist(),
                    duration_s=DRIVE_START_REFRESH_S)
    try:
        est.set_commanded(target_robot)
        bus.write_all(target_deg.tolist(), speed=speed, acc=acc)
    except Exception as e:
        refresh["write_error"] = str(e)
        if debug is not None:
            debug.event("start_refresh_write_failed", error=str(e),
                        refresh=refresh)
        return None, refresh, f"start pose refresh failed: {e}"

    deadline = time.monotonic() + DRIVE_START_REFRESH_S
    snapshot_samples = 0
    stale_samples = 0
    while time.monotonic() < deadline:
        if abort_check():
            return state_robot, refresh, "aborted"
        time.sleep(min(float(timing.policy_dt),
                       max(0.0, deadline - time.monotonic())))
        try:
            sampled = est.update(want_full_feedback=False)
        except Exception:
            sampled = None
        if sampled is not None and sampled.bus_ok:
            state_robot = sampled
            snapshot_samples += 1
        else:
            stale_samples += 1

    try:
        sampled = est.update(want_full_feedback=True)
    except Exception:
        sampled = None
    if sampled is not None and sampled.bus_ok:
        state_robot = sampled
        snapshot_samples += 1
    else:
        stale_samples += 1
    refresh.update({
        "snapshot_samples": snapshot_samples,
        "stale_samples": stale_samples,
    })
    if state_robot is None or not state_robot.bus_ok:
        state_robot = _direct_start_state(bus, target_robot, refresh)
        if debug is not None:
            debug.event("start_refresh_fallback",
                        refresh=refresh,
                        state=_state_debug(state_robot,
                                           target_robot=target_robot))
    if state_robot is None or not state_robot.bus_ok:
        if debug is not None:
            debug.event("start_refresh_failed", refresh=refresh)
        return (state_robot, refresh,
                "feedback unavailable during start refresh")

    delta, joint = _max_pose_delta_deg(state_robot.joint_position,
                                       target_robot)
    refresh.update({
        "max_pose_delta_deg": round(delta, 1),
        "worst_joint": joint,
        "tol_deg": DRIVE_START_DRIFT_TOL_DEG,
        "speed": speed,
        "acc": acc,
    })
    if delta > DRIVE_START_DRIFT_TOL_DEG:
        # Leave the servos actively commanded to the plant. The bug we are
        # preventing is treating the sagged feedback pose as the new nominal.
        try:
            est.set_commanded(target_robot)
            bus.write_all(target_deg.tolist(), speed=speed, acc=acc)
        except Exception:
            pass
        if debug is not None:
            debug.event("start_refresh_drift_failed",
                        refresh=refresh,
                        state=_state_debug(state_robot,
                                           target_robot=target_robot))
        return (
            state_robot, refresh,
            f"start pose drifted {delta:.1f} deg from {label} "
            f"on joint {joint} during drive arming")
    if debug is not None:
        debug.event("start_refresh_ok", refresh=refresh,
                    state=_state_debug(state_robot,
                                       target_robot=target_robot))
    return state_robot, refresh, ""


def _run_policy_move_impl(drive, mode: str, *, on_progress=None,
                          abort_check=None, vx: float = 0.03,
                          vy: float = 0.0,
                          duration_s: float = 6.0, rot60: bool = True,
                          turn: str | None = None,
                          weights_path: Path | None = None,
                          tilt_trip_deg: float | None = None,
                          extra_hold_s: float = 0.0,
                          allow_step_stand_start: bool = False,
                          stand_handoff: bool = True) -> dict:
    """Blocking policy episode. Call from a worker thread.

    ``drive`` is web_drive's DriveController (bus + arm state).
    ``mode`` is "stand", "lower" or "walk". Walk extras: body-frame
    vx/vy (m/s, clamped to the trained band; ANY heading with the
    rot-60 canonicalizer, else the trained +/-30 deg wedge only) and
    duration_s. ``rot60=False`` runs the naked policy (A/B baseline
    for a hardware parity session) — wedge headings only.
    ``turn`` (walk only): None = today's naked path, bit-identical;
    "left"/"right" = constant-chirality arc turn (~2 deg/s, the
    gait's own drift steered by naked-vs-mirrored selection);
    "hold" = heading hold, alternating chirality on the integrated
    gyro-z heading (4 deg hysteresis). Zero training; sim-proven
    (probe_mirror_turn PASS 08-11). Requires rl_move/sim/mirror.py
    on the board or the request is refused up front.
    ``weights_path`` overrides the default slot file (role registry,
    bench_api.rl_roles); obs-dim checks still apply.
    ``tilt_trip_deg`` (stand/lower only, clamped 5..30): operator-
    requested aggressive-tip test envelope — the 08-12 bench trips at
    10.3 deg mid-curl left "would it have stood?" unanswered. Walk
    keeps its own 25 deg envelope.
    ``extra_hold_s`` (stand/lower only, clamped 0..15): extends the
    episode past the profile's total_s; the height ref simply holds
    the target, so the extension is a longer settled hold.
    ``stand_handoff`` (stand only): normal interactive learned stands
    finish once the trained ramp is done and tilt/current stay calm for
    a short window. Disable it for full-profile validation/soak runs.
    """
    assert mode in ("stand", "lower", "walk")
    if turn is not None and mode != "walk":
        return {"ok": False, "error": "turn= is walk-only"}
    if turn is not None and turn not in ("left", "right", "hold"):
        return {"ok": False,
                "error": f"bad turn {turn!r} (left / right / hold)"}
    on_progress = on_progress or (lambda p: None)
    abort_check = abort_check or (lambda: False)
    bus = drive.bus
    if bus is None or drive.dry_run:
        return {"ok": False, "error": "no bus"}

    cfg = load_config(str(_HERE.parent / "rl_move" / "config.yaml"))
    canon = None
    mirror = None
    selector = None
    if mode == "walk":
        wpath = weights_path or WALK_WEIGHTS_PATH
        policy = NumpyPolicy(wpath)
        walk_obs = policy.meta.get("obs_dim")
        if walk_obs not in WALK_OBS_DIMS:
            return {"ok": False,
                    "error": (f"{Path(wpath).name} is not a walk policy "
                              f"(obs {walk_obs} not 72/74/93)")}
        # obs 74 = walk + phase clock (cw-arch-noslipphase1 no-slip
        # line): the runner appends [sin, cos] of a clock that advances
        # at meta["phase_hz"] while a velocity is commanded — the exact
        # contract of the sim's goal.walk_phase_obs=1. That line trains
        # ALL headings (no wedge) and has no rot-60/mirror machinery,
        # so it always runs naked. phase_hz MUST come from the export
        # meta: the sim default (1.0 Hz) is NOT this line's clock
        # (0.1666667 Hz) and a wrong clock is a silently broken gait.
        phase_hz = 0.0
        if walk_obs in WALK_PHASE_OBS_DIMS:
            if "phase_hz" not in policy.meta:
                return {"ok": False,
                        "error": (f"{Path(wpath).name} is obs-{walk_obs} "
                                  "but has "
                                  "no phase_hz in meta — re-export with "
                                  "--extra-meta phase_hz=<trained hz>")}
            phase_hz = float(policy.meta["phase_hz"])
            if turn is not None and walk_obs != 93:
                return {"ok": False,
                        "error": ("turn= is not supported for phase-"
                                  "clock (obs 74) walk policies")}
        walk_speed_min, walk_speed_max = _policy_walk_speed_band(policy)
        vx, vy = _drive_clamp_translation(
            vx, vy, walk_speed_min, walk_speed_max)
        total_s = min(max(float(duration_s), 3.0), WALK_MAX_TOTAL_S)
        if rot60 and walk_obs == 72:
            canon = make_walk_canonicalizer(policy, cfg)
        if turn is not None and walk_obs == 93 and turn == "hold":
            return {"ok": False,
                    "error": "turn=hold is not supported for obs-93 yet"}
        if turn is not None and walk_obs != 93:
            mirror = make_walk_mirror(policy, cfg, rot60=rot60)
            if mirror is None:
                return {"ok": False,
                        "error": ("turn= requested but the mirror "
                                  "module is unavailable "
                                  "(rl_move/sim/mirror.py not "
                                  "deployed)")}
            selector = ChiralitySelector(turn)
        if (canon is None and walk_obs == 72
                and not heading_in_trained_wedge(vx, vy)):
            # Naked, the policy freezes/degenerates off-wedge (sim-
            # proven, rot60.py docstring) — refuse rather than wander.
            return {"ok": False,
                    "error": ("command heading outside the trained "
                              "+/-30 deg wedge and the rot-60 "
                              "canonicalizer is "
                              + ("disabled" if _ROT60_OK else
                                 "unavailable (rl_move/sim/rot60.py "
                                 "not deployed)"))}
    else:
        wpath = weights_path or WEIGHTS_PATH
        policy = NumpyPolicy(wpath)
        if policy.meta.get("obs_dim") != 68:
            return {"ok": False,
                    "error": (f"{Path(wpath).name} is not a stance/"
                              "goal policy (obs "
                              f"{policy.meta.get('obs_dim')} != 68)")}
        prof = policy_profile(policy, mode)
        total_s = float(prof["total_s"]) + min(
            max(float(extra_hold_s or 0.0), 0.0), 15.0)
    try:
        timing = _policy_timing(policy)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    try:
        joint_frame = policy_joint_frame(policy, cfg)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    write_speed, write_acc = _policy_bus_profile(policy, cfg)
    inner_steps, inner_hz, inner_dt = _inner_stream_plan(
        policy, cfg, timing.policy_hz)
    async_move = _policy_move_uses_async(mode, timing.policy_hz)
    move_write = (_drive_write_plan(policy, cfg, timing.policy_hz)
                  if async_move else None)
    debug = _RunDebug(mode, {
        "policy_path": str(wpath),
        "policy_name": policy.meta.get("name"),
        "obs_dim": policy.meta.get("obs_dim"),
        "joint_frame": joint_frame,
        "joint_contract": JOINT_CONTRACT,
        "timing": {
            "policy_hz": timing.policy_hz,
            "training_hz": timing.policy_hz,
            "trained_control_hz": timing.trained_control_hz,
            "runner_config_hz": timing.runner_config_hz,
            "adapted": timing.adapted,
            "inner_hz": inner_hz,
            "inner_steps": inner_steps,
            "transport": "async" if async_move else "direct",
            "bus_write_hz": (move_write.write_hz
                             if move_write is not None else inner_hz),
            "bus_write_every_ticks": (
                move_write.write_every_ticks
                if move_write is not None else 1),
        },
        "write_speed": write_speed,
        "write_acc": write_acc,
        "command": {"vx": vx, "vy": vy, "duration_s": duration_s,
                    "turn": turn, "rot60": rot60},
    })

    ok, reason, details = preflight(
        bus, mode,
        allow_step_stand=bool(allow_step_stand_start and mode == "walk"))
    debug.event("preflight", ok=ok, reason=reason, details=details)
    if not ok:
        return _finish_debug(
            debug, {"ok": False, "error": f"preflight: {reason}", **details})
    start_target_deg = None
    if mode == "walk":
        start_target_deg, start_err = _preflight_start_target_deg(
            mode, details,
            allow_step_stand=bool(allow_step_stand_start and mode == "walk"))
        if start_target_deg is None:
            return _finish_debug(
                debug, {"ok": False, "error": f"preflight: {start_err}",
                        **details})
        debug.event("start_target_selected",
                    start_pose=details.get("start_pose"),
                    target_deg=start_target_deg.tolist())

    if async_move:
        async_probe = _probe_async_transport(bus)
        details["async_transport_probe"] = async_probe
        debug.event("async_transport_prearm", **async_probe)
        if not async_probe["async_capable"]:
            return _finish_debug(
                debug, {"ok": False,
                        "error": ("async transport unavailable before arm: "
                                  + str(async_probe.get("error") or
                                        "freshness proof failed")),
                        "held_pose": True, "limped": False,
                        "preflight": details})

    def limp():
        try:
            bus.enable_all_torque(False)
        except Exception:
            try:
                drive._torque_all(False)
            except Exception:
                pass

    # --- arm: torque on, hold the PRESENT pose (never yank) ---
    with drive._lock:
        drive.mode = "demo"
        try:
            drive.gait.stop()
        except Exception:
            pass
        # The cached DriveController.armed flag can survive a UI stop or
        # controller restart while the servo torque state is actually off.
        # Force a fresh torque-enable before RL takes ownership; otherwise
        # the runner can log "hold" while the body physically sags.
        _set_weight_bearing_torque(bus)
        drive._torque_all(True)
        drive.armed = True
        drive.status = "rl policy armed"

    est = RobotStateEstimator(bus, cfg)
    safety = SafetyLayer(cfg)
    max_dq_deg, max_dq_explicit = _apply_policy_safety_timing(
        safety, policy, cfg, timing)
    if mode == "walk":
        # Match the walk policy's trained tilt envelope (see
        # WALK_MAX_TILT_DEG). The config's 10 deg stays for stand/lower.
        safety.max_roll = math.radians(WALK_MAX_TILT_DEG)
        safety.max_pitch = math.radians(WALK_MAX_TILT_DEG)
    elif tilt_trip_deg:
        # Operator aggressive-tip test envelope (see docstring). The
        # 35 deg fell detector and the current/temp trips stay as-is.
        t_deg = min(max(float(tilt_trip_deg), 5.0), 30.0)
        safety.max_roll = math.radians(t_deg)
        safety.max_pitch = math.radians(t_deg)
    tilt_trip_deg = round(math.degrees(safety.max_roll), 1)

    # Walk policies expect the simulator's normal walk-start frame. Do not let
    # a sag during arming become the new nominal pose.
    if mode == "walk" and start_target_deg is not None:
        state_robot, refresh, start_err = _refresh_verified_start_pose(
            bus, est, start_target_deg, timing=timing,
            write_speed=write_speed, write_acc=write_acc,
            abort_check=abort_check, label=str(details.get("start_pose")),
            debug=debug)
        details["start_refresh"] = refresh
        if start_err:
            return _finish_debug(
                debug, {"ok": False, "error": start_err, "held_pose": True,
                        "limped": False, "preflight": details})
        q_nom_robot = np.asarray(start_target_deg, dtype=float) * DEG2RAD
    else:
        # Stance/lower policies still use the exact pose they start from.
        state_robot = None
        for _ in range(5):
            state_robot = est.update(want_full_feedback=True)
            time.sleep(timing.policy_dt)
        if state_robot is None or not state_robot.bus_ok:
            limp()
            return {"ok": False,
                    "error": "feedback unavailable during settle"}
        q_nom_robot = state_robot.joint_position.copy()
    q_nom = q_nom_robot.copy()
    est.set_commanded(q_nom_robot)
    bus.write_all((q_nom_robot * RAD2DEG).tolist(), speed=write_speed,
                  acc=write_acc)
    last_q_robot_cmd = q_nom_robot.copy()
    est.reset_episode_filters()
    warmup_good = 0
    warmup_stale = 0
    for _ in range(3):
        try:
            sampled = est.update(want_full_feedback=False)
        except Exception:
            sampled = None
        if sampled is not None and sampled.bus_ok:
            state_robot = sampled
            warmup_good += 1
        else:
            warmup_stale += 1
        time.sleep(timing.policy_dt)
    if state_robot is None or not state_robot.bus_ok:
        warmup_refresh: dict = {}
        state_robot = _direct_start_state(bus, q_nom_robot, warmup_refresh)
        if state_robot is None:
            return _finish_debug(
                debug, {"ok": False,
                        "error": "feedback unavailable during start warmup",
                        "preflight": details,
                        "start_warmup": warmup_refresh})
        details["start_warmup_fallback"] = warmup_refresh
    if warmup_stale:
        details["start_warmup"] = {
            "snapshot_samples": warmup_good,
            "stale_samples": warmup_stale,
        }
    debug.event("start_warmup_done", state=_state_debug(state_robot),
                warmup=details.get("start_warmup"),
                fallback=details.get("start_warmup_fallback"))
    async_sampler: _AsyncSnapshotSampler | None = None
    async_sampler_last_stats: dict | None = None
    async_feedback_hz: float | None = None
    if async_move:
        async_feedback_hz = _apply_async_safety_feedback_timing(
            safety, cfg, DRIVE_ASYNC_SNAPSHOT_HZ)
        async_sampler = _AsyncSnapshotSampler(
            bus, cfg, initial_state=state_robot,
            hz=DRIVE_ASYNC_SNAPSHOT_HZ,
            max_age_s=DRIVE_ASYNC_STATE_MAX_AGE_S)
        async_sampler.set_commanded(last_q_robot_cmd)
        async_sampler.start()
        state_ready, ready_details, ready_err = _await_async_sampler_ready(
            async_sampler, abort_check, health_safety=safety)
        details["async_start"] = ready_details
        debug.event("move_async_snapshot_start", ok=not bool(ready_err),
                    error=ready_err or None,
                    hz=DRIVE_ASYNC_SNAPSHOT_HZ,
                    feedback_hz=async_feedback_hz,
                    max_age_ms=async_sampler.max_age_s * 1000.0,
                    details=ready_details,
                    state=_state_debug(state_ready))
        if ready_err:
            async_sampler_last_stats = async_sampler.stats()
            async_sampler.stop()
            async_sampler = None
            physical_trip = _async_readiness_requires_limp(ready_err)
            if physical_trip:
                limp()
            return _finish_debug(
                debug, {"ok": False, "error": ready_err,
                        "held_pose": not physical_trip,
                        "limped": physical_trip,
                        "preflight": details,
                        "async_snapshot": async_sampler_last_stats})
        state_robot = state_ready
    state = _state_for_policy_frame(state_robot, joint_frame)
    tilt_ref0 = (state.imu_roll, state.imu_pitch)
    safety.set_nominal(q_nom)
    safety.set_tilt_reference(*tilt_ref0)

    prev_action = np.zeros(N_JOINTS, dtype=float)
    vx_r = vy_r = 0.0
    if async_move:
        # Pay numpy allocation/BLAS and SafetyLayer cold-start costs while the
        # robot is still holding its verified start pose, before t_next starts.
        try:
            warm_goal = TaskGoal(
                roll_ref=0.0, pitch_ref=0.0,
                height_ref=_height_ref(prof, 0.0), unload_leg=None)
            warm_obs = build_obs(
                cfg, state, q_nom, prev_action, goal=warm_goal,
                tilt_ref=tilt_ref0)
            warm_action, bad = safety.validate_action(
                policy.act(warm_obs), n_act=N_JOINTS)
            if warm_action is None:
                raise ValueError(bad or "warmup action rejected")
            scratch_safety = SafetyLayer(cfg)
            _apply_policy_safety_timing(
                scratch_safety, policy, cfg, timing)
            _apply_async_safety_feedback_timing(
                scratch_safety, cfg, DRIVE_ASYNC_SNAPSHOT_HZ)
            scratch_safety.max_roll = safety.max_roll
            scratch_safety.max_pitch = safety.max_pitch
            scratch_safety.set_nominal(q_nom)
            scratch_safety.set_tilt_reference(*tilt_ref0)
            scratch_safety.filter(
                _CENTER_RAD + warm_action * _HALF_RAD,
                _state_for_async_safety(state), action=warm_action)
            debug.event("move_hot_path_warmup", publish=False,
                        obs_len=len(warm_obs), safety_filter=True)
        except Exception as e:
            debug.event("move_hot_path_warmup_failed", error=repr(e))
    n_ticks = int(round(total_s * timing.policy_hz))
    stand_handoff_enabled = (
        mode == "stand" and bool(stand_handoff)
        and float(extra_hold_s or 0.0) <= 0.0)
    stand_handoff_after_s = 0.0
    stand_handoff_ticks = 0
    stand_handoff_good = 0
    if stand_handoff_enabled:
        stand_handoff_after_s = (
            float(prof["hold_s"]) + float(prof["ramp_s"])
            + STAND_HANDOFF_SETTLE_S)
        stand_handoff_ticks = max(1, int(round(
            STAND_HANDOFF_STABLE_S * timing.policy_hz)))
    overruns = 0
    max_cur = 0.0
    tilt_rel_max = 0.0
    t_end = 0.0
    timing_stats = _TimingStats()
    consecutive_late = 0
    progress_every = max(1, int(round(timing.policy_hz / 5.0)))
    result: dict = {"ok": True, "mode": mode,
                    "training_hz": timing.policy_hz,
                    "policy_joint_frame": joint_frame,
                    "policy_joint_contract": JOINT_CONTRACT}
    last_good_stream_state = state_robot
    stale_stream_ticks = 0
    stale_stream_samples = 0
    max_stale_stream_ticks_seen = 0
    stale_stream_bursts = 0
    first_stale_at_s: float | None = None
    last_stale_at_s: float | None = None
    elog = _EpisodeLog(mode, obs_dim=int(policy.meta.get("obs_dim", 0)),
                       params={
        "mode": mode, "total_s": round(total_s, 1),
        "hz": timing.policy_hz,
        "policy_hz": timing.policy_hz,
        "training_hz": timing.policy_hz,
        "trained_control_hz": timing.trained_control_hz,
        "trained_control_hz_explicit": timing.trained_control_hz_explicit,
        "runner_config_hz": timing.runner_config_hz,
        "policy_rate_adapted": timing.adapted,
        "inner_hz": inner_hz, "inner_steps": inner_steps,
        "transport": "async" if async_move else "direct",
        "bus_write_hz": (move_write.write_hz
                         if move_write is not None else inner_hz),
        "bus_write_every_ticks": (
            move_write.write_every_ticks if move_write is not None else 1),
        "async_snapshot": ({
            "hz": DRIVE_ASYNC_SNAPSHOT_HZ,
            "feedback_hz": async_feedback_hz,
            "max_age_s": (async_sampler.max_age_s
                          if async_sampler is not None
                          else DRIVE_ASYNC_STATE_MAX_AGE_S),
            "ready": details.get("async_start"),
        } if async_move else None),
        "max_delta_q_deg": round(max_dq_deg, 4),
        "max_delta_q_deg_explicit": max_dq_explicit,
        "write_speed": write_speed, "write_acc": write_acc,
        "policy": dict(policy.meta),
        "policy_joint_frame": joint_frame,
        "policy_joint_contract": JOINT_CONTRACT,
        "q_nom_deg": [round(float(q) * RAD2DEG, 2) for q in q_nom],
        "tilt_ref_deg": [round(tilt_ref0[0] * RAD2DEG, 2),
                         round(tilt_ref0[1] * RAD2DEG, 2)],
        "tilt_trip_deg": tilt_trip_deg,
        "debug_log": debug.name,
        "preflight": details,
        **({"stand_handoff": {
            "enabled": True,
            "after_s": round(stand_handoff_after_s, 2),
            "stable_s": STAND_HANDOFF_STABLE_S,
            "max_tilt_deg": STAND_HANDOFF_MAX_TILT_DEG,
            "max_current_a": STAND_HANDOFF_MAX_CURRENT_A,
        }} if stand_handoff_enabled else {}),
        **({"vx": round(vx, 3), "vy": round(vy, 3),
            "rot60": canon is not None,
            **({"turn": turn} if turn else {})}
           if mode == "walk" else {}),
    }, debug=debug)
    t_next = time.monotonic()

    phase = 0.0        # walk phase clock (obs-74/93 policies only)
    phase_run_on_yaw = bool(float(policy.meta.get("walk_phase_run_on_yaw",
                                                  0.0)))
    for i in range(n_ticks):
        if abort_check():
            # Operator stop: HOLD pose (torque stays on); X still limps.
            result.update(ok=False, error="aborted",
                          held_pose=True, ticks=i)
            break
        t = i * timing.policy_dt
        tick_t0 = time.monotonic()
        stage_t = tick_t0
        if mode == "walk":
            goal = TaskGoal(roll_ref=0.0, pitch_ref=0.0,
                            height_ref=0.0, unload_leg=None)
            vx_r, vy_r = _walk_vel_ref(t, total_s, vx, vy)
            wz_r = 0.0
            if walk_obs == 93 and turn in ("left", "right"):
                turn_sign = 1.0 if turn == "left" else -1.0
                wz_r = turn_sign * float(policy.meta.get(
                    "walk_yaw_max_rad_s", WALK_YAW_SCALE))
            obs = build_obs(cfg, state, q_nom, prev_action, goal=goal,
                            tilt_ref=tilt_ref0)
            obs = np.concatenate(
                [obs, _walk_obs_tail(walk_obs, vx_r, vy_r, phase, wz_r)]
            ).astype(np.float32)
            if _walk_phase_runs(walk_obs, vx_r, vy_r, wz_r,
                                phase_run_on_yaw=phase_run_on_yaw):
                phase = (phase + 2.0 * math.pi * phase_hz
                         * timing.policy_dt) \
                    % (2.0 * math.pi)
        else:
            goal = TaskGoal(roll_ref=0.0, pitch_ref=0.0,
                            height_ref=_height_ref(prof, t),
                            unload_leg=None)
            obs = build_obs(cfg, state, q_nom, prev_action, goal=goal,
                            tilt_ref=tilt_ref0)
        obs_s = time.monotonic() - stage_t
        stage_t = time.monotonic()
        chirality = None
        if selector is not None:
            # Chirality selection (turn=): integrate the heading from
            # gyro z and pick naked vs mirrored for THIS tick. Each
            # chirality runs its own rot60 instance (sector state
            # never sees the other's frames); obs/prev_action/logs
            # stay REAL-frame for both — the wrappers permute
            # internally.
            chirality = selector.update(
                float(state.imu_gyro[2]), timing.policy_dt)
        if chirality == "mirror":
            raw_act, _ = mirror.predict(obs)
        elif canon is not None:
            # Canonicalize the REAL-frame obs into the trained wedge,
            # un-relabel the action back to real legs (rot60.py).
            # prev_action / logs stay REAL-frame — same contract as
            # the sim evals (Rot60Policy permutes them internally).
            raw_act, _ = canon.predict(obs)
        else:
            raw_act = policy.act(obs)
        policy_s = time.monotonic() - stage_t
        stage_t = time.monotonic()
        action, bad = safety.validate_action(raw_act, n_act=N_JOINTS)
        if action is None:
            limp()
            debug.event("bad_action", tick=i, t_s=t, error=bad,
                        obs_len=len(obs), state=_state_debug(state))
            result.update(ok=False, error=f"bad action: {bad}", ticks=i)
            break
        q_prop = _CENTER_RAD + action * _HALF_RAD
        q_safe, status = safety.filter(
            q_prop, _state_for_async_safety(state), action=action)
        q_robot_cmd = q_safe.copy()
        safety_s = time.monotonic() - stage_t
        if status.terminate:
            limp()
            debug.event("safety_trip", tick=i, t_s=t,
                        reason=status.reason, detail=status.detail,
                        held=status.held, state=_state_debug(state),
                        q_prop_deg=[round(float(x) * RAD2DEG, 2)
                                    for x in q_prop],
                        q_safe_deg=[round(float(x) * RAD2DEG, 2)
                                    for x in q_safe])
            result.update(ok=False, error=f"safety trip: {status.reason}"
                          + (f" ({status.detail})" if status.detail else ""),
                          limped=True, ticks=i)
            break
        prev_stale_ticks = stale_stream_ticks
        if async_sampler is not None and move_write is not None:
            write_due = (i == 0
                         or i % move_write.write_every_ticks == 0)
            (state_robot, t_next, extra_overruns, stream_err,
             stale_stream_ticks, stale_added, stream_timing) = (
                _stream_target_async(
                    bus, async_sampler, last_q_robot_cmd, q_robot_cmd,
                    # Exactly one possible bus write per policy tick; the
                    # divisor, not inner interpolation, owns this transport.
                    t_next=t_next, inner_steps=1,
                    inner_dt=timing.policy_dt,
                    write_speed=write_speed, write_acc=write_acc,
                    abort_check=abort_check,
                    last_good_state=last_good_stream_state,
                    stale_ticks=stale_stream_ticks,
                    max_stale_ticks=DRIVE_STREAM_STALE_TICKS,
                    write_target=write_due))
        else:
            (state_robot, t_next, extra_overruns, stream_err,
             stale_stream_ticks, stale_added, stream_timing) = _stream_target(
                bus, est, last_q_robot_cmd, q_robot_cmd,
                t_next=t_next, inner_steps=inner_steps, inner_dt=inner_dt,
                write_speed=write_speed, write_acc=write_acc,
                abort_check=abort_check,
                last_good_state=last_good_stream_state,
                stale_ticks=stale_stream_ticks,
                max_stale_ticks=DRIVE_STREAM_STALE_TICKS)
        overruns += extra_overruns
        stale_stream_samples += stale_added
        if stale_added:
            burst_peak = max(prev_stale_ticks + stale_added,
                             stale_stream_ticks)
            max_stale_stream_ticks_seen = max(
                max_stale_stream_ticks_seen, burst_peak)
            last_stale_at_s = t
            if first_stale_at_s is None:
                first_stale_at_s = t
            if prev_stale_ticks == 0:
                stale_stream_bursts += 1
                debug.event("stream_feedback_stale_begin", tick=i, t_s=t,
                            stale_added=stale_added,
                            stale_ticks=stale_stream_ticks,
                            state=_state_debug(state_robot,
                                               q_cmd_rad=q_robot_cmd))
            if stale_stream_ticks == 0:
                debug.event("stream_feedback_recovered", tick=i, t_s=t,
                            previous_stale_ticks=burst_peak,
                            state=_state_debug(state_robot,
                                               q_cmd_rad=q_robot_cmd))
        elif prev_stale_ticks > 0 and stale_stream_ticks == 0:
            debug.event("stream_feedback_recovered", tick=i, t_s=t,
                        previous_stale_ticks=prev_stale_ticks,
                        state=_state_debug(state_robot,
                                           q_cmd_rad=q_robot_cmd))
        if stream_err:
            debug.event("stream_error", tick=i, t_s=t, error=stream_err,
                        stale_ticks=stale_stream_ticks,
                        stale_samples=stale_stream_samples,
                        state=_state_debug(state_robot,
                                           q_cmd_rad=q_robot_cmd))
            if stream_err == "aborted":
                result.update(ok=False, error="aborted",
                              held_pose=True, ticks=i)
            elif (async_move
                  and stream_err == "feedback stale during stream"):
                # A sampler/framework freshness stop is not evidence of a
                # physical tip or jam.  Leave the last verified target held;
                # do not collapse a weight-bearing stance by cutting torque.
                result.update(ok=False, error=stream_err,
                              held_pose=True, limped=False, ticks=i)
            else:
                limp()
                result.update(ok=False, error=stream_err,
                              limped=True, ticks=i)
            break
        last_q_robot_cmd = q_robot_cmd.copy()
        prev_action = action.copy()
        if not _stream_state_is_stale(state_robot):
            last_good_stream_state = state_robot
        state = _state_for_policy_frame(state_robot, joint_frame)
        cur_now = None
        if state.servo_current is not None:
            cur_now = float(np.max(np.abs(state.servo_current)))
            max_cur = max(max_cur, cur_now)
        tilt_now = max(
            abs(state.imu_roll - tilt_ref0[0]) * RAD2DEG,
            abs(state.imu_pitch - tilt_ref0[1]) * RAD2DEG)
        tilt_rel_max = max(tilt_rel_max, tilt_now)
        t_end = t + timing.policy_dt
        service_s = time.monotonic() - tick_t0
        lag_s = float(stream_timing.get("lag_s") or 0.0)
        late_s = max(lag_s, service_s - timing.policy_dt)
        if late_s > _timing_late_grace(timing.policy_dt):
            consecutive_late += 1
        else:
            consecutive_late = 0
        runner_timing = {
            "service_s": service_s,
            "obs_s": obs_s,
            "policy_s": policy_s,
            "safety_s": safety_s,
            "write_s": float(stream_timing.get("write_s") or 0.0),
            "read_s": float(stream_timing.get("read_s") or 0.0),
            "lag_s": lag_s,
        }
        timing_stats.add(runner_timing)
        timing_error = (
            _drive_timing_trip_reason(
                mode, policy, i, timing, late_s, consecutive_late,
                uses_policy=True, label=mode)
            if async_move else
            _timing_trip_reason(
                mode, i, timing.policy_hz, late_s, consecutive_late))
        elog.tick(t, state, action, q_safe, goal, vx_r, vy_r, max_cur,
                  obs=obs,
                  rot60_k=(canon.k if canon is not None else None),
                  mirror_on=(None if chirality is None
                             else chirality == "mirror"),
                  runner_timing=runner_timing,
                  walk_engaged=(mode == "walk" and
                                (abs(vx_r) + abs(vy_r) + abs(wz_r) > 1e-4)),
                  learned_policy_active=True,
                  bus_write_due=(move_write is None or
                                 i % move_write.write_every_ticks == 0))
        if timing_error:
            # Timing is a controller-health fault, not evidence of a physical
            # tip, jam, or hot motor.  Preserve the last safe commanded pose
            # so an isolated scheduler miss cannot collapse a standing robot.
            # Physical safety trips above still limp immediately.
            result.update(ok=False, error=timing_error, held_pose=True,
                          limped=False, ticks=i,
                          timing=timing_stats.summary())
            on_progress({
                "level": "error", "error": timing_error,
                "msg": timing_error,
                "t_s": round(t, 2), "overruns": overruns,
                "timing_ms": {k[:-2]: round(v * 1000.0, 3)
                              for k, v in runner_timing.items()},
            })
            break
        if stand_handoff_enabled and t_end >= stand_handoff_after_s:
            if (tilt_now <= STAND_HANDOFF_MAX_TILT_DEG
                    and (cur_now is None
                         or cur_now <= STAND_HANDOFF_MAX_CURRENT_A)):
                stand_handoff_good += 1
            else:
                stand_handoff_good = 0
            if stand_handoff_good >= stand_handoff_ticks:
                result.update(
                    ticks=i + 1,
                    early_handoff=True,
                    handoff_t_s=round(t_end, 2),
                    profile_total_s=round(total_s, 1),
                    handoff_stable_s=STAND_HANDOFF_STABLE_S,
                    handoff_tilt_rel_deg=round(tilt_now, 1),
                    handoff_current_a=(round(cur_now, 2)
                                       if cur_now is not None else None),
                )
                on_progress({
                    "msg": (f"stand ready for walk t={t_end:4.1f}s "
                            f"tilt={tilt_now:.1f}deg "
                            f"maxI={max_cur:.2f}A"),
                    "t_s": round(t_end, 2),
                    "phase": "handoff",
                    "early_handoff": True,
                    "height_ref_mm": round(goal.height_ref * 1000, 1),
                    "roll_deg": round((state.imu_roll - tilt_ref0[0])
                                      * RAD2DEG, 2),
                    "pitch_deg": round((state.imu_pitch - tilt_ref0[1])
                                       * RAD2DEG, 2),
                    "max_current_a": round(max_cur, 2),
                    "overruns": overruns,
                })
                break
        if i % progress_every == 0:
            if mode == "walk":
                progress_phase = ("settle" if t < WALK_HOLD_S else
                                  "decel" if t > total_s - WALK_RAMP_S else
                                  "ramp" if t < WALK_HOLD_S + WALK_RAMP_S
                                  else "walk")
                ref_txt = (f"v=({vx_r * 1000:+.0f},{vy_r * 1000:+.0f})mm/s")
                if canon is not None and canon.k:
                    ref_txt += f" sec={canon.k:+d}"
                if selector is not None:
                    ref_txt += (f" {selector.active[:3]}"
                                f" hd={math.degrees(selector.heading):+.0f}")
            else:
                progress_phase = (
                    "curl" if mode == "stand" and t < prof["hold_s"]
                    else "ramp" if t < prof["hold_s"] + prof["ramp_s"]
                    else "hold")
                ref_txt = f"href={goal.height_ref * 1000:+.0f}mm"
            on_progress({
                "msg": (f"{mode} {progress_phase} t={t:4.1f}s "
                        f"{ref_txt} "
                        f"maxI={max_cur:.2f}A"),
                "t_s": round(t, 2), "phase": progress_phase,
                "height_ref_mm": round(goal.height_ref * 1000, 1),
                "roll_deg": round((state.imu_roll - tilt_ref0[0])
                                  * RAD2DEG, 2),
                "pitch_deg": round((state.imu_pitch - tilt_ref0[1])
                                   * RAD2DEG, 2),
                "max_current_a": round(max_cur, 2),
                "stale_stream_ticks": stale_stream_ticks,
                "stale_stream_samples": stale_stream_samples,
                "overruns": overruns,
                "timing_ms": {
                    "service": round(service_s * 1000.0, 3),
                    "read": round(runner_timing["read_s"] * 1000.0, 3),
                    "lag": round(lag_s * 1000.0, 3),
                },
            })
    else:
        result["ticks"] = n_ticks

    if result.get("ok") and mode == "lower":
        # Finished on the belly: go limp, that's the safe rest state.
        limp()
        result["limped"] = True
    if mode == "walk":
        # Walk ends holding the final stance (torque on) after the
        # decel ramp — the operator decides what happens next.
        result.update(vx_cmd=round(vx, 3), vy_cmd=round(vy, 3),
                      duration_s=round(total_s, 1),
                      rot60=canon is not None,
                      rot60_k_end=(canon.k if canon is not None
                                   else None))
        if selector is not None:
            result.update(
                turn=turn, turn_switches=selector.switches,
                heading_end_deg=round(
                    math.degrees(selector.heading), 1))

    # Post-episode tail (08-10, dep-tip1 fall debug): the robot tipped
    # AFTER "walk done" — the episode ended holding a ~15° lean and
    # the log stopped with it. Keep READING (never commanding) for a
    # few seconds so a tip-over during the end-of-episode hold (or
    # the collapse after a trip limp) is in the trace. A successful
    # learned-stand handoff intentionally skips this tail so joystick
    # control can take over immediately.
    TAIL_S = 0.0 if result.get("early_handoff") and mode == "stand" else 3.0
    tail_tilt_samples: list[float] = []
    for k in range(int(TAIL_S * 10)):
        time.sleep(0.1)
        try:
            if async_sampler is not None:
                state_robot, _tail_stats = _latest_async_tail_state(
                    async_sampler)
                if state_robot is None:
                    break
            else:
                state_robot = est.update()
            state = _state_for_policy_frame(state_robot, joint_frame)
        except Exception:
            break
        if state is None or not state.bus_ok:
            break
        tail_tilt_samples.append(max(
            abs(state.imu_roll - tilt_ref0[0]) * RAD2DEG,
            abs(state.imu_pitch - tilt_ref0[1]) * RAD2DEG))
        elog.tick(t_end + (k + 1) * 0.1, state, None, None, None,
                  0.0, 0.0, max_cur, phase="tail")

    tail_tilt = _tail_tilt_summary(tail_tilt_samples)
    if async_sampler is not None:
        async_sampler_last_stats = async_sampler.stats()
        async_sampler.stop()
        debug.event("move_async_snapshot_stop", publish=False,
                    stats=async_sampler_last_stats)
        async_sampler = None

    result.update(
        max_current_a=round(max_cur, 2), overruns=overruns,
        policy_hz=timing.policy_hz,
        runner_config_hz=timing.runner_config_hz,
        policy_rate_adapted=timing.adapted,
        inner_hz=inner_hz, inner_steps=inner_steps,
        transport="async" if async_move else "direct",
        bus_write_hz=(move_write.write_hz
                      if move_write is not None else inner_hz),
        bus_write_every_ticks=(
            move_write.write_every_ticks if move_write is not None else 1),
        async_snapshot=async_sampler_last_stats,
        max_delta_q_deg=round(max_dq_deg, 4),
        max_delta_q_deg_explicit=max_dq_explicit,
        write_speed=write_speed, write_acc=write_acc,
        stale_stream_samples=stale_stream_samples,
        stale_stream_ticks=stale_stream_ticks,
        stale_stream_bursts=stale_stream_bursts,
        max_stale_stream_ticks_seen=max_stale_stream_ticks_seen,
        first_stale_stream_at_s=(round(first_stale_at_s, 3)
                                 if first_stale_at_s is not None else None),
        last_stale_stream_at_s=(round(last_stale_at_s, 3)
                                if last_stale_at_s is not None else None),
        max_stale_stream_ticks=DRIVE_STREAM_STALE_TICKS,
        timing=timing_stats.summary(),
        tilt_ref_deg=[round(tilt_ref0[0] * RAD2DEG, 2),
                      round(tilt_ref0[1] * RAD2DEG, 2)],
        # Attitude bookkeeping, all relative to the episode tilt ref:
        # the summary alone should answer "did it stay level, and did
        # it go over after the episode?" without opening the CSV.
        tilt_rel_max_deg=round(tilt_rel_max, 1),
        roll_rel_end_deg=round(
            (state.imu_roll - tilt_ref0[0]) * RAD2DEG, 1)
        if state is not None else None,
        pitch_rel_end_deg=round(
            (state.imu_pitch - tilt_ref0[1]) * RAD2DEG, 1)
        if state is not None else None,
        tail_s=TAIL_S,
        **tail_tilt,
        # >35° relative during the commanded run is already beyond the
        # 25° walk trip.  Tail-only excursions count as a fall unless the
        # IMU demonstrably returns inside 25° for three samples.
        fell=bool(tilt_rel_max > TAIL_FALL_TILT_DEG
                  or tail_tilt["tail_fell"]),
    )
    debug.attach(result)
    result["log"] = elog.close(result)
    debug.event("episode_complete", result=result)
    debug.close(result)
    return result


def run_policy_move(drive, mode: str, *, on_progress=None,
                    abort_check=None, vx: float = 0.03, vy: float = 0.0,
                    duration_s: float = 6.0, rot60: bool = True,
                    turn: str | None = None,
                    weights_path: Path | None = None,
                    tilt_trip_deg: float | None = None,
                    extra_hold_s: float = 0.0,
                    allow_step_stand_start: bool = False,
                    stand_handoff: bool = True) -> dict:
    """Exception-safe public wrapper for a bounded policy move."""
    require_bus_available(getattr(drive, "bus", None))
    try:
        return _run_policy_move_impl(
            drive, mode, on_progress=on_progress,
            abort_check=abort_check, vx=vx, vy=vy,
            duration_s=duration_s, rot60=rot60, turn=turn,
            weights_path=weights_path, tilt_trip_deg=tilt_trip_deg,
            extra_hold_s=extra_hold_s,
            allow_step_stand_start=allow_step_stand_start,
            stand_handoff=stand_handoff)
    finally:
        _stop_active_async_samplers()


def benchmark_drive_hot_path(drive, *, walk_weights: Path | None = None,
                             samples: int = 200,
                             read_samples: int = 8) -> dict:
    """No-motion timing probe for the drive loop's CPU-side hot path.

    This loads the selected walk policy, takes read-only snapshots, and
    repeatedly runs the same obs -> policy -> safety code used by
    ``run_drive_session``. It never enables torque, writes servo targets,
    or changes ``drive.armed``.
    """
    bus = drive.bus
    if bus is None or drive.dry_run:
        return {"ok": False, "error": "no bus"}
    samples = max(1, min(2000, int(samples)))
    read_samples = max(0, min(50, int(read_samples)))

    cfg = load_config(str(_HERE.parent / "rl_move" / "config.yaml"))
    wpath = walk_weights or WALK_WEIGHTS_PATH
    policy = NumpyPolicy(wpath)
    walk_obs = int(policy.meta.get("obs_dim") or 0)
    if walk_obs not in WALK_OBS_DIMS:
        return {"ok": False,
                "error": f"{Path(wpath).name} is not a walk policy"}
    walk_speed_min, walk_speed_max = _policy_walk_speed_band(policy)
    try:
        timing = _policy_timing(policy)
        joint_frame = policy_joint_frame(policy, cfg)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    async_probe = _probe_async_transport(
        bus, samples=max(3, min(10, read_samples or 3)))

    est = RobotStateEstimator(bus, cfg)
    read_times: list[float] = []
    state_robot = None
    read_errors = 0
    observed_sources: list[str] = []
    for _ in range(max(1, read_samples)):
        t0 = time.perf_counter()
        try:
            sampled = est.update(want_full_feedback=False)
        except Exception:
            sampled = None
        read_times.append(time.perf_counter() - t0)
        if sampled is not None and sampled.bus_ok:
            state_robot = sampled
            source = str((sampled.timing or {}).get("source") or "unknown")
            if source not in observed_sources:
                observed_sources.append(source)
        else:
            read_errors += 1
    if state_robot is None:
        fallback: dict = {}
        q_deg, err = _read_q_deg(bus)
        if q_deg is None:
            return {"ok": False,
                    "error": f"feedback unavailable: {err}",
                    "snapshot_read": _ms_stats(read_times),
                    "snapshot_read_errors": read_errors,
                    "async_transport": async_probe}
        state_robot = _direct_start_state(
            bus, np.asarray(q_deg, dtype=float) * DEG2RAD, fallback)
        if state_robot is None:
            return {"ok": False,
                    "error": "feedback unavailable",
                    "snapshot_read": _ms_stats(read_times),
                    "snapshot_read_errors": read_errors,
                    "async_transport": async_probe,
                    "fallback": fallback}

    state = _state_for_policy_frame(state_robot, joint_frame)
    q_nom = state.joint_position.copy()
    prev_action = np.zeros(N_JOINTS, dtype=float)
    goal = TaskGoal(roll_ref=0.0, pitch_ref=0.0, height_ref=0.0,
                    unload_leg=None)
    tilt_ref0 = (state.imu_roll, state.imu_pitch)
    safety = SafetyLayer(cfg)
    max_dq_deg, max_dq_explicit = _apply_policy_safety_timing(
        safety, policy, cfg, timing)
    safety.max_roll = math.radians(WALK_MAX_TILT_DEG)
    safety.max_pitch = math.radians(WALK_MAX_TILT_DEG)
    safety.set_nominal(q_nom)
    safety.set_tilt_reference(*tilt_ref0)
    canon = make_walk_canonicalizer(policy, cfg) if walk_obs == 72 else None
    phase = 0.0
    phase_hz = float(policy.meta.get("phase_hz", 0.0) or 0.0)
    vx_r = walk_speed_min
    vy_r = 0.0
    wz_r = 0.0
    phase_run_on_yaw = bool(float(policy.meta.get(
        "walk_phase_run_on_yaw", 0.0)))

    obs_times: list[float] = []
    policy_times: list[float] = []
    safety_times: list[float] = []
    total_times: list[float] = []
    bad_action = ""
    safety_trip = ""

    for _ in range(samples):
        tick_t0 = time.perf_counter()
        stage_t = tick_t0
        base_obs = build_obs(cfg, state, q_nom, prev_action, goal=goal,
                             tilt_ref=tilt_ref0)
        obs = np.concatenate(
            [base_obs, _walk_obs_tail(walk_obs, vx_r, vy_r, phase, wz_r)]
        ).astype(np.float32)
        obs_times.append(time.perf_counter() - stage_t)

        stage_t = time.perf_counter()
        raw_act, _ = (canon.predict(obs) if canon is not None
                      else (policy.act(obs), None))
        policy_times.append(time.perf_counter() - stage_t)

        stage_t = time.perf_counter()
        action, bad = safety.validate_action(raw_act, n_act=N_JOINTS)
        if action is None:
            bad_action = bad
            break
        q_prop = _CENTER_RAD + action * _HALF_RAD
        q_safe, status = safety.filter(q_prop, state, action=action)
        safety_times.append(time.perf_counter() - stage_t)
        if status.terminate:
            safety_trip = status.reason
            break

        prev_action = action.copy()
        if _walk_phase_runs(walk_obs, vx_r, vy_r, wz_r,
                            phase_run_on_yaw=phase_run_on_yaw):
            phase = (phase + 2.0 * math.pi * phase_hz * timing.policy_dt) % (
                2.0 * math.pi)
        total_times.append(time.perf_counter() - tick_t0)

    return {
        "ok": not bad_action and not safety_trip,
        "motion_free": True,
        "writes_servo_targets": False,
        "enables_torque": False,
        "policy": policy.meta.get("name") or Path(wpath).name,
        "policy_file": Path(wpath).name,
        "obs_dim": walk_obs,
        "policy_hz": timing.policy_hz,
        "budget_ms": round(timing.policy_dt * 1000.0, 3),
        "bus_write_not_measured": True,
        "last_known_write_ms_note": (
            "drive hot path probe omits step_all/write_all; use episode CSV "
            "from a supervised drive attempt for bus write timing"),
        "snapshot_read": _ms_stats(read_times),
        "snapshot_read_errors": read_errors,
        "state_source": (observed_sources[-1] if observed_sources
                         else async_probe.get("source")),
        "state_sources": observed_sources,
        "snapshot_seq_first": async_probe.get("seq_first"),
        "snapshot_seq_last": async_probe.get("seq_last"),
        "snapshot_seq_advance_count": async_probe.get(
            "seq_advance_count"),
        "max_position_source_age_ms": async_probe.get("max_pos_age_ms"),
        "max_imu_source_age_ms": async_probe.get("max_imu_age_ms"),
        "async_capable": async_probe.get("async_capable", False),
        "async_transport": async_probe,
        "hot_path": {
            "total": _ms_stats(total_times),
            "obs": _ms_stats(obs_times),
            "policy": _ms_stats(policy_times),
            "safety": _ms_stats(safety_times),
        },
        "max_delta_q_deg": round(max_dq_deg, 4),
        "max_delta_q_deg_explicit": max_dq_explicit,
        "bad_action": bad_action or None,
        "safety_trip": safety_trip or None,
    }


def _run_drive_session_impl(drive, cmd: DriveCommand, *, on_progress=None,
                            abort_check=None, rot60: bool = True,
                            walk_weights: Path | None = None,
                            hold_weights: Path | None = None,
                            allow_step_stand_start: bool = False) -> dict:
    """Blocking persistent drive session (MuJoCo-viewer-style driving).

    Same conventions as run_policy_move mode="walk" — plant-stance
    start gate, policy-declared rate, walk obs contract with meas := ref,
    rot-60 canonicalizer, 25 deg tilt trip — but the command is LIVE: the
    browser streams body-frame (vx, vy) heartbeats into ``cmd`` while
    arrow keys are held. Refs slew toward the target at the trained
    ramp rate (0 -> full band in WALK_RAMP_S), so a key press feels
    like the training ramp and a release decays to the trained stop.

    Hold model: with ``hold_weights=None`` the session uses a built-in
    direct joint hold of the last safe commanded pose. This intentionally
    does NOT call the walk policy at zero refs: deployed walk champions
    can produce saturated gait actions at neutral joystick because zero
    speed was outside their useful hardware contract. A separate hold
    policy (obs 68 stance at height_ref 0, or another obs-72/74/93 file
    trained to stand still at zero refs) can take over instead. Every
    model switch re-anchors the episode frame (q_nom := present pose,
    prev_action := 0) — the same episode re-anchor the sim viewer's
    play.py does on policy handoff.

    Height: heartbeats may carry ``dh`` in [-1, 1] (gamepad D-pad).
    Only an obs-68 stance hold policy tracks the resulting height ref,
    and only while holding; see the DRIVE_HEIGHT_* constants.

    Ends by: operator stop (decel then HOLD pose), abort (hold),
    heartbeat silence > DRIVE_IDLE_END_S (browser gone -> hold),
    session cap DRIVE_MAX_SESSION_S (hold), or safety trip (limp).
    """
    on_progress = on_progress or (lambda p: None)
    abort_check = abort_check or (lambda: False)
    bus = drive.bus
    if bus is None or drive.dry_run:
        return {"ok": False, "error": "no bus"}

    cfg = load_config(str(_HERE.parent / "rl_move" / "config.yaml"))
    wpath = walk_weights or WALK_WEIGHTS_PATH
    walk_policy = NumpyPolicy(wpath)
    walk_obs = walk_policy.meta.get("obs_dim")
    if walk_obs not in WALK_OBS_DIMS:
        return {"ok": False,
                "error": (f"{Path(wpath).name} is not a walk policy "
                          f"(obs {walk_obs} not 72/74/93)")}
    # obs 74 = phase-clock walk (see run_policy_move): all-heading
    # training, no rot-60/mirror, phase_hz required in export meta.
    phase_hz = 0.0
    if walk_obs in WALK_PHASE_OBS_DIMS:
        if "phase_hz" not in walk_policy.meta:
            return {"ok": False,
                    "error": (f"{Path(wpath).name} is obs-{walk_obs} "
                              "but has no "
                              "phase_hz in meta — re-export with "
                              "--extra-meta phase_hz=<trained hz>")}
        phase_hz = float(walk_policy.meta["phase_hz"])
    hold_policy = None
    hold_obs = None
    if hold_weights is not None:
        hold_policy = NumpyPolicy(hold_weights)
        hold_obs = hold_policy.meta.get("obs_dim")
        if hold_obs not in (68, *WALK_OBS_DIMS):
            return {"ok": False,
                    "error": (f"{Path(hold_weights).name} fits no hold "
                              f"role (obs {hold_obs}, need 68/72/74/93)")}
        if hold_obs in WALK_PHASE_OBS_DIMS and "phase_hz" not in hold_policy.meta:
            return {"ok": False,
                    "error": (f"{Path(hold_weights).name} is "
                              f"obs-{hold_obs} but has no phase_hz in meta")}
    try:
        joint_frame = policy_joint_frame(walk_policy, cfg)
        hold_joint_frame = (policy_joint_frame(hold_policy, cfg)
                            if hold_policy is not None else joint_frame)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    if hold_policy is not None and hold_joint_frame != joint_frame:
        return {"ok": False,
                "error": ("walk/hold policy joint_frame mismatch "
                          f"({joint_frame} vs {hold_joint_frame})")}
    walk_speed_min, walk_speed_max = _policy_walk_speed_band(walk_policy)
    try:
        timing = _policy_timing(walk_policy)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    if hold_policy is not None:
        try:
            hold_timing = _policy_timing(hold_policy)
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        if abs(hold_timing.policy_hz - timing.policy_hz) > 1e-6:
            return {"ok": False,
                    "error": ("drive walk/hold training_hz mismatch "
                              f"({timing.policy_hz:g} vs "
                              f"{hold_timing.policy_hz:g}); select a "
                              "hold policy trained at the same cadence")}
    write_speed, write_acc = _policy_bus_profile(walk_policy, cfg)
    inner_steps, inner_hz, inner_dt = _inner_stream_plan(
        walk_policy, cfg, timing.policy_hz)
    drive_write = _drive_write_plan(walk_policy, cfg, timing.policy_hz)
    debug = _RunDebug("drive", {
        "walk_policy_path": str(wpath),
        "walk_policy_name": walk_policy.meta.get("name"),
        "walk_obs_dim": walk_obs,
        "hold_policy_path": str(hold_weights) if hold_weights else None,
        "hold_obs_dim": hold_obs,
        "joint_frame": joint_frame,
        "joint_contract": JOINT_CONTRACT,
        "timing": {
            "policy_hz": timing.policy_hz,
            "training_hz": timing.policy_hz,
            "trained_control_hz": timing.trained_control_hz,
            "runner_config_hz": timing.runner_config_hz,
            "adapted": timing.adapted,
            "inner_hz": inner_hz,
            "inner_steps": inner_steps,
            "drive_write_hz": drive_write.write_hz,
            "drive_write_requested_hz": drive_write.requested_hz,
            "drive_write_every_ticks": drive_write.write_every_ticks,
        },
        "write_speed": write_speed,
        "write_acc": write_acc,
        "rot60": rot60,
    })

    canon = (make_walk_canonicalizer(walk_policy, cfg)
             if rot60 and walk_obs == 72 else None)
    hold_canon = (make_walk_canonicalizer(hold_policy, cfg)
                  if rot60 and hold_policy is not None and hold_obs == 72
                  else None)
    if canon is None and walk_obs == 72 and not _ROT60_OK:
        # Without the canonicalizer only the trained forward wedge is
        # safe; a live joystick can't be trusted to stay inside it.
        # (obs-74 phase policies trained all headings — naked is fine.)
        return _finish_debug(
            debug, {"ok": False,
                    "error": ("drive session needs the rot-60 canonicalizer "
                              "(rl_move/sim/rot60.py not deployed)")})

    ok, reason, details = preflight(
        bus, "walk", allow_step_stand=bool(allow_step_stand_start))
    debug.event("preflight", ok=ok, reason=reason, details=details)
    if not ok:
        return _finish_debug(
            debug, {"ok": False, "error": f"preflight: {reason}", **details})
    start_target_deg, start_err = _preflight_start_target_deg(
        "walk", details, allow_step_stand=bool(allow_step_stand_start))
    if start_target_deg is None:
        return _finish_debug(
            debug, {"ok": False, "error": f"preflight: {start_err}",
                    **details})
    debug.event("start_target_selected",
                start_pose=details.get("start_pose"),
                target_deg=start_target_deg.tolist())

    async_probe = _probe_async_transport(bus)
    details["async_transport_probe"] = async_probe
    debug.event("async_transport_prearm", **async_probe)
    if not async_probe["async_capable"]:
        return _finish_debug(
            debug, {"ok": False,
                    "error": ("async transport unavailable before arm: "
                              + str(async_probe.get("error") or
                                    "freshness proof failed")),
                    "held_pose": True, "limped": False,
                    "preflight": details})

    def limp():
        try:
            bus.enable_all_torque(False)
        except Exception:
            try:
                drive._torque_all(False)
            except Exception:
                pass

    def hold_current_pose_after_stream_loss(
            fallback_robot: np.ndarray) -> bool:
        """Keep a weight-bearing walk from turning one bus miss into a drop."""
        debug.event("hold_after_stream_loss_begin",
                    fallback_deg=[round(float(x) * RAD2DEG, 2)
                                  for x in fallback_robot])
        try:
            _set_weight_bearing_torque(bus)
            drive._torque_all(True)
            drive.armed = True
        except Exception:
            pass

        pose = None
        for _ in range(5):
            try:
                sampled = est.update(want_full_feedback=True)
            except Exception:
                sampled = None
            if sampled is not None and sampled.bus_ok:
                pose = sampled.joint_position.copy()
                debug.event("hold_after_stream_loss_sampled",
                            state=_state_debug(sampled))
                break
            time.sleep(min(0.05, timing.policy_dt))
        if pose is None:
            pose = np.asarray(fallback_robot, dtype=float).copy()

        try:
            est.set_commanded(pose)
            bus.write_all((pose * RAD2DEG).tolist(), speed=write_speed,
                          acc=write_acc)
            with drive._lock:
                drive.status = "rl drive holding after stream loss"
            debug.event("hold_after_stream_loss_ok",
                        pose_deg=[round(float(x) * RAD2DEG, 2)
                                  for x in pose])
            return True
        except Exception:
            # If the half-duplex bus is still recovering, the least bad
            # weight-bearing choice is to leave torque enabled instead of
            # limping the whole body onto the floor.
            try:
                _set_weight_bearing_torque(bus)
                drive._torque_all(True)
            except Exception:
                pass
            debug.event("hold_after_stream_loss_write_failed")
            return False

    with drive._lock:
        drive.mode = "demo"
        try:
            drive.gait.stop()
        except Exception:
            pass
        # Do not trust the cached armed flag here. A stale True with actual
        # torque disabled lets joint-hold command start pose at ~0A, which
        # looks like a slow/drop fall when Start Driving is pressed.
        _set_weight_bearing_torque(bus)
        drive._torque_all(True)
        drive.armed = True
        drive.status = "rl drive armed"

    est = RobotStateEstimator(bus, cfg)
    safety = SafetyLayer(cfg)
    max_dq_deg, max_dq_explicit = _apply_policy_safety_timing(
        safety, walk_policy, cfg, timing)
    direct_over_current_trip_ticks = safety._over_current_trip_ticks  # noqa: SLF001
    safety.max_roll = math.radians(WALK_MAX_TILT_DEG)
    safety.max_pitch = math.radians(WALK_MAX_TILT_DEG)

    state_robot, refresh, start_err = _refresh_verified_start_pose(
        bus, est, start_target_deg, timing=timing,
        write_speed=write_speed, write_acc=write_acc,
        abort_check=abort_check, label=str(details.get("start_pose")),
        debug=debug)
    details["start_refresh"] = refresh
    if start_err:
        return _finish_debug(
            debug, {"ok": False, "error": start_err, "held_pose": True,
                    "limped": False, "preflight": details})
    q_nom_robot = np.asarray(start_target_deg, dtype=float) * DEG2RAD
    q_nom = q_nom_robot.copy()
    est.set_commanded(q_nom_robot)
    bus.write_all((q_nom_robot * RAD2DEG).tolist(), speed=write_speed,
                  acc=write_acc)
    last_q_robot_cmd = q_nom_robot.copy()
    last_q_policy_cmd = q_nom.copy()
    est.reset_episode_filters()
    warmup_good = 0
    warmup_stale = 0
    for _ in range(3):
        try:
            sampled = est.update(want_full_feedback=False)
        except Exception:
            sampled = None
        if sampled is not None and sampled.bus_ok:
            state_robot = sampled
            warmup_good += 1
        else:
            warmup_stale += 1
        time.sleep(timing.policy_dt)
    if state_robot is None or not state_robot.bus_ok:
        warmup_refresh: dict = {}
        state_robot = _direct_start_state(bus, q_nom_robot, warmup_refresh)
        if state_robot is None:
            return _finish_debug(
                debug, {"ok": False,
                        "error": "feedback unavailable during start warmup",
                        "held_pose": True,
                        "limped": False,
                        "preflight": details,
                        "start_warmup": warmup_refresh})
        details["start_warmup_fallback"] = warmup_refresh
    if warmup_stale:
        details["start_warmup"] = {
            "snapshot_samples": warmup_good,
            "stale_samples": warmup_stale,
        }
    debug.event("start_warmup_done", state=_state_debug(state_robot),
                warmup=details.get("start_warmup"),
                fallback=details.get("start_warmup_fallback"))
    state = _state_for_policy_frame(state_robot, joint_frame)
    tilt_ref0 = (state.imu_roll, state.imu_pitch)
    safety.set_nominal(q_nom)
    safety.set_tilt_reference(*tilt_ref0)

    prev_action = np.zeros(N_JOINTS, dtype=float)
    vx_r = vy_r = 0.0
    # Live height ref (D-pad up/down): only a learned obs-68 stance hold
    # can track it; everyone else keeps the trained height_ref = 0.
    height_can_track = hold_policy is not None and hold_obs == 68
    height_ref = 0.0
    phase = 0.0     # walk phase clock (obs-74/93 policies only); like the
                    # sim it starts at 0 and freezes at zero command
    phase_run_on_yaw = bool(float(walk_policy.meta.get(
        "walk_phase_run_on_yaw", 0.0)))
    dv_max = walk_speed_max * timing.policy_dt / WALK_RAMP_S
    active = "hold"
    walk_has_engaged = False
    walk_cmd_since: float | None = None
    walk_active_since: float | None = None
    zero_since: float | None = None  # first tick of neutral input while walking
    stopping = None             # reason string once winding down
    overruns = 0
    max_cur = 0.0
    tilt_rel_max = 0.0
    t = 0.0
    i = 0
    last_hold_refresh_t = -DRIVE_HOLD_REFRESH_S
    timing_stats = _TimingStats()
    consecutive_late = 0
    progress_every = max(1, int(round(timing.policy_hz / 5.0)))
    result: dict = {"ok": True, "mode": "drive",
                    "training_hz": timing.policy_hz,
                    "policy_joint_frame": joint_frame,
                    "policy_joint_contract": JOINT_CONTRACT}
    last_good_stream_state = state_robot
    stale_stream_ticks = 0
    stale_stream_samples = 0
    max_stale_stream_ticks_seen = 0
    stale_stream_bursts = 0
    first_stale_at_s: float | None = None
    last_stale_at_s: float | None = None
    async_sampler: _AsyncSnapshotSampler | None = None
    async_sampler_last_stats: dict | None = None
    async_start_wait_s = 0.0
    waiting_for_command_logged = False
    first_drive_command_logged = False
    elog = _EpisodeLog("drive", obs_dim=int(walk_obs), params={
        "mode": "drive", "hz": timing.policy_hz,
        "policy_hz": timing.policy_hz,
        "training_hz": timing.policy_hz,
        "trained_control_hz": timing.trained_control_hz,
        "trained_control_hz_explicit": timing.trained_control_hz_explicit,
        "runner_config_hz": timing.runner_config_hz,
        "policy_rate_adapted": timing.adapted,
        "inner_hz": inner_hz, "inner_steps": inner_steps,
        "max_delta_q_deg": round(max_dq_deg, 4),
        "max_delta_q_deg_explicit": max_dq_explicit,
        "write_speed": write_speed, "write_acc": write_acc,
        "policy": dict(walk_policy.meta),
        "hold_policy": (dict(hold_policy.meta)
                        if hold_policy is not None else None),
        "hold_strategy": ("learned_policy"
                          if hold_policy is not None else "joint_hold"),
        "initial_hold_strategy": "joint_hold_until_first_walk_command",
        "height_can_track": height_can_track,
        "policy_joint_frame": joint_frame,
        "policy_joint_contract": JOINT_CONTRACT,
        "q_nom_deg": [round(float(q) * RAD2DEG, 2) for q in q_nom],
        "tilt_ref_deg": [round(tilt_ref0[0] * RAD2DEG, 2),
                         round(tilt_ref0[1] * RAD2DEG, 2)],
        "tilt_trip_deg": WALK_MAX_TILT_DEG,
        "drive_snapshot": {
            "mode": "async",
            "hz": DRIVE_ASYNC_SNAPSHOT_HZ,
            "max_age_s": DRIVE_ASYNC_STATE_MAX_AGE_S,
        },
        "debug_log": debug.name,
        "preflight": details, "rot60": canon is not None,
    }, debug=debug)

    def warm_drive_hot_path() -> None:
        """Pay numpy/policy/safety cold-start costs before the 100 Hz clock."""
        try:
            warm_goal = TaskGoal(roll_ref=0.0, pitch_ref=0.0,
                                 height_ref=0.0, unload_leg=None)
            warm_base = build_obs(cfg, state, q_nom, prev_action,
                                  goal=warm_goal, tilt_ref=tilt_ref0)
            warm_tail = _walk_obs_tail(int(walk_obs), walk_speed_min, 0.0,
                                       phase, 0.0)
            warm_walk_obs = np.concatenate(
                [warm_base, warm_tail]).astype(np.float32)
            walk_policy.act(warm_walk_obs)

            warm_hold_len = None
            if hold_policy is not None:
                if hold_obs in WALK_OBS_DIMS:
                    hold_tail = _walk_obs_tail(int(hold_obs),
                                               walk_speed_min, 0.0,
                                               phase, 0.0)
                    warm_hold_obs = np.concatenate(
                        [warm_base, hold_tail]).astype(np.float32)
                else:
                    warm_hold_obs = warm_base
                hold_policy.act(warm_hold_obs)
                warm_hold_len = len(warm_hold_obs)

            scratch_safety = SafetyLayer(cfg)
            scratch_safety.max_roll = safety.max_roll
            scratch_safety.max_pitch = safety.max_pitch
            scratch_safety.max_dq = safety.max_dq
            scratch_safety.set_nominal(q_nom)
            scratch_safety.set_tilt_reference(*tilt_ref0)
            warm_action, _ = scratch_safety.validate_action(
                np.zeros(N_JOINTS, dtype=float), n_act=N_JOINTS)
            scratch_safety.filter(q_nom, state, action=warm_action)
            debug.event("drive_hot_path_warmup", publish=False,
                        walk_obs_len=len(warm_walk_obs),
                        hold_obs_len=warm_hold_len,
                        safety_filter=True)
        except Exception as e:
            debug.event("drive_hot_path_warmup_failed", error=repr(e))

    warm_drive_hot_path()
    t_next = time.monotonic()

    def ensure_async_sampler() -> tuple[
            _AsyncSnapshotSampler | None, object | None, str, bool]:
        nonlocal async_sampler, async_sampler_last_stats
        nonlocal async_start_wait_s, t_next
        state_ready = None
        ready_err = ""
        started = False
        if async_sampler is None:
            started = True
            ready_t0 = time.monotonic()
            feedback_hz = _apply_async_safety_feedback_timing(
                safety, cfg, DRIVE_ASYNC_SNAPSHOT_HZ)
            async_sampler = _AsyncSnapshotSampler(
                bus, cfg, initial_state=state_robot,
                hz=DRIVE_ASYNC_SNAPSHOT_HZ,
                max_age_s=DRIVE_ASYNC_STATE_MAX_AGE_S)
            async_sampler.set_commanded(last_q_robot_cmd)
            async_sampler.start()
            state_ready, ready_details, ready_err = (
                _await_async_sampler_ready(
                    async_sampler, abort_check, health_safety=safety))
            async_start_wait_s += time.monotonic() - ready_t0
            # The motionless readiness probation is not a missed policy
            # deadline.  Start the command clock only after it completes.
            t_next = time.monotonic()
            debug.event("drive_async_snapshot_start", publish=False,
                        ok=not bool(ready_err), error=ready_err or None,
                        hz=DRIVE_ASYNC_SNAPSHOT_HZ,
                        feedback_hz=feedback_hz,
                        max_age_ms=async_sampler.max_age_s * 1000.0,
                        details=ready_details,
                        state=_state_debug(state_ready))
            if ready_err:
                async_sampler_last_stats = async_sampler.stats()
                # Confirm the reader released the UART before returning the
                # exact readiness error to the drive loop.
                async_sampler.stop()
                debug.event("drive_async_snapshot_stop", publish=False,
                            stats=async_sampler_last_stats,
                            reason="readiness_failed")
                async_sampler = None
                safety._over_current_trip_ticks = (  # noqa: SLF001
                    direct_over_current_trip_ticks)
        return async_sampler, state_ready, ready_err, started

    def stop_async_sampler() -> None:
        nonlocal async_sampler, async_sampler_last_stats
        if async_sampler is None:
            return
        async_sampler_last_stats = async_sampler.stats()
        async_sampler.stop()
        debug.event("drive_async_snapshot_stop", publish=False,
                    stats=async_sampler_last_stats)
        async_sampler = None
        safety._over_current_trip_ticks = (  # noqa: SLF001
            direct_over_current_trip_ticks)

    def reanchor():
        """Episode re-anchor on model switch (q frame + prev_action)."""
        nonlocal q_nom, prev_action, last_q_robot_cmd, last_q_policy_cmd
        q_nom = state.joint_position.copy()
        safety.set_nominal(q_nom)
        prev_action = np.zeros(N_JOINTS, dtype=float)
        last_q_policy_cmd = q_nom.copy()
        if state_robot is not None:
            last_q_robot_cmd = state_robot.joint_position.copy()

    def sample_hold_tick() -> tuple[object | None, float, int, str, dict]:
        """Wait one policy tick and read state without writing targets."""
        nonlocal t_next
        hold_t0 = time.monotonic()
        read_s = 0.0
        lag_s = 0.0

        def hold_timing() -> dict:
            return {
                "stream_s": time.monotonic() - hold_t0,
                "write_s": 0.0,
                "read_s": read_s,
                "lag_s": lag_s,
            }

        if abort_check():
            return state_robot, t_next, 0, "aborted", hold_timing()
        t_next += timing.policy_dt
        lag = time.monotonic() - t_next
        overruns_tick = 0
        if lag > 0:
            overruns_tick = 1
            lag_s = max(lag_s, float(lag))
            t_next = time.monotonic()
        else:
            time.sleep(-lag)
        sampled = None
        for attempt in range(4):
            op_t = time.monotonic()
            sampled = est.update()
            read_s += time.monotonic() - op_t
            if sampled is not None and sampled.bus_ok:
                return sampled, t_next, overruns_tick, "", hold_timing()
            if abort_check():
                return (state_robot, t_next, overruns_tick, "aborted",
                        hold_timing())
            # Snapshot reads can miss a beat while the MCU is recovering
            # from a previous stream/glide. In joint-hold mode the servos
            # already have a safe target, so retry briefly instead of
            # converting one telemetry miss into an emergency limp.
            time.sleep(min(0.02, timing.policy_dt * 0.5))
        return (sampled, t_next, overruns_tick,
                "feedback lost during hold", hold_timing())

    while True:
        if abort_check():
            result.update(ok=False, error="aborted", held_pose=True,
                          ticks=i)
            break
        t = i * timing.policy_dt
        tick_t0 = time.monotonic()
        stage_t = tick_t0
        async_start_wait_s = 0.0
        model_switched = False
        write_due = False
        vx_t, vy_t, wz_t, dh_t, hb_age, stop_req = cmd.get()
        if stop_req and stopping is None:
            stopping = "stopped"
        if hb_age > DRIVE_IDLE_END_S and stopping is None:
            stopping = "no command from browser — session ended"
        if t > DRIVE_MAX_SESSION_S and stopping is None:
            stopping = f"session cap {DRIVE_MAX_SESSION_S:.0f}s reached"
        if stopping is not None or hb_age > DRIVE_CMD_TIMEOUT_S:
            vx_t = vy_t = wz_t = 0.0
            dh_t = 0.0
        if not height_can_track:
            dh_t = 0.0
        vx_t, vy_t = _drive_clamp_translation(
            vx_t, vy_t, walk_speed_min, walk_speed_max)
        moving_requested = _drive_command_is_moving(
            vx_t, vy_t, wz_t, int(walk_obs))
        waiting_for_drive_command = (
            active == "hold" and not walk_has_engaged
            and not moving_requested and stopping is None)
        if waiting_for_drive_command and not waiting_for_command_logged:
            debug.event("drive_waiting_for_command", tick=i, t_s=t,
                        hold_policy_available=hold_policy is not None,
                        publish=False, flush=False)
            waiting_for_command_logged = True
        if moving_requested and not first_drive_command_logged:
            debug.event("drive_command_received", tick=i, t_s=t,
                        vx_cmd=vx_t, vy_cmd=vy_t, wz_cmd=wz_t,
                        hb_age_s=round(float(hb_age), 3),
                        publish=False, flush=False)
            first_drive_command_logged = True
        # A crouched/raised body must return to the walk anchor height
        # before the gait engages (walk champions trained at ref 0).
        height_returning = (moving_requested and active != "walk"
                            and abs(height_ref) > DRIVE_HEIGHT_EPS_M)
        if moving_requested:
            if walk_cmd_since is None:
                walk_cmd_since = t
            moving = (active == "walk"
                      or ((t - walk_cmd_since) >= DRIVE_WALK_ENGAGE_S
                          and not height_returning))
        else:
            walk_cmd_since = None
            moving = False
        if stopping is not None and not moving:
            # Graceful end: refs decayed to zero, robot HOLDS the pose.
            result.update(ticks=i, ended=stopping)
            break

        zero_dwell_active, zero_since = _drive_zero_dwell(
            active, moving_requested, zero_since, t)
        if moving:
            zero_since = None
            if active != "walk":
                prev_active = active
                active = "walk"
                model_switched = True
                walk_active_since = t
                walk_has_engaged = True
                reanchor()
                debug.event("drive_model_switch", tick=i, t_s=t,
                            from_model=prev_active, to_model=active,
                            vx_cmd=vx_t, vy_cmd=vy_t, wz_cmd=wz_t,
                            publish=False, flush=False)
                # Engage inside the policy's trained command band on the
                # first walk tick. The safety layer still rate-limits joint
                # motion; this only prevents feeding the actor a 0.002 m/s
                # ramp value it was never meant to interpret.
                vx_r, vy_r = vx_t, vy_t
            else:
                # Slew refs toward the target at the trained ramp rate, then
                # keep the nonzero ref inside the trained band.
                vx_r += max(-dv_max, min(dv_max, vx_t - vx_r))
                vy_r += max(-dv_max, min(dv_max, vy_t - vy_r))
                vx_r, vy_r = _drive_clamp_translation(
                    vx_r, vy_r, walk_speed_min, walk_speed_max)
        elif zero_dwell_active:
            # Do not run walk obs at true zero and do not instant-handoff
            # to static joint hold from an arbitrary gait phase. Brief
            # neutral joystick/browser samples coast on the last trained
            # nonzero gait ref; sustained neutral still falls through to
            # the explicit hold handoff below.
            if math.hypot(vx_r, vy_r) <= DRIVE_MOVE_EPS_MPS:
                vx_r, vy_r = walk_speed_min, 0.0
        elif active == "walk":
            prev_active = active
            vx_r = vy_r = 0.0
            active = "hold"
            model_switched = True
            walk_active_since = None
            zero_since = None
            reanchor()
            last_hold_refresh_t = -DRIVE_HOLD_REFRESH_S
            debug.event("drive_model_switch", tick=i, t_s=t,
                        from_model=prev_active, to_model=active,
                        publish=False, flush=False)
        else:
            vx_r = vy_r = 0.0
            zero_since = None

        # Height ref: 0 while walking (trained contract), ramp back to 0
        # when a move command wants the gait, else integrate held D-pad.
        if active == "walk":
            height_ref = 0.0
        elif height_returning:
            step = DRIVE_HEIGHT_RATE_MPS * timing.policy_dt
            height_ref = (0.0 if abs(height_ref) <= step
                          else height_ref - math.copysign(step, height_ref))
        elif dh_t:
            height_ref = max(DRIVE_HEIGHT_MIN_M,
                             min(DRIVE_HEIGHT_MAX_M,
                                 height_ref + dh_t * DRIVE_HEIGHT_RATE_MPS
                                 * timing.policy_dt))

        goal = TaskGoal(roll_ref=0.0, pitch_ref=0.0, height_ref=height_ref,
                        unload_leg=None)
        base_obs = build_obs(cfg, state, q_nom, prev_action, goal=goal,
                             tilt_ref=tilt_ref0)
        need_obs = walk_obs if active == "walk" else hold_obs
        wz_r = wz_t if active == "walk" else 0.0
        obs = None
        action = None
        policy_s = 0.0
        uses_policy = _drive_should_run_learned_policy(
            active, hold_policy, walk_has_engaged=walk_has_engaged)
        if uses_policy:
            if need_obs in WALK_OBS_DIMS:
                obs = np.concatenate(
                    [base_obs, _walk_obs_tail(need_obs, vx_r, vy_r,
                                              phase, wz_r)]
                ).astype(np.float32)
            else:   # 68-obs stance hold at height_ref 0
                obs = base_obs
            obs_s = time.monotonic() - stage_t
            stage_t = time.monotonic()
            if need_obs in WALK_OBS_DIMS:
                if active == "walk":
                    raw_act, _ = (canon.predict(obs) if canon is not None
                                  else (walk_policy.act(obs), None))
                else:
                    raw_act, _ = (hold_canon.predict(obs)
                                  if hold_canon is not None
                                  else (hold_policy.act(obs), None))
            else:
                raw_act = hold_policy.act(obs)
            # Phase clock advance (obs-74/93 policies): after obs, gated on a
            # live command ref. obs-93 AMP policies may also advance on yaw.
            if _walk_phase_runs(walk_obs, vx_r, vy_r, wz_r,
                                phase_run_on_yaw=phase_run_on_yaw):
                phase = (phase + 2.0 * math.pi * phase_hz
                         * timing.policy_dt) \
                    % (2.0 * math.pi)
            policy_s = time.monotonic() - stage_t
            stage_t = time.monotonic()
            action, bad = safety.validate_action(raw_act, n_act=N_JOINTS)
            if action is None:
                limp()
                debug.event("bad_action", tick=i, t_s=t, active=active,
                            error=bad, obs_len=len(obs),
                            state=_state_debug(state))
                result.update(ok=False, error=f"bad action: {bad}", ticks=i)
                break
            q_prop = _CENTER_RAD + action * _HALF_RAD
            if (active == "walk" and walk_active_since is not None
                    and DRIVE_WALK_ACTION_RAMP_S > 0.0):
                alpha = min(1.0, max(
                    0.0, (t - walk_active_since)
                    / DRIVE_WALK_ACTION_RAMP_S))
                q_prop = last_q_policy_cmd + alpha * (
                    q_prop - last_q_policy_cmd)
        else:
            obs_s = time.monotonic() - stage_t
            stage_t = time.monotonic()
            q_prop = last_q_policy_cmd.copy()
        q_safe, status = safety.filter(
            q_prop, _state_for_async_safety(state), action=action)
        q_robot_cmd = q_safe.copy()
        safety_s = time.monotonic() - stage_t
        if status.terminate:
            limp()
            debug.event("safety_trip", tick=i, t_s=t, active=active,
                        reason=status.reason, detail=status.detail,
                        held=status.held, state=_state_debug(state),
                        q_prop_deg=[round(float(x) * RAD2DEG, 2)
                                    for x in q_prop],
                        q_safe_deg=[round(float(x) * RAD2DEG, 2)
                                    for x in q_safe])
            result.update(ok=False, error=f"safety trip: {status.reason}"
                          + (f" ({status.detail})" if status.detail else ""),
                          limped=True, ticks=i)
            break
        prev_stale_ticks = stale_stream_ticks
        if uses_policy:
            sampler, ready_state, ready_err, sampler_started = (
                ensure_async_sampler())
            if ready_err:
                state_robot = ready_state or last_good_stream_state
                extra_overruns = 0
                stale_added = 0
                stream_err = ready_err
                stream_timing = {
                    "stream_s": async_start_wait_s,
                    "write_s": 0.0,
                    "read_s": 0.0,
                    "lag_s": 0.0,
                }
            elif sampler_started:
                # Probation can take several command-heartbeat intervals.
                # Adopt its fresh state, then re-read the mailbox and restart
                # this same policy tick; never send the pre-probation action.
                state_robot = ready_state
                last_good_stream_state = ready_state
                state = _state_for_policy_frame(ready_state, joint_frame)
                safety.set_nominal(last_q_robot_cmd)
                phase = 0.0
                cmd_after = cmd.get()
                debug.event(
                    "drive_command_after_async_ready", publish=False,
                    vx_cmd=cmd_after[0], vy_cmd=cmd_after[1],
                    wz_cmd=cmd_after[2], dh_cmd=cmd_after[3],
                    heartbeat_age_s=round(float(cmd_after[4]), 3),
                    stop=bool(cmd_after[5]))
                after_vx, after_vy = _drive_clamp_translation(
                    float(cmd_after[0]), float(cmd_after[1]),
                    walk_speed_min, walk_speed_max)
                after_moving = _drive_command_is_moving(
                    after_vx, after_vy, float(cmd_after[2]), int(walk_obs))
                if (cmd_after[5] or cmd_after[4] > DRIVE_CMD_TIMEOUT_S
                        or not after_moving):
                    active = "hold"
                    walk_has_engaged = False
                    walk_active_since = None
                    walk_cmd_since = None
                    zero_since = None
                    vx_r = vy_r = 0.0
                    stop_async_sampler()
                continue
            else:
                write_due = (model_switched or i == 0
                             or i % drive_write.write_every_ticks == 0)
                stream_steps = inner_steps if write_due else 1
                stream_dt = inner_dt if write_due else timing.policy_dt
                (state_robot, t_next, extra_overruns, stream_err,
                 stale_stream_ticks, stale_added, stream_timing) = (
                    _stream_target_async(
                    bus, sampler, last_q_robot_cmd, q_robot_cmd,
                    t_next=t_next, inner_steps=stream_steps,
                    inner_dt=stream_dt,
                    write_speed=write_speed, write_acc=write_acc,
                    abort_check=abort_check,
                    last_good_state=last_good_stream_state,
                    stale_ticks=stale_stream_ticks,
                    max_stale_ticks=DRIVE_STREAM_STALE_TICKS,
                    write_target=write_due))
        else:
            stop_async_sampler()
            est.set_commanded(q_robot_cmd)
            stream_err = ""
            hold_write_s = 0.0
            if t - last_hold_refresh_t >= DRIVE_HOLD_REFRESH_S:
                try:
                    op_t = time.monotonic()
                    bus.write_all((q_robot_cmd * RAD2DEG).tolist(),
                                  speed=write_speed, acc=write_acc)
                    hold_write_s += time.monotonic() - op_t
                    last_hold_refresh_t = t
                    write_due = True
                except Exception as e:
                    stream_err = f"hold write failed: {e}"
            if stream_err:
                extra_overruns = 0
                stale_added = 0
                stream_timing = {
                    "stream_s": hold_write_s,
                    "write_s": hold_write_s,
                    "read_s": 0.0,
                    "lag_s": 0.0,
                }
            else:
                state_robot, t_next, extra_overruns, stream_err, stream_timing = (
                    sample_hold_tick())
                stream_timing["write_s"] = (
                    float(stream_timing.get("write_s") or 0.0)
                    + hold_write_s)
                stream_timing["stream_s"] = (
                    float(stream_timing.get("stream_s") or 0.0)
                    + hold_write_s)
                stale_added = 0
        overruns += extra_overruns
        stale_stream_samples += stale_added
        if stale_added:
            burst_peak = max(prev_stale_ticks + stale_added,
                             stale_stream_ticks)
            max_stale_stream_ticks_seen = max(
                max_stale_stream_ticks_seen, burst_peak)
            last_stale_at_s = t
            if first_stale_at_s is None:
                first_stale_at_s = t
            if prev_stale_ticks == 0:
                stale_stream_bursts += 1
                debug.event("stream_feedback_stale_begin", tick=i, t_s=t,
                            active=active, stale_added=stale_added,
                            stale_ticks=stale_stream_ticks,
                            state=_state_debug(state_robot,
                                               q_cmd_rad=q_robot_cmd))
            if stale_stream_ticks == 0:
                debug.event("stream_feedback_recovered", tick=i, t_s=t,
                            active=active,
                            previous_stale_ticks=burst_peak,
                            state=_state_debug(state_robot,
                                               q_cmd_rad=q_robot_cmd))
        elif prev_stale_ticks > 0 and stale_stream_ticks == 0:
            debug.event("stream_feedback_recovered", tick=i, t_s=t,
                        active=active,
                        previous_stale_ticks=prev_stale_ticks,
                        state=_state_debug(state_robot,
                                           q_cmd_rad=q_robot_cmd))
        if stream_err:
            debug.event("stream_error", tick=i, t_s=t, active=active,
                        error=stream_err,
                        stale_ticks=stale_stream_ticks,
                        stale_samples=stale_stream_samples,
                        state=_state_debug(state_robot,
                                           q_cmd_rad=q_robot_cmd))
            # Any synchronous recovery below must have exclusive UART
            # ownership. This is also prompt cleanup for abort/readiness
            # failures; stop_async_sampler() is deliberately fail-closed.
            stop_async_sampler()
            if stream_err == "aborted":
                result.update(ok=False, error="aborted",
                              held_pose=True, ticks=i)
            elif isinstance(stream_err, AsyncReadinessFailure):
                # Readiness happens before the first learned write and its
                # sampler is already stopped. Confirmed physical health trips
                # limp; transport/freshness incapability leaves the verified
                # pose held and preserves the precise failure.
                if _async_readiness_requires_limp(stream_err):
                    limp()
                    result.update(ok=False, error=stream_err,
                                  held_pose=False, limped=True, ticks=i)
                else:
                    result.update(ok=False, error=stream_err,
                                  held_pose=True, limped=False, ticks=i)
            elif (stream_err == "feedback lost during hold"
                  and not uses_policy):
                result.update(ok=False, error=stream_err,
                              held_pose=True, ticks=i)
            elif (stream_err == "feedback stale during stream"
                  and active == "walk"):
                held = hold_current_pose_after_stream_loss(last_q_robot_cmd)
                result.update(
                    ok=False,
                    error=(stream_err + ("; held current pose" if held
                                         else "; torque left enabled")),
                    held_pose=held, limped=False, ticks=i)
            else:
                limp()
                result.update(ok=False, error=stream_err,
                              limped=True, ticks=i)
            break
        last_q_robot_cmd = q_robot_cmd.copy()
        last_q_policy_cmd = q_safe.copy()
        if action is not None:
            prev_action = action.copy()
        if not _stream_state_is_stale(state_robot):
            last_good_stream_state = state_robot
        state = _state_for_policy_frame(state_robot, joint_frame)
        if state.servo_current is not None:
            max_cur = max(max_cur,
                          float(np.max(np.abs(state.servo_current))))
        tilt_rel_max = max(
            tilt_rel_max,
            abs(state.imu_roll - tilt_ref0[0]) * RAD2DEG,
            abs(state.imu_pitch - tilt_ref0[1]) * RAD2DEG)
        service_s = max(
            0.0, time.monotonic() - tick_t0 - async_start_wait_s)
        lag_s = float(stream_timing.get("lag_s") or 0.0)
        late_s = max(lag_s, service_s - timing.policy_dt)
        if late_s > _timing_late_grace(timing.policy_dt):
            consecutive_late += 1
        else:
            consecutive_late = 0
        runner_timing = {
            "service_s": service_s,
            "obs_s": obs_s,
            "policy_s": policy_s,
            "safety_s": safety_s,
            "write_s": float(stream_timing.get("write_s") or 0.0),
            "read_s": float(stream_timing.get("read_s") or 0.0),
            "lag_s": lag_s,
        }
        timing_stats.add(runner_timing)
        timing_error = _drive_timing_trip_reason(
            active, hold_policy, i, timing, late_s, consecutive_late,
            uses_policy=uses_policy)
        # Hold-68 obs would misalign the fixed walk-wide obs columns —
        # blank them for those ticks (walk replay parity is what the
        # offline contract needs).
        obs_for_log = (obs if obs is not None and len(obs) == elog.obs_dim
                       else None)
        display_active = (
            "waiting" if waiting_for_drive_command else
            "arming" if moving_requested and not moving
            and stopping is None else active)
        elog.tick(t, state, action, q_safe, goal, vx_r, vy_r, max_cur,
                  obs=obs_for_log,
                  phase=("stopping" if stopping else display_active),
                  rot60_k=(canon.k if canon is not None
                           and active == "walk" else None),
                  runner_timing=runner_timing,
                  walk_engaged=(active == "walk" and uses_policy
                                and walk_has_engaged),
                  learned_policy_active=uses_policy,
                  bus_write_due=write_due)
        snap = {
            "t_s": round(t, 1), "model": display_active,
            "vx_ref": round(vx_r, 3), "vy_ref": round(vy_r, 3),
            "wz_ref": round(wz_r, 3),
            "vx_cmd": round(vx_t, 3), "vy_cmd": round(vy_t, 3),
            "wz_cmd": round(wz_t, 3),
            "height_ref_mm": round(height_ref * 1000.0, 1),
            "height_live": height_can_track,
            "height_returning": height_returning,
            "waiting_for_drive_command": waiting_for_drive_command,
            "learned_policy_active": uses_policy,
            "walk_has_engaged": walk_has_engaged,
            "walk_arming": bool(moving_requested and not moving),
            "walk_zero_dwell_s": round(
                max(0.0, DRIVE_HOLD_SWITCH_S - (t - zero_since)), 2)
            if zero_dwell_active and zero_since is not None else 0.0,
            "roll_deg": round((state.imu_roll - tilt_ref0[0]) * RAD2DEG,
                              1),
            "pitch_deg": round((state.imu_pitch - tilt_ref0[1])
                               * RAD2DEG, 1),
            "max_current_a": round(max_cur, 2),
            "stale_stream_ticks": stale_stream_ticks,
            "stale_stream_samples": stale_stream_samples,
            "rot60_k": canon.k if canon is not None else None,
            "stopping": stopping, "overruns": overruns,
            "drive_write_hz": round(drive_write.write_hz, 3),
            "drive_write_due": bool(write_due),
            "timing_ms": {
                "service": round(service_s * 1000.0, 3),
                "read": round(runner_timing["read_s"] * 1000.0, 3),
                "lag": round(lag_s * 1000.0, 3),
            },
        }
        cmd.publish(snap)
        if timing_error:
            # Confirm exclusive bus ownership before the synchronous hold
            # recovery. A failed join propagates and blocks later bus use.
            stop_async_sampler()
            held = hold_current_pose_after_stream_loss(last_q_robot_cmd)
            result.update(
                ok=False, error=timing_error,
                held_pose=held, limped=False, ticks=i,
                timing=timing_stats.summary())
            err_snap = {"level": "error", "error": timing_error,
                        "msg": timing_error, **snap}
            cmd.publish(err_snap)
            on_progress(err_snap)
            break
        if i % progress_every == 0:
            drive_msg = (f"drive waiting t={t:5.1f}s "
                         "no joystick/key command received "
                         if waiting_for_drive_command
                         else f"drive {display_active} t={t:5.1f}s "
                              f"v=({vx_r * 1000:+.0f},"
                              f"{vy_r * 1000:+.0f})mm/s "
                              f"wz={wz_r:+.2f}rad/s ")
            on_progress({
                "msg": (drive_msg
                        + (f"h={height_ref * 1000:+.0f}mm "
                           if height_ref else "")
                        + f"maxI={max_cur:.2f}A"
                        + (f" · {stopping}" if stopping else "")),
                **snap})
        i += 1
        t = i * timing.policy_dt

    # Same post-episode observation tail as run_policy_move: keep
    # reading (never commanding) so a fall during the end-of-session
    # hold is in the trace.  When live drive used the background snapshot
    # estimator, keep reading that same estimator through the tail.  Switching
    # back to the idle foreground estimator here used to inject a large stale
    # complementary-filter discontinuity (one upright course appeared to jump
    # from -3 to -56 deg exactly when its tail began).
    TAIL_S = 3.0
    tail_tilt_samples: list[float] = []
    for k in range(int(TAIL_S * 10)):
        time.sleep(0.1)
        try:
            if async_sampler is not None:
                state_robot, _stats = _latest_async_tail_state(async_sampler)
                if state_robot is None:
                    break
            else:
                state_robot = est.update()
            state = _state_for_policy_frame(state_robot, joint_frame)
        except Exception:
            break
        if state is None or not state.bus_ok:
            break
        tail_tilt_samples.append(max(
            abs(state.imu_roll - tilt_ref0[0]) * RAD2DEG,
            abs(state.imu_pitch - tilt_ref0[1]) * RAD2DEG))
        elog.tick(t + (k + 1) * 0.1, state, None, None, None,
                  0.0, 0.0, max_cur, phase="tail")

    stop_async_sampler()
    tail_tilt = _tail_tilt_summary(tail_tilt_samples)

    result.update(
        duration_s=round(t, 1),
        max_current_a=round(max_cur, 2), overruns=overruns,
        policy_hz=timing.policy_hz,
        runner_config_hz=timing.runner_config_hz,
        policy_rate_adapted=timing.adapted,
        inner_hz=inner_hz, inner_steps=inner_steps,
        drive_write_hz=drive_write.write_hz,
        drive_write_requested_hz=drive_write.requested_hz,
        drive_write_every_ticks=drive_write.write_every_ticks,
        walk_command_received=first_drive_command_logged,
        walk_has_engaged=walk_has_engaged,
        max_delta_q_deg=round(max_dq_deg, 4),
        max_delta_q_deg_explicit=max_dq_explicit,
        write_speed=write_speed, write_acc=write_acc,
        stale_stream_samples=stale_stream_samples,
        stale_stream_ticks=stale_stream_ticks,
        stale_stream_bursts=stale_stream_bursts,
        max_stale_stream_ticks_seen=max_stale_stream_ticks_seen,
        first_stale_stream_at_s=(round(first_stale_at_s, 3)
                                 if first_stale_at_s is not None else None),
        last_stale_stream_at_s=(round(last_stale_at_s, 3)
                                if last_stale_at_s is not None else None),
        max_stale_stream_ticks=DRIVE_STREAM_STALE_TICKS,
        async_snapshot=async_sampler_last_stats,
        timing=timing_stats.summary(),
        tilt_ref_deg=[round(tilt_ref0[0] * RAD2DEG, 2),
                      round(tilt_ref0[1] * RAD2DEG, 2)],
        tilt_rel_max_deg=round(tilt_rel_max, 1),
        tail_s=TAIL_S,
        **tail_tilt,
        fell=bool(tilt_rel_max > TAIL_FALL_TILT_DEG
                  or tail_tilt["tail_fell"]),
    )
    debug.attach(result)
    result["log"] = elog.close(result)
    debug.event("episode_complete", result=result)
    debug.close(result)
    return result


def run_drive_session(drive, cmd: DriveCommand, *, on_progress=None,
                      abort_check=None, rot60: bool = True,
                      walk_weights: Path | None = None,
                      hold_weights: Path | None = None,
                      allow_step_stand_start: bool = False) -> dict:
    """Exception-safe public wrapper for a persistent drive session."""
    require_bus_available(getattr(drive, "bus", None))
    try:
        return _run_drive_session_impl(
            drive, cmd, on_progress=on_progress,
            abort_check=abort_check, rot60=rot60,
            walk_weights=walk_weights, hold_weights=hold_weights,
            allow_step_stand_start=allow_step_stand_start)
    finally:
        _stop_active_async_samplers()
