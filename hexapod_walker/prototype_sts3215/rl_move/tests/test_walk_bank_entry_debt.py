"""goal.walk_bank_entry_debt_scale (2026-09-23, standwalk walk-entry
composed-session gap): the reward-level lever named after THREE prior
fix shapes (goal.walk_entry_bank position-only, goal.bank_qvel_restore
position+velocity, goal_mode_batch_split_walk_start_kind disjoint
minibatch) all FAILed to move the walk-entry handoff fall rate. This
prices |height_err| directly, only on genuine start_kind=="bank" walk
episodes, only within an early post-reset window.

Pure mechanics tests against fake env/goal/traj objects -- no MuJoCo,
no rollout, no ranking (RESEARCH_RULES "Tests").
"""
from __future__ import annotations

from rl_move.config import load_config
from rl_move.sim.walk_reward_bankentry import walk_bank_entry_debt_reward


class _FakeGoal:
    def __init__(self, mode="walk"):
        self.mode = mode


class _FakeTraj:
    def __init__(self, start_kind=None, start_at="plant"):
        self.start_kind = start_kind
        self.start_at = start_at


class _FakeEnv:
    def __init__(self, cfg, goal_traj, step_i):
        self.cfg = cfg
        self._goal_traj = goal_traj
        self._step_i = step_i


def _cfg(**goal_over):
    cfg = load_config()
    cfg.setdefault("goal", {}).update(goal_over)
    return cfg


def test_default_off_is_bit_exact_even_on_a_bank_episode():
    cfg = _cfg()  # walk_bank_entry_debt_scale defaults to 0.0
    env = _FakeEnv(cfg, _FakeTraj(start_kind="bank"), step_i=1)
    parts = {}
    reward = walk_bank_entry_debt_reward(env, _FakeGoal("walk"),
                                          0.05, parts, 10.0)
    assert reward == 10.0
    assert "reward_bank_entry_debt" not in parts


def test_armed_but_not_a_bank_draw_is_a_no_op():
    cfg = _cfg(walk_bank_entry_debt_scale=5.0)
    env = _FakeEnv(cfg, _FakeTraj(start_kind=None, start_at="plant"),
                    step_i=1)
    parts = {}
    reward = walk_bank_entry_debt_reward(env, _FakeGoal("walk"),
                                          0.05, parts, 10.0)
    assert reward == 10.0
    assert "reward_bank_entry_debt" not in parts


def test_armed_but_not_walk_mode_is_a_no_op():
    cfg = _cfg(walk_bank_entry_debt_scale=5.0)
    env = _FakeEnv(cfg, _FakeTraj(start_kind="bank"), step_i=1)
    parts = {}
    reward = walk_bank_entry_debt_reward(env, _FakeGoal("rise"),
                                          0.05, parts, 10.0)
    assert reward == 10.0
    assert "reward_bank_entry_debt" not in parts


def test_bank_episode_inside_safe_band_pays_nothing():
    cfg = _cfg(walk_bank_entry_debt_scale=5.0,
               walk_bank_entry_debt_safe_mm=20.0)
    env = _FakeEnv(cfg, _FakeTraj(start_kind="bank"), step_i=1)
    parts = {}
    # 15mm height_err, safe band is 20mm -> zero debt.
    reward = walk_bank_entry_debt_reward(env, _FakeGoal("walk"),
                                          0.015, parts, 10.0)
    assert reward == 10.0
    assert parts["reward_bank_entry_debt"] == 0.0


def test_bank_episode_beyond_safe_band_pays_the_excess():
    cfg = _cfg(walk_bank_entry_debt_scale=5.0,
               walk_bank_entry_debt_safe_mm=20.0)
    env = _FakeEnv(cfg, _FakeTraj(start_kind="bank"), step_i=1)
    parts = {}
    # 40mm height_err, safe band 20mm -> 20mm excess -> penalty
    # = 5.0 * (20/1000) = 0.1.
    reward = walk_bank_entry_debt_reward(env, _FakeGoal("walk"),
                                          0.040, parts, 10.0)
    assert abs(reward - 9.9) < 1e-9
    assert abs(parts["reward_bank_entry_debt"] - (-0.1)) < 1e-9


def test_penalty_is_capped_for_an_extreme_height_err():
    cfg = _cfg(walk_bank_entry_debt_scale=5.0,
               walk_bank_entry_debt_safe_mm=20.0)
    env = _FakeEnv(cfg, _FakeTraj(start_kind="bank"), step_i=1)
    parts = {}
    # 500mm height_err -> debt clipped at 100mm-equivalent -> penalty
    # capped at 5.0 * (100/1000) = 0.5, not 5.0 * (480/1000) = 2.4.
    reward = walk_bank_entry_debt_reward(env, _FakeGoal("walk"),
                                          0.500, parts, 10.0)
    assert abs(reward - 9.5) < 1e-9
    assert abs(parts["reward_bank_entry_debt"] - (-0.5)) < 1e-9


def test_window_expires_after_configured_seconds():
    cfg = _cfg(walk_bank_entry_debt_scale=5.0,
               walk_bank_entry_debt_window_s=1.0)
    cfg.setdefault("control", {})["hz"] = 50.0
    # window_steps = round(1.0 * 50) = 50; step_i=51 is past it.
    env = _FakeEnv(cfg, _FakeTraj(start_kind="bank"), step_i=51)
    parts = {}
    reward = walk_bank_entry_debt_reward(env, _FakeGoal("walk"),
                                          0.040, parts, 10.0)
    assert reward == 10.0
    assert "reward_bank_entry_debt" not in parts


def test_window_still_applies_at_the_boundary_tick():
    cfg = _cfg(walk_bank_entry_debt_scale=5.0,
               walk_bank_entry_debt_window_s=1.0)
    cfg.setdefault("control", {})["hz"] = 50.0
    env = _FakeEnv(cfg, _FakeTraj(start_kind="bank"), step_i=50)
    parts = {}
    reward = walk_bank_entry_debt_reward(env, _FakeGoal("walk"),
                                          0.040, parts, 10.0)
    assert reward != 10.0
    assert parts["reward_bank_entry_debt"] < 0.0


def test_none_height_err_is_a_no_op():
    cfg = _cfg(walk_bank_entry_debt_scale=5.0)
    env = _FakeEnv(cfg, _FakeTraj(start_kind="bank"), step_i=1)
    parts = {}
    reward = walk_bank_entry_debt_reward(env, _FakeGoal("walk"),
                                          None, parts, 10.0)
    assert reward == 10.0
    assert "reward_bank_entry_debt" not in parts


def test_none_goal_is_a_no_op():
    cfg = _cfg(walk_bank_entry_debt_scale=5.0)
    env = _FakeEnv(cfg, _FakeTraj(start_kind="bank"), step_i=1)
    parts = {}
    reward = walk_bank_entry_debt_reward(env, None, 0.05, parts, 10.0)
    assert reward == 10.0
    assert "reward_bank_entry_debt" not in parts
