"""probe_turn_pipeline.py — WHERE along the control pipeline is commanded
motion lost? (todaypolicy steering diagnostic, 2026-09-08)

Plain English: the corrected frozen turn audit (99bb5c01,
artifacts/rl_watchdog/turnauth_corrected_20260907) showed BOTH learned
policies AND the scripted controller substantially undertrack combined
forward/yaw commands (arc +-0.15 @ vx=0.08 achieves only ~0.064 rad/s),
and even pure forward tracks ~50%. This probe walks the whole chain —
desired foot trajectory -> IK joint target -> post-SafetyLayer command
-> measured joint response -> actual foot-vs-body motion -> body twist —
and fits the implied planar body twist (vx, vy, wz) at every stage, so
the stage where the commanded twist collapses is measured, not inferred.

It also records per-joint-class commanded/achieved angular rates against
the RESOLVED servo profile-speed ceiling (sim_model.json fits carry
vel_max_deg_s ~= 30.76 deg/s = 350 counts/s sys-ID speed; the
SafetyLayer slew clip is 37.5 deg/s at the pinned 0.375 deg/tick@100Hz),
because the candidate mechanism under test is:

  MECHANISM HYPOTHESIS: all tangential (yaw-direction) foot motion flows
  through the leg's yaw servo alone (TripodGait IK gives hip/knee only
  radial/vertical roles), so the servo profile-speed ceiling times the
  yaw-frame moment arm (~0.071 m at WALK_PLANT) caps tangential foot
  speed at ~0.038 m/s — a SHARED vx+wz budget. Predicts: measured yaw
  joint speed pinned at ~0.537 rad/s in every saturated cell; achieved
  (vx, wz*r) proportionally scaled to the cap; raising the profile
  ceiling (bus.servo_vel_max_counts_s) recovers tracking while raising
  only the slew clip (already tried 09-04) does not.

Diagnostic only: read-only isolated tool, no shared-code changes, no
training, runs frozen checkpoints / the scripted TripodGait through
probe_turn_authority.make_env. Lever arms (--cfg-set overrides for the
profile ceiling / slew clip) are DIAGNOSTIC doses; the qualification
safety contract (0.375 deg/tick, operator order fb_20260824T174619)
is not touched by this tool's defaults.

Usage (from the prototype dir, pristine snapshot):
  python -m rl_move.sim.probe_turn_pipeline --policy scripted \
      --cells 0.08:0,0:0.3,0.08:0.15,0.08:-0.15 \
      --cfg-json spec_cfg.json --out out.json
"""
from __future__ import annotations

import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "2")

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

_RL = Path(__file__).resolve().parents[1]
_PROTO = _RL.parent
for _p in (_PROTO, _PROTO / "linux_control"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from rl_move.robot_state import DEG2RAD  # noqa: E402
from rl_move.sim import probe_turn_authority as pta  # noqa: E402
from rl_move.sim.eval_checkpoint import CONTACT_N, model_identity  # noqa: E402
from rl_move.sim.joint_task import q_rad_to_action  # noqa: E402
from rl_move.sim.servo_model import motor_contract  # noqa: E402

from hexapod_core.tripod_gait import (  # noqa: E402
    COXA, FEMUR, TIBIA, LEG_RADIAL, TripodGait)

RAD2DEG = 1.0 / DEG2RAD
LEG_ANGLES = [(i + 0.5) * math.pi / 3.0 for i in range(6)]


def fk_body_xy(q18: np.ndarray) -> np.ndarray:
    """Planar body-frame foot positions (6,2) from LOGICAL q
    (yaw, hip, knee-absolute-tibia per leg) using the same geometry
    TripodGait's IK targets (hexapod_core constants). Internally
    consistent across stages; the true-mesh check is the separate
    'pad' stage read straight from MuJoCo."""
    out = np.zeros((6, 2))
    for i, a in enumerate(LEG_ANGLES):
        yaw, hip, knee = q18[3 * i], q18[3 * i + 1], q18[3 * i + 2]
        reach = COXA + FEMUR * math.cos(hip) + TIBIA * math.cos(knee)
        th = a + yaw
        out[i, 0] = LEG_RADIAL * math.cos(a) + reach * math.cos(th)
        out[i, 1] = LEG_RADIAL * math.sin(a) + reach * math.sin(th)
    return out


def fk_body_z(q18: np.ndarray) -> np.ndarray:
    return np.array([
        -FEMUR * math.sin(q18[3 * i + 1]) - TIBIA * math.sin(q18[3 * i + 2])
        for i in range(6)])


def fit_twist(pos: np.ndarray, vel: np.ndarray, sel: np.ndarray):
    """LSQ planar twist from body-frame foot velocities of selected feet.

    No-slip stance kinematics: foot velocity relative to body
    f_dot = -(v + w x p). Returns (vx, vy, wz) or None if <2 feet."""
    idx = np.flatnonzero(sel)
    if len(idx) < 2:
        return None
    rows, rhs = [], []
    for f in idx:
        px, py = pos[f]
        rows.append([1.0, 0.0, -py]); rhs.append(-vel[f, 0])
        rows.append([0.0, 1.0, px]); rhs.append(-vel[f, 1])
    sol, *_ = np.linalg.lstsq(np.asarray(rows), np.asarray(rhs), rcond=None)
    return sol  # vx, vy, wz


def rollout(*, policy: str, model, model_obs_width, cfg_set: list[str],
            vx_cmd: float, wz_cmd: float, seed: int, episode_seconds: float,
            phase_offset: float = 0.0) -> dict:
    env = pta.make_env(cfg_set, seed, episode_seconds)
    if model_obs_width is not None:
        n_env = int(env.observation_space.shape[0])
        if model_obs_width != n_env:
            raise SystemExit(f"obs width {model_obs_width} != env {n_env}")
    identity = model_identity(env)
    if identity["model_variant"] != "full_mesh" or abs(env.dt - .01) > 1e-10:
        raise RuntimeError(f"requires full-mesh 100Hz: {identity} dt={env.dt}")
    obs, info = env.reset()
    if policy == "checkpoint" and hasattr(model, "reset"):
        model.reset()
    if phase_offset:
        env._phase = float(phase_offset) % (2 * math.pi)

    cap: dict = {}
    _orig_atq = env._act_to_q

    def _atq_rec(clipped):
        out = _orig_atq(clipped)
        cap["q_prop"] = np.asarray(out[0], dtype=float).copy()
        return out

    env._act_to_q = _atq_rec

    traj = env._goal_traj
    n = len(traj.vx)
    hold_n = ramp_n = int(round(1.0 / env.dt))
    traj.vx[:] = vx_cmd; traj.vy[:] = 0.0; traj.wz[:] = wz_cmd
    traj.vx[:hold_n] = 0.0; traj.wz[:hold_n] = 0.0
    traj.vx[hold_n:hold_n + ramp_n] = np.linspace(0.0, vx_cmd, ramp_n)
    traj.wz[hold_n:hold_n + ramp_n] = np.linspace(0.0, wz_cmd, ramp_n)

    gait = None
    if policy == "scripted":
        gait = TripodGait(vx=0.0)
        gait.sync_plant_stance(*pta.WALK_PLANT)
        gait.reset_phase(phase=phase_offset)

    rows = []
    step = 0
    fell = False
    try:
        while True:
            cmd_wz = float(traj.wz[min(step, n - 1)])
            cmd_vx = float(traj.vx[min(step, n - 1)])
            if policy == "scripted":
                t = step * env.dt
                gait.set_velocity(vx=cmd_vx, omega=cmd_wz)
                q_des = np.asarray(gait.desired_deg(t)) * DEG2RAD
                act = q_rad_to_action(q_des)
                plan_stance = np.array([not s for s in gait.leg_swing_state()])
                sm_cmd = (gait._vx_smooth, gait._om_smooth)
            else:
                act, _ = model.predict(obs, deterministic=True)
                q_des = None
                plan_stance = None
                sm_cmd = (cmd_vx, cmd_wz)
            obs, r, term, trunc, info = env.step(act)
            gm = info.get("goal_mode")
            if step >= hold_n + ramp_n and gm == "walk":
                d = env.data
                R = d.xmat[env._chassis_bid].reshape(3, 3)
                cx = d.xpos[env._chassis_bid]
                pads_w = d.xpos[env._pad_bids]
                pads_b = (pads_w - cx) @ R  # body-frame
                rows.append({
                    "q_des": q_des,
                    "q_prop": cap.get("q_prop"),
                    "q_safe": env.safety._last_safe.copy(),
                    "q_act": env._state.joint_position.copy(),
                    "plan_stance": plan_stance,
                    "contact": np.array([float(d.sensordata[x]) > CONTACT_N
                                          for x in env._touch_adr]),
                    "pads_b": pads_b.copy(),
                    "pads_wz": pads_w[:, 2].copy(),
                    "vx_body": float(env._body_vel_xy()[0]),
                    "wz_body": float(env._body_wz()),
                    "cmd": sm_cmd,
                })
            step += 1
            if term:
                fell = True
            if term or trunc:
                break
    finally:
        env._act_to_q = _orig_atq
        contract = motor_contract(env.cfg)
        env.close()

    dt = 0.01
    out = {"policy": policy, "vx_cmd": vx_cmd, "wz_cmd": wz_cmd,
           "seed": seed, "fell": fell, "n_scored_ticks": len(rows),
           "model_identity": identity, "motor_contract": contract}
    if len(rows) < 20:
        out["error"] = "insufficient scored ticks"
        return out

    stages = ["des", "prop", "safe", "act"] if policy == "scripted" else \
             ["prop", "safe", "act"]
    qs = {s: np.stack([r[f"q_{s}"] for r in rows]) for s in stages}
    pads = np.stack([r["pads_b"] for r in rows])          # (T,6,3->2?)
    pads_xy = pads[:, :, :2]
    contact = np.stack([r["contact"] for r in rows]).astype(bool)
    plan_st = (np.stack([r["plan_stance"] for r in rows]).astype(bool)
               if rows[0]["plan_stance"] is not None else None)

    # --- per-joint-class angular rates per stage -------------------------
    cls = {"yaw": [3 * l for l in range(6)],
           "hip": [3 * l + 1 for l in range(6)],
           "knee": [3 * l + 2 for l in range(6)]}
    vel_ceiling = float(contract["resolved_vel_max_deg_s_min"]) * DEG2RAD
    slew_rad_s = float(contract["slew_limit_deg_s"]) * DEG2RAD
    rates = {}
    for s in stages:
        dq = np.abs(np.diff(qs[s], axis=0)) / dt   # (T-1,18) rad/s
        rates[s] = {k: {"med": float(np.median(dq[:, i])),
                        "p90": float(np.percentile(dq[:, i], 90)),
                        "pinned_frac": float(np.mean(
                            dq[:, i] >= 0.95 * min(vel_ceiling, slew_rad_s)))}
                    for k, i in cls.items()}
    out["joint_rates_rad_s"] = rates
    out["resolved_vel_ceiling_rad_s"] = vel_ceiling
    out["slew_clip_rad_s"] = slew_rad_s

    # --- stage twists ----------------------------------------------------
    def stage_twists(pos_seq, sel_seq):
        fits = []
        for t in range(1, len(pos_seq)):
            sel = sel_seq[t] & sel_seq[t - 1]
            v = (pos_seq[t] - pos_seq[t - 1]) / dt
            f = fit_twist(pos_seq[t - 1], v, sel)
            if f is not None:
                fits.append(f)
        if not fits:
            return None
        f = np.asarray(fits)
        return {"vx_med": float(np.median(f[:, 0])),
                "vy_med": float(np.median(f[:, 1])),
                "wz_med": float(np.median(f[:, 2])), "n": len(fits)}

    tw = {}
    for s in stages:
        xy = np.stack([fk_body_xy(q) for q in qs[s]])
        tw[f"fk_{s}_contactsel"] = stage_twists(xy, contact)
        if plan_st is not None:
            tw[f"fk_{s}_plansel"] = stage_twists(xy, plan_st)
    tw["pads_contactsel"] = stage_twists(pads_xy, contact)
    if plan_st is not None:
        tw["pads_plansel"] = stage_twists(pads_xy, plan_st)
    out["stage_twists"] = tw
    out["body"] = {"vx_med": float(np.median([r["vx_body"] for r in rows])),
                   "wz_med": float(np.median([r["wz_body"] for r in rows]))}
    out["duty"] = np.mean(contact, axis=0).tolist()
    if plan_st is not None:
        out["scuff_frac_planswing_in_contact"] = float(
            np.mean(contact[~plan_st]))
        # achieved lift: pad height above its own stance median, during
        # plan-swing ticks (commanded lift = 25 mm * sin profile)
        wz_pads = np.stack([r["pads_wz"] for r in rows])
        lift = []
        for f in range(6):
            st_med = np.median(wz_pads[plan_st[:, f], f]) \
                if plan_st[:, f].any() else np.nan
            sw = wz_pads[~plan_st[:, f], f]
            if len(sw) and np.isfinite(st_med):
                lift.append(float(np.percentile(sw - st_med, 90)))
        out["achieved_swing_lift_p90_m"] = lift
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", choices=("scripted", "checkpoint"),
                    required=True)
    ap.add_argument("--checkpoint", type=Path, default=None)
    ap.add_argument("--cfg-json", type=Path, required=True,
                    help="JSON file with the base cfg_set list (replayed "
                         "from the checkpoint's training cfg)")
    ap.add_argument("--extra-cfg", action="append", default=[],
                    help="additional --cfg-set style overrides (lever arms)")
    ap.add_argument("--cells", required=True,
                    help="comma-separated vx:wz list")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--episode-seconds", type=float, default=15.0)
    ap.add_argument("--phase-offset", type=float, default=0.0)
    ap.add_argument("--label", default="")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    cfg_set = json.loads(args.cfg_json.read_text()) + list(args.extra_cfg)
    model = width = None
    if args.policy == "checkpoint":
        model, width = pta._load_model(args.checkpoint)
    cells = []
    for c in args.cells.split(","):
        vx, wz = c.split(":")
        cells.append((float(vx), float(wz)))
    results = []
    for vx, wz in cells:
        r = rollout(policy=args.policy, model=model, model_obs_width=width,
                    cfg_set=cfg_set, vx_cmd=vx, wz_cmd=wz, seed=args.seed,
                    episode_seconds=args.episode_seconds,
                    phase_offset=args.phase_offset)
        results.append(r)
        b = r.get("body", {})
        print(json.dumps({"cell": [vx, wz], "fell": r["fell"],
                          "body": b, "label": args.label}), flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(
        {"schema": "hexapod.turn_pipeline_probe.v1", "label": args.label,
         "policy": args.policy,
         "checkpoint": str(args.checkpoint) if args.checkpoint else None,
         "cfg_set": cfg_set, "seed": args.seed,
         "episode_seconds": args.episode_seconds,
         "results": results}, indent=1, default=str) + "\n")
    print("COMPLETE", args.out, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
