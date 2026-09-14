"""Frozen-policy dose screen: does dynamic, LOAD-COUPLED COMMAND LATENCY
(dr.latency_load_gain / dr.latency_load_group) reproduce the PS200
hardware roll signature, where the sibling load-coupled BACKLASH
mechanism plateaued at ~29-31% (speed/STATUS.md 2026-09-14 ~02:4x/~03:5x,
"the right-side-static/dynamic backlash family's ~29-31%-of-signature
plateau ... stands as the best reading from the whole joint-backlash
mechanism class ... the remaining un-tried options are: incorporate a
fresh Robot Lab telemetry export ... or a structurally different
mechanism family entirely (stick-slip/velocity-dependent ground contact,
or LOAD-COUPLED CONTROL-LATENCY)").

Physical picture: a heavily loaded joint's own position-sense-to-motion
loop (SyncWrite backlog, current-limited slew before the servo even
begins moving) responds SLOWER than an unloaded one -- bus/motion-start
latency is not a fixed per-episode draw but grows under load. Concentrated
on one side (the same heterogeneity-not-global-scale story the backlash
group probe validated), a differential delay between load-favored and
load-starved legs could produce a persistent roll bias through a
completely different physical channel (WHEN each leg's push lands, not
HOW MUCH it can move).

Same protocol as probe_backlash_asym_dose.py: frozen PS200 fast parent,
0.10 m/s forward command, dr_scale=0.0 isolation (only the named
latency_load_* override is active), 4 seeds, uniform-vs-grouped ladder.

Run from ``prototype_sts3215``::

    uv run python -m rl_move.sim.probe_latency_load_dose

Outputs ``results.json`` + ``report.md`` beneath
``logs/ckpt_eval/latency_load_dose_probe_<UTC>`` unless ``--out`` is
given.
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

# Dose grid: (name, group, gain, ref_nm). group="" spreads the gain
# independently across all 18 joints (uniform sanity check, expected to
# average out like every uniform-independent axis this track has tried);
# the rest concentrate it on the same named subsets the backlash ladder
# used, so the two mechanism families are read on an identical scale.
DOSES = [
    ("none", "", 0.0, 1.2),
    ("uniform_lo", "", 2.0, 1.2),
    ("uniform_hi", "", 5.0, 1.2),
    ("right_lo", "right", 2.0, 1.2),
    ("right_hi", "right", 5.0, 1.2),
    ("right_extreme", "right", 10.0, 1.2),
    ("right_knee", "right+knee", 5.0, 1.2),
    ("right_pitch", "right+pitch", 5.0, 1.2),
    ("single_leg", "leg0", 5.0, 1.2),
    ("single_leg_extreme", "leg0", 10.0, 1.2),
]


def rollout_dose(spec_name: str, *, dose: tuple, seed: int) -> dict:
    name, group, gain, ref_nm = dose
    spec = POLICIES[spec_name]
    policy = load_np_policy(_policy_path(spec))
    cfg = _policy_cfg(policy.meta, Intervention(name="none"))
    cfg["dr"]["latency_load_gain"] = f"{gain},{gain}"
    cfg["dr"]["latency_load_ref_nm"] = ref_nm
    cfg["dr"]["latency_load_group"] = group
    # dr_scale=0.0 isolation, same convention as probe_backlash_dose.py:
    # only the explicit latency_load_* override is active.
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
        "ref_nm": ref_nm,
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
           f"latency_load_dose_probe_"
           f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(rows, indent=2))

    lines = ["| dose | group | gain | median peak roll | "
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
        f"# Load-coupled latency dose probe ({args.policy})\n\n"
        f"Hardware target peak roll: {HARDWARE_PS200_PEAK_ROLL_DEG:.2f} deg "
        f"(matched-sim baseline {SIM_TRACE_PS200_PEAK_ROLL_DEG:.2f} deg).\n\n"
        f"Sibling load-coupled BACKLASH reference (probe_backlash_asym_"
        f"dose.py, prior cycle): right_16 (all 3 axes, 16deg gap) plateaus "
        f"at median peak 4.93 deg / signed 3.69 deg (~29-31% of signature) "
        f"before speed collapses.\n\n"
        + "\n".join(lines) + "\n"
    )
    (out / "report.md").write_text(report)
    print(report)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
