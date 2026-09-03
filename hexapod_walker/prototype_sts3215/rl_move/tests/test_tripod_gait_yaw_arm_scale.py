"""TripodGait.combined_yaw_arm_scale unit tests (standwalk Next item 2,
candidate (i)-v2, 09-03) -- pure stdlib, no mujoco/env dependency.

See hexapod_core/tripod_gait.py's __init__ docstring for the full
derivation: this dose scales ONLY the atan2 denominator used to back
out the yaw SERVO ANGLE from a leg's true tangential foot displacement
(hip/knee IK keeps using the true, unscaled r_planar/z target), gated
to combined ticks (vx!=0 AND omega!=0) only.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "linux_control"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from hexapod_core.tripod_gait import TripodGait  # noqa: E402


def _make(scale=1.0):
    g = TripodGait(vx=0.0, combined_yaw_arm_scale=scale)
    g.sync_plant_stance(20.0, 100.0)
    g.reset_phase()
    return g


def test_default_is_bit_exact_identity():
    """No dose given: behaves exactly like a plain TripodGait."""
    ref = _make(1.0)
    dosed = TripodGait(vx=0.0)
    dosed.sync_plant_stance(20.0, 100.0)
    dosed.reset_phase()
    ref.set_velocity(vx=0.05, omega=0.2)
    dosed.set_velocity(vx=0.05, omega=0.2)
    for t in (0.0, 0.05, 0.1, 0.37, 1.2):
        assert ref.desired_deg(t) == dosed.desired_deg(t)


def test_scale_changes_only_combined_ticks():
    """scale=2.0 must diverge from scale=1.0 on a combined tick (vx!=0
    AND omega!=0) but be bit-identical on pure-turn and pure-walk."""
    plain = _make(1.0)
    dosed = _make(2.0)

    # pure turn: vx=0
    plain.set_velocity(vx=0.0, omega=0.25)
    dosed.set_velocity(vx=0.0, omega=0.25)
    for t in (0.05, 0.3, 0.7, 1.5):
        assert plain.desired_deg(t) == dosed.desired_deg(t), "pure-turn"

    plain = _make(1.0)
    dosed = _make(2.0)
    # pure walk: omega=0
    plain.set_velocity(vx=0.06, omega=0.0)
    dosed.set_velocity(vx=0.06, omega=0.0)
    for t in (0.05, 0.3, 0.7, 1.5):
        assert plain.desired_deg(t) == dosed.desired_deg(t), "pure-walk"

    plain = _make(1.0)
    dosed = _make(2.0)
    # combined: both nonzero -- must actually diverge somewhere
    plain.set_velocity(vx=0.08, omega=0.25)
    dosed.set_velocity(vx=0.08, omega=0.25)
    saw_diff = False
    for t in (0.05, 0.3, 0.7, 1.5, 2.3):
        a = plain.desired_deg(t)
        b = dosed.desired_deg(t)
        if a != b:
            saw_diff = True
        # only yaw channels (indices 0,3,6,9,12,15) may differ; hip/knee
        # (foot placement/lift) must be untouched by this knob.
        for leg in range(6):
            hip_i, knee_i = 3 * leg + 1, 3 * leg + 2
            assert abs(a[hip_i] - b[hip_i]) < 1e-9, "hip changed"
            assert abs(a[knee_i] - b[knee_i]) < 1e-9, "knee changed"
    assert saw_diff, "combined tick never diverged under scale=2.0"


def test_scale_shrinks_yaw_excursion_on_combined_tick():
    """The whole point: |yaw_scaled| <= |yaw_plain| (in magnitude, same
    sign) on a combined tick, for a scale > 1 that pushes atan2 toward
    its x-dominated (small-angle) regime."""
    plain = _make(1.0)
    dosed = _make(2.0)
    plain.set_velocity(vx=0.08, omega=0.25)
    dosed.set_velocity(vx=0.08, omega=0.25)
    for t in (0.05, 0.3, 0.7, 1.5, 2.3):
        a = plain.desired_deg(t)
        b = dosed.desired_deg(t)
        for leg in range(6):
            yaw_i = 3 * leg
            ya, yb = a[yaw_i], b[yaw_i]
            if abs(ya) > 1e-6:
                assert abs(yb) <= abs(ya) + 1e-9
