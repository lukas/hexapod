"""Walk-mode STEP-EVENT reward package and tripod-phase term, moved out of SimHexapodJointWalkEnv._post_step.

Every function here is one contiguous block of the walk-mode pricing stack
moved mechanically: ``env`` is the env instance (the former ``self``), the
remaining parameters are the block's live inputs and the return values its
live outputs, so the call site in ``_post_step`` is a single assignment.
Bodies are byte-identical to the original apart from ``self`` -> ``env``
and re-indentation; the header comments travelled with the code.
"""
from __future__ import annotations

import math

import numpy as np

from rl_move.config import cfg_get
from .walk_task import (
    PHASE_TRIPOD_A, transition_window_liftoff, transition_window_tick,
    transition_window_touchdown,
    walk_leg_swing_initiation_maxload,
    walk_legduty_ratio_tick, walk_legslip_ratio_tick,
)


def step_event_package(env,
                       along, g_duty, g_gait, g_lsratio, g_ratio,
                       g_ratio_swingfloor, g_swing, g_swinggap, g_swinit, goal,
                       info, lift, reward, s_ref):
    # Swing touchdown bonus (default OFF): both cw-walk and
    # cw-walk2 plateaued at a ~0.04 m/s skate — nothing in the
    # reward ever pays for LIFTING a foot, and the smoothness
    # regularizers charge for it. Pay a one-shot bonus when a
    # foot completes a real swing (airborne, then lands >=15 mm
    # from where it lifted off) while a velocity is commanded.
    # Enable with --cfg-set reward.k_walk_swing=<k>.
    k_swing = float(cfg_get(env.cfg, "reward", "k_walk_swing",
                            default=0.0))
    # Step-event reward package (operator directive 08-08
    # ~23:00Z, queue item 0 — cw-walk-step0). Walk-mode ONLY by
    # construction (this block). Three cfg-gated terms, all
    # default OFF:
    #   k_step_event: one-shot per-leg credit for a COMPLETED
    #     lift->swing->touchdown whose displacement projects
    #     >=10 mm along the commanded direction; scaled by
    #     along/30 mm, capped at 1.5x. A parked leg never
    #     touches down -> never paid, by construction.
    #   k_drag_loaded: per-tick charge on foot XY translation
    #     while IN CONTACT (skating), 0.5 mm/tick deadband for
    #     compliance jitter.
    #   k_park_duty: per-tick charge on per-leg contact duty
    #     pinned outside [0.1, 0.9] over a trailing 2 s window
    #     of COMMANDED ticks — a tripod park (3 legs at 1.0,
    #     3 at 0.0) pays ~0.6*k every tick; a real gait
    #     (duty ~0.3-0.8) pays nothing.
    k_step = float(cfg_get(env.cfg, "reward", "k_step_event",
                           default=0.0))
    k_drag = float(cfg_get(env.cfg, "reward", "k_drag_loaded",
                           default=0.0))
    # Deadband was a bare 0.5mm/tick literal calibrated at the
    # pre-08-24 default control.hz=25 (dt=0.04s) -- a PER-TICK
    # floor, not per-second. At today's default control.hz=100
    # (dt=0.01s) the identical literal is a 4x LOOSER real
    # velocity floor (50mm/s vs the intended ~12.5mm/s),
    # silently under-pricing slow persistent slip
    # ("paddle-creep"). Scale by dt/0.04 so hz=25 stays
    # bit-exact (scale=1.0) and hz=100 correctly shrinks to the
    # same real-velocity floor (2026-09-02 trans_drag
    # semantics-bank dig-in; mirrors sim_env.py's identical
    # trans_drag_mm fix and safety.max_delta_q_deg's existing
    # hz-scaling convention). k_drag_stance's own
    # drag_stance_tick_floor_mm deadband is the SAME shape but
    # is NOT touched here -- it needs its own measurement
    # before changing (OPERATOR_QUESTIONS.md 2026-09-02).
    k_drag_deadband_m = 0.0005 * (env.dt / 0.04)
    k_park = float(cfg_get(env.cfg, "reward", "k_park_duty",
                           default=0.0)) \
        * env._walk_charge_scale()
    # Per-foot LOAD-MIN bonus (standwalk 2026-09-26 ~14:2x control
    # experiment: an open-loop scripted TripodGait sacrifices the
    # IDENTICAL legs on the IDENTICAL per-leg-asymmetry DR draws as
    # every trained RL transformer -- gait_valid at the ceil225 rung
    # is the fixed plant trajectory never reaching the ground under
    # that draw's geometry, controller-independent, not a learning
    # failure. k_park_duty (a BEHAVIOR-pattern charge on contact duty)
    # was already tried alone and closed 2026-09-26 ~05:5x. A FORCE-
    # based soft-min bonus (reward.k_walk_foot_load_min, stacked with
    # obs.foot_contact_sense) was tried next and closed 2026-09-26
    # ~15:4x (2 seeds, both an exact TIE on gait_valid_rate vs the
    # untrained zero-shot parent AND the identical sacrificed-leg
    # identities as the scripted-tripod floor on the fixed seed-0
    # draws) -- removed, RESEARCH_RULES close-the-key rule.
    # Structural stance-slip charge (charge-magnitude audit,
    # 2026-08-11, probe_drag_audit.py): per-foot accumulated
    # loaded XY travel per STANCE PERIOD, charged continuously
    # beyond drag_stance_allow_mm. Unlike k_drag_loaded's
    # per-tick form (audit: cannot separate skating from
    # honest touchdown scuff at ANY k/deadband), the stance
    # accumulator prices the dragging STROKE: audit-derived
    # operating point k=7000/m @ allow 6mm makes a learned
    # skater's drag cost ~2.4x its income while the honest
    # scripted gait pays on <5% of stances (~20% of income).
    # Default 0 = off, legacy exact.
    k_ds = float(cfg_get(env.cfg, "reward", "k_drag_stance",
                         default=0.0))
    # Ramp override (see __init__/apply_drag_allow_frac): None
    # unless reward.drag_stance_allow_ramp_steps is armed AND
    # the trainer has broadcast at least one frac — bit-exact
    # legacy cfg lookup otherwise.
    if env._drag_allow_override_m is not None:
        allow_m = env._drag_allow_override_m
    else:
        allow_m = float(cfg_get(env.cfg, "reward",
                                "drag_stance_allow_mm",
                                default=6.0)) / 1000.0
    # Contact-solver micro-jitter (~0.2 mm/tick on a motionless
    # loaded foot) must not integrate into the accumulator, or
    # any long stance eventually pays regardless of behavior:
    # only ticks sliding faster than this floor accumulate.
    # Dragging strokes run 0.4-0.5 mm/tick (audit medians).
    ds_floor = float(cfg_get(env.cfg, "reward",
                             "drag_stance_tick_floor_mm",
                             default=0.25)) / 1000.0
    # Displacement-gated step-event credit (cycle 34; operator
    # 0-c.2 "so stride-in-place can't collect", pre-registered
    # escalation from the closed tolerance rung). Root cause: the
    # step-event credit pays PER TOUCHDOWN with no body-
    # displacement accounting, so cadence inflation is the one
    # income channel that still pays for creeping transport
    # (step income +24% at c1, +32% at tol5, 2x cadence from
    # scratch at c33). Mechanism: each tick banks the body's net
    # displacement along the commanded direction; each PAID step
    # credit CONSUMES reward.step_disp_budget_mm of bank; a
    # touchdown with an empty bank earns 0. Total step income is
    # therefore <= k_step*1.5*(ground covered)/budget BY
    # CONSTRUCTION — extra cadence at fixed distance is worth
    # nothing, stride-in-place (no net body motion) collects
    # nothing. Backward motion never banks (max(along,0)); the
    # gate removes income only, never shrinks a penalty. Default
    # 0 = off, legacy exact. Walk-mode only by construction.
    budget_m = float(cfg_get(env.cfg, "reward",
                             "step_disp_budget_mm",
                             default=0.0)) / 1000.0
    # gait_gate_stride_mm: min completed-swing XY stride the
    # walk_gait_gate above counts as "this leg is cycling"
    # (below the step credit's 10 mm ALONG-command bar on
    # purpose — the gate scores gait legality, not progress;
    # direction is priced by the kernel/progress terms).
    gait_stride_m = float(cfg_get(env.cfg, "reward",
                                  "gait_gate_stride_mm",
                                  default=10.0)) / 1000.0
    # Tangential planted-foot slip charge and contact diagnostics
    # (2026-08-23 Stage-A probe). This is deliberately lighter
    # than the episode-level loadslip ratio above: it only
    # charges foot XY velocity while the same foot has meaningful
    # contact on consecutive ticks, averages across measured
    # feet instead of summing all six, applies a deadband/cap,
    # and is default-off. cfg: reward.k_foot_slip_tangent,
    # reward.foot_slip_contact_n,
    # reward.foot_slip_deadband_m_s,
    # reward.foot_slip_max_m_s; goal.walk_contact_diagnostics.
    k_tslip = float(cfg_get(env.cfg, "reward",
                            "k_foot_slip_tangent", default=0.0))
    contact_diag = bool(float(cfg_get(
        env.cfg, "goal", "walk_contact_diagnostics",
        default=0.0)) > 0.0)
    tslip_contact_n = float(cfg_get(
        env.cfg, "reward", "foot_slip_contact_n", default=1.0))
    tslip_deadband = float(cfg_get(
        env.cfg, "reward", "foot_slip_deadband_m_s",
        default=0.015))
    tslip_cap = float(cfg_get(
        env.cfg, "reward", "foot_slip_max_m_s", default=0.25))
    # TRANSITION-WINDOW slip charge (2026-09-07, walkcurr
    # phase-binned slip audit follow-up:
    # rl_docs/tracks/walkcurr/STATUS.md 09-07 ~18:2x). Every
    # direct-slip lever tried so far (k_foot_slip_tangent,
    # k_foot_slip_height, the episode-level loadslip ratio)
    # charges the WHOLE loaded duration uniformly and was
    # CLOSED 5/5 without moving held-out slip/m — the phase-
    # binned audit shows why: slip concentrates in two SHORT
    # windows (touchdown impact + pre-liftoff drag), not
    # uniform mid-stance creep, so a flat-rate charge spends
    # most of its "budget" pricing ticks that were already
    # cheap. This charges ONLY those two windows, at
    # `k_walk_transition_slip` per m/s of excess tangential
    # velocity over the SAME deadband/cap units as
    # `k_foot_slip_tangent` (independently configurable so a
    # combined arm can dose them differently): the touchdown
    # window is the touchdown tick itself plus the next
    # `walk_transition_td_ticks - 1` on-ticks (priced live,
    # per tick, exactly like k_foot_slip_tangent's own
    # mid-stance charge but starting one tick earlier so the
    # impact tick itself is covered); the liftoff window is
    # the LAST `walk_transition_lo_ticks` on-ticks of the
    # stance bout, priced RETROSPECTIVELY as one lump sample
    # at the tick the foot actually leaves the ground (using
    # a small trailing per-leg ring buffer, `_trans_lo_buf`,
    # of already-observed per-tick tangential velocities — no
    # lookahead, everything charged already happened). Default
    # off (`k_walk_transition_slip=0.0`): bit-exact vs no
    # mechanism at all — the gate condition below and every
    # write below are guarded by `k_wts > 0.0`. Does not
    # replace or zero `k_foot_slip_tangent`; if both are armed
    # together, touchdown/liftoff-window ticks are charged by
    # both (a combined-dose question for a follow-up arm, not
    # this one). No interaction with `k_step_event`: that
    # prices ALONG-command stride
    # length between liftoff and the NEXT touchdown, this
    # prices tangential (skid) velocity within a fixed tick
    # window — different quantities, same shared touchdown/
    # liftoff flags, no double-counted term.
    k_wts = float(cfg_get(env.cfg, "reward",
                          "k_walk_transition_slip", default=0.0))
    wts_contact_n = float(cfg_get(
        env.cfg, "reward", "walk_transition_contact_n",
        default=1.0))
    wts_deadband = float(cfg_get(
        env.cfg, "reward", "walk_transition_slip_deadband_m_s",
        default=0.015))
    wts_cap = float(cfg_get(
        env.cfg, "reward", "walk_transition_slip_max_m_s",
        default=0.25))
    wts_td_ticks = max(1, int(round(float(cfg_get(
        env.cfg, "reward", "walk_transition_td_ticks",
        default=3.0)))))
    wts_lo_ticks = max(1, int(round(float(cfg_get(
        env.cfg, "reward", "walk_transition_lo_ticks",
        default=3.0)))))
    if (k_swing > 0.0 or k_step > 0.0
            or k_drag > 0.0
            or k_park > 0.0 or k_ds > 0.0
            or g_gait > 0.0 or g_duty > 0.0 or g_swing > 0.0
            or g_ratio > 0.0 or g_lsratio > 0.0
            or g_swinggap > 0.0 or g_swinit > 0.0
            or k_tslip > 0.0 or k_wts > 0.0
            or contact_diag) and s_ref > 1e-3:
        if budget_m > 0.0:
            # `along` here is still the BODY along-command
            # velocity (m/s) from the r_prog block above (the
            # foot-displacement loop below shadows it).
            env._step_disp_bank += max(along, 0.0) * env.dt
        r_step_denied = 0.0
        r_swing = 0.0
        r_step = 0.0
        r_drag = 0.0
        r_ds = 0.0
        r_tslip = 0.0
        r_wts = 0.0
        r_swinit = 0.0
        # walk_leg_swing_initiation_income: whole-tick snapshot
        # of the per-leg trailing LOAD EMA (`_swinit_load_ema`,
        # NOT the raw instantaneous `_foot_prev_force` -- see
        # that state's own __init__ comment for why the raw
        # single-tick value cannot be used), taken BEFORE this
        # tick's per-leg loop starts overwriting the EMA
        # leg-by-leg (only safe to compare across all six legs
        # as a single consistent instant right here; mid-loop
        # it would be a mix of this-tick-updated and
        # still-previous-tick values, the same hazard
        # `_foot_prev_force` has). None (never indexed) when
        # the mechanism is off.
        prev_load_ema_snapshot = (
            list(env._swinit_load_ema) if g_swinit > 0.0 else None)
        prev_maxload_flags = (
            walk_leg_swing_initiation_maxload(prev_load_ema_snapshot)
            if prev_load_ema_snapshot is not None else None)
        wts_excess = []
        wts_td_events = 0
        wts_lo_events = 0
        swing_gate_flags = [False] * 6
        ratio_swing_flags = [False] * 6
        swinggap_flags = [False] * 6
        contacts = [False] * 6
        contact_forces = [0.0] * 6
        meaningful_contacts = 0
        touchdown_flags = [False] * 6
        liftoff_flags = [False] * 6
        swinging_flags = [False] * 6
        air_times_s = [0.0] * 6
        tangent_vels = [0.0] * 6
        measured_tangent_vels = []
        tangent_excess = []
        for f in range(6):
            adr = env._touch_adr[f]
            force = (max(0.0, float(env.data.sensordata[adr]))
                     if adr >= 0 else 0.0)
            contact_forces[f] = force
            on = force > 0.5
            contacts[f] = on
            meaningful = on and force >= tslip_contact_n
            if meaningful:
                meaningful_contacts += 1
            wts_meaningful = (k_wts > 0.0
                               and on and force >= wts_contact_n)
            xy = env.data.xpos[env._pad_bids[f], :2]
            if on and not env._foot_on[f]:
                touchdown_flags[f] = True
                # Touchdown: a new stance period earns a fresh
                # slip allowance (k_drag_stance bookkeeping).
                env._stance_slip_acc[f] = 0.0
                # TRANSITION-WINDOW touchdown charge: does NOT
                # price the touchdown tick's own raw XY delta
                # (that measures the airborne->contact
                # boundary, i.e. ordinary swing-approach
                # motion, not loaded skid — corrected 09-07
                # per accounting review fb_20260907T185803_
                # c8af66, see the `transition_window_*` module
                # comment above). Arms the live window at the
                # FULL `walk_transition_td_ticks` (not -1, to
                # keep the same tick COUNT charged): the next
                # `wts_td_ticks` mid-stance ticks (all
                # unambiguously loaded-to-loaded) are priced
                # below via `transition_window_tick`.
                if k_wts > 0.0 and f not in lift:
                    env._trans_lo_buf[f], env._trans_td_count[f] \
                        = transition_window_touchdown(wts_td_ticks)
            if env._foot_on[f] and not on:
                liftoff_flags[f] = True
                env._liftoff_xy[f] = xy.copy()
                env._liftoff_step[f] = env._step_i
                # walk_leg_swing_initiation_income bookkeeping:
                # was THIS leg carrying the single highest
                # TRAILING LOAD EMA of all six at the point it
                # left the ground? Read from the whole-tick EMA
                # snapshot taken before this loop started
                # (never the live, mid-loop `_swinit_load_ema`,
                # which is only half-updated at this point in
                # the iteration -- same hazard as
                # `_foot_prev_force`). Strict > 0 guards the
                # degenerate all-zero tick (nobody loaded yet,
                # e.g. right at episode reset) from awarding a
                # spurious "most loaded" claim.
                if prev_maxload_flags is not None:
                    env._liftoff_was_maxload[f] = \
                        prev_maxload_flags[f]
                # TRANSITION-WINDOW liftoff charge: retrospective
                # lump over the trailing `walk_transition_lo_
                # ticks` per-tick excess samples already
                # observed during this stance (no lookahead —
                # everything in the buffer already happened).
                if k_wts > 0.0 and f not in lift:
                    lo_charge = transition_window_liftoff(
                        env._trans_lo_buf[f])
                    if lo_charge is not None:
                        wts_excess.append(lo_charge)
                        wts_lo_events += 1
                    env._trans_lo_buf[f] = []
            elif on and not env._foot_on[f] \
                    and env._liftoff_xy[f] is not None:
                d = xy - env._liftoff_xy[f]
                stride = float(np.linalg.norm(d))
                air = env._step_i - env._liftoff_step[f]
                # >=2 ticks airborne filters contact chatter /
                # settle wobble (zero-action probe scored one
                # phantom swing without this).
                # Lift-leg exemption (quadwalk): a commanded-
                # lifted front never earns swing/step credit —
                # stepping with the "hands" is the six-leg
                # cheat, not the task. Charges below still
                # apply to it (a dragging front pays).
                # walk_gait_gate bookkeeping: a completed real
                # swing marks this leg "cycling" on the
                # commanded-tick clock (lift legs excluded —
                # their stepping is the six-leg cheat).
                if g_gait > 0.0 and air >= 2 \
                        and stride >= gait_stride_m \
                        and f not in lift:
                    env._gait_last_step[f] = env._gait_cmd_tick
                # walk_swing_gate bookkeeping: same qualifying
                # definition as walk_gait_gate immediately
                # above, recorded as a per-tick event flag
                # (not a "last tick" pointer) so the gate
                # above can COUNT occurrences in its own
                # trailing window instead of only checking
                # recency.
                if g_swing > 0.0 and air >= 2 \
                        and stride >= gait_stride_m \
                        and f not in lift:
                    swing_gate_flags[f] = True
                # walk_leg_duty_ratio_swing_min_count
                # bookkeeping: identical qualifying-swing
                # definition, own flag array/hist so the
                # ratio-charge's swing floor cannot be
                # perturbed by walk_swing_gate's independent
                # dose (both default-off, own state).
                if g_ratio_swingfloor > 0.0 and air >= 2 \
                        and stride >= gait_stride_m \
                        and f not in lift:
                    ratio_swing_flags[f] = True
                # walk_leg_swing_gap_charge bookkeeping:
                # identical qualifying-swing definition, own
                # flag array so this charge's dose can be
                # swept standalone (never perturbs
                # walk_swing_gate/the duty-ratio swing floor's
                # own arrays).
                if g_swinggap > 0.0 and air >= 2 \
                        and stride >= gait_stride_m \
                        and f not in lift:
                    swinggap_flags[f] = True
                # walk_leg_swing_initiation_income: pay the
                # fixed per-event income exactly once, at the
                # touchdown that resolves a qualifying swing
                # (identical filter to every sibling gate
                # immediately above) whose OWN liftoff instant
                # was flagged as "this leg was the single most
                # loaded of all six" by the bookkeeping at the
                # liftoff branch above. A leg that swings while
                # NOT the most loaded, or that never completes
                # a real swing at all, earns nothing here --
                # this cannot be gamed by holding still (no
                # event = no income) or by swinging cheaply
                # while lightly loaded (fails the maxload
                # check at liftoff).
                if g_swinit > 0.0 and air >= 2 \
                        and stride >= gait_stride_m \
                        and f not in lift \
                        and env._liftoff_was_maxload[f]:
                    r_swinit += g_swinit
                if k_swing > 0.0 and stride >= 0.015 \
                        and air >= 2 and f not in lift:
                    r_swing += k_swing
                if k_step > 0.0 and air >= 2 and f not in lift:
                    along_f = float(
                        d[0] * goal.vx_ref + d[1] * goal.vy_ref
                    ) / s_ref
                    if along_f >= 0.010:
                        credit = k_step * min(along_f / 0.030, 1.5)
                        if budget_m > 0.0:
                            if env._step_disp_bank >= budget_m:
                                env._step_disp_bank -= budget_m
                            else:
                                r_step_denied += credit
                                credit = 0.0
                        r_step += credit
            elif on and env._foot_on[f] \
                    and env._foot_prev_xy[f] is not None:
                slip = float(np.linalg.norm(
                    xy - env._foot_prev_xy[f]))
                prev_meaningful = (
                    env._foot_prev_force[f] >= tslip_contact_n)
                if meaningful and prev_meaningful:
                    tv = slip / max(env.dt, 1e-9)
                    tangent_vels[f] = tv
                    measured_tangent_vels.append(tv)
                    env._foot_tan_slip_m[f] += slip
                    ex = max(tv - tslip_deadband, 0.0)
                    if tslip_cap > 0.0:
                        ex = min(ex, tslip_cap)
                    tangent_excess.append(ex)
                if k_drag > 0.0 and slip > k_drag_deadband_m:
                    r_drag -= k_drag * slip
                if k_ds > 0.0 and slip > ds_floor:
                    acc0 = env._stance_slip_acc[f]
                    acc1 = acc0 + slip
                    env._stance_slip_acc[f] = acc1
                    # Incremental charge: integrates to
                    # k * max(stance travel - allowance, 0)
                    # per stance, paid as it accrues (a foot
                    # that never lifts cannot defer payment).
                    r_ds -= k_ds * (max(acc1 - allow_m, 0.0)
                                    - max(acc0 - allow_m, 0.0))
                if k_wts > 0.0 and f not in lift:
                    wts_both_meaningful = (
                        wts_meaningful and env._foot_prev_force[f]
                        >= wts_contact_n)
                    ex_w = 0.0
                    if wts_both_meaningful:
                        tv_w = slip / max(env.dt, 1e-9)
                        ex_w = max(tv_w - wts_deadband, 0.0)
                        if wts_cap > 0.0:
                            ex_w = min(ex_w, wts_cap)
                    # Live touchdown-window continuation +
                    # trailing liftoff ring, both advanced on
                    # EVERY on-tick (not gated on
                    # wts_both_meaningful) so a low-force
                    # contact gap ages the window/buffer in
                    # TICK time rather than pausing it —
                    # corrected 09-07 per accounting review
                    # fb_20260907T185803_c8af66 (see the
                    # `transition_window_tick` module comment
                    # above).
                    (env._trans_td_count[f],
                     env._trans_lo_buf[f],
                     wts_live_charge) = transition_window_tick(
                        env._trans_td_count[f],
                        env._trans_lo_buf[f],
                        meaningful=wts_both_meaningful,
                        ex_w=ex_w, lo_ticks=wts_lo_ticks)
                    if wts_live_charge is not None:
                        wts_excess.append(wts_live_charge)
                        wts_td_events += 1
            if not on and env._liftoff_xy[f] is not None:
                swinging_flags[f] = True
                air_times_s[f] = (env._step_i
                                  - env._liftoff_step[f]) * env.dt
            env._foot_prev_xy[f] = xy.copy()
            env._foot_prev_force[f] = force
            if g_swinit > 0.0:
                env._swinit_load_ema[f] = (
                    env._swinit_load_ema[f]
                    + (env.dt / 0.3)
                    * (force - env._swinit_load_ema[f]))
            env._foot_on[f] = on
        if k_tslip > 0.0:
            if tangent_excess:
                r_tslip = -k_tslip * float(np.mean(tangent_excess))
            reward += r_tslip
            info["reward_foot_slip_tangent"] = r_tslip
        if k_wts > 0.0:
            if wts_excess:
                r_wts = -k_wts * float(np.mean(wts_excess))
            reward += r_wts
            info["reward_walk_transition_slip"] = r_wts
            info["walk_transition_td_events"] = float(
                wts_td_events)
            info["walk_transition_lo_events"] = float(
                wts_lo_events)
        if k_tslip > 0.0 or contact_diag:
            info["walk_contact_feet"] = float(sum(contacts))
            info["walk_contact_meaningful_feet"] = float(
                meaningful_contacts)
            if measured_tangent_vels:
                info["walk_tangent_contact_vel_mean_m_s"] = float(
                    np.mean(measured_tangent_vels))
                info["walk_tangent_contact_vel_max_m_s"] = float(
                    max(measured_tangent_vels))
            else:
                info["walk_tangent_contact_vel_mean_m_s"] = 0.0
                info["walk_tangent_contact_vel_max_m_s"] = 0.0
            info["walk_touchdown_count"] = float(
                sum(touchdown_flags))
            info["walk_liftoff_count"] = float(sum(liftoff_flags))
            info["walk_swinging_feet"] = float(sum(swinging_flags))
        if contact_diag:
            for f in range(6):
                info[f"walk_foot{f}_contact"] = (
                    1.0 if contacts[f] else 0.0)
                info[f"walk_foot{f}_meaningful_contact"] = (
                    1.0 if contact_forces[f] >= tslip_contact_n
                    and contacts[f] else 0.0)
                info[f"walk_foot{f}_contact_force"] = (
                    contact_forces[f])
                info[f"walk_foot{f}_tangent_vel_m_s"] = (
                    tangent_vels[f])
                info[f"walk_foot{f}_tangent_slip_m_total"] = (
                    env._foot_tan_slip_m[f])
                info[f"walk_foot{f}_swinging"] = (
                    1.0 if swinging_flags[f] else 0.0)
                info[f"walk_foot{f}_touchdown"] = (
                    1.0 if touchdown_flags[f] else 0.0)
                info[f"walk_foot{f}_liftoff"] = (
                    1.0 if liftoff_flags[f] else 0.0)
                info[f"walk_foot{f}_air_time_s"] = air_times_s[f]
        if r_swing:
            reward += r_swing
        if k_swing > 0.0:
            info["reward_swing"] = r_swing
        if r_swinit:
            reward += r_swinit
        if g_swinit > 0.0:
            info["reward_walk_leg_swing_initiation"] = r_swinit
        if k_step > 0.0:
            reward += r_step
            info["reward_step_event"] = r_step
            if budget_m > 0.0:
                info["walk_step_denied"] = r_step_denied
                info["walk_step_bank_m"] = env._step_disp_bank
        if k_drag > 0.0:
            reward += r_drag
            info["reward_drag"] = r_drag
        if k_ds > 0.0:
            reward += r_ds
            info["reward_drag_stance"] = r_ds
        if g_duty > 0.0:
            # walk_duty_gate bookkeeping (09-05): trailing
            # contact-duty window, own state so k_park's
            # window config cannot perturb the gate.
            env._dgate_hist.append(
                [1.0 if c else 0.0 for c in contacts])
            n_dwin = max(1, int(round(float(cfg_get(
                env.cfg, "reward", "duty_gate_window_s",
                default=3.0)) / env.dt)))
            if len(env._dgate_hist) > n_dwin:
                env._dgate_hist = env._dgate_hist[-n_dwin:]
        if g_swing > 0.0:
            # walk_swing_gate bookkeeping (09-05): trailing
            # qualifying-swing-event window, own state so
            # neither k_park's nor walk_duty_gate's window
            # config can perturb this gate.
            env._swing_gate_hist.append(
                [1.0 if s else 0.0 for s in swing_gate_flags])
            n_swin = max(1, int(round(float(cfg_get(
                env.cfg, "reward", "swing_gate_window_s",
                default=4.0)) / env.dt)))
            if len(env._swing_gate_hist) > n_swin:
                env._swing_gate_hist = (
                    env._swing_gate_hist[-n_swin:])
        if g_ratio > 0.0:
            # walk_leg_duty_ratio_charge bookkeeping (09-08):
            # own EMA, independent of every other gate's
            # window/EMA state above. Updates with THIS tick's
            # contacts so the price block (which ran earlier
            # this same step()) always reads last tick's value
            # -- the same one-tick lag every other gate here
            # uses.
            ratio_tau_s = max(float(cfg_get(
                env.cfg, "reward", "walk_leg_duty_ratio_tau_s",
                default=1.0)), env.dt)
            env._legduty_ratio_ema = walk_legduty_ratio_tick(
                env._legduty_ratio_ema,
                on=[1.0 if c else 0.0 for c in contacts],
                dt=env.dt, tau_s=ratio_tau_s)
            env._legduty_ratio_ticks += 1
            if g_ratio_swingfloor > 0.0:
                # walk_leg_duty_ratio_swing_min_count
                # bookkeeping: own trailing qualifying-swing
                # window, independent of walk_swing_gate's
                # _swing_gate_hist so this axis's dose can be
                # sweept standalone.
                env._legduty_ratio_swing_hist.append(
                    [1.0 if s else 0.0 for s in ratio_swing_flags])
                ratio_swing_win = max(1, int(round(float(cfg_get(
                    env.cfg, "reward",
                    "walk_leg_duty_ratio_swing_window_s",
                    default=4.0)) / env.dt)))
                if len(env._legduty_ratio_swing_hist) \
                        > ratio_swing_win:
                    env._legduty_ratio_swing_hist = (
                        env._legduty_ratio_swing_hist[
                            -ratio_swing_win:])
        if g_lsratio > 0.0:
            # walk_leg_loadslip_ratio_charge bookkeeping
            # (09-08): own EMA, independent of every other
            # gate's window/EMA state above (including the
            # duty-ratio charge's own EMA just above -- both
            # can run simultaneously without perturbing each
            # other). Updates with THIS tick's per-foot
            # tangential velocity (`tangent_vels`, already
            # computed by the per-foot loop above whenever
            # this gate's own OR-clause enabled it) so the
            # price block (which ran earlier this same
            # step()) always reads last tick's value -- same
            # one-tick lag every other gate here uses.
            lsratio_tau_s = max(float(cfg_get(
                env.cfg, "reward", "walk_leg_loadslip_ratio_tau_s",
                default=1.0)), env.dt)
            env._legslip_ratio_ema = walk_legslip_ratio_tick(
                env._legslip_ratio_ema, tv=tangent_vels,
                dt=env.dt, tau_s=lsratio_tau_s)
            env._legslip_ratio_ticks += 1
        if g_swinggap > 0.0:
            # walk_leg_swing_gap_charge bookkeeping (09-08):
            # per-leg seconds-since-last-qualifying-swing --
            # reset to 0 on a leg that completed a qualifying
            # swing THIS tick (`swinggap_flags`), otherwise
            # incremented by dt. Own state (`_swing_gap_s`),
            # independent of every other gate's window/EMA/
            # hist above; updates with THIS tick's swing
            # events so the price block (which ran earlier
            # this same step()) always reads last tick's
            # value -- same one-tick lag every other gate uses.
            env._swing_gap_s = [
                0.0 if swinggap_flags[f]
                else (env._swing_gap_s[f] + env.dt)
                for f in range(6)
            ]
        if k_park > 0.0:
            env._duty_hist.append(
                [1.0 if c else 0.0 for c in contacts])
            n_win = int(round(float(cfg_get(
                env.cfg, "goal", "park_duty_window_s",
                default=2.0)) / env.dt))
            if len(env._duty_hist) > n_win:
                env._duty_hist = env._duty_hist[-n_win:]
            r_park = 0.0
            if len(env._duty_hist) >= n_win:
                duty = np.mean(env._duty_hist, axis=0)
                # Lift-leg exemption (quadwalk): the window
                # spans only the support legs — a permanently
                # lifted front is the COMMAND, not a park
                # (audit 08-13: all six spanned meant an
                # honest quad stance paid ~0.2k every tick).
                # `lift` empty (walk mode) = original array,
                # bit-exact.
                if lift:
                    duty = duty[[f for f in range(6)
                                 if f not in lift]]
                over = float(np.sum(
                    np.maximum(0.0, duty - 0.9)
                    + np.maximum(0.0, 0.1 - duty)))
                r_park = -k_park * over
                reward += r_park
            info["reward_park_duty"] = r_park
    return reward


def phase_contact_agreement(env, info, reward, s_ref):
    # Tripod phase clock + contact-agreement reward (walk-routed
    # by construction; runs only while a velocity is commanded so
    # the settle hold is never charged). Parked/dragged legs
    # average 50% agreement = zero net reward; only stepping in
    # sync with the clock pays.
    if env._phase_obs and s_ref > 1e-3:
        # clock already advanced in _augment_obs (same tick)
        k_phase = float(cfg_get(env.cfg, "reward",
                                "k_phase_contact", default=0.0))
        if k_phase > 0.0:
            stance_a = math.sin(env._phase) >= 0.0
            agree = 0
            for f in range(6):
                adr = env._touch_adr[f]
                on = (adr >= 0 and
                      float(env.data.sensordata[adr]) > 0.5)
                expect_on = ((f in PHASE_TRIPOD_A) == stance_a)
                agree += int(on == expect_on)
            r_phase = k_phase * (agree / 6.0 - 0.5) * 2.0
            reward = float(reward) + r_phase
            info["reward_phase_contact"] = r_phase
            info["phase_agreement"] = agree / 6.0
    return reward
