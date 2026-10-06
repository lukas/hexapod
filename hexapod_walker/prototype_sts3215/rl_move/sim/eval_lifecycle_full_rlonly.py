"""`rl_only` FULL-LIFECYCLE composition: rise+hold -> WALK -> TURN-and-
hold -> LOWER, four SEPARATELY trained clean-RL checkpoints chained in
one session via role-selection plumbing (RL_GOALS.md's allowed
non-motion category), zero new training.

THE GAP THIS CLOSES (named in both STATUS.md -- the cross-track Goal
readiness digest -- and walkcurr/STATUS.md's "Now" section as of
2026-10-06): `bundle_rlonly_lifecycle_v2` chains rise+hold->walk->lower
(no turn); `bundle_rlonly_curvewalk_v1` chains walk<->turn (no
rise/lower). Nobody had ever run all four roles back to back in one
session -- this script is that session, built from the two existing,
already-validated pairwise tools' own precedent rather than new
mechanism: `eval_lifecycle_handoff_rlonly.py`'s rise->walk cross-env
reanchor trick (`PhysicalState`/`capture_physical_state`/
`apply_physical_state`, imported not re-derived) generalizes to
walk->turn and turn->lower exactly the way `eval_walk_turn_compose.py`
already generalized it to walk<->turn. No env/reward code is touched;
this is pure external orchestration of four frozen policies.

WHY FOUR ENV INSTANCES: each role's own training recipe pins different
actuator/safety/task cfg (box_yaw, term_penalty, safety.max_delta_q_deg,
safety.hip_pitch_max_deg, motor.thermal_derate_*, ...) that
SimServoParams/SafetyLayer cache at env `__init__` and cannot hot-swap
mid-episode on one live env -- same rationale both precedent tools
state in their own docstrings. At each segment boundary the raw
PHYSICAL state (qpos/qvel/ctrl/act + the safety layer's slew memory)
is copied across; nothing is ever teleported or scripted.

Per-segment criteria (reused verbatim from each role's own established
gate, not re-derived):
  rise   `env.plant_report()` (`eval_lifecycle_handoff_rlonly`'s own
         rise bar).
  walk   tracking error + `gait_valid` (`sacrificed_legs`, strict --
         no relaxed-hold).
  turn   terminal-quartile |walk_yaw_offset_err| <= 0.05 rad (the acq5
         gate's own bar) + `gait_valid` with `gait_valid_relaxed_hold`
         (a converged hold legitimately stops swinging some/all legs).
  lower  not terminated AND |height_err_end_mm| <= 15 (the lower
         role's own established `lower_ok` bar, same formula
         `eval_lifecycle_handoff_rlonly.lower_phase` uses without that
         tool's optional forensics instrumentation -- out of scope
         here, this script answers "does the FULL chain survive",
         forensics on any one role still live on their own tool).
Whole-session: zero_fall across all four segments.

DEFAULT CHECKPOINTS are the current standing champions as of
2026-10-06 (see STATUS.md / walkcurr STATUS.md / todaypolicy STATUS.md):
  stance rl_move/sim/policies/ppo_goal_cw_stance50hz_rlonly_currentcap29_s5_klrollback05_acq15m.zip
  walk   rl_move/sim/policies/ppo_goal_cw_walk50hz_slew_smooth_s0.zip (--walk-recipe slew_smooth_s0 --rot60)
  turn   rl_move/sim/policies/ppo_goal_cw_walkyaw50hz_rlonly_scratch_sac_s5_acq5_seedsweep_hippitchfix_ft1.zip
         (the post-regression-fix checkpoint; see
         rl_docs/tracks/walkcurr/curvewalk_turnhold_hippitchmax_regression_2026-10-06/SUMMARY.md)
  lower  rl_move/sim/policies/ppo_goal_cw_stance50hz_rlonly_lowerrole_scratch_sac_s2_drramp_thermalderate50_acq1.zip
         (--lower-cfg motor.thermal_derate_enable=1 --lower-cfg motor.thermal_derate_max_frac=0.5,
         replaying the candidate's own training delta, same convention
         `pod_eval.lifecycle_lower_cfg_delta` already established)

Usage (first full-chain read, zero GPU spend):
    uv run python -m rl_move.sim.eval_lifecycle_full_rlonly \
        --episodes 12 --out logs/ckpt_eval/lifecycle_full_rlonly_v1_det.json
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

from .eval_lifecycle_handoff_rlonly import (
    PHASE_A_S,
    PhysicalState,
    _build_env,
    _compose_lower_cfg_args,
    _set_mix,
    apply_physical_state,
    capture_physical_state,
    heading_to_vxvy,
    sacrificed_legs,
    schedule,
)

DEFAULT_STANCE = Path("rl_move/sim/policies/"
                      "ppo_goal_cw_stance50hz_rlonly_currentcap29_s5_"
                      "klrollback05_acq15m.zip")
DEFAULT_WALK = Path("rl_move/sim/policies/ppo_goal_cw_walk50hz_slew_smooth_s0.zip")
DEFAULT_TURN = Path("rl_move/sim/policies/"
                    "ppo_goal_cw_walkyaw50hz_rlonly_scratch_sac_s5_"
                    "acq5_seedsweep_hippitchfix_ft1.zip")
DEFAULT_LOWER = Path("rl_move/sim/policies/"
                     "ppo_goal_cw_stance50hz_rlonly_lowerrole_scratch_"
                     "sac_s2_drramp_thermalderate50_acq1.zip")


def summarize_segments(episodes: list) -> dict:
    """Pure aggregation over this script's own per-episode `segments`
    records (list of dicts with `seg` in {rise,walk,turn,lower} and a
    `success`/`fall` key each) -- factored out so it is unit-testable
    without mujoco/a real session (same convention as
    `eval_mixed_session.aggregate_session`)."""
    n_ep = len(episodes)
    zero_fall = sum(1 for e in episodes if e.get("zero_fall"))
    out = {"episodes": n_ep, "zero_fall_episodes": f"{zero_fall}/{n_ep}"}
    for seg_name in ("rise", "walk", "turn", "lower"):
        segs = [s for e in episodes for s in e["segments"]
                if s["seg"] == seg_name]
        if not segs:
            continue
        out[f"{seg_name}_reached"] = len(segs)
        out[f"{seg_name}_success"] = sum(
            1 for s in segs if s.get("success"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stance", type=Path, default=DEFAULT_STANCE)
    ap.add_argument("--walk", type=Path, default=DEFAULT_WALK)
    ap.add_argument("--turn", type=Path, default=DEFAULT_TURN,
                    help="pass --turn '' (empty) to skip the turn "
                         "segment entirely (rise->walk->lower only, "
                         "matching bundle_rlonly_lifecycle_v2's own "
                         "chain for an apples-to-apples lower_ok read)")
    ap.add_argument("--lower", type=Path, default=DEFAULT_LOWER,
                    help="pass --lower '' (empty) to skip the lower "
                         "segment (rise->walk->turn only, matching "
                         "bundle_rlonly_curvewalk_v1's own chain)")
    ap.add_argument("--walk-recipe", choices=("rlonly_v2", "slew_smooth_s0"),
                    default="slew_smooth_s0")
    ap.add_argument("--turn-recipe", choices=("acq5_seedsweep",),
                    default="acq5_seedsweep")
    ap.add_argument("--lower-recipe", choices=("lowerrole_sac_drramp",),
                    default="lowerrole_sac_drramp")
    ap.add_argument("--rot60", action="store_true", default=True,
                    help="wrap the WALK policy in rot60.Rot60Policy "
                         "(default ON here -- the slew_smooth_s0 "
                         "default walk checkpoint's own validated "
                         "full-direction composition convention; pass "
                         "--no-rot60 to disable)")
    ap.add_argument("--no-rot60", dest="rot60", action="store_false")
    ap.add_argument("--episodes", type=int, default=12)
    ap.add_argument("--speed", type=float, default=0.06)
    ap.add_argument("--heading-deg", type=float, default=0.0)
    ap.add_argument("--hold-s", type=float, default=6.0)
    ap.add_argument("--settle-grounded-s", type=float, default=1.0,
                    help="extend the walk segment's stop phase (up to "
                         "this many extra seconds) until all six feet "
                         "register contact on the same tick, same fix "
                         "eval_walk_turn_compose.py uses before "
                         "handing off to the turn specialist (default "
                         "1.0, matches the registered slewsmooth+"
                         "hippitchfix-ft1 recheck; 0.0 = off)")
    ap.add_argument("--turn-offset-deg", type=float, default=None,
                    help="fixed turn target (default None = cycle "
                         "through the turn checkpoint's own trained "
                         "OFFSET_SET_DEG, one per episode)")
    ap.add_argument("--turn-episode-s", type=float, default=20.0)
    ap.add_argument("--lower-episode-s", type=float, default=15.0)
    ap.add_argument("--walk-cfg", action="append", default=None)
    ap.add_argument("--turn-cfg", action="append", default=None)
    ap.add_argument("--lower-cfg", action="append", default=None,
                    help="EXTRA cfg-set override(s) for env_lower, same "
                         "append convention as eval_lifecycle_handoff_"
                         "rlonly.py's --lower-cfg. Default None: if "
                         "--lower is left at DEFAULT_LOWER this still "
                         "gets the thermalderate50 champion's own "
                         "training delta auto-applied below (a physics "
                         "key that MUST be replayed at eval or the "
                         "champion runs under the wrong actuator model "
                         "and over_current-fails -- the exact "
                         "holdonly100-class eval/train cfg-mismatch "
                         "confound this track already root-caused once; "
                         "found again right here, 2026-10-06, smoke-"
                         "testing this tool before trusting its first "
                         "real numbers). Pass an explicit --lower-cfg "
                         "to fully control the override list when using "
                         "a DIFFERENT --lower checkpoint.")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--stochastic", action="store_true")
    ap.add_argument("--strips", type=Path, default=None,
                    help="dir for one combined 1fps strip spanning all "
                         "four segments, episode 0 only")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    if args.lower_cfg is None and str(args.lower) == str(DEFAULT_LOWER):
        # Replay the thermalderate50-s2 champion's own training delta
        # (see --lower-cfg help) -- without this the champion runs
        # under the shared-default actuator model it was NOT trained
        # with and over_current-fails most episodes (confirmed
        # 2026-10-06 smoke-testing this exact gap before trusting a
        # real number: 5/36 -> re-verify after this fix).
        args.lower_cfg = ["motor.thermal_derate_enable=1",
                          "motor.thermal_derate_max_frac=0.5"]

    import mujoco

    from rl_move.env import build_obs
    from .eval_checkpoint import _sacrificed_legs
    from .gru_policy import load_checkpoint_auto, wrap_recurrent_predictor
    from .probe_currentcap29_flatonly import (
        BASE_CFG_ARGS, FLATONLY_OVERRIDE_ARGS,
    )

    want_turn = str(args.turn) not in ("", ".")
    want_lower = str(args.lower) not in ("", ".")

    if args.walk_recipe == "slew_smooth_s0":
        from .cfg_recipe_walk50hz_slew_smooth_s0 import CFG_ARGS as WALK_ARGS
    else:
        from .cfg_recipe_walk50hz_rlonly_v2 import CFG_ARGS as WALK_ARGS
    if want_turn:
        from .cfg_recipe_walkyaw50hz_acq5_seedsweep import (
            CFG_ARGS as TURN_ARGS, OFFSET_SET_DEG,
        )
    if want_lower:
        from .cfg_recipe_stance50hz_rlonly_lowerrole_scratch_sac_drramp \
            import CFG_ARGS as LOWER_ARGS

    stance_cfg_args = list(BASE_CFG_ARGS) + list(FLATONLY_OVERRIDE_ARGS)
    want_strips = args.strips is not None

    env_rise = _build_env(stance_cfg_args, episode_seconds=15.0,
                          seed=args.seed, render=want_strips)
    walk_episode_s = (1.0 + args.hold_s + 2.0
                      + max(0.0, args.settle_grounded_s) + 2.0)
    env_walk = _build_env(_compose_lower_cfg_args(WALK_ARGS, args.walk_cfg),
                          episode_seconds=walk_episode_s,
                          seed=args.seed, render=want_strips)
    env_turn = (_build_env(_compose_lower_cfg_args(TURN_ARGS, args.turn_cfg),
                           episode_seconds=args.turn_episode_s + 2.0,
                           seed=args.seed, render=want_strips)
               if want_turn else None)
    env_lower = (_build_env(_compose_lower_cfg_args(LOWER_ARGS, args.lower_cfg),
                            episode_seconds=args.lower_episode_s,
                            seed=args.seed, render=want_strips)
                if want_lower else None)

    stance = wrap_recurrent_predictor(
        load_checkpoint_auto(args.stance, device="cpu"))
    walk = wrap_recurrent_predictor(load_checkpoint_auto(args.walk, device="cpu"))
    if args.rot60:
        from .rot60 import Rot60Policy
        walk = Rot60Policy(walk)
    turn = (wrap_recurrent_predictor(load_checkpoint_auto(args.turn, device="cpu"))
           if want_turn else None)
    lower = (wrap_recurrent_predictor(load_checkpoint_auto(args.lower, device="cpu"))
            if want_lower else None)

    n_stance = int(stance.observation_space.shape[0])
    n_turn = int(turn.observation_space.shape[0]) if want_turn else None
    n_lower = int(lower.observation_space.shape[0]) if want_lower else None
    deterministic = not args.stochastic
    pads_walk = [env_walk.model.body(f"L{i}_pad").id for i in range(6)]
    pads_turn = ([env_turn.model.body(f"L{i}_pad").id for i in range(6)]
                if want_turn else None)

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
        imageio.imwrite(args.strips / f"{name}.png", np.hstack(strip_frames))
        strip_frames.clear()

    def reanchor(env, state: PhysicalState | None, seed: int):
        gen = env._goal_gen
        _set_mix(gen, walk=1.0)
        env.reset(seed=seed)
        if state is not None:
            apply_physical_state(env, state)
            mujoco.mj_forward(env.model, env.data)
            env._state = env._read_state()
        return env._final_obs(
            build_obs(env.cfg, env._state, env._q_nom, env._prev_action,
                      goal=env._current_goal(), tilt_ref=env._tilt_ref0),
            reset=True)

    def rise_phase(ep_seed: int):
        gen = env_rise._goal_gen
        _set_mix(gen, rise=1.0)
        gen.force_rise_start = "flat"
        obs, _ = env_rise.reset(seed=ep_seed)
        gen.force_rise_start = None
        for _ in range(int(round(PHASE_A_S / env_rise.dt))):
            a, _ = stance.predict(obs[:n_stance], deterministic=deterministic)
            obs, _rw, term, trunc, info = env_rise.step(a)
            grab(env_rise)
            if term or trunc:
                return ({"seg": "rise", "fall": str(
                    info.get("termination_reason") or "end"),
                    "success": False}, None)
        h_err = (float(env_rise.data.xpos[env_rise._chassis_bid, 2])
                 - (env_rise._z0 + env_rise._h_target))
        ok, _detail = env_rise.plant_report(height_err_m=h_err)
        return ({"seg": "rise", "fall": None, "success": bool(ok),
                 "height_err_mm": round(h_err * 1000.0, 1)},
                capture_physical_state(env_rise))

    def walk_phase(state: PhysicalState, ep_seed: int):
        obs = reanchor(env_walk, state, ep_seed)
        if hasattr(walk, "reset"):
            walk.reset()
        traj = env_walk._goal_traj
        rec = {"seg": "walk", "fall": None, "trk_err": 0.0}
        n_err = 0
        contact_hist, pad_xy_hist = [], []
        cmd_vx, cmd_vy = heading_to_vxvy(args.speed, args.heading_deg)
        for seconds, vx, vy in schedule(cmd_vx, cmd_vy, args.hold_s):
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
                    float(env_walk.data.sensordata[adr]) > 0.5
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
        if not rec["fall"] and args.settle_grounded_s > 0.0:
            settle_ticks = max(1, int(round(
                args.settle_grounded_s / env_walk.dt)))
            for _ in range(settle_ticks):
                if hasattr(traj, "vx"):
                    traj.vx[:] = 0.0
                    traj.vy[:] = 0.0
                if getattr(traj, "wz", None) is not None:
                    traj.wz[:] = 0.0
                a, _ = walk.predict(obs, deterministic=deterministic)
                obs, _rw, term, trunc, info = env_walk.step(a)
                grab(env_walk)
                tick_contact = [
                    float(env_walk.data.sensordata[adr]) > 0.5
                    for adr in env_walk._touch_adr]
                contact_hist.append(tick_contact)
                pad_xy_hist.append(
                    [env_walk.data.xpos[b, :2].copy() for b in pads_walk])
                if term or trunc:
                    rec["fall"] = str(
                        info.get("termination_reason") or "episode_end")
                    break
                if all(tick_contact):
                    break
        rec["trk_err"] = round(rec["trk_err"] / max(n_err, 1), 4)
        contact = np.asarray(contact_hist, dtype=bool)
        pad_xy = np.asarray(pad_xy_hist)
        sac = sacrificed_legs(contact, pad_xy) if len(contact_hist) > 1 else []
        rec["sacrificed_legs"] = sac
        rec["gait_valid"] = not sac
        rec["success"] = rec["fall"] is None and rec["gait_valid"]
        return rec, (capture_physical_state(env_walk)
                    if rec["fall"] is None else None)

    def turn_phase(state: PhysicalState, ep_seed: int, offset_deg: float):
        obs = reanchor(env_turn, state, ep_seed)
        if hasattr(turn, "reset"):
            turn.reset()
        traj = env_turn._goal_traj
        delta = math.radians(offset_deg)
        n_steps = max(1, int(round(args.turn_episode_s / env_turn.dt)))
        errs = []
        contact_hist = []
        rec = {"seg": "turn", "fall": None, "target_deg": offset_deg}
        for _ in range(n_steps):
            if hasattr(traj, "vx"):
                traj.vx[:] = 0.0
                traj.vy[:] = 0.0
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
                rec["fall"] = str(
                    info.get("termination_reason") or "episode_end")
                break
        q4 = errs[-max(1, len(errs) // 4):] if errs else []
        rec["err_q4_mean_rad"] = round(float(np.mean(q4)), 4) if q4 else None
        contact = np.asarray(contact_hist, dtype=bool)
        if len(contact_hist) > 1:
            duty = contact.mean(axis=0)
            swings = [int(np.sum(np.diff(contact[:, f].astype(int)) == -1))
                      for f in range(6)]
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

    def lower_phase(state: PhysicalState, ep_seed: int):
        gen = env_lower._goal_gen
        _set_mix(gen, lower=1.0)
        env_lower.reset(seed=ep_seed)
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
        return {"seg": "lower", "fall": fall, "height_err_end_mm": h_err_mm,
                "success": bool(lower_ok)}, None

    offsets = (OFFSET_SET_DEG if (want_turn and args.turn_offset_deg is None)
              else ([args.turn_offset_deg] if want_turn else []))
    episodes_out = []
    off_i = 0
    for ep in range(args.episodes):
        ep_seed = args.seed + ep
        name = f"ep{ep}"
        strip_frames.clear()
        segs = []
        zero_fall = True
        rep, state = rise_phase(ep_seed)
        segs.append(rep)
        if state is not None:
            rep, state = walk_phase(state, ep_seed)
            segs.append(rep)
        else:
            zero_fall = False
        if state is not None and want_turn:
            offset_deg = offsets[off_i % len(offsets)]
            off_i += 1
            rep, state = turn_phase(state, ep_seed, offset_deg)
            segs.append(rep)
        if state is None:
            zero_fall = False
        if state is not None and want_lower:
            rep, _ = lower_phase(state, ep_seed)
            segs.append(rep)
            if not rep["success"]:
                zero_fall = False
        if want_strips and ep == 0:
            save_strip(name)
        episodes_out.append({"episode": ep, "zero_fall": zero_fall,
                             "segments": segs})
        print(f"[lifecycle_full] {name} zero_fall={zero_fall} "
              f"segs={[(s['seg'], s.get('success')) for s in segs]}")

    summary = summarize_segments(episodes_out)
    results = {
        "stance": str(args.stance), "walk": str(args.walk),
        "turn": (str(args.turn) if want_turn else None),
        "lower": (str(args.lower) if want_lower else None),
        "walk_recipe": args.walk_recipe, "rot60": bool(args.rot60),
        "settle_grounded_s": args.settle_grounded_s,
        "heading_deg": args.heading_deg, "speed": args.speed,
        "deterministic": deterministic,
        "episodes": episodes_out, "summary": summary,
    }
    print(f"[lifecycle_full] SUMMARY {summary}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, indent=2))
        print(f"[lifecycle_full] wrote {args.out}")
    clean = summary["zero_fall_episodes"].split("/")
    return 0 if clean[0] == clean[1] else 1


if __name__ == "__main__":
    raise SystemExit(main())
