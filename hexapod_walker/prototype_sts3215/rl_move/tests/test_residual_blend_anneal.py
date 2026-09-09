"""goal.walk_residual_anneal_gate — GATED (ignition-assay-triggered)
anneal of the assistfade rung-3 residual blend, via
apply_residual_blend_frac.

2026-09-09, assistfade rung 3 "blend-schedule fix"
(rl_docs/tracks/assistfade/STATUS.md 09-09 ~07:5x closure): 6/6
per-leg reward-shaping addons (bare duty-ratio, swing-count-floor,
load-slip-ratio x2, swing-gap-dose10, swing-initiation-income, plus a
base-dose recalibration) FAIL to move rung3's chronic single-leg-
sacrifice, all layered on top of the SAME unchanged residual-fade base
whose blend anneals UP on a fixed step-count CALENDAR (sched.key=
goal.walk_residual_blend) regardless of whether the policy is
actually ready -- and the three already-closed schedule-SHAPE levers
(stdslow/latehandover/longbudget, 6 arms) show tweaking that
calendar's timing/slope doesn't help either. This is a structurally
different lever: hold the blend low until a dedicated ignition-
quality assay of the policy's OWN unassisted output passes (mirrors
rung 2's already-proven train.bc_anchor_anneal_gate design, ported
from an anchor-LOSS coefficient to this action-space BLEND), then
anneal it up -- broadcast via apply_residual_blend_frac like every
other trainer-driven ramp (apply_drag_allow_frac etc, walk_task.py),
rather than the self-clocked sched.* engine, since the anneal START
POINT now depends on external assay state the per-env tick clock
cannot observe alone.

Contract under test (mechanics only, no training spend):
  - default (goal.walk_residual_anneal_gate absent/0) is bit-exact
    OFF: no ramp state, apply raises, the plain fallback (static
    goal.walk_residual_blend / the legacy sched.* path) is untouched;
  - fails closed if the base mechanism (goal.walk_residual_gate)
    isn't armed too -- nothing to anneal;
  - ARMED env sits at the LOW start (opposite convention from the
    other ramps, which sit at TARGET when unbroadcast -- documented
    in sim_env.py's __init__ block: this ramp's only consumer always
    broadcasts frac=0 before anything else could read it);
  - frac 0 -> start, 0.5 -> midpoint, 1 -> the cfg target, clamped;
  - fail-closed: a start above the cfg target raises at construction
    (the gate only ever RAISES the blend toward more raw-policy
    authority, never the reverse);
  - the live override actually changes the applied action: at
    blend=0 the commanded joint targets are IDENTICAL regardless of
    the raw policy action (the reference fully dominates); at
    blend=1 two different raw actions produce DIFFERENT commanded
    targets (raw policy fully in control) -- probed via the real
    physics coupling (env.data.ctrl), not just stored state.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.servo_model import SimServoParams

RESIDUAL_KEYS = {
    ("goal", "walk_residual_gate"): 1.0,
    ("goal", "walk_pure"): 1.0,
}
GATE_KEYS = {
    **RESIDUAL_KEYS,
    ("goal", "walk_residual_anneal_gate"): 1.0,
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


def test_default_off_bit_exact_and_apply_raises():
    env = _env(RESIDUAL_KEYS)  # base mechanism on, gate NOT armed
    assert env._residual_blend_ramp is None
    assert env._residual_blend_override is None
    with pytest.raises(RuntimeError, match="not armed"):
        env.apply_residual_blend_frac(0.5)
    env.close()


def test_gate_without_base_mechanism_fails_closed():
    with pytest.raises(ValueError, match="walk_residual_gate<=0"):
        _env({("goal", "walk_residual_anneal_gate"): 1.0})


def test_armed_env_sits_at_the_low_start_before_any_broadcast():
    env = _env(GATE_KEYS)
    assert env._residual_blend_ramp is not None
    # Default v0=0.05 -- opposite convention from the other ramps
    # (they sit at TARGET unbroadcast); documented in __init__.
    assert env._residual_blend_override == pytest.approx(0.05)
    env.close()


def test_frac_endpoints_midpoint_and_clamp():
    env = _env({**GATE_KEYS,
                ("goal", "walk_residual_anneal_v0"): 0.1,
                ("goal", "walk_residual_blend"): 1.0})
    v0 = env.apply_residual_blend_frac(0.0)
    assert v0["blend"] == pytest.approx(0.1)
    vm = env.apply_residual_blend_frac(0.5)
    assert vm["blend"] == pytest.approx(0.55)
    v1 = env.apply_residual_blend_frac(1.0)
    assert v1["blend"] == pytest.approx(1.0)
    assert env.apply_residual_blend_frac(7.0)["frac"] == 1.0
    assert env.apply_residual_blend_frac(-3.0)["frac"] == 0.0
    env.close()


def test_start_above_target_fails_closed():
    with pytest.raises(ValueError, match="must be in"):
        _env({**GATE_KEYS,
              ("goal", "walk_residual_anneal_v0"): 0.9,
              ("goal", "walk_residual_blend"): 0.5})


def test_blend_zero_ignores_the_raw_action_blend_one_obeys_it():
    """Real physics coupling, not stored state: at blend=0 the
    commanded joint targets stay IDENTICAL regardless of the raw
    policy action (the reference fully dominates, over a run of ticks
    so any raw-action influence would compound, not just tick 0);
    at blend=1 two different raw actions diverge. Sets
    ``_residual_blend_override`` directly (bypassing the ramp's own
    start/target frac arithmetic, already covered by
    ``test_frac_endpoints_midpoint_and_clamp`` above) so this test is
    purely about what the override VALUE does downstream, not about
    the ramp math that produces it."""
    def _ctrl_after_steps(blend, action_val, n=20, seed=0):
        env = _env({**GATE_KEYS,
                    ("goal", "walk_residual_blend"): 1.0}, seed=seed)
        env.reset(seed=seed)
        env._residual_blend_override = blend
        action = np.full(env.n_act, action_val, dtype=np.float32)
        for _ in range(n):
            _o, _r, term, trunc, _info = env.step(action)
            if term or trunc:
                break
        ctrl = np.array(env.data.ctrl[env._pos_act], dtype=float)
        env.close()
        return ctrl

    ref_lo = _ctrl_after_steps(0.0, -1.0)
    ref_hi = _ctrl_after_steps(0.0, 1.0)
    np.testing.assert_allclose(ref_lo, ref_hi, atol=1e-9)

    raw_lo = _ctrl_after_steps(1.0, -1.0)
    raw_hi = _ctrl_after_steps(1.0, 1.0)
    assert np.max(np.abs(raw_lo - raw_hi)) > 1e-3
