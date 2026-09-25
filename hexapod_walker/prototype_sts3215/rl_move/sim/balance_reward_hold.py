"""Hold/track-mode prices of the balance env's _step_finish: the
reward_hold_barrier schema key, the HOLD/TRACK stillness + feet-load
pricing (reward.hold_still_gate), the hold min-foot-load shortfall price
and the transition foot-drag metric; moved verbatim out of sim_env.py.
"""
from __future__ import annotations

import math
import numpy as np

from rl_move.config import cfg_get

from .balance_helpers import PLANT_SPEC


def hold_still_gate_reward(env, goal, parts, ref_quiet, reward):
    """reward_hold_barrier schema key + HOLD/TRACK stillness and feet-load
    pricing (reward.hold_still_gate); moved verbatim from
    SimHexapodBalanceEnv._step_finish.
    """
    # reward_hold_barrier: the reward.hold_barrier_gain barrier
    # shaping was removed (both 09-13 canaries CANARY FAIL -
    # MECHANISM); the key stays at 0.0 so the info/W&B schema is
    # unchanged.
    parts["reward_hold_barrier"] = 0.0
    # HOLD/TRACK stillness+feet pricing (2026-08-11, cfg
    # reward.hold_still_gate in [0,1], default 0 = legacy exact).
    # cw-stand-bc1-hard1's dig-in showed hold/track are not quiet
    # stands under the stand-line stack: the tracking kernel pays
    # torso attitude/height with NO opinion on the legs, so a policy
    # that cycles legs continuously (duty 0.85/0.09, 6-19 swings per
    # 15 s episode, feet ending 100-161 mm up) or parks two legs
    # splayed in the air collects near-full income; k_still is a
    # BONUS (default 0) and charges nothing. This gate scales the
    # kernel income on hold/track ticks by
    #   feet_factor * still_factor, where
    #   feet_factor = (fraction of feet down)^2 x HARD zero when any
    #     foot exceeds PLANT_SPEC.flag_leg_mm (60 mm: honest
    #     recovery/adjustment swings stay far below it, the observed
    #     splay sits at 100-160 mm),
    #   still_factor = Gaussian on mean qd^2 (sigma 0.3 rad/s),
    #     applied only while the reference is stationary so TRACK's
    #     commanded attitude motion is never charged.
    # Blend: f = (1-g) + g*feet*still. Scoped strictly to
    # hold/track (quad lifts legs on purpose, unload opens a
    # contact on purpose, rise/lower/raise have their own stacks).
    # A fresh v2 HOLD bank must re-pin these orderings before promotion.
    g_hold = float(cfg_get(env.cfg, "reward", "hold_still_gate",
                           default=0.0))
    if (g_hold > 0.0 and goal is not None
            and env._goal_traj is not None
            and getattr(env._goal_traj, "mode", "") in ("hold",
                                                         "track")
            and env._pad_z_ref is not None):
        clear_h = np.array(
            [float(env.data.xpos[b, 2]) - env._pad_z_ref[i]
             for i, b in enumerate(env._pad_bids)])
        n_down_h = float(np.sum(
            clear_h <= PLANT_SPEC["foot_down_mm"] * 0.001))
        # No-flag factor: hard zero by default. cw-stand-holdstill1
        # (08-11) showed the hard zero is a zero-gradient plateau:
        # a leg parked at ~110 mm earns 0 income, but so does every
        # nearby behavior, so PPO gets no slope pointing the leg
        # back down and the park persists. reward.hold_flag_fade=1
        # swaps a linear fade over [flag_leg_mm, 2*flag_leg_mm]
        # (60->120 mm): compliant poses keep exactly 1.0, the
        # observed 110 mm park earns scraps WITH a downhill slope,
        # and the 190 mm class still earns 0.
        worst_h = float(np.max(clear_h))
        flag_m = PLANT_SPEC["flag_leg_mm"] * 0.001
        if float(cfg_get(env.cfg, "reward", "hold_flag_fade",
                         default=0.0)) > 0.0:
            noflag_h = min(max((2.0 * flag_m - worst_h) / flag_m,
                               0.0), 1.0)
        else:
            noflag_h = 1.0 if worst_h <= flag_m else 0.0
        feet_h = (n_down_h / max(float(len(clear_h)), 1.0)) ** 2 \
            * noflag_h
        # Measured-load gate on hold income (2026-08-11, cfg
        # reward.hold_feet_load in [0,1], default 0 = legacy
        # exact). The crouchrise1/2/3 trio all converged on the
        # SAME hold cheat under this stack: two legs hover 1-19 mm
        # up — below foot_down_mm (20 mm), so the clearance count
        # above prices them as "down", and far below flag_leg_mm,
        # so the no-flag fade never fires — while the eval's
        # contact-duty clause (touch force > 0.5 N) reads them at
        # 0.01-0.04 duty. Clearance is the wrong proxy at the
        # bottom of its range; the gate must price MEASURED LOAD,
        # the same signal the gate metric uses. Per-foot
        #   s_i = max(clip(touch_N / 1 N, 0, 1), floor)
        # multiplied over the six feet: an all-loaded stance keeps
        # exactly 1.0 (per-foot force >> 1 N at this robot's
        # weight), each unloaded foot costs a factor of
        # hold_load_floor (0.5 -> the two-leg hover earns 0.25, the
        # fade bank's "scraps, not a living" band), and the linear
        # ramp below ref gives partially-loaded feet a slope. The
        # holdstill1 zero-gradient lesson doesn't apply: this
        # plateau is only the ~2 mm to contact (crossed constantly
        # by DR + action noise), not a 50 mm climb, and the floor
        # keeps paid slope alive everywhere else.
        l_load = float(cfg_get(env.cfg, "reward", "hold_feet_load",
                               default=0.0))
        if l_load > 0.0:
            floor_l = float(cfg_get(env.cfg, "reward",
                                    "hold_load_floor", default=0.5))
            s_feet = []
            for i in range(6):
                if env._touch_adr[i] >= 0:
                    f_n = max(float(
                        env.data.sensordata[env._touch_adr[i]]),
                        0.0)
                    s_i = min(f_n, 1.0)
                else:   # no sensor: fall back to the clearance test
                    s_i = (1.0 if clear_h[i]
                           <= PLANT_SPEC["foot_down_mm"] * 0.001
                           else 0.0)
                s_feet.append(s_i)
            # MIN-over-feet variant (2026-08-12, the pre-registered
            # anchormix1-r1 reopen lever — CURRENT_TRUTHS: "price
            # the min-over-feet load, not the product"). The
            # product with floor 0.5 caps ONE unloaded foot's tax
            # at x0.5 — and six straight stand runs (crouchrise1/2/
            # 3, holdload1, anchorstate1/2, anchormix1-r1) show the
            # habit sheds EXACTLY ONE foot: a five-foot stance at
            # half pay is "sufficient and cheaper", and supervision
            # only moves WHICH foot parks. With
            # reward.hold_feet_load_min=1 the WORST foot is the
            # whole factor: load = max(min_i s_i, min_floor), so a
            # single fully-unloaded foot cuts gated hold income to
            # hold_load_min_floor (default 0.1 — scraps), with the
            # same linear on-ramp below ref for slope. An
            # all-loaded stance keeps exactly 1.0 either way.
            # Default 0 = the legacy product path, bit-exact.
            min_w = float(cfg_get(env.cfg, "reward",
                                  "hold_feet_load_min", default=0.0))
            if min_w > 0.0:
                floor_min = float(cfg_get(
                    env.cfg, "reward", "hold_load_min_floor",
                    default=0.1))
                load_h = max(min(s_feet), floor_min)
            else:
                load_h = 1.0
                for s_i in s_feet:
                    load_h *= max(s_i, floor_l)
            feet_h *= (1.0 - l_load) + l_load * load_h
            parts["hold_load_factor"] = load_h
        still_h = 1.0
        if ref_quiet:
            qd2_h = float(np.mean(np.square(
                env._state.joint_velocity)))
            still_h = math.exp(-qd2_h / (2.0 * 0.3 ** 2))
        f_hold = (1.0 - g_hold) + g_hold * feet_h * still_h
        r_task_h = parts.get("reward_task", 0.0)
        if r_task_h > 0.0:
            reward += r_task_h * (f_hold - 1.0)
            parts["reward_task"] = r_task_h * f_hold
        parts["hold_feet_factor"] = feet_h
        parts["hold_still_factor"] = still_h
    return reward


def hold_minload_shortfall_reward(env, minload_floor_n, minload_in_hold, minload_short_k, parts, reward):
    """HOLD min-foot-load shortfall price; moved verbatim from
    SimHexapodBalanceEnv._step_finish.
    """
    # HOLD min-foot-load SHORTFALL price (2026-09-04, standwalk
    # transtress-s1-acq8m dig-in -- the priced twin of the
    # hold_min_load termination, per the 08-24 op ruling pattern
    # "termination WITH a price"). The acq8m FAIL showed the
    # termination alone does not teach the switch: 6/72 stress
    # episodes still die in mid-transition hold entries after 8M
    # steps because the only signal against an unloaded-through-
    # the-switch foot is a CLIFF that fires ~grace+sustain (~2 s)
    # AFTER the causal foot placement, with zero dense gradient in
    # between (hold_feet_load only scales income, and the
    # termination grace window is a blind spot by design). This
    # charge is that gradient: every hold-mode tick pays
    #   -k * dt * max(0, 1 - ema/floor)
    # with the SAME min-over-feet EMA and floor the termination
    # reads (reward optimum == gate behavior, 08-21 alignment
    # rule), active from the very FIRST hold tick INCLUDING the
    # grace window -- planting the worst foot faster genuinely
    # shrinks the integral, so the optimum is "re-plant all six
    # feet at entry", exactly what the eval terminates on. Designed
    # to run WITH hold_min_load_ema_continuous=1 (otherwise the
    # zero/stale entry EMA makes the entry ticks spuriously
    # charged/blind). reward.k_hold_min_load_short default 0.0 =
    # off, bit-exact.
    if (minload_short_k > 0.0 and minload_in_hold
            and env._pad_z_ref is not None):
        short_ml = max(0.0, 1.0 - env._hold_minload_ema
                       / max(minload_floor_n, 1e-6))
        if short_ml > 0.0:
            pen_ml = minload_short_k * short_ml * env.dt
            reward -= pen_ml
            parts["hold_minload_short"] = parts.get(
                "hold_minload_short", 0.0) - pen_ml
    return reward


def transition_foot_drag_metric(env, parts):
    """Transition foot-drag metric (parts trans_drag_mm); moved verbatim
    from SimHexapodBalanceEnv._step_finish.
    """
    # Transition foot-drag metric (operator 08-11 night: stand/sit
    # scrape their feet across the floor and nothing outside walk
    # mode measured it). trans_drag_mm = loaded foot-XY translation
    # this tick (per-foot deadband, walk's k_drag_loaded convention)
    # on every NON-walk tick: rise, lower, raise, hold, track, lean,
    # unload, quad. A pivoting/sliding loaded foot counts; a foot
    # that LIFTS and steps does not. Emitted whenever the axis is
    # measured so evals and W&B can watch the dragging.
    mode_td = (getattr(env._goal_traj, "mode", "")
               if env._goal_traj is not None else "")
    if mode_td and mode_td != "walk":
        drag_td = 0.0
        # Deadband was a bare 0.5mm/tick literal calibrated at the
        # pre-08-24 default control.hz=25 (dt=0.04s) against
        # "dragging strokes run 0.4-0.5mm/tick" measurements -- a
        # PER-TICK floor, not a per-second one. At today's default
        # control.hz=100 (dt=0.01s) the identical literal represents
        # a 4x LOOSER real-world velocity floor (50mm/s instead of
        # the intended ~12.5mm/s), silently swallowing genuine slow
        # persistent slip (2026-09-02 trans_drag semantics-bank
        # dig-in). Scale by dt/0.04 so hz=25 stays bit-exact
        # (scale=1.0) and hz=100 correctly shrinks to the same
        # real-velocity floor -- mirrors how safety.max_delta_q_deg
        # is already hz-scaled by convention.
        tdrag_deadband_m = 0.0005 * (env.dt / 0.04)
        for f_td in range(6):
            adr_td = env._touch_adr[f_td]
            on_td = (adr_td >= 0 and
                     float(env.data.sensordata[adr_td]) > 0.5)
            xy_td = env.data.xpos[env._pad_bids[f_td], :2]
            if (on_td and env._tdrag_prev_on[f_td]
                    and env._tdrag_prev_xy[f_td] is not None):
                slip_td = float(np.linalg.norm(
                    xy_td - env._tdrag_prev_xy[f_td]))
                if slip_td > tdrag_deadband_m:
                    drag_td += slip_td
            env._tdrag_prev_xy[f_td] = xy_td.copy()
            env._tdrag_prev_on[f_td] = on_td
        parts["trans_drag_mm"] = drag_td * 1000.0

