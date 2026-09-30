"""Joystick-DRIVEN demo of the `rl_only` role composition (walkcurr
Next item 2, 2026-09-30): renders a viewable mp4 of the SAME two
frozen checkpoints `eval_walk_turn_compose.py` already validated
(forward-walk specialist `bundle_rlonly_v2` + stationary-heading-hold
turn specialist `acq5-seedsweep`), but driven by an ordered JOYSTICK
COMMAND timeline (vx, vy, wz per segment, exactly the (forward,
lateral, yaw-rate) triple a real joystick/gamepad reports -- the same
convention `drive_video.py`'s scripts use) instead of that tool's
fixed forward-then-turn cycle grammar.

THE GAP THIS CLOSES (RL_GOALS.md's simulation deliverable: "Lukas must
be able to steer it interactively... demonstrate command changes,
turns, starts, stops and restarts"): `eval_walk_turn_compose.py` is
scripted SEGMENTS only (one fixed alternation, no mp4). This module
adds (a) a joystick-shaped command timeline, one role-composition
video render pipeline can be pointed at multiple named scripts, and
(b) an mp4, not just a 1 fps contact-sheet strip. It is NOT a new
training run: same two frozen checkpoints, zero GPU spend, CPU-only
MuJoCo -- role-selection/state-capture plumbing per RL_GOALS.md's
allowed composition category.

ROLE-SWITCH RULE (pure function `resolve_roles`, testable without
mujoco): a joystick segment with |wz| <= WZ_EPS routes through the
WALK role (heading/speed derived from vx,vy via `heading_to_vxvy`'s
own inverse); a segment with |wz| > WZ_EPS routes through the TURN
role, whose trained contract is a STATIONARY heading-hold target, not
a continuous rate -- so the commanded yaw RATE is integrated over the
segment's own duration into one target OFFSET
(`degrees(wz * duration_s)`), matching how a human holding a joystick
yaw axis for N seconds means "turn by about wz*N radians". If vx/vy
is ALSO nonzero on a turn segment, `curve_speed=hypot(vx,vy)` is
passed through to the turn checkpoint exactly as
`eval_walk_turn_compose.py --curve-speed` already validated (OOD
probe on the frozen turn specialist, zero-fall in that tool's own
composed session read) -- no new mechanism, this reuses that one.

Usage (first read, zero GPU spend):
    uv run python -m rl_move.sim.joystick_demo_compose \
        --walk rl_move/sim/policies/ppo_goal_cw_walk50hz_rlonly_crutchoff_s0_warmadapt_acq1.zip \
        --turn rl_move/sim/policies/ppo_goal_cw_walkyaw50hz_rlonly_scratch_sac_s5_easedterm_tipmix05_yawbox30_bodyassist_ysema1_term400_gapincome_yawoffset_bothleggate_acq5_seedsweep.zip \
        --script demo1 --out logs/ckpt_eval/joystick_demo_compose_demo1.mp4
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "2")

import argparse
import json
import math
from pathlib import Path

import numpy as np

WZ_EPS = 1e-6  # below this, a segment is a pure translate (WALK role)


def joystick_script(name: str) -> list[dict]:
    """Named joystick command timelines: an ordered list of segments a
    human would feed a real joystick over time -- {duration_s, vx, vy,
    wz, label}. vx/vy m/s body-frame forward/lateral (0 deg = pure
    forward, matching `heading_to_vxvy`'s convention: vy>0 = +90 deg,
    i.e. left); wz commanded yaw rate rad/s, positive = turn left
    (counter-clockwise), matching `walk_yaw_offset_cmd`'s own sign
    (`eval_walk_turn_compose.py --turn-offset-deg` positive = left).
    Pure data, no env/model dependency -- testable without mujoco.
    """
    fwd = 0.06     # bundle_rlonly_v2's own trained speed band
    turn = 0.35    # rad/s -> ~0.35*8=2.8rad=160deg over an 8s hold;
                   # kept inside the turn specialist's trained authority
                   # band (box_yaw=30deg -> ~0.52rad single-segment cap
                   # is enforced downstream by `resolve_roles`'s own
                   # clamp, see its docstring)
    if name == "demo1":
        return [
            {"duration_s": 6.0, "vx": fwd, "vy": 0.0, "wz": 0.0,
             "label": "forward"},
            {"duration_s": 8.0, "vx": 0.0, "vy": 0.0, "wz": turn,
             "label": "turn-left"},
            {"duration_s": 6.0, "vx": fwd, "vy": 0.0, "wz": 0.0,
             "label": "forward"},
            {"duration_s": 8.0, "vx": 0.0, "vy": 0.0, "wz": -turn,
             "label": "turn-right"},
            {"duration_s": 6.0, "vx": -fwd, "vy": 0.0, "wz": 0.0,
             "label": "reverse"},
            {"duration_s": 8.0, "vx": fwd, "vy": 0.0, "wz": turn,
             "label": "curve-left"},
            {"duration_s": 6.0, "vx": 0.0, "vy": 0.0, "wz": 0.0,
             "label": "stop"},
        ]
    if name == "turns_only":
        return [
            {"duration_s": 8.0, "vx": 0.0, "vy": 0.0, "wz": turn,
             "label": "turn-left"},
            {"duration_s": 8.0, "vx": 0.0, "vy": 0.0, "wz": -turn,
             "label": "turn-right"},
        ]
    if name == "smoke":
        # minimal 2-segment script for fast local/CI-adjacent smoke
        # runs (still real mujoco, just short)
        return [
            {"duration_s": 2.0, "vx": fwd, "vy": 0.0, "wz": 0.0,
             "label": "forward"},
            {"duration_s": 3.0, "vx": 0.0, "vy": 0.0, "wz": turn,
             "label": "turn-left"},
        ]
    raise ValueError(f"unknown joystick script {name!r}")


# The turn specialist's own trained heading-offset authority
# (`goal.joint_action_box_hip_deg`-independent task box, see
# cfg_recipe_walkyaw50hz_acq5_seedsweep's `box_yaw=30deg`): clamp any
# single resolved turn segment's integrated offset to this band so an
# over-long/over-fast joystick hold cannot silently ask the frozen
# checkpoint for an OOD target the acq5 gate never swept. Matches the
# `--turn-offset-deg` range `eval_walk_turn_compose.py`'s own
# `OFFSET_SET_DEG` cycles through.
TURN_OFFSET_CLAMP_DEG = 30.0


def resolve_roles(segments: list[dict], wz_eps: float = WZ_EPS
                  ) -> list[dict]:
    """Map raw joystick segments (vx, vy, wz) to role-tagged segments
    ready to drive `env_walk`/`env_turn`: {role, duration_s, label,
    ...role params}. Pure function (math only), no env/model
    dependency -- testable without mujoco. See module docstring for
    the switch rule."""
    out = []
    for seg in segments:
        vx, vy, wz = float(seg["vx"]), float(seg["vy"]), float(seg["wz"])
        dur = float(seg["duration_s"])
        label = seg.get("label", "")
        if abs(wz) <= wz_eps:
            speed = math.hypot(vx, vy)
            heading_deg = (math.degrees(math.atan2(vy, vx))
                          if speed > 0.0 else 0.0)
            out.append({"role": "walk", "duration_s": dur,
                        "speed": speed, "heading_deg": heading_deg,
                        "label": label})
        else:
            offset_deg = math.degrees(wz * dur)
            clamped = max(-TURN_OFFSET_CLAMP_DEG,
                         min(TURN_OFFSET_CLAMP_DEG, offset_deg))
            out.append({"role": "turn", "duration_s": dur,
                        "offset_deg": clamped,
                        "curve_speed": math.hypot(vx, vy),
                        "label": label,
                        "clamped": clamped != offset_deg})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--walk", type=Path, required=True)
    ap.add_argument("--turn", type=Path, required=True)
    ap.add_argument("--walk-recipe", choices=("rlonly_v2",),
                    default="rlonly_v2")
    ap.add_argument("--turn-recipe", choices=("acq5_seedsweep",),
                    default="acq5_seedsweep")
    ap.add_argument("--script", default="demo1",
                    choices=("demo1", "turns_only", "smoke"))
    ap.add_argument("--rot60", action="store_true",
                    help="wrap the walk policy in Rot60Policy (see "
                         "eval_walk_turn_compose.py's own flag)")
    ap.add_argument("--settle-grounded-s", type=float, default=1.0,
                    help="extend the end of every WALK segment up to "
                         "this many extra seconds, stopping the "
                         "instant all six feet are simultaneously "
                         "planted, before handing state to the next "
                         "segment's role (default 1.0 -- the "
                         "eval_walk_turn_compose.py root-caused "
                         "leg-3-unload-during-hold fix; 0.0 = off)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--stochastic", action="store_true")
    ap.add_argument("--fps", type=int, default=None,
                    help="default None = 1/env.dt (real time)")
    ap.add_argument("--out", type=Path, required=True,
                    help="output .mp4 path")
    ap.add_argument("--summary-out", type=Path, default=None,
                    help="optional per-segment JSON summary path")
    args = ap.parse_args()

    import mujoco

    from rl_move.env import build_obs
    from .eval_checkpoint import _sacrificed_legs
    from .eval_lifecycle_handoff_rlonly import (
        PhysicalState, _build_env, _set_mix, apply_physical_state,
        capture_physical_state, heading_to_vxvy, write_mp4,
    )
    from .eval_walk_turn_compose import _duty_swings
    from .gru_policy import load_checkpoint_auto
    if args.walk_recipe == "rlonly_v2":
        from .cfg_recipe_walk50hz_rlonly_v2 import CFG_ARGS as WALK_ARGS
    if args.turn_recipe == "acq5_seedsweep":
        from .cfg_recipe_walkyaw50hz_acq5_seedsweep import (
            CFG_ARGS as TURN_ARGS,
        )

    roles = resolve_roles(joystick_script(args.script))
    total_s = sum(r["duration_s"] for r in roles)
    margin_s = 2.0
    env_walk = _build_env(WALK_ARGS, episode_seconds=total_s + margin_s,
                          seed=args.seed, render=True)
    env_turn = _build_env(TURN_ARGS, episode_seconds=total_s + margin_s,
                          seed=args.seed, render=True)

    walk = load_checkpoint_auto(args.walk, device="cpu")
    turn = load_checkpoint_auto(args.turn, device="cpu")
    if args.rot60:
        from .rot60 import Rot60Policy
        walk = Rot60Policy(walk)

    n_walk_env = int(env_walk.observation_space.shape[0])
    n_turn_env = int(env_turn.observation_space.shape[0])
    n_walk_model = int(walk.observation_space.shape[0])
    n_turn_model = int(turn.observation_space.shape[0])
    compat = {
        "walk_env_obs": n_walk_env, "walk_model_obs": n_walk_model,
        "turn_env_obs": n_turn_env, "turn_model_obs": n_turn_model,
        "walk_compatible": n_walk_model == n_walk_env,
        "turn_compatible": n_turn_model == n_turn_env,
    }
    print(f"[joystick_demo_compose] obs compatibility: {compat}")
    if not (compat["walk_compatible"] and compat["turn_compatible"]):
        report = {"compat": compat, "segments": [],
                  "verdict": "OBS_INCOMPATIBLE"}
        if args.summary_out:
            args.summary_out.parent.mkdir(parents=True, exist_ok=True)
            args.summary_out.write_text(json.dumps(report, indent=2))
        print("[joystick_demo_compose] ABORT: obs shape mismatch, see "
              "compat above.")
        return 1

    pads_walk = [env_walk.model.body(f"L{i}_pad").id for i in range(6)]
    pads_turn = [env_turn.model.body(f"L{i}_pad").id for i in range(6)]
    deterministic = not args.stochastic

    frames: list = []

    def grab(env) -> None:
        frames.append(env.render())

    def reanchor(env, state: PhysicalState | None):
        gen = env._goal_gen
        _set_mix(gen, walk=1.0)
        env.reset(seed=args.seed)
        if state is not None:
            apply_physical_state(env, state)
            mujoco.mj_forward(env.model, env.data)
            env._state = env._read_state()
        return env._final_obs(
            build_obs(env.cfg, env._state, env._q_nom, env._prev_action,
                      goal=env._current_goal(), tilt_ref=env._tilt_ref0),
            reset=True)

    def gait_valid(contact_hist, pads, **kw) -> tuple[bool, list]:
        if len(contact_hist) <= 1:
            return True, []
        duty, swings = _duty_swings(np.asarray(contact_hist, dtype=bool))
        sac = _sacrificed_legs(duty, swings, **kw)
        return not sac, sac

    def run_walk(state, seg) -> tuple[dict, PhysicalState | None]:
        obs = reanchor(env_walk, state)
        if hasattr(walk, "reset"):
            walk.reset()
        traj = env_walk._goal_traj
        vx, vy = heading_to_vxvy(seg["speed"], seg["heading_deg"])
        rec = {"role": "walk", "label": seg["label"], "fall": None}
        contact_hist = []
        n_steps = max(1, int(round(seg["duration_s"] / env_walk.dt)))
        for _ in range(n_steps):
            if hasattr(traj, "vx"):
                traj.vx[:] = vx
                traj.vy[:] = vy
            if getattr(traj, "wz", None) is not None:
                traj.wz[:] = 0.0
            a, _ = walk.predict(obs, deterministic=deterministic)
            obs, _rw, term, trunc, info = env_walk.step(a)
            grab(env_walk)
            contact_hist.append([
                float(env_walk.data.sensordata[adr]) > 0.5
                for adr in env_walk._touch_adr])
            if term or trunc:
                rec["fall"] = str(
                    info.get("termination_reason") or "episode_end")
                break
        if not rec["fall"] and args.settle_grounded_s > 0.0:
            settle_ticks = max(1, int(round(
                args.settle_grounded_s / env_walk.dt)))
            for _ in range(settle_ticks):
                if hasattr(traj, "vx"):
                    traj.vx[:] = 0.0
                    traj.vy[:] = 0.0
                a, _ = walk.predict(obs, deterministic=deterministic)
                obs, _rw, term, trunc, info = env_walk.step(a)
                grab(env_walk)
                tick_contact = [
                    float(env_walk.data.sensordata[adr]) > 0.5
                    for adr in env_walk._touch_adr]
                contact_hist.append(tick_contact)
                if term or trunc:
                    rec["fall"] = str(
                        info.get("termination_reason") or "episode_end")
                    break
                if all(tick_contact):
                    break
        valid, sac = gait_valid(contact_hist, pads_walk)
        rec["gait_valid"] = valid
        rec["sacrificed_legs"] = sac
        rec["success"] = rec["fall"] is None and valid
        return rec, (capture_physical_state(env_walk)
                     if rec["fall"] is None else None)

    def run_turn(state, seg) -> tuple[dict, PhysicalState | None]:
        obs = reanchor(env_turn, state)
        if hasattr(turn, "reset"):
            turn.reset()
        traj = env_turn._goal_traj
        delta = math.radians(seg["offset_deg"])
        cvx, cvy = heading_to_vxvy(seg["curve_speed"], 0.0)
        rec = {"role": "turn", "label": seg["label"], "fall": None,
              "target_deg": seg["offset_deg"], "clamped": seg["clamped"]}
        errs = []
        contact_hist = []
        n_steps = max(1, int(round(seg["duration_s"] / env_turn.dt)))
        for _ in range(n_steps):
            if hasattr(traj, "vx"):
                traj.vx[:] = cvx
                traj.vy[:] = cvy
            if getattr(traj, "wz", None) is not None:
                traj.wz[:] = 0.0
            if getattr(traj, "yaw_offset", None) is not None:
                traj.yaw_offset[:] = delta
            a, _ = turn.predict(obs, deterministic=deterministic)
            obs, _rw, term, trunc, info = env_turn.step(a)
            grab(env_turn)
            if "walk_yaw_offset_err" in info:
                errs.append(abs(float(info["walk_yaw_offset_err"])))
            contact_hist.append([
                float(env_turn.data.sensordata[adr]) > 0.5
                for adr in env_turn._touch_adr])
            if term or trunc:
                rec["fall"] = str(
                    info.get("termination_reason") or "episode_end")
                break
        q4 = errs[-max(1, len(errs) // 4):] if errs else []
        rec["err_q4_mean_rad"] = (round(float(np.mean(q4)), 4)
                                  if q4 else None)
        valid, sac = gait_valid(contact_hist, pads_turn,
                                gait_valid_relaxed_hold=True)
        rec["gait_valid"] = valid
        rec["sacrificed_legs"] = sac
        rec["success"] = rec["fall"] is None and valid
        return rec, (capture_physical_state(env_turn)
                     if rec["fall"] is None else None)

    segs_out = []
    state = None
    for seg in roles:
        if seg["role"] == "walk":
            rec, state = run_walk(state, seg)
        else:
            rec, state = run_turn(state, seg)
        segs_out.append(rec)
        print(f"[joystick_demo_compose] seg={rec['label']} "
              f"role={rec['role']} success={rec['success']} "
              f"fall={rec['fall']}")
        if state is None:
            break

    zero_fall = all(s["fall"] is None for s in segs_out)
    summary = {
        "script": args.script, "compat": compat, "segments": segs_out,
        "zero_fall": zero_fall,
        "all_gait_valid": all(s["gait_valid"] for s in segs_out),
    }
    print(f"[joystick_demo_compose] SUMMARY zero_fall={zero_fall} "
          f"all_gait_valid={summary['all_gait_valid']}")

    fps = args.fps if args.fps is not None else round(1.0 / env_walk.dt)
    write_mp4(frames, args.out, fps=fps)
    print(f"[joystick_demo_compose] wrote {args.out} "
          f"({len(frames)} frames @ {fps}fps)")

    if args.summary_out:
        args.summary_out.parent.mkdir(parents=True, exist_ok=True)
        args.summary_out.write_text(json.dumps(summary, indent=2))
        print(f"[joystick_demo_compose] wrote {args.summary_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
