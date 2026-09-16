"""Rise/lower income of the balance env's _step_finish: rise decomposed
into scored steps (progress, milestones, posture and plant-polygon
gates, stand-score income, lower ratchet, finish bonus, footprint rent),
curl scores, rise-reference tracking and the curl-only pretrain stage;
moved verbatim out of sim_env.py.
"""
from __future__ import annotations

import math
import numpy as np

from rl_move.config import cfg_get
from rl_move.robot_state import DEG2RAD, RAD2DEG

from .balance_helpers import PLANT_SPEC, current_headroom_income_factor, footprint_fade, footprint_rent_m, load_rise_ref, lower_depth_frac, support_margin_m


def rise_scored_steps_reward(env, goal, h_err, h_rel, parts, reward):
    """Rise decomposed into scored steps (+ the lower_score_mode/depth_frac
    defaults the terminal settlement relies on); moved verbatim from
    SimHexapodBalanceEnv._step_finish.
    """
    # Defaults so the terminal bleed-settlement block below (which
    # runs unconditionally on every terminated tick, lower episode
    # or not) never hits an UnboundLocalError when this tick's
    # `h_err`/`h_target` guard below is false (e.g. hold/track/walk
    # episodes, or a lower episode with lower_score_prog unset).
    lower_score_mode = False
    depth_frac = 0.0
    # Rise decomposed into scored steps (rise/raise episodes only —
    # the ones with a real height target). Progress is potential-
    # based (telescoping: total = k * (start_err − end_err)) so it
    # steers exploration toward the target without changing what the
    # optimal policy is; freezing while the ref ramps away CHARGES.
    # Milestones pay once when the body first reaches a fraction of
    # the target — belly-off, half-way, nearly-there.
    if h_err is not None and abs(env._h_target) > 1e-3:
        kpg = float(cfg_get(env.cfg, "reward", "k_rise_progress",
                            default=100.0))
        kms = float(cfg_get(env.cfg, "reward", "k_rise_milestone",
                            default=2.0))
        e_abs = abs(h_err)
        r_prog = kpg * (env._prev_h_err_abs - e_abs)
        env._prev_h_err_abs = e_abs
        # Posture gate on rise/lower INCOME (2026-08-10, cfg
        # reward.rise_posture_gate in [0,1], default 0 = legacy
        # exact). The rfix pair (cw-uni-rfix-warm1/fresh1) showed
        # the height terms alone are gameable: fresh1 saturated the
        # in-training height criterion (rise "6/6") while the
        # posture-strict harness scored it 0/6 with a foot 273-313
        # mm in the air — torso-at-height via bridge/flail, not
        # standing. Height income (milestones, finish bonus, and
        # the post-ramp tracking kernel) is scaled by the fraction
        # of pads within 20 mm of their grounded z
        # (GEOMETRIC clearance, matching the eval harness's
        # end_posture_ok — NOT touch force: the champions' known
        # load concentration leaves grounded feet under 0.5 N, and
        # lightly-loaded is not the exploit; airborne is). "At
        # height, on your feet" pays full; "at height, feet
        # flying" earns ~(1-g). Progress and penalties are never
        # scaled (same construction as rise_income_prog_gate).
        g_pf = float(cfg_get(env.cfg, "reward",
                             "rise_posture_gate", default=0.0))
        pf = 1.0
        if g_pf > 0.0 and env._pad_z_ref is not None:
            # Mode-correct allowance (bug found 2026-08-10,
            # cw-uni-rfix-postgate1 dig-in): the belly-ending lower
            # pose legitimately leaves pads 20-45 mm up (measured on
            # cw-uni-rfix-warm1's 6/6 harness-PASSING lowers:
            # 16.9-43.4 mm), so gating lower at the 20 mm stand
            # allowance made an HONEST lower earn pf 0.67-0.83 —
            # indistinguishable from the legs-aloft outrigger cheat
            # (pf 0.67), which then won on faster post-ramp income
            # and eroded warm1's clean lower to 0/12. Use the same
            # 60 mm lower allowance the harness end_posture_ok and
            # the reward_end_posture penalty already use
            # (self._h_target < 0 == lower episode).
            allow_pf = 0.06 if env._h_target < 0.0 else 0.02
            n_on, n_tot = 0, 0
            for i in range(6):
                if env._pad_bids[i] < 0:
                    continue
                n_tot += 1
                if (float(env.data.xpos[env._pad_bids[i], 2])
                        - env._pad_z_ref[i]) <= allow_pf:
                    n_on += 1
            if n_tot:
                pf = (1.0 - g_pf) + g_pf * (n_on / n_tot)
            parts["rise_posture_factor"] = pf
        # Valid-plant geometric gate (operator spec 2026-08-10; cfg
        # reward.rise_plant_polygon_gate in [0,1], default 0 =
        # legacy exact). The clearance gate above counts feet near
        # the ground but is blind to WHERE they are: a stilt/splay
        # stand or a CoM-on-the-polygon-edge pose passes it. This
        # gate scales the same income terms by a continuous
        # PLANT_SPEC factor: CoM depth inside the down-feet support
        # polygon (full pay at the 20 mm spec margin), level
        # attitude (fades 10->20 deg), and body-frame footprint
        # near the walkable plant anchors (fades 40->80 mm — the
        # stilt family sits ~50 mm out). Rise only; lower ends on
        # the belly where a support polygon is meaningless.
        g_poly = float(cfg_get(env.cfg, "reward",
                               "rise_plant_polygon_gate",
                               default=0.0))
        # Stand-score income routing (operator, 08-10 evening, after
        # cw-stand-plantgate1 STOP): multiplicative gates LEAK — the
        # flag-leg cheat still collected ~60% of the height income
        # (5/6 feet down -> pf .83; footprint fade at ~50 mm -> .75)
        # and out-earned the harder honest stand, even warm-started
        # FROM the honest champion. Detection is not enough; the
        # income itself must come from standing correctly. Under
        # reward.rise_score_income=1 (RISE episodes only; lower keeps
        # its solved legacy stack) all height income is zeroed and
        # replaced by two terms on a single stand-score S — see the
        # block after the milestone code below.
        score_mode = (env._h_target > 0.0
                      and env._pad_z_ref is not None
                      and float(cfg_get(env.cfg, "reward",
                                        "rise_score_income",
                                        default=0.0)) == 1.0)
        clear = down = plant_f = None
        if ((g_poly > 0.0 or score_mode) and env._h_target > 0.0
                and env._pad_z_ref is not None):
            clear = np.array(
                [float(env.data.xpos[b, 2]) - env._pad_z_ref[i]
                 for i, b in enumerate(env._pad_bids)])
            down = clear <= PLANT_SPEC["foot_down_mm"] * 0.001
            feet_dn = np.array(
                [env.data.xpos[b, :2] for b in env._pad_bids]
            )[down]
            margin_mm = (support_margin_m(
                feet_dn, env.data.subtree_com[0, :2]) * 1000.0
                if int(down.sum()) >= 3 else -1e9)
            margin_f = min(max(
                margin_mm / PLANT_SPEC["com_margin_mm"], 0.0), 1.0)
            att_deg = max(abs(env._state.imu_roll),
                          abs(env._state.imu_pitch)) * RAD2DEG
            att_f = min(max((2.0 * PLANT_SPEC["attitude_deg"]
                             - att_deg)
                            / PLANT_SPEC["attitude_deg"], 0.0), 1.0)
            fp_mm = env._curl_dist() * 1000.0
            # Footprint fade band (cfg reward.rise_footprint_full_mm /
            # rise_footprint_zero_mm; defaults reproduce the legacy
            # full-pay-at-40/zero-at-80mm fade bit-exact -- see
            # footprint_fade() above for the 2026-09-11 dig-in
            # finding this generalizes). Opt-in only; unset = old
            # numbers.
            fp_full_mm = float(cfg_get(
                env.cfg, "reward", "rise_footprint_full_mm",
                default=PLANT_SPEC["footprint_err_mm"]))
            fp_zero_mm = float(cfg_get(
                env.cfg, "reward", "rise_footprint_zero_mm",
                default=2.0 * PLANT_SPEC["footprint_err_mm"]))
            fp_f = footprint_fade(fp_mm, fp_full_mm, fp_zero_mm)
            plant_f = margin_f * att_f * fp_f
            if g_poly > 0.0:
                pf *= (1.0 - g_poly) + g_poly * plant_f
            parts["rise_plant_factor"] = plant_f
        r_mile = 0.0
        for frac in (0.25, 0.50, 0.75, 0.90):
            # Fraction of the SIGNED target covered — works for rise
            # (positive) and lower (negative) alike.
            if (frac not in env._h_milestones
                    and h_rel / env._h_target >= frac):
                env._h_milestones.add(frac)
                r_mile += kms
        r_mile *= pf
        # Lower-specific income-shaping ratchet (2026-09-13, walkcurr
        # `lowerpartial-{s0,s1}` FAIL-MECHANISM pair: the two-seed
        # start-state-curriculum gate is now closed 2/2 across BOTH
        # start-state mechanisms tried, and both verdicts named the
        # same next lever — lower has no ratcheted "credit for
        # genuine descent" analog of `reward_rise_score_prog` at
        # all, only the moving-reference progress term above (which
        # prices the CURRENT tick's ref-tracking delta, so it never
        # accumulates into a standing income for having actually
        # gotten lower — a frozen park above the wall only costs as
        # much as the ref is currently outrunning it that instant,
        # not a steady bleed). `lower_score_mode` replaces that
        # stream for lower episodes with a potential-based ratchet
        # on depth-toward-target fraction (0..1,
        # `lower_depth_frac = clip(h_rel / h_target, 0, 1)`, both
        # signed negative for a lower episode so the ratio is
        # positive), paid ONLY on new best-ever depth reached this
        # episode (same ratchet math as `_score_best`), net of a
        # small continuous per-tick tracking-error charge so idle
        # parking above the wall stops being free — the exact gap
        # STATUS.md 09-13 ~21:2x named ("lower currently has no
        # lower_score/ratchet analog of rise_score_prog at all ...
        # plausibly WHY the -6mm park is a stable optimum"). Default
        # OFF (reward.lower_score_prog=0): bit-exact, no new
        # arithmetic touches the existing path. Same on/off
        # convention as `rise_score_income` just above.
        lower_score_mode = (
            env._h_target < 0.0
            and float(cfg_get(env.cfg, "reward", "lower_score_prog",
                              default=0.0)) == 1.0)
        if score_mode or lower_score_mode:
            # Height progress + milestones are exactly the streams
            # that bankrolled every flag-leg/tripod cheat — zeroed
            # here; the stand-score (rise) / depth ratchet (lower)
            # below is the only income for that mode instead.
            r_prog, r_mile = 0.0, 0.0
        parts["reward_rise_progress"] = r_prog
        parts["reward_rise_milestone"] = r_mile
        reward += r_prog + r_mile
        if lower_score_mode:
            depth_frac = lower_depth_frac(h_rel, env._h_target)
            if env._lower_score_best is None:
                env._lower_score_best = depth_frac
            delta_lsp = max(0.0, depth_frac - env._lower_score_best)
            env._lower_score_best = env._lower_score_best + delta_lsp
            r_lsp = 100.0 * delta_lsp
            parts["reward_lower_score"] = r_lsp
            parts["lower_depth_frac"] = depth_frac
            reward += r_lsp
            # Continuous tracking-error charge (NOT ratcheted, does
            # not reset once depth is banked): prices the gap
            # between the best depth reached so far and full target
            # every tick, so freezing at ANY partial depth keeps
            # costing instead of going quiet once its one-time
            # ratchet income has been collected. Weak by default
            # (k=1.0) — the ratchet is the primary signal, this
            # only removes the free-parking floor.
            r_lst = -(1.0 - depth_frac) ** 2
            parts["reward_lower_track"] = r_lst
            reward += r_lst
        if score_mode and clear is not None:
            # The tracking kernel pays torso-at-ref-height with no
            # posture opinion — the stream every cheat lived on.
            # Strip it for the whole rise episode (the curl-window
            # repricing below re-installs its own curl-priced kernel
            # during the pre-ramp hold, which is honest shaping).
            # 08-11: strip the NEGATIVE side too (opt-in,
            # reward.rise_score_strip_pen=1). The k_height=100
            # quadratic PENALTY was left live by the original strip
            # and it FUNDS the flag-leg cheat: lying honestly on
            # the belly under a +111mm command costs -1.2/tick
            # while torso-up-feet-flagged costs only the -0.5/tick
            # posture rent, so among behaviors a mediocre policy
            # can actually reach, the cheat is the paid optimum
            # (measured: rsi2 collapsed there even with correct
            # pool restore + RSI state coverage). With the penalty
            # stripped, height gradient comes only from score/ref
            # income — belly rest is free, the cheat pays pure
            # rent, honesty is the only positive slope.
            r_task = parts.get("reward_task", 0.0)
            strip_pen = float(cfg_get(env.cfg, "reward",
                                      "rise_score_strip_pen",
                                      default=0.0)) == 1.0
            if r_task > 0.0 or (strip_pen and r_task != 0.0):
                reward -= r_task
                parts["reward_task"] = 0.0
            # Stand-score S in [0,1]: height kernel x (feet-down
            # fraction)^2 x HARD no-flag x plant factor (attitude,
            # CoM-in-polygon, footprint at the walkable anchors).
            # Conjunction of the full PLANT_SPEC — anything scoring
            # high on all factors at once IS the stand. The no-flag
            # factor is a hard zero (not a fade): a flag-leg pose
            # earns nothing, not a 60% consolation.
            sig_s = 15.0 * 0.001
            err_t = h_rel - env._h_target
            h_f = math.exp(-0.5 * (err_t / max(sig_s, 1e-6)) ** 2)
            n_down = float(down.sum()) / max(float(len(clear)), 1.0)
            noflag = (1.0 if float(np.max(clear))
                      <= PLANT_SPEC["flag_leg_mm"] * 0.001 else 0.0)
            p_now = n_down ** 2 * noflag * float(plant_f)
            s_now = h_f * p_now
            parts["rise_score"] = s_now
            # Exported for the ref-track block below: under score
            # mode ALL rise income is grounded-feet-only, including
            # the exploration crutch (bank, 08-10 late: at k=2 the
            # ref kernel alone re-funded flag-leg +419/ep — 15 of
            # 18 joints track the reference just fine with one leg
            # flagged).
            parts["rise_feet_factor"] = n_down ** 2 * noflag
            if env._score_best is None:
                env._score_best = s_now
            delta_s = max(0.0, s_now - env._score_best)
            # Curl-distance-gated rise_score_prog income (2026-09-13,
            # riseheadroomgate-s1 CANARY FAIL-MECHANISM escalation:
            # the current-only gate above left the rise/det failing
            # trajectories BIT-IDENTICAL to the ungated parent
            # -- cur_rail_frac 0.587/0.457/0.587 in both, meaning
            # the policy never diverged from the doomed straight
            # push even with current-headroom pricing live. Root
            # cause: current only rises LATE in the push (near the
            # 2.64A rail itself), so by the time headroom_f bites
            # the height/posture score has mostly already been
            # banked -- the gate fires too late to redirect the
            # policy. This gate instead prices the SAME income on
            # FOOT GEOMETRY, which is known from tick 0: measured
            # curl_dist_mm at reset is ~176mm flat / ~111mm bridge
            # (the corridor that stays under 1.3A) / ~0mm crouch
            # (probe this cycle, RL_LOG 09-13 21:1x). Reusing the
            # exact current_headroom_income_factor ramp shape
            # (same "pay 0 at/above cap, pay full margin below"
            # math, dimension-agnostic) keyed on curl_dist instead
            # of current: at the flat start's own ~176mm sprawl the
            # score income is fully zero regardless of achieved
            # height, ramping to full pay only once the feet have
            # actually tucked to within ~111mm (bridge-like) of the
            # plant footprint -- the curl-first path is REQUIRED to
            # earn the height/posture score at all, not merely
            # cheaper. Bit-exact OFF by default
            # (reward.rise_score_income_curl_gate=0): curl_f==1.0
            # always, identical to the pre-existing line. Enable:
            # --cfg-set reward.rise_score_income_curl_gate=1.
            curl_f = 1.0
            gate_curl = float(cfg_get(
                env.cfg, "reward",
                "rise_score_income_curl_gate",
                default=0.0)) == 1.0
            if gate_curl and delta_s > 0.0:
                curl_f = current_headroom_income_factor(
                    env._curl_dist(), 0.176, 0.066)
                parts["rise_score_curl_factor"] = curl_f
            gate_f = curl_f
            r_sp = 30.0 * delta_s * gate_f
            env._score_best = env._score_best + delta_s * gate_f
            parts["reward_rise_score_prog"] = r_sp
            reward += r_sp
            # Hold pay: only once the commanded ramp has arrived —
            # holding the true plant quietly is the only way to keep
            # earning. S^2 sharpens the top (5/6 feet at height with
            # perfect geometry otherwise caps at ~0.48).
            if goal is not None \
                    and goal.height_ref >= env._h_target - 1e-9:
                r_sh = s_now ** 2
                parts["reward_rise_score_hold"] = r_sh
                reward += r_sh
            # Airborne-feet rent, ramp-weighted (bank finding,
            # 08-10: with the income fixed, the CHEATS won on the
            # penalty side — reward_height charges "torso not at
            # ref", so flag-leg DODGED ~120/ep of it by getting the
            # torso up on 5 legs while the honest partial rise paid
            # in full). Once the commanded ramp is up you owe rent
            # on FEET IN THE AIR (feet-down^2 x no-flag), exactly
            # as you already owe it on missing height. Deliberately
            # NOT the geometric plant factor: the honest reference
            # itself moves through wide-footprint poses mid-rise
            # (measured: charging plant_f rents the demonstration
            # ~100/ep and prices honest-but-parked below the
            # flag-leg cheat). Grounded-but-imperfect = unfinished,
            # charged via height + zero income; airborne = cheat.
            if goal is not None:
                w = min(max(goal.height_ref / env._h_target,
                            0.0), 1.0)
                r_pp = -w * (1.0 - n_down ** 2 * noflag)
                parts["reward_rise_posture_pen"] = r_pp
                reward += r_pp
        # Income prog-gate (2026-08-10 rise/lower freeze audit; cfg
        # reward.rise_income_prog_gate in [0,1], default 0 = legacy
        # exact). Measured: in lower episodes a robot that FREEZES at
        # the start height banks ~+74/ep (kernel + finish income
        # front-loaded during hold + early ramp) while every imperfect
        # attempt scores below it — a paid freeze plateau, the same
        # "worth less by construction" violation walk_kernel_prog_gate
        # closed for the park basin. Once the ramp has left zero,
        # multiply the INCOME terms (task kernel here, finish bonus
        # below) by the fraction of the signed target covered:
        # freeze earns ~(1-g), tracking earns full pay, penalties are
        # never scaled. The pre-ramp hold window is deliberately
        # ungated (holding IS the commanded behavior there).
        g_inc = float(cfg_get(env.cfg, "reward",
                              "rise_income_prog_gate", default=0.0))
        inc_f = 1.0
        if g_inc > 0.0 and not score_mode and goal is not None \
                and abs(goal.height_ref) > 1e-9:
            covered = min(max(h_rel / env._h_target, 0.0), 1.0)
            inc_f = (1.0 - g_inc) + g_inc * covered
            r_task = parts.get("reward_task", 0.0)
            if r_task > 0.0:
                reward += r_task * (inc_f - 1.0)
                parts["reward_task"] = r_task * inc_f
            parts["rise_income_factor"] = inc_f
        # Finish bonus (run 08): the tracking kernel is 20 mm wide,
        # so parking 20 mm below target still collects 61% of full
        # pay — run 07 drifted into exactly that discount (banked
        # the same curl as run 06 but stopped 43-62 mm short). Once
        # the ref has fully ramped to the target, a narrow second
        # kernel pays ONLY for actually arriving.
        # BUG (found 2026-08-10, cfg reward.rise_finish_gate_signed=1
        # to fix, default 0 = legacy exact): the legacy `ref >=
        # target` gate is correct for rise (ref climbs UP to the
        # target) but always-open for lower (negative target — the
        # ref starts ABOVE it), so the "arrival" kernel paid a robot
        # frozen at the START height through the hold + early ramp
        # (~+57 of the freeze plateau's +74). Signed mode requires
        # the ref to have reached the target from its own side.
        ramp_done = (goal is not None
                     and goal.height_ref >= env._h_target - 1e-9)
        if (goal is not None and env._h_target < 0.0
                and float(cfg_get(
                    env.cfg, "reward", "rise_finish_gate_signed",
                    default=0.0)) == 1.0):
            ramp_done = goal.height_ref <= env._h_target + 1e-9
        if ramp_done and not score_mode:
            kfin = float(cfg_get(env.cfg, "reward", "k_rise_finish",
                                 default=1.0))
            sfin = float(cfg_get(
                env.cfg, "reward", "rise_finish_sigma_mm",
                default=8.0)) * 0.001
            r_fin = kfin * math.exp(
                -0.5 * (h_err / max(sfin, 1e-6)) ** 2)
            if inc_f != 1.0:
                r_fin *= inc_f
            r_fin *= pf
            parts["reward_rise_finish"] = r_fin
            reward += r_fin
            # Post-ramp tracking kernel is also height-only income
            # — a torso parked at the target with feet flying would
            # still collect ~1/tick for the rest of the episode.
            # Gate it by the same loaded-feet factor, but only once
            # the ramp is done: mid-rise transients stay untaxed.
            if pf != 1.0:
                r_task = parts.get("reward_task", 0.0)
                if r_task > 0.0:
                    reward += r_task * (pf - 1.0)
                    parts["reward_task"] = r_task * pf
        # Standalone anchor-distance RENT (2026-09-11 DIG-IN
        # follow-on to the footprint-reprice-via-fade-shape saga —
        # see footprint_rent_m() docstring above for the full
        # reasoning). Deliberately OUTSIDE every multiplicative
        # income chain in this block (pf, plant_f, score s_now) so
        # no other reward stream can buy it off, and deliberately
        # NOT potential-based (unlike k_curl_progress below) so it
        # keeps charging even once the policy stops closing the
        # gap. Opt-in only (default k=0 => identical to every
        # checkpoint already trained — bit-exact old behavior).
        k_fp_pen = float(cfg_get(env.cfg, "reward",
                                 "k_rise_footprint_pen", default=0.0))
        if k_fp_pen > 0.0:
            free_mm = float(PLANT_SPEC["footprint_err_mm"])
            r_fp_pen = -k_fp_pen * footprint_rent_m(
                env._curl_dist() * 1000.0, free_mm)
            parts["reward_rise_footprint_pen"] = r_fp_pen
            reward += r_fp_pen
    return lower_score_mode, depth_frac, reward


def rise_curl_reward(env, goal, h_rel, parts, reward):
    """Curl scores (rise only); moved verbatim from
    SimHexapodBalanceEnv._step_finish.
    """
    # Curl scores (rise only): pay pulling the feet in toward the
    # plant footprint. Potential-based, so crouch starts (dist ~0)
    # and foot-parking exploits earn nothing net.
    if env._is_rise:
        kcp = float(cfg_get(env.cfg, "reward", "k_curl_progress",
                            default=50.0))
        kms = float(cfg_get(env.cfg, "reward", "k_rise_milestone",
                            default=2.0))
        th_mm = cfg_get(env.cfg, "reward", "curl_milestone_mm",
                        default=[40.0, 15.0])
        dist = env._curl_dist()
        _curl_delta = env._curl_dist_prev - dist
        r_cprog = kcp * _curl_delta
        env._curl_dist_prev = dist
        r_cmile = 0.0
        for th in th_mm:
            th = float(th)
            if th not in env._curl_milestones and dist <= th * 0.001:
                env._curl_milestones.add(th)
                r_cmile += kms
        parts["reward_curl_progress"] = r_cprog
        parts["reward_curl_milestone"] = r_cmile
        reward += r_cprog + r_cmile
        # Height-without-curl DECOUPLING price (2026-09-14, follow-on
        # to the risepretuck dose2/dose8 CANARY FAIL-MECHANISM
        # diagnostic). A `--rollout-trace-out` per-tick trace off a
        # FAILING flat-start rise episode (both current_pretuck
        # doses) showed ALL SIX legs' pitch+knee servos pinned at/
        # near the 2.64A ceiling simultaneously for >1.5s while
        # footprint_err_end_mm stayed at the ~52mm stuck band (feet
        # never moved toward the plant anchor) even though torso
        # height climbed 0->53mm over the same window -- i.e. the
        # policy pushes the body straight UP in Z from the
        # original (splayed) foot XY layout instead of pulling feet
        # IN (reducing curl_dist) first, the poor-leverage
        # brute-force shape that costs near-max current on every
        # joint simultaneously. Every closed lever on this sub-
        # problem (current-headroom-gate, geometry/score-income
        # gate, two-phase-freeze, curl-pretrain, current_pretuck)
        # priced CURRENT, SCORE-INCOME, or a TRAINING STAGE in
        # isolation -- none of them couple the two live state
        # signals (curl_dist, h_rel) together. This term does:
        # while pre-tuck (same one-way latch/threshold/crouch-
        # exemption idiom as current_pretuck -- not a scripted
        # clock, not a motion prior, both signals already read
        # elsewhere in this same reward path), any positive torso
        # height gained on a tick where curl_dist did NOT also
        # shrink (`_curl_delta <= 0`) is charged quadratically --
        # i.e. "raising the body without pulling your feet in
        # first" is the specifically priced behavior, height gained
        # WHILE curling is free. Bit-exact OFF by default
        # (reward.k_rise_decouple=0.0): no extra state read, no
        # behavior change for any existing checkpoint/lineage.
        # --cfg-set reward.k_rise_decouple=<k>
        # [--cfg-set reward.rise_decouple_curl_mm=<mm>] (default 40,
        # matches the bridge-pose bar every other pretuck-family
        # lever uses).
        # Tests: rl_move/tests/test_rise_decouple_reward.py.
        k_decouple = float(cfg_get(
            env.cfg, "reward", "k_rise_decouple", default=0.0))
        if (k_decouple > 0.0
                and getattr(env._goal_traj, "start_at", None)
                != "crouch"):
            if getattr(env, "_decouple_latched", False):
                tucked_d = True
            else:
                th_m_d = float(cfg_get(
                    env.cfg, "reward", "rise_decouple_curl_mm",
                    default=40.0)) * 0.001
                tucked_d = dist <= th_m_d
                if tucked_d:
                    env._decouple_latched = True
            h_prev = getattr(env, "_rise_h_prev", None)
            if h_prev is None:
                h_prev = h_rel
            if not tucked_d:
                d_h_mm = max(h_rel - h_prev, 0.0) * 1000.0
                if _curl_delta <= 0.0 and d_h_mm > 0.0:
                    r_decouple = -k_decouple * (d_h_mm ** 2)
                    parts["reward_rise_decouple"] = r_decouple
                    reward += r_decouple
            env._rise_h_prev = h_rel
        # Hold-phase repricing (run 06): while the height ref still
        # sits at 0 (the curl window), the tracking kernel pays for
        # CURL DISTANCE, not stillness. Before this, lying frozen
        # and level earned ~1/tick from the tilt/height kernel while
        # the entire curl bonus summed to ~2.5 — so preparation was
        # priced as a loss and the policy (correctly, by that math)
        # pinned curl negative through runs 03-05. Crouch starts
        # have dist ~0 and earn full pay unchanged.
        if goal is not None and goal.height_ref <= 1e-4:
            sig_c = float(cfg_get(
                env.cfg, "reward", "rise_hold_curl_sigma_mm",
                default=20.0)) * 0.001
            k_tr = float(cfg_get(env.cfg, "reward", "k_track",
                                 default=1.0))
            curl_kernel = k_tr * math.exp(
                -0.5 * (dist / max(sig_c, 1e-6)) ** 2)
            reward += curl_kernel - parts.get("reward_task", 0.0)
            parts["reward_task"] = curl_kernel
            # Reprice the quiet-stance bonus with the swapped kernel
            # too: the plain kernel is ~1 lying level on the belly,
            # which would pay k_still for frozen belly-rest — the
            # exact freeze shortcut this branch exists to prevent.
            if parts.get("reward_still", 0.0) != 0.0:
                ksl = float(cfg_get(env.cfg, "reward", "k_still",
                                    default=0.0))
                r_still = (ksl * (curl_kernel / max(k_tr, 1e-9))
                           * parts.get("still_factor", 0.0))
                reward += r_still - parts["reward_still"]
                parts["reward_still"] = r_still
    return reward


def rise_ref_track_reward(env, parts, reward):
    """Rise-reference tracking (reward.k_rise_ref_track); moved verbatim
    from SimHexapodBalanceEnv._step_finish.
    """
    # Rise-reference tracking (default OFF; operator 08-10, the
    # Stage-II route from the stand-up literature — HumanUP / HoST:
    # discover the motion once, then train the deployable policy to
    # TRACK it instead of rediscovering from a height reward). Our
    # "discovery stage" already exists: the stance champion's
    # learned belly-rise. This term pays a joint-space kernel on
    # RMS error against that recorded trajectory, time-aligned at
    # the RAMP START tick (episodes with jittered holds and
    # crouch/bridge starts all join the same reference — pre-ramp
    # ticks track the reference's own curl phase, clamped at its
    # start). A scaffold, not the objective: run it at full weight
    # to seed the skill, then anneal k to 0 across warm-started
    # arms so the final policy is not trajectory-locked.
    # Enable: --cfg-set reward.k_rise_ref_track=<k>
    #         --cfg-set reward.rise_ref_path=<npz>.
    k_ref = float(cfg_get(env.cfg, "reward", "k_rise_ref_track",
                          default=0.0))
    if k_ref > 0.0 and env._is_rise:
        ref_path = cfg_get(env.cfg, "reward", "rise_ref_path",
                           default=None)
        if ref_path:
            ref = load_rise_ref(str(ref_path))
            j, _is_rsi = env._rise_ref_clock(ref)
            parts["rise_rsi"] = 1.0 if _is_rsi else 0.0
            err = (env._mujoco_to_logical_q(
                env.data.qpos[env._qadr]) - ref["q"][j])
            sig = float(cfg_get(
                env.cfg, "reward", "rise_ref_sigma_deg",
                default=12.0)) * DEG2RAD
            rms = float(np.sqrt(np.mean(err ** 2)))
            r_ref = k_ref * math.exp(-0.5 * (rms / max(sig, 1e-6)) ** 2)
            # Score-income mode: the crutch is income too, and
            # income only pays on grounded feet (see the
            # rise_feet_factor export above). Legacy stacks
            # (factor absent) are exactly unchanged.
            r_ref *= parts.get("rise_feet_factor", 1.0)
            parts["reward_rise_ref"] = r_ref
            reward += r_ref
    return reward


def rise_curl_only_pretrain_reward(env, parts, reward):
    """Curl-only pretrain stage (rise income mask); moved verbatim from
    SimHexapodBalanceEnv._step_finish.
    """
    # CURL-ONLY PRETRAIN STAGE (2026-09-13, risetwophase-s1-canary2m
    # FAIL-MECHANISM escalation: THREE successive reward-pricing/
    # curriculum levers on the SAME continuous height-ramp income
    # (current-headroom-gated, curl-geometry-gated, and finally a
    # genuine two-phase freeze-the-ramp-until-curled sub-goal) all
    # left the rise/det flat+bridge failing trajectories within
    # noise of the ungated parent's own fingerprint
    # (cur_rail_frac 0.587/0.46/0.584 vs the parent's own
    # 0.587/0.457/0.587) -- the freeze mechanism demonstrably FIRES
    # (env/rise_gate_freeze_ticks > 0 throughout, unlike the prior
    # gate whose factor never left 1.0) but a 2.0s-capped freeze
    # inside the full multi-mode rise/hold/lower recipe still never
    # gives the policy a REASON strong/isolated enough to discover
    # the coordinated tuck-in motion -- every further dose of the
    # SAME income-pricing family is now refuted 3/3, so per the
    # gate's own escalation this does not re-price the ramp again;
    # it makes a completely separate, narrower, BC-free RL-only
    # training STAGE possible: this flag turns OFF every rise
    # height/score/posture/finish-related reward term (the exact
    # keys that pay for climbing regardless of curl state) so the
    # ENTIRE per-tick reward for is_rise ticks becomes JUST the
    # pre-existing curl-progress/curl-milestone telescoping reward
    # (reward.k_curl_progress/k_rise_milestone, unchanged formulas,
    # no new physics, no teacher/anchor/demo signal anywhere) plus
    # the general actuator/gait safety regularizers that already
    # apply regardless of mode (current-hot, action-rate, stance,
    # clearance, flag-leg, termination) -- a policy trained under
    # this flag is optimizing PURELY "get your feet under you
    # without cooking a servo", the narrowest possible RL-only
    # sub-task, intended to run for a short episode
    # (--episode-seconds ~3-4s) as a warm-start PRECURSOR to the
    # normal full recipe (this flag OFF, goal.rise_curl_gate=1 as
    # before) -- i.e. a genuine two-stage CURRICULUM (explicitly
    # allowed for rl_only: "Calibration, system ID, task rewards,
    # curricula ... are allowed"), not another reward-pricing dose
    # on the same continuous income. Bit-exact OFF by default
    # (reward.rise_curl_pretrain=0): every existing checkpoint's
    # reward is untouched. Crouch starts are EXEMPT (same exemption
    # as `_rise_gate_tick`'s freeze): curl_dist is already ~0 there,
    # so there is nothing to pretrain and the full height/score
    # reward stays live -- without this exemption, a mixed-mode
    # pretrain batch would starve the crouch->full-rise pathway of
    # its own already-working reward signal and risk regressing the
    # one branch this campaign already trusts (rise_crouch_success
    # held at 1.0 across every prior canary). Tests:
    # rl_move/tests/test_rise_curl_pretrain_reward.py.
    if (env._is_rise and getattr(env._goal_traj, "start_at", None)
            != "crouch" and float(cfg_get(
            env.cfg, "reward", "rise_curl_pretrain",
            default=0.0)) == 1.0):
        _keep_keys = (
            "reward_curl_progress", "reward_curl_milestone",
            "reward_current_hot", "reward_current_pretuck",
            "reward_current_rate",
            "reward_rise_decouple",
            "reward_support_margin", "reward_load_even",
            "reward_torque_headroom", "reward_action_rate",
            "reward_stance", "reward_clearance", "reward_flag_leg",
            "reward_termination", "reward_task", "reward_still",
        )
        _dropped_total = 0.0
        for _k in list(parts.keys()):
            if (_k.startswith("reward_") and _k not in _keep_keys
                    and isinstance(parts[_k], (int, float))):
                _dropped_total += parts[_k]
                parts[_k] = 0.0
        reward -= _dropped_total
        parts["rise_curl_pretrain_active"] = 1.0
    return reward
