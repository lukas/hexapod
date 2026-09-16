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


def collapse_terminations(env, h_rel, status, terminated):
    """Walk-only and HOLD-mode collapse (low-height) terminations; moved
    verbatim from SimHexapodBalanceEnv._step_finish.
    """
    # Optional walk-only collapse termination.  Tilt alone does not
    # catch a level chassis resting on its belly, which lets a seated
    # scoot survive and collect locomotion income for the full episode.
    # Keep this opt-in so every existing task/config remains bit-exact.
    walk_max_drop_mm = float(cfg_get(
        env.cfg, "safety", "walk_max_height_drop_mm", default=0.0))
    walk_height_grace_s = float(cfg_get(
        env.cfg, "safety", "walk_height_grace_s", default=0.0))
    if (not terminated and walk_max_drop_mm > 0.0
            and env._goal_traj is not None
            and getattr(env._goal_traj, "mode", "") == "walk"
            and (env._step_i - env._seg_entry_step) * env.dt
            >= walk_height_grace_s
            and h_rel < -walk_max_drop_mm * 0.001):
        terminated = True
        status.ok = False
        status.terminate = True
        status.reason = "walk_low_height"
    # HOLD-mode collapse termination (2026-08-25, standwalk mesh2
    # rung-5 — the walk_low_height twin for hold episodes). The
    # mesh-family hold-from-scratch waves (holdload1min seed0/s1/
    # warm/dr0/ent4, holdprod-f01) all leave the PAYING plant start
    # within ~0.7M steps, and the one basin that never terminates —
    # the belly-flop freeze (h_rel ~-70 mm, 0 terminations, cur_p95
    # 0.5 A, 12/12 "survive") — quietly absorbs the policy for the
    # rest of training: income shapes (min AND product over feet)
    # have no gradient from belly back to plant, and neither 4x
    # entropy (ent4: std held 1.68, still flops) nor DR-0 evicts
    # it. Op ruling 08-24 (walk_idle_terminate block above):
    # "absorbing states beat prices; must come WITH a termination,
    # never instead of one." Terminating the basin exit (a) prices
    # it via safety_termination_penalty + term_cost_per_remaining_s
    # like every real fall, and (b) resets the env back INTO the
    # paying basin, so time-in-basin becomes the dominant, MONOTONE
    # return axis (each planted second strictly out-earns flopping
    # one tick sooner — see the HOLD_BASIN_TERM semantics bank).
    # Tilt/OC already terminate the rear-up and topple basins; this
    # catches the level-bellied survivor tilt cannot see, exactly
    # like walk_low_height for the seated scoot. Default 0.0 = off,
    # bit-exact for every existing task/config.
    if env._hold_grace_ramp is not None:
        # Gated tightening curriculum armed: read the LIVE
        # trainer-broadcast envelope (starts loose, ratchets to
        # the cfg target — see apply_hold_grace_frac), not the
        # static cfg leaves directly.
        hold_max_drop_mm = float(env._hold_grace_override_drop_mm)
        hold_height_grace_s = float(env._hold_grace_override_grace_s)
    else:
        hold_max_drop_mm = float(cfg_get(
            env.cfg, "safety", "hold_max_height_drop_mm",
            default=0.0))
        hold_height_grace_s = float(cfg_get(
            env.cfg, "safety", "hold_height_grace_s", default=0.0))
    if (not terminated and hold_max_drop_mm > 0.0
            and env._goal_traj is not None
            and getattr(env._goal_traj, "mode", "") == "hold"
            and (env._step_i - env._seg_entry_step) * env.dt
            >= hold_height_grace_s
            and h_rel < -hold_max_drop_mm * 0.001):
        terminated = True
        status.ok = False
        status.terminate = True
        status.reason = "hold_low_height"
    return terminated
