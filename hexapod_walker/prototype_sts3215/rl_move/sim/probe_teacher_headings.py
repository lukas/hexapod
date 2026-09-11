"""Sanity-check the scripted tripod teacher at EVERY heading on the
current contract (mesh family, 100 Hz, 0.375 deg/tick slew).

WHAT THIS PROBE ANSWERS (operator order fb_20260829T144550_c921fa,
item 2, 2026-08-29): before anchoring a from-scratch all-heading
walker to the scripted TripodGait teacher, verify the teacher itself
actually walks laterally / diagonally / in reverse under the SAME
contract the student trains on — not just forward (probe_dir_floor
measured forward only). The robot is near 6-fold symmetric; if the
open-loop teacher follows all headings cleanly, weak sideways walking
in a trained policy is a training/reward failure, not a robot limit.

Method: per commanded heading, roll TripodGait(vx=s*cos h, vy=s*sin h)
through real physics (same explicit MuJoCo boundary as
build_motion_library / probe_dir_floor) and report net-path course
error vs the command, completion (along-command speed / commanded
speed), trailing-window course error, tick-level direction error,
loaded-foot slip/m, per-leg touchdowns, and falls.

Read-only diagnostic: no shared behavior changes, no cfg keys.
Usage (controller-ok, single env, ~3-5 min for the 8-heading panel):
  uv run python -m rl_move.sim.probe_teacher_headings \
      --model-source mesh --hz 100 --speed 0.08 --seconds 16
"""
from __future__ import annotations

import argparse
import json
import math
import os
from collections import deque
from pathlib import Path

import numpy as np


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-source", default="mesh",
                    choices=["mesh", "mesh_mjx", "primitive"])
    ap.add_argument("--hz", type=float, default=100.0)
    ap.add_argument("--max-delta-q-deg", type=float, default=None)
    ap.add_argument("--speed", type=float, default=0.08)
    ap.add_argument("--seconds", type=float, default=16.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--window-s", type=float, default=1.0)
    ap.add_argument("--min-speed", type=float, default=0.005)
    ap.add_argument("--headings-deg",
                    default="0,45,-45,90,-90,135,-135,180",
                    help="comma list of commanded headings (deg, 0 = "
                         "forward, +90 = crab left, 180 = reverse) — "
                         "the balanced 8-set the all-heading walker "
                         "curriculum trains on")
    # Speed-track feasibility knobs (2026-09-11, speed track step 0b):
    # sweep the scripted teacher's OWN gait geometry — stride length,
    # swing lift, cycle period — under the conservative transfer slew,
    # to find whether any open-loop setting moves the BODY faster
    # before spending GPU on it. Defaults 1.0 = bit-identical to the
    # pre-09-11 probe (plain TripodGait). Purely additive; the extra
    # report fields (achieved speed, slew saturation, roll/pitch
    # motion) are appended keys on the same rows.
    ap.add_argument("--period-scale", type=float, default=1.0,
                    help="TripodGait period_scale (cycle time x this; "
                         "stride grows with period at fixed speed)")
    ap.add_argument("--lift-scale", type=float, default=1.0,
                    help="TripodGait lift_scale (swing apex x this)")
    ap.add_argument("--stride-scale", type=float, default=1.0,
                    help="TripodGait stride_scale (foot stroke x this "
                         "at the same commanded speed/cadence)")
    ap.add_argument("--stance-radius-scale", type=float, default=1.0,
                    help="TripodGait stance_radius_scale (home foot "
                         "radial distance x this, clipped to "
                         "[0.55, 1.05] same as the turn-track knob) "
                         "-- untested for pure-forward speed before "
                         "2026-09-11: a wider stance increases the "
                         "moment arm the yaw joint's atan2 conversion "
                         "uses, so the SAME commanded yaw angle (same "
                         "slew budget) maps to a larger tangential foot "
                         "excursion. Only plumbed for turn authority "
                         "so far (probe_turn_authority.py); this wires "
                         "it into the same forward-heading harness step "
                         "0b/0c already used for period/lift/stride.")
    ap.add_argument("--write-speed", type=float, default=None,
                    help="optional bus.write_speed (counts/s) for the "
                         "actuator-envelope ladder (speed track, "
                         "2026-09-11): also sets "
                         "bus.servo_vel_max_counts_s='write_speed' and "
                         "re-resolves SimServoParams from cfg so the "
                         "profile velocity ceiling actually follows the "
                         "dose (the fitted sets carry the ~350 counts/s "
                         "sys-ID ceiling; raising write_speed alone is a "
                         "silent no-op — same rationale as the 08-19 "
                         "servo_vel_max_counts_s override). Default "
                         "None = bit-identical legacy behavior "
                         "(SimServoParams.from_cfg(None), stock 400 "
                         "counts/s write profile).")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    os.environ["HEXAPOD_MODEL_SOURCE"] = args.model_source
    os.environ["HEXAPOD_CONTROL_HZ"] = ("%g" % args.hz)

    from rl_move.config import load_config
    from rl_move.robot_state import DEG2RAD
    from rl_move.sim.joint_task import q_rad_to_action
    from rl_move.sim.servo_model import SimServoParams
    from rl_move.sim.walk_task import (
        SimHexapodJointWalkEnv, walk_direction_error_deg)
    from rl_move.sim.probe_walk_income import WALK_PLANT
    from hexapod_core.tripod_gait import TripodGait

    max_dq = (args.max_delta_q_deg if args.max_delta_q_deg is not None
              else 37.5 / args.hz)
    cfg = load_config()
    cfg.setdefault("safety", {})["max_delta_q_deg"] = float(max_dq)
    if args.write_speed is not None:
        if not args.write_speed > 0:
            raise SystemExit("--write-speed must be > 0 (counts/s)")
        cfg.setdefault("bus", {})["write_speed"] = float(args.write_speed)
        # Mirror the ceiling onto the profile (fail-closed override,
        # servo_model.SimServoParams.from_cfg) so the dose is real.
        cfg["bus"]["servo_vel_max_counts_s"] = "write_speed"
    _params = (SimServoParams.from_cfg(cfg)
               if args.write_speed is not None
               else SimServoParams.from_cfg(None))

    rows = []
    for h_deg in [float(x) for x in args.headings_deg.split(",") if x]:
        h = math.radians(h_deg)
        vx_c = args.speed * math.cos(h)
        vy_c = args.speed * math.sin(h)
        env = SimHexapodJointWalkEnv(
            params=_params, randomize=False,
            dr_scale=0.0, episode_seconds=args.seconds + 2.0,
            seed=args.seed, cfg=cfg)
        gen = env._goal_gen
        for m in ("hold", "lean", "track", "unload", "raise", "rise",
                  "lower", "quad", "walk"):
            if hasattr(gen, f"p_{m}"):
                setattr(gen, f"p_{m}", 1.0 if m == "walk" else 0.0)
        env.reset()
        gait = TripodGait(vx=0.0, lift=0.025,
                          period_scale=args.period_scale,
                          lift_scale=args.lift_scale,
                          stride_scale=args.stride_scale,
                          stance_radius_scale=args.stance_radius_scale)
        gait.sync_plant_stance(*WALK_PLANT)
        gait.set_velocity(vx=vx_c, vy=vy_c, omega=0.0)
        gait.reset_phase()

        dt = env.dt
        n = int(round(args.seconds / dt))
        win_ticks = max(int(round(args.window_s / dt)), 1)
        hist: deque = deque(maxlen=win_ticks + 1)
        tick_errs, win_errs, along = [], [], []
        cmd_hist, rolls, pitches = [], [], []
        fell = False
        xy0 = env.data.xpos[env._chassis_bid, :2].copy()
        prev_on = [False] * 6
        prev_xy = [None] * 6
        touchdowns = [0] * 6
        slip_m = 0.0
        u = np.array([math.cos(h), math.sin(h)])
        for step in range(n):
            t = step * dt
            act = q_rad_to_action(
                np.asarray(gait.desired_deg(t)) * DEG2RAD)
            _obs, _r, term, trunc, _info = env.step(act)
            for f in range(6):
                adr = env._touch_adr[f]
                on = bool(adr >= 0 and env.data.sensordata[adr] > 0.5)
                xy_w = env.data.xpos[env._pad_bids[f], :2].copy()
                if on and not prev_on[f]:
                    touchdowns[f] += 1
                if on and prev_on[f] and prev_xy[f] is not None:
                    slip_m += float(np.linalg.norm(xy_w - prev_xy[f]))
                prev_xy[f] = xy_w
                prev_on[f] = on
            st = env._state
            if st.commanded_position is not None:
                cmd_hist.append(
                    np.asarray(st.commanded_position, dtype=np.float64)
                    .copy())
            rolls.append(abs(float(st.imu_roll)))
            pitches.append(abs(float(st.imu_pitch)))
            v = env._body_vel_xy()
            err = walk_direction_error_deg(
                float(v[0]), float(v[1]), vx_c, vy_c,
                min_speed_m_s=args.min_speed)
            if err is not None:
                tick_errs.append(err)
            along.append(float(np.dot([float(v[0]), float(v[1])], u)))
            bxy = env.data.xpos[env._chassis_bid, :2]
            hist.append((float(bxy[0]), float(bxy[1])))
            if len(hist) == hist.maxlen:
                dx = hist[-1][0] - hist[0][0]
                dy = hist[-1][1] - hist[0][1]
                d = math.hypot(dx, dy)
                if d / args.window_s >= 0.02:
                    win_errs.append(math.degrees(math.acos(max(-1.0, min(
                        1.0, (dx * u[0] + dy * u[1]) / d)))))
            if term:
                fell = True
                break
            if trunc:
                break
        xy1 = env.data.xpos[env._chassis_bid, :2].copy()
        net = xy1 - xy0
        net_d = float(np.hypot(*net))
        net_err = (math.degrees(math.acos(max(-1.0, min(
            1.0, float(np.dot(net, u)) / net_d))))
            if net_d > 1e-6 else float("nan"))
        env.close()
        elapsed_s = (step + 1) * dt
        # Achieved body speed = displacement / elapsed time (the speed
        # track's only admissible speed number): along-command signed,
        # plus net-path magnitude.
        ach_along = float(np.dot(net, u)) / max(elapsed_s, 1e-9)
        # Actuator-limit proxy: dwell at >=98% of the SafetyLayer slew
        # cap on the post-safety commanded targets (same definition as
        # eval_checkpoint._smoothness_fields).
        slew_sat = None
        cmd_rate_p95 = None
        if len(cmd_hist) >= 3:
            cmd_deg = np.degrees(np.asarray(cmd_hist))
            d1 = np.abs(np.diff(cmd_deg, axis=0)).max(axis=1)
            slew_sat = round(float((d1 >= 0.98 * max_dq).mean()), 3)
            cmd_rate_p95 = round(float(np.percentile(d1, 95)) / dt, 2)
        rows.append({
            "heading_deg": h_deg, "fell": fell,
            "elapsed_s": round(elapsed_s, 2),
            "achieved_speed_m_s": round(ach_along, 4),
            "achieved_speed_net_m_s": round(
                net_d / max(elapsed_s, 1e-9), 4),
            "slew_sat_frac": slew_sat,
            "cmd_rate_p95_deg_s": cmd_rate_p95,
            "roll_mean_abs_deg": round(
                math.degrees(float(np.mean(rolls))), 2) if rolls else None,
            "pitch_mean_abs_deg": round(
                math.degrees(float(np.mean(pitches))), 2)
                if pitches else None,
            "net_course_err_deg": round(net_err, 2),
            "net_disp_m": round(net_d, 4),
            "completion": round(float(np.mean(along)) / args.speed, 3),
            "win_course_err_med_deg": round(
                float(np.median(win_errs)), 2) if win_errs else None,
            "win_course_err_p95_deg": round(
                float(np.percentile(win_errs, 95)), 2)
                if win_errs else None,
            "tick_dir_err_med_deg": round(
                float(np.median(tick_errs)), 2) if tick_errs else None,
            "slip_per_m": round(slip_m / max(net_d, 1e-6), 3),
            "touchdowns_per_leg": touchdowns,
        })
        print(json.dumps(rows[-1]), flush=True)

    out = {"model_source": args.model_source, "hz": args.hz,
           "max_delta_q_deg": max_dq, "speed_cmd": args.speed,
           "write_speed_counts_s": args.write_speed,
           "seconds": args.seconds, "seed": args.seed,
           "window_s": args.window_s, "rows": rows}
    print(json.dumps(out, indent=1))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
