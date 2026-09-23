"""probe_box_stride_income.py — forced-stride income probe UNDER an action box.

WHY (2026-09-23 dig-in, extplant82-actionbox lineage): four box arms
(fixed / 3M-ramp / 5M-ramp / 5M-ramp+log-std-comp) all landed the same
signature — extended stance held (~201 mm / 85 deg), prog ~= 0 in every
eval bucket — and the log-std-compensation FAIL refuted the
exploration-noise hypothesis. Before any 7th arm, answer the structural
question: can ANY stride expressible inside this run's action box earn
net-positive walk income under its exact reward stack? Note the box
mechanism FREEZES a joint class whose box_*_deg is 0 (joint_task.py),
and the extplant82 arms set only hip/knee — all six coxa YAW joints
(the fore/aft swing DOF) are frozen at center; the original walkcurr
litrep box arms set yaw=11 (ledger 001949).

WHAT IT DOES: builds the joint_walk env from config.yaml + the run's
--cfg-set list (same parser as eval_checkpoint), pins a forward walk
command, and rolls a SCRIPTED reference policy expressed IN BOX ACTION
SPACE: a TripodGait synced to the box's own plant stance is converted
per tick via a = (q_gait - box_center) / box_rad (frozen classes -> 0,
their amputated request recorded in degrees). Accumulates every
info["reward_*"] term, walk_prog_factor / walk_anchor_frac, along-command
displacement, loaded-foot slip and per-class clip stats. Run it once per
cfg variant (e.g. base vs + goal.joint_action_box_yaw_deg=11) and diff.

    uv run python -m rl_move.scripts.probe_box_stride_income \
        --policy tripod --seconds 12 --vx 0.08 \
        --cfg-set env.model_source=mesh --cfg-set control.hz=50 ... \
        --out /tmp/box_probe_base_tripod.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

DEG2RAD = math.pi / 180.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", choices=("freeze", "tripod"),
                    default="tripod")
    ap.add_argument("--cfg-set", action="append", default=[])
    ap.add_argument("--seconds", type=float, default=12.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--vx", type=float, default=0.08)
    ap.add_argument("--period-scale", type=float, default=1.0,
                    help="TripodGait period_scale (1.0 = nominal)")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    from rl_move.config import load_config
    from rl_move.sim.cfg_set import _parse_cfg_set
    from rl_move.sim.servo_model import SimServoParams
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    from hexapod_core.tripod_gait import TripodGait

    cfg = load_config()
    for key, parsed in _parse_cfg_set(args.cfg_set).items():
        node = cfg
        *path, leaf = key.split(".")
        for k in path:
            node = node.setdefault(k, {})
        node[leaf] = parsed

    env = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(cfg), randomize=False,
        dr_scale=0.0, episode_seconds=args.seconds, seed=args.seed,
        cfg=cfg)
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 1.0 if m == "walk" else 0.0)
    obs, _ = env.reset()
    if not env._joint_action_box_active:
        raise SystemExit("this probe is for ACTIVE action-box cfgs")
    center = env._joint_action_box_center.copy()
    box_rad = env._joint_action_box_rad.copy()   # target box (ramp
    # armed-but-never-broadcast = TARGET width, same as eval)
    frozen = box_rad <= 1e-9

    # pin forward command: hold 1 s, ramp 1 s, constant (probe_walk_income
    # pin_command pattern)
    traj = env._goal_traj
    n = len(traj.vx)
    hold_n = ramp_n = int(round(1.0 / env.dt))
    ramp = np.linspace(0.0, 1.0, ramp_n)
    traj.vx[:] = args.vx
    traj.vx[:hold_n] = 0.0
    traj.vx[hold_n:hold_n + ramp_n] = args.vx * ramp
    traj.vy[:] = 0.0
    if getattr(traj, "wz", None) is not None:
        traj.wz[:] = 0.0

    # stance the box is centered on, in robot_abs degrees (bias keys)
    hip_deg = float(cfg.get("plant", {}).get("hip_deg", 20.0))
    knee_deg = float(cfg.get("plant", {}).get("knee_deg", 82.0))
    gait = TripodGait(vx=0.0, period_scale=args.period_scale)
    gait.sync_plant_stance(hip_deg, knee_deg)
    gait.reset_phase()

    term_sums: dict[str, float] = defaultdict(float)
    factor_sums: dict[str, float] = defaultdict(float)
    factor_n: dict[str, int] = defaultdict(int)
    total, step, cmd_dist, along_dist = 0.0, 0, 0.0, 0.0
    slip_m = 0.0
    pad_prev = None
    contact_prev = None
    # per-class clip accounting: what the reference gait ASKED for vs
    # what the box let through
    cls_idx = {"yaw": slice(0, 18, 3), "hip": slice(1, 18, 3),
               "knee": slice(2, 18, 3)}
    ask_deg = {k: [] for k in cls_idx}
    clip_frac = {k: [] for k in cls_idx}
    term_reason = None
    while True:
        t = step * env.dt
        i = min(step, n - 1)
        if args.policy == "freeze":
            act = np.zeros(18)
        else:
            gait.set_velocity(vx=float(traj.vx[i]), vy=0.0, omega=0.0)
            q_des = np.asarray(gait.desired_deg(t)) * DEG2RAD
            a_raw = (q_des - center) / np.where(frozen, 1.0, box_rad)
            a_raw[frozen] = 0.0
            act = np.clip(a_raw, -1.0, 1.0)
            for k, sl in cls_idx.items():
                ask_deg[k].append(float(np.max(
                    np.abs(q_des[sl] - center[sl])) / DEG2RAD))
                clip_frac[k].append(float(np.mean(
                    np.abs(a_raw[sl]) > 1.0)))
        obs, r, term, trunc, info = env.step(act)
        total += float(r)
        for k, v in info.items():
            if k.startswith("reward_"):
                term_sums[k] += float(v)
            elif k in ("walk_prog_factor", "walk_anchor_frac"):
                factor_sums[k] += float(v)
                factor_n[k] += 1
        g = env._current_goal()
        if g is not None:
            s_ref = math.hypot(g.vx_ref, g.vy_ref)
            if s_ref > 1e-3:
                v_b = env._body_vel_xy()
                cmd_dist += s_ref * env.dt
                along_dist += ((v_b[0] * g.vx_ref + v_b[1] * g.vy_ref)
                               / s_ref) * env.dt
        contact_now = [float(env.data.sensordata[adr]) > 0.5
                       for adr in env._touch_adr]
        pad_now = env.data.xpos[env._pad_bids, :2].copy()
        if pad_prev is not None:
            moved = np.linalg.norm(pad_now - pad_prev, axis=1)
            slip_m += float(moved[np.asarray(contact_prev, bool)].sum())
        pad_prev, contact_prev = pad_now, contact_now
        step += 1
        if term or trunc:
            term_reason = info.get("termination_reason")
            break
    env.close()
    labelled = float(sum(term_sums.values()))
    rec = {
        "policy": args.policy, "seed": args.seed, "ticks": step,
        "vx_cmd": args.vx, "period_scale": args.period_scale,
        "box_deg": {k: float(np.max(box_rad[sl]) / DEG2RAD)
                    for k, sl in cls_idx.items()},
        "return": round(total, 2),
        "terms": {k: round(v, 2) for k, v in sorted(term_sums.items())},
        "residual_base": round(total - labelled, 2),
        "factors": {k: round(factor_sums[k] / max(factor_n[k], 1), 4)
                    for k in factor_sums},
        "progress_ratio": round(along_dist / cmd_dist, 4)
        if cmd_dist > 0 else 0.0,
        "along_dist_m": round(along_dist, 4),
        "slip_m_total": round(slip_m, 4),
        "gait_ask_deg_max": {k: round(max(v), 2) if v else None
                             for k, v in ask_deg.items()},
        "gait_clip_frac_mean": {k: round(float(np.mean(v)), 4) if v
                                else None for k, v in clip_frac.items()},
        "terminated": term_reason if term_reason not in (None, "time")
        else None,
    }
    out = json.dumps(rec, indent=1)
    print(out)
    if args.out:
        args.out.write_text(out)


if __name__ == "__main__":
    main()
