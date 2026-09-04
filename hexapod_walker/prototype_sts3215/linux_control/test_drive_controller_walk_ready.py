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
    DT, DriveController, SIM_WALK_START_HIP_DEG, SIM_WALK_START_KNEE_DEG,
    _advance_periodic_deadline,
    walk_start_pose_degrees,
)
from hexapod_core.scripted_walk_contract import (  # noqa: E402
    SCRIPTED_WALK_ACC_UNITS,
    SCRIPTED_WALK_CONTROL_HZ,
    SCRIPTED_WALK_SPEED_COUNTS_S,
)
from hexapod_core.middle_tuck_quad_gait import TUCK_DEG  # noqa: E402


class FakeBus:
    trims = [0.0] * 18

    def __init__(self, pose):
        self.pose = [float(x) for x in pose]
        self.scan_calls = 0

    def scan(self, ids):
        self.scan_calls += 1
        return list(ids)

    def read_all_positions(self):
        return {j: q for j, q in enumerate(self.pose)}


def test_scripted_walk_uses_shared_100hz_raised_profile_contract():
    assert SCRIPTED_WALK_CONTROL_HZ == 100.0
    assert DT == 0.01
    assert SCRIPTED_WALK_SPEED_COUNTS_S == 2000
    assert SCRIPTED_WALK_ACC_UNITS == 80
    state = DriveController(dry_run=True).scripted_contract_state()
    assert state == {
        "control_hz": 100.0,
        "servo_speed_counts_s": 2000,
        "servo_acc_units": 80,
        "deadline_overruns": 0,
    }


def test_scripted_deadline_scheduler_does_not_accumulate_work_time():
    deadline, skipped = _advance_periodic_deadline(10.0, 10.002)
    assert deadline == 10.01
    assert skipped == 0

    deadline, skipped = _advance_periodic_deadline(deadline, 10.035)
    assert abs(deadline - 10.04) < 1e-12
    assert skipped == 2


def test_walk_loop_can_reuse_verified_live_id_cache_without_scan():
    drive = DriveController(dry_run=False)
    bus = FakeBus(walk_start_pose_degrees())
    drive.bus = bus
    drive._live_ids_cache = set(range(2, 20))  # noqa: SLF001
    drive._live_ids_t = 0.0  # deliberately expired  # noqa: SLF001

    assert drive._live_ids(allow_stale=True) == set(range(2, 20))  # noqa: SLF001
    assert bus.scan_calls == 0
    assert drive._live_ids() == set(range(2, 20))  # noqa: SLF001
    assert bus.scan_calls == 1


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


def test_gait1_accepts_raised_60mm_s_envelope_only_for_gait1():
    drive = DriveController(dry_run=False)
    drive.bus = FakeBus(walk_start_pose_degrees())
    drive.armed = True

    assert drive.handle("J 60 0 0 1") == "J"
    assert drive._vx == 0.060  # noqa: SLF001
    assert drive.gait.max_vx == 0.060
    assert drive.gait.stride_max == 0.192

    fluid_drive = DriveController(dry_run=True)
    assert "FLUID" in fluid_drive.handle("GAIT 9")
    assert fluid_drive.gait.max_vx == fluid_drive.gait.MAX_VX == 0.040
    assert fluid_drive.gait.stride_max == fluid_drive.gait.STRIDE_MAX == 0.080


def test_neutral_j_after_walk_enters_quiet_hold_not_stand_pulse():
    drive = DriveController(dry_run=True)
    drive.armed = True

    assert drive.handle("J 30 0 0 0") == "J"
    assert drive.mode == "walk"

    assert drive.handle("J 0 0 0 0") == "J"

    assert drive.mode == "idle"
    assert drive._vx == 0.0  # noqa: SLF001
    assert drive._vy == 0.0  # noqa: SLF001
    assert drive._omega == 0.0  # noqa: SLF001
    assert "quiet hold" in drive.status


def test_settle_keeps_gait_loop_live_and_zeroes_velocity():
    drive = DriveController(dry_run=True)
    drive.armed = True
    assert drive.handle("GAIT 14").startswith("gait")
    assert drive.handle("J 30 0 0 14") == "J"

    response = drive.handle("GAITSTOP")

    assert response == "gaitstop_s=4.475"
    assert drive.mode == "walk"
    assert drive._vx == drive._vy == drive._omega == 0.0  # noqa: SLF001
    assert drive.gait.vx == drive.gait.vy == drive.gait.omega == 0.0


def test_fluid_gait_settle_reaches_motionless_neutral_stance():
    drive = DriveController(dry_run=True)
    drive.armed = True
    assert drive.handle("GAIT 14").startswith("gait")
    assert drive.handle("J 30 0 0 14") == "J"
    gait = drive.gait
    for tick in range(601):
        gait.desired_deg(tick / 100.0)
    assert drive.handle("GAITSTOP") == "gaitstop_s=4.475"
    for tick in range(602, 1101):
        settled = gait.desired_deg(tick / 100.0)
    later = gait.desired_deg(11.5)
    goal = walk_start_pose_degrees()
    assert max(abs(a - b) for a, b in zip(settled, goal)) < 0.01
    assert max(abs(a - b) for a, b in zip(later, settled)) < 0.01


def test_basic_tripod_caps_full_stick_to_demo_safe_envelope():
    drive = DriveController(dry_run=False)
    drive.bus = FakeBus(walk_start_pose_degrees())
    drive.armed = True

    result = drive.handle("J 100 100 1.0 0")

    assert result == "J"
    assert drive._vx == DEMO_TRIPOD_MAX_VX_MPS  # noqa: SLF001
    assert drive._vy == DEMO_TRIPOD_MAX_VY_MPS  # noqa: SLF001
    assert drive._omega == DEMO_TRIPOD_MAX_OMEGA_RAD_S  # noqa: SLF001


def test_gtune_updates_basic_tripod_params_and_caps():
    drive = DriveController(dry_run=True)

    result = drive.handle(
        "GTUNE period=1.95 lift=42 stride=0.75 ramp=0.90 "
        "vx=35 vy=21 omega=0.40")

    assert result.startswith("GTUNE")
    assert drive.gait.period == 1.95
    assert drive.gait.lift == 0.042
    assert drive.gait.stride_scale == 0.75
    assert drive.gait.ramp == 0.90
    assert drive._caps_for_gait(0) == (0.035, 0.021, 0.40)  # noqa: SLF001


def test_gtune_refuses_while_basic_tripod_is_walking():
    drive = DriveController(dry_run=False)
    drive.bus = FakeBus(walk_start_pose_degrees())
    drive.armed = True

    assert drive.handle("J 30 0 0 0") == "J"
    result = drive.handle("GTUNE stride=0.75")

    assert result.startswith("refused GTUNE while walking")
    assert drive.gait.stride_scale == DEMO_TRIPOD_STRIDE_SCALE


def test_clampfit_gait_id_selects_smooth_noslip_tripod():
    drive = DriveController(dry_run=True)

    result = drive.handle("GAIT 7")

    assert "CLAMP-FIT" in result
    assert drive._gait_id == 7  # noqa: SLF001
    assert drive.gait.period == 6.0
    assert drive.gait.lift == 0.020
    assert drive.gait.alpha == 1.0


def test_middle_tuck_quad_gait_id_tucks_middle_legs_with_ramp():
    drive = DriveController(dry_run=True)

    result = drive.handle("GAIT 8")

    assert "middle-tuck quad" in result
    assert drive._gait_id == 8  # noqa: SLF001
    q0 = drive.gait.desired_deg(0.0)
    q2 = drive.gait.desired_deg(2.0)
    for leg in (1, 4):
        off = 3 * leg
        assert q0[off:off + 3] == [
            0.0, SIM_WALK_START_HIP_DEG, SIM_WALK_START_KNEE_DEG]
        assert q2[off:off + 3] == list(TUCK_DEG)


def test_fluid_noslip_gait_id_uses_near_continuous_timing():
    drive = DriveController(dry_run=True)
    result = drive.handle("GAIT 9")
    assert "FLUID" in result
    assert drive._gait_id == 9  # noqa: SLF001
    assert drive.gait.alpha == 1.0
    assert drive.gait.period == 2.9
    assert abs(drive.gait.lift - 0.018) < 1e-12
    # Each half-cycle has only 2% shift and 0.5% dwell.
    assert abs(drive.gait._durations[0] / drive.gait.period - 0.02) < 1e-12
    assert abs(drive.gait._durations[2] / drive.gait.period - 0.005) < 1e-12


def test_fluid_fast_gait_id_raises_cadence_and_lowers_lift():
    drive = DriveController(dry_run=True)
    result = drive.handle("GAIT 10")
    assert "FLUID-FAST" in result
    assert drive._gait_id == 10  # noqa: SLF001
    assert drive.gait.alpha == 1.0
    assert drive.gait.period == 2.4
    assert abs(drive.gait.lift - 0.014) < 1e-12


def test_fluid_mid_gait_id_interpolates_cadence_and_lift():
    drive = DriveController(dry_run=True)
    result = drive.handle("GAIT 14")
    assert "FLUID-MID" in result
    assert drive._gait_id == 14  # noqa: SLF001
    assert drive.gait.alpha == 1.0
    assert drive.gait.period == 2.65
    assert abs(drive.gait.lift - 0.016) < 1e-12
    assert abs(drive.gait._durations[0] / drive.gait.period - 0.02) < 1e-12
    assert abs(drive.gait._durations[2] / drive.gait.period - 0.005) < 1e-12


def test_unknown_gait_id_is_refused_without_changing_gait():
    drive = DriveController(dry_run=True)
    assert "FLUID" in drive.handle("GAIT 9")
    gait = drive.gait

    result = drive.handle("GAIT 99")

    assert result == "refused unknown GAIT 99"
    assert drive._gait_id == 9  # noqa: SLF001
    assert drive.gait is gait


def test_fluid_hybrid_gait_id_retains_small_shift_impulse():
    drive = DriveController(dry_run=True)
    result = drive.handle("GAIT 11")
    assert "FLUID-HYBRID" in result
    assert drive._gait_id == 11  # noqa: SLF001
    assert drive.gait.alpha == 0.75
    assert drive.gait.period == 3.2
    assert abs(drive.gait._durations[0] / drive.gait.period - 0.08) < 1e-12
    assert abs(drive.gait._durations[1] / drive.gait.period - 0.40) < 1e-12


def test_fluid_push_gait_id_strengthens_short_shift_impulse():
    drive = DriveController(dry_run=True)
    result = drive.handle("GAIT 12")
    assert "FLUID-PUSH" in result
    assert drive._gait_id == 12  # noqa: SLF001
    assert drive.gait.alpha == 0.70
    assert drive.gait.period == 3.2
    assert abs(drive.gait._durations[0] / drive.gait.period - 0.12) < 1e-12
    assert abs(drive.gait._durations[1] / drive.gait.period - 0.36) < 1e-12


def test_fluid_pulse_gait_id_compresses_hybrid_shift():
    drive = DriveController(dry_run=True)
    result = drive.handle("GAIT 13")
    assert "FLUID-PULSE" in result
    assert drive._gait_id == 13  # noqa: SLF001
    assert drive.gait.alpha == 0.75
    assert drive.gait.period == 3.2
    assert abs(drive.gait._durations[0] / drive.gait.period - 0.06) < 1e-12
    assert abs(drive.gait._durations[1] / drive.gait.period - 0.42) < 1e-12
