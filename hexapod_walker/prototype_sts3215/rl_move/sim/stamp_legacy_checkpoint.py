"""Backfill the joint_frame/joint_contract stamp onto pre-migration
SB3 checkpoints (2026-09-02 ~22:0x operator merge 66c4af30 / b7e7ea05
"Unify hexapod vision and joint coordinates" added
``hexapod_core.joint_frame.require_checkpoint_joint_contract`` to gate
every ``--init-from``/respec warm-start; ``train_ppo_mjx.py`` stamps
NEW checkpoints (``model.joint_frame = FRAME_ROBOT_ABS`` at
construction) but every checkpoint SAVED BY A PROCESS LAUNCHED BEFORE
that merge landed has no such attribute and therefore no such key in
its saved ``data`` dict -- verified empirically 2026-09-03 across
checkpoints spanning multiple tracks (standwalk, joystick), i.e. this
is a fleet-wide gap, not one lineage's problem).

WHY BACKFILLING IS SAFE (not a numeric behavior change): the migration
did not touch ``rl_move/sim/joint_task.py``'s ``action_to_q_rad``/
``q_rad_to_action`` (the actual policy action<->joint mapping every
trained checkpoint's weights are numerically tied to) -- diffed
``b7e7ea05~1..b7e7ea05`` directly to confirm. The migration fixed
scattered POSE-LITERAL bugs in harness/probe code (e.g. a stale
mujoco-relative tuck-knee literal 2.40 -> the equivalent robot_abs
1.30) and added the stamp/enforcement; it did not change what a raw
action float means to any already-trained policy. Every checkpoint in
this tree was trained under the robot_abs joint convention (the sim
has used absolute hip/knee targets since long before this migration),
so stamping them ``robot_abs``/``robot_abs_tibia_v2`` is not a
reinterpretation -- it is recording a fact the file always had but
never wrote down.

Rewrites the zip's ``data`` JSON member in place (all other members --
policy.pth, optimizer state, pytorch_variables -- copied byte-for-byte
unchanged); refuses (raises) if the checkpoint's ``data`` already
disagrees with robot_abs (a real foreign-contract file, which this
tool must never paper over).

    uv run python -m rl_move.sim.stamp_legacy_checkpoint <ckpt.zip> [...]
    uv run python -m rl_move.sim.stamp_legacy_checkpoint --all-in-dir rl_move/sim/policies
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from hexapod_core.joint_frame import FRAME_ROBOT_ABS, JOINT_CONTRACT


def already_stamped(data: dict) -> bool:
    return (data.get("joint_frame") == FRAME_ROBOT_ABS
            and data.get("joint_contract") == JOINT_CONTRACT)


def stamp_one(path: Path, *, dry_run: bool = False) -> str:
    """Return 'stamped', 'already', or 'skip-foreign'."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if "data" not in names:
            return "skip-not-sb3"
        data = json.loads(archive.read("data"))
        frame = data.get("joint_frame")
        contract = data.get("joint_contract")
        if frame is not None or contract is not None:
            if already_stamped(data):
                return "already"
            raise ValueError(
                f"{path}: refuses to overwrite a DIFFERENT existing "
                f"stamp {frame!r}/{contract!r} -- this is a real "
                "foreign-contract checkpoint, not a backfill target")
        members = {n: archive.read(n) for n in names}

    data["joint_frame"] = FRAME_ROBOT_ABS
    data["joint_contract"] = JOINT_CONTRACT
    members["data"] = json.dumps(data).encode("utf-8")

    if dry_run:
        return "would-stamp"

    import os
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp_stamp.zip")
    os.close(fd)
    try:
        with zipfile.ZipFile(path) as src, \
                zipfile.ZipFile(tmp_name, "w") as out:
            # Copy every member byte-for-byte with its original
            # compress_type (STORED for 'data', DEFLATED for the large
            # pytorch members) except the rewritten 'data' entry.
            for info in src.infolist():
                out.writestr(info, members[info.filename],
                             compress_type=info.compress_type)
        shutil.move(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
    return "stamped"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", type=Path)
    ap.add_argument("--all-in-dir", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    paths = list(args.paths)
    if args.all_in_dir:
        paths += sorted(args.all_in_dir.glob("*.zip"))
    if not paths:
        print("no paths given", file=sys.stderr)
        return 2

    counts: dict[str, int] = {}
    for p in paths:
        try:
            r = stamp_one(p, dry_run=args.dry_run)
        except ValueError as exc:
            print(f"REFUSED {p}: {exc}", file=sys.stderr)
            r = "refused"
        counts[r] = counts.get(r, 0) + 1
        print(f"{r:14s} {p}")
    print("---", counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
