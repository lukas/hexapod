"""Held-out DR robustness gate (speed sim-to-real, 2026-09-13 order).

WHY: `docs/DR_JOINT_PANEL_2026-09-13.md` pre-registers the ARM-CTRL/
ARM-WIDE/ARM-STRUCT training comparison but its own text says "arms
launch only after the held-out gate harness exists" -- this module is
that harness, item (a) of the panel doc's "Next" list. It replays the
panel's own `heldout_manifest.json` ensembles (NEVER used for search/
ranking/model-selection, per the panel's own held-out split) against a
frozen parent and one or more trained-candidate policies, using the
EXACT SAME rollout mechanics as `probe_dr_joint_panel.rollout()` (same
env, same fixed-ensemble randomizer, same cmd pin), and reports the
panel doc's five gate criteria (a)-(e).

GATE (verbatim from the panel doc, this module's `--hard-frac` and
speed-loss comparator are this cycle's ENGINEERING CHOICE for the doc's
undefined terms -- recorded here, not an operator ruling, adjust freely):
  (a) candidate reduces the parent's held-out MEDIAN peak roll by >=30%,
      both on the full held-out set and on a "hard" subset (this module:
      the top `--hard-frac` (default 0.3) of the 16 held-out ensembles,
      ranked by the PARENT's own per-ensemble median peak roll -- i.e.
      the ensembles that bite the parent hardest);
  (b) zero falls (terminated=True) for the candidate across every
      held-out episode;
  (c) six-leg gait validity >=90% of held-out episodes for the candidate
      (this module: an episode is "gait-valid" when every one of the six
      `contact_duty` values lands in [0.05, 0.95], i.e. every leg both
      stands and swings -- no permanently sacrificed/planted leg);
  (d) robust speed loss <=20% vs parent on the SAME held-out ensembles
      (this module: candidate's held-out median speed >= 0.8x the
      PARENT's held-out median speed, both measured by this harness);
  (e) nominal (no ensemble) speed at the panel's own command pin >=90%
      of the parent's own nominal speed, both measured by this harness
      over the held-out seed set.

Usage (from `prototype_sts3215`)::

    uv run python -m rl_move.sim.eval_dr_robustness_gate \
        --panel-dir logs/ckpt_eval/dr_joint_panel_20260913 \
        --parent-name ps200 \
        --parent-artifact linux_control/policies/speed50hz_stride_ps200_lift14_massfix_sr105_acq10m.json \
        --candidate armstruct=linux_control/policies/<exported_candidate>.json \
        --out logs/ckpt_eval/dr_robustness_gate_<stamp>

Candidates may also be RAW SB3 ``.zip`` checkpoints (the trained DR
arms' native artifact — no export step needed):

    --candidate armwide=rl_move/sim/policies/ppo_goal_<candidate>.zip

The env contract for a .zip candidate is taken from the PARENT's
exported meta (see `CkptPolicy`); the parent artifact must therefore be
an exported .json.

Smoke/self-check (existing exported policies, no new checkpoint
required): substitute an already-exported control policy as the
"--candidate" to prove the pipeline produces sane, non-trivial deltas
end to end (see the speed track STATUS entry for a recorded run of
this kind) -- this is NOT a claim that policy is a real DR candidate.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from rl_move.sim.probe_dr_joint_panel import Ensemble, rollout
from rl_move.sim.probe_ps200_transfer import PolicySpec

ROOT = Path(__file__).resolve().parents[2]


class CkptPolicy:
    """Raw SB3 ``.zip`` checkpoint adapter for `probe_dr_joint_panel.rollout`.

    The trained DR arms produce SB3 checkpoints, not linux_control
    exports; the operator task requires the gate to load checkpoints
    directly. The env contract (control hz, speed band, safety deltas,
    phase hz ...) is NOT stored in the zip — it is supplied by ``meta``,
    taken from the PARENT's exported policy artifact: the pre-registered
    arms hold gait/reward/actuator envelope fixed, so the parent's
    deployment meta IS the candidate's env contract. A candidate with a
    different obs layout fails the rollout's own obs-shape assert.
    """

    def __init__(self, zip_path: str | Path, meta: dict):
        from stable_baselines3 import PPO
        self._m = PPO.load(str(zip_path), device="cpu")
        self.meta = dict(meta)
        self.observation_space = self._m.observation_space

    def predict(self, obs, deterministic: bool = True):
        return self._m.predict(obs, deterministic=deterministic)

    def reset(self) -> None:
        pass


def resolve_policy(artifact: str | Path, parent_meta: dict | None):
    """None (exported-artifact path inside rollout) or a CkptPolicy."""
    if not str(artifact).endswith(".zip"):
        return None
    if parent_meta is None:
        raise ValueError(f"{artifact}: .zip candidates need the parent's "
                         "exported meta for the env contract")
    return CkptPolicy(artifact, parent_meta)


def load_heldout_ensembles(panel_dir: Path) -> tuple[list[Ensemble], dict]:
    """Reload the held-out ensembles + protocol from a panel run's manifest.

    `heldout_manifest.json`'s `ensembles` entries are
    `dataclasses.asdict(Ensemble(...))` -- reconstructing via
    `Ensemble(**d)` round-trips exactly (checked by
    `test_eval_dr_robustness_gate.py`).
    """
    manifest = json.loads((panel_dir / "heldout_manifest.json").read_text())
    ens = [Ensemble(**d) for d in manifest["ensembles"]]
    if not ens:
        raise ValueError(f"{panel_dir}: heldout_manifest.json has no "
                          "ensembles -- wrong/empty panel dir?")
    proto = {
        "heldout_seeds": tuple(manifest["heldout_seeds"]),
        "episode_s": float(manifest["episode_s"]),
        "cmd_m_s": float(manifest["cmd_m_s"]),
    }
    return ens, proto


def gait_valid(row: dict) -> bool:
    """True iff every one of the six legs both stood AND swung.

    Uses the already-computed `contact_duty` (fraction of ticks each
    foot was in contact) from `probe_dr_joint_panel.rollout()` -- a
    duty pinned at 0 (never touches) or 1 (planted/dragged the whole
    episode) is a sacrificed/non-cycling leg, not a walking gait.
    """
    duty = row.get("contact_duty") or []
    if len(duty) != 6:
        return False
    return all(0.05 <= d <= 0.95 for d in duty)


def _episode_rows(spec: PolicySpec, ensembles: list[Ensemble],
                   seeds: tuple[int, ...], *, episode_s: float,
                   cmd_m_s: float, policy=None) -> list[dict]:
    return [rollout(spec, e, seed=s, episode_s=episode_s, cmd_m_s=cmd_m_s,
                    policy=policy)
            for e in ensembles for s in seeds]


def _nominal_rows(spec: PolicySpec, seeds: tuple[int, ...], *,
                  episode_s: float, cmd_m_s: float, policy=None) -> list[dict]:
    return [rollout(spec, None, seed=s, episode_s=episode_s, cmd_m_s=cmd_m_s,
                    policy=policy)
            for s in seeds]


def hard_subset(parent_rows: list[dict], ensembles: list[Ensemble],
                hard_frac: float) -> set[str]:
    """Names of the ensembles that bite the PARENT hardest (by its own
    per-ensemble median peak roll across held-out seeds)."""
    by_name: dict[str, list[float]] = {e.name: [] for e in ensembles}
    for r in parent_rows:
        if r["ensemble"] in by_name:
            by_name[r["ensemble"]].append(r["peak_abs_roll_deg"])
    ranked = sorted(by_name.items(), key=lambda kv: median(kv[1])
                    if kv[1] else 0.0, reverse=True)
    n_hard = max(1, round(hard_frac * len(ranked)))
    return {name for name, _ in ranked[:n_hard]}


def gate_report(*, parent_name: str, parent_rows: list[dict],
                parent_nominal: list[dict], cand_name: str,
                cand_rows: list[dict], cand_nominal: list[dict],
                ensembles: list[Ensemble], hard_frac: float) -> dict:
    hard = hard_subset(parent_rows, ensembles, hard_frac)

    def med_roll(rows, names=None):
        vals = [r["peak_abs_roll_deg"] for r in rows
                if names is None or r["ensemble"] in names]
        return float(median(vals)) if vals else 0.0

    def med_speed(rows):
        vals = [r["forward_speed_after_2s_m_s"] for r in rows]
        return float(median(vals)) if vals else 0.0

    parent_roll_all = med_roll(parent_rows)
    parent_roll_hard = med_roll(parent_rows, hard)
    cand_roll_all = med_roll(cand_rows)
    cand_roll_hard = med_roll(cand_rows, hard)
    parent_speed_ho = med_speed(parent_rows)
    cand_speed_ho = med_speed(cand_rows)
    parent_speed_nom = med_speed(parent_nominal)
    cand_speed_nom = med_speed(cand_nominal)

    def reduction(parent_v, cand_v):
        return (1.0 - cand_v / parent_v) if parent_v > 1e-9 else 0.0

    roll_reduction_all = reduction(parent_roll_all, cand_roll_all)
    roll_reduction_hard = reduction(parent_roll_hard, cand_roll_hard)
    falls = sum(1 for r in cand_rows if r["terminated"])
    n_ep = len(cand_rows)
    valid_frac = (sum(1 for r in cand_rows if gait_valid(r)) / n_ep
                  if n_ep else 0.0)
    speed_loss_robust = reduction(parent_speed_ho, cand_speed_ho)
    speed_ratio_nom = (cand_speed_nom / parent_speed_nom
                       if parent_speed_nom > 1e-9 else 0.0)

    checks = {
        "a_roll_reduction_overall_ge_30pct": roll_reduction_all >= 0.30,
        "a_roll_reduction_hard_ge_30pct": roll_reduction_hard >= 0.30,
        "b_zero_falls": falls == 0,
        "c_gait_valid_ge_90pct": valid_frac >= 0.90,
        "d_robust_speed_loss_le_20pct": speed_loss_robust <= 0.20,
        "e_nominal_speed_ge_90pct_parent": speed_ratio_nom >= 0.90,
    }
    return {
        "parent": parent_name,
        "candidate": cand_name,
        "n_heldout_ensembles": len(ensembles),
        "n_hard_ensembles": len(hard),
        "hard_ensemble_names": sorted(hard),
        "n_episodes_per_policy": n_ep,
        "parent_med_peak_roll_deg_overall": round(parent_roll_all, 3),
        "parent_med_peak_roll_deg_hard": round(parent_roll_hard, 3),
        "candidate_med_peak_roll_deg_overall": round(cand_roll_all, 3),
        "candidate_med_peak_roll_deg_hard": round(cand_roll_hard, 3),
        "roll_reduction_overall": round(roll_reduction_all, 4),
        "roll_reduction_hard": round(roll_reduction_hard, 4),
        "candidate_falls": falls,
        "candidate_gait_valid_frac": round(valid_frac, 4),
        "parent_heldout_med_speed_m_s": round(parent_speed_ho, 4),
        "candidate_heldout_med_speed_m_s": round(cand_speed_ho, 4),
        "robust_speed_loss_vs_parent": round(speed_loss_robust, 4),
        "parent_nominal_med_speed_m_s": round(parent_speed_nom, 4),
        "candidate_nominal_med_speed_m_s": round(cand_speed_nom, 4),
        "nominal_speed_ratio_vs_parent": round(speed_ratio_nom, 4),
        "checks": checks,
        "gate_pass": all(checks.values()),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--panel-dir", type=Path, required=True,
                    help="dr_joint_panel_* output dir with "
                         "heldout_manifest.json")
    ap.add_argument("--parent-name", default="ps200")
    ap.add_argument("--parent-artifact", type=Path, required=True)
    ap.add_argument("--candidate", action="append", required=True,
                    help="name=artifact_path, repeatable")
    ap.add_argument("--hard-frac", type=float, default=0.3)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    ensembles, proto = load_heldout_ensembles(args.panel_dir)
    seeds = proto["heldout_seeds"]
    episode_s = proto["episode_s"]
    cmd_m_s = proto["cmd_m_s"]

    parent_spec = PolicySpec(args.parent_name, str(args.parent_artifact))
    print(f"[gate] parent={parent_spec.name} heldout ensembles="
          f"{len(ensembles)} seeds={seeds}", flush=True)
    parent_rows = _episode_rows(parent_spec, ensembles, seeds,
                                episode_s=episode_s, cmd_m_s=cmd_m_s)
    parent_nominal = _nominal_rows(parent_spec, seeds, episode_s=episode_s,
                                   cmd_m_s=cmd_m_s)

    # Env-contract meta for raw .zip candidates comes from the parent
    # export (arms hold the env contract fixed by pre-registration).
    from rl_move.np_policy import load_np_policy
    parent_meta = load_np_policy(args.parent_artifact).meta

    reports = []
    for cand_arg in args.candidate:
        name, _, artifact = cand_arg.partition("=")
        if not artifact:
            ap.error(f"--candidate must be name=path, got {cand_arg!r}")
        cand_spec = PolicySpec(name, artifact)
        cand_policy = resolve_policy(artifact, parent_meta)
        print(f"[gate] candidate={name}"
              + (" (raw SB3 zip checkpoint)" if cand_policy else ""),
              flush=True)
        cand_rows = _episode_rows(cand_spec, ensembles, seeds,
                                  episode_s=episode_s, cmd_m_s=cmd_m_s,
                                  policy=cand_policy)
        cand_nominal = _nominal_rows(cand_spec, seeds, episode_s=episode_s,
                                     cmd_m_s=cmd_m_s, policy=cand_policy)
        report = gate_report(
            parent_name=parent_spec.name, parent_rows=parent_rows,
            parent_nominal=parent_nominal, cand_name=name,
            cand_rows=cand_rows, cand_nominal=cand_nominal,
            ensembles=ensembles, hard_frac=args.hard_frac)
        print(f"[gate] {name}: pass={report['gate_pass']} "
              f"roll_reduction={report['roll_reduction_overall']:.2f}/"
              f"{report['roll_reduction_hard']:.2f} falls="
              f"{report['candidate_falls']} gait_valid="
              f"{report['candidate_gait_valid_frac']:.2f} "
              f"speed_loss={report['robust_speed_loss_vs_parent']:.2f} "
              f"nominal_ratio={report['nominal_speed_ratio_vs_parent']:.2f}",
              flush=True)
        reports.append(report)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = args.out or (ROOT / "logs" / "ckpt_eval"
                           / f"dr_robustness_gate_{stamp}")
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "panel_dir": str(args.panel_dir),
        "protocol": proto,
        "hard_frac": args.hard_frac,
        "parent": dataclasses.asdict(parent_spec),
        "reports": reports,
    }
    (out_dir / "gate_report.json").write_text(json.dumps(payload, indent=2))
    print(f"wrote {out_dir / 'gate_report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
