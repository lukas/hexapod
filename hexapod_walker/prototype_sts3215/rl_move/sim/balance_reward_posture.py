"""First-principles posture prices of the balance env's _step_finish:
support margin, load evenness, torque headroom debt, action-rate /
stance-contact / stance-clearance / flag-leg shaping and the terminal
end-posture pricing; moved verbatim out of sim_env.py.
"""
from __future__ import annotations

import numpy as np

from rl_move.config import cfg_get

from .balance_helpers import action_rate_penalty, support_margin_m, torque_headroom_debt_step


def posture_support_load_headroom_reward(env, goal, parts, reward):
    """Support-margin, load-even and torque-headroom prices; moved verbatim
    from SimHexapodBalanceEnv._step_finish.
    """
    # --- First-principles posture terms (operator 08-08 ~20:45Z,
    # default OFF). WHY a waving leg is bad: smaller support polygon
    # (tips), load concentration (hot knees), wasted hold torque.
    # Static-hold pricing was measured CORRECT (hip 0.149 Nm -> 0.179 A,
    # actuator carries full gravity torque; diagnosis 08-08 cycle 12):
    # the defect is that the LINEAR current charge is invariant to load
    # distribution, so concentration is free. These two GLOBAL terms
    # price the physics directly, in every mode (declared routing:
    # GLOBAL - they encode "don't tip / don't concentrate heat", not
    # gait morphology). The unload target leg is skipped like the
    # other stance terms.
    k_margin = float(cfg_get(env.cfg, "reward", "k_support_margin",
                             default=0.0))
    k_even = float(cfg_get(env.cfg, "reward", "k_load_even",
                           default=0.0))
    if (k_margin > 0.0 or k_even > 0.0):
        skip = int(goal.unload_leg) if (
            goal is not None and goal.unload_leg is not None) else -1
        forces, feet_xy = [], []
        for i in range(6):
            if i == skip or env._touch_adr[i] < 0:
                continue
            f = max(float(env.data.sensordata[env._touch_adr[i]]), 0.0)
            forces.append(f)
            if f > 0.5 and env._pad_bids[i] >= 0:
                feet_xy.append(env.data.xpos[env._pad_bids[i], :2])
        if k_margin > 0.0 and len(feet_xy) >= 3:
            # Reward CoM depth inside the support polygon, saturating
            # at 40 mm: centered stances earn the cap, near-edge or
            # outside-CoM poses earn ~0/negative. Belly rest (<3 foot
            # contacts, chassis supported) is exempt by the gate.
            m = support_margin_m(np.asarray(feet_xy),
                                 env.data.subtree_com[0, :2])
            r_margin = k_margin * float(np.clip(m, -0.04, 0.04)) / 0.04
            parts["reward_support_margin"] = r_margin
            reward += r_margin
        ftot = float(np.sum(forces))
        if k_even > 0.0 and ftot > 1.0:
            # Load concentration: Herfindahl index of foot normal
            # forces. Even 6-leg load = 1/6 (charge 0); everything on
            # one foot = 1 (max charge). Dense, mode-independent.
            fr = np.asarray(forces) / ftot
            hhi = float(np.sum(fr ** 2))
            r_even = -k_even * (hhi - 1.0 / len(forces))
            parts["reward_load_even"] = r_even
            reward += r_even
    # Per-actuator torque-HEADROOM debt (standwalk track, 2026-09-11 —
    # the structural mechanism named after both `k_current_hot` (dose
    # bracket b23k12/k6/b23k36) and `k_load_even` (dose bracket 2/8/
    # 16/32) closed short of a clean PASS on the b23k12 flat-start
    # rise stall-fight). Root-cause chain (09-11 ~08:0x DIG-IN,
    # CURRENT_TRUTHS.md): a SINGLE femur-row servo pins at torque
    # saturation (raw_current's own 2.2 N-m x 1.2 A/N-m = 2.64 A rail,
    # see the raw_current comment above) for up to 23% of the episode
    # while the existing per-tick current_hot price stays a flat,
    # MEMORYLESS quadratic on instantaneous current (~1.4/tick at
    # this lineage's dose) — cheaper than the ~3.4/tick rise/hold/
    # finish income, so fighting through isometrically instead of
    # momentarily unloading is the reward optimum. Raising the FLAT
    # per-tick price alone (b23k36, ~4.2/tick, ABOVE that income) did
    # NOT move the residual at all (over_current pinned at 1/12
    # across a 3.5x price range) — so the missing axis is DURATION,
    # not magnitude: this term is a per-actuator leaky integrator
    # ("debt") that only grows while a servo dwells inside a red zone
    # just below the physical torque-saturation current, decaying
    # back to 0 once it unloads, then prices the debt QUADRATICALLY.
    # A brief transient spike (a few ticks) barely moves the debt and
    # costs almost nothing (no new tax on ordinary current use
    # anywhere else in the episode); a SUSTAINED stall-fight compounds
    # every tick it continues, so the charge escalates past whatever
    # a flat per-tick price could reach for the exact pathology named
    # above, without needing a heavier tax on brief/harmless spikes.
    # Dense, mode-independent (declared routing: GLOBAL, same as
    # k_current_hot/k_load_even — "don't let any one actuator stall
    # near its ceiling", not gait morphology). Bit-exact OFF by
    # default: the debt array is only allocated/updated when enabled.
    # Enable: --cfg-set reward.k_torque_headroom=<k>.
    k_headroom = float(cfg_get(env.cfg, "reward", "k_torque_headroom",
                                default=0.0))
    if k_headroom > 0.0 and env._state.servo_current is not None:
        cur = np.abs(env._state.servo_current)
        if (getattr(env, "_torque_debt", None) is None
                or env._torque_debt.shape != cur.shape):
            env._torque_debt = np.zeros_like(cur)
        alpha_d = min(max(env.dt, 0.0), 1.0)
        env._torque_debt = torque_headroom_debt_step(
            env._torque_debt, cur, 2.64, 0.3, alpha_d)
        r_headroom = -k_headroom * float(np.sum(env._torque_debt ** 2))
        parts["reward_torque_headroom"] = r_headroom
        parts["torque_headroom_debt_max"] = float(
            np.max(env._torque_debt))
        reward += r_headroom
    return reward


def stance_shaping_reward(env, clipped, goal, parts, reward):
    """Action-rate, stance-contact, stance-clearance and flag-leg shaping;
    moved verbatim from SimHexapodBalanceEnv._step_finish.
    """
    # Action-rate/smoothness repricing (standwalk track, 2026-09-12 --
    # see action_rate_penalty's docstring for the full root-cause
    # chain: the 9th-and-last flat/income-relative CURRENT price still
    # collapsed on the same late-tail over_current tail, so this
    # prices the policy's own commanded-action dithering directly
    # instead of another guess at the current-price axis. Dense,
    # GLOBAL, mode-independent (same routing convention as
    # k_current_hot/k_torque_headroom above) -- a smooth hold or a
    # smooth move both pay ~0; only rapid direction reversal in the
    # normalized action space is charged. Bit-exact OFF by default
    # (reward.k_action_rate=0): reads self._prev_action, which is
    # ALREADY always tracked (obs needs it) so this term allocates no
    # new per-episode state at all. Enable: --cfg-set
    # reward.k_action_rate=<k>.
    k_act_rate = float(cfg_get(env.cfg, "reward", "k_action_rate",
                                default=0.0))
    if k_act_rate > 0.0:
        r_act_rate = -k_act_rate * action_rate_penalty(
            env._prev_action, clipped)
        parts["reward_action_rate"] = r_act_rate
        reward += r_act_rate
    # Stance-contact shaping (default OFF): during stance modes the
    # kernel is blind to how many feet carry the body, so a 3-leg
    # tripod scores like a 6-leg stance (and cooks servos). Pay a
    # small bonus per loaded foot; for unload episodes the target
    # leg is excluded (it is SUPPOSED to be in the air).
    k_stance = float(cfg_get(env.cfg, "reward", "k_stance_contact",
                             default=0.0))
    mode_now = env._goal_traj.mode if env._goal_traj else ""
    if k_stance > 0.0 and mode_now in ("hold", "lean", "track",
                                       "unload", "raise"):
        skip = int(goal.unload_leg) if (
            goal is not None and goal.unload_leg is not None) else -1
        feet = [i for i in range(6) if i != skip]
        n_on = sum(1 for i in feet
                   if env._touch_adr[i] >= 0
                   and float(env.data.sensordata[env._touch_adr[i]])
                   > 0.5)
        r_stance = k_stance * n_on / len(feet)
        parts["reward_stance"] = r_stance
        reward += r_stance
    # Stance-clearance penalty (default OFF): the contact bonus above
    # failed to break the learned tripod in cw-stance-even — a foot
    # held in the air earns nothing for moving DOWN until it actually
    # touches, so PPO never feels a gradient toward ground. Charging
    # for height above the episode-start (grounded) pad z is dense:
    # every millimeter a hovering foot descends pays immediately.
    # "raise" is exempt: cw-stance-clear collapsed raise to 0/6
    # (parked 13-17 mm short) while hold/rise/lower stayed perfect —
    # lifting the body requires transient foot repositioning that a
    # z-referenced clearance charge punishes.
    k_clear = float(cfg_get(env.cfg, "reward", "k_stance_clearance",
                            default=0.0))
    if k_clear > 0.0 and env._pad_z_ref is not None \
            and mode_now in ("hold", "lean", "track", "unload"):
        skip = int(goal.unload_leg) if (
            goal is not None and goal.unload_leg is not None) else -1
        clear = 0.0
        for i in range(6):
            if i == skip or env._pad_bids[i] < 0:
                continue
            clear += max(float(env.data.xpos[env._pad_bids[i], 2])
                         - env._pad_z_ref[i], 0.0)
        r_clear = -k_clear * clear
        parts["reward_clearance"] = r_clear
        reward += r_clear
    # Flag-leg penalty (default OFF): the 08-08 video review found
    # every walk-lineage policy (and the stance line's lower endings)
    # parking one leg straight up in the air — modes exempt from the
    # stance-clearance penalty (walk/rise/lower/raise) have no
    # gradient against it. Charge only clearance ABOVE a generous
    # allowance (default 50 mm over the episode-start pad z), so
    # normal swing (~10-20 mm) and rise/lower repositioning stay
    # free while a vertical flag leg (~150 mm) pays every step.
    # Default: every mode; the unload target leg is skipped.
    # cw-walk-flag (08-08) refuted the all-modes routing: rise needs
    # >50 mm transient swings from belly starts, and the global
    # charge collapsed rise/raise while only making the walk flag
    # leg transient. reward.flag_leg_walk_only=1 routes the charge
    # to walk mode alone (declared routing per RL_PLAN.md).
    k_flag = float(cfg_get(env.cfg, "reward", "k_flag_leg",
                           default=0.0))
    if k_flag > 0.0 and float(cfg_get(
            env.cfg, "reward", "flag_leg_walk_only",
            default=0.0)) > 0.0 and mode_now != "walk":
        k_flag = 0.0
    if k_flag > 0.0 and env._pad_z_ref is not None:
        allow = float(cfg_get(env.cfg, "reward", "flag_leg_allow_m",
                              default=0.05))
        skip = int(goal.unload_leg) if (
            goal is not None and goal.unload_leg is not None) else -1
        over = 0.0
        for i in range(6):
            if i == skip or env._pad_bids[i] < 0:
                continue
            over += max(float(env.data.xpos[env._pad_bids[i], 2])
                        - env._pad_z_ref[i] - allow, 0.0)
        r_flag = -k_flag * over
        parts["reward_flag_leg"] = r_flag
        reward += r_flag
    return mode_now, reward


def end_posture_reward(env, goal, mode_now, parts, reward):
    """Terminal end-posture pricing (reward.k_end_posture); moved verbatim
    from SimHexapodBalanceEnv._step_finish.
    """
    # Terminal end-posture pricing (default OFF; cycle 14). Root
    # cause chain: flag-leg endings <- airborne legs are free at
    # episode end <- load_even/support_margin have ZERO gradient on
    # an unloaded airborne leg, stance_clearance excludes
    # rise/lower/raise (their transients need freedom), and the
    # all-modes flag_leg charge was refuted for taxing exactly those
    # transients <- the deepest link (current-model dead zone
    # underpricing static holds) needs hardware recalibration, not
    # reachable in sim alone. This term charges per-foot clearance
    # above the grounded pad reference ONLY AFTER the goal height
    # reference has settled to its final value (plus a grace
    # window): the charge window is SCHEDULE-based, so the policy
    # cannot dodge it by avoiding the target, and the motion phase
    # is untaxed. Routed to the modes stance_clearance excludes.
    # Enable: --cfg-set reward.k_end_posture=<k>.
    k_endp = float(cfg_get(env.cfg, "reward", "k_end_posture",
                           default=0.0))
    if k_endp > 0.0 and env._pad_z_ref is not None \
            and env._goal_traj is not None \
            and mode_now in ("rise", "lower", "raise"):
        if env._end_posture_from is None:
            # The lower/rise ramps run to the last scheduled step
            # (no settled plateau exists), so "terminal" means: the
            # height REFERENCE is within 15 mm of its
            # final value from here to the end — still a pure
            # function of the pre-sampled schedule.
            h = np.asarray(env._goal_traj.height)
            ref_m = 15.0 * 0.001
            far = np.nonzero(np.abs(h - h[-1]) > ref_m)[0]
            start = (int(far[-1]) + 1) if len(far) else 0
            # Also clamp to the last 1.5 s of the
            # episode: small-amplitude rise refs sit near final
            # almost immediately, and charging the early curl
            # transient is the exact mistake that refuted the
            # all-modes flag_leg charge.
            # Mode-seq segments end at the next switch, not the
            # episode end — clamp the charge window to the ACTIVE
            # segment (None outside mode_seq = legacy exact).
            _ep_end = int(getattr(env, "_seq_seg_end", None)
                          or env.episode_steps)
            env._end_posture_from = max(
                start + int(round(0.25 / env.dt)),
                _ep_end - int(round(1.5 / env.dt)))
            # Dense variant (cycle 25, lower only): a proper lower
            # keeps all six feet planted THROUGHOUT the descent —
            # there is no legitimate leg-lift transient to protect
            # (the transient exemption exists for rise curls). With
            # this flag the clearance charge covers the whole lower
            # episode, pricing the spear-leg tilt-guard where it is
            # used instead of only at the end. Same term, same k,
            # same per-tick magnitude — only the window changes.
            # Enable: --cfg-set reward.end_posture_lower_dense=1.
            if mode_now == "lower" and float(cfg_get(
                    env.cfg, "reward", "end_posture_lower_dense",
                    default=0.0)) > 0.0:
                env._end_posture_from = 0
        if env._step_i >= env._end_posture_from:
            # Mirror the eval gate's allowances: 20 mm for
            # stand-ending modes, 60 mm for belly-ending lower.
            allow = 0.06 if mode_now == "lower" else 0.02
            skip = int(goal.unload_leg) if (
                goal is not None and goal.unload_leg is not None) \
                else -1
            over_e = 0.0
            for i in range(6):
                if i == skip or env._pad_bids[i] < 0:
                    continue
                c = (float(env.data.xpos[env._pad_bids[i], 2])
                     - env._pad_z_ref[i] - allow)
                over_e += min(max(c, 0.0), 0.30)
            r_endp = -k_endp * over_e
            parts["reward_end_posture"] = r_endp
            reward += r_endp
    return reward
