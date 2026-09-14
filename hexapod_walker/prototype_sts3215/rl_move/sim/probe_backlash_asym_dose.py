"""Frozen-policy dose screen: does ASYMMETRIC (concentrated) joint backlash
reproduce the PS200 hardware roll signature, where the UNIFORM-across-all-
18-joints form (probe_backlash_dose.py, 2026-09-14) was NULL?

`speed/STATUS.md` 2026-09-14 ~02:2x closes the uniform dose as a 2nd
NULL dynamic-mechanism candidate and names the untried next form: "(a) an
ASYMMETRIC per-leg or per-axis-only dose ... the panel's own hard-region
correlation study found per-leg heterogeneity, not global scales, drives
roll; this mechanism was only tested in its uniform form." The panel's own
correlation study (`docs/DR_JOINT_PANEL_2026-09-13.md`) names per-joint/
per-leg kp SPREAD (not mean) as the single strongest roll correlate
(+0.84) -- i.e. some joints badly loose while their neighbors/opposite side
stay tight, not every joint equally loose. Uniform independent-per-joint
backlash (the prior probe) already has SOME per-joint variance but it is
symmetric left/right in expectation and averages out; this probe
deliberately concentrates the SAME (or a stronger) dose onto one named
leg-group or axis-group via the new `dr.joint_backlash_group` mask
(domain_rand.backlash_group_mask) so a persistent, one-sided roll bias
gets a real chance to show up.

Run from ``prototype_sts3215``::

    uv run python -m rl_move.sim.probe_backlash_asym_dose

Outputs ``results.json`` + ``report.md`` beneath
``logs/ckpt_eval/backlash_asym_dose_probe_<UTC>`` unless ``--out`` is given.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from rl_move.np_policy import load_np_policy
from rl_move.sim.probe_backlash_dose import rollout_dose as _rollout_uniform
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

# Dose grid: (name, group, gap_deg, load_gain). group="" replicates the
# uniform-across-all-18 "none"/"static_hi" rows from probe_backlash_dose.py
# as an in-run sanity check (must reproduce those medians); every other
# row concentrates the SAME style of dose onto a named subset via
# dr.joint_backlash_group (domain_rand.BACKLASH_GROUPS).
DOSES = [
    ("none", "", 0.0, 0.0),
    ("uniform_static_hi_sanity", "", 4.0, 0.0),
    ("right_static", "right", 4.0, 0.0),
    ("right_static_hi", "right", 8.0, 0.0),
    ("right_load", "right", 4.0, 2.0),
    ("single_leg_static", "leg0", 8.0, 0.0),
    ("single_leg_load", "leg0", 8.0, 2.0),
    ("single_leg_extreme", "leg0", 16.0, 3.0),
    ("knee_only", "knee", 4.0, 0.0),
    ("pitch_only", "pitch", 4.0, 0.0),
    # Escalation once right_static/right_static_hi showed a genuine
    # monotonic SIGNED bias (unlike any uniform dose): push the same
    # concentrated-on-one-side mechanism further to find where it
    # plateaus/reverses before funding anything.
    ("right_12", "right", 12.0, 0.0),
    ("right_16", "right", 16.0, 0.0),
    ("right_24", "right", 24.0, 0.0),
    ("right_16_load2", "right", 16.0, 2.0),
    ("right_24_load3", "right", 24.0, 3.0),
]


def rollout_dose(spec_name: str, *, dose: tuple, seed: int) -> dict:
    name, group, gap, load_gain = dose
    spec = POLICIES[spec_name]
    policy = load_np_policy(_policy_path(spec))
    cfg = _policy_cfg(policy.meta, Intervention(name="none"))
    cfg["dr"]["joint_backlash_deg"] = f"{gap},{gap}"
    cfg["dr"]["joint_backlash_load_gain"] = f"{load_gain},{load_gain}"
    cfg["dr"]["joint_backlash_group"] = group
    # dr_scale=0.0 isolation, same convention as probe_backlash_dose.py:
    # only the explicit joint_backlash_* override is active.
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
    # should show a persistent DC bias, not just a wider symmetric spread
    # -- this is the key extra diagnostic vs. the uniform probe.
    mean_signed_roll = sum(rolls) / max(len(rolls), 1)
    return {
        "policy": spec_name,
        "dose": name,
        "group": group,
        "gap_deg": gap,
        "load_gain": load_gain,
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
    args = ap.parse_args()

    rows = []
    for dose in DOSES:
        for seed in SEEDS:
            print(f"[dose] {args.policy} {dose[0]} seed={seed}")
            rows.append(rollout_dose(args.policy, dose=dose, seed=seed))

    out = (Path(args.out) if args.out else
           ROOT / "logs" / "ckpt_eval" /
           f"backlash_asym_dose_probe_"
           f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(rows, indent=2))

    lines = ["| dose | group | gap | load_gain | median peak roll | "
             "median signed roll | recurrent>=5deg | falls | speed m/s |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for dose in DOSES:
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
        f"# Asymmetric backlash dose probe ({args.policy})\n\n"
        f"Hardware target peak roll: {HARDWARE_PS200_PEAK_ROLL_DEG:.2f} deg "
        f"(matched-sim baseline {SIM_TRACE_PS200_PEAK_ROLL_DEG:.2f} deg).\n\n"
        f"Uniform-dose reference (probe_backlash_dose.py, prior cycle): "
        f"none=1.39 deg, static_hi(4deg all 18 joints)=1.34 deg median peak "
        f"roll, both NULL vs the 16.78 deg hardware signature.\n\n"
        + "\n".join(lines) + "\n"
    )
    (out / "report.md").write_text(report)
    print(report)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
