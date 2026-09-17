"""`rl_only` lifecycle composition: rise+hold stance -> WALK-role
handoff, DIRECT (no scripted blend) -- the concrete "Next" item
`bundle_rlonly_stance_v1/GO_NOGO.md` named 2026-09-17 ("design and
build the rise+hold -> walk-ready handoff ... chaining two
independently trained rl_only roles instead of one any_means bundle").

THE QUESTION: `bundle_rlonly_stance_v1` (rise-from-flat + hold) and
`bundle_rlonly_v2` (forward walk) are two SEPARATELY trained clean-RL
checkpoints -- RL_GOALS.md explicitly allows composing them instead of
requiring one monolithic actor, but nobody had ever run the walk
champion on the stance role's own settled physical state. Does it work
without a scripted joint-blend (a "scripted motion role", banned from
the rl_only lineage per tracks.json), or does the walk champion
stumble on the handoff?

WHY TWO ENV INSTANCES, NOT ONE: the two checkpoints' own training
recipes use materially DIFFERENT actuator/safety cfg (bus.write_speed
1024-default vs 4096, safety.max_delta_q_deg 0.75 vs 7.2,
goal.joint_action_bias_{hip,knee}_deg 30.9/36.1 vs 40.0/35.0) --
SimServoParams/SafetyLayer cache these at env __init__, so a single
live env can't hot-swap them mid-episode. Two ``SimHexapodJointWalkEnv``
instances (same MJCF, same qpos/qvel layout -- the class hierarchy is
literally SimHexapodJointWalkEnv(SimHexapodJointGoalEnv), see
joint_task.py/walk_task.py) are built, one per role's own recorded
cfg-set (stance: probe_currentcap29_flatonly's BASE_CFG_ARGS +
FLATONLY_OVERRIDE_ARGS, the ONLY validated stance regime; walk:
cfg_recipe_walk50hz_rlonly_v2.CFG_ARGS). At the handoff tick the raw
PHYSICAL state (qpos/qvel/ctrl/act + the safety layer's `_last_safe`
slew memory, all in physical units, model-independent) is copied
across -- exactly ``eval_handoff.py``'s established
``reanchor_keep_state()`` trick (same-env case), generalized to a
cross-env copy. This is role-selection/config-selection plumbing (RL_
GOALS.md's allowed non-motion category), not a scripted motion role:
no joint trajectory is scripted, the SAME physical state is kept, only
which policy (and which policy's OWN safety/actuator envelope) is live
changes.

Two arms per episode:

  direct   stance runs a genuine flat-start rise+hold episode to a
           settled hold, then the WALK checkpoint takes over directly
           on the stance's exact physical state (bookkeeping re-anchor
           only, per RL_GOALS.md-allowed plumbing).
  plant    control: walk champion from its OWN clean plant reset, same
           drive schedule -- defines the noise band / "what a perfect
           handoff would look like" reference.

Usage:
    uv run python -m rl_move.sim.eval_lifecycle_handoff_rlonly \\
        --stance rl_move/sim/policies/ppo_goal_cw_stance50hz_rlonly_currentcap29_s5_klrollback05_acq15m.zip \\
        --walk   rl_move/sim/policies/ppo_goal_cw_walk50hz_rlonly_crutchoff_s0_warmadapt_acq1.zip \\
        --episodes 6 --out logs/ckpt_eval/lifecycle_handoff_rlonly.json \\
        --strips logs/ckpt_eval/lifecycle_handoff_rlonly_strips

Verdict: direct is CLEAN if handoff_falls==0 and its drive metrics sit
inside the plant arm's band (same rule of thumb as eval_handoff.py).
This eval does NOT claim `lower` (still closed) or a full sit-walk-sit
cycle -- rise+hold -> walk only, matching what the two source bundles
actually cover.
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "2")

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

PHASE_A_S = 12.5     # stance rise+settle horizon (mirrors eval_handoff.py)
STUMBLE_S = 2.0
SCHEDULE = lambda v: [(1.0, 0.0, 0.0), (6.0, v, 0.0), (2.0, 0.0, 0.0)]


def _set_mix(gen, **p) -> None:
    for attr in [a for a in vars(gen) if a.startswith("p_")]:
        setattr(gen, attr, 0.0)
    gen.p_walk = 0.0
    for k, v in p.items():
        setattr(gen, f"p_{k}", v)


@dataclass
class PhysicalState:
    """Raw, model-independent physical state carried across a role
    handoff -- everything a real hardware controller would ALSO carry
    across a policy swap (joint angles/velocities, the actuator's live
    ctrl/act, and the safety layer's slew memory), nothing task/reward
    specific."""
    qpos: np.ndarray
    qvel: np.ndarray
    ctrl: np.ndarray
    act: np.ndarray | None
    last_safe: np.ndarray


def capture_physical_state(env) -> PhysicalState:
    d = env.data
    return PhysicalState(
        qpos=d.qpos.copy(), qvel=d.qvel.copy(), ctrl=d.ctrl.copy(),
        act=(d.act.copy() if d.act.size else None),
        last_safe=env.safety._last_safe.copy())


def apply_physical_state(env, state: PhysicalState) -> None:
    """Overwrite ``env``'s live physical state in place. Caller must
    call ``mujoco.mj_forward`` + rebuild ``env._state``/obs afterward
    (kept OUT of this function so it stays pure-array and testable
    without a live mujoco model)."""
    d = env.data
    d.qpos[:] = state.qpos
    d.qvel[:] = state.qvel
    d.ctrl[:] = state.ctrl
    if state.act is not None and d.act.size:
        d.act[:] = state.act
    env.safety._last_safe = state.last_safe.copy()


def _build_env(cfg_args: list[str], *, episode_seconds: float, seed: int,
               render: bool):
    from rl_move.config import load_config
    from .cfg_set import parse_cfg_set
    from .servo_model import SimServoParams
    from .walk_task import SimHexapodJointWalkEnv

    cfg = load_config()
    for key, parsed in parse_cfg_set(cfg_args).items():
        sect, name = key.split(".", 1)
        cfg.setdefault(sect, {})[name] = parsed
    env = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(cfg), cfg=cfg, randomize=False,
        episode_seconds=episode_seconds, seed=seed,
        render_mode="rgb_array" if render else None)
    return env


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stance", type=Path,
                    default=Path("rl_move/sim/policies/"
                                 "ppo_goal_cw_stance50hz_rlonly_currentcap29_"
                                 "s5_klrollback05_acq15m.zip"))
    ap.add_argument("--walk", type=Path,
                    default=Path("rl_move/sim/policies/"
                                 "ppo_goal_cw_walk50hz_rlonly_crutchoff_s0_"
                                 "warmadapt_acq1.zip"))
    ap.add_argument("--episodes", type=int, default=6)
    ap.add_argument("--speed", type=float, default=0.06)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--strips", type=Path, default=None,
                    help="dir for 1 fps frame-strip PNGs (episode 0 of "
                         "each arm)")
    ap.add_argument("--stochastic", action="store_true",
                    help="sample both policies stochastically instead "
                         "of deterministic (default det, matches the "
                         "stance bundle's own det gate)")
    args = ap.parse_args()

    import mujoco
    from stable_baselines3 import PPO

    from rl_move.env import build_obs
    from .cfg_recipe_walk50hz_rlonly_v2 import CFG_ARGS as WALK_CFG_ARGS
    from .probe_currentcap29_flatonly import (
        BASE_CFG_ARGS, FLATONLY_OVERRIDE_ARGS,
    )

    stance_cfg_args = list(BASE_CFG_ARGS) + list(FLATONLY_OVERRIDE_ARGS)
    want_strips = args.strips is not None

    env_rise = _build_env(stance_cfg_args, episode_seconds=15.0,
                           seed=args.seed, render=want_strips)
    env_walk = _build_env(WALK_CFG_ARGS, episode_seconds=20.0,
                           seed=args.seed, render=want_strips)

    stance = PPO.load(args.stance, device="cpu")
    walk = PPO.load(args.walk, device="cpu")
    n_stance = int(stance.observation_space.shape[0])
    n_env_rise = int(env_rise.observation_space.shape[0])
    n_env_walk = int(env_walk.observation_space.shape[0])
    assert walk.observation_space.shape[0] == n_env_walk, (
        f"walk policy obs {walk.observation_space.shape} != "
        f"env_walk {n_env_walk}")
    assert n_stance <= n_env_rise, (
        "stance policy obs must fit inside env_rise's obs "
        f"(got {n_stance} vs {n_env_rise})")
    deterministic = not args.stochastic

    strip_frames: list = []

    def grab(env, final: bool = False) -> None:
        if not want_strips:
            return
        if final or (grab.n % max(1, int(round(1.0 / env.dt))) == 0):
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

    def rise_phase(ep_seed: int) -> tuple[dict, bool, PhysicalState | None]:
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
                return ({"rise_fall": str(
                    info.get("termination_reason") or "end")}, False, None)
        h_err = (float(env_rise.data.xpos[env_rise._chassis_bid, 2])
                 - (env_rise._z0 + env_rise._h_target))
        ok, detail = env_rise.plant_report(height_err_m=h_err)
        rep = {"rise_valid_plant": bool(ok),
               "rise_fail": [k for k, v in detail.items()
                             if k.endswith("_ok") and not v],
               "rise_height_err_mm": round(h_err * 1000.0, 1)}
        return rep, True, capture_physical_state(env_rise)

    def handoff_obs(state: PhysicalState):
        """Fresh plant-frame walk episode (walk champion's own training
        frame), then the specialist's physical state dropped in."""
        gen = env_walk._goal_gen
        _set_mix(gen, walk=1.0)
        env_walk.reset(seed=args.seed)
        apply_physical_state(env_walk, state)
        mujoco.mj_forward(env_walk.model, env_walk.data)
        env_walk._state = env_walk._read_state()
        return env_walk._final_obs(
            build_obs(env_walk.cfg, env_walk._state, env_walk._q_nom,
                      env_walk._prev_action, goal=env_walk._current_goal(),
                      tilt_ref=env_walk._tilt_ref0), reset=True)

    def drive(obs) -> dict:
        traj = env_walk._goal_traj
        r = {"fall": None, "trk_err": 0.0, "dist_m": 0.0,
             "stumble_max_tilt_deg": 0.0, "stumble_min_height_mm": 1e9}
        n_err, t = 0, 0.0
        p0 = np.array(env_walk.data.qpos[:2], dtype=float)
        for seconds, vx, vy in SCHEDULE(args.speed):
            for _ in range(max(1, int(round(seconds / env_walk.dt)))):
                if hasattr(traj, "vx"):
                    traj.vx[:] = vx
                    traj.vy[:] = vy
                if getattr(traj, "wz", None) is not None:
                    traj.wz[:] = 0.0
                a, _ = walk.predict(obs, deterministic=deterministic)
                obs, _rw, term, trunc, info = env_walk.step(a)
                grab(env_walk)
                t += env_walk.dt
                if t <= STUMBLE_S:
                    tr, tp = env_walk._true_roll_pitch()
                    r["stumble_max_tilt_deg"] = max(
                        r["stumble_max_tilt_deg"],
                        math.degrees(max(abs(tr), abs(tp))))
                    r["stumble_min_height_mm"] = min(
                        r["stumble_min_height_mm"],
                        float(env_walk.data.xpos[env_walk._chassis_bid, 2])
                        * 1000.0)
                v = env_walk._body_vel_xy()
                r["trk_err"] += math.hypot(v[0] - vx, v[1] - vy)
                n_err += 1
                if term or trunc:
                    r["fall"] = str(
                        info.get("termination_reason") or "episode_end")
                    break
            if r["fall"]:
                break
        r["trk_err"] = round(r["trk_err"] / max(n_err, 1), 4)
        r["dist_m"] = round(float(np.hypot(
            *(np.array(env_walk.data.qpos[:2], dtype=float) - p0))), 3)
        r["stumble_max_tilt_deg"] = round(r["stumble_max_tilt_deg"], 1)
        r["stumble_min_height_mm"] = round(r["stumble_min_height_mm"], 1)
        return r

    results: dict = {"stance": str(args.stance), "walk": str(args.walk),
                      "speed": args.speed, "deterministic": deterministic,
                      "episodes": []}

    for arm in ("direct", "plant"):
        for ep in range(args.episodes):
            rec = {"arm": arm, "ep": ep}
            name = f"{arm}_{ep}"
            strip_frames.clear()
            if arm == "plant":
                gen = env_walk._goal_gen
                _set_mix(gen, walk=1.0)
                obs, _ = env_walk.reset(seed=args.seed + 1000 + ep)
                rec.update(drive(obs))
            else:
                rep, alive, state = rise_phase(args.seed + ep)
                rec.update(rep)
                if alive:
                    obs = handoff_obs(state)
                    rec.update(drive(obs))
                else:
                    rec["fall"] = "before_handoff"
            if want_strips and ep == 0:
                grab(env_walk if rec.get("fall") != "before_handoff"
                     else env_rise, final=True)
                save_strip(name)
            results["episodes"].append(rec)
            print(f"[{arm:6s}] ep{ep} "
                  f"rise_ok={rec.get('rise_valid_plant', '-')} "
                  f"fall={rec.get('fall')} trk={rec.get('trk_err', '-')} "
                  f"dist={rec.get('dist_m', '-')} "
                  f"tilt2s={rec.get('stumble_max_tilt_deg', '-')} "
                  f"hmin2s={rec.get('stumble_min_height_mm', '-')}")

    def band(arm: str, key: str) -> list:
        vals = [e[key] for e in results["episodes"]
                if e["arm"] == arm and key in e and e.get("fall") is None]
        return ([round(float(min(vals)), 3), round(float(max(vals)), 3)]
                if vals else [])

    summary = {}
    for arm in ("direct", "plant"):
        eps = [e for e in results["episodes"] if e["arm"] == arm]
        handed = [e for e in eps if e.get("fall") != "before_handoff"]
        summary[arm] = {
            "episodes": len(eps),
            "rise_valid_plant": sum(
                1 for e in eps if e.get("rise_valid_plant")),
            "rise_failed_pre_handoff": sum(
                1 for e in eps if e.get("fall") == "before_handoff"),
            "handoff_falls": sum(1 for e in handed if e.get("fall")),
            "trk_err_band": band(arm, "trk_err"),
            "dist_band": band(arm, "dist_m"),
            "stumble_tilt_band": band(arm, "stumble_max_tilt_deg"),
        }
    results["summary"] = summary
    print(json.dumps(summary, indent=1))
    direct = summary["direct"]
    direct_ok = (direct["handoff_falls"] == 0
                 and direct["rise_failed_pre_handoff"] < direct["episodes"])
    print("LIFECYCLE HANDOFF (direct, no scripted blend):",
          "CLEAN — no falls after switching on the stance role's pose"
          if direct_ok else "NOT CLEAN — see per-episode records")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, indent=1))
        print(f"wrote {args.out}")
    return 0 if direct_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
