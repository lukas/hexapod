from datetime import datetime, timedelta, timezone
import hashlib
import json
import sqlite3
import time

import pytest
from fastapi.testclient import TestClient

from hexapod_lab.config import Settings
from hexapod_lab.main import create_app


OPERATOR = {"Authorization": "Bearer secret"}
VIEWER = {"Authorization": "Bearer read-only"}


def _settings(tmp_path, *, with_layout=True):
    values = dict(
        data_dir=tmp_path / "data",
        api_keys="operator:alice:secret,viewer:bob:read-only",
        driver="simulated",
        robot_command=(),
        camera_input="",
        bind="127.0.0.1",
        port=8767,
        public_base_url="",
        auto_worker=False,
        max_duration_seconds=2,
    )
    if with_layout:
        layout = tmp_path / "layout.json"
        pose = tmp_path / "pose.json"
        floor = tmp_path / "floor.json"
        parts = tmp_path / "parts.json"
        layout.write_text(json.dumps({
            "schema_version": 1,
            "robot_id": "hexapod-1",
            "captured": "2026-01-01",
            "robot_tags": [],
        }) + "\n")
        pose.write_text(json.dumps({
            "schema_version": 1,
            "robot_pose": {"visual_joint_bias_deg": {}},
        }) + "\n")
        floor.write_text("{}\n")
        parts.write_text("{}\n")
        values.update(
            tag_layout_path=layout,
            tag_pose_template_path=pose,
            tag_floor_map_path=floor,
            tag_part_map_path=parts,
        )
    return Settings(**values)


def _report(**changes):
    value = {
        "schema_version": 1,
        "kind": "advisory_visual_encoder_calibration",
        "created_unix": time.time() - 5,
        "sample_count": 45,
        "advisory_only": True,
        "configuration_changed": True,
        "servo_zeros_changed": False,
        "motor_commands_sent": False,
    }
    value.update(changes)
    return value


def _mcp(client, name, arguments):
    return client.post(
        "/mcp",
        headers=VIEWER,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    ).json()["result"]


def test_calibration_routes_archive_raw_and_enveloped_reports(tmp_path):
    configured = _settings(tmp_path)
    app = create_app(configured)
    first_report = _report(label="first")

    with TestClient(app) as client:
        assert client.get("/api/calibrations").status_code == 401
        assert client.post("/api/calibrations", json=first_report).status_code == 401
        assert client.post(
            "/api/calibrations", headers=VIEWER, json=first_report
        ).status_code == 403

        first_response = client.post(
            "/api/calibrations", headers=OPERATOR, json=first_report
        )
        assert first_response.status_code == 201, first_response.text
        first = first_response.json()
        canonical_report = json.dumps(
            first_report, sort_keys=True, separators=(",", ":")
        ) + "\n"
        assert first["report_sha256"] == hashlib.sha256(
            canonical_report.encode()
        ).hexdigest()
        assert first["report"] == first_report
        assert first["pose_config"] is None
        assert first["replay_ready"] is False
        assert first["replay_status"] == "pose_config_missing"
        assert first["status"] == "archived"
        assert first["current"] is False
        assert first["created_by"] == "alice"
        assert first["observed_at"] != first["created_at"]
        assert first["tag_layout_revision"]["robot_id"] == "hexapod-1"
        assert len(first["tag_layout_revision"]["layout_sha256"]) == 64
        assert len(first["tag_layout_revision"]["pose_config_sha256"]) == 64

        observed = datetime.now(timezone.utc) - timedelta(minutes=3)
        pose_config = {
            "schema_version": 1,
            "robot_pose": {"visual_joint_bias_deg": {"L0_yaw": 0.25}},
        }
        second_report = _report(label="second")
        envelope = {
            "calibration": second_report,
            "configuration": pose_config,
            "observed_at": observed.isoformat(),
            "robot_id": "hexapod-1",
            "source": {"application": "hexapod-vision", "version": "1.2.3"},
        }
        second_response = client.post(
            "/api/calibrations/import", headers=OPERATOR, json=envelope
        )
        assert second_response.status_code == 201, second_response.text
        second = second_response.json()
        assert second["report"] == second_report
        assert second["pose_config"] == pose_config
        assert second["pose_config_sha256"]
        assert second["replay_ready"] is False
        assert second["replay_status"] == "archived_not_activated"
        assert second["observed_at"] == observed.isoformat()
        assert second["source_metadata"] == {
            "source": {
                "application": "hexapod-vision",
                "version": "1.2.3",
            }
        }

        newest = client.get(
            "/api/calibrations?limit=1", headers=VIEWER
        )
        assert newest.status_code == 200
        assert [item["id"] for item in newest.json()] == [second["id"]]
        assert "report" not in newest.json()[0]
        assert newest.json()[0]["status"] == "archived"
        assert newest.json()[0]["current"] is False
        detail = client.get(
            f"/api/calibrations/{first['id']}", headers=VIEWER
        )
        assert detail.status_code == 200
        assert detail.json() == first
        assert client.get(
            "/api/calibrations/not-found", headers=VIEWER
        ).status_code == 404

        tools = client.post(
            "/mcp",
            headers=VIEWER,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        ).json()["result"]["tools"]
        assert {"list_calibrations", "get_calibration"} <= {
            tool["name"] for tool in tools
        }
        listed = _mcp(client, "list_calibrations", {"limit": 1})
        assert listed["structuredContent"][0]["id"] == second["id"]
        fetched = _mcp(
            client, "get_calibration", {"calibration_id": first["id"]}
        )
        assert fetched["structuredContent"] == first

        openapi = client.get("/openapi.json").json()
        for path in ("/api/calibrations", "/api/calibrations/import"):
            operation = openapi["paths"][path]["post"]
            schema = operation["requestBody"]["content"][
                "application/json"
            ]["schema"]
            assert schema["type"] == "object"
            assert {"report", "calibration", "configuration"} <= set(
                schema["properties"]
            )
            assert operation["responses"]["201"]["content"][
                "application/json"
            ]["schema"]["allOf"]
            assert any(
                parameter["name"] == "Idempotency-Key"
                for parameter in operation["parameters"]
            )
            assert operation["security"] == [
                {"BearerAuth": []},
                {"BasicAuth": []},
            ]
            assert {"401", "403", "409", "413", "415", "422", "500"} <= set(
                operation["responses"]
            )
            assert not any(
                parameter["name"].casefold() == "authorization"
                for parameter in operation["parameters"]
            )
        list_schema = openapi["paths"]["/api/calibrations"]["get"]["responses"][
            "200"
        ]["content"]["application/json"]["schema"]
        assert list_schema["type"] == "array"
        detail_schema = openapi["paths"][
            "/api/calibrations/{calibration_id}"
        ]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        assert detail_schema["allOf"]
        assert openapi["components"]["securitySchemes"]["BearerAuth"] == {
            "type": "http",
            "scheme": "bearer",
        }


def test_calibration_idempotency_conflict_and_restart_persistence(tmp_path):
    configured = _settings(tmp_path, with_layout=False)
    app = create_app(configured)
    body = {
        "report": _report(),
        "pose_config": {"schema_version": 1, "robot_pose": {}},
        "recorded_at": "2026-08-31T14:21:51Z",
        "source": {"application": "hexapod-vision"},
    }
    headers = {**OPERATOR, "Idempotency-Key": "vision-calibration-1"}

    with TestClient(app) as client:
        first = client.post("/api/calibrations", headers=headers, json=body)
        assert first.status_code == 201, first.text
        assert first.json()["pose_config"] == body["pose_config"]
        assert first.json()["tag_layout_revision"] is None
        assert first.json()["replay_ready"] is False
        assert first.json()["replay_status"] == "tag_layout_unresolved"
        assert first.json()["source_metadata"] == {"source": body["source"]}
        repeated = client.post(
            "/api/calibrations/import", headers=headers, json=body
        )
        assert repeated.status_code == 201
        assert repeated.json() == first.json()

        # Exact content is deterministic even when the caller omitted a key.
        assert client.post(
            "/api/calibrations", headers=OPERATOR, json=body
        ).json() == first.json()

        changed = json.loads(json.dumps(body))
        changed["report"]["sample_count"] = 46
        conflict = client.post(
            "/api/calibrations", headers=headers, json=changed
        )
        assert conflict.status_code == 409
        assert len(client.get("/api/calibrations", headers=VIEWER).json()) == 1

        with app.state.store.connect() as connection:
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                connection.execute(
                    "UPDATE calibrations SET created_by='mallory' WHERE id=?",
                    (first.json()["id"],),
                )
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                connection.execute(
                    "DELETE FROM calibrations WHERE id=?", (first.json()["id"],)
                )

    restarted = create_app(configured)
    with TestClient(restarted) as client:
        persisted = client.get(
            f"/api/calibrations/{first.json()['id']}", headers=VIEWER
        )
        assert persisted.status_code == 200
        assert persisted.json() == first.json()
        assert persisted.json()["tag_layout_revision"] is None
        assert persisted.json()["source_metadata"] == {"source": body["source"]}


def test_calibration_resolves_layout_at_observation_time(tmp_path):
    app = create_app(_settings(tmp_path))
    body = {
        "report": _report(),
        "pose_config": {"schema_version": 1, "robot_pose": {}},
        "observed_at": "2025-12-31T23:59:59Z",
    }
    with TestClient(app) as client:
        imported = client.post(
            "/api/calibrations/import", headers=OPERATOR, json=body
        )
        assert imported.status_code == 201, imported.text
        assert imported.json()["tag_layout_revision"] is None
        assert imported.json()["replay_ready"] is False
        assert imported.json()["replay_status"] == "tag_layout_unresolved"


def test_calibration_read_detects_cross_field_tampering(tmp_path):
    app = create_app(_settings(tmp_path, with_layout=False))
    with TestClient(app) as client:
        archived = client.post(
            "/api/calibrations",
            headers=OPERATOR,
            json={"report": _report(), "source": {"application": "vision"}},
        )
        assert archived.status_code == 201, archived.text
        with app.state.store.connect() as connection:
            connection.execute("DROP TRIGGER calibrations_no_update")
            connection.execute(
                "UPDATE calibrations SET source_metadata_json=? WHERE id=?",
                ('{"source":{"application":"tampered"}}\n', archived.json()["id"]),
            )
        detected = client.get(
            f"/api/calibrations/{archived.json()['id']}", headers=VIEWER
        )
        assert detected.status_code == 500, detected.text


@pytest.mark.parametrize("pose_key", ["pose_config", "config", "configuration"])
def test_flat_report_pose_sidecar_and_nested_calibration_are_preserved(
    pose_key, tmp_path
):
    app = create_app(_settings(tmp_path))
    pose_config = {
        "schema_version": 1,
        "robot_pose": {"visual_joint_bias_deg": {"L0_yaw": 0.5}},
    }
    payload = {
        "schema_version": 1,
        "kind": "camera_calibration",
        "created_unix": time.time() - 5,
        "calibration": {"camera_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]},
        pose_key: pose_config,
    }
    with TestClient(app) as client:
        imported = client.post(
            "/api/calibrations", headers=OPERATOR, json=payload
        )
        assert imported.status_code == 201, imported.text
        archived = imported.json()
        assert archived["report"] == {
            key: value for key, value in payload.items() if key != pose_key
        }
        assert archived["report"]["calibration"] == payload["calibration"]
        assert archived["pose_config"] == pose_config
        assert archived["replay_ready"] is False
        assert archived["replay_status"] == "archived_not_activated"


def test_calibration_accepts_small_clock_skew_and_generic_session_fields(tmp_path):
    app = create_app(_settings(tmp_path, with_layout=False))
    body = {
        "report": _report(
            created_unix=time.time() + 0.5,
            session_id="capture-42",
            token_count=12,
        ),
        "source": {"session_id": "publisher-7", "token_count": 4},
    }
    with TestClient(app) as client:
        response = client.post(
            "/api/calibrations", headers=OPERATOR, json=body
        )
        assert response.status_code == 201, response.text
        assert response.json()["report"]["session_id"] == "capture-42"
        assert response.json()["source_metadata"]["source"]["session_id"] == (
            "publisher-7"
        )


@pytest.mark.parametrize(
    "params",
    [
        {"name": "list_calibrations", "arguments": None},
        {"name": "list_calibrations", "arguments": []},
        {"name": "get_calibration", "arguments": {"calibration_id": {}}},
        None,
    ],
)
def test_calibration_mcp_rejects_malformed_arguments_without_500(params, tmp_path):
    app = create_app(_settings(tmp_path, with_layout=False))
    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            headers=VIEWER,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": params,
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["result"]["isError"] is True


def test_calibration_rejects_layout_robot_mismatch_and_empty_pose(tmp_path):
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        mismatch = client.post(
            "/api/calibrations",
            headers=OPERATOR,
            json={
                "report": _report(),
                "robot_id": "another-robot",
                "observed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert mismatch.status_code == 409, mismatch.text

        report_mismatch = client.post(
            "/api/calibrations",
            headers=OPERATOR,
            json={
                "report": _report(robot_id="hexapod-1"),
                "robot_id": "another-robot",
            },
        )
        assert report_mismatch.status_code == 409, report_mismatch.text

        for pose_config in (
            {},
            {"robot_pose": {}},
            {"schema_version": 1},
            {"schema_version": 10**100, "robot_pose": {}},
        ):
            invalid_pose = client.post(
                "/api/calibrations",
                headers=OPERATOR,
                json={"report": _report(), "pose_config": pose_config},
            )
            assert invalid_pose.status_code == 422, invalid_pose.text

        assert client.get("/api/calibrations", headers=VIEWER).json() == []


@pytest.mark.parametrize(
    "payload",
    [
        _report(motor_commands_sent=True),
        {
            key: value
            for key, value in _report().items()
            if key != "servo_zeros_changed"
        },
        {"report": _report(), "observed_at": "2026-08-31T14:21:51"},
        {"report": _report(), "observed_at": "9999-12-31T23:59:59-08:00"},
        {
            "report": _report(recorded_at="2026-08-30T14:21:51Z"),
            "observed_at": "2026-08-31T14:21:51Z",
        },
        _report(created_unix=time.time() + 3600),
        _report(created_unix=10**1000),
        _report(schema_version=10**100),
        {"schema_version": 1, "created_unix": time.time() - 1},
        {"kind": "camera_calibration", "created_unix": time.time() - 1},
    ],
)
def test_calibration_rejects_invalid_safety_and_time(payload, tmp_path):
    app = create_app(_settings(tmp_path, with_layout=False))
    with TestClient(app) as client:
        response = client.post(
            "/api/calibrations", headers=OPERATOR, json=payload
        )
        assert response.status_code == 422, response.text
        assert client.get("/api/calibrations", headers=VIEWER).json() == []


@pytest.mark.parametrize(
    "source_metadata",
    [
        {"authorization": "Bearer accidental"},
        {"source": {"api_key": "accidental"}},
        {"source": [{"refresh_token_hint": "accidental"}]},
        {"cookie": "session=accidental"},
    ],
)
def test_calibration_rejects_credential_like_source_metadata(
    source_metadata, tmp_path
):
    app = create_app(_settings(tmp_path, with_layout=False))
    body = {"report": _report(), **source_metadata}
    with TestClient(app) as client:
        response = client.post(
            "/api/calibrations", headers=OPERATOR, json=body
        )
        assert response.status_code == 422, response.text
        assert "accidental" not in response.text
        assert client.get("/api/calibrations", headers=VIEWER).json() == []


def test_calibration_rejects_credentials_in_documents_and_non_json_media(tmp_path):
    app = create_app(_settings(tmp_path, with_layout=False))
    with TestClient(app) as client:
        report_secret = client.post(
            "/api/calibrations",
            headers=OPERATOR,
            json=_report(source={"refresh_token": "accidental"}),
        )
        assert report_secret.status_code == 422, report_secret.text
        assert "accidental" not in report_secret.text

        pose_secret = client.post(
            "/api/calibrations",
            headers=OPERATOR,
            json={
                "report": _report(),
                "pose_config": {
                    "schema_version": 1,
                    "robot_pose": {},
                    "api_key": "accidental",
                },
            },
        )
        assert pose_secret.status_code == 422, pose_secret.text
        assert "accidental" not in pose_secret.text

        text_plain = client.post(
            "/api/calibrations",
            headers={**OPERATOR, "Content-Type": "text/plain"},
            content=json.dumps(_report()),
        )
        assert text_plain.status_code == 415, text_plain.text
        assert client.get("/api/calibrations", headers=VIEWER).json() == []


def test_calibration_rejects_non_finite_and_oversized_json(tmp_path):
    app = create_app(_settings(tmp_path, with_layout=False))
    with TestClient(app) as client:
        non_finite = client.post(
            "/api/calibrations",
            headers={**OPERATOR, "Content-Type": "application/json"},
            content=(
                b'{"schema_version":1,"kind":"camera_calibration",'
                b'"created_unix":NaN}'
            ),
        )
        assert non_finite.status_code == 422
        invalid_unicode = client.post(
            "/api/calibrations",
            headers={**OPERATOR, "Content-Type": "application/json"},
            content=(
                b'{"schema_version":1,"kind":"camera_calibration",'
                b'"created_unix":1,"label":"\\ud800"}'
            ),
        )
        assert invalid_unicode.status_code == 422
        enormous_integer = client.post(
            "/api/calibrations",
            headers={**OPERATOR, "Content-Type": "application/json"},
            content=(
                b'{"schema_version":1,"kind":"camera_calibration",'
                b'"created_unix":1,"sample_count":' + b"9" * 5000 + b"}"
            ),
        )
        assert enormous_integer.status_code == 422
        not_object = client.post(
            "/api/calibrations",
            headers={**OPERATOR, "Content-Type": "application/json"},
            content=b"[]",
        )
        assert not_object.status_code == 422
        oversized = client.post(
            "/api/calibrations",
            headers={
                **OPERATOR,
                "Content-Type": "application/json",
                "Content-Length": "1",
            },
            content=b"{" + b" " * (2 * 1024 * 1024),
        )
        assert oversized.status_code == 413
