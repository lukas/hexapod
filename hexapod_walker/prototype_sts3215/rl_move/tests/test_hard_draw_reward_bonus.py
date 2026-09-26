"""reward.k_hard_draw_bonus -- per-episode DR-draw-difficulty reward
MULTIPLIER (standwalk track, 2026-09-26, closing the input-observability
grid).

Background: park-price (k_park_duty), measured-velocity feedback
(goal.walk_obs_body_vel=3), per-joint current-sense and per-foot
contact/load-sense observation channels are now ALL instrument-
confirmed NULL (CURRENT_TRUTHS 2026-09-26 ~06:3x, 8+ arch/seed cells
via gait_valid_rate.py's Wilson-CI two-proportion test) at the
2.25deg/0.035pct no-ramp DR ceiling: no tested input channel lets any
architecture beat its own ceil20 zero-shot parent. draw_feasibility.py
independently found the DR draw ALONE predicts gait_valid at ~87% CV
accuracy regardless of which checkpoint trained on it (link_scale_range
span + zero_bias_max_deg dominate the fit) -- the walker's INPUT is not
the bottleneck, so the next untried lever is the LEARNING SIGNAL: give
harder draws a bigger say in the policy-gradient loss instead of
another observation channel.

This is a REWEIGHTING, not a new reward term: every step's WHOLE reward
is multiplied by `1.0 + k_hard_draw_bonus * difficulty`, where
`difficulty in [0, 1]` is a fixed, already-evidence-backed proxy (this
episode's own link_scale span / configured link_len_leg_pct ceiling,
averaged with max|zero_bias| / configured joint_zero_bias_deg ceiling,
each self-normalizing against the ACTIVE dr_scale-scaled ceiling, not a
hardcoded constant). Because it scales the return uniformly within an
episode, it cannot change what is rewarded (same optimum, same shape)
-- only how much this episode's transitions count in the batch, exactly
like an importance/curriculum weight.

Contract under test (RESEARCH_RULES "Tests": fast, mechanics-only):
  - default OFF (`reward.k_hard_draw_bonus` unset or 0.0) ->
    `_compute_hard_draw_mult()` is always 1.0 and `_post_step` never
    rebuilds the reward tuple -- bit-exact vs a keyless env;
  - the difficulty formula: an exactly-nominal draw (link_scale==1.0
    everywhere, zero_bias==0) -> difficulty 0.0 -> mult == 1.0; a
    draw pinned at both configured ceilings -> difficulty 1.0 -> mult
    == 1.0 + k; a half-ceiling draw on ONE axis only -> mult == 1.0 +
    0.25*k (each axis is half the average);
  - self-normalizing: doubling the configured ceiling while keeping
    the same absolute draw halves that axis's contribution;
  - end-to-end: stepping a real env with k>0 multiplies the same-seed
    keyless env's reward by exactly this episode's own mult, every
    tick, with no other reward term disturbed.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.servo_model import SimServoParams
from rl_move.sim.walk_task import SimHexapodJointWalkEnv


def _walk_env(seed: int, k_hard_draw: float | None = None,
              dr_scale: float = 1.0) -> SimHexapodJointWalkEnv:
    cfg = load_config()
    if k_hard_draw is not None:
        cfg.setdefault("reward", {})["k_hard_draw_bonus"] = k_hard_draw
    env = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(None), randomize=True,
        dr_scale=dr_scale, episode_seconds=4, seed=seed, cfg=cfg)
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 1.0 if m == "walk" else 0.0)
    return env


# --------------------------------------------------------------- default off

def test_default_unset_mult_is_one():
    env = _walk_env(seed=0)
    env.reset()
    assert env._hard_draw_mult == 1.0
    env.close()


def test_explicit_zero_mult_is_one():
    env = _walk_env(seed=0, k_hard_draw=0.0)
    env.reset()
    assert env._hard_draw_mult == 1.0
    env.close()


def test_default_off_rewards_bit_exact_vs_keyless():
    action = None
    env_a = _walk_env(seed=3)
    env_b = _walk_env(seed=3, k_hard_draw=0.0)
    for env in (env_a, env_b):
        env.reset()
        if action is None:
            action = np.zeros(env.action_space.shape, dtype=np.float32)
    for _ in range(20):
        _, r_a, ta, tra, _ = env_a.step(action)
        _, r_b, tb, trb, _ = env_b.step(action)
        assert r_a == r_b
        assert ta == tb and tra == trb
    env_a.close()
    env_b.close()


# ------------------------------------------------------------- the formula

def test_nominal_draw_is_zero_difficulty():
    env = _walk_env(seed=1, k_hard_draw=2.0)
    env.reset()
    link_pct = env.randomizer.ranges.link_len_leg_pct
    bias_deg = env.randomizer.ranges.joint_zero_bias_deg
    assert link_pct > 0 and bias_deg > 0  # else this test proves nothing
    env._ep_rand = dataclasses.replace(
        env._ep_rand,
        link_scale=np.ones((6, 3)),
        joint_zero_bias_rad=np.zeros(18))
    assert env._compute_hard_draw_mult() == pytest.approx(1.0)
    env.close()


def test_ceiling_draw_is_full_difficulty():
    k = 2.0
    env = _walk_env(seed=1, k_hard_draw=k)
    env.reset()
    link_pct = env.randomizer.ranges.link_len_leg_pct
    bias_deg = env.randomizer.ranges.joint_zero_bias_deg
    link_scale = np.ones((6, 3))
    link_scale[0, 0] = 1.0 - link_pct   # lo
    link_scale[0, 1] = 1.0 + link_pct   # hi -> full 2*link_pct span
    env._ep_rand = dataclasses.replace(
        env._ep_rand,
        link_scale=link_scale,
        joint_zero_bias_rad=np.full(18, np.deg2rad(bias_deg)))
    assert env._compute_hard_draw_mult() == pytest.approx(1.0 + k)
    env.close()


def test_single_axis_half_ceiling_is_quarter_difficulty():
    k = 4.0
    env = _walk_env(seed=1, k_hard_draw=k)
    env.reset()
    link_pct = env.randomizer.ranges.link_len_leg_pct
    link_scale = np.ones((6, 3))
    # span == link_pct (half of the full 2*link_pct ceiling) -> that
    # axis's fraction is 0.5; zero-bias axis untouched (0) -> average
    # difficulty == 0.25 -> mult == 1 + 0.25*k.
    link_scale[0, 0] = 1.0 - link_pct / 2.0
    link_scale[0, 1] = 1.0 + link_pct / 2.0
    env._ep_rand = dataclasses.replace(
        env._ep_rand, link_scale=link_scale,
        joint_zero_bias_rad=np.zeros(18))
    assert env._compute_hard_draw_mult() == pytest.approx(1.0 + 0.25 * k)
    env.close()


def test_self_normalizing_to_configured_ceiling():
    # Same absolute zero-bias draw, but a randomizer whose CONFIGURED
    # ceiling (dr_scale) is doubled, halves that axis's contribution --
    # the score reads relative to the ACTIVE ceiling, not a constant.
    k = 2.0
    env_full = _walk_env(seed=2, k_hard_draw=k, dr_scale=1.0)
    env_full.reset()
    env_half = _walk_env(seed=2, k_hard_draw=k, dr_scale=0.5)
    env_half.reset()
    bias_deg_full = env_full.randomizer.ranges.joint_zero_bias_deg
    fixed_bias_rad = np.full(18, np.deg2rad(bias_deg_full))
    env_full._ep_rand = dataclasses.replace(
        env_full._ep_rand, link_scale=np.ones((6, 3)),
        joint_zero_bias_rad=fixed_bias_rad)
    env_half._ep_rand = dataclasses.replace(
        env_half._ep_rand, link_scale=np.ones((6, 3)),
        joint_zero_bias_rad=fixed_bias_rad)
    mult_full = env_full._compute_hard_draw_mult()
    mult_half = env_half._compute_hard_draw_mult()
    # env_half's ceiling is HALF env_full's (dr_scale 0.5 vs 1.0), same
    # absolute bias draw -> double the fraction (clipped at the axis's
    # own 1.0), so env_half's difficulty >= env_full's.
    assert mult_half >= mult_full
    env_full.close()
    env_half.close()


# ------------------------------------------------------------- end-to-end

def test_post_step_scales_reward_by_this_episode_mult():
    k = 3.0
    env_hd = _walk_env(seed=5, k_hard_draw=k)
    env_hd.reset()
    # Force a known, non-1.0 mult directly (bypassing the exact draw,
    # and NOT touching _ep_rand -- some reward terms read _ep_rand's
    # bias/link fields every tick, not just at reset, so mutating it
    # here would change env_hd's own dynamics and confound the
    # comparison) to isolate _post_step's multiply-and-rebuild path
    # from the difficulty-score math already covered above.
    env_hd._hard_draw_mult = 1.75
    env_base = _walk_env(seed=5, k_hard_draw=0.0)
    env_base.reset()
    action = np.zeros(env_hd.action_space.shape, dtype=np.float32)
    for _ in range(10):
        _, r_hd, _, _, _ = env_hd.step(action)
        _, r_base, _, _, _ = env_base.step(action)
        assert r_hd == pytest.approx(r_base * 1.75)
    env_hd.close()
    env_base.close()
