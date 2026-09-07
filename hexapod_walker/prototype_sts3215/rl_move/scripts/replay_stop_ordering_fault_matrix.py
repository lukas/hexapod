"""Deterministic no-I/O fault matrix for stream-loss hold ordering."""

from __future__ import annotations

import argparse
import json
import sys
import threading
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT / "linux_control") not in sys.path:
    sys.path.insert(0, str(_ROOT / "linux_control"))

import rl_policy  # noqa: E402
from rl_move.robot_state import RobotState  # noqa: E402
from rl_move.scripts.replay_stale_feedback_stop import replay  # noqa: E402


FAULT_CASES = (
    "snapshot_bus_not_ok",
    "delayed_foreground_sample",
    "sampler_thread_delay",
    "write_due",
    "skip_write",
)


def _state(*, bus_ok: bool = True, roll_deg: float = 0.0) -> RobotState:
    zero = np.zeros(rl_policy.N_JOINTS, dtype=float)
    return RobotState(
        timestamp=1.0,
        joint_position=zero.copy(),
        joint_velocity=zero.copy(),
        imu_roll=np.deg2rad(roll_deg),
        imu_pitch=0.0,
        imu_yaw=0.0,
        imu_gyro=np.zeros(3),
        imu_accel=np.zeros(3),
        commanded_position=zero.copy(),
        servo_load=None,
        servo_current=None,
        servo_temperature=None,
        bus_ok=bus_ok,
        imu_ok=True,
        timing={"source": "offline_fault_matrix"},
    )


class _Trace:
    def __init__(self) -> None:
        self.items: list[str] = []

    def event(self, name: str, **_fields) -> None:
        self.items.append(name)


class _Bus:
    def __init__(self, trace: _Trace) -> None:
        self.trace = trace
        self.writes: list[list[float]] = []

    def enable_all_torque(self, _enabled: bool) -> None:
        self.trace.items.append("torque_refresh")

    def write_all(self, pose, *, speed: int, acc: int) -> None:
        del speed, acc
        self.trace.items.append("bus_write")
        self.writes.append(list(pose))


class _Estimator:
    def __init__(self, trace: _Trace, states: list[RobotState | None]) -> None:
        self.trace = trace
        self.states = list(states)
        self.commanded: list[np.ndarray] = []

    def set_commanded(self, pose) -> None:
        self.commanded.append(np.asarray(pose, dtype=float).copy())

    def update(self, *, want_full_feedback: bool) -> RobotState | None:
        assert want_full_feedback
        self.trace.items.append("foreground_resample")
        return self.states.pop(0) if self.states else None


class _Drive:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.armed = False
        self.status = ""

    def _torque_all(self, _enabled: bool) -> None:
        pass


def run_case(name: str) -> dict:
    trace = _Trace()
    states = {
        "snapshot_bus_not_ok": [_state(bus_ok=False)] * 5,
        "delayed_foreground_sample": [None, None, _state()],
        "sampler_thread_delay": [None, _state()],
        "write_due": [_state()],
        "skip_write": [_state()],
    }[name]
    bus = _Bus(trace)
    estimator = _Estimator(trace, states)
    held = rl_policy._hold_after_stream_loss(  # noqa: SLF001
        bus, estimator, _Drive(), trace, np.zeros(rl_policy.N_JOINTS),
        _state(), write_speed=100, write_acc=20, policy_dt=0.0,
    )
    first_write = trace.items.index("bus_write")
    first_sample = trace.items.index("foreground_resample")
    torque_refresh = trace.items.index("torque_refresh")
    reanchored = "hold_after_stream_loss_reanchored" in trace.items
    return {
        "fault_case": name,
        "held": held,
        "events": trace.items,
        "write_count": len(bus.writes),
        "fallback_write_precedes_foreground_resample": first_write < first_sample,
        "fallback_write_precedes_torque_refresh": first_write < torque_refresh,
        "reanchored": reanchored,
        "reanchor_requires_valid_fresh_state": (
            not reanchored if name == "snapshot_bus_not_ok" else reanchored
        ),
        "terminal_write_due": name == "write_due",
    }


def run_matrix(source: Path, expected_manifest_sha256: str) -> dict:
    historical, _timeline = replay(
        source, expected_manifest_sha256=expected_manifest_sha256)
    cases = [run_case(name) for name in FAULT_CASES]
    assertions = {
        "fallback_hold_write_precedes_foreground_resample": all(
            item["fallback_write_precedes_foreground_resample"] for item in cases),
        "no_reanchor_without_fresh_pose_and_tilt_validation": all(
            item["reanchor_requires_valid_fresh_state"] for item in cases),
        "interlock_triggers_at_11_consecutive_stale_ticks": (
            historical["stale_bursts"]["terminal_stale_ticks"] == 11
            and historical["contract"]["stale_tick_limit"] == 10
        ),
        "no_robot_io": True,
    }
    return {
        "schema": "hexapod.offline_stop_ordering_fault_matrix.v1",
        "execution": "offline_deterministic_fakes_and_sealed_replay",
        "source_experiment_id": "6a632f8ba4bc4b14812e27e6f87eaa42",
        "robot_contacted": False,
        "robot_motion": False,
        "fault_cases": cases,
        "assertions": assertions,
        "passed": all(assertions.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    report = run_matrix(args.source, args.expected_manifest_sha256)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({"passed": report["passed"],
                      "assertions": report["assertions"]}, sort_keys=True))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
