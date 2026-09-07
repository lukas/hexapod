"""Combined-command frame audit (todaypolicy robotwalk-turns lineage,
2026-09-07).

WHAT THIS PROBE MEASURES, in one sentence: when the robot is told
"walk forward AND turn" (fixed vx=0.08 m/s + wz=0.25 rad/s, the exact
combined cell the turns campaign keeps failing), does the live reward
stack pay the behavior the yaw terms/eval arcs demand (a body-frame
arc) or the behavior the course-income/eval-course terms demand (a
straight world-frame line), i.e. are the two halves of the reward
mutually contradictory on combined ticks?

Three scripted drives on the REAL env + the EXACT reward stack of
cw-robotwalk-turns-20260906 (ledger cfg, verbatim):
  arc     -- faithful body-frame tracker: stroke (0.08, 0) in the body
             frame while yawing at wz_ref (TripodGait omega=wz).  This
             is what the velocity kernel (body-frame, walk_task
             _body_vel_xy) + yaw income jointly demand, what
             eval_cmd_suite's arc cells call correct, and the hardware
             joystick semantics.
  noturn  -- wz-ignoring straight walker (omega=0): what the
             course-income / excess-sway / eval windowed-course terms
             demand (they integrate (vx_ref, vy_ref) as a FIXED
             world-frame chord, never rotated by wz_ref).
  crab    -- world-course holder that still yaws (omega=wz_ref, linear
             stroke rotated -yaw each tick): the only behavior that
             could satisfy BOTH world-frame course terms and yaw
             income -- at the price of the body-frame kernel.

For each drive: every reward_* channel summed, income factors, then
the EVAL-side windowed course error (windowed_course_stats, 1 s -- the
joygate course_err_1s_med machinery) under (a) the live world-chord
reference and (b) a CORRECTED reference rotated by the commanded yaw
integral anchored at each window-start body pose (the body-frame /
arc-aware semantics).  If arc loses income+eval to noturn under (a)
but wins under (b), the frame confound is proven as the concrete
misalignment mechanism behind course_err_1s_med worsening (8.55 ->
10.2 -> 11.93 deg) while reward rose.
"""
from __future__ import annotations

import math

import numpy as np

CFG = {
    "env.model_source": "mesh", "control.hz": 100,
    "safety.max_delta_q_deg": 0.375, "safety.max_roll_deg": 25,
    "safety.max_pitch_deg": 25,
    "goal.walk_speed_min_m_s": 0.08, "goal.walk_speed_max_m_s": 0.08,
    "goal.walk_heading_max_rad": 3.1415927, "goal.walk_stop_frac": 0.15,
    "goal.walk_cmd_resample_s": 6.0, "goal.walk_cmd_resample_jitter": 0.2,
    "goal.walk_park_start_frac": 0.25, "goal.walk_obs_body_vel": 2,
    "goal.walk_phase_obs": 1, "goal.walk_phase_hz": 1.333333,
    "goal.walk_yaw_cmd": 1, "goal.walk_phase_run_on_yaw": 1,
    "goal.walk_yaw_zero_frac": 0.5,
    "reward.walk_kernel_prog_gate": 1.0, "reward.walk_anchor_gate": 1.0,
    "reward.anchor_tol_mm": 10.0, "reward.walk_height_gate": 1.0,
    "reward.walk_height_sigma_mm": 30.0, "reward.walk_loadslip_gate": 1.0,
    "reward.loadslip_ok": 3.0, "reward.loadslip_max": 6.0,
    "reward.k_loadslip_excess": 10.0, "reward.k_walk_idle_charge": 20.0,
    "reward.walk_idle_speed_m_s": 0.02, "reward.k_park_duty": 2.0,
    "reward.k_drag_loaded": 10.0,
    "reward.k_walk_course_income": 2.0,
    "reward.walk_course_income_window_s": 0.75,
    "reward.walk_course_income_deadband_deg": 6.0,
    "reward.walk_course_income_sigma_deg": 20.0,
    "reward.k_walk_excess_sway": 2.0, "reward.walk_sway_window_s": 0.75,
    "reward.walk_sway_allow_mm": 5.0,
    "reward.k_walk_course_disp": 0.15,
    "reward.walk_course_disp_window_s": 1.5,
    "reward.walk_course_disp_min_speed_m_s": 0.02,
    "reward.k_walk_course_disp_overspeed": 4.0,
    "reward.walk_course_disp_overspeed_tol": 0.05,
    "reward.walk_course_disp_overspeed_along": 1.0,
    "reward.walk_course_disp_overspeed_ref_floor_m_s": 0.06,
    "goal.walk_turn_in_place_frac": 0.30,
    "reward.k_walk_yaw": 1.0, "reward.walk_yaw_kernel_gate": 1.0,
    "reward.walk_kernel_yaw_gate": 1.0, "reward.k_yaw_prog": 1.0,
    "reward.k_yaw_still": 50.0, "reward.walk_yaw_hold_prog_gate": 1.0,
    "reward.yaw_still_avg_s": 1.0, "reward.yaw_prog_overshoot_decay": 1.0,
    "reward.yaw_prog_avg_s": 1.0,
    # optional extras exercised by follow-up arms:
    # reward.walk_sway_arc_aware / reward.walk_course_ref_yaw via --extra
}

VX, WZ = 0.08, 0.25
SECONDS = 8.0


def _rollout(drive: str, extra: dict | None = None, seed: int = 0):
    from rl_move.config import load_config
    from rl_move.robot_state import DEG2RAD
    from rl_move.sim.joint_task import q_rad_to_action
    from rl_move.sim.servo_model import SimServoParams
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    from rl_move.sim.probe_walk_income import WALK_PLANT
    from hexapod_core.tripod_gait import TripodGait

    cfg = load_config()
    stack = dict(CFG)
    if extra:
        stack.update(extra)
    for key, val in stack.items():
        sec, leaf = key.split(".", 1)
        cfg.setdefault(sec, {})[leaf] = val
    env = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(None), randomize=False,
        dr_scale=0.0, episode_seconds=SECONDS, seed=seed, cfg=cfg)
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 1.0 if m == "walk" else 0.0)
    env.reset()
    # Force the exact combined cell on every tick: fixed body/world
    # linear command + fixed commanded yaw rate (the eval_cmd_suite
    # arc-left cell).  Overwrites the drawn command arrays in place.
    tr = env._goal_traj
    tr.vx[:] = VX
    tr.vy[:] = 0.0
    tr.wz[:] = WZ
    gait = TripodGait(vx=0.0, lift=0.025)
    gait.sync_plant_stance(*WALK_PLANT)
    gait.reset_phase()
    tot, t_gait = 0.0, 0.0
    sums: dict = {}
    means: dict = {}
    xy, cmd, yaw_h, wz_h = [], [], [], []
    while True:
        g = env._current_goal()
        vxr, vyr = float(g.vx_ref), float(g.vy_ref)
        wzr = float(getattr(g, "wz_ref", 0.0))
        R = env.data.xmat[env._chassis_bid].reshape(3, 3)
        yaw = math.atan2(R[1, 0], R[0, 0])
        if drive == "arc":
            gv, om = (vxr, vyr), wzr
        elif drive == "noturn":
            gv, om = (vxr, vyr), 0.0
        elif drive == "crab":
            # rotate the (world-interpreted) command into the body
            # frame so the WORLD course stays on the fixed chord while
            # the body still yaws at wz_ref
            gv = (vxr * math.cos(-yaw) - vyr * math.sin(-yaw),
                  vxr * math.sin(-yaw) + vyr * math.cos(-yaw))
            om = wzr
        else:
            raise ValueError(drive)
        t_gait += env.dt
        gait.set_velocity(vx=gv[0], vy=gv[1], omega=om)
        act = q_rad_to_action(
            np.asarray(gait.desired_deg(t_gait)) * DEG2RAD)
        bxy = env.data.xpos[env._chassis_bid, :2]
        xy.append((float(bxy[0]), float(bxy[1])))
        cmd.append((vxr, vyr))
        yaw_h.append(yaw)
        wz_h.append(wzr)
        _o, r, term, trunc, info = env.step(act)
        tot += float(r)
        for k, v in info.items():
            if isinstance(v, (int, float)) and k.startswith("reward_"):
                sums[k] = sums.get(k, 0.0) + float(v)
        for k in ("walk_course_income_angle_f",
                  "walk_course_income_speed_f", "walk_sway_rms_mm"):
            if k in info:
                means.setdefault(k, []).append(float(info[k]))
        if term or trunc:
            break
    dt = env.dt
    env.close()
    return dict(total=tot, sums=sums,
                means={k: float(np.mean(v)) for k, v in means.items()},
                xy=np.array(xy), cmd=np.array(cmd),
                yaw=np.array(yaw_h), wz=np.array(wz_h), dt=dt)


def corrected_course_err(xy, cmd, yaw, wz, dt, window_s=1.0,
                         stride_s=0.1, motion_floor_m_s=0.01):
    """windowed course err with the commanded-yaw-rotated reference:
    ref displacement for window [i0,i1] integrates
    R(yaw_body(i0) + integral(wz_ref)) @ (vx_ref, vy_ref) dt."""
    n = max(int(round(window_s / dt)), 1)
    stride = max(int(round(stride_s / dt)), 1)
    theta_ref = np.concatenate([[0.0], np.cumsum(wz * dt)])
    # per-tick command rotated by the wz integral (offset applied per
    # window below via a constant rotation)
    ct = np.cos(theta_ref[:-1]); st = np.sin(theta_ref[:-1])
    rot = np.stack([cmd[:, 0] * ct - cmd[:, 1] * st,
                    cmd[:, 0] * st + cmd[:, 1] * ct], axis=1)
    cum_rot = np.vstack([[0.0, 0.0], np.cumsum(rot * dt, axis=0)])
    errs = []
    for i0 in range(0, len(xy) - n, stride):
        i1 = i0 + n
        d_ref = cum_rot[i1] - cum_rot[i0]
        off = yaw[i0] - theta_ref[i0]
        c, s = math.cos(off), math.sin(off)
        d_ref = np.array([d_ref[0] * c - d_ref[1] * s,
                          d_ref[0] * s + d_ref[1] * c])
        d_ref_n = float(np.hypot(*d_ref))
        if d_ref_n < 1e-9:
            continue
        d_xy = xy[i1] - xy[i0]
        d_n = float(np.hypot(*d_xy))
        if d_n < motion_floor_m_s * (n * dt):
            continue
        cosv = float(d_xy @ d_ref) / (d_n * d_ref_n)
        errs.append(math.degrees(math.acos(max(-1.0, min(1.0, cosv)))))
    return errs


def main():
    import argparse
    from rl_move.sim.eval_checkpoint import windowed_course_stats
    ap = argparse.ArgumentParser()
    ap.add_argument("--extra", action="append", default=[],
                    help="extra cfg overrides key=val")
    args = ap.parse_args()
    extra = {}
    for kv in args.extra:
        k, v = kv.split("=", 1)
        extra[k] = float(v)
    print(f"combined cell: vx={VX} m/s, wz={WZ} rad/s, {SECONDS}s, "
          f"stack=cw-robotwalk-turns-20260906 (+{extra or 'none'})")
    for drive in ("arc", "noturn", "crab"):
        r = _rollout(drive, extra)
        st = windowed_course_stats(r["xy"], r["cmd"], r["dt"], 1.0)
        legacy = (float(np.median(st["err_deg"]))
                  if st["err_deg"] else float("nan"))
        corr = corrected_course_err(
            r["xy"], r["cmd"], r["yaw"], r["wz"], r["dt"])
        corr_med = float(np.median(corr)) if corr else float("nan")
        yaw_net = math.degrees(r["yaw"][-1] - r["yaw"][0])
        print(f"\n== {drive}  total_reward={r['total']:.1f}  "
              f"net_body_yaw={yaw_net:+.1f} deg "
              f"(cmd {math.degrees(WZ * SECONDS):+.1f})")
        for k in sorted(r["sums"]):
            print(f"   {k:38s} {r['sums'][k]:+10.1f}")
        for k in sorted(r["means"]):
            print(f"   mean {k:33s} {r['means'][k]:10.3f}")
        print(f"   EVAL course_err_1s_med LEGACY(chord) {legacy:8.2f} deg"
              f"   CORRECTED(yaw-rotated) {corr_med:8.2f} deg")


if __name__ == "__main__":
    main()
