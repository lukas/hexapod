"""Mechanics-only coverage for reward.k_walk_persistence_bonus
(walk_reward_course.walk_persistence_bonus, amp/STATUS.md Next item
(i), 2026-09-26).

Per RESEARCH_RULES "Tests": mechanics, not measurements -- no rollout,
no MuJoCo model, no tuned/ordering assertions. A minimal fake env
carries only the attributes the function under test actually reads
(`cfg`, `dt`, `_walk_persist_s`).
"""
from __future__ import annotations

from rl_move.sim import walk_reward_course as wrc


class _FakeGoal:
    pass


def _make_env(cfg, dt=0.02):
    class _Env:
        pass
    e = _Env()
    e.cfg = cfg
    e.dt = dt
    e._walk_persist_s = 0.0
    return e


def test_default_off_is_bit_exact():
    """k_walk_persistence_bonus unset (default 0.0): reward and info
    are untouched, streak state is left alone."""
    env = _make_env(cfg={})
    info = {"reward_walk_course_income": 5.0}
    reward = wrc.walk_persistence_bonus(env, _FakeGoal(), info, 100.0,
                                         s_ref=0.05)
    assert reward == 100.0
    assert "reward_walk_persistence_bonus" not in info
    assert "walk_persistence_s" not in info
    assert env._walk_persist_s == 0.0


def test_zero_dose_is_bit_exact():
    """Explicit k=0.0 behaves identically to unset (off path taken)."""
    env = _make_env(cfg={"reward": {"k_walk_persistence_bonus": 0.0}})
    info = {"reward_walk_course_income": 5.0}
    reward = wrc.walk_persistence_bonus(env, _FakeGoal(), info, 42.0,
                                         s_ref=0.05)
    assert reward == 42.0
    assert "reward_walk_persistence_bonus" not in info


def test_stop_command_does_not_grow_or_touch_streak():
    """s_ref<=1e-3 (a commanded stop) is a no-op: no info keys, no
    streak mutation, whatever its current value."""
    cfg = {"reward": {"k_walk_persistence_bonus": 1.0}}
    env = _make_env(cfg=cfg)
    env._walk_persist_s = 1.5
    info = {"reward_walk_course_income": 5.0}
    reward = wrc.walk_persistence_bonus(env, _FakeGoal(), info, 10.0,
                                         s_ref=0.0)
    assert reward == 10.0
    assert env._walk_persist_s == 1.5
    assert "reward_walk_persistence_bonus" not in info


def test_streak_grows_on_consecutive_positive_income_ticks():
    """Each moving tick with positive course income extends the
    streak by env.dt and the bonus ramps up (never exceeding the
    cap) rather than jumping straight to full dose."""
    cfg = {"reward": {"k_walk_persistence_bonus": 2.0,
                       "walk_persistence_ramp_s": 1.0,
                       "walk_persistence_cap": 1.0}}
    env = _make_env(cfg=cfg, dt=0.25)
    bonuses = []
    for _ in range(6):
        info = {"reward_walk_course_income": 1.0}
        reward = wrc.walk_persistence_bonus(env, _FakeGoal(), info,
                                             0.0, s_ref=0.05)
        bonuses.append(info["reward_walk_persistence_bonus"])
    # streak: 0.25, 0.5, 0.75, 1.0, 1.0(capped), 1.0(capped)
    assert bonuses == sorted(bonuses)  # monotone non-decreasing
    assert bonuses[0] < bonuses[3]
    assert bonuses[3] == bonuses[4] == bonuses[5]  # capped at ramp_s
    assert bonuses[-1] <= 2.0 + 1e-9  # k * cap is the ceiling
    # raw streak time itself is uncapped (6 * 0.25s); only the
    # PRICED fraction saturates at the cap.
    assert abs(env._walk_persist_s - 1.5) < 1e-9


def test_streak_resets_on_a_zero_or_missing_income_tick():
    """A moving tick that does NOT earn positive course income
    (frozen/derailed/wrong-course) resets the streak to 0 and the
    bonus for that tick is skipped entirely (no partial credit)."""
    cfg = {"reward": {"k_walk_persistence_bonus": 2.0,
                       "walk_persistence_ramp_s": 1.0}}
    env = _make_env(cfg=cfg, dt=0.5)
    info = {"reward_walk_course_income": 1.0}
    wrc.walk_persistence_bonus(env, _FakeGoal(), info, 0.0, s_ref=0.05)
    assert env._walk_persist_s > 0.0
    # freeze: window fires with a non-positive value
    info2 = {"reward_walk_course_income": 0.0}
    reward2 = wrc.walk_persistence_bonus(env, _FakeGoal(), info2, 9.0,
                                          s_ref=0.05)
    assert env._walk_persist_s == 0.0
    assert reward2 == 9.0
    assert "reward_walk_persistence_bonus" not in info2
    # missing key (window not yet complete) also counts as non-positive
    env._walk_persist_s = 0.3
    info3 = {}
    wrc.walk_persistence_bonus(env, _FakeGoal(), info3, 1.0, s_ref=0.05)
    assert env._walk_persist_s == 0.0


def test_negative_k_treated_as_off():
    """A negative dose (misconfiguration) is also treated as off, not
    a penalty -- matches the <= 0.0 gate used by every sibling term."""
    env = _make_env(cfg={"reward": {"k_walk_persistence_bonus": -1.0}})
    info = {"reward_walk_course_income": 3.0}
    reward = wrc.walk_persistence_bonus(env, _FakeGoal(), info, 7.0,
                                         s_ref=0.05)
    assert reward == 7.0
    assert "reward_walk_persistence_bonus" not in info
