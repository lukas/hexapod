"""reward.k_walk_foot_load_min -- per-tick FORCE-based per-foot load-min
bonus (standwalk track, 2026-09-26 ~14:2x control-experiment follow-up).

Background: an open-loop scripted TripodGait (zero learning, one fixed
per-tick target trajectory) was found to sacrifice the IDENTICAL legs on
the IDENTICAL per-leg-asymmetry DR draws as every trained RL transformer
at the ceil225 rung (CURRENT_TRUTHS 2026-09-26 ~14:2x) -- gait_valid at
that ceiling measures the fixed plant never reaching the ground under a
hard draw's geometry, controller-independent, not a training failure.
`reward.k_park_duty` (a behavior-pattern charge on per-leg contact DUTY)
was already tried alone and closed as a null lever (2026-09-26 ~05:5x): a
policy that cannot sense/adapt just eats a bigger flat penalty for the
same behavior. This is a structurally different mechanism -- a per-tick
bonus on the actual FORCE of the worst-loaded foot (soft-min, same
log-sum-exp/tau=0.15 shape as `walk_reward_recover`'s already-proven
getup/recover-role "M" potential term), meant to reward literally
extending an under-reaching leg until it carries load, paired with (but
not requiring) `obs.foot_contact_sense`.

Contract under test (RESEARCH_RULES "Tests": fast, mechanics-only):
  - `walk_foot_load_min_bonus()` is a pure function: k<=0 -> exactly 0.0;
    all-zero forces -> exactly 0.0; a saturating (>>scale) force on
    every foot -> bonus ~= k; a single hovering (0 N) foot among five
    saturated feet stays near 0 regardless of the other five, and is
    ORDER-INDEPENDENT (which index is the zero one does not matter);
    monotone increasing in the minimum foot's own force; always bounded
    in [0, k].
  - default OFF (`reward.k_walk_foot_load_min` unset or 0.0) -> bit-exact
    reward/term/trunc vs a keyless env across a real rollout.
  - end-to-end: stepping a real walk-mode env with k>0 produces
    `info["reward_walk_foot_load_min"]` in [0, k] whenever it fires, and
    the k>0 run's total episode reward exceeds the keyless run's by
    EXACTLY the sum of those per-tick bonuses (no other reward term is
    disturbed).
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.servo_model import SimServoParams
from rl_move.sim.walk_task import SimHexapodJointWalkEnv, walk_foot_load_min_bonus


# --------------------------------------------------------- pure function

def test_k_zero_or_negative_is_always_zero():
    assert walk_foot_load_min_bonus([0, 1, 2, 3, 4, 5], k=0.0) == 0.0
    assert walk_foot_load_min_bonus([9, 9, 9, 9, 9, 9], k=0.0) == 0.0
    assert walk_foot_load_min_bonus([9, 9, 9, 9, 9, 9], k=-1.0) == 0.0


def test_all_zero_forces_is_zero_bonus():
    assert walk_foot_load_min_bonus([0.0] * 6, k=5.0) == pytest.approx(0.0)


def test_all_saturated_forces_approach_k():
    # force >> scale_n saturates tanh -> x ~= 1 for every foot -> the
    # soft-min of six near-1 values is itself near 1 -> bonus ~= k.
    r = walk_foot_load_min_bonus([50.0] * 6, k=3.0, scale_n=5.0)
    assert r == pytest.approx(3.0, abs=1e-3)


def test_single_hovering_foot_stays_near_zero_regardless_of_peers():
    k = 4.0
    r_all_loaded = walk_foot_load_min_bonus([5.0] * 6, k=k, scale_n=5.0)
    r_low_peers = walk_foot_load_min_bonus(
        [0.0, 5.0, 5.0, 5.0, 5.0, 5.0], k=k, scale_n=5.0)
    r_high_peers = walk_foot_load_min_bonus(
        [0.0, 500.0, 500.0, 500.0, 500.0, 500.0], k=k, scale_n=5.0)
    # one hovering foot pulls the soft-min WAY down from the all-loaded
    # case, and (the actual "cannot be bought" property) piling ten
    # thousand percent more raw force onto the five already-saturating
    # peers barely moves it, because THEIR tanh term is already ~1
    # either way -- the min is set by the zero foot, not diluted by a
    # mean over the other five.
    assert r_low_peers < 0.4 * r_all_loaded
    assert r_high_peers < 0.4 * r_all_loaded
    assert abs(r_low_peers - r_high_peers) < 0.05 * k


def test_order_independent():
    k = 2.0
    a = walk_foot_load_min_bonus([0.0, 5, 5, 5, 5, 5], k=k)
    b = walk_foot_load_min_bonus([5, 5, 0.0, 5, 5, 5], k=k)
    c = walk_foot_load_min_bonus([5, 5, 5, 5, 5, 0.0], k=k)
    assert a == pytest.approx(b) == pytest.approx(c)


def test_monotone_in_the_minimum_foot_force():
    k = 1.0
    lo = walk_foot_load_min_bonus([1.0, 5, 5, 5, 5, 5], k=k)
    mid = walk_foot_load_min_bonus([2.5, 5, 5, 5, 5, 5], k=k)
    hi = walk_foot_load_min_bonus([4.0, 5, 5, 5, 5, 5], k=k)
    assert lo < mid < hi


def test_bounded_in_zero_k():
    rng = np.random.default_rng(0)
    k = 2.5
    for _ in range(200):
        forces = rng.uniform(0.0, 200.0, size=6)
        r = walk_foot_load_min_bonus(forces, k=k)
        assert -1e-9 <= r <= k + 1e-9


# ------------------------------------------------------------- env-level

def _walk_env(seed: int, k: float | None = None) -> SimHexapodJointWalkEnv:
    cfg = load_config()
    if k is not None:
        cfg.setdefault("reward", {})["k_walk_foot_load_min"] = k
    env = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(None), randomize=True,
        dr_scale=1.0, episode_seconds=4, seed=seed, cfg=cfg)
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 1.0 if m == "walk" else 0.0)
    return env


def test_default_unset_is_bit_exact_vs_keyless():
    action = None
    env_a = _walk_env(seed=3)
    env_b = _walk_env(seed=3, k=0.0)
    for env in (env_a, env_b):
        env.reset()
        if action is None:
            action = np.zeros(env.action_space.shape, dtype=np.float32)
    for _ in range(150):
        _, r_a, ta, tra, info_a = env_a.step(action)
        _, r_b, tb, trb, info_b = env_b.step(action)
        assert r_a == r_b
        assert ta == tb and tra == trb
        assert "reward_walk_foot_load_min" not in info_a
        assert "reward_walk_foot_load_min" not in info_b
    env_a.close()
    env_b.close()


def test_on_arm_pays_exactly_the_logged_bonus_and_nothing_else():
    action = None
    k = 3.0
    env_off = _walk_env(seed=5, k=0.0)
    env_on = _walk_env(seed=5, k=k)
    for env in (env_off, env_on):
        env.reset()
        if action is None:
            action = np.zeros(env.action_space.shape, dtype=np.float32)
    total_off = 0.0
    total_on = 0.0
    bonus_sum = 0.0
    saw_bonus = False
    for _ in range(200):
        _, r_off, _, _, info_off = env_off.step(action)
        _, r_on, _, _, info_on = env_on.step(action)
        total_off += r_off
        total_on += r_on
        b = info_on.get("reward_walk_foot_load_min", 0.0)
        if b:
            saw_bonus = True
            assert -1e-9 <= b <= k + 1e-9
        bonus_sum += b
    env_off.close()
    env_on.close()
    assert saw_bonus, "expected the bonus to fire at least once over 200 walk-mode ticks"
    assert total_on == pytest.approx(total_off + bonus_sum, abs=1e-6)
