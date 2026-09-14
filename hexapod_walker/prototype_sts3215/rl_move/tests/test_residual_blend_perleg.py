"""goal.walk_residual_perleg_gate — per-LEG refinement of the assistfade
rung-3 residual-blend gated anneal (test_residual_blend_anneal.py's
own mechanism), 2026-09-14.

Motivation (rl_docs/tracks/assistfade/STATUS.md 09-09 ~07:5x closure,
its own flagged-but-untried candidate (b)): the closed reward-shaping
family layered six different per-leg ADDONS on top of one SHARED
global residual-blend scalar and all six failed to move the chronic
single-leg sacrifice; the untried lever is making the blend itself six
INDEPENDENT scalars, one per leg, each annealed only once that leg's
OWN ignition assay clears — so a chronically-stuck leg can keep more
scripted authority while its five healthy siblings advance toward raw
policy control.

Contract under test (mechanics only, no training spend):
  - default (goal.walk_residual_perleg_gate absent/0) is bit-exact
    OFF: no behavior change to the base anneal-gate mechanism at all
    (test_residual_blend_anneal.py's own suite already covers that
    mechanism unchanged; this file only adds NEW coverage for the
    per-leg refinement);
  - fails closed if the base walk_residual_anneal_gate isn't armed
    too (per-leg gating refines that ramp, nothing to refine
    otherwise);
  - armed env starts with a (6,) override array, every leg at the
    same ramp start;
  - apply_residual_blend_frac_perleg validates its input shape and
    requires goal.walk_residual_perleg_gate itself (not just the base
    gate) to be armed;
  - per-leg fracs actually diverge legs: at frac=0 for leg A and
    frac=1 for leg B, leg A's commanded joint targets stay IDENTICAL
    regardless of the raw policy action (reference dominates) while
    leg B's diverge with the raw action (matches the base mechanism's
    own real-physics-coupling test, sliced per leg via env.data.ctrl);
  - walkcurr_cert.ignition_gate_pass_per_leg: a chronically-stuck
    single leg (low foot_sw_per_s) fails its own gate while five
    healthy siblings pass, given otherwise-healthy shared metrics;
    nan/missing per-leg data fails every leg closed.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.servo_model import SimServoParams
from rl_move.sim.walkcurr_cert import (
    aggregate_walk_probe, ignition_gate_pass_per_leg)

RESIDUAL_KEYS = {
    ("goal", "walk_residual_gate"): 1.0,
    ("goal", "walk_pure"): 1.0,
}
GATE_KEYS = {
    **RESIDUAL_KEYS,
    ("goal", "walk_residual_anneal_gate"): 1.0,
}
PERLEG_KEYS = {
    **GATE_KEYS,
    ("goal", "walk_residual_perleg_gate"): 1.0,
}


def _cfg(extra=None):
    cfg = load_config()
    for (sec, leaf), val in (extra or {}).items():
        cfg.setdefault(sec, {})[leaf] = val
    return cfg


def _env(extra=None, seed=0):
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg = _cfg(extra)
    params = SimServoParams.from_cfg(cfg)
    return SimHexapodJointWalkEnv(
        params=params, randomize=False, dr_scale=0.0,
        episode_seconds=2.0, seed=seed, cfg=cfg)


def test_default_off_bit_exact():
    # Base gate armed, per-leg NOT requested: override stays a scalar,
    # exactly the pre-09-14 behavior (test_residual_blend_anneal.py's
    # own suite already pins this; re-asserted here as the "no
    # per-leg" baseline this file's own tests diff against).
    env = _env(GATE_KEYS)
    assert env._residual_perleg_gate is False
    assert env._residual_blend_override == pytest.approx(0.05)
    assert np.ndim(env._residual_blend_override) == 0
    env.close()


def test_perleg_without_base_anneal_gate_fails_closed():
    with pytest.raises(ValueError, match="walk_residual_anneal_gate<=0"):
        _env({**RESIDUAL_KEYS,
              ("goal", "walk_residual_perleg_gate"): 1.0})


def test_perleg_armed_starts_all_six_legs_at_the_same_low_start():
    env = _env(PERLEG_KEYS)
    assert env._residual_perleg_gate is True
    override = env._residual_blend_override
    assert np.shape(override) == (6,)
    np.testing.assert_allclose(override, 0.05)
    env.close()


def test_apply_perleg_requires_perleg_gate_not_just_base_gate():
    # Base (scalar) gate armed but per-leg NOT: the per-leg apply
    # method must still refuse (calling it would silently clobber the
    # scalar override with an array shape nothing else expects).
    env = _env(GATE_KEYS)
    with pytest.raises(RuntimeError, match="not armed"):
        env.apply_residual_blend_frac_perleg([0.0] * 6)
    env.close()


def test_apply_perleg_validates_shape():
    env = _env(PERLEG_KEYS)
    with pytest.raises(ValueError, match="expects 6 fracs"):
        env.apply_residual_blend_frac_perleg([0.0, 1.0, 0.5])
    env.close()


def test_apply_perleg_endpoints_and_clamp():
    env = _env({**PERLEG_KEYS,
                ("goal", "walk_residual_anneal_v0"): 0.1,
                ("goal", "walk_residual_blend"): 1.0})
    fracs = [0.0, 0.5, 1.0, 0.0, 0.5, 1.0]
    out = env.apply_residual_blend_frac_perleg(fracs)
    expected = [0.1, 0.55, 1.0, 0.1, 0.55, 1.0]
    np.testing.assert_allclose(out["blend"], expected, atol=1e-9)
    # Clamp: out-of-range fracs are clipped to [0, 1] same as the
    # scalar apply's own clamp contract.
    out2 = env.apply_residual_blend_frac_perleg([7.0, -3.0, 0, 0, 0, 0])
    assert out2["blend"][0] == pytest.approx(1.0)
    assert out2["blend"][1] == pytest.approx(0.1)
    env.close()


def test_perleg_blend_diverges_legs_independently():
    """With legs at blend [0, .5, .5, .5, .5, 1] (all others mid), the
    blended target sent downstream is IDENTICAL for leg 0 across two
    different raw actions (reference fully dominates), moves by
    exactly HALF the raw delta for the 0.5-blend legs, and by the
    FULL raw delta for leg 5 (raw policy fully in control) — the
    per-leg arithmetic's direct prediction, checked pre-safety/IK via
    the existing ``debug_pipeline_record`` / ``_dbg_applied_action``
    hook (sim_env.py ``_step_begin``, built 2026-09-08 for exactly
    this "audit actor -> proposed-target -> SafetyLayer transmission
    offline" purpose) instead of reading post-physics
    ``env.data.ctrl``: the slew-rate/IK/safety filter stages
    downstream of the blend are a real, independent part of the
    control pipeline that dominates ``data.ctrl`` at low tick counts
    regardless of the blended target (confirmed by hand while
    building this test — the two raw actions' pre-safety blended
    targets already diverge exactly as the arithmetic predicts on
    tick 1; reading post-safety ctrl only adds an unrelated confound
    this mechanism doesn't own)."""
    def _applied_action(action_val, seed=0):
        env = _env({**PERLEG_KEYS,
                    ("goal", "walk_residual_blend"): 1.0}, seed=seed)
        env.reset(seed=seed)
        env._residual_blend_override = np.array(
            [0.0, 0.5, 0.5, 0.5, 0.5, 1.0], dtype=np.float64)
        env.debug_pipeline_record = True
        action = np.full(env.n_act, action_val, dtype=np.float32)
        env.step(action)
        applied = np.asarray(env._dbg_applied_action, dtype=float).copy()
        env.close()
        return applied

    lo = _applied_action(-0.3)
    hi = _applied_action(0.3)
    # Leg 0 (indices 0:3, blend=0): reference dominates, the blended
    # target is IDENTICAL regardless of the raw action.
    np.testing.assert_allclose(lo[0:3], hi[0:3], atol=1e-6)
    # Legs 1-4 (indices 3:15, blend=0.5): move by exactly HALF the raw
    # action delta (0.5 * (-0.3 - 0.3) = -0.3).
    np.testing.assert_allclose(lo[3:15] - hi[3:15], -0.3, atol=1e-5)
    # Leg 5 (indices 15:18, blend=1.0): the raw policy fully in
    # control, the full delta (-0.3 - 0.3 = -0.6) passes through.
    np.testing.assert_allclose(lo[15:18] - hi[15:18], -0.6, atol=1e-5)


def test_ignition_gate_pass_per_leg_isolates_the_stuck_leg():
    healthy_fsw = [2.0, 2.0, 2.0, 2.0, 2.0, 2.0]
    stuck_fsw = list(healthy_fsw)
    stuck_fsw[4] = 0.05  # leg 4 chronically stuck (below the 0.5 bar)
    m = {
        "early_term_rate": 0.0,
        "contact_sw_per_s": 5.0,
        "cmd_prog_frac": 0.9,
        "foot_sw_per_s": stuck_fsw,
    }
    per_leg, shared = ignition_gate_pass_per_leg(m)
    assert per_leg == [True, True, True, True, False, True]
    assert all(shared.values())


def test_ignition_gate_pass_per_leg_shared_failure_fails_every_leg():
    m = {
        "early_term_rate": 1.0,  # a fall this round
        "contact_sw_per_s": 5.0,
        "cmd_prog_frac": 0.9,
        "foot_sw_per_s": [2.0] * 6,
    }
    per_leg, shared = ignition_gate_pass_per_leg(m)
    assert per_leg == [False] * 6
    assert shared["no_falls"] is False


def test_ignition_gate_pass_per_leg_missing_data_fails_closed():
    per_leg, shared = ignition_gate_pass_per_leg({
        "early_term_rate": 0.0, "contact_sw_per_s": 5.0,
        "cmd_prog_frac": 0.9})  # no foot_sw_per_s at all
    assert per_leg == [False] * 6


def test_aggregate_walk_probe_perleg_key():
    rows = [
        {"foot_sw_per_s": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]},
        {"foot_sw_per_s": [3.0, 2.0, 1.0, 0.0, 5.0, 4.0]},
    ]
    out = aggregate_walk_probe(rows)
    np.testing.assert_allclose(
        out["foot_sw_per_s"], [2.0, 2.0, 2.0, 2.0, 5.0, 5.0])


def test_aggregate_walk_probe_perleg_key_nan_when_any_row_missing_it():
    rows = [{"foot_sw_per_s": [1.0] * 6}, {}]
    out = aggregate_walk_probe(rows)
    assert all(v != v for v in out["foot_sw_per_s"])  # all nan
