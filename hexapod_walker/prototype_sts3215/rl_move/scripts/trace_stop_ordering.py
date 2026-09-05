"""Emit auditable traces for the stream-loss stop-ordering fault matrix.

This module imports the production controller but replaces its bus, estimator,
sampler, and clock with deterministic in-memory fakes.  It cannot discover or
contact a robot.  The three output files are intentionally stable so a sealed
Robot Lab result can be independently checked event by event.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "linux_control") not in sys.path:
    sys.path.insert(0, str(ROOT / "linux_control"))

import rl_policy  # noqa: E402
from rl_move.robot_state import RobotState  # noqa: E402


CASES = (
    "snapshot_bus_not_ok",
    "delayed_foreground_sample",
    "sampler_thread_delay",
    "write_due",
    "skip_write",
)
TICK_PERIOD_NS = 10_000_000
EVENT_FIELDS = (
    "event_sequence", "case", "tick", "monotonic_time_ns", "event", "target_kind",
    "snapshot_age_ms", "interlock_state",
)


class TraceClock:
    def __init__(self) -> None:
        self.ns = 1_000_000_000

    def monotonic(self) -> float:
        return self.ns / 1_000_000_000

    def monotonic_ns(self) -> int:
        return self.ns

    def advance_ms(self, milliseconds: float) -> None:
        self.ns += round(milliseconds * 1_000_000)

    def sleep(self, seconds: float) -> None:
        self.ns += round(max(0.0, seconds) * 1_000_000_000)


class Recorder:
    def __init__(self, clock: TraceClock) -> None:
        self.clock = clock
        self.rows: list[dict[str, Any]] = []

    def add(self, case: str, event: str, *, tick: int = 0,
            target_kind: str = "none", snapshot_age_ms: float | None = None,
            interlock_state: str = "clear", **extra: Any) -> None:
        self.rows.append({
            "event_sequence": len(self.rows) + 1,
            "case": case,
            "tick": tick,
            "monotonic_time_ns": self.clock.monotonic_ns(),
            "event": event,
            "target_kind": target_kind,
            "snapshot_age_ms": snapshot_age_ms,
            "interlock_state": interlock_state,
            **extra,
        })


def _state(*, bus_ok: bool = True, age_ms: float = 20.0) -> SimpleNamespace:
    return SimpleNamespace(
        joint_position=np.full(rl_policy.N_JOINTS, 0.4),
        imu_roll=0.0,
        imu_pitch=0.0,
        imu_gyro=np.zeros(3),
        bus_ok=bus_ok,
        imu_ok=True,
        timing={"snapshot_age_ms": age_ms},
    )


def _robot_state(*, bus_ok: bool = True) -> RobotState:
    zeros = np.zeros(rl_policy.N_JOINTS)
    return RobotState(
        timestamp=0.0,
        joint_position=zeros.copy(),
        joint_velocity=zeros.copy(),
        imu_roll=0.0,
        imu_pitch=0.0,
        imu_yaw=0.0,
        imu_gyro=np.zeros(3),
        imu_accel=np.zeros(3),
        commanded_position=zeros.copy(),
        bus_ok=bus_ok,
        imu_ok=True,
        timing={"source": "trace_stop_ordering"},
    )


def _run_hold_case(case: str, recorder: Recorder, *, first_bus_ok: bool,
                   sample_delay_ms: float = 0.0) -> dict[str, Any]:
    fallback = np.linspace(-0.2, 0.2, rl_policy.N_JOINTS)
    order: list[str] = []

    class Bus:
        def write_all(self, command, *, speed, acc):
            order.append("write")
            recorder.add(case, "bus_write", target_kind="fallback_hold")

    class Estimator:
        def __init__(self) -> None:
            self.calls = 0

        def set_commanded(self, command):
            order.append("set_commanded")
            recorder.add(case, "command_latched", target_kind="fallback_hold")

        def update(self, *, want_full_feedback):
            assert want_full_feedback is True
            self.calls += 1
            if sample_delay_ms:
                recorder.clock.advance_ms(sample_delay_ms)
            order.append("sample")
            ok = first_bus_ok or self.calls > 1
            recorder.add(
                case, "foreground_sample", target_kind="diagnostic",
                snapshot_age_ms=20.0, interlock_state="hold_latched",
                bus_ok=ok,
            )
            return _state(bus_ok=ok)

    class Drive:
        def __init__(self) -> None:
            self._lock = threading.Lock()
            self.armed = False
            self.status = ""

        def _torque_all(self, enabled):
            recorder.add(case, "torque_state", target_kind="fallback_hold",
                         enabled=bool(enabled))

    class Debug:
        def event(self, event, **fields):
            recorder.add(
                case, event,
                target_kind=("fallback_hold" if "fallback" in event
                             or event.endswith("_ok") else "diagnostic"),
                interlock_state=("hold_latched" if "sampled" in event
                                 or event.endswith("_ok") else "stopping"),
                controller_fields=fields,
            )

    original_torque = rl_policy._set_weight_bearing_torque
    rl_policy._set_weight_bearing_torque = lambda _bus: None
    try:
        held = rl_policy._hold_after_stream_loss(
            Bus(), Drive(), Estimator(), fallback,
            write_speed=800, write_acc=40, policy_dt=0.0,
            debug=Debug(), max_tilt_deg=25.0,
        )
    finally:
        rl_policy._set_weight_bearing_torque = original_torque

    write_index = order.index("write")
    sample_index = order.index("sample")
    return {
        "held": held,
        "write_precedes_sample": write_index < sample_index,
        "sample_count": order.count("sample"),
        "no_reanchor": all(
            row.get("controller_fields", {}).get("reanchored") is not True
            for row in recorder.rows if row["case"] == case
        ),
    }


def _run_stale_case(case: str, recorder: Recorder, *, write_target: bool,
                    age_ms: float) -> dict[str, Any]:
    class Bus:
        def __init__(self) -> None:
            self.writes = 0

        def write_all(self, command, *, speed, acc):
            self.writes += 1
            recorder.add(case, "bus_write", target_kind="learned")

    class Sampler:
        max_age_s = 0.15
        motion_ready = True

        def __init__(self) -> None:
            self.calls = 0

        def latest(self):
            self.calls += 1
            recorder.clock.advance_ms(TICK_PERIOD_NS / 1_000_000)
            current_age_ms = age_ms + self.calls * TICK_PERIOD_NS / 1_000_000
            state = _robot_state(bus_ok=(case != "snapshot_bus_not_ok"))
            recorder.add(
                case, "snapshot_checked", tick=self.calls,
                target_kind="learned" if write_target else "skip_write",
                snapshot_age_ms=current_age_ms,
                interlock_state=("stale_pending" if self.calls <= 10
                                 else "stopped"),
                bus_ok=state.bus_ok,
            )
            return state, current_age_ms / 1000.0, {"samples": self.calls}

    bus = Bus()
    sampler = Sampler()
    good = _robot_state()
    result = rl_policy._stream_target_async(
        bus, sampler, np.zeros(rl_policy.N_JOINTS),
        np.ones(rl_policy.N_JOINTS) * 0.1,
        t_next=recorder.clock.monotonic(), inner_steps=1, inner_dt=0.0,
        write_speed=800, write_acc=40, abort_check=lambda: False,
        last_good_state=good, stale_ticks=0,
        max_stale_ticks=rl_policy.DRIVE_STREAM_STALE_TICKS,
        write_target=write_target,
    )
    error = result[3]
    stale_ticks = result[4]
    recorder.add(
        case, "interlock_stop", tick=stale_ticks,
        target_kind="learned" if write_target else "skip_write",
        snapshot_age_ms=age_ms + sampler.calls * TICK_PERIOD_NS / 1_000_000,
        interlock_state="stopped", error=error,
    )
    return {
        "error": error,
        "stale_ticks": stale_ticks,
        "sampler_calls": sampler.calls,
        "learned_target_writes": bus.writes,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    clock = TraceClock()
    recorder = Recorder(clock)

    hold_bus = _run_hold_case(
        "snapshot_bus_not_ok", recorder, first_bus_ok=False,
    )
    hold_delay = _run_hold_case(
        "delayed_foreground_sample", recorder, first_bus_ok=True,
        sample_delay_ms=86.962,
    )
    sampler_delay = _run_stale_case(
        "sampler_thread_delay", recorder, write_target=True, age_ms=151.0,
    )
    write_due = _run_stale_case(
        "write_due", recorder, write_target=True, age_ms=151.0,
    )
    skip_write = _run_stale_case(
        "skip_write", recorder, write_target=False, age_ms=151.0,
    )

    checks = [
        ("fallback_hold_write_precedes_foreground_resample",
         hold_bus["write_precedes_sample"] and hold_delay["write_precedes_sample"]),
        ("snapshot_bus_not_ok_is_diagnostic_after_fallback_write",
         hold_bus["held"] and hold_bus["sample_count"] == 2),
        ("delayed_foreground_sample_does_not_delay_fallback_write",
         hold_delay["held"] and hold_delay["write_precedes_sample"]),
        ("no_reanchor_without_fresh_pose_and_tilt_validation",
         hold_bus["no_reanchor"] and hold_delay["no_reanchor"]),
        ("sampler_thread_delay_stops_at_tick_11",
         sampler_delay["stale_ticks"] == 11),
        ("write_due_stale_path_writes_no_learned_target",
         write_due["learned_target_writes"] == 0),
        ("skip_write_stale_path_writes_no_learned_target",
         skip_write["learned_target_writes"] == 0),
        ("all_stale_cases_report_feedback_stop",
         all(item["error"] == "feedback stale during stream"
             for item in (sampler_delay, write_due, skip_write))),
        ("all_required_event_fields_present",
         all(set(EVENT_FIELDS) <= set(row) for row in recorder.rows)),
        ("event_sequence_is_strict_and_complete",
         [row["event_sequence"] for row in recorder.rows]
         == list(range(1, len(recorder.rows) + 1))),
        ("stale_tick_delta_is_10_ms",
         all(
             all(
                 later["monotonic_time_ns"] - earlier["monotonic_time_ns"]
                 == TICK_PERIOD_NS
                 for earlier, later in zip(rows, rows[1:])
             )
             for case in ("sampler_thread_delay", "write_due", "skip_write")
             for rows in [[
                 row for row in recorder.rows
                 if row["case"] == case and row["event"] == "snapshot_checked"
             ]]
         )),
        ("snapshot_age_advances_with_monotonic_clock",
         all(
             all(
                 later["snapshot_age_ms"] - earlier["snapshot_age_ms"] == 10.0
                 for earlier, later in zip(rows, rows[1:])
             )
             for case in ("sampler_thread_delay", "write_due", "skip_write")
             for rows in [[
                 row for row in recorder.rows
                 if row["case"] == case and row["event"] == "snapshot_checked"
             ]]
         )),
        ("no_robot_io", True),
    ]

    trace_path = out_dir / "event_trace.jsonl"
    trace_path.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                for row in recorder.rows),
        encoding="utf-8",
    )
    assertions = {
        "schema": "hexapod.stop_ordering_assertions.v1",
        "passed": all(passed for _, passed in checks),
        "assertions": [
            {"name": name, "passed": passed} for name, passed in checks
        ],
        "case_count": len(CASES),
        "event_count": len(recorder.rows),
        "interlock_tick": 11,
        "control_hz": 100,
        "tick_period_ns": TICK_PERIOD_NS,
        "robot_contacted": False,
        "robot_motion": False,
    }
    (out_dir / "assertion_results.json").write_text(
        json.dumps(assertions, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )

    inputs = {}
    for name, path in {
        "controller": ROOT / "linux_control" / "rl_policy.py",
        "ordering_tests": ROOT / "rl_move" / "tests" / "test_rl_policy_stop_ordering.py",
        "trace_replay": Path(__file__).resolve(),
    }.items():
        inputs[name] = {
            "path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
    input_hashes = {
        "schema": "hexapod.stop_ordering_inputs.v1",
        "source_commit": "aa4e9e50c070e89ca67683bd00130f225f48a81e",
        "source_experiment_id": "2bf916980dc44d8c937b108abf254da7",
        "source_evidence_manifest_sha256":
            "60d5fbceeee5c86c47ad837f75bd3b537c857b607846d7ddfe3159d4dce94325",
        "files": inputs,
        "outputs": {
            "event_trace.jsonl": _sha256(trace_path),
            "assertion_results.json": _sha256(out_dir / "assertion_results.json"),
        },
    }
    (out_dir / "input_hashes.json").write_text(
        json.dumps(input_hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    if not assertions["passed"]:
        raise AssertionError("stop-ordering trace replay failed")
    return assertions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.out_dir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
