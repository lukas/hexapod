"""TripodGait.combined_selective_omega_boost unit tests (standwalk
Next item 2, "selective per-leg omega boost" candidate, 09-04) --
pure stdlib, no mujoco/env dependency.

See hexapod_core/tripod_gait.py's __init__ docstring for the full
derivation. Unlike every candidate in the 09-04 "reshape the
commanded yaw ANGLE" family (uniform combined_yaw_arm_scale, selective
combined_yaw_amplify_scale, the unwired "detangle" idea -- all
REFUTED because scaling the yaw servo angle's atan2 denominator never
changes the TRUE foot offset, so physical rotation shrinks with the
commanded angle), this knob boosts the TRUE foot target itself (via
omega) for ATTENUATED legs only -- the mirror image of
combined_yaw_amplify_scale's classification, using the SAME
_yaw_frame_xy/pure-omega-reference machinery, but a genuinely
different (physically real) mechanism: the uniform sibling of this
idea is train.bc_anchor_teacher_omega_boost, already proven (09-03)
to recover real scripted-teacher wz (at a vx cost) at the SCRIPTED
level -- this restricts that same recovery to only the 3 legs that
lose authority to the vx cross term, leaving the 3 already-amplified
legs untouched.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "linux_control"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from hexapod_core.tripod_gait import TripodGait  # noqa: E402


def _make(boost=1.0):
    g = TripodGait(vx=0.0, combined_selective_omega_boost=boost)
    g.sync_plant_stance(20.0, 100.0)
    g.reset_phase()
    return g


def test_default_is_bit_exact_identity():
    ref = _make(1.0)
    dosed = TripodGait(vx=0.0)
    dosed.sync_plant_stance(20.0, 100.0)
    dosed.reset_phase()
    ref.set_velocity(vx=0.08, omega=0.25)
    dosed.set_velocity(vx=0.08, omega=0.25)
    for t in (0.0, 0.05, 0.1, 0.37, 1.2):
        assert ref.desired_deg(t) == dosed.desired_deg(t)


def test_pure_turn_and_pure_walk_bit_exact_regardless_of_dose():
    plain = _make(1.0)
    dosed = _make(3.0)
    plain.set_velocity(vx=0.0, omega=0.25)
    dosed.set_velocity(vx=0.0, omega=0.25)
    for t in (0.05, 0.3, 0.7, 1.5):
        assert plain.desired_deg(t) == dosed.desired_deg(t), "pure-turn"

    plain = _make(1.0)
    dosed = _make(3.0)
    plain.set_velocity(vx=0.06, omega=0.0)
    dosed.set_velocity(vx=0.06, omega=0.0)
    for t in (0.05, 0.3, 0.7, 1.5):
        assert plain.desired_deg(t) == dosed.desired_deg(t), "pure-walk"


def test_selective_dose_leaves_amplified_legs_bit_exact_on_combined_tick():
    """Mirror image of the amplify_scale test: at least one leg (an
    AMPLIFIED one) must be BYTE-IDENTICAL across dose here (untouched
    by this knob), while at least one (an ATTENUATED one) diverges --
    the opposite leg set from combined_yaw_amplify_scale, same
    combined command."""
    plain = _make(1.0)
    dosed = _make(3.0)
    plain.set_velocity(vx=0.08, omega=0.25)
    dosed.set_velocity(vx=0.08, omega=0.25)
    saw_same = saw_diff = False
    for t in (0.05, 0.3, 0.7, 1.5, 2.3):
        a = plain.desired_deg(t)
        b = dosed.desired_deg(t)
        for leg in range(6):
            if abs(a[3 * leg] - b[3 * leg]) < 1e-9:
                saw_same = True
            else:
                saw_diff = True
    assert saw_same, "expected >=1 leg (amplified) untouched"
    assert saw_diff, "expected >=1 leg (attenuated) to diverge"


def test_attenuated_legs_grow_toward_pure_turn_magnitude():
    """A leg the vx cross term attenuates below the pure-turn
    magnitude should grow toward (not away from) that pure-turn
    magnitude as the dose increases -- the mechanism's actual
    purpose, mirroring amplify_scale's shrink-toward-pure-turn test."""
    turn_only = _make(1.0)
    turn_only.set_velocity(vx=0.0, omega=0.25)
    pure_turn_yaw = turn_only.desired_deg(0.3)

    combined_ref = _make(1.0)
    combined_ref.set_velocity(vx=0.08, omega=0.25)
    combined_yaw = combined_ref.desired_deg(0.3)
    attenuated_leg = next(
        i for i in range(6)
        if abs(combined_yaw[3 * i]) < abs(pure_turn_yaw[3 * i]) - 1e-6)

    doses = (1.0, 1.5, 2.0, 3.0)
    mags = []
    for d in doses:
        g = _make(d)
        g.set_velocity(vx=0.08, omega=0.25)
        mags.append(abs(g.desired_deg(0.3)[3 * attenuated_leg]))
    assert mags == sorted(mags), mags
    assert mags[-1] > mags[0]


def test_hip_and_knee_move_with_the_boosted_target():
    """Unlike yaw_arm_scale/amplify_scale (angle-only, hip/knee frozen
    by construction), this knob boosts the TRUE foot target -- an
    attenuated leg's hip/knee (foot placement/lift) MUST also change
    at dose!=1.0, since the physical foot offset genuinely changed.
    This is the intended, load-bearing difference from the refuted
    angle-reshape family, not a bug to eliminate."""
    plain = _make(1.0)
    dosed = _make(3.0)
    plain.set_velocity(vx=0.08, omega=0.25)
    dosed.set_velocity(vx=0.08, omega=0.25)
    saw_hip_knee_diff = False
    for t in (0.05, 0.3, 0.7, 1.5, 2.3):
        a = plain.desired_deg(t)
        b = dosed.desired_deg(t)
        for leg in range(6):
            hip_i, knee_i = 3 * leg + 1, 3 * leg + 2
            if abs(a[hip_i] - b[hip_i]) > 1e-9 or abs(a[knee_i] - b[knee_i]) > 1e-9:
                saw_hip_knee_diff = True
    assert saw_hip_knee_diff, "expected hip/knee to move for a boosted leg"
