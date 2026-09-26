"""Tests for the optional ORACLE per-leg draw observation channel
(``obs.dr_oracle_sense``, see ``rl_move/sim/walk_task.py::
dr_oracle_sense_obs_dim`` / ``_augment_obs``).

2026-09-26 standwalk SENSE-hypothesis closure: every INDIRECT sensing
lever (park-price, measured velocity, current-sense, foot-contact-
sense) tied its zero-shot parent at the ceil225 stepping-stone. This
channel hands the policy the RAW ground-truth per-leg draw itself
(mean link-scale deviation + max zero-bias degrees, the two axes
``draw_feasibility.py`` found most predictive) at the absolute frame
tail. Default OFF and bit-exact when off, per RESEARCH_RULES.
"""
from __future__ import annotations

import numpy as np

from rl_move.config import load_config
from rl_move.robot_state import DEG2RAD
from rl_move.sim.walk_task import (
    N_DR_ORACLE_OBS, SimHexapodJointWalkEnv, dr_oracle_sense_obs_dim,
)


def test_dim_default_off():
    assert dr_oracle_sense_obs_dim({}) == 0
    assert dr_oracle_sense_obs_dim(
        {"obs": {"dr_oracle_sense": 0.0}}) == 0


def test_dim_on():
    assert dr_oracle_sense_obs_dim(
        {"obs": {"dr_oracle_sense": 1.0}}) == N_DR_ORACLE_OBS


def _make_env(on: bool, *, link_scale: float | None = None,
              bias_scale: float | None = None, randomize: bool = False):
    cfg = load_config()
    obs_cfg = cfg.setdefault("obs", {})
    if on:
        obs_cfg["dr_oracle_sense"] = 1.0
        if link_scale is not None:
            obs_cfg["dr_oracle_link_scale"] = link_scale
        if bias_scale is not None:
            obs_cfg["dr_oracle_bias_scale"] = bias_scale
    if randomize:
        return SimHexapodJointWalkEnv(cfg, randomize=True, dr_scale=1.0,
                                       seed=0)
    return SimHexapodJointWalkEnv(cfg, seed=0)


def test_default_off_bit_exact():
    a = _make_env(False)
    obs_a, _ = a.reset(seed=0)
    b = _make_env(False)
    obs_b, _ = b.reset(seed=0)
    np.testing.assert_array_equal(obs_a, obs_b)
    assert a.observation_space.shape == b.observation_space.shape


def test_on_widens_frame_tail_by_twelve_and_prefix_identical():
    off = _make_env(False)
    obs_off, _ = off.reset(seed=0)
    on = _make_env(True)
    obs_on, _ = on.reset(seed=0)
    k = off._hist_n
    w_off = obs_off.shape[0] // k
    w_on = obs_on.shape[0] // k
    assert w_on == w_off + N_DR_ORACLE_OBS
    assert on.observation_space.shape[0] == obs_on.shape[0]
    for f in range(k):
        np.testing.assert_allclose(
            obs_on[f * w_on:f * w_on + w_off],
            obs_off[f * w_off:(f + 1) * w_off], atol=0.0)


def test_tail_matches_ep_rand_ground_truth():
    env = _make_env(True, link_scale=0.05, bias_scale=3.0, randomize=True)
    obs, _ = env.reset(seed=0)
    w = obs.shape[0] // env._hist_n
    tail = obs[w - N_DR_ORACLE_OBS:w]
    er = env._ep_rand
    want_link = [float(np.mean(er.link_scale[i])) - 1.0
                 for i in range(6)]
    want_bias = [float(np.max(np.abs(er.joint_zero_bias_rad[
        3 * i:3 * i + 3]))) / DEG2RAD for i in range(6)]
    want = np.array([v / 0.05 for v in want_link]
                     + [v / 3.0 for v in want_bias], dtype=np.float32)
    np.testing.assert_allclose(tail, want, atol=1e-5)


def test_step_keeps_tail_live_and_constant_within_episode():
    # The DR draw is fixed per episode -- the oracle channel must not
    # change tick-to-tick.
    env = _make_env(True)
    obs, _ = env.reset(seed=1)
    w = obs.shape[0] // env._hist_n
    tail0 = obs[w - N_DR_ORACLE_OBS:w].copy()
    a = np.zeros(env.action_space.shape, dtype=np.float32)
    obs, _, term, trunc, _ = env.step(a)
    tail1 = obs[w - N_DR_ORACLE_OBS:w]
    assert tail1.shape == (N_DR_ORACLE_OBS,)
    np.testing.assert_allclose(tail0, tail1, atol=1e-6)


def test_combines_with_foot_contact_sense_tail_order():
    from rl_move.sim.walk_task import N_FOOT_CONTACT_OBS
    cfg = load_config()
    obs_cfg = cfg.setdefault("obs", {})
    obs_cfg["foot_contact_sense"] = 1.0
    obs_cfg["dr_oracle_sense"] = 1.0
    env = SimHexapodJointWalkEnv(cfg, randomize=True, dr_scale=1.0, seed=0)
    obs, _ = env.reset(seed=0)
    w = obs.shape[0] // env._hist_n
    oracle_tail = obs[w - N_DR_ORACLE_OBS:w]
    foot_block = obs[w - N_DR_ORACLE_OBS - N_FOOT_CONTACT_OBS:
                     w - N_DR_ORACLE_OBS]
    er = env._ep_rand
    want_link = [float(np.mean(er.link_scale[i])) - 1.0
                 for i in range(6)]
    np.testing.assert_allclose(
        oracle_tail[:6], np.asarray(want_link, dtype=np.float32) / 0.05,
        atol=1e-5)
    assert foot_block.shape == (N_FOOT_CONTACT_OBS,)
