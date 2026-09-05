"""Focused off-robot checks for calibrated walk-video evidence."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

from rl_move.scripts import analyze_apriltag_gait_motion as motion
from rl_move.scripts.hardware_walk_benchmark import (
    engaged_interval,
    motion_metrics,
    read_csv,
)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: dict) -> str:
    encoded = (
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _detection(tag_id: int, corners: np.ndarray) -> dict:
    return {
        "tag_id": tag_id,
        "source": "detected",
        "center_px": np.mean(corners, axis=0).tolist(),
        "corners_px": corners.tolist(),
    }


def _make_run(
    tmp_path: Path,
    *,
    include_body: bool = True,
    body_frames: set[int] | None = None,
    duplicate_capture: bool = False,
    legacy: bool = False,
) -> tuple[Path, Path]:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    video_path = run_dir / "camera_raw.mp4"
    writer = cv2.VideoWriter(
        str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (64, 48)
    )
    assert writer.isOpened()
    for index in range(5):
        writer.write(np.full((48, 64, 3), index * 20, dtype=np.uint8))
    writer.release()
    capture_times = [100 + index / 10 for index in range(5)]
    if duplicate_capture:
        capture_times[2] = capture_times[1]
    _write_csv(
        run_dir / "camera_timestamps.csv",
        ["frame", "elapsed_s", "unix_s", "capture_unix_s"],
        [
            {
                "frame": index,
                "elapsed_s": index / 10,
                "unix_s": 100.05 + index / 10,
                "capture_unix_s": capture_times[index],
            }
            for index in range(5)
        ],
    )
    trace = run_dir / "robot_rl_drive_test.csv"
    _write_csv(
        trace,
        ["phase", "mono_s", "unix_s", "walk_engaged", "learned_policy_active"],
        [
            {
                "phase": "walk",
                "mono_s": 50 + index / 10,
                "unix_s": 100.1 + index / 10,
                "walk_engaged": int(index < 3),
                "learned_policy_active": int(index < 3),
            }
            for index in range(4)
        ],
    )
    (run_dir / "summary.json").write_text(json.dumps({
        "results": [{
            "phase": "forward",
            "request": {"vx": 0.08, "vy": 0.0},
            "robot_logs": [trace.name],
        }],
    }))

    config = json.loads(motion.CURRENT_LAYOUT.with_name(
        "apriltag_pose_config_20260831.json"
    ).read_text())
    floor_map = None if legacy else motion.CURRENT_FLOOR_MAP
    specs, marker_size = motion._floor_specs(config, floor_map)
    floor_corners = motion._floor_corners(specs, marker_size)
    floor_to_image = np.asarray([
        [900.0, 25.0, 300.0],
        [20.0, 850.0, 220.0],
        [0.0, 0.0, 1.0],
    ], dtype=np.float32)

    pose_jsonl = run_dir / "apriltag_pose.jsonl"
    poses = []
    half = marker_size / 2
    for frame in range(5):
        detections = []
        for tag_id in ((12, 13) if legacy else (102, 104)):
            image = cv2.perspectiveTransform(
                floor_corners[tag_id].astype(np.float32).reshape(1, -1, 2),
                floor_to_image,
            )[0]
            detections.append(_detection(tag_id, image))
        if include_body and (body_frames is None or frame in body_frames):
            center = np.asarray([0.08 + frame * 0.01, 0.10])
            body_world = np.asarray([
                center + [-half, +half],
                center + [+half, +half],
                center + [+half, -half],
                center + [-half, -half],
            ], dtype=np.float32)
            body_image = cv2.perspectiveTransform(
                body_world.reshape(1, -1, 2), floor_to_image
            )[0]
            detections.append(_detection(0, body_image))
        robot_tags = (1, 2, 3, 4, 5) if legacy else (16, 31, 42, 53, 62)
        for tag_id in robot_tags:
            offset = float(tag_id * 8)
            corners = np.asarray([
                [40 + offset, 40], [45 + offset, 40],
                [45 + offset, 35], [40 + offset, 35],
            ], dtype=np.float32)
            detections.append(_detection(tag_id, corners))
        poses.append(json.dumps({
            "frame_index": frame,
            "time_s": frame / 10,
            "detections": detections,
        }))
    pose_jsonl.write_text("\n".join(poses) + "\n")
    return run_dir, pose_jsonl


def _evidence_bundle(
    tmp_path: Path,
    *,
    revision_id: str = "historical-test-revision",
) -> dict[str, Path | str]:
    bundle = tmp_path / "historical-vision-bundle"
    bundle.mkdir()
    layout = bundle / "apriltag-layout.snapshot.json"
    config = bundle / "apriltag-pose-config.snapshot.json"
    floor_map = bundle / "floor-tag-map.snapshot.json"
    layout.write_bytes(motion.CURRENT_LAYOUT.read_bytes())
    config.write_bytes((
        motion.TRACKER_CONFIGS / "apriltag_pose_config_20260831.json"
    ).read_bytes())
    floor_map.write_bytes(motion.CURRENT_FLOOR_MAP.read_bytes())
    context = bundle / "vision-context.json"
    _write_json(context, {
        "schema_version": 1,
        "kind": "hexapod_vision_context",
        "experiment_id": "candidate-a-test",
        "recorded_at": "1970-01-01T00:01:40.100000+00:00",
        "tag_layout_revision": {
            "id": revision_id,
            "revision_number": 7,
            "robot_id": "hexapod-1",
            "effective_from": "1969-12-31T00:00:00+00:00",
            "effective_to_known_at_pin": None,
            "observed_at": "1969-12-30T12:00:00+00:00",
            "source_kind": "historical_test_fixture",
        },
        "recording_interval": {
            "start": "1970-01-01T00:01:40.100000+00:00",
            "end": "1970-01-01T00:01:43.100000+00:00",
            "duration_seconds": 3.0,
            "crosses_known_revision_boundary": False,
        },
        "snapshots": {
            "layout": {"filename": layout.name, "sha256": _sha256(layout)},
            "pose_config": {
                "filename": config.name, "sha256": _sha256(config),
            },
            "floor_map": {
                "filename": floor_map.name, "sha256": _sha256(floor_map),
            },
        },
    })

    pose_config = json.loads(config.read_text())
    observed_at = "1969-12-31T12:00:00+00:00"
    report = {
        "kind": "camera_calibration",
        "schema_version": 1,
        "observed_at": observed_at,
        "robot_id": "hexapod-1",
    }
    request = {
        "observed_at": observed_at,
        "pose_config": pose_config,
        "report": report,
        "robot_id": "hexapod-1",
    }
    request_hash = _canonical_sha256(request)
    calibration_id = f"cal-{request_hash}"
    calibration = bundle / "calibration-record.json"
    _write_json(calibration, {
        "id": calibration_id,
        "sequence": 3,
        "request_sha256": request_hash,
        "report_sha256": _canonical_sha256(report),
        "pose_config_sha256": _canonical_sha256(pose_config),
        "observed_at": observed_at,
        "created_at": "1970-01-01T00:00:00+00:00",
        "created_by": "test-operator",
        "robot_id": "hexapod-1",
        "kind": "camera_calibration",
        "schema_version": 1,
        "status": "archived",
        "current": False,
        "replay_ready": False,
        "replay_status": "archived_not_activated",
        "tag_layout_revision": {
            "id": revision_id,
            "revision_number": 7,
            "robot_id": "hexapod-1",
            "layout_sha256": _sha256(layout),
            "pose_config_sha256": _sha256(config),
            "floor_map_sha256": _sha256(floor_map),
            "effective_from": "1969-12-31T00:00:00+00:00",
            "observed_at": "1969-12-30T12:00:00+00:00",
            "source_kind": "historical_test_fixture",
        },
        "report": report,
        "pose_config": pose_config,
        "source_metadata": {},
    })
    return {
        "layout": layout,
        "config": config,
        "floor_map": floor_map,
        "context": context,
        "calibration": calibration,
        "calibration_id": calibration_id,
        "revision_id": revision_id,
    }


def _argv(
    run_dir: Path,
    pose: Path,
    report: Path,
    calibrated: Path,
    bundle: dict[str, Path | str],
) -> list[str]:
    return [
        "analyze_apriltag_gait_motion",
        "--run-dir", str(run_dir),
        "--pose-jsonl", str(pose),
        "--config", str(bundle["config"]),
        "--floor-map", str(bundle["floor_map"]),
        "--layout", str(bundle["layout"]),
        "--vision-context", str(bundle["context"]),
        "--phase", "forward",
        "--output", str(report),
        "--calibrated-motion-output", str(calibrated),
        "--calibration-id", str(bundle["calibration_id"]),
        "--calibration-record", str(bundle["calibration"]),
        "--tag-layout-revision-id", str(bundle["revision_id"]),
    ]


def test_walk_trial_names_and_drive_phase_emit_bound_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, pose = _make_run(tmp_path)
    bundle = _evidence_bundle(tmp_path)
    report_path = tmp_path / "report.json"
    calibrated_path = run_dir / "calibrated_motion.json"
    monkeypatch.setattr(sys, "argv", _argv(
        run_dir, pose, report_path, calibrated_path, bundle
    ))

    assert motion.main() == 0
    report = json.loads(report_path.read_text())
    calibrated = json.loads(calibrated_path.read_text())
    assert Path(bundle["layout"]).resolve() != motion.CURRENT_LAYOUT.resolve()
    assert report["recording_source"] == "run_rl_walk_trial"
    assert report["time_alignment"].endswith(":capture_unix_s")
    assert "drive_forward" in report["phases"]
    assert report["calibrated_motion"]["status"] == "emitted"
    assert calibrated["schema"] == "hexapod.calibrated_motion.v1"
    assert calibrated["calibration_status"] == "validated"
    assert calibrated["clock"] == "mono_s"
    assert calibrated["phase"] == "drive_forward"
    assert calibrated["tag_layout_revision_id"] == bundle["revision_id"]
    assert calibrated["provenance"]["captured"] == "2026-09-03"
    assert calibrated["provenance"]["floor_tag_ids"] == [
        100, 101, 102, 103, 104, 105, 112,
    ]
    assert 62 in calibrated["provenance"]["robot_tag_ids"]
    assert calibrated["provenance"]["vision_context_sha256"] == _sha256(
        bundle["context"]
    )
    assert calibrated["provenance"]["layout_sha256"] == _sha256(
        bundle["layout"]
    )
    assert calibrated["provenance"]["camera_video_sha256"] == _sha256(
        run_dir / "camera_raw.mp4"
    )
    assert calibrated["provenance"]["calibration_selection"] == (
        "explicit_content_addressed_archive"
    )
    assert calibrated["provenance"]["calibration_replay_ready"] is False
    assert calibrated["samples"][0]["t"] <= 50.0
    assert calibrated["samples"][-1]["t"] >= 50.2
    assert calibrated["samples"][0]["source_unix_s"] == 100.1
    assert all(sample["direct_robot_tags"] >= 6
               for sample in calibrated["samples"])
    assert all(sample["mapped_floor_tags"] >= 2
               for sample in calibrated["samples"])

    trace = run_dir / "robot_rl_drive_test.csv"
    interval = engaged_interval(read_csv(trace))
    accepted = motion_metrics(
        calibrated_path, trace, interval, {"vx": 0.08, "vy": 0.0}
    )
    assert accepted["available"] is True
    assert abs(accepted["progress_m"]) > 0.0


def test_missing_tag_zero_rejects_without_emitting_motion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, pose = _make_run(tmp_path, include_body=False)
    bundle = _evidence_bundle(tmp_path)
    report_path = tmp_path / "report.json"
    calibrated_path = run_dir / "calibrated_motion.json"
    calibrated_path.write_text(json.dumps({
        "schema": "hexapod.calibrated_motion.v1",
        "calibration_status": "validated",
    }))
    monkeypatch.setattr(sys, "argv", _argv(
        run_dir, pose, report_path, calibrated_path, bundle
    ))

    assert motion.main() == 2
    report = json.loads(report_path.read_text())
    assert report["ok"] is False
    assert report["coverage_gate"]["counts"]["missing_body_tag_0"] == 5
    assert report["calibrated_motion"]["status"] == "rejected"
    assert "direct tag 0" in report["calibrated_motion"]["error"]
    assert not calibrated_path.exists()


def test_candidate_style_duplicate_capture_timestamps_are_collapsed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, pose = _make_run(tmp_path, duplicate_capture=True)
    bundle = _evidence_bundle(tmp_path)
    report_path = tmp_path / "report.json"
    calibrated_path = run_dir / "calibrated_motion.json"
    monkeypatch.setattr(sys, "argv", _argv(
        run_dir, pose, report_path, calibrated_path, bundle
    ))

    assert motion.main() == 0
    report = json.loads(report_path.read_text())
    calibrated = json.loads(calibrated_path.read_text())
    assert report["camera_timestamp_duplicates_collapsed"] == 1
    assert "capture_unix_s" in report["time_alignment"]
    assert 2 not in {
        sample["source_frame"] for sample in calibrated["samples"]
    }


def test_tag_dropout_across_active_window_rejects_metric_motion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, pose = _make_run(tmp_path, body_frames={0, 4})
    bundle = _evidence_bundle(tmp_path)
    report_path = tmp_path / "report.json"
    calibrated_path = run_dir / "calibrated_motion.json"
    monkeypatch.setattr(sys, "argv", _argv(
        run_dir, pose, report_path, calibrated_path, bundle
    ))

    assert motion.main() == 2
    report = json.loads(report_path.read_text())
    assert report["calibrated_motion"]["status"] == "rejected"
    assert "interior gap" in report["calibrated_motion"]["error"]
    assert not calibrated_path.exists()


def test_invalid_video_rejects_and_removes_stale_motion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, pose = _make_run(tmp_path)
    bundle = _evidence_bundle(tmp_path)
    report_path = tmp_path / "report.json"
    calibrated_path = run_dir / "calibrated_motion.json"
    calibrated_path.write_text('{"calibration_status":"validated"}\n')
    (run_dir / "camera_raw.mp4").write_bytes(b"not a video")
    monkeypatch.setattr(sys, "argv", _argv(
        run_dir, pose, report_path, calibrated_path, bundle
    ))

    assert motion.main() == 2
    assert "could not open camera video" in report_path.read_text()
    assert not calibrated_path.exists()


def test_revision_id_must_match_historical_vision_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, pose = _make_run(tmp_path)
    bundle = _evidence_bundle(tmp_path)
    bundle["revision_id"] = "wrong-revision"
    report_path = tmp_path / "report.json"
    calibrated_path = run_dir / "calibrated_motion.json"
    monkeypatch.setattr(sys, "argv", _argv(
        run_dir, pose, report_path, calibrated_path, bundle
    ))

    assert motion.main() == 2
    report = json.loads(report_path.read_text())
    assert "does not match vision context" in report["calibrated_motion"]["error"]
    assert not calibrated_path.exists()


def test_snapshot_bytes_must_match_historical_vision_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, pose = _make_run(tmp_path)
    bundle = _evidence_bundle(tmp_path)
    floor_path = Path(bundle["floor_map"])
    floor_map = json.loads(floor_path.read_text())
    floor_map["tampered"] = True
    _write_json(floor_path, floor_map)
    report_path = tmp_path / "report.json"
    calibrated_path = run_dir / "calibrated_motion.json"
    monkeypatch.setattr(sys, "argv", _argv(
        run_dir, pose, report_path, calibrated_path, bundle
    ))

    assert motion.main() == 2
    report = json.loads(report_path.read_text())
    assert "snapshot bytes do not match" in report["calibrated_motion"]["error"]
    assert not calibrated_path.exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "reviewed"),
        ("current", True),
        ("replay_ready", True),
        ("replay_status", "pose_config_missing"),
    ],
)
def test_calibration_record_must_have_real_archive_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: object,
) -> None:
    run_dir, pose = _make_run(tmp_path)
    bundle = _evidence_bundle(tmp_path)
    calibration_path = Path(bundle["calibration"])
    calibration = json.loads(calibration_path.read_text())
    calibration[field] = value
    _write_json(calibration_path, calibration)
    report_path = tmp_path / "report.json"
    calibrated_path = run_dir / "calibrated_motion.json"
    monkeypatch.setattr(sys, "argv", _argv(
        run_dir, pose, report_path, calibrated_path, bundle
    ))

    assert motion.main() == 2
    report = json.loads(report_path.read_text())
    assert "not a complete archival" in report["calibrated_motion"]["error"]
    assert not calibrated_path.exists()


def test_calibration_layout_snapshot_hash_must_match_selected_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, pose = _make_run(tmp_path)
    bundle = _evidence_bundle(tmp_path)
    calibration_path = Path(bundle["calibration"])
    calibration = json.loads(calibration_path.read_text())
    calibration["tag_layout_revision"]["layout_sha256"] = "0" * 64
    _write_json(calibration_path, calibration)
    report_path = tmp_path / "report.json"
    calibrated_path = run_dir / "calibrated_motion.json"
    monkeypatch.setattr(sys, "argv", _argv(
        run_dir, pose, report_path, calibrated_path, bundle
    ))

    assert motion.main() == 2
    report = json.loads(report_path.read_text())
    assert "selected layout bytes" in report["calibrated_motion"]["error"]
    assert not calibrated_path.exists()


def test_calibration_id_must_match_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, pose = _make_run(tmp_path)
    bundle = _evidence_bundle(tmp_path)
    bundle["calibration_id"] = "cal-wrong"
    report_path = tmp_path / "report.json"
    calibrated_path = run_dir / "calibrated_motion.json"
    monkeypatch.setattr(sys, "argv", _argv(
        run_dir, pose, report_path, calibrated_path, bundle
    ))

    assert motion.main() == 2
    report = json.loads(report_path.read_text())
    assert "does not match calibration record" in (
        report["calibrated_motion"]["error"]
    )
    assert not calibrated_path.exists()


def test_calibration_record_digest_mismatch_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, pose = _make_run(tmp_path)
    bundle = _evidence_bundle(tmp_path)
    calibration_path = Path(bundle["calibration"])
    calibration = json.loads(calibration_path.read_text())
    calibration["report"]["tampered"] = True
    _write_json(calibration_path, calibration)
    report_path = tmp_path / "report.json"
    calibrated_path = run_dir / "calibrated_motion.json"
    monkeypatch.setattr(sys, "argv", _argv(
        run_dir, pose, report_path, calibrated_path, bundle
    ))

    assert motion.main() == 2
    report = json.loads(report_path.read_text())
    assert "report digest" in report["calibrated_motion"]["error"]
    assert not calibrated_path.exists()


def test_parser_rejection_removes_stale_motion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    calibrated_path = tmp_path / "calibrated_motion.json"
    calibrated_path.write_text('{"calibration_status":"validated"}\n')
    monkeypatch.setattr(sys, "argv", [
        "analyze_apriltag_gait_motion",
        "--run-dir", str(tmp_path),
        "--pose-jsonl", str(tmp_path / "pose.jsonl"),
        "--config", str(tmp_path / "config.json"),
        "--output", str(tmp_path / "report.json"),
        "--calibrated-motion-output", str(calibrated_path),
    ])

    with pytest.raises(SystemExit):
        motion.main()
    assert not calibrated_path.exists()


def test_legacy_recording_names_and_gait_phase_still_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir, pose = _make_run(tmp_path, legacy=True)
    (run_dir / "camera_raw.mp4").rename(run_dir / "iphone_raw.mp4")
    (run_dir / "camera_timestamps.csv").rename(
        run_dir / "iphone_raw_timestamps.csv"
    )
    _write_csv(
        run_dir / "iphone_raw_timestamps.csv",
        ["frame", "elapsed_s", "unix_s"],
        [
            {"frame": index, "elapsed_s": index / 10, "unix_s": 100 + index / 10}
            for index in range(5)
        ],
    )
    (run_dir / "summary.json").unlink()
    _write_csv(
        run_dir / "telemetry.csv",
        ["receipt_unix_s", "phase"],
        [
            {"receipt_unix_s": 100 + index / 10, "phase": "gait_0_forward"}
            for index in range(5)
        ],
    )
    report_path = tmp_path / "legacy_report.json"
    monkeypatch.setattr(sys, "argv", [
        "analyze_apriltag_gait_motion",
        "--run-dir", str(run_dir),
        "--pose-jsonl", str(pose),
        "--config", str(
            motion.TRACKER_CONFIGS / "apriltag_pose_config_20260831.json"
        ),
        "--output", str(report_path),
    ])

    assert motion.main() == 0
    report = json.loads(report_path.read_text())
    assert report["recording_source"] == "scripted_gait_survey"
    assert report["camera_video"].endswith("iphone_raw.mp4")
    assert report["floor_map"] is None
    assert report["layout"] is None
    assert "gait_0_forward" in report["phases"]
