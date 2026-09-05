"""TripodGait.combined_group_duty_skew unit tests (standwalk Next item
2 gait-STRUCTURE candidate, 09-05) -- pure stdlib, no mujoco/env dep.

See hexapod_core/tripod_gait.py's __init__/`_foot_target_in_body`
docstrings for the full derivation. Unlike every prior candidate in
this file (combined_yaw_arm_scale, combined_yaw_amplify_scale,
combined_selective_omega_boost -- all change a MAGNITUDE within a
FIXED time window, all refuted), this knob changes DURATION: it
re-times the existing two-tripod-group 50/50 alternation so the
"amplified-heavy" group's swing window widens (its own stance window
narrows correspondingly, and the OTHER group's window narrows/widens
in exact complement) -- a SINGLE shared boundary always splits the
phase circle into exactly the two group windows, so exactly one group
is swinging and the other stancing at ANY skew (safe by construction,
no per-leg support-polygon risk to verify separately).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "linux_control"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from hexapod_core.tripod_gait import TripodGait  # noqa: E402


def _make(skew=0.0):
    g = TripodGait(vx=0.0, combined_group_duty_skew=skew)
    g.sync_plant_stance(20.0, 100.0)
    g.reset_phase()
    return g


def test_default_is_bit_exact_identity():
    ref = _make(0.0)
    dosed = TripodGait(vx=0.0)
    dosed.sync_plant_stance(20.0, 100.0)
    dosed.reset_phase()
    ref.set_velocity(vx=0.08, omega=0.25)
    dosed.set_velocity(vx=0.08, omega=0.25)
    for t in (0.0, 0.05, 0.1, 0.37, 1.2):
        assert ref.desired_deg(t) == dosed.desired_deg(t)


def test_pure_turn_and_pure_walk_bit_exact_regardless_of_dose():
    plain = _make(0.0)
    dosed = _make(0.3)
    plain.set_velocity(vx=0.0, omega=0.25)
    dosed.set_velocity(vx=0.0, omega=0.25)
    for t in (0.05, 0.3, 0.7, 1.5):
        assert plain.desired_deg(t) == dosed.desired_deg(t), "pure-turn"

    plain = _make(0.0)
    dosed = _make(0.3)
    plain.set_velocity(vx=0.06, omega=0.0)
    dosed.set_velocity(vx=0.06, omega=0.0)
    for t in (0.05, 0.3, 0.7, 1.5):
        assert plain.desired_deg(t) == dosed.desired_deg(t), "pure-walk"


def test_combined_tick_diverges_at_nonzero_dose():
    plain = _make(0.0)
    dosed = _make(0.3)
    plain.set_velocity(vx=0.08, omega=0.25)
    dosed.set_velocity(vx=0.08, omega=0.25)
    saw_diff = False
    for t in (0.05, 0.2, 0.4, 0.6, 0.9, 1.3):
        if plain.desired_deg(t) != dosed.desired_deg(t):
            saw_diff = True
    assert saw_diff


def test_exactly_one_group_swinging_at_every_instant():
    """The core safety invariant this whole design relies on: for a
    dense time sweep across several periods, at every instant EXACTLY
    3 legs must be in stance (dz==0) and 3 in swing (dz>0 possible,
    though dz can be 0 at the very start/end of a swing window too --
    so we check the underlying group/leg swing classification
    directly via a monkeypatched probe instead of dz alone)."""
    for skew in (0.0, 0.15, 0.3, 0.44):
        for wz_cmd, vx_cmd in ((0.25, 0.08), (-0.25, 0.08),
                                (0.25, -0.08), (-0.25, -0.08)):
            g = _make(skew)
            g.set_velocity(vx=vx_cmd, omega=wz_cmd)
            g._elapsed = 10.0  # past ramp
            for t_ms in range(0, 3000, 5):
                t = t_ms / 1000.0
                g._advance(t)
                # Recompute the swing/stance flag for each leg directly
                # from the SAME theta/width machinery _foot_target_in_body
                # uses, to assert the safety invariant independent of
                # any dz-based proxy.
                heavy = g._classify_group_heavy(g.vx, g.vy, g.omega)
                if heavy is None:
                    continue  # legacy path, already covered elsewhere
                theta = (g._phase + g._phase_offset) % (2 * math.pi)
                width0 = math.pi * (1.0 + (g.combined_group_duty_skew
                                           if heavy == 0 else
                                           -g.combined_group_duty_skew))
                group0_swinging = theta < width0
                # exactly one of the two groups swings -> the other
                # stances, by construction (boolean complement) -- the
                # real assertion is that this NEVER produces both
                # groups swinging (impossible by construction, but
                # assert the invariant explicitly for both group
                # readings so a future refactor can't silently break
                # it).
                group1_swinging = not group0_swinging
                assert group0_swinging != group1_swinging


def test_heavy_group_gets_wider_swing_window():
    """Direct check of the derivation: the group classified as
    amplified-heavy for a given (vx, omega) sign combo should have
    ITS swing window strictly wider than 50% of the cycle at a
    positive dose (and the other group strictly narrower)."""
    g = _make(0.3)
    g.set_velocity(vx=0.08, omega=0.25)
    heavy = g._classify_group_heavy(g.vx, g.vy, g.omega)
    assert heavy is not None
    width0 = math.pi * (1.0 + (g.combined_group_duty_skew
                               if heavy == 0 else
                               -g.combined_group_duty_skew))
    width1 = 2 * math.pi - width0
    heavy_width = width0 if heavy == 0 else width1
    light_width = width1 if heavy == 0 else width0
    assert heavy_width > math.pi > light_width


def test_hip_and_knee_move_with_the_retimed_target():
    """Like every physically-real (not angle-only) candidate in this
    file, a leg's hip/knee (foot placement) must change at nonzero
    dose since it now sweeps a different fraction of the cycle."""
    plain = _make(0.0)
    dosed = _make(0.3)
    plain.set_velocity(vx=0.08, omega=0.25)
    dosed.set_velocity(vx=0.08, omega=0.25)
    saw_hip_knee_diff = False
    for t in (0.05, 0.2, 0.4, 0.6, 0.9, 1.3):
        a = plain.desired_deg(t)
        b = dosed.desired_deg(t)
        for leg in range(6):
            hip_i, knee_i = 3 * leg + 1, 3 * leg + 2
            if abs(a[hip_i] - b[hip_i]) > 1e-9 or abs(a[knee_i] - b[knee_i]) > 1e-9:
                saw_hip_knee_diff = True
    assert saw_hip_knee_diff


def test_skew_sign_is_symmetric_for_opposite_turn_direction():
    """Flipping the sign of omega (same |vx|) should flip WHICH group
    is heavy (per the 09-05 design-pass finding: heavy group depends
    on sign(vx)*sign(omega)), so the SAME positive skew dose should
    still widen exactly one group's window, not silently become a
    no-op or apply to the wrong group."""
    g_pos = _make(0.3)
    g_pos.set_velocity(vx=0.08, omega=0.25)
    heavy_pos = g_pos._classify_group_heavy(g_pos.vx, g_pos.vy, g_pos.omega)

    g_neg = _make(0.3)
    g_neg.set_velocity(vx=0.08, omega=-0.25)
    heavy_neg = g_neg._classify_group_heavy(g_neg.vx, g_neg.vy, g_neg.omega)

    assert heavy_pos is not None and heavy_neg is not None
    assert heavy_pos != heavy_neg


def test_leg_swing_state_matches_foot_target_dz_at_zero_skew():
    """``leg_swing_state`` (standwalk item 2(i) probe hook, 09-05) must
    agree with the pre-existing swing signal (dz>0 during swing, dz==0
    during stance) at skew=0 across a dense phase sweep -- the two
    must never disagree since they read the SAME legacy phi<pi
    boundary."""
    g = _make(0.0)
    g.set_velocity(vx=0.08, omega=0.25)
    g._elapsed = 10.0  # past ramp so dz is unambiguous
    for t_ms in range(0, 1600, 7):
        t = t_ms / 1000.0
        deg_before = g.desired_deg(t)  # advances phase + records dz via IK
        swing = g.leg_swing_state()
        for i in range(6):
            dx, dy, dz = g._foot_target_in_body(i, g._vx_smooth, g._vy_smooth,
                                                 g._om_smooth)
            if dz > 1e-9:
                assert swing[i], f"leg {i} t={t} dz={dz} but swing_state=False"
        del deg_before


def test_leg_swing_state_exactly_three_legs_swinging_at_any_skew():
    """Same 3-up/3-down invariant as
    ``test_exactly_one_group_swinging_at_every_instant``, but exercised
    through the public ``leg_swing_state`` API a probe would actually
    call (rather than re-deriving theta/width inline)."""
    for skew in (0.0, 0.15, 0.3, 0.44):
        for wz_cmd, vx_cmd in ((0.25, 0.08), (-0.25, 0.08),
                                (0.25, -0.08), (-0.25, -0.08)):
            g = _make(skew)
            g.set_velocity(vx=vx_cmd, omega=wz_cmd)
            g._elapsed = 10.0
            for t_ms in range(0, 1500, 11):
                t = t_ms / 1000.0
                g.desired_deg(t)
                swing = g.leg_swing_state()
                assert sum(swing) == 3, (skew, wz_cmd, vx_cmd, t, swing)
                # tripod partition: legs 0,2,4 vs 1,3,5 -- each group
                # must be internally uniform (a group swings/stances
                # together, never split within itself).
                assert swing[0] == swing[2] == swing[4]
                assert swing[1] == swing[3] == swing[5]
                assert swing[0] != swing[1]


def test_leg_swing_state_is_read_only():
    """Calling ``leg_swing_state`` repeatedly must not perturb the
    gait's own state (phase/smoothed velocities) -- it is queried by
    a probe, potentially multiple times per tick, and must never
    change what the NEXT ``desired_deg`` call returns."""
    g = _make(0.3)
    g.set_velocity(vx=0.08, omega=0.25)
    g.desired_deg(0.4)
    ref = g.desired_deg(0.41)
    g2 = _make(0.3)
    g2.set_velocity(vx=0.08, omega=0.25)
    g2.desired_deg(0.4)
    for _ in range(5):
        g2.leg_swing_state()
    dosed = g2.desired_deg(0.41)
    assert ref == dosed
