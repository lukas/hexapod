"""Frozen-policy dose screen: does extreme `struct_comp` (already-built,
default-ON reversible structural compliance) reproduce the PS200 hardware
roll signature?

Companion to `probe_backlash_dose.py` (dynamic/load-coupled BACKLASH,
NULL) — this is the OTHER half of DR_JOINT_PANEL_2026-09-13's named
"series compliance/backlash under load" candidate pair, using existing
code (`rl_move/sim/struct_compliance.py`, quasi-static series-elastic
deflection = torque / stiffness, already enabled by default in every
training/eval cfg at k_yaw/hip/knee = 300/180/120 N*m/rad) instead of new
sim physics — a near-zero-marginal-cost check before writing anything new.

Unlike JointBacklash (hysteretic — has memory of the last reversal),
struct_comp is perfectly REVERSIBLE and load-proportional every tick, so
this screen asks a different question: does simply softening the whole
structure (lower stiffness = more deflection under the SAME gait torques)
reproduce the signature, rather than a play/lag effect.

Run from ``prototype_sts3215``::

    uv run python -m rl_move.sim.probe_struct_comp_dose

Outputs ``results.json`` + ``report.md`` beneath
``logs/ckpt_eval/struct_comp_dose_probe_<UTC>`` unless ``--out`` is given.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from rl_move.np_policy import load_np_policy
from rl_move.sim.probe_ps200_transfer import (
    HARDWARE_PS200_PEAK_ROLL_DEG, POLICIES, SIM_TRACE_PS200_PEAK_ROLL_DEG,
    Intervention, _force_walk, _policy_cfg, _policy_path,
    _separated_peak_count)
from rl_move.sim.probe_walk_income import pin_command
from rl_move.sim.servo_model import SimServoParams
from rl_move.sim.walk_task import SimHexapodJointWalkEnv

ROOT = Path(__file__).resolve().parents[2]
CMD_M_S = 0.10
EPISODE_S = 12.0
SEEDS = (0, 1, 2, 3)
NOMINAL_K = {"yaw": 300.0, "hip": 180.0, "knee": 120.0}
# k_scale multiplies ALL three nominal stiffnesses together (softer
# structure = more deflection under the same torques). 1.0 = nominal
# (already the training default); <1.0 = progressively softer, well past
# the measured-bench 08-21 estimate's plausible error bar at the low end.
K_SCALES = (1.0, 0.3, 0.1, 0.03)


def rollout_dose(spec_name: str, *, k_scale: float, seed: int) -> dict:
    spec = POLICIES[spec_name]
    policy = load_np_policy(_policy_path(spec))
    cfg = _policy_cfg(policy.meta, Intervention(name="none"))
    sc = cfg["struct_comp"]
    sc["k_yaw_nm_rad"] = NOMINAL_K["yaw"] * k_scale
    sc["k_hip_nm_rad"] = NOMINAL_K["hip"] * k_scale
    sc["k_knee_nm_rad"] = NOMINAL_K["knee"] * k_scale
    # dr_scale=0.0: isolates this dose (no ordinary training-DR noise);
    # struct_comp itself samples at scale=0 -> nominal (= this override),
    # same isolation convention as probe_backlash_dose.py.
    env = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(cfg), randomize=True, dr_scale=0.0,
        episode_seconds=EPISODE_S, seed=seed, cfg=cfg)
    _force_walk(env)
    obs, _reset_info = env.reset()
    if obs.shape != policy.observation_space.shape:
        raise RuntimeError(
            f"{spec_name}: env obs {obs.shape} != policy "
            f"{policy.observation_space.shape}")
    pin_command(env, CMD_M_S, 0.0, 0.0)
    policy.reset()
    rolls: list[float] = []
    x0 = float(env.data.xpos[env._chassis_bid, 0])
    term_reason = ""
    ticks = 0
    try:
        while True:
            action, _ = policy.predict(obs, deterministic=True)
            obs, _reward, terminated, truncated, info = env.step(action)
            ticks += 1
            rolls.append(float(info.get("roll_rel_deg", 0.0)))
            if terminated or truncated:
                term_reason = str(info.get("termination_reason") or "")
                break
    finally:
        x_final = float(env.data.xpos[env._chassis_bid, 0])
        env.close()
    abs_rolls = [abs(v) for v in rolls]
    dt = 1.0 / float(policy.meta["control_hz"])
    speed = (x_final - x0) / max(ticks * dt, 1e-9)
    return {
        "policy": spec_name,
        "k_scale": k_scale,
        "seed": seed,
        "ticks": ticks,
        "terminated": bool(term_reason),
        "termination_reason": term_reason,
        "peak_abs_roll_deg": round(max(abs_rolls, default=0.0), 3),
        "positive_peaks_over_5deg": _separated_peak_count(
            rolls, threshold=5.0, dt=dt),
        "negative_peaks_over_5deg": _separated_peak_count(
            [-v for v in rolls], threshold=5.0, dt=dt),
        "forward_speed_m_s": round(speed, 4),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--policy", default="ps200")
    args = ap.parse_args()

    rows = []
    for k_scale in K_SCALES:
        for seed in SEEDS:
            print(f"[dose] {args.policy} k_scale={k_scale} seed={seed}")
            rows.append(rollout_dose(args.policy, k_scale=k_scale, seed=seed))

    out = (Path(args.out) if args.out else
           ROOT / "logs" / "ckpt_eval" /
           f"struct_comp_dose_probe_"
           f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(rows, indent=2))

    lines = ["| k_scale | median peak roll | recurrent>=5deg | falls | speed m/s |",
             "|---:|---:|---:|---:|---:|"]
    for k_scale in K_SCALES:
        group = [r for r in rows if r["k_scale"] == k_scale]
        peaks = [r["peak_abs_roll_deg"] for r in group]
        recur = [max(r["positive_peaks_over_5deg"],
                     r["negative_peaks_over_5deg"]) for r in group]
        falls = sum(1 for r in group if r["terminated"])
        speeds = [r["forward_speed_m_s"] for r in group]
        lines.append(
            f"| {k_scale} | {median(peaks):.2f} | {median(recur):.1f} | "
            f"{falls}/{len(group)} | {median(speeds):.3f} |")
    report = (
        f"# struct_comp dose probe ({args.policy})\n\n"
        f"Hardware target peak roll: {HARDWARE_PS200_PEAK_ROLL_DEG:.2f} deg "
        f"(matched-sim baseline {SIM_TRACE_PS200_PEAK_ROLL_DEG:.2f} deg). "
        f"Nominal k_yaw/hip/knee = "
        f"{NOMINAL_K['yaw']}/{NOMINAL_K['hip']}/{NOMINAL_K['knee']} "
        "N*m/rad (k_scale=1.0, already the training default).\n\n"
        + "\n".join(lines) + "\n"
    )
    (out / "report.md").write_text(report)
    print(report)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
