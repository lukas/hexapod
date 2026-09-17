"""Frozen-policy JOINT probe: concentrated joint BACKLASH combined with
concentrated per-leg LINK-LENGTH bias (2026-09-17, speed track).

Background (`rl_docs/tracks/speed/STATUS.md` 09-14/09-17): every mechanism
DESIGN.md names has now been probed and (where warranted) trained
CONCENTRATED but ONE AT A TIME -- mass/CoM (NULL), latency (NULL),
stick-slip (NULL), joint backlash (partial magnitude match, ~29-31% of the
16.78-deg PS200 signature at `right_16`, but its own trained DR arm FAILED
the held-out robustness gate), link-length bias (real dose-dependent
magnitude match, 22-32% at 0.20-0.30, but FAILS the selectivity check --
the two slower CONTROL gaits roll the SAME amount and lose far more speed
than the fast ps200 parent, the opposite of the hardware pattern). Per the
operator's own 09-13 order (`DESIGN.md` "Diagnose interacting model
error" -- "Search jointly sampled and correlated/asymmetric ensembles",
not one-factor probes) and the two closure notes' own named remaining
option ("a genuinely new mechanism family... e.g. a mechanism combining a
real positional error with gait-phase timing"), this is the first probe
in the whole saga that actually composes two mechanisms together instead
of testing each in isolation -- and it composes the ONLY two mechanisms
that individually cleared the roll noise floor with a real signed effect,
rather than an arbitrary/unmotivated pair. Backlash is a DYNAMIC,
load/direction-coupled position defect (bites at specific reversal
moments, cadence-linked); link-length is a STATIC, permanent kinematic
offset (bites every tick, gait-agnostic). A gait with a higher reversal
rate (the fast ps200 parent) may experience backlash's per-reversal
kick more often per unit time than a slower gait even at the same
per-joint gap -- combining it with a length bias that alone supplies the
missing MAGNITUDE could, in principle, recover both the scale AND the
selectivity that neither mechanism alone achieved. This probe tests that
hypothesis directly; it does not assume the answer.

Same isolation convention as every prior probe in this saga (`probe_
massbias_dose`/`probe_backlash_dose`/`probe_linklenbias_dose`, the first
two deleted as one-off scripts once their result was recorded): frozen
policy, `dr_scale=0.0` so ONLY the explicit `dr.joint_backlash_*`/
`dr.link_len_bias_*` overrides are active (no ordinary training-DR noise
contaminating the read), pinned 0.10 m/s forward command, seeds 0-3,
15 s episodes. No training arm is funded here -- this stays a
frozen-policy probe per the operator's diagnose-before-train order.

Run from ``prototype_sts3215``::

    uv run python -m rl_move.sim.probe_combined_backlash_linklen

Outputs ``results.json`` and ``report.md`` beneath
``logs/ckpt_eval/combined_backlash_linklen_probe_<UTC>`` unless ``--out``
is supplied.
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
    backlash_deg: float = 0.0
    backlash_group: str = ""
    linklen_pct: float = 0.0
    linklen_group: str = ""


# Stage 1: ps200-only ladder. Single-mechanism reference rows reproduce
# each mechanism's own prior best-reading dose (backlash right_16,
# link-length right_025) plus a lower "weak" dose of each (8 deg / 0.15),
# then every weak x strong cross of the two combined.
DOSES = (
    Dose("none"),
    Dose("backlash_8", backlash_deg=8.0, backlash_group="right"),
    Dose("backlash_16", backlash_deg=16.0, backlash_group="right"),
    Dose("linklen_15", linklen_pct=0.15, linklen_group="right"),
    Dose("linklen_25", linklen_pct=0.25, linklen_group="right"),
    Dose("combo_8_15", backlash_deg=8.0, backlash_group="right",
         linklen_pct=0.15, linklen_group="right"),
    Dose("combo_16_25", backlash_deg=16.0, backlash_group="right",
         linklen_pct=0.25, linklen_group="right"),
    Dose("combo_8_25", backlash_deg=8.0, backlash_group="right",
         linklen_pct=0.25, linklen_group="right"),
    Dose("combo_16_15", backlash_deg=16.0, backlash_group="right",
         linklen_pct=0.15, linklen_group="right"),
)

# Stage 2 (selectivity): filled in by main() from Stage 1's own results --
# re-run the combo dose(s) that clear the ps200 noise floor with the
# smallest speed cost, on the two control policies, same convention as
# probe_linklenbias_dose's own stage 2.
SELECTIVITY_DOSE_NAMES = ("combo_8_15", "combo_16_25")


def _dose_cfg(dose: Dose) -> dict:
    d: dict = {}
    if dose.backlash_deg > 0.0:
        d["joint_backlash_deg"] = f"{dose.backlash_deg},{dose.backlash_deg}"
        if dose.backlash_group:
            d["joint_backlash_group"] = dose.backlash_group
    if dose.linklen_pct > 0.0:
        d["link_len_bias_pct"] = f"{dose.linklen_pct},{dose.linklen_pct}"
        if dose.linklen_group:
            d["link_len_bias_group"] = dose.linklen_group
    return d


def rollout(dose: Dose, *, seed: int, policy=None,
            spec: PolicySpec = FROZEN_POLICY) -> dict:
    if policy is None:
        policy = load_np_policy(_policy_path(spec))
    cfg = _policy_cfg(policy.meta, Intervention(name="combinedbacklashlinklen"))
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
        "backlash_deg": dose.backlash_deg,
        "linklen_pct": dose.linklen_pct,
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
        "backlash_deg": grp[0]["backlash_deg"],
        "linklen_pct": grp[0]["linklen_pct"],
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
        "| policy | dose | backlash deg | linklen pct | med peak roll | "
        "med signed roll | recurrent | speed m/s | fall_frac |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in summaries:
        if not s:
            continue
        lines.append(
            f"| {s['policy']} | {s['dose']} | {s['backlash_deg']} | "
            f"{s['linklen_pct']} | {s['med_peak_abs_roll_deg']} | "
            f"{s['med_signed_roll_deg']} | {s['med_recurrent_peaks']} | "
            f"{s['med_speed_m_s']} | {s['fall_frac']} |")
    return lines


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    # Stage 1: dose ladder + combos on the frozen ps200 fast parent alone.
    policy = load_np_policy(_policy_path(FROZEN_POLICY))
    rows: list[dict] = []
    for dose in DOSES:
        for seed in SEEDS:
            rows.append(rollout(dose, seed=seed, policy=policy))
    summaries = [summarize(rows, d.name) for d in DOSES]

    # Stage 2: selectivity check on the two lower-roll CONTROL policies,
    # same convention as probe_linklenbias_dose (a mechanism only earns a
    # training recommendation if it reproduces the PS200 scale WITHOUT
    # doing the same thing to these two).
    sel_doses = [d for d in DOSES
                 if d.name in ("none",) + SELECTIVITY_DOSE_NAMES]
    ctrl_rows: list[dict] = []
    ctrl_summaries: list[dict] = []
    for spec in CONTROL_POLICIES:
        cpolicy = load_np_policy(_policy_path(spec))
        for dose in sel_doses:
            for seed in SEEDS:
                ctrl_rows.append(
                    rollout(dose, seed=seed, policy=cpolicy, spec=spec))
        ctrl_summaries.extend(
            summarize(ctrl_rows, d.name, policy_name=spec.name)
            for d in sel_doses)

    out_dir = args.out or (
        Path("logs/ckpt_eval")
        / f"combined_backlash_linklen_probe_"
          f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(
        {"rows": rows, "summaries": summaries,
         "ctrl_rows": ctrl_rows, "ctrl_summaries": ctrl_summaries,
         "hardware_ps200_peak_roll_deg": HARDWARE_PS200_PEAK_ROLL_DEG},
        indent=2))

    lines = ["# combined backlash + link-length-bias frozen-policy probe",
             "",
             f"Hardware PS200 peak roll target: "
             f"{HARDWARE_PS200_PEAK_ROLL_DEG} deg", "",
             "## Stage 1: dose ladder + combos (ps200 fast parent)", ""]
    lines += _table(summaries)
    lines += ["", "## Stage 2: selectivity check (control policies)", ""]
    ps200_sel_summaries = [summarize(rows, d.name) for d in sel_doses]
    lines += _table(ps200_sel_summaries + ctrl_summaries)
    (out_dir / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nWrote {out_dir}")


if __name__ == "__main__":
    main()
