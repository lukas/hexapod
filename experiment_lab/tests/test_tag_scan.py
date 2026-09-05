import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import time

from fastapi.testclient import TestClient

from hexapod_lab.config import Settings
from hexapod_lab.main import create_app
from hexapod_lab.tag_scan import TagScanService, build_orientation_proposal


def _layout():
    return {
        "schema_version": 1,
        "name": "test layout",
        "robot_id": "hexapod-1",
        "captured": "2026-09-03",
        "tag_family": "tag36h11",
        "tag_geometry": {"black_square_m": 0.027},
        "floor": {"tags": [{
            "id": 100,
            "world_from_tag": {
                "translation_m": [0, 0, 0],
                "quaternion_xyzw": [0, 0, 0, 1],
            },
        }]},
        "robot_tags": [
            {
                "id": 0,
                "kind": "chassis_tag",
                "frame": "body",
                "surface": "horizontal",
                "frame_from_tag": {"translation_m": None, "euler_xyz_deg": [0, 0, 0]},
            },
            {
                "id": 1,
                "kind": "servo_lid",
                "leg": 0,
                "joint": "hip",
                "frame": "L0_coxa",
                "surface": "horizontal",
                "frame_from_tag": {"translation_m": None, "euler_xyz_deg": [0, 0, 0]},
            },
            {
                "id": 20,
                "kind": "yoke_face",
                "leg": 0,
                "joint": "hip",
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


def _report(images):
    image_records = [
        {
            "path": str(path),
            "annotation": str(path.with_name(f"{path.stem}-annotated.jpg")),
            "detections": [],
            "duplicate_ids": [],
        }
        for path in images
    ]
    sample_images = [path.name for path in images]
    horizontal = []
    for tag_id, measured in ((0, 1.0), (1, 90.0)):
        horizontal.append({
            "id": tag_id,
            "status": "mismatch" if tag_id == 1 else "confirmed",
            "samples": [
                {"image": name, "measured_euler_z_deg": measured}
                for name in sample_images
            ],
        })
    side = [{
        "id": 20,
        "status": "confirmed",
        "samples": [
            {
                "image": name,
                "predicted_tag_axes_in_frame": {"x": "+x", "y": "-z", "z": "+y"},
                "link_axis_cosine": 0.99,
                "vertical_axis_cosine": 0.92,
            }
            for name in sample_images
        ],
    }]
    floor = [{
        "id": 100,
        "status": "confirmed",
        "samples": [{"image": name, "measured_yaw_deg": 0} for name in sample_images],
    }]
    return {
        "schema_version": 1,
        "layout_name": "test layout",
        "expected_ids": [0, 1, 20, 100],
        "detected_ids": [0, 1, 20, 100],
        "missing_ids": [],
        "unexpected_ids": [],
        "images": image_records,
        "horizontal_orientation_audit": {"tags": horizontal},
        "side_orientation_audit": {"tags": side},
        "floor_orientation_audit": {"tags": floor},
        "layout_validation": {"ok": True, "issues": []},
    }


def _configured(tmp_path):
    layout = tmp_path / "layout.json"
    floor = tmp_path / "floor.json"
    parts = tmp_path / "parts.json"
    pose = tmp_path / "pose.json"
    layout.write_text(json.dumps(_layout()))
    floor.write_text("{}")
    parts.write_text("{}")
    pose.write_text(json.dumps({
        "schema_version": 1,
        "tag_family": "tag36h11",
        "marker_size_m": 0.027,
        "floor_tags": {},
        "robot_pose": {"tags": {
            "0": {"frame": "body", "frame_from_tag": {
                "euler_xyz_deg": [0, 0, 0],
            }},
            "1": {"frame": "L0_coxa", "frame_from_tag": {
                "euler_xyz_deg": [0, 0, 0],
            }},
        }},
    }))
    return Settings(
        data_dir=tmp_path / "data",
        api_keys="operator:alice:secret,viewer:phone:read-only",
        driver="simulated",
        robot_command=(),
        camera_input="",
        bind="127.0.0.1",
        port=8767,
        public_base_url="https://robot-lab.example",
        auto_worker=False,
        max_duration_seconds=2,
        tag_audit_command=("fake-audit",),
        tag_layout_path=layout,
        tag_pose_template_path=pose,
        tag_floor_map_path=floor,
        tag_part_map_path=parts,
    )


def _fake_audit(
    self, images, report_path, output_dir, layout_path, floor_map_path,
    part_map_path,
):
    output_dir.mkdir(parents=True, exist_ok=True)
    for image in images:
        (output_dir / f"{image.stem}-annotated.jpg").write_bytes(b"annotated")
    report = _report(images)
    report_path.write_text(json.dumps(report))
    return report


def test_phone_scan_is_a_narrow_viewer_write_and_saves_review(monkeypatch, tmp_path):
    monkeypatch.setattr(TagScanService, "_run_audit", _fake_audit)
    app = create_app(_configured(tmp_path))
    viewer = {"Authorization": "Bearer read-only", "X-Hexapod-Scan": "1"}
    with TestClient(app) as client:
        page = client.get("/tag-scan", auth=("phone", "read-only"))
        assert page.status_code == 200
        assert "getUserMedia" in page.text
        assert "playsinline" in page.text
        assert "camera only · no motion" in page.text

        assert client.post("/api/tag-scans", headers={"Authorization": "Bearer read-only"}).status_code == 403
        scan = client.post("/api/tag-scans", headers=viewer).json()
        assert scan["robot_tags"] == {"seen": 0, "total": 3, "missing_ids": [0, 1, 20]}
        scan_dir = tmp_path / "data" / "tag-scans" / scan["id"]
        assert (scan_dir / "baseline-apriltag-layout.json").is_file()
        assert (scan_dir / "baseline-floor-tag-map.json").is_file()
        assert (scan_dir / "baseline-hexapod-tag-map.json").is_file()

        oversized = client.post(
            f"/api/tag-scans/{scan['id']}/photos",
            headers={**viewer, "Content-Type": "image/jpeg"},
            content=b"x" * (8 * 1024 * 1024 + 1),
        )
        assert oversized.status_code == 413

        captured = client.post(
            f"/api/tag-scans/{scan['id']}/photos",
            headers={**viewer, "Content-Type": "image/jpeg"},
            content=b"jpeg",
        )
        assert captured.status_code == 200
        assert captured.json()["ready_for_review"] is True
        assert captured.json()["last_capture"]["kept"] is True

        finished = client.post(
            f"/api/tag-scans/{scan['id']}/finish", headers=viewer
        )
        assert finished.status_code == 200
        body = finished.json()
        assert body["scan"]["status"] == "saved"
        assert body["experiment"]["id"] == scan["id"]
        assert body["experiment"]["parameters"]["apply_state"] == "proposed"
        assert body["experiment"]["parameters"]["changed_tag_ids"] == [1]
        baseline_revision_id = body["experiment"]["tag_layout_revision"]["id"]
        candidate = body["experiment"]["tag_layout_candidate"]
        assert candidate["parent_revision_id"] == baseline_revision_id
        assert candidate["status"] == "ready_for_review"
        artifacts = {item["name"] for item in body["experiment"]["artifacts"]}
        assert {
            "capture-001.jpg",
            "capture-001-annotated.jpg",
            "tag-orientation-audit.json",
            "tag-orientation-proposal.json",
            "proposed-hexapod-1-apriltag-layout.json",
            "baseline-apriltag-layout.json",
            "baseline-floor-tag-map.json",
            "baseline-hexapod-tag-map.json",
            "vision-context.json",
            "apriltag-layout.snapshot.json",
            "apriltag-pose-config.snapshot.json",
            "floor-tag-map.snapshot.json",
            "hexapod-tag-map.snapshot.json",
            "tag-scan-state.json",
        } <= artifacts
        saved_scan = json.loads((scan_dir / "scan.json").read_text())
        assert saved_scan["frames"][0]["captured_at"].endswith("+00:00")

        # The constrained viewer capture did not grant generic experiment writes.
        assert client.post(
            "/api/experiments",
            headers={"Authorization": "Bearer read-only"},
            json={"name": "not allowed", "duration_seconds": 1},
        ).status_code == 403

        manifest_path = (
            tmp_path / "data" / "experiments" / scan["id"] / "manifest.json"
        )
        original_manifest = manifest_path.read_bytes()
        manifest_path.unlink()
        repeated = client.post(
            f"/api/tag-scans/{scan['id']}/finish", headers=viewer
        )
        assert repeated.status_code == 409
        assert "manifest is missing" in repeated.json()["detail"]
        assert not manifest_path.is_file()
        assert len(client.get("/api/experiments", headers=viewer).json()) == 1
        # Model an explicit byte-for-byte evidence repair before continuing
        # the historical-layout assertions below. Finishing again may not
        # silently manufacture a replacement for a sealed manifest.
        manifest_path.write_bytes(original_manifest)

        viewer_page = client.get(
            f"/experiments/{scan['id']}", auth=("phone", "read-only")
        )
        assert "AprilTag orientation proposal" in viewer_page.text
        assert "activate-layout" not in viewer_page.text
        operator_page = client.get(
            f"/experiments/{scan['id']}", auth=("alice", "secret")
        )
        assert "activate-layout" in operator_page.text

        activation_body = {
            "expected_parent_revision_id": baseline_revision_id,
            "expected_layout_sha256": candidate["layout_sha256"],
            "note": "phone test",
        }
        activation_url = f"/api/tag-layout-revisions/{candidate['id']}/activate"
        assert client.post(
            activation_url,
            headers={"Authorization": "Bearer secret"},
            json=activation_body,
        ).status_code == 403
        activated = client.post(
            activation_url,
            headers={
                "Authorization": "Bearer secret",
                "X-Hexapod-Lab": "1",
                "Idempotency-Key": "activate-test-scan",
            },
            json=activation_body,
        )
        assert activated.status_code == 200, activated.text
        assert activated.json()["status"] == "current"

        # The saved scan remains pinned to its old baseline. A new scan sees
        # the accepted revision, so historical evidence is never reinterpreted.
        old = client.get(
            f"/api/experiments/{scan['id']}", headers=viewer
        ).json()
        assert old["tag_layout_revision"]["id"] == baseline_revision_id
        historical_layout = client.get(
            "/api/tag-layout-at?at=2026-09-03T12%3A00%3A00Z",
            headers=viewer,
        )
        assert historical_layout.status_code == 200
        assert historical_layout.json()["id"] == baseline_revision_id
        assert historical_layout.json()["layout"]["robot_id"] == "hexapod-1"
        next_scan = client.post("/api/tag-scans", headers=viewer).json()
        assert next_scan["baseline_revision_id"] == candidate["id"]

        missing_capture_time = client.post(
            "/api/results",
            headers={"Authorization": "Bearer secret"},
            json={
                "name": "Ambiguous old video",
                "duration_seconds": 2,
                "summary_markdown": "# Ambiguous\n",
            },
        )
        assert missing_capture_time.status_code == 422
        historical = client.post(
            "/api/results",
            headers={"Authorization": "Bearer secret"},
            json={
                "name": "Older video",
                "duration_seconds": 2,
                "summary_markdown": "# Older video\n",
                "recorded_at": "2026-09-03T12:00:00Z",
            },
        )
        assert historical.status_code == 201, historical.text
        assert historical.json()["tag_layout_revision"]["id"] == baseline_revision_id
        assert historical.json()["tag_layout_revision"]["pin_basis"] == "recorded_at"
        assert client.post(
            "/api/results",
            headers={"Authorization": "Bearer secret"},
            json={
                "name": "Unknown prehistory",
                "duration_seconds": 1,
                "summary_markdown": "# Unknown\n",
                "recorded_at": "2026-09-02T23:59:59Z",
            },
        ).status_code == 409

        manifest = json.loads(
            (tmp_path / "data" / "experiments" / scan["id"] / "manifest.json")
            .read_text()
        )
        assert manifest["schema_version"] == 2
        assert manifest["vision_context"]["tag_layout_revision"]["id"] == baseline_revision_id


def test_proposal_updates_rotation_only_and_never_claims_auto_apply():
    report = _report([Path("capture.jpg")])
    proposal, candidate = build_orientation_proposal(_layout(), report, scan_id="a" * 32)

    assert proposal["changed_tag_ids"] == [1]
    assert proposal["safe_to_auto_apply"] is False
    assert candidate["robot_tags"][1]["frame_from_tag"]["euler_xyz_deg"] == [0, 0, 90.0]
    assert candidate["robot_tags"][1]["frame_from_tag"]["translation_m"] is None
    assert candidate["robot_tags"][2]["frame_from_tag"] == _layout()["robot_tags"][2]["frame_from_tag"]
    assert candidate["proposal_metadata"]["canonical_configuration_changed"] is False


def test_weak_side_geometry_is_unresolved_not_a_proposal():
    report = _report([Path("capture.jpg")])
    side = report["side_orientation_audit"]["tags"][0]
    side["status"] = "mismatch"
    side["samples"][0].update(
        link_axis_cosine=0.1,
        vertical_axis_cosine=0.1,
    )

    proposal, candidate = build_orientation_proposal(
        _layout(), report, scan_id="b" * 32
    )
    record = next(item for item in proposal["orientations"] if item["id"] == 20)

    assert record["status"] == "unmeasured"
    assert record["rejected_weak_sample_count"] == 1
    assert proposal["ready_for_human_review"] is False
    assert 20 in proposal["unresolved_tag_ids"]
    assert candidate["robot_tags"][2]["frame_from_tag"] == _layout()["robot_tags"][2]["frame_from_tag"]


def test_duplicate_id_blocks_readiness_and_candidate_update():
    report = _report([Path("capture.jpg")])
    report["images"][0]["duplicate_ids"] = [1]

    proposal, candidate = build_orientation_proposal(
        _layout(), report, scan_id="c" * 32
    )
    record = next(item for item in proposal["orientations"] if item["id"] == 1)

    assert record["status"] == "duplicate_id"
    assert proposal["ready_for_human_review"] is False
    assert proposal["duplicate_tag_ids"] == [1]
    assert 1 in proposal["unresolved_tag_ids"]
    assert candidate["robot_tags"][1]["frame_from_tag"] == _layout()["robot_tags"][1]["frame_from_tag"]


def test_runner_pins_vision_context_before_capture(tmp_path):
    configured = _configured(tmp_path)
    configured = Settings(**{**configured.__dict__, "auto_worker": True})
    app = create_app(configured)
    operator = {"Authorization": "Bearer secret"}
    with TestClient(app) as client:
        queued = client.post(
            "/api/experiments",
            headers=operator,
            json={"name": "Camera provenance", "duration_seconds": 0.05},
        )
        assert queued.status_code == 202
        experiment_id = queued.json()["id"]
        for _ in range(50):
            item = client.get(
                f"/api/experiments/{experiment_id}", headers=operator
            ).json()
            if (
                item["status"] in {"succeeded", "failed"}
                and item.get("evidence_sealed_at")
            ):
                break
            time.sleep(0.02)
        assert item["status"] == "succeeded"
        assert item["evidence_sealed_at"]
        assert item["tag_layout_revision"]["pin_basis"] == "recording_start"
        run_dir = tmp_path / "data" / "experiments" / experiment_id
        context = json.loads((run_dir / "vision-context.json").read_text())
        assert context["experiment_id"] == experiment_id
        assert (run_dir / "apriltag-layout.snapshot.json").is_file()
        assert json.loads((run_dir / "manifest.json").read_text())["schema_version"] == 2


def test_external_result_refreshes_legacy_pre_run_vision_context(tmp_path):
    configured = _configured(tmp_path)
    operator = {"Authorization": "Bearer secret"}
    plan = {
        "name": "Timestamped guarded walk",
        "description": "three second canary",
        "duration_seconds": 0.2,
        "parameters": {"vx_m_s": 0.08},
        "execution_mode": "external_guarded",
    }
    initial_app = create_app(configured)
    with TestClient(initial_app) as client:
        queued = client.post("/api/experiments", headers=operator, json=plan)
        assert queued.status_code == 202
        experiment_id = queued.json()["id"]
        queued_at = queued.json()["created_at"]

    # Reproduce an already-existing pre-fix row. New waiting plans are no
    # longer backfilled at queue time.
    initial_app.state.layout_history.pin_experiment(
        experiment_id,
        queued_at,
        pin_basis="legacy_backfill_by_recorded_time",
    )

    # Restart materializes the historical context just as the deployed service
    # did before the completion fix existed.
    app = create_app(configured)
    with TestClient(app) as client:
        before = client.get(
            f"/api/experiments/{experiment_id}", headers=operator
        ).json()
        before_pin = before["tag_layout_revision"]
        assert before_pin["pin_basis"] == "legacy_backfill_by_recorded_time"
        run_dir = configured.data_dir / "experiments" / experiment_id
        context_path = run_dir / "vision-context.json"
        old_context = json.loads(context_path.read_text())
        snapshots = {
            name: (run_dir / name).read_bytes()
            for name in (
                "apriltag-layout.snapshot.json",
                "apriltag-pose-config.snapshot.json",
                "floor-tag-map.snapshot.json",
                "hexapod-tag-map.snapshot.json",
            )
        }

        recorded_at = (
            datetime.now(timezone.utc) - timedelta(seconds=1)
        ).isoformat()
        result = {
            "name": plan["name"],
            "description": plan["description"],
            "duration_seconds": plan["duration_seconds"],
            "parameters": plan["parameters"],
            "status": "succeeded",
            "summary_markdown": "# Timestamped guarded walk\n",
            "recorded_at": recorded_at,
        }
        completed = client.post(
            f"/api/experiments/{experiment_id}/result",
            headers=operator,
            json=result,
        )
        assert completed.status_code == 200, completed.text
        after = completed.json()
        after_pin = after["tag_layout_revision"]
        assert after_pin["id"] == before_pin["id"]
        assert after_pin["pinned_at"] == before_pin["pinned_at"]
        assert after_pin["pin_basis"] == before_pin["pin_basis"]
        assert after_pin["recorded_at"] == recorded_at
        assert after["started_at"] == recorded_at
        assert any(
            event["kind"] == "tag_layout_recording_time_rebound"
            for event in after["events"]
        )

        refreshed_context = json.loads(context_path.read_text())
        assert old_context["recorded_at"] == before_pin["recorded_at"]
        assert refreshed_context["recorded_at"] == recorded_at
        assert refreshed_context["recording_interval"]["start"] == recorded_at
        assert refreshed_context["tag_layout_revision"]["id"] == before_pin["id"]
        assert {
            name: (run_dir / name).read_bytes() for name in snapshots
        } == snapshots
        assert json.loads(
            (run_dir / "manifest.json").read_text()
        )["vision_context"] == refreshed_context

        # An exact completion retry also repairs the sidecar if a prior process
        # committed the database transaction but exited before materialization.
        context_path.write_text(json.dumps(old_context, indent=2) + "\n")
        retry = client.post(
            f"/api/experiments/{experiment_id}/result",
            headers=operator,
            json=result,
        )
        assert retry.status_code == 200, retry.text
        assert json.loads(context_path.read_text())["recorded_at"] == recorded_at

        context_path.write_text(json.dumps(old_context, indent=2) + "\n")

    # Startup can finish the same repair if the process committed the database
    # transaction and exited before replacing the context sidecar.
    restarted = create_app(configured)
    with TestClient(restarted):
        assert json.loads(context_path.read_text())["recorded_at"] == recorded_at
        assert json.loads(
            (run_dir / "manifest.json").read_text()
        )["vision_context"]["recorded_at"] == recorded_at


def test_restart_does_not_backfill_new_waiting_external_plan(tmp_path):
    configured = _configured(tmp_path)
    operator = {"Authorization": "Bearer secret"}
    plan = {
        "name": "Fresh guarded walk",
        "duration_seconds": 1.5,
        "execution_mode": "external_guarded",
    }
    with TestClient(create_app(configured)) as client:
        queued = client.post("/api/experiments", headers=operator, json=plan)
        assert queued.status_code == 202
        experiment_id = queued.json()["id"]

    with TestClient(create_app(configured)) as client:
        waiting = client.get(
            f"/api/experiments/{experiment_id}", headers=operator
        ).json()
        assert waiting["status"] == "waiting_for_operator"
        assert waiting["tag_layout_revision"] is None

        future_interval = client.post(
            f"/api/experiments/{experiment_id}/result",
            headers=operator,
            json={
                "name": plan["name"],
                "duration_seconds": plan["duration_seconds"],
                "summary_markdown": "# Incomplete interval\n",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert future_interval.status_code == 422
        assert client.get(
            f"/api/experiments/{experiment_id}", headers=operator
        ).json()["tag_layout_revision"] is None

        recorded_at = (
            datetime.now(timezone.utc) - timedelta(seconds=2)
        ).isoformat()
        completed = client.post(
            f"/api/experiments/{experiment_id}/result",
            headers=operator,
            json={
                "name": plan["name"],
                "duration_seconds": plan["duration_seconds"],
                "summary_markdown": "# Fresh guarded walk\n",
                "recorded_at": recorded_at,
            },
        )
        assert completed.status_code == 200, completed.text
        pin = completed.json()["tag_layout_revision"]
        assert pin["recorded_at"] == recorded_at
        assert pin["pin_basis"] == "recorded_at"
        assert all(
            event["kind"] != "tag_layout_recording_time_rebound"
            for event in completed.json()["events"]
        )
