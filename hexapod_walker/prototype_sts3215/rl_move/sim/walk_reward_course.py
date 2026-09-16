"""Walk-mode commanded-COURSE charges, moved out of SimHexapodJointWalkEnv._post_step.

Every function here is one contiguous block of the walk-mode pricing stack
moved mechanically: ``env`` is the env instance (the former ``self``), the
remaining parameters are the block's live inputs and the return values its
live outputs, so the call site in ``_post_step`` is a single assignment.
Bodies are byte-identical to the original apart from ``self`` -> ``env``
and re-indentation; the header comments travelled with the code.
"""
from __future__ import annotations

import math

from collections import deque

from rl_move.config import cfg_get


def course_increment_and_sway_charges(env,
                                      goal, info, reward, s_ref, support_gate):
    # ---------------------------------------------------------
    # Windowed command-following INCOME + excess-sway charge
    # (operator reward-design directive fb_20260829T142239_63c818,
    # 2026-08-29). The directive: the training reward must not
    # punish honest short-term tripod sway; the PRIMARY
    # moving-command income compares NET body displacement over
    # a gait-scale window to the command INTEGRATED over the
    # same window ("did the robot advance the requested
    # distance in the requested direction while staying upright
    # and supported?"), gated by support quality; a SEPARATE
    # term charges only sway EXCESS beyond a clean-teacher-
    # calibrated allowance.
    #
    # TEACHER CALIBRATION (probe_dir_floor --envelope-windows,
    # mesh/100 Hz/0.375 deg-tick/0.08 m/s, 2026-08-29, values
    # identical across seeds because DR-0 scripted rollouts are
    # deterministic): windowed course error med 1.2-2.2 deg,
    # p95 <= 5.2 deg (0.5-2.0 s windows); perpendicular sway
    # RMS p95 <= 1.7 mm; along-command completion ratio ~0.39
    # (the scripted teacher CANNOT reach the commanded 0.08
    # under the mesh/100 Hz slew contract — so a raw
    # |disp - cmd| vector kernel is speed-deficit-dominated and
    # would pay a PARK 0.33 of max; refuted before launch,
    # hence the angle-factor x speed-factor decomposition).
    #
    # Income per commanded tick, all factors in [0, 1]:
    #   k * support_gate                     (directive item 5)
    #     * angle_factor(course err, teacher-deadbanded)
    #     * speed_factor(along completion vs command)
    # angle_factor = 1 inside walk_course_income_deadband_deg
    # (default 6 deg ~= teacher p95 + margin: the teacher's own
    # honest sway is NEVER charged), Gaussian falloff with
    # walk_course_income_sigma_deg (20) beyond it. speed_factor
    # = clip(along_disp / cmd_disp, 0, 1): parking/refusal ~0,
    # sideways ~0 via angle, backward 0 (clip), overspeed
    # capped at 1 and priced by the course_disp overspeed twin.
    # Windows with any stop tick pay nothing (command switches:
    # the integrated command IS the time-averaged reference,
    # per item 7). No net motion above
    # walk_course_income_min_speed_m_s => no direction => no
    # income. Defaults 0 = OFF: no state, no info keys, reward
    # bit-exact legacy.
    # cfg: reward.k_walk_course_income,
    # reward.walk_course_income_window_s (0.75 = teacher gait
    # period), reward.walk_course_income_deadband_deg (6),
    # reward.walk_course_income_sigma_deg (20). The net-motion
    # floor is a fixed 0.01 m/s and the support product always
    # gates the income.
    #
    # Excess-sway charge (item 4): RMS perpendicular deviation
    # of the body path around the commanded-course line through
    # the window start, MINUS the teacher-calibrated allowance
    # reward.walk_sway_allow_mm (default 5 mm ~= 3x teacher p95
    # — clean tripod sway rides free), charged
    # -k * min(excess/allow, 3) per tick. Charges the unified
    # lineage's cm-scale zigzag hard while the honest gait's
    # <2 mm RMS never activates. Added after every income gate
    # (charges are never shrunk).
    # cfg: reward.k_walk_excess_sway,
    # reward.walk_sway_window_s (0.75), reward.walk_sway_allow_mm.
    k_cinc = float(cfg_get(env.cfg, "reward",
                           "k_walk_course_income", default=0.0))
    k_sway = float(cfg_get(env.cfg, "reward",
                           "k_walk_excess_sway", default=0.0))
    if k_cinc > 0.0 or k_sway > 0.0:
        win_inc_s = max(float(cfg_get(
            env.cfg, "reward", "walk_course_income_window_s",
            default=0.75)), env.dt)
        win_sway_s = max(float(cfg_get(
            env.cfg, "reward", "walk_sway_window_s",
            default=0.75)), env.dt)
        n_inc = max(int(round(win_inc_s / env.dt)), 1)
        n_sway = max(int(round(win_sway_s / env.dt)), 1)
        n_max = max(n_inc if k_cinc > 0.0 else 1,
                    n_sway if k_sway > 0.0 else 1)
        whist = env._walk_course_win_hist
        if whist is None or whist.maxlen != n_max + 1:
            whist = deque(maxlen=n_max + 1)
            env._walk_course_win_hist = whist
            env._walk_course_win_cum = [0.0, 0.0, 0]
        cum = env._walk_course_win_cum
        # COMMANDED-YAW-ROTATED course reference (2026-09-07
        # combined-frame audit, probe_combined_frame.py /
        # OPERATOR_QUESTIONS same date): the legacy reference
        # integrates (vx_ref, vy_ref) as a FIXED world-frame
        # chord, but the velocity kernel is BODY-frame and the
        # policy obs (walk_obs_body_vel=2 lineages) carries no
        # world compass — on combined vx+wz ticks the legacy
        # course/sway terms pay REFUSING to turn (measured:
        # wz-ignorer out-earns the faithful arc-follower
        # 2094.5 vs 1959.8 total on the exact turns-run stack,
        # course income +597 vs +438). With
        # reward.walk_course_ref_yaw=1 the per-tick command
        # displacement is rotated by the integral of wz_ref,
        # and each window's reference is anchored at the
        # body's OWN window-start heading — the body-frame
        # joystick semantics (vx forward + wz = an arc): a
        # perfect body-frame arc tracker scores zero course
        # error at any wz. Default 0 = legacy world-chord
        # math, bit-exact (rows stay 5-wide, no rotation).
        ref_yaw_on = float(cfg_get(
            env.cfg, "reward", "walk_course_ref_yaw",
            default=0.0)) == 1.0
        if ref_yaw_on:
            wz_ref_t = float(getattr(goal, "wz_ref", 0.0))
            th_prev = whist[-1][5] if whist else 0.0
            c_th, s_th = math.cos(th_prev), math.sin(th_prev)
            cum[0] += (c_th * goal.vx_ref
                       - s_th * goal.vy_ref) * env.dt
            cum[1] += (s_th * goal.vx_ref
                       + c_th * goal.vy_ref) * env.dt
        else:
            cum[0] += goal.vx_ref * env.dt
            cum[1] += goal.vy_ref * env.dt
        cum[2] += 1 if s_ref > 1e-3 else 0
        bxy_w = env.data.xpos[env._chassis_bid, :2]
        if ref_yaw_on:
            R_w = env.data.xmat[env._chassis_bid].reshape(3, 3)
            yaw_w = math.atan2(R_w[1, 0], R_w[0, 0])
            whist.append((float(bxy_w[0]), float(bxy_w[1]),
                          cum[0], cum[1], cum[2],
                          th_prev + wz_ref_t * env.dt, yaw_w))
        else:
            whist.append((float(bxy_w[0]), float(bxy_w[1]),
                          cum[0], cum[1], cum[2]))

        def _win(n_ticks):
            """(dx, dy, dcx, dcy) if the trailing n_ticks window
            is complete and fully commanded, else None.  With
            walk_course_ref_yaw=1 the command displacement is
            re-anchored to the window-start body heading."""
            if len(whist) <= n_ticks:
                return None
            p1 = whist[-1]
            p0 = whist[-1 - n_ticks]
            if p1[4] - p0[4] != n_ticks:
                return None      # stop tick inside the window
            dcx, dcy = p1[2] - p0[2], p1[3] - p0[3]
            if ref_yaw_on and len(p0) >= 7:
                off = p0[6] - p0[5]      # yaw0 - theta0
                c_o, s_o = math.cos(off), math.sin(off)
                dcx, dcy = (c_o * dcx - s_o * dcy,
                            s_o * dcx + c_o * dcy)
            return (p1[0] - p0[0], p1[1] - p0[1], dcx, dcy)

        if k_cinc > 0.0 and s_ref > 1e-3:
            w = _win(n_inc)
            if w is not None:
                dx_w, dy_w, dcx_w, dcy_w = w
                d_cmd_w = math.hypot(dcx_w, dcy_w)
                d_w = math.hypot(dx_w, dy_w)
                if (d_cmd_w > 1e-9
                        and d_w >= 0.01 * win_inc_s):
                    cos_ci = max(-1.0, min(1.0, (
                        dx_w * dcx_w + dy_w * dcy_w)
                        / (d_w * d_cmd_w)))
                    err_deg = math.degrees(math.acos(cos_ci))
                    dead = float(cfg_get(
                        env.cfg, "reward",
                        "walk_course_income_deadband_deg",
                        default=6.0))
                    sig = max(float(cfg_get(
                        env.cfg, "reward",
                        "walk_course_income_sigma_deg",
                        default=20.0)), 1e-6)
                    exc = max(err_deg - dead, 0.0)
                    angle_f = math.exp(-0.5 * (exc / sig) ** 2)
                    along_w = (dx_w * dcx_w + dy_w * dcy_w) \
                        / d_cmd_w
                    # speed factor: rises linearly to 1 at
                    # full command completion, then FALLS
                    # beyond (1 + over_tol) — the income
                    # optimum must sit AT the commanded speed
                    # (08-21 ruling: reward optimum == gate
                    # behavior), never above it. Exceeding the
                    # band also pays the course_disp overspeed
                    # twin when armed.
                    ratio_w = along_w / d_cmd_w
                    exceed_w = max(
                        ratio_w - (1.0 + 0.05), 0.0)
                    speed_f = max(min(ratio_w, 1.0)
                                  - exceed_w / 0.5, 0.0)
                    s_gate = support_gate
                    r_cinc = k_cinc * s_gate * angle_f * speed_f
                    reward = float(reward) + r_cinc
                    info["walk_course_income_err_deg"] = err_deg
                    info["walk_course_income_angle_f"] = angle_f
                    info["walk_course_income_speed_f"] = speed_f
                    info["walk_course_income_support"] = s_gate
                    info["reward_walk_course_income"] = r_cinc
        if k_sway > 0.0 and s_ref > 1e-3:
            w = _win(n_sway)
            if w is not None:
                dx_s, dy_s, dcx_s, dcy_s = w
                d_cmd_s = math.hypot(dcx_s, dcy_s)
                d_s = math.hypot(dx_s, dy_s)
                # Charge sway only around a roughly FOLLOWED
                # course (window course err <=
                # walk_sway_course_cap_deg, default 60, and net
                # motion above the income floor): sustained
                # WRONG-course travel (sideways/backward) is
                # priced by the income/course terms — double-
                # charging it here made moving-wrong pay worse
                # than parking, inverting the directive's own
                # required ordering (sideways/backward > park).
                cap_ok = False
                if d_cmd_s > 1e-9 and d_s >= 0.01 * win_sway_s:
                    cos_s = max(-1.0, min(1.0, (
                        dx_s * dcx_s + dy_s * dcy_s)
                        / (d_s * d_cmd_s)))
                    cap_ok = (math.degrees(math.acos(cos_s))
                              <= 60.0)
                if cap_ok:
                    ux_s, uy_s = dcx_s / d_cmd_s, dcy_s / d_cmd_s
                    pts = list(whist)[-1 - n_sway:]
                    x0_s, y0_s = pts[0][0], pts[0][1]
                    acc = 0.0
                    arc_aware = float(cfg_get(
                        env.cfg, "reward",
                        "walk_sway_arc_aware", default=0.0)) == 1.0
                    if arc_aware:
                        # Arc-aware sway (2026-09-06 fix,
                        # OPERATOR_QUESTIONS 09-06 ~13:0x
                        # audit): the legacy branch below
                        # projects every sample against ONE
                        # global chord direction (window
                        # start->end of the COMMAND). That is
                        # correct for a straight/near-straight
                        # command but over-charges a
                        # genuinely CURVING one -- an arc bows
                        # away from its own chord even when
                        # perfectly tracked (measured: the
                        # tight-turn semantics-bank case
                        # decomposed to
                        # reward_walk_course_income=+165 vs
                        # reward_walk_excess_sway=-1177 purely
                        # from this artifact). Fix: build a
                        # "shadow" reference path that starts
                        # at the body's OWN window-start
                        # position (x0_s, y0_s) and replays
                        # the SAME per-tick reference
                        # displacement the command integral
                        # already accumulates (pts[i][2:4], the
                        # whist cum columns) -- i.e. it curves
                        # exactly like the command -- and
                        # project each sample's deviation from
                        # that shadow point onto the LOCAL
                        # per-tick tangent (not the one global
                        # chord direction), so an along-track
                        # completion lag (already priced by
                        # k_walk_course_income's speed_factor)
                        # never leaks into this lateral-only
                        # charge. Bit-exact-off: default 0.0
                        # reproduces the legacy chord math
                        # exactly (same branch below, unused
                        # when arc_aware is False).
                        cum0x, cum0y = pts[0][2], pts[0][3]
                        ux_i, uy_i = ux_s, uy_s
                        # walk_course_ref_yaw: the shadow path
                        # must curve in the SAME re-anchored
                        # frame the _win reference uses (yaw0
                        # - theta0 of this window's own start
                        # row), or its samples would be
                        # compared against an unrotated
                        # reference.
                        c_o2, s_o2 = 1.0, 0.0
                        if ref_yaw_on and len(pts[0]) >= 7:
                            off2 = pts[0][6] - pts[0][5]
                            c_o2 = math.cos(off2)
                            s_o2 = math.sin(off2)
                        for idx in range(1, len(pts)):
                            px, py = pts[idx][0], pts[idx][1]
                            cx, cy = pts[idx][2], pts[idx][3]
                            pcx = pts[idx - 1][2]
                            pcy = pts[idx - 1][3]
                            dtx, dty = cx - pcx, cy - pcy
                            if ref_yaw_on:
                                dtx, dty = (c_o2 * dtx
                                            - s_o2 * dty,
                                            s_o2 * dtx
                                            + c_o2 * dty)
                            dlen = math.hypot(dtx, dty)
                            if dlen > 1e-9:
                                ux_i, uy_i = (dtx / dlen,
                                              dty / dlen)
                            scx, scy = cx - cum0x, cy - cum0y
                            if ref_yaw_on:
                                scx, scy = (c_o2 * scx
                                            - s_o2 * scy,
                                            s_o2 * scx
                                            + c_o2 * scy)
                            rx = x0_s + scx
                            ry = y0_s + scy
                            ddx, ddy = px - rx, py - ry
                            perp = ddx * uy_i - ddy * ux_i
                            acc += perp * perp
                    else:
                        for px, py, *_rest in pts:
                            perp = ((px - x0_s) * uy_s
                                    - (py - y0_s) * ux_s)
                            acc += perp * perp
                    rms_m = math.sqrt(acc / len(pts))
                    allow_m = max(float(cfg_get(
                        env.cfg, "reward",
                        "walk_sway_allow_mm",
                        default=5.0)), 0.1) / 1000.0
                    exc_m = max(rms_m - allow_m, 0.0)
                    info["walk_sway_rms_mm"] = rms_m * 1000.0
                    if exc_m > 0.0:
                        r_sway = -k_sway * min(
                            exc_m / allow_m, 3.0)
                        reward = float(reward) + r_sway
                        info["reward_walk_excess_sway"] = r_sway
    return reward


def course_displacement_charge(env, goal, info, reward, s_ref):
    # Commanded-COURSE charge via NET POSITION DISPLACEMENT
    # (k_walk_course fix-lever (b), 2026-08-29 standwalk
    # DIG-IN). Root-cause chain: `cw-standwalk-unified1-mix-
    # long-s1-cont1` FAILed its own gate (dir_err plateaued at
    # ~62-68 deg the whole 16-32M-step lineage) -> the ONLY
    # course-pricing term above, k_walk_course, was found
    # COMPLETELY INERT for that entire lineage (0/5899 active
    # ticks in a full deterministic repro) because its
    # vector-EMA of INSTANTANEOUS velocity partially CANCELS
    # under stride-to-stride zigzag even when net travel is
    # real -> the obvious scalar fixes on that EMA (lower
    # walk_course_min_speed_m_s, raise walk_course_tau_s) were
    # closed by direct measurement: every floor value in the
    # diagnosed activation band breaks 8 of this file's own
    # the retired pre-v2 phase-direction invariants, and raising tau
    # measurably LOWERS the achieved EMA magnitude instead of
    # raising it. Direct local repro against the FAILED
    # checkpoint's own real rollout (not a scripted proxy)
    # measured why: per-tick INSTANTANEOUS direction error
    # mean/median 57.6/32.7 deg (matches the harness's own
    # `direction_err_mean_deg` headline of ~55-62 almost
    # exactly -- confirming that headline metric is dominated
    # by honest stride sway, the exact noise class the EMA was
    # built to filter) vs. the SAME rollout's net forward-
    # window direction error only 6.2-6.5 deg at EVERY window
    # tested (0.75 - 6.0 s) with mean windowed speed ~0.029 m/s
    # -- comfortably clearing a 0.02 m/s floor even though the
    # vector EMA of the identical ticks never clears 0.04. This
    # term replaces "EMA of instantaneous velocity" with "true
    # net body-position displacement over a trailing window" --
    # a position delta, not a velocity filter -- which is
    # immune to both intra-stride sway AND slow zigzag
    # cancellation by construction: it measures where the body
    # ACTUALLY ENDED UP over the window, not an average of
    # noisy tick-level velocity samples. Independent cfg key
    # from k_walk_course (both may run in the same stack for a
    # controlled canary); same "added after every income gate"
    # placement so no gate can shrink it. The position ring
    # buffer always tracks (cheap: a python deque of (x, y)
    # tuples, per MJX_SNAPSHOT_EXTRA pool-restore convention)
    # whenever this term is on; when k_walk_course_disp is 0
    # the buffer is never allocated (stays None from reset) --
    # no state update, no info keys, reward bit-exact legacy.
    # cfg: reward.k_walk_course_disp,
    # reward.walk_course_disp_window_s,
    # reward.walk_course_disp_min_speed_m_s.
    k_cdisp = float(cfg_get(env.cfg, "reward",
                            "k_walk_course_disp", default=0.0))
    if k_cdisp > 0.0:
        win_s = max(float(cfg_get(
            env.cfg, "reward", "walk_course_disp_window_s",
            default=1.5)), env.dt)
        win_ticks = max(int(round(win_s / env.dt)), 1)
        hist = env._walk_course_disp_hist
        if hist is None or hist.maxlen != win_ticks + 1:
            hist = deque(maxlen=win_ticks + 1)
            env._walk_course_disp_hist = hist
        bxy = env.data.xpos[env._chassis_bid, :2]
        # walk_course_ref_yaw (see the income/sway block below
        # for the audit): with the flag on, rows carry (yaw,
        # commanded-yaw integral) so the window's reference
        # direction can follow the commanded arc instead of
        # the raw world-frame command. Default off = 2-wide
        # rows, bit-exact legacy.
        refyaw_cd = float(cfg_get(
            env.cfg, "reward", "walk_course_ref_yaw",
            default=0.0)) == 1.0
        if refyaw_cd:
            R_cd = env.data.xmat[env._chassis_bid].reshape(3, 3)
            yaw_cd = math.atan2(R_cd[1, 0], R_cd[0, 0])
            th_cd = (hist[-1][3] if hist else 0.0) + float(
                getattr(goal, "wz_ref", 0.0)) * env.dt
            hist.append((float(bxy[0]), float(bxy[1]),
                         yaw_cd, th_cd))
        else:
            hist.append((float(bxy[0]), float(bxy[1])))
        if s_ref > 1e-3 and len(hist) == hist.maxlen:
            dx = hist[-1][0] - hist[0][0]
            dy = hist[-1][1] - hist[0][1]
            d_disp = math.hypot(dx, dy)
            avg_v_disp = d_disp / win_s
            v_min_cd = float(cfg_get(
                env.cfg, "reward",
                "walk_course_disp_min_speed_m_s", default=0.02))
            vx_cd_ref, vy_cd_ref = goal.vx_ref, goal.vy_ref
            if refyaw_cd and len(hist[0]) >= 4:
                # reference = command rotated to the window's
                # arc-chord direction: body heading at window
                # start plus HALF the commanded rotation over
                # the window (chord of a constant-wz arc).
                ang_cd = hist[0][2] + 0.5 * (
                    hist[-1][3] - hist[0][3])
                c_cd, s_cd = math.cos(ang_cd), math.sin(ang_cd)
                vx_cd_ref, vy_cd_ref = (
                    c_cd * goal.vx_ref - s_cd * goal.vy_ref,
                    s_cd * goal.vx_ref + c_cd * goal.vy_ref)
            if avg_v_disp >= v_min_cd:
                cos_cd = max(-1.0, min(1.0, (
                    dx * vx_cd_ref + dy * vy_cd_ref)
                    / (d_disp * s_ref)))
                r_cdisp = -k_cdisp * (1.0 - cos_cd)
                reward = float(reward) + r_cdisp
                info["walk_course_disp_cos"] = cos_cd
                info["walk_course_disp_speed_m_s"] = avg_v_disp
                info["reward_walk_course_disp"] = r_cdisp
            # Windowed-displacement overspeed band charge --
            # exact structural twin of k_walk_course_overspeed
            # (same tol/along-projection/ref-floor knobs) but
            # keyed off avg_v_disp so it is NOT silently
            # disabled when k_walk_course=0 (that term lives
            # inside the k_walk_course>0 gate above and would
            # otherwise vanish for any stack that runs the
            # disp course charge alone -- caught by this
            # mechanism's own bank probe: fastcadence out-
            # earned obey 899 vs 806 fwd before this charge
            # existed, purely because the anti-overspeed
            # protection had gone missing, not because the
            # course term itself mispriced anything). Default
            # 0 = off, bit-exact.
            # cfg: reward.k_walk_course_disp_overspeed,
            # reward.walk_course_disp_overspeed_tol,
            # reward.walk_course_disp_overspeed_along,
            # reward.walk_course_disp_overspeed_ref_floor_m_s.
            k_dcover = float(cfg_get(
                env.cfg, "reward",
                "k_walk_course_disp_overspeed", default=0.0))
            if k_dcover > 0.0:
                tol_dc = float(cfg_get(
                    env.cfg, "reward",
                    "walk_course_disp_overspeed_tol",
                    default=0.05))
                spd_dover = avg_v_disp
                if float(cfg_get(
                        env.cfg, "reward",
                        "walk_course_disp_overspeed_along",
                        default=0.0)) == 1.0:
                    spd_dover = (dx * vx_cd_ref
                                + dy * vy_cd_ref) / (
                                    s_ref * win_s)
                s_den_d = max(s_ref, float(cfg_get(
                    env.cfg, "reward",
                    "walk_course_disp_overspeed_ref_floor_m_s",
                    default=0.0)))
                over_d = max(0.0, spd_dover
                            - (1.0 + tol_dc) * s_den_d)
                if over_d > 0.0:
                    r_dcover = -k_dcover * min(
                        over_d / s_den_d, 3.0)
                    reward = float(reward) + r_dcover
                    info["walk_course_disp_overspeed_m_s"] = (
                        over_d)
                    info["reward_walk_course_disp_overspeed"] = (
                        r_dcover)
    return reward
