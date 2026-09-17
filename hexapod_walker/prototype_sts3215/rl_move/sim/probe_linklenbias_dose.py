"""Frozen-policy dose ladder: structured, concentrated PER-LEG LINK-LENGTH
bias vs. the PS200 hardware roll signature (2026-09-17, speed track).

Background (`rl_docs/tracks/speed/STATUS.md` 2026-09-14 ~14:3x): every
DR_JOINT_PANEL training arm (CTRL/WIDE/STRUCT/COMBO/ADAPT/BACKLASH) has
closed 6/6 against the held-out >=30% roll-robustness gate, and every
DESIGN.md-named frozen-policy mechanism family tried so far -- backlash
(partial, ~29-31% match, best to date), latency (NULL), stick-slip
(NULL), per-leg mass/CoM/inertia bias (NULL) -- has now been probed in
its CONCENTRATED (single-group) form.  DESIGN.md separately names "link
length and per-leg asymmetric manufacturing error" alongside the
mass/CoM family; the length half of that pair has never been built or
probed concentrated (only symmetric per-leg-independent jitter exists:
``link_len_scale_pct``/``link_len_leg_pct``).  Mechanistically, length
is a POSITION/KINEMATIC-domain defect (like backlash, unlike mass, which
the massbias closure showed is absorbed by the position-controlled
actuators without drifting) -- the policy's own IK still assumes NOMINAL
segment lengths, so a genuine length mismatch is a persistent geometric
error the gait carries forward every step, the same domain that made
backlash the best-to-date match.

Same isolation convention as ``probe_massbias_dose``/``probe_backlash_
dose`` (deleted as one-off scripts once their result was recorded; this
one follows the identical protocol so it reproduces exactly):
frozen ``ps200`` policy, ``dr_scale=0.0`` so ONLY the explicit
``dr.link_len_bias_*`` override is active (no ordinary-training-DR noise
contaminating the read), pinned 0.10 m/s forward command, seeds 0-3,
15 s episodes.  No training arm is funded here -- this stays a
frozen-policy probe per the operator's diagnose-before-train order
(DESIGN.md "Diagnose interacting model error").

Run from ``prototype_sts3215``::

    uv run python -m rl_move.sim.probe_linklenbias_dose

Outputs ``results.json`` and ``report.md`` beneath
``logs/ckpt_eval/linklenbias_dose_probe_<UTC>`` unless ``--out`` is
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
# The two lower-roll 50 Hz CONTROL policies (probe_ps200_transfer's own
# selectivity convention -- a candidate mechanism only earns a training
# recommendation if it reproduces the PS200 scale WITHOUT doing the same
# thing to these two).
CONTROL_POLICIES = (POLICIES["walkteach"], POLICIES["allheading"])
SEEDS = (0, 1, 2, 3)
CMD_M_S = 0.10
EPISODE_S = 15.0


@dataclass(frozen=True)
class Dose:
    name: str
    pct: float = 0.0            # magnitude, applied as (pct, pct) -- a
                                 # fixed dose, not a sampled range, so
                                 # every seed in the ladder sees the
                                 # SAME bias magnitude and only the
                                 # per-episode noise floor (kp/kv/etc,
                                 # which dr_scale=0.0 already zeroes)
                                 # differs seed to seed.
    group: str = ""


DOSES = (
    Dose("none", 0.0, ""),
    Dose("symmetric_sanity", 0.15, ""),
    Dose("right_lo", 0.05, "right"),
    Dose("right_010", 0.10, "right"),
    Dose("right_hi", 0.15, "right"),
    Dose("right_020", 0.20, "right"),
    Dose("right_025", 0.25, "right"),
    Dose("right_extreme", 0.30, "right"),
    Dose("left_hi", 0.15, "left"),
    Dose("single_leg_extreme", 0.40, "leg0"),
    Dose("front_hi", 0.15, "front"),
    Dose("rear_hi", 0.15, "rear"),
)

# Selectivity check (probe_ps200_transfer's own convention): re-run these
# doses on the two lower-roll CONTROL policies too, at the SAME magnitude
# that read clearly above the ps200 noise floor on the ladder above.
SELECTIVITY_DOSES = (
    Dose("none", 0.0, ""),
    Dose("right_025", 0.25, "right"),
    Dose("right_extreme", 0.30, "right"),
)


def _dose_cfg(dose: Dose) -> dict:
    if dose.pct <= 0.0:
        return {}
    d = {"link_len_bias_pct": f"{dose.pct},{dose.pct}"}
    if dose.group:
        d["link_len_bias_group"] = dose.group
    return d


def rollout(dose: Dose, *, seed: int, policy=None,
            spec: PolicySpec = FROZEN_POLICY) -> dict:
    if policy is None:
        policy = load_np_policy(_policy_path(spec))
    cfg = _policy_cfg(policy.meta, Intervention(name="linklenbias"))
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

    # Stage 1: fine dose ladder on the frozen ps200 fast parent alone.
    policy = load_np_policy(_policy_path(FROZEN_POLICY))
    rows: list[dict] = []
    for dose in DOSES:
        for seed in SEEDS:
            rows.append(rollout(dose, seed=seed, policy=policy))
    summaries = [summarize(rows, d.name) for d in DOSES]

    # Stage 2: selectivity check -- the SAME doses on the two lower-roll
    # 50 Hz control policies (probe_ps200_transfer's own convention: a
    # mechanism only earns a training recommendation if it reproduces the
    # PS200 scale WITHOUT doing the same thing to these two).
    ctrl_rows: list[dict] = []
    ctrl_summaries: list[dict] = []
    for spec in CONTROL_POLICIES:
        cpolicy = load_np_policy(_policy_path(spec))
        for dose in SELECTIVITY_DOSES:
            for seed in SEEDS:
                ctrl_rows.append(
                    rollout(dose, seed=seed, policy=cpolicy, spec=spec))
        ctrl_summaries.extend(
            summarize(ctrl_rows, d.name, policy_name=spec.name)
            for d in SELECTIVITY_DOSES)

    out_dir = args.out or (
        Path("logs/ckpt_eval")
        / f"linklenbias_dose_probe_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(
        {"rows": rows, "summaries": summaries,
         "ctrl_rows": ctrl_rows, "ctrl_summaries": ctrl_summaries,
         "hardware_ps200_peak_roll_deg": HARDWARE_PS200_PEAK_ROLL_DEG},
        indent=2))

    lines = ["# link_len_bias frozen-policy dose probe", "",
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
