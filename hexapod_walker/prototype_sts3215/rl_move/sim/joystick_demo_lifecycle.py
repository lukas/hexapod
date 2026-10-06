"""Continuous mp4 of the FULL `rl_only` lifecycle: rise+hold -> JOYSTICK-
DRIVEN walk/turn -> controlled lower, four separately-trained clean-RL
checkpoints chained in one session (zero new training).

THE GAP THIS CLOSES (todaypolicy/STATUS.md 2026-10-06, under
`bundle_rlonly_lifecycle_full_v1`): "Not yet a continuous mp4
(joystick_demo_compose.py's render path not extended to this 4-role
chain)." `eval_lifecycle_full_rlonly.py` proved the four-role chain
survives (148/160 off-axis) but only writes 1fps contact-sheet strips;
`joystick_demo_compose.py` already writes a continuous mp4 driven by a
joystick-shaped (vx, vy, wz) command timeline, but only for the
walk<->turn pair (no rise/lower). RL_GOALS.md's sim deliverable needs
"Lukas must be able to steer it interactively... demonstrate command
changes, turns, starts, stops and restarts" for the FULL grounded-to-
grounded sequence, not just the walking segment -- this module is that
single continuous render, built by reusing both precedent tools
VERBATIM (same checkpoints, same `PhysicalState` cross-env reanchor
trick, same `resolve_roles`/`joystick_script` command grammar) rather
than any new mechanism. Pure external orchestration of four frozen
policies; no env/reward code touched.

Usage (first real render, zero GPU spend, CPU-only MuJoCo):
    uv run python -m rl_move.sim.joystick_demo_lifecycle \
        --script demo1 \
        --out logs/ckpt_eval/joystick_demo_lifecycle_demo1.mp4 \
        --summary-out logs/ckpt_eval/joystick_demo_lifecycle_demo1_summary.json
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

from .eval_lifecycle_full_rlonly import (
    DEFAULT_LOWER, DEFAULT_STANCE, DEFAULT_TURN, DEFAULT_WALK,
)
from .eval_lifecycle_handoff_rlonly import (
    PHASE_A_S,
    PhysicalState,
    _build_env,
    _compose_lower_cfg_args,
    _set_mix,
    apply_physical_state,
    capture_physical_state,
    heading_to_vxvy,
    write_mp4,
)
from .joystick_demo_compose import joystick_script, resolve_roles


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stance", type=Path, default=DEFAULT_STANCE)
    ap.add_argument("--walk", type=Path, default=DEFAULT_WALK)
    ap.add_argument("--turn", type=Path, default=DEFAULT_TURN)
    ap.add_argument("--lower", type=Path, default=DEFAULT_LOWER)
    ap.add_argument("--walk-recipe", choices=("rlonly_v2", "slew_smooth_s0"),
                    default="slew_smooth_s0")
    ap.add_argument("--turn-recipe", choices=("acq5_seedsweep",),
                    default="acq5_seedsweep")
    ap.add_argument("--lower-recipe", choices=("lowerrole_sac_drramp",),
                    default="lowerrole_sac_drramp")
    ap.add_argument("--rot60", action="store_true", default=True,
                    help="wrap the WALK policy in rot60.Rot60Policy "
                         "(default ON -- matches the full-lifecycle "
                         "tool's own validated default; --no-rot60 to "
                         "disable)")
    ap.add_argument("--no-rot60", dest="rot60", action="store_false")
    ap.add_argument("--script", default="demo1",
                    choices=("demo1", "turns_only", "smoke"))
    ap.add_argument("--settle-grounded-s", type=float, default=1.0,
                    help="extend the end of every WALK segment (same "
                         "leg-3-unload-during-hold fix both precedent "
                         "tools use before a role handoff; 0.0 = off)")
    ap.add_argument("--lower-episode-s", type=float, default=15.0)
    ap.add_argument("--lower-cfg", action="append", default=None,
                    help="EXTRA cfg-set override(s) for env_lower. "
                         "Default None: if --lower is left at the "
                         "thermalderate50-s2 champion default this "
                         "still auto-applies its own training delta "
                         "below (the same eval/train cfg-mismatch fix "
                         "eval_lifecycle_full_rlonly.py's own --lower-"
                         "cfg help documents).")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--stochastic", action="store_true")
    ap.add_argument("--fps", type=int, default=None,
                    help="default None = 1/env.dt (real time)")
    ap.add_argument("--out", type=Path, required=True,
                    help="output .mp4 path")
    ap.add_argument("--summary-out", type=Path, default=None)
    args = ap.parse_args()
    if args.lower_cfg is None and str(args.lower) == str(DEFAULT_LOWER):
        args.lower_cfg = ["motor.thermal_derate_enable=1",
                          "motor.thermal_derate_max_frac=0.5"]

    import mujoco

    from rl_move.env import build_obs
    from .eval_checkpoint import _sacrificed_legs
    from .eval_walk_turn_compose import _duty_swings
    from .gru_policy import load_checkpoint_auto, wrap_recurrent_predictor
    from .probe_currentcap29_flatonly import (
        BASE_CFG_ARGS, FLATONLY_OVERRIDE_ARGS,
    )
    if args.walk_recipe == "slew_smooth_s0":
        from .cfg_recipe_walk50hz_slew_smooth_s0 import CFG_ARGS as WALK_ARGS
    else:
        from .cfg_recipe_walk50hz_rlonly_v2 import CFG_ARGS as WALK_ARGS
    from .cfg_recipe_stance50hz_rlonly_lowerrole_scratch_sac_drramp import (
        CFG_ARGS as LOWER_ARGS,
    )
    from .cfg_recipe_walkyaw50hz_acq5_seedsweep import CFG_ARGS as TURN_ARGS

    stance_cfg_args = list(BASE_CFG_ARGS) + list(FLATONLY_OVERRIDE_ARGS)

    env_rise = _build_env(stance_cfg_args, episode_seconds=15.0,
                          seed=args.seed, render=True)
    roles = resolve_roles(joystick_script(args.script))
    walk_turn_total_s = sum(r["duration_s"] for r in roles)
    margin_s = 2.0
    env_walk = _build_env(_compose_lower_cfg_args(WALK_ARGS, None),
                          episode_seconds=walk_turn_total_s + margin_s,
                          seed=args.seed, render=True)
    env_turn = _build_env(_compose_lower_cfg_args(TURN_ARGS, None),
                          episode_seconds=walk_turn_total_s + margin_s,
                          seed=args.seed, render=True)
    env_lower = _build_env(_compose_lower_cfg_args(LOWER_ARGS, args.lower_cfg),
                           episode_seconds=args.lower_episode_s,
                           seed=args.seed, render=True)

    stance = wrap_recurrent_predictor(
        load_checkpoint_auto(args.stance, device="cpu"))
    walk = wrap_recurrent_predictor(load_checkpoint_auto(args.walk, device="cpu"))
    if args.rot60:
        from .rot60 import Rot60Policy
        walk = Rot60Policy(walk)
    turn = wrap_recurrent_predictor(load_checkpoint_auto(args.turn, device="cpu"))
    lower = wrap_recurrent_predictor(load_checkpoint_auto(args.lower, device="cpu"))

    n_stance = int(stance.observation_space.shape[0])
    n_turn = int(turn.observation_space.shape[0])
    n_lower = int(lower.observation_space.shape[0])
    deterministic = not args.stochastic
    pads_walk = [env_walk.model.body(f"L{i}_pad").id for i in range(6)]
    pads_turn = [env_turn.model.body(f"L{i}_pad").id for i in range(6)]

    frames: list = []

    def grab(env) -> None:
        frames.append(env.render())

    def reanchor(env, state: PhysicalState):
        gen = env._goal_gen
        _set_mix(gen, walk=1.0)
        env.reset(seed=args.seed)
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

    def rise_phase():
        gen = env_rise._goal_gen
        _set_mix(gen, rise=1.0)
        gen.force_rise_start = "flat"
        obs, _ = env_rise.reset(seed=args.seed)
        gen.force_rise_start = None
        rec = {"seg": "rise", "label": "rise", "fall": None}
        for _ in range(int(round(PHASE_A_S / env_rise.dt))):
            a, _ = stance.predict(obs[:n_stance], deterministic=deterministic)
            obs, _rw, term, trunc, info = env_rise.step(a)
            grab(env_rise)
            if term or trunc:
                rec["fall"] = str(info.get("termination_reason") or "end")
                rec["success"] = False
                return rec, None
        h_err = (float(env_rise.data.xpos[env_rise._chassis_bid, 2])
                 - (env_rise._z0 + env_rise._h_target))
        ok, _detail = env_rise.plant_report(height_err_m=h_err)
        rec["success"] = bool(ok)
        rec["height_err_mm"] = round(h_err * 1000.0, 1)
        return rec, capture_physical_state(env_rise)

    def run_walk(state, seg):
        obs = reanchor(env_walk, state)
        if hasattr(walk, "reset"):
            walk.reset()
        traj = env_walk._goal_traj
        vx, vy = heading_to_vxvy(seg["speed"], seg["heading_deg"])
        rec = {"seg": "walk", "label": seg["label"], "fall": None}
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
                rec["fall"] = str(info.get("termination_reason") or "episode_end")
                break
        if not rec["fall"] and args.settle_grounded_s > 0.0:
            settle_ticks = max(1, int(round(args.settle_grounded_s / env_walk.dt)))
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
                    rec["fall"] = str(info.get("termination_reason") or "episode_end")
                    break
                if all(tick_contact):
                    break
        valid, sac = gait_valid(contact_hist, pads_walk)
        rec["gait_valid"] = valid
        rec["sacrificed_legs"] = sac
        rec["success"] = rec["fall"] is None and valid
        return rec, (capture_physical_state(env_walk)
                     if rec["fall"] is None else None)

    def run_turn(state, seg):
        obs = reanchor(env_turn, state)
        if hasattr(turn, "reset"):
            turn.reset()
        traj = env_turn._goal_traj
        delta = math.radians(seg["offset_deg"])
        cvx, cvy = heading_to_vxvy(seg["curve_speed"], 0.0)
        rec = {"seg": "turn", "label": seg["label"], "fall": None,
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
            a, _ = turn.predict(obs[:n_turn], deterministic=deterministic)
            obs, _rw, term, trunc, info = env_turn.step(a)
            grab(env_turn)
            if "walk_yaw_offset_err" in info:
                errs.append(abs(float(info["walk_yaw_offset_err"])))
            contact_hist.append([
                float(env_turn.data.sensordata[adr]) > 0.5
                for adr in env_turn._touch_adr])
            if term or trunc:
                rec["fall"] = str(info.get("termination_reason") or "episode_end")
                break
        q4 = errs[-max(1, len(errs) // 4):] if errs else []
        rec["err_q4_mean_rad"] = round(float(np.mean(q4)), 4) if q4 else None
        valid, sac = gait_valid(contact_hist, pads_turn,
                                gait_valid_relaxed_hold=True)
        rec["gait_valid"] = valid
        rec["sacrificed_legs"] = sac
        rec["converged"] = (rec["err_q4_mean_rad"] is not None
                            and rec["err_q4_mean_rad"] <= 0.05)
        rec["success"] = rec["fall"] is None and valid and rec["converged"]
        return rec, (capture_physical_state(env_turn)
                     if rec["fall"] is None else None)

    def lower_phase(state):
        gen = env_lower._goal_gen
        _set_mix(gen, lower=1.0)
        env_lower.reset(seed=args.seed)
        apply_physical_state(env_lower, state)
        mujoco.mj_forward(env_lower.model, env_lower.data)
        env_lower._state = env_lower._read_state()
        obs = env_lower._final_obs(
            build_obs(env_lower.cfg, env_lower._state, env_lower._q_nom,
                      env_lower._prev_action, goal=env_lower._current_goal(),
                      tilt_ref=env_lower._tilt_ref0), reset=True)
        if hasattr(lower, "reset"):
            lower.reset()
        n_steps = max(1, int(round(args.lower_episode_s / env_lower.dt)))
        term = trunc = False
        info: dict = {}
        for _ in range(n_steps):
            a, _ = lower.predict(obs[:n_lower], deterministic=deterministic)
            obs, _rw, term, trunc, info = env_lower.step(a)
            grab(env_lower)
            if term or trunc:
                break
        h_err_mm = round(1000.0 * (
            float(env_lower.data.xpos[env_lower._chassis_bid, 2])
            - (env_lower._z0 + env_lower._h_target)), 1)
        fall = str(info.get("termination_reason") or "end") if term else None
        lower_ok = (not term) and abs(h_err_mm) <= 15.0
        return {"seg": "lower", "label": "lower", "fall": fall,
                "height_err_end_mm": h_err_mm, "success": bool(lower_ok)}

    segs_out = []
    rrec, state = rise_phase()
    segs_out.append(rrec)
    for seg in roles:
        if state is None:
            break
        if seg["role"] == "walk":
            rec, state = run_walk(state, seg)
        else:
            rec, state = run_turn(state, seg)
        segs_out.append(rec)
        print(f"[joystick_demo_lifecycle] seg={rec['label']} "
              f"role={rec['seg']} success={rec.get('success')} "
              f"fall={rec['fall']}")
    if state is not None:
        lrec = lower_phase(state)
        segs_out.append(lrec)
        print(f"[joystick_demo_lifecycle] seg=lower role=lower "
              f"success={lrec['success']} fall={lrec['fall']}")

    zero_fall = all(s["fall"] is None for s in segs_out)
    summary = {
        "script": args.script, "segments": segs_out, "zero_fall": zero_fall,
        "all_gait_valid": all(s.get("gait_valid", True) for s in segs_out),
        "stance": str(args.stance), "walk": str(args.walk),
        "turn": str(args.turn), "lower": str(args.lower),
        "walk_recipe": args.walk_recipe, "rot60": bool(args.rot60),
        "deterministic": deterministic,
    }
    print(f"[joystick_demo_lifecycle] SUMMARY zero_fall={zero_fall} "
          f"all_gait_valid={summary['all_gait_valid']} "
          f"n_segments={len(segs_out)}")

    fps = args.fps if args.fps is not None else round(1.0 / env_walk.dt)
    write_mp4(frames, args.out, fps=fps)
    print(f"[joystick_demo_lifecycle] wrote {args.out} "
          f"({len(frames)} frames @ {fps}fps)")

    if args.summary_out:
        args.summary_out.parent.mkdir(parents=True, exist_ok=True)
        args.summary_out.write_text(json.dumps(summary, indent=2))
        print(f"[joystick_demo_lifecycle] wrote {args.summary_out}")
    return 0 if zero_fall else 1


if __name__ == "__main__":
    raise SystemExit(main())
