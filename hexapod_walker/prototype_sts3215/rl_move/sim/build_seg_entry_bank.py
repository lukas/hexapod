"""Build a goal.walk_entry_bank / goal.lower_start_bank npz from one or
more `eval_modeseq.py --dump-seg-qpos` dumps (2026-09-23, standwalk
STATUS ~18:3x: the walk_entry/lower_entry composed-session poses that
diagnostic already harvests are exactly the "policy's OWN real
handoff pose" bank goal.rise_start_bank's mechanism generalizes to,
same as harvest_lower_endpoints.py built the rise bank from a bespoke
rollout — here the poses are already sitting in the diagnostic's own
npz, so this tool is a pure filter/reshape/relabel, no new rollout.

Usage:
    uv run python -m rl_move.sim.build_seg_entry_bank \\
        --tag walk_entry \\
        --npz logs/.../segstate_dr07_n30.npz logs/.../segstate_dr10_n30.npz \\
        --out rl_move/sim/park_banks/walk_entry_bank_2026_09_23.npz
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from hexapod_core.joint_frame import FRAME_ROBOT_ABS, JOINT_CONTRACT
from rl_move.robot_state import DEG2RAD, N_JOINTS


def extract_bank_rows(npz_paths: list[Path], tag: str) -> np.ndarray:
    """Pool every row tagged ``tag`` (e.g. "walk_entry"/"lower_entry")
    across the given --dump-seg-qpos npz files into one (K,N_JOINTS)
    q_rad (robot_abs) array. Raises if a file has no matching rows
    (a silent empty bank is a footgun, not a legitimate output)."""
    rows = []
    for p in npz_paths:
        d = np.load(p, allow_pickle=True)
        if "seg" not in d.files or "q_deg" not in d.files:
            raise ValueError(
                f"{p}: not a --dump-seg-qpos npz (missing seg/q_deg)")
        mask = d["seg"] == tag
        n = int(mask.sum())
        if n == 0:
            raise ValueError(f"{p}: zero rows tagged {tag!r}")
        q_deg = np.asarray(d["q_deg"], dtype=float)[mask]
        if q_deg.shape[1] != N_JOINTS:
            raise ValueError(
                f"{p}: expected q_deg width {N_JOINTS}, got "
                f"{q_deg.shape[1]}")
        rows.append(q_deg)
    return np.concatenate(rows, axis=0) * DEG2RAD


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--npz", type=Path, nargs="+", required=True,
                    help="one or more --dump-seg-qpos npz files")
    ap.add_argument("--tag", required=True,
                    help='seg tag to pool, e.g. "walk_entry"/'
                         '"lower_entry"')
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    q_rad = extract_bank_rows(args.npz, args.tag)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.out, q_rad=q_rad, joint_frame=FRAME_ROBOT_ABS,
             joint_contract=JOINT_CONTRACT,
             source_npz=[str(p) for p in args.npz], tag=args.tag)
    print(f"wrote {args.out}: {q_rad.shape[0]} rows from "
         f"{len(args.npz)} file(s), tag={args.tag!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
