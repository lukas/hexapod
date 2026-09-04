import copy
from datetime import datetime, timezone
import hashlib
import json
import sqlite3

import pytest

from hexapod_lab.db import Store
from hexapod_lab.layout_history import (
    LayoutHistoryConflict,
    TagLayoutHistory,
)


NOW = datetime(2026, 2, 1, 12, tzinfo=timezone.utc)


def _write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _history(tmp_path):
    layout_path = tmp_path / "layout.json"
    pose_path = tmp_path / "pose.json"
    floor_path = tmp_path / "floor.json"
    part_path = tmp_path / "parts.json"
    layout = {
        "schema_version": 1,
        "robot_id": "hexapod-1",
        "captured": "2026-01-01",
        "tag_family": "tag36h11",
        "tag_geometry": {"black_square_m": 0.0272},
        "floor": {
            "tags": [
                {
                    "id": 100,
                    "world_from_tag": {
                        "translation_m": [0, 0, 0],
                        "quaternion_xyzw": [0, 0, 0, 1],
                    },
                }
            ]
        },
        "robot_tags": [
            {
                "id": 1,
                "kind": "servo_lid",
                "frame": "L0_coxa",
                "surface": "horizontal",
                "frame_from_tag": {
                    "translation_m": None,
                    "euler_xyz_deg": [0, 0, 0],
                },
            },
            {
                "id": 42,
                "kind": "yoke_face",
                "frame": "L0_femur",
                "mount_side": "+y",
                "frame_from_tag": {
                    "translation_m": None,
                    "quaternion_xyzw": [-0.7071068, 0, 0, 0.7071068],
                    "tag_axes_in_frame": {"x": "+x", "y": "-z", "z": "+y"},
                },
            },
        ],
    }
    pose = {
        "schema_version": 1,
        "tag_family": "tag36h11",
        "marker_size_m": 0.027,
        "camera": {},
        "floor_tags": {"old": {}},
        "robot_pose": {
            "tags": {
                "1": {
                    "frame": "old",
                    "frame_from_tag": {
                        "translation_m": [9, 9, 9],
                        "euler_xyz_deg": [0, 0, 180],
                    },
                }
            }
        },
    }
    _write_json(layout_path, layout)
    _write_json(pose_path, pose)
    _write_json(floor_path, {"floor": "exact"})
    _write_json(part_path, {"parts": "exact"})
    store = Store(tmp_path / "data" / "lab.sqlite3")
    history = TagLayoutHistory(
        store,
        tmp_path / "data",
        layout_path=layout_path,
        pose_template_path=pose_path,
        floor_map_path=floor_path,
        part_map_path=part_path,
        clock=lambda: NOW,
    )
    return history, store, layout, layout_path, pose_path, floor_path, part_path


def _result(store, experiment_id, created_at):
    with store.connect() as connection:
        connection.execute(
            "INSERT INTO experiments("
            "id,name,description,duration_seconds,parameters_json,status,submitted_by,"
            "created_at,started_at,finished_at"
            ") VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                experiment_id,
                experiment_id,
                "",
                1,
                "{}",
                "succeeded",
                "test",
                created_at,
                created_at,
                created_at,
            ),
        )


def test_bootstrap_resolution_and_exact_experiment_snapshots(tmp_path):
    history, store, _layout, layout_path, pose_path, floor_path, part_path = _history(tmp_path)
    _result(store, "old", "2025-12-31T23:59:59+00:00")
    _result(store, "known", "2026-01-02T00:00:00+00:00")
    _result(store, "imported-unknown", "2026-01-03T00:00:00+00:00")
    with store.connect() as connection:
        connection.execute(
            "INSERT INTO events(experiment_id,timestamp,kind,message) VALUES(?,?,?,?)",
            ("imported-unknown", "2026-01-03T00:00:00+00:00", "imported", "test"),
        )
    evidence_dir = tmp_path / "data" / "experiments" / "known"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "camera_timestamps.csv").write_text(
        "frame,unix_s\n0,1767312000.25\n", encoding="utf-8"
    )

    changed = history.initialize()
    assert changed == ["known"]
    assert history.resolve("2025-12-31T23:59:59Z") is None
    baseline = history.current()
    assert baseline["status"] == "current"
    assert baseline["layout_sha256"] == hashlib.sha256(layout_path.read_bytes()).hexdigest()
    assert history.experiment_revision("old") is None
    assert history.experiment_revision("imported-unknown") is None
    known_revision = history.experiment_revision("known")
    assert known_revision["id"] == baseline["id"]
    assert known_revision["recorded_at"] == "2026-01-02T00:00:00.250000+00:00"
    assert known_revision["pin_basis"] == "legacy_backfill_camera_timestamp"

    run_dir = tmp_path / "data" / "experiments" / "known"
    assert (run_dir / "apriltag-layout.snapshot.json").read_bytes() == layout_path.read_bytes()
    assert (run_dir / "floor-tag-map.snapshot.json").read_bytes() == floor_path.read_bytes()
    assert (run_dir / "hexapod-tag-map.snapshot.json").read_bytes() == part_path.read_bytes()
    assert (
        run_dir / "apriltag-pose-config.snapshot.json"
    ).read_bytes() == pose_path.read_bytes()


def test_candidate_activation_is_effective_dated_and_old_pin_stays_fixed(tmp_path):
    history, store, layout, _layout_path, _pose_path, _floor_path, _part_path = _history(tmp_path)
    history.initialize()
    baseline = history.current()
    _result(store, "video", "2026-01-10T00:00:00+00:00")
    old_pin = history.pin_experiment("video", "2026-01-10T00:00:00Z")
    _result(store, "scan", "2026-01-20T00:00:00+00:00")

    candidate = copy.deepcopy(layout)
    candidate["robot_tags"][0]["frame_from_tag"]["euler_xyz_deg"][2] = 90
    proposal = {
        "scan_id": "scan",
        "created_at": "2026-01-20T00:00:00Z",
        "baseline": {
            "revision_id": baseline["id"],
            "layout_sha256": baseline["layout_sha256"],
        },
        "ready_for_human_review": True,
        "changed_tag_ids": [1],
        "unresolved_tag_ids": [],
        "missing_tag_ids": [],
        "unexpected_tag_ids": [],
        "duplicate_tag_ids": [],
    }
    revision = history.record_candidate("scan", proposal, candidate, "phone")
    assert revision["status"] == "ready_for_review"
    activated = history.activate(
        "scan",
        activated_by="operator",
        expected_parent_revision_id=baseline["id"],
        expected_layout_sha256=revision["layout_sha256"],
        idempotency_key="activate-scan",
        note="tags repaired",
    )
    assert activated["status"] == "current"
    child_pose = history.get_revision("scan")["pose_config"]
    assert child_pose["marker_size_m"] == 0.027
    assert set(child_pose["floor_tags"]) == {"old"}
    assert child_pose["robot_pose"]["tags"]["1"]["frame_from_tag"] == {
        "translation_m": [9, 9, 9],
        "euler_xyz_deg": [0, 0, 90],
    }
    assert history.resolve("2026-02-01T11:59:59Z")["id"] == baseline["id"]
    assert history.resolve("2026-02-01T12:00:00Z")["id"] == "scan"
    assert history.experiment_revision("video")["id"] == old_pin["id"]

    # Exact retries succeed and repair a missing active pointer; changed reuse
    # of the key still fails.
    history.active_bundle_path.unlink()
    assert history.activate(
        "scan",
        activated_by="operator",
        expected_parent_revision_id=baseline["id"],
        expected_layout_sha256=revision["layout_sha256"],
        idempotency_key="activate-scan",
        note="tags repaired",
    )["id"] == "scan"
    assert history.active_bundle_path.resolve().name == "scan"
    with pytest.raises(LayoutHistoryConflict):
        history.activate(
            "scan",
            activated_by="operator",
            expected_parent_revision_id=baseline["id"],
            expected_layout_sha256=revision["layout_sha256"],
            idempotency_key="activate-scan",
            note="different request",
        )


def test_activation_refuses_to_change_layout_during_running_experiment(tmp_path):
    history, store, layout, _layout_path, _pose_path, _floor_path, _part_path = _history(tmp_path)
    history.initialize()
    baseline = history.current()
    _result(store, "scan", "2026-01-20T00:00:00+00:00")
    candidate = copy.deepcopy(layout)
    candidate["robot_tags"][0]["frame_from_tag"]["euler_xyz_deg"][2] = 90
    proposal = {
        "scan_id": "scan",
        "created_at": "2026-01-20T00:00:00Z",
        "baseline": {
            "revision_id": baseline["id"],
            "layout_sha256": baseline["layout_sha256"],
        },
        "ready_for_human_review": True,
        "changed_tag_ids": [1],
        "unresolved_tag_ids": [],
        "missing_tag_ids": [],
        "unexpected_tag_ids": [],
        "duplicate_tag_ids": [],
    }
    revision = history.record_candidate("scan", proposal, candidate, "phone")
    queued = store.create({"name": "camera", "duration_seconds": 1}, "operator")
    assert store.claim_next()["id"] == queued["id"]

    with pytest.raises(LayoutHistoryConflict, match="running experiment"):
        history.activate(
            "scan",
            activated_by="operator",
            expected_parent_revision_id=baseline["id"],
            expected_layout_sha256=revision["layout_sha256"],
            idempotency_key="blocked-while-running",
        )


def test_pre_release_schema_backfills_missing_audit_documents(tmp_path):
    (tmp_path / "seed").mkdir()
    seed_history, _seed_store, layout, layout_path, pose_path, floor_path, part_path = _history(
        tmp_path / "seed"
    )
    del seed_history
    database = tmp_path / "legacy" / "data" / "lab.sqlite3"
    database.parent.mkdir(parents=True)
    layout_text = layout_path.read_text()
    pose_text = pose_path.read_text()
    with sqlite3.connect(database) as connection:
        connection.executescript("""
        CREATE TABLE tag_layout_revisions (
          sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
          robot_id TEXT NOT NULL, layout_sha256 TEXT NOT NULL,
          pose_config_sha256 TEXT, layout_json TEXT NOT NULL,
          pose_config_json TEXT, observed_at TEXT NOT NULL,
          created_at TEXT NOT NULL, created_by TEXT NOT NULL,
          source_kind TEXT NOT NULL, source_experiment_id TEXT UNIQUE,
          parent_revision_id TEXT, baseline_sha256 TEXT,
          review_ready INTEGER NOT NULL, changed_tag_ids_json TEXT NOT NULL
        );
        CREATE TABLE tag_layout_activations (
          revision_id TEXT PRIMARY KEY, effective_from TEXT NOT NULL UNIQUE,
          activated_at TEXT NOT NULL, activated_by TEXT NOT NULL,
          note TEXT NOT NULL, idempotency_key TEXT NOT NULL UNIQUE,
          request_sha256 TEXT NOT NULL
        );
        """)
        connection.execute(
            "INSERT INTO tag_layout_revisions("
            "id,robot_id,layout_sha256,pose_config_sha256,layout_json,"
            "pose_config_json,observed_at,created_at,created_by,source_kind,"
            "review_ready,changed_tag_ids_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "legacy-baseline",
                "hexapod-1",
                hashlib.sha256(layout_text.encode()).hexdigest(),
                hashlib.sha256(pose_text.encode()).hexdigest(),
                layout_text,
                pose_text,
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
                "test",
                "baseline",
                1,
                "[]",
            ),
        )
        connection.execute(
            "INSERT INTO tag_layout_activations VALUES(?,?,?,?,?,?,?)",
            (
                "legacy-baseline",
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
                "test",
                "legacy",
                "legacy-key",
                "0" * 64,
            ),
        )

    store = Store(database)
    history = TagLayoutHistory(
        store,
        tmp_path / "legacy" / "data",
        layout_path=layout_path,
        pose_template_path=pose_path,
        floor_map_path=floor_path,
        part_map_path=part_path,
        clock=lambda: NOW,
    )
    history.initialize()
    revision = history.get_revision("legacy-baseline")
    assert revision["pose_config_sha256"] == hashlib.sha256(pose_path.read_bytes()).hexdigest()
    assert revision["floor_map"] == json.loads(floor_path.read_text())
    assert revision["part_map"] == json.loads(part_path.read_text())
