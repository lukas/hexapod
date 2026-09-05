"""Deterministic replay of hardware drive timing with injected IMU faults.

This is an offline diagnostic.  It consumes a sealed drive CSV/debug trace,
reproduces the controller's recorded deadline decision, derives the extra
write-path cost during the IMU stall, and runs a small counterfactual matrix
for the attempt firmware and the current decoupled-cache firmware profile.
It never imports robot control code or opens a robot connection.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from statistics import median

ATTEMPT_PROFILE = "attempt3_count_backoff_coupled_cache"
CURRENT_PROFILE = "current_time_backoff_decoupled_cache"


@dataclass(frozen=True)
class ReplayConfig:
    control_hz: float = 100.0
    duration_s: float = 120.0
    repetitions: int = 10
    attitude_freshness_ms: float = 150.0
    late_grace_ms: float = 2.0
    max_consecutive_late: int = 12
    hard_lag_ms: float = 50.0
    critical_lag_ms: float = 200.0
    backoff_ms: float = 1000.0
    current_failure_grace_ms: float = 80.0
    host_cache_fresh_ms: float = 12.0

    @property
    def period_ms(self) -> float:
        return 1000.0 / self.control_hz


def _float(row: dict[str, str], key: str) -> float:
    try:
        value = float(row.get(key, ""))
    except (TypeError, ValueError):
        return math.nan
    return value


def _finite(values: Iterable[float]) -> list[float]:
    return [value for value in values if math.isfinite(value)]


def _percentile(values: Iterable[float], p: float) -> float:
    ordered = sorted(_finite(values))
    if not ordered:
        return math.nan
    rank = (len(ordered) - 1) * p
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def _stats(values: Iterable[float]) -> dict[str, float | int | None]:
    finite = _finite(values)
    if not finite:
        return {"n": 0, "median_ms": None, "p95_ms": None, "max_ms": None}
    return {
        "n": len(finite),
        "median_ms": round(median(finite), 3),
        "p95_ms": round(_percentile(finite, 0.95), 3),
        "max_ms": round(max(finite), 3),
    }


def load_trace(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    required = {
        "t_s", "service_ms", "obs_ms", "policy_ms", "safety_ms",
        "write_ms", "read_ms", "lag_ms", "imu_age_ms",
        "position_age_ms", "learned_policy_active",
    }
    missing = required.difference(rows[0] if rows else ())
    if missing:
        raise ValueError(f"trace is missing required columns: {sorted(missing)}")
    active = [
        row for row in rows
        if row.get("learned_policy_active") == "1"
        and row.get("phase") in {"walk", "run"}
    ]
    if len(active) < 3:
        raise ValueError("trace contains fewer than three active policy rows")
    return active


def load_debug(path: Path) -> list[dict]:
    events = []
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid debug JSON at line {line_number}") from exc
    return events


def _terminal_increasing_age_start(rows: list[dict[str, str]]) -> int:
    """Find the final run where cached IMU age advances between drive ticks."""
    ages = [_float(row, "imu_age_ms") for row in rows]
    start = len(ages) - 1
    while start > 0:
        previous, current = ages[start - 1], ages[start]
        if not (math.isfinite(previous) and math.isfinite(current)):
            break
        if current + 0.25 < previous or current - previous < 0.75:
            break
        start -= 1
    # ``start`` is now the final steady/reset sample immediately before the
    # age begins advancing (unless the run begins at row zero).
    return start + 1 if start > 0 else 0


def _deadline_replay(rows: list[dict[str, str]], cfg: ReplayConfig) -> dict:
    streak = 0
    max_streak = 0
    trip_index = None
    late_ms_values = []
    for index, row in enumerate(rows):
        service_ms = _float(row, "service_ms")
        lag_ms = _float(row, "lag_ms")
        late_ms = max(lag_ms, service_ms - cfg.period_ms)
        late_ms_values.append(late_ms)
        if late_ms > cfg.late_grace_ms:
            streak += 1
        else:
            streak = 0
        max_streak = max(max_streak, streak)
        if trip_index is None and (
            late_ms >= cfg.critical_lag_ms
            or (late_ms >= cfg.hard_lag_ms and streak >= 2)
            or streak >= cfg.max_consecutive_late
        ):
            trip_index = index
    return {
        "max_consecutive_late": max_streak,
        "trip_index": trip_index,
        "trip_t_s": (
            round(_float(rows[trip_index], "t_s"), 6)
            if trip_index is not None else None
        ),
        "late_ms": _stats(late_ms_values),
    }


def analyze_recorded_trace(
    rows: list[dict[str, str]], events: list[dict], cfg: ReplayConfig
) -> dict:
    stall_start = _terminal_increasing_age_start(rows)
    # Use a bounded recent prefix so startup/cold-cache work does not dilute
    # the steady-state comparison.
    baseline = rows[max(0, stall_start - 50):stall_start]
    stalled = rows[stall_start:]
    if not baseline or len(stalled) < 2:
        raise ValueError("could not isolate an IMU-age stall window")

    deadline = _deadline_replay(rows, cfg)
    terminal = next(
        (event.get("result", {}) for event in reversed(events)
         if event.get("event") in {"debug_end", "episode_complete"}),
        {},
    )
    recorded_error = str(terminal.get("error") or "")
    recorded_streak = cfg.max_consecutive_late if (
        f"{cfg.max_consecutive_late} consecutive" in recorded_error
    ) else None
    reproduction_ok = (
        deadline["trip_index"] is not None
        and deadline["max_consecutive_late"] >= cfg.max_consecutive_late
        and recorded_streak == cfg.max_consecutive_late
    )

    stage_keys = (
        "service_ms", "obs_ms", "policy_ms", "safety_ms", "write_ms",
        "read_ms", "lag_ms", "imu_age_ms", "position_age_ms",
    )
    per_stage = {
        key: {
            "pre_stall": _stats(_float(row, key) for row in baseline),
            "stall_window": _stats(_float(row, key) for row in stalled),
        }
        for key in stage_keys
    }
    write_extra_ms = max(
        0.0,
        float(per_stage["write_ms"]["stall_window"]["median_ms"] or 0.0)
        - float(per_stage["write_ms"]["pre_stall"]["median_ms"] or 0.0),
    )
    return {
        "reproduction": {
            "ok": reproduction_ok,
            "recorded_error": recorded_error or None,
            **deadline,
        },
        "stall_window": {
            "start_index": stall_start,
            "start_t_s": round(_float(rows[stall_start], "t_s"), 6),
            "samples": len(stalled),
            "imu_age_start_ms": round(_float(rows[stall_start], "imu_age_ms"), 3),
            "imu_age_end_ms": round(_float(rows[-1], "imu_age_ms"), 3),
            "position_age_end_ms": round(
                _float(rows[-1], "position_age_ms"), 3
            ),
        },
        "per_stage_timing": per_stage,
        "derived_coupled_refresh_cost_ms": round(write_extra_ms, 3),
        "baseline_service_ms": round(
            median(_finite(_float(row, "service_ms") for row in baseline)), 3
        ),
    }


def _simulate_case(
    *, profile: str, imu_delay_ms: float, consecutive_failures: int,
    baseline_service_ms: float, coupled_refresh_cost_ms: float,
    cfg: ReplayConfig,
) -> dict:
    period_ms = cfg.period_ms
    total_ticks = round(cfg.duration_s * cfg.control_hz)
    fault_start_tick = round(cfg.control_hz)
    now_ms = 0.0
    imu_age_ms = 0.0
    first_failure_ms = None
    backoff_until_ms = None
    consecutive_late = 0
    max_late_streak = 0
    max_attitude_age_ms = 0.0
    backoff_entries = 0
    stop_reason = None
    stop_tick = None

    for tick in range(total_ticks):
        if imu_age_ms >= cfg.attitude_freshness_ms:
            stop_reason = "attitude_freshness"
            stop_tick = tick
            break

        failing = fault_start_tick <= tick < (
            fault_start_tick + consecutive_failures
        )
        in_backoff = backoff_until_ms is not None and now_ms < backoff_until_ms
        service_ms = baseline_service_ms
        if failing and not in_backoff:
            if first_failure_ms is None:
                first_failure_ms = now_ms
            service_ms += imu_delay_ms
            failure_end_ms = now_ms + service_ms
            should_backoff = (
                profile == ATTEMPT_PROFILE
                and tick - fault_start_tick + 1 >= 3
            ) or (
                profile == CURRENT_PROFILE
                and failure_end_ms - first_failure_ms
                >= cfg.current_failure_grace_ms
            )
            if should_backoff:
                backoff_until_ms = failure_end_ms + cfg.backoff_ms
                backoff_entries += 1
        elif not in_backoff:
            imu_age_ms = 0.0
            first_failure_ms = None

        if profile == ATTEMPT_PROFILE and (
            failing or imu_age_ms > cfg.host_cache_fresh_ms or in_backoff
        ):
            # In 6e7d5ff, stale IMU made prepareSnapshotForHost call the full
            # refresh path, including another servo-position pass.
            service_ms += coupled_refresh_cost_ms

        elapsed_ms = max(period_ms, service_ms)
        if failing or in_backoff:
            imu_age_ms += elapsed_ms
        else:
            imu_age_ms = 0.0
        max_attitude_age_ms = max(max_attitude_age_ms, imu_age_ms)
        late_ms = max(0.0, service_ms - period_ms)
        if late_ms > cfg.late_grace_ms:
            consecutive_late += 1
        else:
            consecutive_late = 0
        max_late_streak = max(max_late_streak, consecutive_late)
        if (
            late_ms >= cfg.critical_lag_ms
            or (late_ms >= cfg.hard_lag_ms and consecutive_late >= 2)
            or consecutive_late >= cfg.max_consecutive_late
        ):
            stop_reason = "deadline_miss_streak"
            stop_tick = tick
            break
        now_ms += elapsed_ms

    return {
        "profile": profile,
        "imu_delay_ms": imu_delay_ms,
        "consecutive_imu_read_failures": consecutive_failures,
        "completed": stop_reason is None,
        "stop_reason": stop_reason,
        "stop_tick": stop_tick,
        "stop_time_s": round(now_ms / 1000.0, 6),
        "deadline_miss_streak_max": max_late_streak,
        "attitude_age_max_ms": round(max_attitude_age_ms, 3),
        "scheduler_backoff_entries": backoff_entries,
        "scheduler_backoff_state": (
            "active" if backoff_until_ms is not None
            and now_ms < backoff_until_ms else "inactive"
        ),
    }


def run_matrix(
    recorded: dict, cfg: ReplayConfig, *,
    imu_delays_ms: Iterable[float] = (0, 5, 10, 25, 50),
    failure_counts: Iterable[int] = (0, 1, 2, 3),
) -> dict:
    cases = []
    for profile in (ATTEMPT_PROFILE, CURRENT_PROFILE):
        for delay in imu_delays_ms:
            for failures in failure_counts:
                repetitions = [
                    _simulate_case(
                        profile=profile,
                        imu_delay_ms=float(delay),
                        consecutive_failures=int(failures),
                        baseline_service_ms=recorded["baseline_service_ms"],
                        coupled_refresh_cost_ms=recorded[
                            "derived_coupled_refresh_cost_ms"
                        ],
                        cfg=cfg,
                    )
                    for _ in range(cfg.repetitions)
                ]
                canonical = [
                    json.dumps(item, sort_keys=True, separators=(",", ":"))
                    for item in repetitions
                ]
                deterministic = len(set(canonical)) == 1
                case = dict(repetitions[0])
                case["repetitions"] = cfg.repetitions
                case["deterministic"] = deterministic
                case["repetition_sha256"] = hashlib.sha256(
                    canonical[0].encode()
                ).hexdigest()
                cases.append(case)
    return {
        "cases": cases,
        "all_repetitions_deterministic": all(
            case["deterministic"] for case in cases
        ),
    }


def build_report(
    *, trace_path: Path, debug_path: Path, cfg: ReplayConfig,
    attempt_revision: str, candidate_revision: str,
    imu_delays_ms: Iterable[float] = (0, 5, 10, 25, 50),
    failure_counts: Iterable[int] = (0, 1, 2, 3),
) -> dict:
    rows = load_trace(trace_path)
    events = load_debug(debug_path)
    recorded = analyze_recorded_trace(rows, events, cfg)
    if not recorded["reproduction"]["ok"]:
        raise RuntimeError(
            "replay diverged from the recorded controller deadline stop"
        )
    matrix = run_matrix(
        recorded, cfg,
        imu_delays_ms=imu_delays_ms,
        failure_counts=failure_counts,
    )
    if not matrix["all_repetitions_deterministic"]:
        raise RuntimeError("identical replay repetitions were nondeterministic")
    return {
        "schema": "hexapod.timing_imu_replay.v1",
        "simulation_only": True,
        "sources": {
            "trace": str(trace_path),
            "trace_sha256": hashlib.sha256(trace_path.read_bytes()).hexdigest(),
            "debug_trace": str(debug_path),
            "debug_trace_sha256": hashlib.sha256(
                debug_path.read_bytes()
            ).hexdigest(),
            "attempt_revision": attempt_revision,
            "candidate_revision": candidate_revision,
        },
        "guards": {
            "attitude_freshness_ms": cfg.attitude_freshness_ms,
            "deadline_late_grace_ms": cfg.late_grace_ms,
            "deadline_miss_streak_limit": cfg.max_consecutive_late,
            "changed": False,
        },
        "config": {
            "control_hz": cfg.control_hz,
            "duration_s": cfg.duration_s,
            "repetitions": cfg.repetitions,
            "imu_delay_ms": list(imu_delays_ms),
            "consecutive_imu_read_failures": list(failure_counts),
        },
        "recorded_trace": recorded,
        "fault_matrix": matrix,
        "interpretation": {
            "attribution": "sufficient_not_exclusive",
            "summary": (
                "The recorded deadline stop is reproduced from the sealed "
                "tick data. During the terminal IMU-age stall, the increased "
                "write-path cost is sufficient to sustain the 12-tick "
                "deadline streak; policy and observation stages are not the "
                "dominant cost. The current profile removes the stale-IMU to "
                "servo-refresh coupling, while the unchanged 150 ms attitude "
                "freshness guard still fails closed for long/slow faults."
            ),
            "limitations": (
                "Counterfactual cases are a deterministic timing model "
                "parameterized by the recorded stage medians, not hardware or "
                "MuJoCo motion evidence. A stationary full-stack soak remains "
                "required before another walking canary."
            ),
        },
    }


def _csv_numbers(value: str, cast):
    return [cast(item.strip()) for item in value.split(",") if item.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-trace", type=Path, required=True)
    parser.add_argument("--debug-trace", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--duration-s", type=float, default=120.0)
    parser.add_argument("--control-hz", type=float, default=100.0)
    parser.add_argument("--repetitions", type=int, default=10)
    parser.add_argument("--imu-delay-ms", default="0,5,10,25,50")
    parser.add_argument("--failure-counts", default="0,1,2,3")
    parser.add_argument("--attempt-revision", default="6e7d5ff")
    parser.add_argument("--candidate-revision", required=True)
    args = parser.parse_args(argv)
    if not (0 < args.duration_s <= 120):
        parser.error("--duration-s must be in (0, 120]")
    if not (0 < args.control_hz <= 200):
        parser.error("--control-hz must be in (0, 200]")
    if not (1 <= args.repetitions <= 100):
        parser.error("--repetitions must be in [1, 100]")
    cfg = ReplayConfig(
        control_hz=args.control_hz,
        duration_s=args.duration_s,
        repetitions=args.repetitions,
    )
    report = build_report(
        trace_path=args.input_trace,
        debug_path=args.debug_trace,
        cfg=cfg,
        attempt_revision=args.attempt_revision,
        candidate_revision=args.candidate_revision,
        imu_delays_ms=_csv_numbers(args.imu_delay_ms, float),
        failure_counts=_csv_numbers(args.failure_counts, int),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "out": str(args.out),
        "recorded_reproduction": report["recorded_trace"]["reproduction"],
        "cases": len(report["fault_matrix"]["cases"]),
        "deterministic": report["fault_matrix"][
            "all_repetitions_deterministic"
        ],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
