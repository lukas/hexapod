"""Walk-mode velocity/progress INCOME and direction telemetry, moved out of SimHexapodJointWalkEnv._post_step.

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
    WALK_CMD_MODE_IDS, WALK_DIRECTION_MIN_SPEED_M_S, _add_walk_direction_info,
    walk_cmd_track_score, walk_freeprog_score,
)


def direction_telemetry(env,
                        along, cmd_cross, goal, info, k_cmd_track, s_ref, v):
    _add_walk_direction_info(
        info, float(v[0]), float(v[1]),
        float(goal.vx_ref), float(goal.vy_ref),
        min_speed_m_s=WALK_DIRECTION_MIN_SPEED_M_S)
    # Raw commanded-direction speed telemetry (08-15, operator
    # directive fb_20260815T114414: judge command-following by
    # RAW SIGNED m/s along the requested direction, never by
    # clipped gate factors or total speed; SIMPLIFIED by
    # fb_20260815T115650: NO per-heading bin keys in training —
    # uniform [-pi,pi] heading sampling + the signed average
    # already zeroes out command-ignorant motion, and fixed
    # 8/12-direction panels belong in held-out EVAL only). cfg
    # goal.walk_cmd_metrics=1; default 0 = no new info keys,
    # legacy info dict bit-exact. Emitted ONLY on
    # active-command ticks (s_ref > 1e-3), so the trainers'
    # info-scalar means are per-ACTIVE-tick by construction.
    if (s_ref > 1e-3 and float(cfg_get(
            env.cfg, "goal", "walk_cmd_metrics",
            default=0.0)) == 1.0):
        ux, uy = goal.vx_ref / s_ref, goal.vy_ref / s_ref
        info["v_along_cmd_m_s"] = float(along)
        info["v_cross_abs_m_s"] = (
            cmd_cross if k_cmd_track > 0.0 else
            abs(float(ux * v[1] - uy * v[0])))
        info["cmd_speed_m_s"] = s_ref
        info["wrong_way"] = 1.0 if along < 0.0 else 0.0
        info["walk_cmd_mode_id"] = WALK_CMD_MODE_IDS.get(
            getattr(env._goal_traj, "cmd_mode", "legacy"), 0)
        # Walk-direction telemetry (operator directive
        # fb_20260815T192912): angular error in DEGREES between
        # the achieved planar velocity and the commanded
        # direction. Direction is undefined near zero speed, so
        # ticks are VALID only when actual speed >= 5 mm/s;
        # walk_dir_valid is emitted on every active tick (its
        # mean = valid fraction) while the deg key is emitted
        # only on valid ticks (its mean = error over valid
        # ticks). Same walk_cmd_metrics gate as above: the
        # default (0) keeps the legacy info dict bit-exact.
        spd = float(np.hypot(*v))
        dir_valid = spd >= 5e-3
        info["walk_dir_valid"] = 1.0 if dir_valid else 0.0
        if dir_valid:
            cosang = max(-1.0, min(1.0, float(along) / spd))
            info["walk_direction_err_deg"] = math.degrees(
                math.acos(cosang))
    if env._walk_bucket is not None:
        info["walk_bucket"] = env._walk_bucket


def cmd_track_objective(env, along, goal, v):
    # Simple physical joystick objective (default off). Unlike the
    # historical Gaussian/proxy stack, this is negative for parking,
    # cross-track travel, and wrong-way travel by construction.
    k_cmd_track = max(0.0, float(cfg_get(
        env.cfg, "reward", "k_walk_cmd_track", default=0.0)))
    r_cmd_track = 0.0
    cmd_cross = 0.0
    if k_cmd_track > 0.0:
        cmd_score, cmd_along, cmd_cross = walk_cmd_track_score(
            float(v[0]), float(v[1]), goal.vx_ref, goal.vy_ref,
            stop_speed_m_s=float(cfg_get(
                env.cfg, "goal", "walk_speed_min_m_s",
                default=0.03)))
        along = cmd_along
        r_cmd_track = k_cmd_track * cmd_score
    return along, cmd_cross, k_cmd_track, r_cmd_track


def freeprog_income(env, along, goal, info, r_prog, r_walk, s_ref, v):
    # Direction-first, SPEED-TARGET-FREE walk income (operator
    # order 2026-08-21, from-scratch anti-slip walking line).
    # The Gaussian kernel above and the linear progress term
    # both price a commanded SPEED; the operator's task says the
    # policy must move in the commanded DIRECTION and actually
    # travel, but does NOT have to track a speed. When
    # reward.k_walk_freeprog > 0 both are REPLACED by
    # walk_freeprog_score (see its docstring): saturating
    # along-command credit, cross-track/backward charge, no
    # band term. The positive part rides every income gate
    # below (anchor / loadslip / height / gait), the negative
    # part is added ungated at the total so a gate can never
    # shrink a penalty. Pair it with reward.walk_loadslip_gate +
    # reward.k_loadslip_excess (structural loaded-slip
    # accounting) and reward.k_walk_idle_charge (anti-park
    # travel floor); do NOT enable walk_kernel_prog_gate with
    # it — that gate re-introduces a speed target by scaling
    # income with achieved fraction of the commanded speed.
    # Default 0 = off, legacy bit-exact (no new info keys).
    # cfg: reward.k_walk_freeprog, reward.walk_freeprog_cap_m_s.
    k_free = float(cfg_get(env.cfg, "reward",
                           "k_walk_freeprog", default=0.0))
    r_free_pen = 0.0
    if k_free > 0.0 and s_ref > 1e-3:
        # Stride-EMA input (08-22, freeprog-term400-stall dig-in
        # follow-up): a second concurrent cycle's std-anneal
        # arm (cw-amp-m2-freeprog-term400-stdanneal, FAIL)
        # root-caused the marching-in-place plateau as a
        # REWARD-SHAPE defect, not exploration noise —
        # walk_freeprog_score's INSTANTANEOUS along-command
        # velocity nets to ~0 for a symmetric back-and-forth
        # stepping gait (push-off and recovery lobes cancel in
        # the per-tick average) exactly the same way the
        # phasedir7 kernel dig-in found for the Gaussian
        # kernel term above — so it cannot distinguish "no net
        # travel" from "just starting to walk slowly" by
        # construction. Reuse of the SAME already-validated
        # fix (reward.walk_kernel_vel_ema, phasedir7/7b/8):
        # when both flags are on, freeprog scores the
        # STRIDE-AVERAGED velocity (env._walk_kernel_vema,
        # already updated unconditionally above whenever the
        # flag is set) instead of the raw instantaneous one,
        # so a true net-zero marcher still nets ~0 (unchanged)
        # but a policy that starts converting oscillation into
        # real forward drift gets a cleaner, less noise-
        # cancelled gradient toward it. Default (flag off) is
        # bit-exact legacy (raw v, unchanged).
        if float(cfg_get(env.cfg, "reward", "walk_kernel_vel_ema",
                         default=0.0)) > 0.0:
            fv0, fv1 = (env._walk_kernel_vema[0],
                       env._walk_kernel_vema[1])
        else:
            fv0, fv1 = float(v[0]), float(v[1])
        _fp_cap = float(cfg_get(env.cfg, "reward",
                                "walk_freeprog_cap_m_s",
                                default=0.06))
        # Command SPEED-range widening (walkcurr item(1),
        # 09-07 realism ladder): with a single fixed episode
        # speed (min==max) the cap above always equals s_ref,
        # so this branch is a no-op and every existing lineage
        # is bit-exact. Once goal.walk_speed_min/max_m_s are
        # widened into a real band, a FIXED cap makes the
        # command's SPEED MAGNITUDE reward-invisible: a slow
        # command (e.g. 0.03 m/s) already saturates income at
        # the old fixed cap by going no faster than before,
        # and a fast command (e.g. 0.09 m/s) saturates at the
        # SAME old cap too, so faster/slower commands stop
        # differing in what they price. reward.walk_freeprog_
        # cap_dynamic (default 0 = off, bit-exact: no new info
        # key, no cap change) raises the effective cap to
        # max(fixed_cap, s_ref) — commands at/below the fixed
        # cap keep the legacy permissive behavior (still never
        # punished for going faster than commanded, per the
        # walkcurr_pf no-speed-band bank), commands ABOVE it
        # get their own per-episode speed as the saturation
        # point instead of silently under-pricing them.
        if float(cfg_get(env.cfg, "reward",
                         "walk_freeprog_cap_dynamic",
                         default=0.0)) > 0.0:
            _fp_cap = max(_fp_cap, s_ref)
            info["walk_freeprog_cap_used_m_s"] = _fp_cap
        f_score, f_along, f_cross = walk_freeprog_score(
            fv0, fv1, goal.vx_ref, goal.vy_ref, _fp_cap)
        along = f_along
        r_walk = k_free * max(f_score, 0.0)
        r_free_pen = k_free * min(f_score, 0.0)
        r_prog = 0.0
        info["walk_freeprog_score"] = f_score
        info["walk_freeprog_cross"] = f_cross
        # Overspeed SURPLUS charge (2026-09-07, walkcurr
        # slip-mechanism audit, operator focus note
        # 20260907T150325Z): the audit's frozen-champion
        # decomposition (logs/ckpt_eval/slipframe_audit_
        # cont40m) proved the easy0905 champion's ~4.5 slip/m
        # is genuine contact-point sliding (material-point
        # slip == pad-center slip, rolling/chatter/knee-frame
        # artifacts all ruled out) produced by a gait running
        # at 1.6-2.1x the commanded 0.06 m/s — an exact
        # optimum of this saturating score, where speed above
        # the cap is free (test_slipwalk_has_no_speed_band)
        # and every slip/tracking charge is 0. This opt-in key
        # makes the SURPLUS non-free without re-introducing a
        # speed band below the cap: income below/at cap is
        # untouched (ignition asymmetry preserved), along-
        # command speed ABOVE the cap is charged linearly at
        # k_free * this_key * (along/cap - 1), so the reward
        # optimum sits exactly AT the cap instead of at "as
        # fast as the sloppiest gait allows". Uses the same
        # stride-EMA along (f_along) as the income so the
        # charge cannot fire on within-stride oscillation the
        # income itself smooths away. Default 0.0 = off,
        # bit-exact legacy (no new info key). Bank:
        # test_task_semantics.py WALKCURR_OVERSPEED_* tests.
        k_over = float(cfg_get(
            env.cfg, "reward",
            "walk_freeprog_overspeed_charge", default=0.0))
        if k_over > 0.0:
            _over = max(f_along / _fp_cap - 1.0, 0.0)
            if _over > 0.0:
                r_free_pen -= k_free * k_over * _over
                info["walk_freeprog_overspeed"] = round(_over, 4)
    return along, r_free_pen, r_prog, r_walk
