"""Frozen-policy dose ladder: structured, concentrated PER-FOOT CONTACT
compliance vs. the PS200 hardware roll signature (2026-09-20, speed track).

Background (`rl_docs/tracks/speed/STATUS.md` 09-20;
`rl_docs/HEXAPOD2_DIGITAL_TWIN_2026-09-12.md`): the 09-12 Hexapod-2
digital-twin study built and replayed two BODY-domain compliance
mechanisms against the real 25-run PS200/control matrix -- a uniform
six-leg-ROOT flex (``leg_mount_flex``) and a per-joint post-encoder
series hinge (``joint_series_flex``). Root flex was REJECTED (it
worsens the held-out gate 11/21->6/21 and moves PS200 the WRONG
direction: 3.57->3.35 deg sim against 16.69 deg hardware, while
inventing roll in the walkteach negative control). Series-joint flex
modestly IMPROVES aggregate held-out accuracy (11/21->13/21) but ALSO
moves PS200 specifically the wrong way (3.57->2.70 deg). Neither study
ever dosed FOOT-level contact compliance -- a worn/soft pad or a
squashed print is a persistent, per-FOOT-concentrated defect, distinct
from the existing GLOBAL, uniform ``contact_stiff_scale`` (ground and
feet alike) and from per-foot FRICTION (``foot_friction_scale``). This
probe builds and doses the new ``dr.foot_contact_soft_pct``/-group axis
(see ``domain_rand.py``, 2026-09-20) alone, then composes the best dose
with the 09-12 study's own frozen ``joint_series_flex_probe.json``
candidate -- the first test of whether a genuinely different BODY-domain
mechanism can recover the direction series-flex alone gets wrong, the
same "jointly sampled ensemble" mandate DESIGN.md's diagnose step names
and the 09-17 backlash+link-length probe already established as this
saga's own precedent for composing two individually-promising
mechanisms.

Same isolation convention as every prior probe in this saga
(``probe_massbias_dose``/``probe_backlash_dose``/``probe_linklenbias_
dose``): frozen ``ps200`` policy, ``dr_scale=0.0`` so ONLY the explicit
override(s) are active (no ordinary-training-DR noise contaminating the
read), pinned 0.10 m/s forward command, seeds 0-3, 15 s episodes. No
training arm is funded here -- this stays a frozen-policy probe per the
operator's diagnose-before-train order (DESIGN.md "Diagnose interacting
model error").

Run from ``prototype_sts3215``::

    uv run python -m rl_move.sim.probe_footcontactsoft_dose

Outputs ``results.json`` and ``report.md`` beneath
``logs/ckpt_eval/footcontactsoft_dose_probe_<UTC>`` unless ``--out`` is
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
SERIES_FLEX_JSON = Path(__file__).resolve().parent / "joint_series_flex_probe.json"


@dataclass(frozen=True)
class Dose:
    name: str
    pct: float = 0.0            # magnitude, applied as (pct, pct) -- a
                                 # fixed dose. Scale factor on the foot
                                 # geom's solref timeconst is (1+pct):
                                 # pct=1.0 doubles it (on top of the
                                 # existing 3x-softened default), pct=8.0
                                 # is a 9x increase.
    group: str = ""
    compose_series_flex: bool = False


DOSES = (
    Dose("none", 0.0, ""),
    Dose("symmetric_lo", 0.5, ""),
    Dose("symmetric_hi", 2.0, ""),
    Dose("right_lo", 0.5, "right"),
    Dose("right_med", 2.0, "right"),
    Dose("right_hi", 4.0, "right"),
    Dose("right_extreme", 8.0, "right"),
    Dose("left_hi", 4.0, "left"),
    Dose("single_leg_extreme", 8.0, "leg0"),
    Dose("front_hi", 4.0, "front"),
    Dose("rear_hi", 4.0, "rear"),
)

# Selectivity check (probe_ps200_transfer's own convention): re-run the
# doses that read clearly above the ps200 noise floor on the two
# lower-roll CONTROL policies too.
SELECTIVITY_DOSES = (
    Dose("none", 0.0, ""),
    Dose("right_hi", 4.0, "right"),
    Dose("right_extreme", 8.0, "right"),
)


def _load_series_flex_cfg() -> dict:
    blob = json.loads(SERIES_FLEX_JSON.read_text())
    section = blob["joint_series_flex"]
    return {**section, "enabled": 1}


def _dose_cfg(dose: Dose) -> dict:
    cfg: dict = {}
    if dose.pct > 0.0:
        cfg["foot_contact_soft_pct"] = f"{dose.pct},{dose.pct}"
        if dose.group:
            cfg["foot_contact_soft_group"] = dose.group
    return cfg


def rollout(dose: Dose, *, seed: int, policy=None,
            spec: PolicySpec = FROZEN_POLICY) -> dict:
    if policy is None:
        policy = load_np_policy(_policy_path(spec))
    cfg = _policy_cfg(policy.meta, Intervention(name="footcontactsoft"))
    cfg.setdefault("dr", {}).update(_dose_cfg(dose))
    if dose.compose_series_flex:
        # struct_comp (the legacy gain-reduction compliance
        # approximation, on by default in the ps200 training cfg) and
        # joint_series_flex are mutually exclusive (sim_env guards
        # against double-counting an uncalibrated compliance effect).
        # Series-flex is the more physical of the two, so it wins here.
        cfg["struct_comp"] = {"enabled": 0}
        cfg["joint_series_flex"] = _load_series_flex_cfg()
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
        "compose_series_flex": dose.compose_series_flex,
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
              policy_name: str = "ps200",
              compose_series_flex: bool = False) -> dict:
    grp = [r for r in rows
           if r["dose"] == dose_name and r["policy"] == policy_name
           and r["compose_series_flex"] == compose_series_flex]
    if not grp:
        return {}
    return {
        "policy": policy_name,
        "dose": dose_name,
        "group": grp[0]["group"],
        "pct": grp[0]["pct"],
        "compose_series_flex": compose_series_flex,
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
        "| policy | dose | group | pct | +series_flex | med peak roll | "
        "med signed roll | recurrent | speed m/s | fall_frac |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in summaries:
        if not s:
            continue
        lines.append(
            f"| {s['policy']} | {s['dose']} | {s['group'] or '-'} | "
            f"{s['pct']} | {s['compose_series_flex']} | "
            f"{s['med_peak_abs_roll_deg']} | "
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
    # 50 Hz control policies.
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

    # Stage 3: compose the best-reading foot-contact dose from Stage 1
    # with the 09-12 digital-twin study's own frozen joint_series_flex
    # candidate -- does per-foot compliance recover what pure series-flex
    # gets wrong-direction on PS200 (rl_docs/HEXAPOD2_DIGITAL_TWIN_
    # 2026-09-12.md), without giving up series-flex's own general holdout
    # improvement? Picks the dose with the largest ps200 median peak roll
    # from Stage 1 (excluding "none").
    best = max((s for s in summaries if s and s["pct"] > 0.0),
               key=lambda s: s["med_peak_abs_roll_deg"], default=None)
    compose_rows: list[dict] = []
    compose_summaries: list[dict] = []
    if best is not None:
        series_only = Dose("series_flex_only", 0.0, "",
                            compose_series_flex=True)
        composed = Dose(f"composed_{best['dose']}", best["pct"],
                        best["group"], compose_series_flex=True)
        for dose in (series_only, composed):
            for seed in SEEDS:
                compose_rows.append(rollout(dose, seed=seed, policy=policy))
        compose_summaries = [
            summarize(compose_rows, series_only.name,
                      compose_series_flex=True),
            summarize(compose_rows, composed.name, compose_series_flex=True),
        ]

    out_dir = args.out or (
        Path("logs/ckpt_eval")
        / f"footcontactsoft_dose_probe_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(
        {"rows": rows, "summaries": summaries,
         "ctrl_rows": ctrl_rows, "ctrl_summaries": ctrl_summaries,
         "compose_rows": compose_rows,
         "compose_summaries": compose_summaries,
         "hardware_ps200_peak_roll_deg": HARDWARE_PS200_PEAK_ROLL_DEG},
        indent=2))

    lines = ["# foot_contact_soft frozen-policy dose probe", "",
             f"Hardware PS200 peak roll target: "
             f"{HARDWARE_PS200_PEAK_ROLL_DEG} deg", "",
             "## Stage 1: dose ladder (ps200 fast parent)", ""]
    lines += _table(summaries)
    lines += ["", "## Stage 2: selectivity check (control policies)", ""]
    ps200_ctrl_summaries = [summarize(rows, d.name) for d in SELECTIVITY_DOSES]
    lines += _table(ps200_ctrl_summaries + ctrl_summaries)
    lines += ["", "## Stage 3: composed with 09-12 series-flex candidate "
              "(ps200 only)", ""]
    lines += _table([summarize(rows, "none")] + compose_summaries)
    (out_dir / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nWrote {out_dir}")


if __name__ == "__main__":
    main()
