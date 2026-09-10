import json
import time

from fastapi.testclient import TestClient
import httpx

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
        rpc = client.post("/mcp", headers=auth, json={"jsonrpc": "2.0", "id": 1,
                          "method": "tools/call", "params": {"name": "read_artifact",
                          "arguments": {"experiment_id": item["id"], "filename": "summary.md"}}})
        payload = rpc.json()["result"]["structuredContent"]
        assert payload["encoding"] == "utf-8"
        assert "Smoke test" in payload["data"]


def test_duration_limit_and_basic_site_login(tmp_path):
    app = create_app(settings(tmp_path))
    with TestClient(app) as client:
        assert client.get("/", auth=("alice", "secret")).status_code == 200
        response = client.post("/api/experiments", headers={"Authorization": "Bearer secret"},
                               json={"name": "too long", "duration_seconds": 3})
        assert response.status_code == 422


def test_calibration_proxy_uses_same_operator_login(tmp_path):
    seen = []

    def upstream(request: httpx.Request):
        seen.append(request)
        if request.url.path == "/vision":
            return httpx.Response(200, text="<html>calibration</html>", headers={
                "Content-Type": "text/html",
            })
        return httpx.Response(200, content=b"jpeg-data", headers={
            "Content-Type": "image/jpeg",
        })

    configured = Settings(**{
        **settings(tmp_path).__dict__,
        "vision_url": "http://vision.local:8898",
    })
    app = create_app(configured, vision_transport=httpx.MockTransport(upstream))
    with TestClient(app) as client:
        assert client.get("/vision").status_code == 401
        assert client.get("/vision", auth=("bob", "read-only")).status_code == 403

        page = client.get("/vision", auth=("alice", "secret"))
        assert page.status_code == 200
        assert page.text == "<html>calibration</html>"
        assert page.headers["cache-control"] == "no-store"

        frame = client.get(
            "/api/vision/frame.jpg?v=7",
            auth=("alice", "secret"),
        )
        assert frame.status_code == 200
        assert frame.content == b"jpeg-data"
        assert seen[-1].url == "http://vision.local:8898/api/vision/frame.jpg?v=7"
        assert "authorization" not in seen[-1].headers


def test_calibration_proxy_is_disabled_without_fixed_upstream(tmp_path):
    app = create_app(settings(tmp_path))
    with TestClient(app) as client:
        response = client.get("/vision", auth=("alice", "secret"))
        assert response.status_code == 404
        assert response.json()["detail"] == "Calibration studio is not configured"


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
