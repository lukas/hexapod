"""Measure the scripted tripod teacher's per-tick direction-error floor.

WHAT THIS PROBE ANSWERS (standwalk coursedisp-c1 DIG-IN, 2026-08-29):
is the eval harness's `direction_err_mean_deg` headline — a PER-TICK
INSTANTANEOUS velocity-angle statistic — achievable at low values by a
KNOWN-GOOD course-follower on the CURRENT model family/cadence, or is
it floored by honest intra-stride sway?  The joystick track measured a
~35 deg tick-level floor on the PRIMITIVE family at 25 Hz and its DONE
gate judges deltas against that floor (CURRENT_TRUTHS).  No one has
measured the floor on the MESH family at 100 Hz, which is what every
standwalk-track policy is judged on.

Method: roll the hardware-proven scripted TripodGait (robot-absolute
joints, same as build_motion_library)
through real physics at a fixed forward command, and report over the
commanded ticks:
  - per-tick instantaneous direction error (exact harness definition:
    walk_task.walk_direction_error_deg on _body_vel_xy vs command);
  - trailing-window NET-DISPLACEMENT direction error (the
    k_walk_course_disp mechanism's own quantity, default 1.5 s);
  - whole-rollout net path direction error + mean speed + fall flag.

09-05 follow-up (standwalk, closing the mlcontprice8 literal-DONE-gate
FALL): every prior floor read (13.5 deg mean) used a FIXED heading for
the whole rollout -- the real DONE-gate session redraws (speed,
heading) every `goal.walk_cmd_resample_s` (~3 s, jittered) and blends
to it over `walk_cmd_blend_s` (~1 s), per `walk_task._sample_mode_seq`.
A policy plateauing at 42-45 deg tick dir_err regardless of ~20 tested
reward/architecture levers could mean the 40 deg cap was calibrated
against an easier (never-reorients) floor than the task actually
demands. `--resample-s`/`--resample-jitter`/`--heading-max-deg`/
`--blend-s` (all default 0/off = IDENTICAL prior behavior, bit-exact)
add the SAME periodic heading redraw to the teacher's own commanded
(vx, vy), still open-loop TripodGait, no policy involved -- isolates
how much of the achieved dir_err floor is just "honest transient lag
after every command flip" vs a policy competence gap. Known
simplification (documented, not modeled): stop segments
(`walk_stop_frac`) and turn-in-place segments (`walk_turn_in_place_
frac`) are not reproduced, only cruise-with-periodic-heading-change.

Read-only diagnostic: no shared behavior changes, no cfg keys.
Usage (controller-ok, single env, ~1-2 min per rollout):
  uv run python -m rl_move.sim.probe_dir_floor \
      --model-source mesh --hz 100 --vx 0.08 --seconds 60
  # heading-resample floor (matches the DONE-gate session's own
  # command dynamic instead of a single fixed heading):
  uv run python -m rl_move.sim.probe_dir_floor \
      --model-source mesh --hz 100 --vx 0.08 --seconds 60 \
      --resample-s 3.0 --resample-jitter 0.2 --heading-max-deg 180 \
      --blend-s 1.0
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "linux_control", ROOT / "linux_control" / "urt2_setup"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-source", default="mesh",
                    choices=["mesh", "mesh_mjx", "primitive"])
    ap.add_argument("--hz", type=float, default=100.0)
    ap.add_argument("--max-delta-q-deg", type=float, default=None,
                    help="slew clamp per tick (default: 37.5deg/s / hz, "
                         "the rate-invariant physical contract)")
    ap.add_argument("--vx", type=float, default=0.08)
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--resample-s", type=float, default=0.0,
                    help="periodic heading redraw interval, seconds "
                         "(0 = off, legacy fixed-heading floor, "
                         "bit-exact prior behavior)")
    ap.add_argument("--resample-jitter", type=float, default=0.2,
                    help="each segment length ~ U[rs*(1-j), rs*(1+j)], "
                         "matching goal.walk_cmd_resample_jitter")
    ap.add_argument("--heading-max-deg", type=float, default=180.0,
                    help="new heading drawn ~ U[-max, max] degrees "
                         "every resample (matches goal.walk_heading_"
                         "max_rad=pi on the standwalk cap29 lineage)")
    ap.add_argument("--blend-s", type=float, default=1.0,
                    help="linear ramp duration from the old commanded "
                         "(vx,vy) to the new one, matching goal.walk_"
                         "cmd_blend_s")
    ap.add_argument("--window-s", type=float, default=1.5)
    ap.add_argument("--min-speed", type=float, default=0.005,
                    help="dir-err validity threshold m/s (5e-3 = the "
                         "joint_walk env's own inline emitter)")
    ap.add_argument("--envelope-windows", default="0.5,0.75,1.0,2.0",
                    help="comma list of window lengths (s) for the "
                         "teacher-envelope calibration block: windowed "
                         "course error / |disp-cmd| vector error / "
                         "perpendicular sway RMS via "
                         "eval_checkpoint.windowed_course_stats "
                         "(reward-design directive "
                         "fb_20260829T142239_63c818 item 3: charge only "
                         "EXCESS sway beyond the clean teacher's own "
                         "envelope, so the teacher's numbers ARE the "
                         "allowance)")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    # Same override pattern the pinned test suite uses; must be set
    # before the env/config imports below resolve anything.
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

    env = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(None), randomize=False,
        dr_scale=0.0, episode_seconds=args.seconds + 2.0,
        seed=args.seed, cfg=cfg)
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 1.0 if m == "walk" else 0.0)
    env.reset()

    gait = TripodGait(vx=0.0, lift=0.025)
    gait.sync_plant_stance(*WALK_PLANT)
    gait.set_velocity(vx=args.vx, vy=0.0, omega=0.0)
    gait.reset_phase()

    dt = env.dt
    n = int(round(args.seconds / dt))
    win_ticks = max(int(round(args.window_s / dt)), 1)
    hist: deque = deque(maxlen=win_ticks + 1)

    # Heading-resample state (off by default: cmd_vx/cmd_vy stay pinned
    # to args.vx/0.0 for the whole rollout, identical to the legacy
    # fixed-heading floor). A SEPARATE rng stream (seed offset) so the
    # legacy fixed-heading call sites' rng usage (none, currently) can
    # never be perturbed by turning this on. The transition itself
    # reuses TripodGait's OWN internal tau=0.15s command low-pass
    # (`_smoothed_command`, unconditional, same path a live velocity
    # change always takes) instead of a second hand-rolled blend --
    # `--blend-s` is accepted for CLI/doc symmetry with `goal.walk_
    # cmd_blend_s` but only used to log intent, not to double-smooth.
    resample_rng = np.random.default_rng(args.seed + 1000)
    heading_max_rad = math.radians(args.heading_max_deg)
    cmd_vx, cmd_vy = args.vx, 0.0

    def _draw_next_resample_t(t_now: float) -> float:
        j = args.resample_jitter
        span = args.resample_s * (1.0 + resample_rng.uniform(-j, j))
        return t_now + max(span, 1e-3)

    next_resample_t = (_draw_next_resample_t(0.0)
                        if args.resample_s > 0.0 else float("inf"))
    n_resamples = 0

    tick_errs, win_errs, speeds = [], [], []
    all_xy, all_cmd = [], []       # full tick streams for the envelope
    n_cmd, n_valid = 0, 0
    fell = False
    xy0 = env.data.xpos[env._chassis_bid, :2].copy()
    # Six-leg gait-validity + loaded-slip telemetry: a floor measured
    # on a gliding/dragging rollout would be unrepresentative.
    prev_on = [False] * 6
    prev_xy = [None] * 6
    touchdowns = [0] * 6
    slip_m = 0.0
    for step in range(n):
        t = step * dt
        if t >= next_resample_t:
            heading = resample_rng.uniform(-heading_max_rad, heading_max_rad)
            cmd_vx = args.vx * math.cos(heading)
            cmd_vy = args.vx * math.sin(heading)
            gait.set_velocity(vx=cmd_vx, vy=cmd_vy, omega=0.0)
            n_resamples += 1
            next_resample_t = _draw_next_resample_t(t)
        act = q_rad_to_action(np.asarray(gait.desired_deg(t)) * DEG2RAD)
        _obs, _r, term, trunc, _info = env.step(act)
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
        v = env._body_vel_xy()
        n_cmd += 1
        err = walk_direction_error_deg(
            float(v[0]), float(v[1]), cmd_vx, cmd_vy,
            min_speed_m_s=args.min_speed)
        if err is not None:
            n_valid += 1
            tick_errs.append(err)
        speeds.append(float(np.hypot(*v)))
        bxy = env.data.xpos[env._chassis_bid, :2]
        all_xy.append((float(bxy[0]), float(bxy[1])))
        all_cmd.append((cmd_vx, cmd_vy))
        hist.append((float(bxy[0]), float(bxy[1])))
        if len(hist) == hist.maxlen:
            dx = hist[-1][0] - hist[0][0]
            dy = hist[-1][1] - hist[0][1]
            d = math.hypot(dx, dy)
            if d / args.window_s >= 0.02:  # mechanism's own min speed
                # Project net window displacement onto the CURRENT
                # commanded direction (world +x only coincides with
                # the command when resampling is off, the legacy
                # heading_max_rad=0 forward-only case).
                cmd_ang = math.atan2(cmd_vy, cmd_vx)
                disp_ang = math.atan2(dy, dx)
                da = abs(disp_ang - cmd_ang)
                if da > math.pi:
                    da = 2 * math.pi - da
                win_errs.append(math.degrees(da))
        if term:
            fell = True
            break
        if trunc:
            break

    xy1 = env.data.xpos[env._chassis_bid, :2].copy()
    net = xy1 - xy0
    net_err = (math.degrees(math.atan2(net[1], net[0]))
               if np.hypot(*net) > 1e-6 else float("nan"))
    out = {
        "model_source": args.model_source, "hz": args.hz,
        "max_delta_q_deg": max_dq, "vx_cmd": args.vx,
        "resample_s": args.resample_s,
        "resample_jitter": args.resample_jitter,
        "heading_max_deg": args.heading_max_deg,
        "blend_s_requested": args.blend_s,
        "n_resamples": n_resamples,
        "seconds": args.seconds, "seed": args.seed, "fell": fell,
        "ticks": n_cmd, "dir_valid_frac": round(n_valid / max(n_cmd, 1), 4),
        "tick_dir_err_mean_deg": round(float(np.mean(tick_errs)), 2)
            if tick_errs else None,
        "tick_dir_err_med_deg": round(float(np.median(tick_errs)), 2)
            if tick_errs else None,
        "tick_dir_err_p90_deg": round(float(np.percentile(tick_errs, 90)), 2)
            if tick_errs else None,
        "win_dir_err_mean_deg": round(float(np.mean(win_errs)), 2)
            if win_errs else None,
        "win_dir_err_med_deg": round(float(np.median(win_errs)), 2)
            if win_errs else None,
        "window_s": args.window_s,
        "net_path_dir_err_deg": round(abs(net_err), 2),
        "net_disp_m": round(float(np.hypot(*net)), 4),
        "mean_speed_m_s": round(float(np.mean(speeds)), 4),
        "touchdowns_per_leg": touchdowns,
        "slip_per_m": round(slip_m / max(float(np.hypot(*net)), 1e-6), 3),
    }
    # Teacher-envelope calibration block: the exact quantities the
    # windowed reward terms (k_walk_course_income / k_walk_excess_sway)
    # and the harness's windowed course metrics consume. Uses the
    # SHARED implementation so calibration and scoring can never drift.
    from rl_move.sim.eval_checkpoint import windowed_course_stats

    def _pct(a, q):
        return round(float(np.percentile(a, q)), 4) if len(a) else None

    env_windows = {}
    for w_s in [float(x) for x in args.envelope_windows.split(",") if x]:
        st = windowed_course_stats(all_xy, all_cmd, dt, w_s,
                                   with_sway=True)
        env_windows["%g" % w_s] = {
            "n_cmd_windows": st["n_cmd_windows"],
            "n_motion_valid": st["n_motion_valid"],
            "course_err_deg": {
                "mean": round(float(np.mean(st["err_deg"])), 2)
                    if st["err_deg"] else None,
                "med": _pct(st["err_deg"], 50),
                "p90": _pct(st["err_deg"], 90),
                "p95": _pct(st["err_deg"], 95)},
            "vec_err_mm": {
                "mean": round(1e3 * float(np.mean(st["vec_err_m"])), 2)
                    if st["vec_err_m"] else None,
                "p90": _pct(1e3 * np.asarray(st["vec_err_m"]), 90),
                "p95": _pct(1e3 * np.asarray(st["vec_err_m"]), 95)},
            "speed_ratio": {
                "mean": round(float(np.mean(st["speed_ratio"])), 3)
                    if st["speed_ratio"] else None,
                "med": _pct(st["speed_ratio"], 50),
                "p10": _pct(st["speed_ratio"], 10)},
            "sway_rms_mm": {
                "mean": round(1e3 * float(np.mean(st["sway_rms_m"])), 2)
                    if st["sway_rms_m"] else None,
                "p90": _pct(1e3 * np.asarray(st["sway_rms_m"]), 90),
                "p95": _pct(1e3 * np.asarray(st["sway_rms_m"]), 95)},
        }
    out["envelope_windows"] = env_windows
    env.close()
    print(json.dumps(out, indent=1))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
