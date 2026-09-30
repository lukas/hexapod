"""`rl_only` role composition: alternating FORWARD-walk <-> STATIONARY
TURN-OFFSET segments, driven by two SEPARATELY trained clean-RL
checkpoints on the SAME goal_task walk env (mode stays "walk"
throughout -- no rise/lower lifecycle grammar).

THE QUESTION (walkcurr Next item, 2026-09-30, following the champs5-
acq1/acq2 mixwalk05 single-policy composition's decisive 2/2 FAIL):
does chaining the ALREADY-PROVEN forward-walk specialist
(`bundle_rlonly_v2` / `ppo_goal_cw_walk50hz_rlonly_crutchoff_s0_
warmadapt_acq1`) with the stationary-heading-hold turn specialist
(`cw-walkyaw50hz-rlonly-scratch-sac-s5-...-acq5-seedsweep`, the
walkcurr recipe champion) -- via role-selection plumbing, not a joint
single-policy reward mix -- produce a zero-fall, direction-following
session? This is role composition (RL_GOALS.md's allowed non-motion
category: "separately trained clean RL roles may be composed by
non-motion state-selection/blending plumbing"), NOT a new training
run: zero GPU spend, CPU-only MuJoCo, both checkpoints frozen.

WHY TWO ENV INSTANCES: exactly `eval_lifecycle_handoff_rlonly.py`'s own
rationale -- the two roles' cfg differ in ways SimServoParams/
_act_to_q cache at env __init__ (box_yaw 15deg vs 30deg, term_penalty
24 vs 400, safety.max_roll/pitch 30 vs 45) and cannot be hot-swapped
mid-episode on one live env. Two `SimHexapodJointWalkEnv` instances
(one per role's own versioned cfg-set recipe --
`cfg_recipe_walk50hz_rlonly_v2` / `cfg_recipe_walkyaw50hz_
acq5_seedsweep`) are built; at each segment boundary the raw PHYSICAL
state (qpos/qvel/ctrl/act + the safety layer's slew memory) is copied
across via that module's own `capture_physical_state`/
`apply_physical_state` (reused, not re-derived) -- role-selection
plumbing per RL_GOALS.md, no scripted joint trajectory, no reward
touched.

Per-segment criteria (per the walkcurr Next item's own spec):
  forward  eval_checkpoint's walk bar: tracking error (mean |v -
           v_ref|) + gait_valid (`eval_checkpoint._sacrificed_legs`,
           strict -- a persistently parked/dragged leg fails even if
           tracking is clean).
  turn     the acq5 gate's own bar: terminal-quartile
           |walk_yaw_offset_err| <= 0.05 rad (info key the reward
           kernel already writes every tick) + gait_valid with
           `gait_valid_relaxed_hold=True` (a converged hold
           legitimately stops swinging some/all legs -- see that
           flag's own docstring, added FOR this exact task shape).
Whole-session: zero-fall rate across every alternating segment.

Usage (first CPU-only read, zero GPU spend):
    uv run python -m rl_move.sim.eval_walk_turn_compose \
        --walk rl_move/sim/policies/ppo_goal_cw_walk50hz_rlonly_crutchoff_s0_warmadapt_acq1.zip \
        --turn rl_move/sim/policies/ppo_goal_cw_walkyaw50hz_rlonly_scratch_sac_s5_easedterm_tipmix05_yawbox30_bodyassist_ysema1_term400_gapincome_yawoffset_bothleggate_acq5_seedsweep.zip \
        --episodes 12 --cycles 2 --out logs/ckpt_eval/walk_turn_compose_v1.json
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

FWD_SETTLE_S = 1.0
FWD_HOLD_S = 6.0
FWD_STOP_S = 1.0
CONTACT_N = 0.5   # same threshold eval_checkpoint.py / eval_lifecycle_
                  # handoff_rlonly.py use for touch-sensor contact


def forward_schedule(vx: float, vy: float):
    return [(FWD_SETTLE_S, 0.0, 0.0), (FWD_HOLD_S, vx, vy),
            (FWD_STOP_S, 0.0, 0.0)]


def _duty_swings(contact: np.ndarray) -> tuple[np.ndarray, list]:
    """(6,) duty fraction + swing-count list from a (T,6) bool contact
    window -- identical formula to eval_checkpoint.py's walk-mode
    gait-validity accumulation (`duty_w`/`swings_w`)."""
    duty = contact.mean(axis=0)
    swings = [0] * 6
    for f in range(6):
        d = np.diff(contact[:, f].astype(int))
        swings[f] = int(np.sum(d == -1))
    return duty, swings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--walk", type=Path, required=True,
                    help="forward-walk specialist checkpoint (obs/"
                         "action contract = cfg_recipe_walk50hz_"
                         "rlonly_v2 unless --walk-recipe overrides)")
    ap.add_argument("--turn", type=Path, required=True,
                    help="stationary-heading-hold turn specialist "
                         "checkpoint (obs/action contract = "
                         "cfg_recipe_walkyaw50hz_acq5_seedsweep unless "
                         "--turn-recipe overrides)")
    ap.add_argument("--walk-recipe", choices=("rlonly_v2",),
                    default="rlonly_v2")
    ap.add_argument("--turn-recipe", choices=("acq5_seedsweep",),
                    default="acq5_seedsweep")
    ap.add_argument("--episodes", type=int, default=12)
    ap.add_argument("--cycles", type=int, default=2,
                    help="number of forward-then-turn segment pairs "
                         "per episode (default 2: fwd,turn,fwd,turn)")
    ap.add_argument("--speed", type=float, default=0.06,
                    help="forward segment commanded speed, m/s "
                         "(default = bundle_rlonly_v2's own trained "
                         "band, goal.walk_speed_{min,max}_m_s=0.06)")
    ap.add_argument("--heading-deg", type=float, default=0.0,
                    help="forward segment commanded body-frame heading "
                         "in degrees, 0=forward (default, bit-exact "
                         "prior behavior); +-45/+-90/+-135/180 match "
                         "eval_checkpoint.py's heading convention -- "
                         "the walk champion's own closed off-axis "
                         "mechanism-class failures apply at nonzero "
                         "headings unless --rot60 is also set")
    ap.add_argument("--rot60", action="store_true",
                    help="wrap the forward (--walk) policy in "
                         "rot60.Rot60Policy (default off = bit-exact "
                         "unwrapped champion) -- rot60_fullcircle's "
                         "own validated fix for the closed chronic "
                         "off-forward front-pair-sacrifice failure, "
                         "tested here composed with a turn-and-hold "
                         "segment instead of the walk role in "
                         "isolation")
    ap.add_argument("--turn-offset-deg", type=float, default=None,
                    help="fixed turn-segment target offset in degrees "
                         "(default None = cycle through the turn "
                         "checkpoint's own trained set in order, "
                         "cfg_recipe_walkyaw50hz_acq5_seedsweep."
                         "OFFSET_SET_DEG)")
    ap.add_argument("--turn-episode-s", type=float, default=20.0,
                    help="turn segment duration, seconds (default 20.0 "
                         "= the acq5-seedsweep recipe's own trained/"
                         "gated episode length, so the tail-quartile "
                         "convergence read is comparable to that "
                         "checkpoint's own isolated gate)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--stochastic", action="store_true",
                    help="both policies predict stochastically "
                         "(default deterministic)")
    ap.add_argument("--strips", type=Path, default=None,
                    help="dir for 1 fps frame-strip PNGs (episode 0 "
                         "only)")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    import mujoco

    from rl_move.config import load_config
    from rl_move.env import build_obs
    from .gru_policy import load_checkpoint_auto
    from .eval_checkpoint import _sacrificed_legs
    from .eval_lifecycle_handoff_rlonly import (
        PhysicalState, _build_env, _set_mix, apply_physical_state,
        capture_physical_state, heading_to_vxvy,
    )
    if args.walk_recipe == "rlonly_v2":
        from .cfg_recipe_walk50hz_rlonly_v2 import CFG_ARGS as WALK_ARGS
    if args.turn_recipe == "acq5_seedsweep":
        from .cfg_recipe_walkyaw50hz_acq5_seedsweep import (
            CFG_ARGS as TURN_ARGS, OFFSET_SET_DEG,
        )

    want_strips = args.strips is not None
    # +2s margin on BOTH envs (eval_lifecycle_handoff_rlonly's own
    # convention): the harness's own step-count loop must always
    # finish strictly BEFORE the env's internal time-limit `trunc`
    # fires, or an honest schedule-complete episode gets misread as a
    # fall (found during smoke-testing this tool: a 4.0s turn segment
    # against episode_seconds=4.0 truncated on the segment's own final
    # tick and was wrongly recorded as fall="episode_end").
    fwd_episode_s = FWD_SETTLE_S + FWD_HOLD_S + FWD_STOP_S + 2.0
    env_walk = _build_env(WALK_ARGS, episode_seconds=fwd_episode_s,
                          seed=args.seed, render=want_strips)
    env_turn = _build_env(TURN_ARGS,
                          episode_seconds=args.turn_episode_s + 2.0,
                          seed=args.seed, render=want_strips)

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
    print(f"[walk_turn_compose] obs compatibility: {compat}")
    if not (compat["walk_compatible"] and compat["turn_compatible"]):
        # Named contingency in the walkcurr Next item itself ("if
        # bundle_rlonly_v2 turns out obs/arch-incompatible") -- a
        # clean, informative NO is a valid first-read result, not a
        # crash. Still write the report so the incompatibility is
        # recorded, not just printed.
        report = {"compat": compat, "episodes": [],
                  "verdict": "OBS_INCOMPATIBLE"}
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(report, indent=2))
        print("[walk_turn_compose] ABORT: obs shape mismatch, see "
              "compat above -- composition needs a matched-arch "
              "forward specialist before this reads anything further.")
        return 1

    pads_walk = [env_walk.model.body(f"L{i}_pad").id for i in range(6)]
    pads_turn = [env_turn.model.body(f"L{i}_pad").id for i in range(6)]
    deterministic = not args.stochastic

    strip_frames: list = []

    def grab(env) -> None:
        if not want_strips:
            return
        if grab.n % max(1, int(round(1.0 / env.dt))) == 0:
            strip_frames.append(env.render())
        grab.n += 1
    grab.n = 0

    def save_strip(name: str) -> None:
        if not want_strips or not strip_frames:
            return
        import imageio.v2 as imageio
        args.strips.mkdir(parents=True, exist_ok=True)
        imageio.imwrite(args.strips / f"{name}.png",
                        np.hstack(strip_frames))
        strip_frames.clear()

    def reanchor(env, gen_mode: str, state: PhysicalState | None,
                seed: int):
        """Fresh <env>'s own mode-1.0 reset (establishes THAT env's own
        start-relative goal references) then the carried physical
        state written back on top -- eval_lifecycle_handoff_rlonly's
        cross-env reanchor trick, generalized to walk<->walk instead of
        stance->walk. `state=None` = a genuine cold reset (episode
        start)."""
        gen = env._goal_gen
        _set_mix(gen, **{gen_mode: 1.0})
        env.reset(seed=seed)
        if state is not None:
            apply_physical_state(env, state)
            mujoco.mj_forward(env.model, env.data)
            env._state = env._read_state()
        return env._final_obs(
            build_obs(env.cfg, env._state, env._q_nom, env._prev_action,
                      goal=env._current_goal(), tilt_ref=env._tilt_ref0),
            reset=True)

    def run_forward(state: PhysicalState | None, ep_seed: int) -> dict:
        obs = reanchor(env_walk, "walk", state, ep_seed)
        if hasattr(walk, "reset"):
            walk.reset()
        traj = env_walk._goal_traj
        rec = {"fall": None, "trk_err": 0.0,
               "heading_deg": args.heading_deg}
        n_err = 0
        contact_hist, pad_xy_hist = [], []
        cmd_vx, cmd_vy = heading_to_vxvy(args.speed, args.heading_deg)
        for seconds, vx, vy in forward_schedule(cmd_vx, cmd_vy):
            for _ in range(max(1, int(round(seconds / env_walk.dt)))):
                if hasattr(traj, "vx"):
                    traj.vx[:] = vx
                    traj.vy[:] = vy
                if getattr(traj, "wz", None) is not None:
                    traj.wz[:] = 0.0
                a, _ = walk.predict(obs, deterministic=deterministic)
                obs, _rw, term, trunc, info = env_walk.step(a)
                grab(env_walk)
                contact_hist.append([
                    float(env_walk.data.sensordata[adr]) > CONTACT_N
                    for adr in env_walk._touch_adr])
                pad_xy_hist.append(
                    [env_walk.data.xpos[b, :2].copy() for b in pads_walk])
                v = env_walk._body_vel_xy()
                rec["trk_err"] += math.hypot(v[0] - vx, v[1] - vy)
                n_err += 1
                if term or trunc:
                    rec["fall"] = str(
                        info.get("termination_reason") or "episode_end")
                    break
            if rec["fall"]:
                break
        rec["trk_err"] = round(rec["trk_err"] / max(n_err, 1), 4)
        contact = np.asarray(contact_hist, dtype=bool)
        pad_xy = np.asarray(pad_xy_hist)
        if len(contact_hist) > 1:
            duty, swings = _duty_swings(contact)
            sac = _sacrificed_legs(duty, swings)
        else:
            sac = []
        rec["sacrificed_legs"] = sac
        rec["gait_valid"] = not sac
        rec["success"] = rec["fall"] is None and rec["gait_valid"]
        return rec, (capture_physical_state(env_walk)
                     if rec["fall"] is None else None)

    def run_turn(state: PhysicalState, ep_seed: int,
                offset_deg: float) -> dict:
        obs = reanchor(env_turn, "walk", state, ep_seed)
        if hasattr(turn, "reset"):
            turn.reset()
        traj = env_turn._goal_traj
        delta = math.radians(offset_deg)
        n_steps = max(1, int(round(args.turn_episode_s / env_turn.dt)))
        errs = []
        contact_hist, pad_xy_hist = [], []
        rec = {"fall": None, "target_deg": offset_deg}
        for _ in range(n_steps):
            if hasattr(traj, "vx"):
                traj.vx[:] = 0.0
                traj.vy[:] = 0.0
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
                float(env_turn.data.sensordata[adr]) > CONTACT_N
                for adr in env_turn._touch_adr])
            pad_xy_hist.append(
                [env_turn.data.xpos[b, :2].copy() for b in pads_turn])
            if term or trunc:
                rec["fall"] = str(
                    info.get("termination_reason") or "episode_end")
                break
        q4 = errs[-max(1, len(errs) // 4):] if errs else []
        rec["err_q4_mean_rad"] = (round(float(np.mean(q4)), 4)
                                  if q4 else None)
        rec["err_final_rad"] = round(errs[-1], 4) if errs else None
        contact = np.asarray(contact_hist, dtype=bool)
        if len(contact_hist) > 1:
            duty, swings = _duty_swings(contact)
            sac = _sacrificed_legs(duty, swings, gait_valid_relaxed_hold=True)
        else:
            sac = []
        rec["sacrificed_legs"] = sac
        rec["gait_valid"] = not sac
        rec["converged"] = (rec["err_q4_mean_rad"] is not None
                            and rec["err_q4_mean_rad"] <= 0.05)
        rec["success"] = (rec["fall"] is None and rec["gait_valid"]
                          and rec["converged"])
        return rec, (capture_physical_state(env_turn)
                     if rec["fall"] is None else None)

    offsets = (OFFSET_SET_DEG if args.turn_offset_deg is None
              else [args.turn_offset_deg])
    results = {
        "walk_ckpt": str(args.walk), "turn_ckpt": str(args.turn),
        "compat": compat, "cycles": args.cycles, "speed": args.speed,
        "turn_episode_s": args.turn_episode_s,
        "deterministic": deterministic, "episodes": [],
    }
    off_i = 0
    for ep in range(args.episodes):
        ep_seed = args.seed + ep
        segs = []
        state = None
        zero_fall = True
        for c in range(args.cycles):
            fwd_rec, state = run_forward(state, ep_seed)
            fwd_rec["seg"] = "forward"
            segs.append(fwd_rec)
            if want_strips and ep == 0:
                save_strip(f"ep0_cycle{c}_forward")
            if state is None:
                zero_fall = False
                break
            offset_deg = offsets[off_i % len(offsets)]
            off_i += 1
            turn_rec, state = run_turn(state, ep_seed, offset_deg)
            turn_rec["seg"] = "turn"
            segs.append(turn_rec)
            if want_strips and ep == 0:
                save_strip(f"ep0_cycle{c}_turn")
            if state is None:
                zero_fall = False
                break
        results["episodes"].append({
            "episode": ep, "zero_fall": zero_fall, "segments": segs,
        })
        print(f"[walk_turn_compose] ep{ep} zero_fall={zero_fall} "
              f"segs={[(s['seg'], s['success']) for s in segs]}")

    n_ep = len(results["episodes"])
    zero_fall_n = sum(e["zero_fall"] for e in results["episodes"])
    fwd_segs = [s for e in results["episodes"] for s in e["segments"]
               if s["seg"] == "forward"]
    turn_segs = [s for e in results["episodes"] for s in e["segments"]
                if s["seg"] == "turn"]
    results["summary"] = {
        "zero_fall_episodes": f"{zero_fall_n}/{n_ep}",
        "forward_success": f"{sum(s['success'] for s in fwd_segs)}/"
                           f"{len(fwd_segs)}",
        "turn_success": f"{sum(s['success'] for s in turn_segs)}/"
                        f"{len(turn_segs)}",
        "forward_gait_valid": f"{sum(s['gait_valid'] for s in fwd_segs)}/"
                              f"{len(fwd_segs)}",
        "turn_gait_valid": f"{sum(s['gait_valid'] for s in turn_segs)}/"
                           f"{len(turn_segs)}",
        "turn_converged": f"{sum(s['converged'] for s in turn_segs)}/"
                          f"{len(turn_segs)}",
    }
    print(f"[walk_turn_compose] SUMMARY {results['summary']}")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, indent=2))
        print(f"[walk_turn_compose] wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
