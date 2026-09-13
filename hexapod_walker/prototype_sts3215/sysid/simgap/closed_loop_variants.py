"""Frozen deployed policies, policy-in-the-loop, under physics VARIANTS.

The replay matrix (sysid.simgap.replay_variants) tests physics open-loop on the
robot's recorded commands.  This runs the same deployable 50 Hz actors the robot
ran (PS200, walkteach, allheading) closed-loop in the training env with a
physics change applied, and reports what the hardware runs were scored on:
peak/RMS body roll, falls, forward speed, feet in contact, stationary feet.

Hardware reference (Robot Lab v2, hexapod2, 2026-09-11, forward commands):
  PS200 0.10 m/s: peak roll 16.7 deg, rms 3.5, camera speed 1.5 mm/s
  walkteach 0.08: peak 2.8-4.2, rms 0.8-1.5, 15-38 mm/s
  allheading 0.08: peak 4.4-7.5, rms 1.0-2.1, 6.5-11.4 mm/s

Usage (prototype_sts3215):
    uv run python -m sysid.simgap.closed_loop_variants --variant baseline --variant mu0.6 \
        --variant series:sysid/simgap/variants/soft_hipknee_40_30.json --seeds 0,1,2,3

Variant tokens (comma separated): baseline | loaded | air | mu<float> | dr<float> (dr_scale) |
    series:<json> | nostruct (struct_comp off) | torsion<float> (foot torsional mu) |
    torque<float> (torque_scale pin) | hz<float> (run the policy at a lower control rate, e.g. hz40:
    models the robot's 71-86 Hz effective rate for '100 Hz' policies / 40-43 Hz for 50 Hz ones)
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from rl_move.config import load_config
from rl_move.np_policy import load_np_policy
from rl_move.sim.probe_ps200_transfer import POLICIES, PolicySpec, _force_walk, _policy_cfg, _policy_path, Intervention
from rl_move.sim.probe_walk_income import pin_command
from rl_move.sim.servo_model import SimServoParams
from rl_move.sim.walk_task import SimHexapodJointWalkEnv

ROOT = Path(__file__).resolve().parents[2]
STANCE_MM_S, SWING_MM_S = 30.0, 77.0


def parse_variant(spec: str) -> dict:
    v = {"name": spec.replace("/", "_").replace(":", "-"), "mu": 0.0, "params": None, "dr": 0.0,
         "series": None, "nostruct": False, "torsion": 0.0, "torque": None, "hz": None, "kp": 1.0}
    for tok in spec.split(","):
        tok = tok.strip()
        if tok in ("", "baseline"):
            continue
        if tok in ("air", "loaded"):
            v["params"] = tok
        elif tok.startswith("mu"):
            v["mu"] = float(tok[2:])
        elif tok.startswith("dr"):
            v["dr"] = float(tok[2:])
        elif tok.startswith("series:"):
            v["series"] = Path(tok[7:])
        elif tok == "nostruct":
            v["nostruct"] = True
        elif tok.startswith("torsion"):
            v["torsion"] = float(tok[7:])
        elif tok.startswith("torque"):
            v["torque"] = float(tok[6:])
        elif tok.startswith("hz"):
            v["hz"] = float(tok[2:])
        elif tok.startswith("kp"):
            v["kp"] = float(tok[2:])   # scale the fitted position gain on every axis
        else:
            raise SystemExit(f"unknown token {tok!r}")
    return v


def make_cfg(meta: dict, v: dict) -> dict:
    cfg = _policy_cfg(meta, Intervention("none"))
    cfg.setdefault("env", {})
    if v["mu"] > 0:
        cfg["env"]["foot_friction_slide"] = v["mu"]
    if v["torsion"] > 0:
        cfg["env"]["foot_friction_torsion"] = v["torsion"]
    if v["params"] is not None:
        cfg.setdefault("bus", {})["servo_params"] = "" if v["params"] == "air" else "loaded"
    if v["series"] is not None:
        blob = json.loads(Path(v["series"]).read_text())
        section = blob.get("joint_series_flex", blob)
        cfg["joint_series_flex"] = {**section, "enabled": 1}
        cfg.setdefault("struct_comp", {})["enabled"] = 0
    if v["nostruct"]:
        cfg.setdefault("struct_comp", {})["enabled"] = 0
    if v["torque"] is not None:
        cfg.setdefault("dr", {})["torque_scale"] = f"{v['torque']},{v['torque']}"
    if v["hz"] is not None:
        cfg.setdefault("control", {})["hz"] = float(v["hz"])
    return cfg


def rollout(spec: PolicySpec, v: dict, *, seed: int, episode_s: float, cmd: float) -> dict:
    import mujoco
    policy = load_np_policy(_policy_path(spec))
    cfg = make_cfg(policy.meta, v)
    params = SimServoParams.from_cfg(cfg)
    if v["kp"] != 1.0:
        for ax in params.axes.values():
            ax.kp *= v["kp"]
    env = SimHexapodJointWalkEnv(params=params, randomize=True, dr_scale=v["dr"],
                                 episode_seconds=episode_s, seed=seed, cfg=cfg)
    _force_walk(env)
    obs, reset_info = env.reset()
    if obs.shape != policy.observation_space.shape:
        raise RuntimeError(f"{spec.name}: env obs {obs.shape} != policy {policy.observation_space.shape}")
    pin_command(env, cmd, 0.0, 0.0)
    policy.reset()
    pad = [mujoco.mj_name2id(env.model, mujoco.mjtObj.mjOBJ_BODY, f"L{i}_pad") for i in range(6)]
    chassis = mujoco.mj_name2id(env.model, mujoco.mjtObj.mjOBJ_BODY, "chassis")
    dt = 1.0 / float(cfg["control"]["hz"])
    rolls, pitches, ncon, xs, foot_xyz, yaws = [], [], [], [], [], []
    term = ""
    while True:
        action, _ = policy.predict(obs, deterministic=True)
        obs, _r, terminated, truncated, info = env.step(action)
        rolls.append(float(info.get("roll_rel_deg", 0.0)))
        pitches.append(float(info.get("pitch_rel_deg", 0.0)))
        c = [bool(info.get(f"walk_foot{l}_contact", False)) for l in range(6)]
        ncon.append(sum(c))
        xs.append(env.data.xpos[chassis, :2].copy())
        q = env.data.xquat[chassis]
        yaws.append(float(np.degrees(np.arctan2(2 * (q[0] * q[3] + q[1] * q[2]), 1 - 2 * (q[2] ** 2 + q[3] ** 2)))))
        foot_xyz.append(np.array([env.data.xpos[b] for b in pad]))
        if terminated or truncated:
            term = str(info.get("termination_reason") or "")
            break
    env.close()
    rolls = np.array(rolls); ncon = np.array(ncon); xs = np.array(xs); fxyz = np.array(foot_xyz)
    t = np.arange(len(rolls)) * dt
    walk = t >= 2.0  # after the standard 1 s hold + 1 s ramp
    if walk.sum() < 10:
        walk = np.ones(len(t), bool)
    vel = np.gradient(fxyz, dt, axis=0)
    speed = np.linalg.norm(vel[:, :, :2], axis=2) * 1000
    disp = xs[walk][-1] - xs[walk][0]
    rand = reset_info.get("randomization") or {}
    rand = {k: (round(float(x), 4) if isinstance(x, (int, float)) else
                [round(float(y), 4) for y in x] if isinstance(x, (list, tuple)) and len(x) <= 18 and all(isinstance(y, (int, float)) for y in x) else None)
            for k, x in rand.items()}
    rand = {k: x for k, x in rand.items() if x is not None}
    return {
        "randomization": rand,
        "policy": spec.name, "variant": v["name"], "seed": seed, "ticks": int(len(rolls)), "fell": bool(term),
        "termination": term, "peak_abs_roll": round(float(np.max(np.abs(rolls[walk]))), 2),
        "rms_roll": round(float(np.sqrt(np.mean(rolls[walk] ** 2))), 2),
        "rms_pitch": round(float(np.sqrt(np.mean(np.array(pitches)[walk] ** 2))), 2),
        "speed_mm_s": round(float(np.hypot(*disp) / max(t[walk][-1] - t[walk][0], 1e-6) * 1000), 1),
        "yaw_drift_deg": round(float(yaws[-1] - yaws[int(np.argmax(walk))]), 1),
        "mean_feet_contact": round(float(ncon[walk].mean()), 2),
        "frac_le3_feet": round(float(np.mean(ncon[walk] <= 3)), 3),
        "frac_le2_feet": round(float(np.mean(ncon[walk] <= 2)), 3),
        "mean_feet_stationary": round(float((speed[walk] < STANCE_MM_S).sum(1).mean()), 2),
        "mean_feet_swinging": round(float((speed[walk] > SWING_MM_S).sum(1).mean()), 2),
        "foot_lift_p95_mm": [round(float(x), 1) for x in np.percentile(fxyz[walk][:, :, 2], 95, axis=0) * 1000],
        "roll_series": [round(float(x), 2) for x in rolls[::5]],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--variant", action="append", default=["baseline"])
    ap.add_argument("--policy", action="append", default=None)
    ap.add_argument("--seeds", default="0,1,2,3")
    ap.add_argument("--episode-s", type=float, default=10.0)
    ap.add_argument("--cmd", type=float, default=None, help="m/s; default = policy min speed (PS200 0.10 like hardware)")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    variants = a.variant if len(a.variant) == 1 else a.variant[1:]
    pols = a.policy or list(POLICIES)
    out_dir = a.out or (ROOT / "logs" / "ckpt_eval" / f"simgap_closed_loop_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for spec in variants:
        v = parse_variant(spec)
        for pname in pols:
            p = POLICIES[pname]
            cmd = a.cmd if a.cmd is not None else (0.10 if pname == "ps200" else 0.08)
            for seed in [int(s) for s in a.seeds.split(",")]:
                r = rollout(p, v, seed=seed, episode_s=a.episode_s, cmd=cmd)
                rows.append(r)
                print(f"{v['name']:<40} {pname:<11} s{seed} roll pk/rms={r['peak_abs_roll']:>5.1f}/{r['rms_roll']:.2f} "
                      f"spd={r['speed_mm_s']:>5.1f} feet={r['mean_feet_contact']:.2f} le3={r['frac_le3_feet']:.2f} "
                      f"stat={r['mean_feet_stationary']:.2f} fell={r['fell']} {r['termination']}", flush=True)
                (out_dir / "rows.json").write_text(json.dumps(rows, indent=0))
    # summary
    summ = {}
    for spec in variants:
        v = parse_variant(spec)
        for pname in pols:
            g = [r for r in rows if r["variant"] == v["name"] and r["policy"] == pname]
            if not g:
                continue
            summ[f"{v['name']}|{pname}"] = {k: round(float(np.median([r[k] for r in g])), 2) for k in
                                            ("peak_abs_roll", "rms_roll", "speed_mm_s", "mean_feet_contact", "frac_le3_feet", "mean_feet_stationary")}
            summ[f"{v['name']}|{pname}"]["falls"] = int(sum(r["fell"] for r in g))
            summ[f"{v['name']}|{pname}"]["n"] = len(g)
    (out_dir / "summary.json").write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ, indent=1))
    print("out:", out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
