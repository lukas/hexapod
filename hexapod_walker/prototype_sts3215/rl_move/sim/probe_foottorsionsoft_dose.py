"""Frozen-policy dose ladder: structured, concentrated PER-FOOT
TORSIONAL/ROLLING friction reduction vs. the PS200 hardware roll
signature (2026-09-20, speed track).

Background (`rl_docs/tracks/speed/STATUS.md` 09-20): the sibling
``probe_footcontactsoft_dose.py`` dosed foot contact SOLREF/SOLIMP
(compliance/give) up to a 9x factor and found a clean NULL -- no
dose-response at all, ps200 and both controls scatter identically in
the 1.1-2.3 deg noise floor regardless of dose or leg group. That
probe only ever touched the foot's PENETRATION stiffness. MuJoCo's
foot pad geom is condim=6 (full torsional + rolling friction, currently
"2.0 0.1 0.001" -- sliding/torsional/rolling), but the only existing
per-foot friction axis (``foot_friction_scale``) touches SLIDING
(index 0) alone. A worn/rounded pad or bearing that lets a planted
foot twist more freely under a swinging leg's yaw reaction is a
mechanistically distinct hypothesis from either contact stiffness or
sliding grip: it is a candidate route for ordinary gait yaw reaction to
convert into extra BODY roll via the support tripod pivoting rather
than holding still. Never dosed by any prior probe in this saga.

Same isolation convention as every prior probe: frozen ``ps200`` policy,
``dr_scale=0.0``, pinned 0.10 m/s forward command, seeds 0-3, 15 s
episodes. No training arm is funded here -- this stays a frozen-policy
probe per the operator's diagnose-before-train order.

Run from ``prototype_sts3215``::

    uv run python -m rl_move.sim.probe_foottorsionsoft_dose

Outputs ``results.json`` and ``report.md`` beneath
``logs/ckpt_eval/foottorsionsoft_dose_probe_<UTC>`` unless ``--out`` is
supplied.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

import numpy as np

from rl_move.np_policy import load_np_policy
from rl_move.sim.probe_dr_joint_panel import _separated_peak_count
from rl_move.sim.probe_ps200_transfer import (
    POLICIES, Intervention, PolicySpec, _force_walk, _policy_cfg,
    _policy_path,
)
from rl_move.sim.probe_walk_income import pin_command
from rl_move.sim.servo_model import SimServoParams
from rl_move.sim.walk_task import SimHexapodJointWalkEnv

HARDWARE_PS200_PEAK_ROLL_DEG = 16.78
FROZEN_POLICY = POLICIES["ps200"]
CONTROL_POLICIES = (POLICIES["walkteach"], POLICIES["allheading"])
SEEDS = (0, 1, 2, 3)
CMD_M_S = 0.10
EPISODE_S = 15.0


@dataclass(frozen=True)
class Dose:
    name: str
    pct: float = 0.0            # magnitude, applied as (pct, pct) -- a
                                 # fixed dose. Scale factor on the foot
                                 # geom's torsional+rolling friction is
                                 # (1-pct), floored at 0: pct=0.9 leaves
                                 # 10% of nominal torsional grip.
    group: str = ""


DOSES = (
    Dose("none", 0.0, ""),
    Dose("symmetric_lo", 0.5, ""),
    Dose("symmetric_hi", 0.9, ""),
    Dose("right_lo", 0.5, "right"),
    Dose("right_hi", 0.9, "right"),
    Dose("right_extreme", 0.99, "right"),
    Dose("left_hi", 0.9, "left"),
    Dose("single_leg_extreme", 0.99, "leg0"),
    Dose("front_hi", 0.9, "front"),
    Dose("rear_hi", 0.9, "rear"),
)

SELECTIVITY_DOSES = (
    Dose("none", 0.0, ""),
    Dose("right_hi", 0.9, "right"),
    Dose("right_extreme", 0.99, "right"),
)


def _dose_cfg(dose: Dose) -> dict:
    cfg: dict = {}
    if dose.pct > 0.0:
        cfg["foot_torsion_soft_pct"] = f"{dose.pct},{dose.pct}"
        if dose.group:
            cfg["foot_torsion_soft_group"] = dose.group
    return cfg


def rollout(dose: Dose, *, seed: int, policy=None,
            spec: PolicySpec = FROZEN_POLICY) -> dict:
    if policy is None:
        policy = load_np_policy(_policy_path(spec))
    cfg = _policy_cfg(policy.meta, Intervention(name="foottorsionsoft"))
    cfg.setdefault("dr", {}).update(_dose_cfg(dose))
    env = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(cfg), randomize=True, dr_scale=0.0,
        episode_seconds=EPISODE_S, seed=seed, cfg=cfg)
    _force_walk(env)
    obs, _info = env.reset()
    if obs.shape != policy.observation_space.shape:
        raise RuntimeError(
            f"obs {obs.shape} != policy {policy.observation_space.shape}")
    pin_command(env, CMD_M_S, 0.0, 0.0)
    policy.reset()

    hz = float(policy.meta["control_hz"])
    rolls: list[float] = []
    x0 = float(env.data.xpos[env._chassis_bid, 0])
    x_walk = None
    x_final = x0
    term_reason = ""
    ticks = 0
    try:
        while True:
            t_s = env._step_i * env.dt
            action, _ = policy.predict(obs, deterministic=True)
            obs, _r, terminated, truncated, info = env.step(action)
            ticks += 1
            rolls.append(float(info.get("roll_rel_deg", 0.0)))
            if t_s >= 2.0 and x_walk is None:
                x_walk = float(env.data.xpos[env._chassis_bid, 0])
            x_final = float(env.data.xpos[env._chassis_bid, 0])
            if terminated or truncated:
                term_reason = str(info.get("termination_reason") or "")
                break
    finally:
        env.close()

    abs_rolls = [abs(v) for v in rolls]
    peak_idx = int(np.argmax(abs_rolls)) if abs_rolls else 0
    signed_at_peak = rolls[peak_idx] if rolls else 0.0
    elapsed_walk = max(ticks / hz - 2.0, 1e-9)
    x_walk = x_final if x_walk is None else x_walk
    return {
        "policy": spec.name,
        "dose": dose.name,
        "group": dose.group,
        "pct": dose.pct,
        "seed": seed,
        "ticks": ticks,
        "terminated": bool(term_reason),
        "termination_reason": term_reason,
        "peak_abs_roll_deg": round(max(abs_rolls, default=0.0), 3),
        "signed_roll_at_peak_deg": round(signed_at_peak, 3),
        "recurrent_peaks_over_5deg": max(
            _separated_peak_count(rolls, threshold=5.0, dt=1.0 / hz),
            _separated_peak_count([-v for v in rolls], threshold=5.0,
                                  dt=1.0 / hz)),
        "speed_m_s": round((x_final - x_walk) / elapsed_walk, 4),
    }


def summarize(rows: list[dict], dose_name: str,
              policy_name: str = "ps200") -> dict:
    grp = [r for r in rows
           if r["dose"] == dose_name and r["policy"] == policy_name]
    if not grp:
        return {}
    return {
        "policy": policy_name,
        "dose": dose_name,
        "group": grp[0]["group"],
        "pct": grp[0]["pct"],
        "n": len(grp),
        "med_peak_abs_roll_deg": round(
            float(median(r["peak_abs_roll_deg"] for r in grp)), 3),
        "med_signed_roll_deg": round(
            float(median(r["signed_roll_at_peak_deg"] for r in grp)), 3),
        "med_recurrent_peaks": round(
            float(median(r["recurrent_peaks_over_5deg"] for r in grp)), 1),
        "med_speed_m_s": round(
            float(median(r["speed_m_s"] for r in grp)), 4),
        "fall_frac": round(sum(r["terminated"] for r in grp) / len(grp), 3),
    }


def _table(summaries: list[dict]) -> list[str]:
    lines = [
        "| policy | dose | group | pct | med peak roll | med signed roll | "
        "recurrent | speed m/s | fall_frac |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for s in summaries:
        if not s:
            continue
        lines.append(
            f"| {s['policy']} | {s['dose']} | {s['group'] or '-'} | "
            f"{s['pct']} | {s['med_peak_abs_roll_deg']} | "
            f"{s['med_signed_roll_deg']} | {s['med_recurrent_peaks']} | "
            f"{s['med_speed_m_s']} | {s['fall_frac']} |")
    return lines


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    policy = load_np_policy(_policy_path(FROZEN_POLICY))
    rows: list[dict] = []
    for dose in DOSES:
        for seed in SEEDS:
            rows.append(rollout(dose, seed=seed, policy=policy))
    summaries = [summarize(rows, d.name) for d in DOSES]

    ctrl_rows: list[dict] = []
    for spec in CONTROL_POLICIES:
        cpolicy = load_np_policy(_policy_path(spec))
        for dose in SELECTIVITY_DOSES:
            for seed in SEEDS:
                ctrl_rows.append(
                    rollout(dose, seed=seed, policy=cpolicy, spec=spec))
    ctrl_summaries = [
        summarize(ctrl_rows, d.name, policy_name=spec.name)
        for spec in CONTROL_POLICIES for d in SELECTIVITY_DOSES]

    out_dir = args.out or (
        Path("logs/ckpt_eval")
        / f"foottorsionsoft_dose_probe_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(
        {"rows": rows, "summaries": summaries,
         "ctrl_rows": ctrl_rows, "ctrl_summaries": ctrl_summaries,
         "hardware_ps200_peak_roll_deg": HARDWARE_PS200_PEAK_ROLL_DEG},
        indent=2))

    lines = ["# foot_torsion_soft frozen-policy dose probe", "",
             f"Hardware PS200 peak roll target: "
             f"{HARDWARE_PS200_PEAK_ROLL_DEG} deg", "",
             "## Stage 1: dose ladder (ps200 fast parent)", ""]
    lines += _table(summaries)
    lines += ["", "## Stage 2: selectivity check (control policies)", ""]
    ps200_ctrl_summaries = [summarize(rows, d.name) for d in SELECTIVITY_DOSES]
    lines += _table(ps200_ctrl_summaries + ctrl_summaries)
    (out_dir / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nWrote {out_dir}")


if __name__ == "__main__":
    main()
