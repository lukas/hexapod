import json
import threading
import time

from fastapi.testclient import TestClient

from hexapod_lab.config import Settings
from hexapod_lab.main import create_app
from hexapod_lab.db import Store


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


def test_worker_terminal_status_waits_for_closed_camera_and_manifest(tmp_path, monkeypatch):
    from hexapod_lab.runner import ExperimentRunner
    store = Store(tmp_path / "lab.sqlite3")
    item = store.create({"name": "Artifact ordering", "duration_seconds": .01}, "operator")
    experiment = store.claim_next()
    runner = ExperimentRunner(store, settings(tmp_path))
    manifest_started, release = threading.Event(), threading.Event()

    class Camera:
        closed = False
        def terminate(self):
            pass
        def wait(self, timeout):
            self.closed = True
    camera = Camera()
    monkeypatch.setattr(runner, "_start_camera", lambda path: camera)
    monkeypatch.setattr(runner, "_simulate", lambda *args: {"telemetry_samples": 0})
    write_manifest = runner._write_manifest

    def paused_manifest(path):
        assert camera.closed
        assert (path / "summary.md").is_file()
        assert store.get(item["id"])["status"] == "running"
        manifest_started.set()
        assert release.wait(5)
        write_manifest(path)

    monkeypatch.setattr(runner, "_write_manifest", paused_manifest)
    worker = threading.Thread(target=lambda: runner._execute(experiment))
    worker.start()
    try:
        assert manifest_started.wait(5)
        assert store.get(item["id"])["status"] == "running"
        assert not (tmp_path / "experiments" / item["id"] / "manifest.json").exists()
    finally:
        release.set()
        worker.join(5)
    assert not worker.is_alive()
    final = store.get(item["id"])
    assert final["status"] == "succeeded"
    run_dir = tmp_path / "experiments" / item["id"]
    assert (run_dir / "manifest.json").is_file()
    assert f"- Finished: {final['finished_at']}" in (run_dir / "summary.md").read_text()


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


def test_worker_never_claims_external_mode_even_with_queued_status(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    external = store.create({"name": "External", "duration_seconds": .1,
                             "execution_mode": "external_guarded"}, "operator")
    # Defensive invariant for a legacy/manual state repair: mode itself
    # excludes physical work, even if status has accidentally been queued.
    with store.connect() as con:
        con.execute("UPDATE experiments SET status='queued' WHERE id=?", (external["id"],))
    builtin = store.create({"name": "Builtin", "duration_seconds": .1}, "operator")
    assert store.claim_next()["id"] == builtin["id"]
    assert store.claim_next() is None
    assert store.get(external["id"])["status"] == "queued"


def test_cancel_and_external_completion_are_serialized(tmp_path, monkeypatch):
    import hexapod_lab.db as db_module
    store = Store(tmp_path / "lab.sqlite3")
    spec = {"name": "Concurrent external", "duration_seconds": .1,
            "execution_mode": "external_guarded"}
    item = store.create(spec, "operator")
    selected = threading.Event()
    release = threading.Event()
    completion_done = threading.Event()
    real_clock = db_module.utcnow
    failures = []

    def pause_after_cancel_select():
        if threading.current_thread().name == "cancel-test":
            selected.set()
            assert release.wait(5)
        return real_clock()

    def complete():
        try:
            store.import_result(spec, "operator", "succeeded",
                                experiment_id=item["id"], completion_sha256="receipt")
        except ValueError as error:
            failures.append(str(error))
        finally:
            completion_done.set()

    monkeypatch.setattr(db_module, "utcnow", pause_after_cancel_select)
    cancelling = threading.Thread(name="cancel-test", target=lambda: store.cancel(item["id"]))
    completing = threading.Thread(target=complete)
    cancelling.start()
    assert selected.wait(5)
    completing.start()
    try:
        # Completion must wait for the cancellation transaction, not create
        # a successful receipt that an older unconditional UPDATE overwrites.
        assert not completion_done.wait(.1)
    finally:
        release.set()
        cancelling.join(5)
        completing.join(5)
    assert not cancelling.is_alive() and not completing.is_alive()
    assert failures == ["experiment already has a different terminal result"]
    final = store.get(item["id"])
    assert final["status"] == "cancelled"
    assert final["completion_sha256"] is None


def test_cancellation_preserves_a_completed_receipt(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    spec = {"name": "Completed external", "duration_seconds": .1,
            "execution_mode": "external_guarded"}
    item = store.create(spec, "operator")
    store.import_result(spec, "operator", "succeeded", experiment_id=item["id"],
                        completion_sha256="receipt")
    assert store.cancel(item["id"])["status"] == "succeeded"
    assert store.import_result(spec, "operator", "succeeded", experiment_id=item["id"],
                               completion_sha256="receipt")["status"] == "succeeded"


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
