"""Frozen-policy dose screen: does a structured, CONCENTRATED per-leg
MASS/INERTIA bias reproduce the PS200 hardware roll signature?

speed/STATUS.md 2026-09-14 ~12:0x closed the entire DR_JOINT_PANEL_
2026-09-13 training panel at 6/6 (CTRL/WIDE/STRUCT/COMBO/ADAPT/
BACKLASH-training), and the frozen-policy diagnostic probes that
preceded it found joint backlash CONCENTRATED on one leg group (the
"right" side) to be the only mechanism so far that reproduces a real,
monotonic SIGNED roll bias (~29-31% of the 16.78-deg PS200 signature,
`probe_backlash_asym_dose.py`) -- load-coupled command latency and
per-foot Coulomb stick-slip were both clean NULLs. Every prior mass/
CoM/link-length knob in this codebase (`RandRanges.mass_scale`/
`leg_mass_jitter_pct`/`com_offset_m`/`link_len_leg_pct`) is drawn
SYMMETRICALLY and independently, per leg or per link -- exactly the
"uniform" shape that was NULL for backlash too. This is the analogous
CONCENTRATED form for the mass/CoM family DESIGN.md's own mechanism
inventory names ("body/link mass, CoM and inertia ... per-leg
asymmetric manufacturing error") but no cycle had actually built or
probed: `dr.leg_mass_bias_pct` / `dr.leg_mass_bias_group`
(domain_rand.py, 2026-09-14) -- a single persistent bias magnitude
applied to one named leg group's mass+inertia, modeling a real build
asymmetry (battery/wiring routed to one side, uneven print infill
between the left/right leg sets), a STATIC structural mechanism (no
per-tick hook needed, unlike backlash/latency/stick-slip -- it is
baked into the model once at reset, like the existing symmetric mass
knobs it extends).

Run from ``prototype_sts3215``::

    uv run python -m rl_move.sim.probe_massbias_dose

Outputs ``results.json`` + ``report.md`` beneath
``logs/ckpt_eval/massbias_dose_probe_<UTC>`` unless ``--out`` is given.
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

# Dose grid: (name, group, bias_pct). group="" replicates a symmetric
# global mass bump (every leg biased identically -- a sanity check,
# should behave like a small mass_scale bump, not a roll mechanism);
# every other row concentrates the SAME bias onto a named leg group,
# mirroring probe_backlash_asym_dose.py's right/left/single-leg ladder.
DOSES = [
    ("none", "", 0.0),
    ("symmetric_sanity", "", 0.30),
    ("right_lo", "right", 0.10),
    ("right_mod", "right", 0.20),
    ("right_hi", "right", 0.30),
    ("right_extreme", "right", 0.50),
    ("left_hi", "left", 0.30),
    ("single_leg_extreme", "leg0", 0.60),
    ("front_hi", "front", 0.30),
    ("rear_hi", "rear", 0.30),
]


def rollout_dose(spec_name: str, *, dose: tuple, seed: int) -> dict:
    name, group, bias_pct = dose
    spec = POLICIES[spec_name]
    policy = load_np_policy(_policy_path(spec))
    cfg = _policy_cfg(policy.meta, Intervention(name="none"))
    cfg["dr"]["leg_mass_bias_pct"] = f"{bias_pct},{bias_pct}"
    cfg["dr"]["leg_mass_bias_group"] = group
    # dr_scale=0.0 isolation, same convention as the backlash/latency/
    # stickslip probes: only the explicit leg_mass_bias_* override is
    # active, so seed-to-seed roll variance measures ONLY this
    # mechanism, not the ordinary training-DR noise floor.
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
    # Signed mean roll: a genuinely one-sided (asymmetric) mechanism
    # should show a persistent DC bias, not just a wider symmetric
    # spread -- same diagnostic the backlash asym probe uses.
    mean_signed_roll = sum(rolls) / max(len(rolls), 1)
    return {
        "policy": spec_name,
        "dose": name,
        "group": group,
        "bias_pct": bias_pct,
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
           f"massbias_dose_probe_"
           f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(rows, indent=2))

    lines = ["| dose | group | bias pct | median peak roll | "
             "median signed roll | recurrent>=5deg | falls | speed m/s |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
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
            f"| {name} | {dose[1]} | {dose[2]} | "
            f"{median(peaks):.2f} | {median(signed):.2f} | "
            f"{median(recur):.1f} | {falls}/{len(group)} | "
            f"{median(speeds):.3f} |")
    report = (
        f"# Structured per-leg mass-bias dose probe ({args.policy})\n\n"
        f"Hardware target peak roll: {HARDWARE_PS200_PEAK_ROLL_DEG:.2f} deg "
        f"(matched-sim baseline {SIM_TRACE_PS200_PEAK_ROLL_DEG:.2f} deg).\n\n"
        f"Backlash reference (probe_backlash_asym_dose.py, prior cycle): "
        f"none=1.39 deg, right_16 (best-to-date)=4.93 deg median peak roll, "
        f"signed roll 0.47 -> ~0.17 deg, plateaus at ~29-31% of the "
        f"hardware signature.\n\n"
        + "\n".join(lines) + "\n"
    )
    (out / "report.md").write_text(report)
    print(report)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
