"""Build a goal.walk_entry_bank / goal.lower_start_bank npz from one or
more `eval_modeseq.py --dump-seg-qpos` dumps (2026-09-23, standwalk
STATUS ~18:3x: the walk_entry/lower_entry composed-session poses that
diagnostic already harvests are exactly the "policy's OWN real
handoff pose" bank goal.rise_start_bank's mechanism generalizes to,
same as harvest_lower_endpoints.py built the rise bank from a bespoke
rollout -- here the poses are already sitting in the diagnostic's own
npz, so this tool is a pure filter/reshape/relabel, no new rollout.

v2 (2026-09-23, standwalk ~19:5x): also pools each row's ``qvel_rad_s``
(MuJoCo-native hinge frame, no conversion needed -- unlike ``q_rad``
this is NOT run through the robot_abs contract, it is consumed
directly as ``data.qvel[env._vadr]``) alongside the position. This is
the ingredient the position-only v1 bank never carried: the exposure-
fraction position blend (goal.walk_entry_bank_frac / goal.
lower_start_bank_frac) was refuted 6/6 (rise + walk sides,
CURRENT_TRUTHS 2026-09-23 ~19:3x) in part because even a specialist
exposed to the exact harvested JOINT ANGLE still went through the
standard ~1.2s static PD settle (env.reset()'s _place_at_plant +
_settle sequence), which drives velocity to ~zero regardless of what
the pose is -- so no bank episode, at any dose, ever taught the
specialist to handle the real MOMENTUM a live composed-session
handoff actually carries (a walk-exiting or lower-exiting robot is
still moving, not standing still). ``qvel_mujoco`` here plus sim_env.
py's ``_apply_bank_qvel_handoff`` (goal.bank_qvel_restore) close that
gap: velocity is restored AFTER the ordinary settle, at the exact
reset() insertion point _apply_walk_reverse_handoff already uses for
the same reason.

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


def extract_bank_rows(npz_paths: list[Path],
                       tag: str) -> tuple[np.ndarray, np.ndarray]:
    """Pool every row tagged ``tag`` (e.g. "walk_entry"/"lower_entry")
    across the given --dump-seg-qpos npz files into one (K,N_JOINTS)
    q_rad (robot_abs) array plus its matching (K,N_JOINTS) qvel_rad_s
    array (MuJoCo-native hinge frame, straight from the dump -- see
    module docstring). Raises if a file has no matching rows (a
    silent empty bank is a footgun, not a legitimate output)."""
    q_rows, qvel_rows = [], []
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
        q_rows.append(q_deg)
        if "qvel_rad_s" not in d.files:
            raise ValueError(
                f"{p}: missing qvel_rad_s -- re-dump with a current "
                "eval_modeseq.py --dump-seg-qpos (qvel has been "
                "captured since before this tool existed)")
        qvel = np.asarray(d["qvel_rad_s"], dtype=float)[mask]
        if qvel.shape != q_deg.shape:
            raise ValueError(
                f"{p}: qvel_rad_s shape {qvel.shape} != q_deg shape "
                f"{q_deg.shape}")
        qvel_rows.append(qvel)
    return (np.concatenate(q_rows, axis=0) * DEG2RAD,
            np.concatenate(qvel_rows, axis=0))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--npz", type=Path, nargs="+", required=True,
                    help="one or more --dump-seg-qpos npz files")
    ap.add_argument("--tag", required=True,
                    help='seg tag to pool, e.g. "walk_entry"/'
                         '"lower_entry"')
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    q_rad, qvel_mujoco = extract_bank_rows(args.npz, args.tag)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.out, q_rad=q_rad, qvel_mujoco=qvel_mujoco,
             joint_frame=FRAME_ROBOT_ABS,
             joint_contract=JOINT_CONTRACT,
             source_npz=[str(p) for p in args.npz], tag=args.tag)
    print(f"wrote {args.out}: {q_rad.shape[0]} rows from "
         f"{len(args.npz)} file(s), tag={args.tag!r}, qvel included")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
