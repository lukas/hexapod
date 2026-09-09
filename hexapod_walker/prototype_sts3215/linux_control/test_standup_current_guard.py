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

    def __init__(self, currents: dict[int, float], *, speed_deg_s=0.0):
        self.currents = currents
        self.speed_deg_s = speed_deg_s

    def read_feedback(self, joint: int) -> dict:
        return {"joint": joint,
                "current_a": self.currents.get(joint, 0.1),
                "speed_deg_s": self.speed_deg_s,
                "deg": 0.0}


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
