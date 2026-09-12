from pathlib import Path

import numpy as np

from sysid.archive_review import classify, contact_sheet, error_joint, family, local_iso_to_unix


def test_classify_reads_the_runner_error_not_the_exit_code() -> None:
    assert classify("ok", 100, "", "") == "ok"
    assert classify("failed", 0, "no trace CSV found on the robot", "") == "plumbing"
    assert classify("failed", 0, "", "posture: ...") == "plumbing"
    assert classify("failed", 0, "joint 14 overcurrent 0.39 A (limit 0.25, 1 consecutive polls)", "") == "overcurrent"
    assert classify("failed", 61, "joint 8 tracking error 30 deg > 30 (cmd 89.0, ref 87.7, present 57.6)", "") == "tracking"
    assert classify("failed", 1046, "joint 0 (ID 2) missed 3 consecutive reads", "") == "comms"
    assert classify("failed", 2720, "seg 34: joints [4] not answering at segment start", "") == "comms"
    assert classify("failed", 2125, "bus write failed: Write timeout", "") == "comms"
    assert classify("failed", 0, "start pose did not verify: joint 1 off by 3.8 deg after glide (tol 3)", "") == "start_pose"
    assert classify("failed", 12, "something new", "") == "other"
    assert classify("held", 0, "", "") == "held"


def test_error_joint_and_family() -> None:
    assert error_joint("joint 14 overcurrent 2.34 A") == 14
    assert error_joint("seg 34: joints [4] not answering") == 4
    assert error_joint("bus write failed") is None
    assert family("champion_stand_ground_hold90_v1") == "stand"
    assert family("l4_vertical_ground_load_ladder_v1") == "leg_vertical_ground_load_ladder"
    assert family("l4_vertical_ground_load_ladder_v1") == family("l0_vertical_ground_load_ladder_v1")
    assert family("walk_fwd30_oab10_v1") == "walk"
    assert family("") == "?"


def test_runner_summary_timestamps_are_utc() -> None:
    # 2026-09-10T22:25:00 UTC; vision.jsonl capture_unix in the same dataset agrees with this, not with local time
    assert local_iso_to_unix("2026-09-10T22:25:00") == 1789079100.0
    assert local_iso_to_unix("garbage") is None


def test_contact_sheet_tiles_frames(tmp_path: Path) -> None:
    import cv2

    frames = []
    for k in range(5):
        p = tmp_path / f"f{k}.jpg"
        cv2.imwrite(str(p), np.full((90, 160, 3), 40 * k, np.uint8))
        frames.append((p, f"{k - 3:+d} s"))
    out = tmp_path / "sheet.jpg"
    assert contact_sheet(frames, out, "five frames") is True
    im = cv2.imread(str(out))
    assert im is not None
    assert im.shape[1] == 4 * 480          # four tiles wide
    assert im.shape[0] > 2 * 200           # two rows plus banner
    assert contact_sheet([], tmp_path / "none.jpg", "empty") is False
