#!/usr/bin/env python3
"""Scripted-gait stance A/B in the CPU twin: does the actuator model decide
whether the sim prefers the tucked or the extended plant?

Hardware (hexapod2, 2026-09-26, scripted gait 10 at 2000/80, vx 60 mm/s,
sessions 20260926-1426xx): knee 80 walks 13-15 mm/s with little yaw, knee
100 walks 6-9 mm/s and rocks; the RL sim trains happily at the tucked
20/100 plant and every extended-plant retrain ended flat.  This probe
rolls the same open-loop TripodGait at a chosen plant through real
physics with a chosen servo model (``--servo-params`` json) and the
robot's scripted write profile, and reports the numbers the hardware A/B
reported plus the loaded cmd->q gain/lag per axis (to be compared with the
tape metrics in ~/.hexapod/analysis/servo_profile_fit).

No policy, no reward, no cfg key: read-only diagnostic.

    PYTHONPATH=$PWD python -m rl_move.sim.probe_stance_actuator \
        --hip 20 --knee 80 --servo-params rl_move/sim/sim_model_profilefit_20260926.json \
        --write-speed 2000 --write-acc 80 --hz 20 --vx 0.06 --seconds 10
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import numpy as np


def _xcorr_lag(a, b, dt, max_lag_s=0.6):
    a = a - a.mean()
    b = b - b.mean()
    if a.std() < 1e-9 or b.std() < 1e-9:
        return float("nan"), float("nan")
    n = int(max_lag_s / dt)
    best = (0.0, -2.0)
    for k in range(-n // 4, n + 1):
        x, y = (a[:len(a) - k], b[k:]) if k >= 0 else (a[-k:], b[:k])
        if len(x) < 20:
            continue
        r = float(np.corrcoef(x, y)[0, 1])
        if r > best[1]:
            best = (k * dt, r)
    return best


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hip", type=float, default=20.0)
    ap.add_argument("--knee", type=float, default=100.0,
                    help="robot_abs absolute tibia angle (80 extended, 100 tucked)")
    ap.add_argument("--servo-params", default="",
                    help="sim_model json path ('' = the default sim_model.json, "
                         "'air'/'loaded' as in bus.servo_params)")
    ap.add_argument("--write-speed", type=float, default=2000.0)
    ap.add_argument("--write-acc", type=float, default=80.0)
    ap.add_argument("--vel-from-write-speed", action="store_true",
                    help="legacy sets: lift the json vel_max ceiling to the write speed "
                         "(bus.servo_vel_max_counts_s=write_speed)")
    ap.add_argument("--latency-scale", type=float, default=1.0)
    ap.add_argument("--hz", type=float, default=20.0,
                    help="control/write rate (the robot's scripted gait writes at 20 Hz)")
    ap.add_argument("--vx", type=float, default=0.06)
    ap.add_argument("--gait", type=int, default=10, help="informational; TripodGait stock geometry")
    ap.add_argument("--seconds", type=float, default=10.0)
    ap.add_argument("--settle-s", type=float, default=1.0,
                    help="hold the plant for this long before commanding vx")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--model-source", default="mesh")
    ap.add_argument("--max-delta-q-deg", type=float, default=100.0,
                    help="RL runner slew clamp per tick; the robot's scripted path has none")
    ap.add_argument("--replay-run", default="",
                    help="lab run dir: replay that session's recorded scripted SyncWrite "
                         "stream (goals at their own 20 Hz timing, the tape's write "
                         "profile) instead of the stock TripodGait; --hip/--knee are "
                         "taken from the first walking write")
    ap.add_argument("--bout", type=int, default=0, help="which walking bout of the tape")
    ap.add_argument("--cfg", action="append", default=[],
                    help="cfg override section.key=value (float), e.g. env.foot_friction_slide=0.6")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--label", default="")
    args = ap.parse_args(argv)

    replay = None
    if args.replay_run:
        from pathlib import Path as _P
        from sysid.fit_servo_profile import load_scripted_raw
        raw = load_scripted_raw(_P(args.replay_run))
        bi = raw["bouts"][args.bout]
        # the write before the leg is the lab's standing pose = the plant
        # the robot settled on; the leg's own writes run on their clock
        pre = raw["C"][max(bi[0] - 1, 0)]
        t_rel = raw["t_cmd"][bi] - raw["t_cmd"][bi[0]]
        goals = raw["C"][bi]
        replay = dict(t=t_rel, goals=goals, plant=pre,
                      speed=float(np.median(raw["S"][bi])),
                      acc=float(np.median(raw["A"][bi])),
                      label=raw["labels"][args.bout])
        args.write_speed, args.write_acc = replay["speed"], replay["acc"]
        args.hz = 1.0 / float(np.median(np.diff(t_rel)))
        args.hip, args.knee = float(pre[1]), float(pre[2])
        args.seconds = float(t_rel[-1])
        print(f"replay {args.replay_run} bout {args.bout}: {len(goals)} writes, "
              f"{args.seconds:.1f} s at {args.hz:.1f} Hz, profile {args.write_speed:g}/"
              f"{args.write_acc:g}, first write hip {args.hip:.1f} knee {args.knee:.1f}",
              file=sys.stderr)

    os.environ["HEXAPOD_MODEL_SOURCE"] = args.model_source
    os.environ["HEXAPOD_CONTROL_HZ"] = "%g" % args.hz

    from rl_move.config import load_config
    from rl_move.robot_state import DEG2RAD
    from rl_move.sim.joint_task import q_rad_to_action
    from rl_move.sim.servo_model import N_JOINTS, SimServoParams
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    from hexapod_core.tripod_gait import TripodGait

    cfg = load_config()
    for kv in args.cfg:
        key, val = kv.split("=", 1)
        node = cfg
        parts = key.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = float(val)
    cfg.setdefault("safety", {})["max_delta_q_deg"] = float(args.max_delta_q_deg)
    bus = cfg.setdefault("bus", {})
    bus["write_speed"] = float(args.write_speed)
    bus["write_acc"] = float(args.write_acc)
    if args.servo_params:
        bus["servo_params"] = args.servo_params
    if args.vel_from_write_speed:
        bus["servo_vel_max_counts_s"] = "write_speed"
    params = SimServoParams.from_cfg(cfg)
    if args.latency_scale != 1.0:
        for ax in params.axes.values():
            ax.latency_ms *= args.latency_scale
        params.source += f"+latency_scale={args.latency_scale:g}"

    plant = (np.asarray(replay["plant"], dtype=float) if replay is not None
             else np.array([0.0, args.hip, args.knee] * 6, dtype=float))
    env = SimHexapodJointWalkEnv(
        params=params, randomize=False, dr_scale=0.0,
        episode_seconds=args.seconds + args.settle_s + 2.0,
        seed=args.seed, cfg=cfg, plant_deg=plant)
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk", "quadwalk", "recover"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 1.0 if m == "walk" else 0.0)
    env.reset()

    gait = TripodGait(vx=0.0, lift=0.025)
    gait.sync_plant_stance(args.hip, args.knee)
    gait.reset_phase()

    dt = env.dt
    n_settle = int(round(args.settle_s / dt))
    n_walk = int(round(args.seconds / dt))
    t_hist, cmd_hist, q_hist, xy_hist, yaw_hist, gyro_hist, cur_hist = ([] for _ in range(7))
    slip_m, touchdowns = 0.0, [0] * 6
    prev_on, prev_xy = [False] * 6, [None] * 6
    fell = False
    t0 = time.time()
    for step in range(n_settle + n_walk):
        t = step * dt
        if replay is not None:
            if step < n_settle:
                des_deg = plant
            else:
                k = int(np.searchsorted(replay["t"], t - n_settle * dt, side="right")) - 1
                des_deg = np.asarray(replay["goals"][max(k, 0)], dtype=float)
        else:
            if step == n_settle:
                gait.set_velocity(vx=args.vx, vy=0.0, omega=0.0)
                gait.reset_phase(t=t)
            des_deg = np.asarray(gait.desired_deg(t))
        act = q_rad_to_action(des_deg * DEG2RAD)
        _obs, _r, term, trunc, _info = env.step(act)
        q_deg = env._mujoco_to_logical_q(env.data.qpos[env._qadr]) / DEG2RAD
        bxy = env.data.xpos[env._chassis_bid, :2].copy()
        R = env.data.xmat[env._chassis_bid].reshape(3, 3)
        yaw = math.atan2(R[1, 0], R[0, 0])
        # free-joint angular velocity (chassis frame) as the body gyro
        gyro = env.data.qvel[3:6].copy() / DEG2RAD
        cur = getattr(env, "_cur_filt", None)
        t_hist.append(t)
        cmd_hist.append(des_deg)
        q_hist.append(q_deg)
        xy_hist.append(bxy)
        yaw_hist.append(yaw)
        gyro_hist.append(gyro)
        cur_hist.append(float(np.sum(cur)) if cur is not None else float("nan"))
        if step >= n_settle:
            for f in range(6):
                adr = env._touch_adr[f]
                on = bool(adr >= 0 and env.data.sensordata[adr] > 0.5)
                xy_world = env.data.xpos[env._pad_bids[f], :2].copy()
                if on and not prev_on[f]:
                    touchdowns[f] += 1
                if on and prev_on[f] and prev_xy[f] is not None:
                    slip_m += float(np.linalg.norm(xy_world - prev_xy[f]))
                prev_xy[f] = xy_world
                prev_on[f] = on
        if term:
            fell = True
            break
    wall = time.time() - t0

    t_hist = np.asarray(t_hist)
    cmd = np.asarray(cmd_hist)
    q = np.asarray(q_hist)
    xy = np.asarray(xy_hist)
    yaw = np.unwrap(np.asarray(yaw_hist))
    gyro = np.asarray(gyro_hist)
    w = slice(n_settle, len(t_hist))
    # walking-window kinematics: displacement along the initial heading
    heading0 = yaw[n_settle]
    d = xy[-1] - xy[n_settle]
    straight = float(d[0] * math.cos(heading0) + d[1] * math.sin(heading0))
    lateral = float(-d[0] * math.sin(heading0) + d[1] * math.cos(heading0))
    dur = float(t_hist[-1] - t_hist[n_settle]) if len(t_hist) > n_settle + 1 else float("nan")
    speed = straight / dur if dur > 0 else float("nan")
    g = gyro[w]
    rate = {"gyro_rms_dps": float(np.sqrt(np.mean(np.sum(g ** 2, axis=1)))),
            "gyro_rms_roll_dps": float(np.sqrt(np.mean(g[:, 0] ** 2))),
            "gyro_rms_pitch_dps": float(np.sqrt(np.mean(g[:, 1] ** 2))),
            "gyro_rms_yaw_dps": float(np.sqrt(np.mean(g[:, 2] ** 2)))}
    # loaded cmd->q gain / lag per axis (median over the 6 legs), 5 ms grid
    track = {}
    tt = np.arange(t_hist[n_settle] + 1.0, t_hist[-1], 0.005)
    for ai, axis in enumerate(("yaw", "hip", "knee")):
        gains, lags, rmses = [], [], []
        for leg in range(6):
            j = 3 * leg + ai
            c = np.interp(tt, t_hist, cmd[:, j])
            m = np.interp(tt, t_hist, q[:, j])
            if c.std() < 0.3:
                continue
            gains.append(m.std() / c.std())
            lags.append(_xcorr_lag(c, m, 0.005)[0] * 1e3)
            rmses.append(float(np.sqrt(np.mean((m - c) ** 2))))
        if gains:
            track[axis] = {"gain": float(np.median(gains)), "lag_ms": float(np.median(lags)),
                           "rmse_deg": float(np.median(rmses))}
    out = {
        "label": args.label, "cfg": args.cfg, "hip": args.hip, "knee": args.knee,
        "replay_run": args.replay_run or None,
        "replay_leg": replay["label"] if replay is not None else None,
        "servo_params": params.source, "write_speed": args.write_speed,
        "write_acc": args.write_acc, "hz": args.hz, "vx_mm_s": args.vx * 1e3,
        "seconds": dur, "fell": fell, "wall_s": round(wall, 1),
        "straight_mm": round(straight * 1e3, 1),
        "straight_speed_mm_s": round(speed * 1e3, 2),
        "speed_ratio": round(speed / args.vx, 3) if args.vx else None,
        "lateral_drift_mm": round(lateral * 1e3, 1),
        "heading_change_deg": round(float((yaw[-1] - yaw[n_settle]) / DEG2RAD), 1),
        **{k: round(v, 2) for k, v in rate.items()},
        "slip_mm": round(slip_m * 1e3, 1),
        "touchdowns": touchdowns,
        "mean_current_a": (round(float(np.nanmean(cur_hist[n_settle:])), 3)
                           if np.isfinite(np.nanmean(cur_hist[n_settle:])) else None),
        "settle_current_a": (round(float(np.nanmean(cur_hist[:n_settle])), 3)
                             if n_settle and np.isfinite(np.nanmean(cur_hist[:n_settle])) else None),
        "tracking": track,
    }
    print(json.dumps(out, indent=1))
    if args.json_out:
        with open(args.json_out, "a") as fh:
            fh.write(json.dumps(out) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
