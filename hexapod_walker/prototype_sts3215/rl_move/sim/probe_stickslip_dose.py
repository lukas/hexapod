"""Frozen-policy dose screen: does per-foot Coulomb STICK-SLIP ground
contact (dr.foot_stickslip_gain / dr.foot_stickslip_group /
dr.foot_stickslip_vel_ref_mps) reproduce the PS200 hardware roll
signature, where both prior named dynamic-mechanism candidates closed
short -- load-coupled backlash plateaued at ~29-31% of the signature
(speed/STATUS.md 2026-09-14 ~02:4x/~03:5x) and load-coupled command
latency was a clean NULL (~04:4x, no roll effect at any dose -- this
slow creep gait's trapezoidal profile always catches up within the
gait's own phase duration regardless of latency, so no static position
error is ever created).

Physical picture: real rubber feet exhibit classic Coulomb stick-slip --
STATIC friction (foot planted, near-zero sliding speed) exceeds KINETIC
friction (foot actively sliding) by some fraction. MuJoCo's constant-
coefficient contact model expresses neither; this mechanism targets the
FOOT-GROUND CONTACT itself rather than the actuator chain (unlike both
prior candidates), so it is a genuinely different physical channel for
a persistent per-side roll bias: if one side's feet are "stickier"
(higher static friction) than the other, that side resists lateral/
push-off slip more, producing an asymmetric propulsion moment.

Same protocol as probe_latency_load_dose.py / probe_backlash_asym_
dose.py: frozen PS200 fast parent, 0.10 m/s forward command,
dr_scale=0.0 isolation (only the named foot_stickslip_* override is
active), 4 seeds, uniform-vs-grouped ladder, plus a vel_ref_mps
sensitivity pair (the threshold separating "stuck" from "sliding" is a
free modeling choice this probe has not yet swept).

Run from ``prototype_sts3215``::

    uv run python -m rl_move.sim.probe_stickslip_dose

Outputs ``results.json`` + ``report.md`` beneath
``logs/ckpt_eval/stickslip_dose_probe_<UTC>`` unless ``--out`` is given.
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

# Dose grid: (name, group, gain, vel_ref_mps). group="" spreads the gain
# independently across all 6 feet (uniform sanity check, expected to
# average out like every uniform-independent axis this track has
# tried); "right"/"leg0" concentrate it, matching the backlash/latency
# ladders' own escalation shape so all three mechanism families read on
# an identical scale. The last two rows hold gain fixed and sweep
# vel_ref_mps instead (tight vs wide "stuck" threshold), since neither
# prior probe in this saga had a second free parameter to check.
DOSES = [
    ("none", "", 0.0, 0.02),
    ("uniform_lo", "", 1.0, 0.02),
    ("uniform_hi", "", 3.0, 0.02),
    ("right_lo", "right", 1.0, 0.02),
    ("right_hi", "right", 3.0, 0.02),
    ("right_extreme", "right", 8.0, 0.02),
    ("single_leg", "leg0", 3.0, 0.02),
    ("single_leg_extreme", "leg0", 8.0, 0.02),
    ("right_hi_tight_ref", "right", 3.0, 0.005),
    ("right_hi_wide_ref", "right", 3.0, 0.08),
]


def rollout_dose(spec_name: str, *, dose: tuple, seed: int) -> dict:
    name, group, gain, vel_ref = dose
    spec = POLICIES[spec_name]
    policy = load_np_policy(_policy_path(spec))
    cfg = _policy_cfg(policy.meta, Intervention(name="none"))
    cfg["dr"]["foot_stickslip_gain"] = f"{gain},{gain}"
    cfg["dr"]["foot_stickslip_vel_ref_mps"] = vel_ref
    cfg["dr"]["foot_stickslip_group"] = group
    # dr_scale=0.0 isolation, same convention as every prior dose probe:
    # only the explicit foot_stickslip_* override is active.
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
    mean_signed_roll = sum(rolls) / max(len(rolls), 1)
    return {
        "policy": spec_name,
        "dose": name,
        "group": group,
        "gain": gain,
        "vel_ref_mps": vel_ref,
        "seed": seed,
        "ticks": ticks,
        "terminated": bool(term_reason),
        "termination_reason": term_reason,
        "peak_abs_roll_deg": round(max(abs_rolls, default=0.0), 3),
        "mean_signed_roll_deg": round(mean_signed_roll, 3),
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
    ap.add_argument("--doses", default=None,
                     help="comma-separated dose names to run (default: all)")
    args = ap.parse_args()
    doses = DOSES
    if args.doses:
        names = set(args.doses.split(","))
        doses = [d for d in DOSES if d[0] in names]
        missing = names - {d[0] for d in doses}
        if missing:
            raise SystemExit(f"unknown dose name(s): {sorted(missing)}")

    rows = []
    for dose in doses:
        for seed in SEEDS:
            print(f"[dose] {args.policy} {dose[0]} seed={seed}")
            rows.append(rollout_dose(args.policy, dose=dose, seed=seed))

    out = (Path(args.out) if args.out else
           ROOT / "logs" / "ckpt_eval" /
           f"stickslip_dose_probe_"
           f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(rows, indent=2))

    lines = ["| dose | group | gain | vel_ref_mps | median peak roll | "
             "median signed roll | recurrent>=5deg | falls | speed m/s |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for dose in doses:
        name = dose[0]
        group = [r for r in rows if r["dose"] == name]
        peaks = [r["peak_abs_roll_deg"] for r in group]
        signed = [r["mean_signed_roll_deg"] for r in group]
        recur = [max(r["positive_peaks_over_5deg"],
                     r["negative_peaks_over_5deg"]) for r in group]
        falls = sum(1 for r in group if r["terminated"])
        speeds = [r["forward_speed_m_s"] for r in group]
        lines.append(
            f"| {name} | {dose[1]} | {dose[2]} | {dose[3]} | "
            f"{median(peaks):.2f} | {median(signed):.2f} | "
            f"{median(recur):.1f} | {falls}/{len(group)} | "
            f"{median(speeds):.3f} |")
    report = (
        f"# Stick-slip ground-contact dose probe ({args.policy})\n\n"
        f"Hardware target peak roll: {HARDWARE_PS200_PEAK_ROLL_DEG:.2f} deg "
        f"(matched-sim baseline {SIM_TRACE_PS200_PEAK_ROLL_DEG:.2f} deg).\n\n"
        f"Sibling references (prior cycles): load-coupled BACKLASH "
        f"(right_16, probe_backlash_asym_dose.py) plateaus at median peak "
        f"4.93 deg / signed 3.69 deg (~29-31% of signature); load-coupled "
        f"LATENCY (probe_latency_load_dose.py) is a clean NULL (peak never "
        f"leaves the 0.85-1.71 deg noise floor).\n\n"
        + "\n".join(lines) + "\n"
    )
    (out / "report.md").write_text(report)
    print(report)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
