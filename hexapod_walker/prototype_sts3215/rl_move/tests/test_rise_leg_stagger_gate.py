"""Per-leg staggered curl-order gate (``ik.rise_leg_stagger_gate``,
walkcurr track, 2026-09-14).

Background (STATUS/TRUTHS 09-14 ~07:1x): 19/19 independent levers on
walkcurr flat-start rise are now null across three axes -- action-space
magnitude caps (height 9 arms + rate 2 doses, 10/10), reward-shaping
(7/7) and reset-distribution curricula (2/2) -- all closed on the
IDENTICAL flat-start over_current fingerprint. Every one of those
levers treated all six legs' curl timing as one undifferentiated
object. The binding conclusion names the untried axis explicitly:
WHICH ORDER the six legs individually curl/tuck, not how much/fast or
when. This is the first mechanism to make that axis literal: split the
single global ``curl_frac`` ratchet into a per-leg array and hold one
tripod group's ratchet until the other tripod group's own progress
clears a threshold -- a structural, demonstration-free bias toward a
staggered curl order (never a magnitude cap on all legs alike, and
never priced against any scripted reference trajectory).

Contract under test:
  - default OFF (no cfg, or ``ik.rise_leg_stagger_gate`` unset/0) is
    bit-exact: per-leg array stays uniform every tick, ``curl_frac``
    matches the pre-existing scalar-ratchet formula exactly, and
    ``_anchor`` interpolation is identical regardless of leg index.
  - ON: group A (legs 0,2,4) ratchets every tick ``offset.curl>0``
    fires, unconditionally; group B (legs 1,3,5) is HELD at its
    current value until group A's mean progress reaches
    ``rise_leg_stagger_threshold``, then ratchets normally from there.
  - ``curl_frac`` (the legacy scalar other gates read) tracks
    ``min(curl_frac_per_leg)`` so downstream gates see the
    least-advanced leg's progress, never a leg that raced ahead.
  - The gate never runs backward (monotonic ratchet preserved) and
    never touches height/rate gating code paths.

RESEARCH_RULES "Tests": fast, mechanics only, no artifacts, no
rollout-ranking.
"""
from __future__ import annotations

import numpy as np

from rl_move.body_ik import (
    BodyOffset, FixedFootBodyIK, N_LEGS, STAGGER_GROUPS_TRIPOD,
)


def _q_nom():
    return np.zeros(18, dtype=float)


def _plant_q():
    # Any distinct pose so feet_plant_xy differs from feet_world and the
    # ratchet has somewhere to go.
    q = np.zeros(18, dtype=float)
    q[1::3] = 0.3   # femur joints
    q[2::3] = -0.6  # tibia joints
    return q


def test_default_off_bit_exact_uniform_per_leg():
    ik = FixedFootBodyIK()  # no cfg -> gate off
    ik.reset(_q_nom(), plant_q_rad=_plant_q())
    assert not ik.stagger_gate
    offset = BodyOffset(curl=1.0)
    prev_scalar = 0.0
    for _ in range(20):
        ik.solve(offset)
        # Per-leg array stays perfectly uniform.
        assert np.allclose(ik.curl_frac_per_leg, ik.curl_frac_per_leg[0])
        expected = min(prev_scalar + ik.CURL_RATE_PER_TICK, 1.0)
        assert abs(ik.curl_frac - expected) < 1e-12
        prev_scalar = expected


def test_default_off_anchor_identical_across_legs():
    ik = FixedFootBodyIK()
    ik.reset(_q_nom(), plant_q_rad=_plant_q())
    ik.solve(BodyOffset(curl=1.0))
    # Every leg's anchor interpolation used the same curl_frac.
    fracs = {i: ik.curl_frac_per_leg[i] for i in range(N_LEGS)}
    assert len(set(fracs.values())) == 1


def _cfg(gate=1, threshold=0.5):
    return {"ik": {"rise_leg_stagger_gate": gate,
                   "rise_leg_stagger_threshold": threshold}}


def test_gate_on_group_b_held_until_threshold():
    ik = FixedFootBodyIK(cfg=_cfg(gate=1, threshold=0.5))
    ik.reset(_q_nom(), plant_q_rad=_plant_q())
    assert ik.stagger_gate
    group_a, group_b = STAGGER_GROUPS_TRIPOD
    offset = BodyOffset(curl=1.0)
    for _ in range(10):  # 10 * 0.016 = 0.16 < 0.5 threshold
        ik.solve(offset)
        for i in group_b:
            assert ik.curl_frac_per_leg[i] == 0.0, "group B moved before threshold"
    for i in group_a:
        assert ik.curl_frac_per_leg[i] > 0.0, "group A must ratchet unconditionally"


def test_gate_on_group_b_resumes_after_threshold():
    ik = FixedFootBodyIK(cfg=_cfg(gate=1, threshold=0.3))
    ik.reset(_q_nom(), plant_q_rad=_plant_q())
    group_a, group_b = STAGGER_GROUPS_TRIPOD
    offset = BodyOffset(curl=1.0)
    # threshold 0.3 / rate 0.016 ~= 19 ticks for group A to cross it.
    crossed = False
    for tick in range(60):
        before_b = ik.curl_frac_per_leg[group_b[0]]
        ik.solve(offset)
        after_b = ik.curl_frac_per_leg[group_b[0]]
        a_prog = float(np.mean(ik.curl_frac_per_leg[list(group_a)]))
        if a_prog >= 0.3:
            crossed = True
        if crossed:
            assert after_b >= before_b
    assert crossed
    for i in group_b:
        assert ik.curl_frac_per_leg[i] > 0.0, "group B must resume after threshold"


def test_gate_on_curl_frac_is_min_of_per_leg():
    ik = FixedFootBodyIK(cfg=_cfg(gate=1, threshold=0.5))
    ik.reset(_q_nom(), plant_q_rad=_plant_q())
    offset = BodyOffset(curl=1.0)
    for _ in range(15):
        ik.solve(offset)
    assert abs(ik.curl_frac - float(np.min(ik.curl_frac_per_leg))) < 1e-12
    group_a, group_b = STAGGER_GROUPS_TRIPOD
    # Group B held at 0 while group A advances -> curl_frac must be 0.
    if float(np.mean(ik.curl_frac_per_leg[list(group_a)])) < 0.5:
        assert ik.curl_frac == 0.0


def test_gate_on_monotonic_never_decreases():
    ik = FixedFootBodyIK(cfg=_cfg(gate=1, threshold=0.4))
    ik.reset(_q_nom(), plant_q_rad=_plant_q())
    offset = BodyOffset(curl=1.0)
    prev = ik.curl_frac_per_leg.copy()
    for _ in range(80):
        ik.solve(offset)
        assert np.all(ik.curl_frac_per_leg >= prev - 1e-12)
        prev = ik.curl_frac_per_leg.copy()


def test_zero_curl_action_never_advances_either_group():
    ik = FixedFootBodyIK(cfg=_cfg(gate=1, threshold=0.5))
    ik.reset(_q_nom(), plant_q_rad=_plant_q())
    offset = BodyOffset(curl=0.0)
    for _ in range(5):
        ik.solve(offset)
    assert np.all(ik.curl_frac_per_leg == 0.0)
    assert ik.curl_frac == 0.0


def test_cfg_none_never_crashes_and_matches_gate_off_default():
    ik_a = FixedFootBodyIK(cfg=None)
    ik_b = FixedFootBodyIK()
    for ik in (ik_a, ik_b):
        assert not ik.stagger_gate
        ik.reset(_q_nom(), plant_q_rad=_plant_q())
        ik.solve(BodyOffset(curl=1.0))
    assert abs(ik_a.curl_frac - ik_b.curl_frac) < 1e-12


def test_sim_env_wires_cfg_into_ik_stagger_gate():
    import pytest
    pytest.importorskip("mujoco")
    from rl_move.config import load_config
    from rl_move.sim.servo_model import SimServoParams
    from rl_move.sim.sim_env import SimHexapodBalanceEnv

    cfg = load_config()
    cfg.setdefault("ik", {})
    cfg["ik"]["rise_leg_stagger_gate"] = 1
    cfg["ik"]["rise_leg_stagger_threshold"] = 0.5
    params = SimServoParams.from_cfg(cfg)
    env = SimHexapodBalanceEnv(params=params, randomize=False, dr_scale=0.0,
                               episode_seconds=2.0, seed=0, cfg=cfg)
    assert env.ik.stagger_gate
    assert abs(env.ik.stagger_threshold - 0.5) < 1e-9
    env.reset(seed=0)
    assert env.ik.stagger_gate  # survives reset() (constructed once, not rebuilt)
