"""Frozen-policy dose screen: does dynamic, load-coupled JOINT BACKLASH
reproduce the PS200 hardware roll signature?

DR_JOINT_PANEL_2026-09-13's held-out training comparison (CTRL / WIDE /
STRUCT / COMBO / ADAPT) closed 0/5 against the 30% held-out roll-reduction
gate; its own "Result: NULL" section concludes the gap is "very likely a
DYNAMIC, load-coupled mechanism (series compliance/backlash under load,
servo-loop behavior under load, stick-slip) that the simulator's parametric
families do not express" and names the escalation: "build a DYNAMIC/
load-coupled uncertainty mechanism ... and should be built+tested against
the panel's own frozen-policy signature-reproduction protocol BEFORE
funding another training arm." (speed/STATUS.md, 2026-09-14 ~01:4x.)

This is that check for the new mechanism: `domain_rand.JointBacklash`
(dr.joint_backlash_deg / dr.joint_backlash_load_gain, 2026-09-14). It is
NOT the earlier "deadband (backlash/post-encoder compliance) dose" table
in probe_ps200_transfer.py — that probed the ALWAYS-ON symmetric dead-zone
(deadband_scale), refuted alone; this is a true direction-reversal-
triggered mechanical play, load-widened, applied to the frozen PS200 fast
parent on the SAME command protocol (0.10 m/s forward, out-and-back).

Run from ``prototype_sts3215``::

    uv run python -m rl_move.sim.probe_backlash_dose

Outputs ``results.json`` + ``report.md`` beneath
``logs/ckpt_eval/backlash_dose_probe_<UTC>`` unless ``--out`` is given.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

import numpy as np

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

# Dose grid: (name, backlash_deg_lo, backlash_deg_hi, load_gain_lo, hi).
# Gaps span from well inside ordinary training DR's implicit tolerance
# (deadband ~1-3 deg already) up to an engineering-generous "worn gearbox"
# upper bound; load_gain doses from none (pure static play) to a strong
# load-coupling (gap ~triples at the reference load).
DOSES = [
    ("none", 0.0, 0.0, 0.0, 0.0),
    ("static_lo", 1.0, 1.0, 0.0, 0.0),
    ("static_hi", 4.0, 4.0, 0.0, 0.0),
    ("load_lo", 1.0, 1.0, 1.0, 1.0),
    ("load_hi", 2.0, 2.0, 2.0, 2.0),
    ("load_hi_wide_gap", 4.0, 4.0, 2.0, 2.0),
]


def rollout_dose(spec_name: str, *, dose: tuple, seed: int) -> dict:
    name, glo, ghi, llo, lhi = dose
    spec = POLICIES[spec_name]
    policy = load_np_policy(_policy_path(spec))
    cfg = _policy_cfg(policy.meta, Intervention(name="none"))
    cfg["dr"]["joint_backlash_deg"] = f"{glo},{ghi}"
    cfg["dr"]["joint_backlash_load_gain"] = f"{llo},{lhi}"
    # dr_scale=0.0: the ONLY active randomization is the explicit
    # joint_backlash_* override below (an ABSOLUTE post-scale override,
    # same convention _policy_cfg's zero/deadband overrides already rely
    # on) -- every other DR axis (mass/friction/kp/etc) sits at its
    # guarded nominal, exactly like probe_ps200_transfer.rollout()'s own
    # isolation convention, so seed-to-seed roll variance measures ONLY
    # this mechanism, not the ordinary training-DR noise floor.
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
        "dose": name,
        "backlash_deg_range": [glo, ghi],
        "load_gain_range": [llo, lhi],
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
    for dose in DOSES:
        for seed in SEEDS:
            print(f"[dose] {args.policy} {dose[0]} seed={seed}")
            rows.append(rollout_dose(args.policy, dose=dose, seed=seed))

    out = (Path(args.out) if args.out else
           ROOT / "logs" / "ckpt_eval" /
           f"backlash_dose_probe_"
           f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(rows, indent=2))

    lines = ["| dose | gap deg | load_gain | median peak roll | recurrent>=5deg | falls | speed m/s |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for dose in DOSES:
        name = dose[0]
        group = [r for r in rows if r["dose"] == name]
        peaks = [r["peak_abs_roll_deg"] for r in group]
        recur = [max(r["positive_peaks_over_5deg"],
                     r["negative_peaks_over_5deg"]) for r in group]
        falls = sum(1 for r in group if r["terminated"])
        speeds = [r["forward_speed_m_s"] for r in group]
        lines.append(
            f"| {name} | {dose[1]}-{dose[2]} | {dose[3]}-{dose[4]} | "
            f"{median(peaks):.2f} | {median(recur):.1f} | {falls}/{len(group)} | "
            f"{median(speeds):.3f} |")
    report = (
        f"# Backlash dose probe ({args.policy})\n\n"
        f"Hardware target peak roll: {HARDWARE_PS200_PEAK_ROLL_DEG:.2f} deg "
        f"(matched-sim baseline {SIM_TRACE_PS200_PEAK_ROLL_DEG:.2f} deg).\n\n"
        + "\n".join(lines) + "\n"
    )
    (out / "report.md").write_text(report)
    print(report)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
