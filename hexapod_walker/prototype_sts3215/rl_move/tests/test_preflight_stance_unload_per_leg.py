"""preflight_stance_unload_per_leg.py -- mechanics only (2026-09-30).

Pure-Python pieces only (cfg-merge, difficulty formula, dummy-model
contract) -- no MuJoCo/env build, well under 5 s. The tool's actual
scripted rollout was validated interactively (own-cfg CEIL225 dose
sweep, n=60/dose, reported in standwalk STATUS.md); that measurement
run is diagnostic, not a pinned regression test (RESEARCH_RULES
"Tests": mechanics, never a rollout-ranking bank).
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from rl_move.sim.preflight_stance_unload_per_leg import (
    _ZeroModel, _build_cfg, _leg_difficulty_fracs,
)


def test_zero_model_predicts_zero_action_of_the_right_width():
    m = _ZeroModel()
    act, state = m.predict(np.zeros(10), deterministic=True)
    assert act.shape == (18,)
    assert np.all(act == 0.0)
    assert state is None
    m.reset()   # must not raise


def test_build_cfg_default_dose_is_zero():
    cfg = _build_cfg(0.0, None)
    assert cfg["train"]["bc_anchor_teacher_stance_unload_frac_per_leg_dose"] == 0.0
    assert cfg["dr"]["joint_zero_bias_deg"] == 2.25
    assert cfg["goal"]["walk_residual_gate"] == 1.0
    assert cfg["goal"]["walk_residual_blend"] == 0.0


def test_build_cfg_dose_is_injected():
    cfg = _build_cfg(0.4, None)
    assert cfg["train"]["bc_anchor_teacher_stance_unload_frac_per_leg_dose"] == 0.4


def test_build_cfg_extra_overrides_apply_on_top():
    cfg = _build_cfg(0.0, ["dr.joint_zero_bias_deg=1.0"])
    assert cfg["dr"]["joint_zero_bias_deg"] == 1.0
    # unrelated ceil225 physics keys stay in place
    assert cfg["dr"]["link_len_leg_pct"] == 0.035


def _draw(link_scale, zero_bias_deg, link_len_leg_pct=0.1,
          joint_zero_bias_deg=5.0):
    ep_rand = SimpleNamespace(
        link_scale=np.asarray(link_scale, dtype=float),
        joint_zero_bias_rad=np.radians(np.asarray(zero_bias_deg,
                                                   dtype=float)))
    ranges = SimpleNamespace(link_len_leg_pct=link_len_leg_pct,
                             joint_zero_bias_deg=joint_zero_bias_deg)
    return SimpleNamespace(_ep_rand=ep_rand,
                           randomizer=SimpleNamespace(ranges=ranges))


def test_leg_difficulty_none_without_a_draw():
    env = SimpleNamespace(_ep_rand=None, randomizer=None)
    assert _leg_difficulty_fracs(env) is None


def test_leg_difficulty_zero_for_a_nominal_draw():
    env = _draw([[1.0, 1.0, 1.0]] * 6, [0.0] * 18)
    fracs = _leg_difficulty_fracs(env)
    assert fracs == [0.0] * 6


def test_leg_difficulty_picks_out_the_hardest_leg():
    zero_bias_deg = [0.0] * 18
    zero_bias_deg[3 * 4] = 5.0    # leg 4 draws the full ceiling
    env = _draw([[1.0, 1.0, 1.0]] * 6, zero_bias_deg)
    fracs = _leg_difficulty_fracs(env)
    assert int(np.argmax(fracs)) == 4
    assert fracs[4] == 0.5   # 0.5*(link_frac=0 + bias_frac=1.0)
    assert all(f == 0.0 for i, f in enumerate(fracs) if i != 4)


def test_leg_difficulty_matches_the_sim_env_per_leg_dose_formula():
    """Same formula as `sim_env._stance_unload_frac_per_leg_from_draw`
    at dose=1.0 -- this probe's difficulty read must agree with the
    mechanism it is evaluating, not a redefinition."""
    from rl_move.sim.sim_env import SimHexapodBalanceEnv, _default_plant_deg
    import types
    zero_bias_deg = [0.0] * 18
    zero_bias_deg[3 * 2] = 3.0
    zero_bias_deg[3 * 2 + 1] = 1.0
    link_scale = [[1.0, 1.0, 1.0]] * 6
    link_scale[2] = [1.02, 1.0, 1.0]
    env = _draw(link_scale, zero_bias_deg, link_len_leg_pct=0.1,
                joint_zero_bias_deg=5.0)
    fracs = _leg_difficulty_fracs(env)

    holder = SimpleNamespace(
        cfg={"train": {
            "bc_anchor_teacher_stance_unload_frac_per_leg_dose": 1.0}},
        _plant_deg=_default_plant_deg(), _ep_rand=env._ep_rand,
        randomizer=env.randomizer)
    holder._stance_unload_frac_per_leg_from_draw = types.MethodType(
        SimHexapodBalanceEnv._stance_unload_frac_per_leg_from_draw, holder)
    per_leg = holder._stance_unload_frac_per_leg_from_draw()
    assert per_leg is not None
    for a, b in zip(fracs, per_leg):
        assert abs(a - b) < 1e-9
