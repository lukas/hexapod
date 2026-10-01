"""Walkcurr lower-role over_current FORENSICS follow-up (2026-10-01):
does the WALK-EXIT physical state (static joint pose, body tilt, or
joint velocity at the rise->walk->lower handoff) predict WHICH leg a
subsequent over_current termination will trip on?

Scoped item: `lowerrole_overcurrent_forensics_2026-10-01/SUMMARY.md`'s
own "Conclusion" names this as "left as a next step, not a new
mechanism to design from scratch" -- this module is that next step.
Consumes the `*_over_current.json` dumps `eval_lifecycle_handoff_
rlonly.py --current-trace-dir` already writes (``walk_exit_qpos``/
``walk_exit_qvel`` + ``trip_summary``); no new sim/training run, no
mujoco/env dependency, pure array analysis -- testable with synthetic
data.

Method: z-score each of the 18 joint qpos (or qvel) columns across ALL
collected failing episodes, take the max |z| over each leg's 3 joints
as that leg's "entry-state abnormality" for the episode, then ask
whether the leg the SafetyLayer actually tripped on (``trip_summary``'s
``final_joint // 3``) tends to be the MOST abnormal leg at handoff. A
leg that is reliably the most-deviant one at entry would support an
entry-pose-conditioned stabilization mechanism (e.g. extra margin/
pricing keyed to how far a leg's handoff pose sits from the population
norm); a flat/null rank (no better than chance, mean rank == (6+1)/2
= 3.5 for 6 legs) rules that story out and points back at the dynamics
of the descent itself, not the handoff snapshot.
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np

N_LEGS = 6
N_JOINTS_PER_LEG = 3
FREE_JOINT_QPOS = 7  # x,y,z + quat(w,x,y,z)
FREE_JOINT_QVEL = 6  # linear(3) + angular(3)


def per_leg_abnormality(values: np.ndarray) -> np.ndarray:
    """``values``: (N episodes, 18 joints). Z-scores each joint column
    over the N episodes, returns (N, 6) per-leg abnormality = max |z|
    over that leg's 3 joints. A column with zero variance (e.g. N==1,
    or a joint that never varies) scores 0 everywhere (epsilon-guarded,
    no div-by-zero / NaN propagation)."""
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 2 or arr.shape[1] != N_LEGS * N_JOINTS_PER_LEG:
        raise ValueError(
            f"values must be (N, {N_LEGS * N_JOINTS_PER_LEG}), got {arr.shape}")
    mean = arr.mean(axis=0)
    std = arr.std(axis=0) + 1e-9
    z = (arr - mean) / std
    return np.abs(z).reshape(arr.shape[0], N_LEGS, N_JOINTS_PER_LEG).max(axis=2)


def trip_leg_rank(per_leg_abn_row: np.ndarray, final_leg: int) -> int:
    """1-based rank of ``final_leg`` in ``per_leg_abn_row`` sorted most-
    to-least abnormal (1 == the most-abnormal leg this episode). A
    mechanism where entry state predicts the trip leg would show a mean
    rank well below the no-information value (N_LEGS + 1) / 2 == 3.5."""
    order = np.argsort(-np.asarray(per_leg_abn_row, dtype=float))
    return int(list(order).index(final_leg)) + 1


def load_trace_records(trace_dirs: list[str]) -> list[dict]:
    """Load every ``*_over_current.json`` under ``trace_dirs`` (as
    written by ``eval_lifecycle_handoff_rlonly.py
    --current-trace-dir``), extracting the fields this module needs."""
    files: list[str] = []
    for d in trace_dirs:
        files.extend(sorted(glob.glob(str(Path(d) / "*_over_current.json"))))
    recs = []
    for f in files:
        d = json.loads(Path(f).read_text())
        qpos = np.asarray(d["walk_exit_qpos"], dtype=float)
        qvel = np.asarray(d["walk_exit_qvel"], dtype=float)
        final_joint = int(d["trip_summary"]["final_joint"])
        recs.append({
            "file": f,
            "joint_qpos": qpos[FREE_JOINT_QPOS:FREE_JOINT_QPOS + 18],
            "joint_qvel": qvel[FREE_JOINT_QVEL:FREE_JOINT_QVEL + 18],
            "final_joint": final_joint,
            "final_leg": final_joint // N_JOINTS_PER_LEG,
            "final_joint_label": d["trip_summary"]["final_joint_label"],
        })
    return recs


def summarize(recs: list[dict]) -> dict:
    """Mean trip-leg rank (lower == entry state predicts the trip leg,
    3.5 == no-information chance level for 6 legs) under both the
    static-pose (qpos) and velocity (qvel) readings, plus the fraction
    of episodes where the trip leg IS the single most-abnormal one."""
    if not recs:
        return {"n": 0}
    qpos_abn = per_leg_abnormality(np.stack([r["joint_qpos"] for r in recs]))
    qvel_abn = per_leg_abnormality(np.stack([r["joint_qvel"] for r in recs]))
    qpos_ranks = [trip_leg_rank(qpos_abn[i], r["final_leg"])
                  for i, r in enumerate(recs)]
    qvel_ranks = [trip_leg_rank(qvel_abn[i], r["final_leg"])
                  for i, r in enumerate(recs)]
    return {
        "n": len(recs),
        "chance_mean_rank": (N_LEGS + 1) / 2.0,
        "qpos_mean_rank": round(float(np.mean(qpos_ranks)), 3),
        "qpos_frac_rank1": round(float(np.mean(np.array(qpos_ranks) == 1)), 3),
        "qvel_mean_rank": round(float(np.mean(qvel_ranks)), 3),
        "qvel_frac_rank1": round(float(np.mean(np.array(qvel_ranks) == 1)), 3),
    }


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace_dirs", nargs="+",
                    help="one or more --current-trace-dir output dirs")
    args = p.parse_args()
    recs = load_trace_records(args.trace_dirs)
    print(json.dumps(summarize(recs), indent=2))


if __name__ == "__main__":
    main()
