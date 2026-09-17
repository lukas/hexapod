"""Termination logic of the balance env's _step_finish: the walk/hold
collapse, hold min-foot-load, sustained-idle and per-leg duty
terminations, plus the terminated-tick settlement (early-fall horizon
cost, lower bleed settlement); moved verbatim out of sim_env.py.
"""
from __future__ import annotations

import numpy as np

from rl_move.config import cfg_get
from rl_move.robot_state import DEG2RAD


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


def lower_stall_termination(env, goal, h_err, status, terminated):
    """LOWER-mode STALL termination (``safety.lower_stall_terminate_s``,
    default 0.0 = OFF, bit-exact legacy): 2026-09-17, walkcurr
    achievability-audit follow-up.

    ``probe_lower_achievability.py`` (frozen-open-loop-action, no
    policy) found the trained descent target range (25-55mm, this
    lineage's ``goal.lower_m``) draws under 0.5A holding still at
    every depth tested up to the actuator envelope's own action-space
    ceiling — nowhere near the 2.9A safety trip. So the ~28-31mm/
    0-2-of-12-ok floor every one of the 4 reward-pricing/gate levers
    (score-prog, ratchet-partial, dense-posture, stage-gate x2
    directions) left untouched is NOT a reachability/torque-budget
    limit — the video signature (body barely descends, then stops) is
    a "safe/no-progress" absorbing state, structurally the same class
    the 08-24 operator ruling ("absorbing states beat prices; must
    come WITH a termination, never instead of one") already fixed for
    HOLD's min-foot-load absorbing state (``hold_minload_termination``
    above) and WALK's frozen-output absorbing state
    (``walk_idle_and_leg_duty_terminations`` below). This is that same
    boundary for LOWER: track the best (smallest) |height error| this
    lower segment has reached so far; if it does not improve by at
    least ``safety.lower_stall_improve_mm`` for
    ``safety.lower_stall_terminate_s`` consecutive seconds (after
    ``safety.lower_stall_terminate_grace_s`` from the ramp's own
    onset — never during the pre-ramp hold, when height_ref is still
    0 and there is nothing to stall on yet, AND only while the CURRENT
    error exceeds ``safety.lower_stall_active_floor_mm`` — a policy
    already tracking closely (error at/below the floor) has nothing
    left to "improve" and is never penalized for it), the episode
    ends. The
    existing flat ``reward.safety_termination_penalty`` +
    ``term_cost_per_remaining_s``/``term_cost_max`` terminal-settlement
    machinery (``terminal_settlement_reward``) prices ANY termination
    reason identically — no new reward code needed, exactly the
    hold_min_load/walk_idle precedent.

    Default OFF: no new state is READ (only written, harmlessly) and
    no episode outcome changes for any existing task/cfg.
    Tests: ``rl_move/tests/test_lower_stall_terminate.py``.
    """
    stall_s = float(cfg_get(env.cfg, "safety",
                            "lower_stall_terminate_s", default=0.0))
    in_lower = (env._goal_traj is not None
               and getattr(env._goal_traj, "mode", "") == "lower")
    if (terminated or stall_s <= 0.0 or not in_lower
            or h_err is None or goal is None):
        return terminated
    if abs(goal.height_ref) <= 1e-6:
        return terminated  # still in the pre-ramp hold -- nothing to stall on
    if env._lower_stall_ramp_start_step is None:
        env._lower_stall_ramp_start_step = env._step_i
    grace_s = float(cfg_get(env.cfg, "safety",
                            "lower_stall_terminate_grace_s", default=1.0))
    elapsed_s = (env._step_i
                - env._lower_stall_ramp_start_step) * env.dt
    if elapsed_s < grace_s:
        return terminated
    e_abs_mm = abs(h_err) * 1000.0
    # Only a genuinely large, persistent gap counts as "stalled" --
    # gated on the CURRENT error, not just its own running best, so a
    # policy that tracks the ramp closely the whole way (error stays
    # near 0 from the very first checked tick, nothing left to
    # "improve") is never penalized for having no headroom to shrink
    # further (test_a_genuinely_tracking_descent_never_stalls). Below
    # the floor clears the counter outright -- a policy that closes
    # the gap and re-opens it later gets a fresh grace window, exactly
    # hold_min_load's EMA-reset-on-recovery behavior.
    active_floor_mm = float(cfg_get(env.cfg, "safety",
                                    "lower_stall_active_floor_mm",
                                    default=15.0))
    if e_abs_mm <= active_floor_mm:
        env._lower_stall_best_mm = None
        env._lower_stall_low_s = 0.0
        return terminated
    improve_mm = float(cfg_get(env.cfg, "safety",
                               "lower_stall_improve_mm", default=3.0))
    if (env._lower_stall_best_mm is None
            or e_abs_mm <= env._lower_stall_best_mm - improve_mm):
        env._lower_stall_best_mm = e_abs_mm
        env._lower_stall_low_s = 0.0
    else:
        env._lower_stall_low_s += env.dt
        if env._lower_stall_low_s >= stall_s:
            terminated = True
            status.ok = False
            status.terminate = True
            status.reason = "lower_stall"
    return terminated


def hold_minload_termination(env, status, terminated):
    """HOLD-mode min-foot-load termination (+ the segment-entry EMA
    continuity and the shortfall-price parameters it shares); moved
    verbatim from SimHexapodBalanceEnv._step_finish.
    """
    # HOLD-mode MIN-FOOT-LOAD termination (2026-08-25, standwalk
    # mesh2 rung-6 -- the direct-measurement twin of hold_low_height
    # just above). holdterm40's own gate report (h_err pinned at
    # exactly 40.0-40.3 mm EVERY episode, valid_plant 0/12 both
    # DR-0 and own-DR, cur_max ~2.6 A, leg imbalance 1.8-1.9)
    # confirms the STATUS-pre-registered "alternative cheat": the
    # policy learns to hover its CHASSIS right at/around the
    # height-drop boundary while the actual per-foot load
    # distribution never recovers -- a body-height proxy alone
    # cannot see a foot that stays functionally unloaded (or one
    # foot carrying everyone else's share) as long as the chassis
    # itself stays within the drop line. This lever measures the
    # ground truth directly instead of a height proxy: if the
    # WORST (min-over-feet) touch force stays below
    # safety.hold_min_load_terminate_n for
    # safety.hold_min_load_terminate_s consecutive seconds (after
    # its own grace window), the episode ends and resets back into
    # the paying plant -- same story as hold_low_height/walk_idle_
    # terminate: "absorbing states beat prices; must come WITH a
    # termination, never instead of one" (op ruling 08-24). An EMA
    # (tau 0.25 s) smooths sensor/contact
    # chatter so one missed-contact tick can't false-trigger. A
    # foot with no touch sensor (adr<0) falls back to the
    # clearance test used elsewhere in this file (clear >
    # foot_down_mm => "up" => scored as unloaded). Default
    # hold_min_load_terminate_s=0.0 = off, bit-exact -- no new
    # state is read and no episode outcome changes for any
    # existing task/cfg.
    hold_minload_term_s = float(cfg_get(
        env.cfg, "safety", "hold_min_load_terminate_s", default=0.0))
    # Segment-entry EMA CONTINUITY (2026-09-04, standwalk
    # transtress-s1-acq8m dig-in). The legacy EMA lifecycle only
    # updates INSIDE a hold segment: at a mode_seq mid-transition
    # hold entry (walk->hold, rise->hold, walk->lower->rise->hold)
    # the EMA is zero (first hold) or stale (value frozen at the
    # END of the previous hold segment) instead of the true recent
    # per-foot load. With the training grace (1.0 s) at 4x the EMA
    # tau (0.25 s) the seed washes out before the termination clock
    # unpins (e^-4 residual), so the stale seed alone cannot fire
    # the termination -- but it DOES make any entry-window signal
    # built on the EMA (the k_hold_min_load_short price below)
    # blind or spurious exactly at the switch, the one place the
    # acq8m fires cluster. safety.hold_min_load_ema_continuous=1
    # keeps the EMA honest: seeded from the measured min force at
    # reset (feet are planted at spawn) and updated EVERY control
    # tick in EVERY mode, so a hold entry reads the actual load
    # carried through the switch. Termination clock/grace/floor are
    # untouched. Default 0 = legacy lifecycle, bit-exact.
    minload_cont = float(cfg_get(
        env.cfg, "safety", "hold_min_load_ema_continuous",
        default=0.0)) > 0.0
    minload_short_k = float(cfg_get(
        env.cfg, "reward", "k_hold_min_load_short", default=0.0))
    minload_in_hold = (env._goal_traj is not None
                       and getattr(env._goal_traj, "mode", "")
                       == "hold")
    minload_floor_n = float(cfg_get(
        env.cfg, "safety", "hold_min_load_terminate_n",
        default=0.3))
    if (env._pad_z_ref is not None
            and (hold_minload_term_s > 0.0 or minload_short_k > 0.0)
            and (minload_cont
                 or (not terminated and hold_minload_term_s > 0.0
                     and minload_in_hold))):
        minload_tau_s = max(0.25, env.dt)
        min_force_now = env._minload_min_force_now(minload_floor_n)
        env._hold_minload_ema += (env.dt / minload_tau_s) * (
            min_force_now - env._hold_minload_ema)
    if (not terminated and hold_minload_term_s > 0.0
            and minload_in_hold and env._pad_z_ref is not None):
        minload_grace_s = float(cfg_get(
            env.cfg, "safety", "hold_min_load_terminate_grace_s",
            default=0.0))
        if (env._step_i - env._seg_entry_step) * env.dt < minload_grace_s:
            env._hold_minload_low_s = 0.0
        else:
            if env._hold_minload_ema < minload_floor_n:
                env._hold_minload_low_s += env.dt
            else:
                env._hold_minload_low_s = 0.0
            if env._hold_minload_low_s >= hold_minload_term_s:
                terminated = True
                status.ok = False
                status.terminate = True
                status.reason = "hold_min_load"
    return minload_short_k, minload_in_hold, minload_floor_n, terminated


def walk_idle_and_leg_duty_terminations(env, status, terminated):
    """Sustained-idle and per-leg minimum-duty walk terminations; moved
    verbatim from SimHexapodBalanceEnv._step_finish.
    """
    # Sustained-idle termination (2026-08-24, walkcurr park_duty-
    # class closure dig-in): every anti-park PRICE tried so far
    # (idle charge, park_duty, up to bank-legal 1.5x dose) left a
    # clean, non-colliding static stand as PPO's cheapest optimum
    # for the entire episode -- an absorbing state the stagea-
    # slip1 lesson says a soft price alone cannot evict (op ruling
    # 08-24: "absorbing states beat prices; must come WITH a
    # termination, never instead of one"). This is that boundary
    # for the FROZEN-POLICY-OUTPUT absorbing state, mirroring
    # walk_max_height_drop_mm's structure exactly: if mean
    # |joint velocity| across the 18 actuated joints (own EMA,
    # _walk_qvel_ema) stays below
    # safety.walk_idle_terminate_qvel_deg_s for
    # safety.walk_idle_terminate_s consecutive seconds (after an
    # initial grace window), the episode ends with
    # reward.walk_idle_terminate_penalty (falls back to the usual
    # reward.term_penalty if unset). Joint velocity, not body
    # speed, is the deliberate choice: a body-speed version also
    # flagged a real dragging/skating gait (near-zero BODY speed,
    # legs cycling hard) and genuine wrong-direction travel
    # (reverse/sideways -- near-zero ALONG-command speed, real
    # total speed) as "idle", cutting both short and robbing them
    # of the full-episode loadslip/heading charges the
    # WALKCURR_PF bank relies on to rank them below a plain park
    # -- measured to invert that ranking in bank probes. Mean
    # |qvel| cleanly separates a literally FROZEN policy output
    # (~5e-5 rad/s, pure settle jitter) from every other scripted
    # behavior (>=0.1 rad/s, ~35x higher) regardless of whether
    # the legs' motion translates into body progress, wrong-way
    # progress, or slip -- see the WALKCURR_PF_IDLE_TERM bank.
    # Default walk_idle_terminate_s=0.0 = off, bit-exact legacy
    # (no new state read, no behavior change) -- every existing
    # task/cfg is unaffected until a walkcurr rung explicitly arms
    # this.
    walk_idle_term_s = float(cfg_get(
        env.cfg, "safety", "walk_idle_terminate_s", default=0.0))
    if (not terminated and walk_idle_term_s > 0.0
            and env._goal_traj is not None
            and getattr(env._goal_traj, "mode", "") == "walk"):
        idle_grace_s = float(cfg_get(
            env.cfg, "safety", "walk_idle_terminate_grace_s",
            default=0.0))
        idle_floor = max(float(cfg_get(
            env.cfg, "safety", "walk_idle_terminate_qvel_deg_s",
            default=2.0)) * DEG2RAD, 1e-9)
        idle_tau = max(0.25, env.dt)
        qvel_now = float(np.mean(np.abs(env.data.qvel[env._vadr])))
        env._walk_qvel_ema += (env.dt / idle_tau) * (
            qvel_now - env._walk_qvel_ema)
        if (env._step_i - env._seg_entry_step) * env.dt < idle_grace_s:
            env._walk_idle_low_s = 0.0
        else:
            if env._walk_qvel_ema < idle_floor:
                env._walk_idle_low_s += env.dt
            else:
                env._walk_idle_low_s = 0.0
            if env._walk_idle_low_s >= walk_idle_term_s:
                terminated = True
                status.ok = False
                status.terminate = True
                status.reason = "walk_idle_terminate"
    # Per-LEG minimum-duty termination (safety.walk_leg_duty_
    # terminate_s, 2026-09-07 -- walkcurr role-aware-mechanism gap).
    # CURRENT_TRUTHS 09-05 ~22:3x / 09-07 ~04:4x-~09:5x/~11:5x
    # established that a heading-dependent leg PAIR (the L1/L4
    # middle pair for forward commands, the L0/L5 front pair for
    # rear-ish commands -- the hexagon's one diametrically-opposite
    # pair with no fore/aft neighbor, whichever pair that is for
    # THIS commanded heading) is a genuinely CHEAPER STABLE 4-leg
    # gait: 11 independently-designed PER-TICK PRICE mechanisms
    # (walk_duty_gate x9 dose/threshold variants, walk_swing_gate
    # x5, walk_duty_band_gate x2, walk_gait_gate+k_step_event x6)
    # all failed against it, because a price is just amortized
    # against the cheap gait's income for the whole episode -- see
    # each mechanism's own closure note. Per the op ruling already
    # validated on hold_min_load_terminate/walk_idle_terminate
    # above ("absorbing states beat prices; must come WITH a
    # termination, never instead of one"), this is the per-LEG
    # analogue, deliberately UNIFORM across all 6 legs (no
    # heading-conditioned role table needed): track a slow EMA of
    # each leg's own ground-contact duty (own sensor, same
    # on=force>0.5 convention as the rest of this file); if ANY
    # leg's EMA duty stays below safety.walk_leg_duty_terminate_
    # floor for safety.walk_leg_duty_terminate_s consecutive
    # seconds (after a grace window), the episode ends -- exactly
    # like a fall, denying ALL further reward, which a per-tick
    # price structurally cannot do regardless of dose. The EMA
    # (not an event/count) is deliberate: a brief one-or-two-tick
    # "token" touch barely moves it (same chatter-smoothing
    # reasoning as hold_min_load's own EMA), so a leg must
    # accumulate REAL sustained ground time to clear the floor --
    # unlike the already-closed walk_gait_gate/walk_swing_gate
    # event-based designs, which a rare periodic swing could
    # satisfy without ever loading the leg (the exact dodge
    # measured on the sde-family idle-terminate/gait-gate levers,
    # CURRENT_TRUTHS 09-05 ~13:1x/~14:3x). Floor default 0.05 sits
    # below the passing-checkpoint low-duty band the 09-07 ~04:4x
    # diagnostic measured (0.10-0.30 on PASSING episodes, one as
    # low as 0.10) so a genuinely-passing graded gait is not
    # charged; tau default 1.0s (roughly one stride period at this
    # campaign's commanded speeds) smooths a single swing's
    # transient dip without hiding a truly chronic near-zero-duty
    # leg over walk_leg_duty_terminate_s (default off) seconds.
    # Default walk_leg_duty_terminate_s=0.0 = off, bit-exact legacy
    # (no new state read beyond the always-initialized EMA seed,
    # no behavior change) for every existing task/cfg.
    walk_ldt_s = float(cfg_get(
        env.cfg, "safety", "walk_leg_duty_terminate_s", default=0.0))
    if (not terminated and walk_ldt_s > 0.0
            and env._goal_traj is not None
            and getattr(env._goal_traj, "mode", "") == "walk"):
        ldt_grace_s = float(cfg_get(
            env.cfg, "safety", "walk_leg_duty_terminate_grace_s",
            default=0.0))
        ldt_floor = float(cfg_get(
            env.cfg, "safety", "walk_leg_duty_terminate_floor",
            default=0.05))
        ldt_tau = max(float(cfg_get(
            env.cfg, "safety", "walk_leg_duty_terminate_tau_s",
            default=1.0)), env.dt)
        # floor_rel_frac is fixed at 0.0 here (the relative floor was
        # never configured); walk_legduty_term_tick keeps the parameter.
        in_grace = ((env._step_i - env._seg_entry_step) * env.dt
                    < ldt_grace_s)
        on_now = []
        for f in range(6):
            adr = env._touch_adr[f]
            force = (max(0.0, float(env.data.sensordata[adr]))
                      if adr >= 0 else 0.0)
            on_now.append(1.0 if force > 0.5 else 0.0)
        from rl_move.sim.walk_task import walk_legduty_term_tick
        (env._walk_legduty_ema, env._walk_legduty_low_s,
         worst_low_s) = walk_legduty_term_tick(
            env._walk_legduty_ema, env._walk_legduty_low_s,
            on=on_now, dt=env.dt, tau_s=ldt_tau, floor=ldt_floor,
            floor_rel_frac=0.0, in_grace=in_grace)
        if worst_low_s >= walk_ldt_s:
            terminated = True
            status.ok = False
            status.terminate = True
            status.reason = "walk_leg_duty_terminate"
    return terminated
