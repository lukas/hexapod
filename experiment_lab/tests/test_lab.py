import json
import time

from fastapi.testclient import TestClient

from hexapod_lab.config import Settings
from hexapod_lab.main import create_app


def settings(tmp_path, worker=False):
    return Settings(data_dir=tmp_path, api_keys="admin:alice:secret,viewer:bob:read-only",
                    driver="simulated", robot_command=(), camera_input="", bind="127.0.0.1",
                    port=8767, public_base_url="", auto_worker=worker, max_duration_seconds=2)


def test_auth_queue_and_artifact(tmp_path):
    app = create_app(settings(tmp_path))
    with TestClient(app) as client:
        assert client.get("/api/experiments").status_code == 401
        assert client.post("/api/experiments", headers={"Authorization": "Bearer read-only"},
                           json={"name": "x", "duration_seconds": .1}).status_code == 403
        response = client.post("/api/experiments", headers={"Authorization": "Bearer secret"},
                               json={"name": "Tripod gait", "duration_seconds": .1,
                                     "parameters": {"speed": .2}})
        assert response.status_code == 202
        experiment_id = response.json()["id"]
        run_dir = tmp_path / "experiments" / experiment_id
        run_dir.mkdir(parents=True)
        (run_dir / "note.txt").write_text("evidence")
        got = client.get(f"/api/experiments/{experiment_id}/artifacts/note.txt",
                         headers={"Authorization": "Bearer read-only"})
        assert got.text == "evidence"
        assert client.get(f"/api/experiments/{experiment_id}/artifacts/../lab.sqlite3",
                          headers={"Authorization": "Bearer secret"}).status_code in {400, 404}


def test_queue_rejects_conflicting_motion_flags(tmp_path):
    app = create_app(settings(tmp_path))
    with TestClient(app) as client:
        response = client.post(
            "/api/experiments",
            headers={"Authorization": "Bearer secret"},
            json={
                "name": "conflicting plan",
                "duration_seconds": 0.1,
                "execution_mode": "external_guarded",
                "parameters": {
                    "simulation_only": True,
                    "robot_motion": True,
                },
            },
        )
    assert response.status_code == 422
    assert "simulation_only and robot_motion cannot both be true" in response.text


def test_worker_completes_and_mcp_reads(tmp_path):
    app = create_app(settings(tmp_path, worker=True))
    auth = {"Authorization": "Bearer secret"}
    with TestClient(app) as client:
        item = client.post("/api/experiments", headers=auth,
                           json={"name": "Smoke test", "duration_seconds": .15}).json()
        for _ in range(50):
            current = client.get(f"/api/experiments/{item['id']}", headers=auth).json()
            if current["status"] == "succeeded":
                break
            time.sleep(.02)
        assert current["status"] == "succeeded"
        names = {artifact["name"] for artifact in current["artifacts"]}
        assert {"experiment.json", "telemetry.jsonl", "summary.md"} <= names
        recorded = client.get(
            f"/api/experiments/{item['id']}/artifacts/experiment.json",
            headers=auth,
        ).json()
        assert recorded["status"] == "succeeded"
        assert recorded["started_at"] == current["started_at"]
        assert recorded["finished_at"] == current["finished_at"]
        rpc = client.post("/mcp", headers=auth, json={"jsonrpc": "2.0", "id": 1,
                          "method": "tools/call", "params": {"name": "read_artifact",
                          "arguments": {"experiment_id": item["id"], "filename": "summary.md"}}})
        payload = rpc.json()["result"]["structuredContent"]
        assert payload["encoding"] == "utf-8"
        assert "Smoke test" in payload["data"]


def test_external_guarded_job_waits_for_operator_and_can_be_cancelled(tmp_path):
    app = create_app(settings(tmp_path, worker=True))
    operator = {"Authorization": "Bearer secret"}
    with TestClient(app) as client:
        waiting = client.post(
            "/api/experiments",
            headers=operator,
            json={
                "name": "Guarded leg comparison",
                "duration_seconds": 0.1,
                "execution_mode": "external_guarded",
            },
        )
        assert waiting.status_code == 202
        item = waiting.json()
        assert item["status"] == "waiting_for_operator"
        assert item["execution_mode"] == "external_guarded"

        # Even with the built-in worker enabled, this lane is never claimed.
        time.sleep(0.25)
        current = client.get(
            f"/api/experiments/{item['id']}", headers=operator
        ).json()
        assert current["status"] == "waiting_for_operator"
        assert all(event["kind"] != "started" for event in current["events"])

        cancelled = client.post(
            f"/api/experiments/{item['id']}/cancel", headers=operator
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"


def test_external_guarded_completion_is_strict_and_idempotent(tmp_path):
    app = create_app(settings(tmp_path, worker=True))
    operator = {"Authorization": "Bearer secret"}
    plan = {
        "name": "Independent L5 test",
        "description": "Supported single-leg comparison",
        "duration_seconds": 0.2,
        "parameters": {"leg": 5, "runner": "sysid.run_hw"},
        "execution_mode": "external_guarded",
    }
    result = {
        "name": plan["name"],
        "description": plan["description"],
        "duration_seconds": plan["duration_seconds"],
        "parameters": plan["parameters"],
        "status": "succeeded",
        "summary_markdown": "# L5 result\n\nNo safety trip.\n",
    }
    with TestClient(app) as client:
        experiment_id = client.post(
            "/api/experiments", headers=operator, json=plan
        ).json()["id"]
        endpoint = f"/api/experiments/{experiment_id}/result"

        completed = client.post(endpoint, headers=operator, json=result)
        assert completed.status_code == 200, completed.text
        item = completed.json()
        assert item["id"] == experiment_id
        assert item["status"] == "succeeded"
        assert item["execution_mode"] == "external_guarded"
        assert any(
            event["kind"] == "external_result_registered"
            for event in item["events"]
        )
        assert {
            artifact["name"] for artifact in item["artifacts"]
        } >= {"experiment.json", "summary.md", "manifest.json"}

        retry = client.post(endpoint, headers=operator, json=result)
        assert retry.status_code == 200
        assert retry.json()["id"] == experiment_id

        changed_summary = {**result, "summary_markdown": "# Different evidence\n"}
        assert client.post(
            endpoint, headers=operator, json=changed_summary
        ).status_code == 409


def test_external_completion_rejects_spec_mismatch_and_builtin_queue(tmp_path):
    app = create_app(settings(tmp_path))
    operator = {"Authorization": "Bearer secret"}
    base = {"name": "L2 test", "duration_seconds": 0.1, "parameters": {"leg": 2}}
    result = {**base, "summary_markdown": "# Result\n"}
    with TestClient(app) as client:
        waiting_id = client.post(
            "/api/experiments",
            headers=operator,
            json={**base, "execution_mode": "external_guarded"},
        ).json()["id"]
        mismatch = client.post(
            f"/api/experiments/{waiting_id}/result",
            headers=operator,
            json={**result, "parameters": {"leg": 5}},
        )
        assert mismatch.status_code == 409
        assert client.get(
            f"/api/experiments/{waiting_id}", headers=operator
        ).json()["status"] == "waiting_for_operator"

        builtin_id = client.post(
            "/api/experiments", headers=operator, json=base
        ).json()["id"]
        rejected = client.post(
            f"/api/experiments/{builtin_id}/result",
            headers=operator,
            json=result,
        )
        assert rejected.status_code == 409

        missing = client.post(
            "/api/experiments/does-not-exist/result",
            headers=operator,
            json=result,
        )
        assert missing.status_code == 404


def test_external_queue_and_completion_are_available_over_mcp(tmp_path):
    app = create_app(settings(tmp_path, worker=True))
    operator = {"Authorization": "Bearer secret"}
    with TestClient(app) as client:
        queued = client.post("/mcp", headers=operator, json={
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "queue_experiment", "arguments": {
                "name": "MCP guarded job", "duration_seconds": 0.1,
                "parameters": {"leg": 0}, "execution_mode": "external_guarded",
            }},
        }).json()["result"]["structuredContent"]
        assert queued["status"] == "waiting_for_operator"

        completed = client.post("/mcp", headers=operator, json={
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "complete_external_experiment", "arguments": {
                "experiment_id": queued["id"], "name": "MCP guarded job",
                "duration_seconds": 0.1, "parameters": {"leg": 0},
                "summary_markdown": "# MCP result\n",
            }},
        }).json()["result"]["structuredContent"]
        assert completed["id"] == queued["id"]
        assert completed["status"] == "succeeded"


def test_guarded_runner_status_and_progress_tools_are_available_over_mcp(tmp_path, monkeypatch):
    app = create_app(settings(tmp_path))
    operator = {"Authorization": "Bearer secret"}
    viewer = {"Authorization": "Bearer read-only"}
    observed = {
        "health": {"state": "healthy", "fresh": True},
        "robot": {"busy": False},
        "camera": {"fresh": True},
        "readiness": {"state": "guarded_ready", "guarded_runner_ready": True},
        "queue": {"waiting": 0, "software_blocked": 0},
    }
    monkeypatch.setattr(
        app.state.robot_status,
        "snapshot",
        lambda _experiments=(): dict(observed),
    )
    with TestClient(app) as client:
        listed = client.post("/mcp", headers=viewer, json={
            "jsonrpc": "2.0", "id": 10, "method": "tools/list", "params": {},
        }).json()["result"]["tools"]
        names = {tool["name"] for tool in listed}
        assert {
            "get_robot_status", "get_queue_controls", "resume_codex_queue",
            "resume_runner_safety", "report_execution_progress",
        } <= names

        status = client.post("/mcp", headers=viewer, json={
            "jsonrpc": "2.0", "id": 11, "method": "tools/call",
            "params": {"name": "get_robot_status", "arguments": {}},
        }).json()["result"]["structuredContent"]
        assert status["readiness"]["guarded_runner_ready"] is True

        denied = client.post("/mcp", headers=viewer, json={
            "jsonrpc": "2.0", "id": 12, "method": "tools/call",
            "params": {"name": "report_execution_progress", "arguments": {
                "state": "preparing", "summary": "Checking the oldest plan",
                "next_action": "Inspect camera and telemetry",
            }},
        }).json()["result"]
        assert denied["isError"] is True

        reported = client.post("/mcp", headers=operator, json={
            "jsonrpc": "2.0", "id": 13, "method": "tools/call",
            "params": {"name": "report_execution_progress", "arguments": {
                "state": "preparing", "summary": "Checking the oldest plan",
                "next_action": "Inspect camera and telemetry",
            }},
        }).json()["result"]["structuredContent"]
        assert reported["updated_by"] == "alice"


def test_duration_limit_and_basic_site_login(tmp_path):
    app = create_app(settings(tmp_path))
    with TestClient(app) as client:
        assert client.get("/", auth=("alice", "secret")).status_code == 200
        response = client.post("/api/experiments", headers={"Authorization": "Bearer secret"},
                               json={"name": "too long", "duration_seconds": 3})
        assert response.status_code == 422


def test_register_completed_result_and_stream_artifacts(tmp_path):
    configured = settings(tmp_path)
    configured = Settings(**{
        **configured.__dict__,
        "public_base_url": "https://robot-lab.example",
        "max_artifact_bytes": 16,
    })
    app = create_app(configured)
    operator = {"Authorization": "Bearer secret"}
    viewer = {"Authorization": "Bearer read-only"}
    with TestClient(app) as client:
        rpc = client.post("/mcp", headers=operator, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "register_result", "arguments": {
                "name": "Guarded L5 acceptance", "duration_seconds": 252,
                "summary_markdown": "# Guarded L5 acceptance\n\nNo safety trip.\n",
                "parameters": {"runner": "sysid.run_hw"},
            }},
        })
        result = rpc.json()["result"]["structuredContent"]
        assert result["status"] == "succeeded"
        experiment_id = result["id"]

        upload = client.put(
            f"/api/experiments/{experiment_id}/artifacts/video.mp4",
            headers={**operator, "Content-Type": "video/mp4"},
            content=b"0123456789",
        )
        assert upload.status_code == 201
        assert upload.json()["download_url"] == (
            f"https://robot-lab.example/api/experiments/{experiment_id}/artifacts/video.mp4"
        )
        assert client.get(
            f"/api/experiments/{experiment_id}/artifacts/video.mp4", headers=viewer
        ).content == b"0123456789"
        assert client.put(
            f"/api/experiments/{experiment_id}/artifacts/video.mp4",
            headers=operator,
            content=b"replace",
        ).status_code == 409
        assert client.put(
            f"/api/experiments/{experiment_id}/artifacts/too-big.bin",
            headers=operator,
            content=b"x" * 17,
        ).status_code == 413

        page = client.get(f"/experiments/{experiment_id}", auth=("alice", "secret"))
        assert "<video controls" in page.text
        manifest = client.get(
            f"/api/experiments/{experiment_id}/artifacts/manifest.json", headers=viewer
        ).json()
        assert any(item["name"] == "video.mp4" for item in manifest["artifacts"])
