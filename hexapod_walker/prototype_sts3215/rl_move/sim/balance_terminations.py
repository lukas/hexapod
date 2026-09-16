"""Termination logic of the balance env's _step_finish: the walk/hold
collapse, hold min-foot-load, sustained-idle and per-leg duty
terminations, plus the terminated-tick settlement (early-fall horizon
cost, lower bleed settlement); moved verbatim out of sim_env.py.
"""
from __future__ import annotations

from rl_move.config import cfg_get


def terminal_settlement_reward(env, depth_frac, lower_score_mode, parts, pen, reward, terminated):
    """Terminated-tick settlement (early-fall horizon cost, lower bleed
    settlement); moved verbatim from SimHexapodBalanceEnv._step_finish.
    """
    if terminated:
        # Early-fall horizon cost — same key/semantics as the
        # _step_begin site (reward.term_cost_per_remaining_s,
        # default 0.0 = legacy bit-exact); only safety
        # terminations are charged, never time-limit truncation.
        k_rem = float(cfg_get(env.cfg, "reward",
                              "term_cost_per_remaining_s",
                              default=0.0))
        if k_rem > 0.0:
            rem_cost = k_rem * max(env._active_episode_steps()
                                   - env._step_i,
                                   0) * env.dt
            # reward.term_cost_max: same bounded-terminal-cost
            # semantics as the _step_begin site above (08-17,
            # fb_20260817T005114 item 5); default 0 = off.
            cap = float(cfg_get(env.cfg, "reward",
                                "term_cost_max", default=0.0))
            if cap > 0.0:
                rem_cost = min(rem_cost, cap)
            pen += rem_cost
        parts["reward_termination"] = -pen
        reward -= pen
        # Terminal bleed-settlement (2026-09-13, lowerscoreprog-s1
        # A/B pair FAIL-MECHANISM escalation: the pre-registered
        # fork fired -- `s1-track01-cont15m` (k_lower_score_track
        # 1.0->0.1) plateaued/decayed at depth_frac ~0.24 while the
        # unchanged k=1.0 sibling `s1-cont15m` kept climbing past
        # 0.33 over the SAME +9M budget, and the weakened arm's
        # rise over_current terms regressed vs the s1-6m parent --
        # so the gate's own verdict is "the fix is NOT scale": a
        # WEAK continuous `reward_lower_track` charge just removes
        # the death-vs-park pricing inversion; the STRONG (k=1.0)
        # charge that actually drives depth also makes tipping over
        # early strictly cheaper than surviving to park (a whole
        # surviving lower episode integrates ~-450..-600 of bleed;
        # dying costs at most the flat+horizon term-fee cap), which
        # is exactly the tilt_roll-at-spawn exploit caught on video
        # in the s1-6m owncfg eval. This charges, ONCE, at
        # termination, the SAME per-tick `reward_lower_track` rate
        # (`-klst * (1 - depth_frac) ** 2`, at the depth_frac the
        # episode actually reached) projected over the remaining
        # ticks it would have kept paying had it survived to the
        # horizon -- i.e. the bleed the death would otherwise have
        # dodged. A death at low depth_frac now pays close to what
        # a park at that same depth would have paid; a death AFTER
        # real progress (higher depth_frac) is charged little,
        # exactly as a survivor would be. Lower-episodes only
        # (`lower_score_mode`); zero for every other mode. Default OFF
        # (reward.lower_term_bleed_settle=0): bit-exact, no new
        # arithmetic touches any existing lineage. Tests:
        # rl_move/tests/test_lower_term_bleed_settle.py.
        if (lower_score_mode
                and float(cfg_get(
                    env.cfg, "reward", "lower_term_bleed_settle",
                    default=0.0)) == 1.0):
            rem_ticks = max(
                env._active_episode_steps() - env._step_i, 0)
            settle = (1.0 - depth_frac) ** 2 * rem_ticks
            cap = float(cfg_get(
                env.cfg, "reward", "lower_term_bleed_settle_max",
                default=0.0))
            if cap > 0.0:
                settle = min(settle, cap)
            parts["reward_lower_term_bleed"] = -settle
            reward -= settle
    return reward
