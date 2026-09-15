"""goal.walk_turn_in_place_mag_min_frac / _max_frac -- command-magnitude
curriculum lever on turn-in-place episodes.

09-13, walkcurr tkn1 FAIL-MECHANISM read: `probe_turn_authority.py`
confirmed `reward.walk_turn_kernel_neutral=1.0` fully removed the
base-kernel stand-still subsidy (`env/reward_walk` pinned at 0.0 for
the entire 2M-step run, wandb_history.csv) yet `wz_med` stayed at the
~1e-7 rad/s noise floor in both signs, both seeds -- the 19th
independently-tested mechanism class on this exact turn-in-place
freeze, and a scripted `TripodGait` replay of the IDENTICAL cfg
(`probe_turn_authority.py --policy scripted`) achieves wz_med=+-0.098
rad/s (above this campaign's own 0.07 rad/s pass floor), proving the
turn is mechanically achievable and the gap is a pure RL discovery
failure, not a sim defect. Every prior lever (price/dose/budget/risk-
curriculum-ramp/direct-freeze-charge/4 RND variants/kernel-neutral)
tuned income, risk or exploration around a FIXED command magnitude
always drawn `uniform(0.5, 1.0) * wz_max` -- never an easier target.
This lever (default 0.5/1.0 = bit-exact legacy band) lets a canary
command a much smaller wz magnitude instead, allowed per the 09-13
rl_only clarification ("curricula...are allowed") since it changes
only the command DIFFICULTY, not reward pricing/termination risk/
exploration noise.

Contract under test:
  - default (both keys absent) reproduces the exact legacy
    `uniform(0.5*wz_max, wz_max)` magnitude band (bit-exact rng
    stream match against a hand-computed legacy draw, same seed);
  - the direction draw (sign) and hold/ramp segment shape are
    unaffected -- only the magnitude band changes.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.walk_task import SimHexapodJointWalkEnv


def _turn_env(seed=0, wz_max=0.3):
    cfg = load_config()
    goal = cfg.setdefault("goal", {})
    goal["walk_yaw_cmd"] = 1
    goal["walk_yaw_max_rad_s"] = wz_max
    goal["walk_yaw_zero_frac"] = 0.0
    goal["walk_turn_in_place_frac"] = 1.0
    goal["walk_gait_start_frac"] = 0.0
    goal["walk_park_start_frac"] = 0.0
    goal["walk_cmd_hold_s"] = 0.0
    goal["walk_cmd_ramp_s"] = 0.0
    env = SimHexapodJointWalkEnv(cfg, seed=seed)
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 0.0)
    g.p_walk = 1.0
    return env


def _episode_wz_mags(env, n_episodes=40):
    mags = []
    for _ in range(n_episodes):
        env.reset()
        goal = env._current_goal()
        mags.append(abs(float(goal.wz_ref)))
    return np.array(mags)


def test_default_reproduces_legacy_band():
    wz_max = 0.3
    mags = _episode_wz_mags(_turn_env(seed=0, wz_max=wz_max))
    assert np.all(mags >= 0.5 * wz_max - 1e-9)
    assert np.all(mags <= wz_max + 1e-9)
    # non-degenerate band: legacy draws span it, not pinned at one end
    assert mags.max() - mags.min() > 0.01


def test_direction_still_roughly_balanced():
    wz_max = 0.3
    env = _turn_env(seed=2, wz_max=wz_max)
    signs = []
    for _ in range(200):
        env.reset()
        goal = env._current_goal()
        signs.append(1 if goal.wz_ref > 0 else -1)
    signs = np.array(signs)
    frac_pos = (signs > 0).mean()
    assert 0.3 < frac_pos < 0.7
