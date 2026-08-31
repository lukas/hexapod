"""Regression tests for scripted Drive-tab walk readiness.

No hardware: FakeBus only reports encoder positions. The tests lock the
operator-facing path where an armed-but-not-standing robot must not start a
basic tripod gait from a low/sit pose.
"""
from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from drive_controller import (  # noqa: E402
    DEMO_TRIPOD_LIFT_M,
    DEMO_TRIPOD_MAX_OMEGA_RAD_S,
    DEMO_TRIPOD_MAX_VX_MPS,
    DEMO_TRIPOD_MAX_VY_MPS,
    DEMO_TRIPOD_PERIOD_S,
    DEMO_TRIPOD_STRIDE_SCALE,
    DriveController, SIM_WALK_START_HIP_DEG, SIM_WALK_START_KNEE_DEG,
    walk_start_pose_degrees,
)


class FakeBus:
    trims = [0.0] * 18

    def __init__(self, pose):
        self.pose = [float(x) for x in pose]

    def scan(self, ids):
        return list(ids)

    def read_all_positions(self):
        return {j: q for j, q in enumerate(self.pose)}


def test_default_scripted_gait_uses_tall_walk_ready_stance():
    drive = DriveController(dry_run=True)

    assert drive._last_pose == walk_start_pose_degrees()  # noqa: SLF001
    assert drive.gait.plant_hip_deg == SIM_WALK_START_HIP_DEG
    assert drive.gait.plant_knee_deg == SIM_WALK_START_KNEE_DEG
    assert drive.gait.period == DEMO_TRIPOD_PERIOD_S
    assert drive.gait.lift == DEMO_TRIPOD_LIFT_M
    assert drive.gait.stride_scale == DEMO_TRIPOD_STRIDE_SCALE


def test_moving_j_refuses_when_not_near_walk_ready_pose():
    drive = DriveController(dry_run=False)
    drive.bus = FakeBus([0.0] * 18)
    drive.armed = True

    result = drive.handle("J 30 0 0 0")

    assert result.startswith("refused walk: not at walk-ready pose")
    assert drive.mode == "idle"
    assert drive._vx == 0.0  # noqa: SLF001


def test_moving_j_starts_from_walk_ready_pose():
    drive = DriveController(dry_run=False)
    drive.bus = FakeBus(walk_start_pose_degrees())
    drive.armed = True

    result = drive.handle("J 30 0 0 0")

    assert result == "J"
    assert drive.mode == "walk"
    assert drive._vx == 0.03  # noqa: SLF001
    assert drive.gait.plant_knee_deg == SIM_WALK_START_KNEE_DEG


def test_j_can_select_gait_while_starting_from_stand():
    drive = DriveController(dry_run=False)
    drive.bus = FakeBus(walk_start_pose_degrees())
    drive.armed = True

    result = drive.handle("J 30 0 0 1")

    assert result == "J"
    assert drive.mode == "walk"
    assert drive._gait_id == 1  # noqa: SLF001


def test_basic_tripod_caps_full_stick_to_demo_safe_envelope():
    drive = DriveController(dry_run=False)
    drive.bus = FakeBus(walk_start_pose_degrees())
    drive.armed = True

    result = drive.handle("J 100 100 1.0 0")

    assert result == "J"
    assert drive._vx == DEMO_TRIPOD_MAX_VX_MPS  # noqa: SLF001
    assert drive._vy == DEMO_TRIPOD_MAX_VY_MPS  # noqa: SLF001
    assert drive._omega == DEMO_TRIPOD_MAX_OMEGA_RAD_S  # noqa: SLF001
