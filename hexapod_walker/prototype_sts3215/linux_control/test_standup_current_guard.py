"""Off-robot tests for the stand-up over-current guard's plausibility bound.

Run locally:  uv run python linux_control/test_standup_current_guard.py
No hardware: a FakeBus returns scripted feedback dicts.

Covers the 09-09 defect (experiment 922434955b): a stand-up self-aborted
on a 106.50 A reading — 16384 raw counts, 0x4000, one flipped bit at
6.5 mA/count — while the run's true peak was 2.88 A. An STS3215 stalls
at 2.70 A, so no honest per-servo reading gets near the ceiling here.
"""
from __future__ import annotations

import sys

from feetech_bus import N_JOINTS, joint_to_servo_id
from inplace_demos import (IMPLAUSIBLE_CURRENT_A, IMPLAUSIBLE_FAULT_READS,
                           CurrentPeakTracker)

LIVE = {joint_to_servo_id(j) for j in range(N_JOINTS)}

# The exact corrupted reading from experiment 922434955b: 16384 counts
# at the bus's 6.5 mA/count scale.
CORRUPT_A = 16384 * 0.0065


class FakeBus:
    """Returns whatever per-joint currents the test scripts."""

    def __init__(self, currents: dict[int, float], *, speed_deg_s=0.0, deg=0.0):
        self.currents = currents
        self.speed_deg_s = speed_deg_s
        self.deg = deg

    def read_feedback(self, joint: int) -> dict:
        return {"joint": joint,
                "current_a": self.currents.get(joint, 0.1),
                "speed_deg_s": self.speed_deg_s,
                "deg": self.deg}


def test_corrupt_sample_stays_out_of_peak():
    """One 106.50 A bit-flip must not become the run's peak."""
    t = CurrentPeakTracker()
    t.sample(FakeBus({0: 2.88}), LIVE)
    t.sample(FakeBus({0: CORRUPT_A}), LIVE)
    assert t.peak_a == 2.88, t.peak_a
    assert t.discarded == 1, t.discarded
    assert t.discarded_peak_a == CORRUPT_A
    assert t.telemetry_fault_joint is None


def test_corrupt_sample_does_not_latch_the_sweep_peak():
    """peak_a is monotonic; sweep_peak_a() must follow the live sweep."""
    t = CurrentPeakTracker()
    t.sample(FakeBus({0: 3.5}), LIVE)
    assert t.sweep_peak_a()[0] == 3.5
    t.sample(FakeBus({0: 0.4}), LIVE)
    assert t.peak_a == 3.5, "running max should remember the real spike"
    assert t.sweep_peak_a()[0] == 0.4, "live sweep should have moved on"


def test_persistent_corruption_escalates_to_a_telemetry_fault():
    """Three in a row on one joint is a real fault, not a flipped bit."""
    t = CurrentPeakTracker()
    bus = FakeBus({4: CORRUPT_A})
    for _ in range(IMPLAUSIBLE_FAULT_READS):
        t.sample(bus, LIVE)
    assert t.telemetry_fault_joint == 4, t.telemetry_fault_joint


def test_a_plausible_read_resets_the_fault_streak():
    """Scattered single bit-flips must never accumulate into a fault."""
    t = CurrentPeakTracker()
    corrupt, clean = FakeBus({4: CORRUPT_A}), FakeBus({4: 1.2})
    for _ in range(IMPLAUSIBLE_FAULT_READS * 3):
        t.sample(corrupt, LIVE)
        t.sample(clean, LIVE)
    assert t.telemetry_fault_joint is None
    assert t.discarded == IMPLAUSIBLE_FAULT_READS * 3


def test_real_over_current_is_still_seen():
    """The ceiling must not weaken the guard for honest currents."""
    t = CurrentPeakTracker()
    t.sample(FakeBus({2: 5.0}), LIVE)
    assert t.discarded == 0, "5.0 A is physically possible — keep it"
    assert t.peak_a == 5.0
    assert t.sweep_peak_a() == (5.0, 2), t.sweep_peak_a()


def test_ceiling_sits_above_stall_and_below_the_corrupt_read():
    """The bound has to separate the two cases it exists to separate."""
    assert 2.70 < IMPLAUSIBLE_CURRENT_A < CORRUPT_A


def test_implausible_joints_tracks_the_current_sweep_only():
    """The guard skips corrupt joints per sweep, not permanently."""
    t = CurrentPeakTracker()
    t.sample(FakeBus({3: CORRUPT_A}), LIVE)
    assert t.implausible_joints == {3}
    t.sample(FakeBus({3: 0.9}), LIVE)
    assert t.implausible_joints == set()


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in fns:
        try:
            fn()
            print(f"  ok    {name}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {name}: {e}")
    print(f"{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)


def test_sweep_total_tracks_bus_current_and_ignores_corrupt_samples():
    """2026-09-21: 18 servos at ~0.5 A each folded the shared supply (9 A)
    with no single servo over 2.2 A -- the guard needs the sweep TOTAL."""
    t = CurrentPeakTracker()
    t.sample(FakeBus({j: 0.5 for j in range(N_JOINTS)}), LIVE)
    assert abs(t.sweep_total_a() - 9.0) < 1e-9, t.sweep_total_a()
    assert abs(t.peak_total_a - 9.0) < 1e-9
    # a corrupt reading is excluded from the total, not summed
    t.sample(FakeBus({0: CORRUPT_A}), LIVE)
    assert abs(t.sweep_total_a() - 17 * 0.1) < 1e-9, t.sweep_total_a()
    # peak_total_a is a running max; the live total has moved on
    assert abs(t.peak_total_a - 9.0) < 1e-9
    assert t.peak_a == 0.5


def test_motion_guard_two_sweep_rules_and_messages():
    """MotionGuard is the one guard every scripted loop uses (2026-09-22)."""
    from inplace_demos import MotionGuard
    # summed current while STILL: one sweep over is not a trip, two are
    t = CurrentPeakTracker(); g = MotionGuard(t, stall_a=3.0, total_cap_a=6.0)
    t.sample(FakeBus({j: 0.5 for j in range(N_JOINTS)}), LIVE); assert g.check() is False
    t.sample(FakeBus({j: 0.5 for j in range(N_JOINTS)}), LIVE); assert g.check() is True
    assert g.trip_kind == "total" and "summed servo current" in g.message()
    assert g.check() is True, "latched"
    # the same 9 A while the legs MOVE is an honest loaded push (hexapod2 STEP rise 2026-09-22): no trip
    t = CurrentPeakTracker(); g = MotionGuard(t, stall_a=3.0, total_cap_a=6.0)
    for _ in range(4):
        t.sample(FakeBus({j: 0.5 for j in range(N_JOINTS)}, speed_deg_s=30.0), LIVE); assert g.check() is False
    # ...until the absolute cap: 18 x 0.9 A = 16 A moving still trips
    t.sample(FakeBus({j: 0.9 for j in range(N_JOINTS)}, speed_deg_s=30.0), LIVE); assert g.check() is False
    t.sample(FakeBus({j: 0.9 for j in range(N_JOINTS)}, speed_deg_s=30.0), LIVE); assert g.check() is True and g.trip_kind == "total"
    # hard cap: a single corrupt-looking 4.5 A sweep does not trip; two do
    # (FakeBus idles the other 17 joints at 0.1 A = 1.7 A, so lift the total cap out of the way here)
    t = CurrentPeakTracker(); g = MotionGuard(t, total_cap_a=20.0)
    t.sample(FakeBus({2: 4.5}), LIVE); assert g.check() is False
    t.sample(FakeBus({2: 0.2}), LIVE); assert g.check() is False
    t.sample(FakeBus({2: 4.5}), LIVE); t.sample(FakeBus({2: 4.5}), LIVE)
    g2 = MotionGuard(t, total_cap_a=20.0); t.sample(FakeBus({2: 4.5}), LIVE); g2.check(); t.sample(FakeBus({2: 4.5}), LIVE)
    assert g2.check() is True and g2.trip_kind == "cap"
    # stall: 3.2 A while still, two sweeps -> stall; while moving -> honest work
    t = CurrentPeakTracker(); g = MotionGuard(t, stall_a=3.0, total_cap_a=20.0)
    t.sample(FakeBus({5: 3.2}, speed_deg_s=0.0), LIVE); assert g.check() is False
    t.sample(FakeBus({5: 3.2}, speed_deg_s=0.0), LIVE); assert g.check() is True and g.trip_kind == "stall"
    t = CurrentPeakTracker(); g = MotionGuard(t, stall_a=3.0, total_cap_a=20.0)
    for _ in range(3):
        t.sample(FakeBus({5: 3.2}, speed_deg_s=60.0), LIVE); assert g.check() is False


def test_motion_guard_judges_motion_by_position_progress():
    """A slow loaded push reads < 8 deg/s on the speed register but the joints advance
    several degrees per sweep: that is work, not a fight.  Same current with the
    positions frozen is a jam."""
    from inplace_demos import MotionGuard
    t = CurrentPeakTracker(); g = MotionGuard(t, total_cap_a=6.0)
    for k in range(4):                                  # 9 A, speed register ~0, positions advancing 5 deg/sweep
        t.sample(FakeBus({j: 0.5 for j in range(N_JOINTS)}, speed_deg_s=1.0, deg=5.0 * k), LIVE)
        assert g.check() is False, k
    t.sample(FakeBus({j: 0.5 for j in range(N_JOINTS)}, speed_deg_s=1.0, deg=15.0), LIVE)   # stopped advancing
    assert g.check() is False                            # first still sweep: not yet
    t.sample(FakeBus({j: 0.5 for j in range(N_JOINTS)}, speed_deg_s=1.0, deg=15.0), LIVE)
    assert g.check() is True and g.trip_kind == "total"
