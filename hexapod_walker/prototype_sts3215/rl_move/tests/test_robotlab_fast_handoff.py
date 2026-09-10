"""Fast, motionless checks for publishing evidence and releasing worker ownership."""

import hashlib
import io
import json
from pathlib import Path
import subprocess
import uuid

from fastapi.testclient import TestClient
import pytest

import hexapod_lab.codex_orchestrator as supervisor
from hexapod_lab.config import Settings
from hexapod_lab.db import Store
from hexapod_lab.finalize_run import LabPublisher, finalize
from hexapod_lab.handoff import HandoffExitWatch, SealedHandoffComplete, verify_handoff_manifest
from hexapod_lab.main import create_app


def settings(tmp_path, **overrides):
    return Settings(**dict(dict(data_dir=tmp_path, api_keys="admin:test:secret",
        driver="simulated", robot_command=(), camera_input="", bind="127.0.0.1",
        port=8767, public_base_url="", auto_worker=False, max_duration_seconds=10,
        codex_bin=Path("/bin/true"), codex_engineering_workdir=tmp_path,
        codex_handoff_exit_grace_seconds=1), **overrides))


def test_batch_upload_stays_pending_until_all_files_exist_then_hashes_once_per_boundary(tmp_path, monkeypatch):
    app = create_app(settings(tmp_path / "lab"))
    auth = {"Authorization": "Bearer secret"}
    with TestClient(app) as client:
        plan = client.post("/api/experiments", headers=auth, json={"name": "test",
            "duration_seconds": 1, "execution_mode": "external_guarded"}).json()
        eid = plan["id"]
        files = []
        for n in range(8):
            p = tmp_path / f"trace-{n}.csv"
            p.write_text(f"tick,angle\n0,{n}\n")
            files.append(p)
        manifests = []
        original = app.state.runner.write_manifest
        monkeypatch.setattr(app.state.runner, "write_manifest",
                            lambda path: (manifests.append(path), original(path))[1])

        class Publisher:
            def upload(self, experiment_id, path):
                assert app.state.store.get(eid)["status"] == "waiting_for_operator"
                response = client.put(f"/api/experiments/{eid}/artifacts/{path.name}?defer_manifest=true",
                                      headers=auth, content=path.read_bytes())
                assert response.status_code == 201, response.text
                assert manifests == []
                return path.stat().st_size

            def json(self, method, path, payload=None):
                response = client.request(method, path, headers=auth, json=payload)
                assert response.status_code == 200, response.text
                return response.json()

        receipt = finalize(Publisher(), eid, {"name": "test", "duration_seconds": 1,
            "status": "succeeded", "summary_markdown": "Raw measurements saved."}, files)
        assert receipt["uploaded_artifacts"] == 8
        assert len(manifests) == 2  # register and seal, not each upload
        manifest = json.loads((tmp_path / "lab" / "experiments" / eid / "manifest.json").read_text())
        entries = {entry["name"]: entry for entry in manifest["artifacts"]}
        for path in files:
            assert entries[path.name]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert app.state.store.get(eid)["evidence_sealed_at"]


def test_failed_upload_cannot_register_or_seal_success(tmp_path):
    path = tmp_path / "trace.csv"
    path.write_text("evidence")

    class BrokenPublisher:
        def upload(self, *_):
            raise OSError("interrupted")

        def json(self, method, *_):
            if method == "GET":
                return {"name": "test", "description": "", "duration_seconds": 1, "parameters": {}}
            pytest.fail("An incomplete bundle must remain pending")

    with pytest.raises(OSError, match="interrupted"):
        finalize(BrokenPublisher(), "a" * 32,
                 {"status": "succeeded", "summary_markdown": "test"}, [path])


@pytest.mark.parametrize("status,sealed", [("waiting_for_operator", True), ("failed", True),
                                          ("cancelled", True), ("succeeded", False)])
def test_exit_watch_does_not_retire_incomplete_or_failed_work(status, sealed):
    watch = HandoffExitWatch("test", 60)
    record = {"id": "test", "status": status, "evidence_manifest_sha256": "a" * 64,
              "evidence_sealed_at": "now" if sealed else None}
    assert watch.observe(record, 0) is None
    assert watch.observe(record, 1000) is None


def test_exit_grace_resets_if_sealed_identity_changes(tmp_path):
    watch = HandoffExitWatch("test", 60)
    record = {"id": "test", "status": "succeeded", "evidence_manifest_sha256": "a" * 64,
              "evidence_sealed_at": "now"}
    assert watch.observe(record, 0) is None
    record["evidence_manifest_sha256"] = "b" * 64
    assert watch.observe(record, 59) is None
    assert watch.observe(record, 60) is None
    receipt = watch.observe(record, 119)
    with pytest.raises(RuntimeError, match="missing"):
        verify_handoff_manifest(receipt, tmp_path)


def test_new_stop_keeps_successful_handoff_owned_until_resolved():
    watch = HandoffExitWatch("test", 60)
    record = {"id": "test", "status": "succeeded", "evidence_manifest_sha256": "a" * 64,
              "evidence_sealed_at": "now"}
    assert watch.observe(record, 0) is None
    assert watch.observe(record, 90, blocked=True) is None
    assert watch.observe(record, 100) is None
    assert watch.observe(record, 159) is None
    assert watch.observe(record, 160)


@pytest.mark.parametrize("cleanup_ok", [True, False])
def test_supervisor_stops_agent_before_releasing_completed_hardware_job(tmp_path, monkeypatch, cleanup_ok):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "sts3215")
    store = Store(tmp_path / "lab.sqlite3")
    orchestrator = supervisor.CodexOrchestrator(store, settings(tmp_path))
    plan = store.create({"name": "bounded test", "duration_seconds": 1,
        "execution_mode": "external_guarded", "parameters": {}}, "test")
    advance = store.enqueue_advance(uuid.uuid4().hex, "test", experiment_id=plan["id"])
    orchestrator.engineering.ensure_queue_handoff(advance, plan, 3)
    job = orchestrator.engineering.claim(orchestrator.owner, 600, lane="hardware")
    run_dir = tmp_path / "experiments" / plan["id"]
    run_dir.mkdir(parents=True)
    raw = b'{"artifacts": []}\n'
    (run_dir / "manifest.json").write_bytes(raw)
    with store.connect() as con:
        con.execute("UPDATE experiments SET status='succeeded',evidence_sealed_at='now',"
                    "evidence_manifest_sha256=? WHERE id=?",
                    (hashlib.sha256(raw).hexdigest(), plan["id"]))
    clock = [0.0]
    events = []

    class Process:
        pid = 987654321
        returncode = None

        def __init__(self, *_args, **_kwargs):
            self.stdin = io.BytesIO()

        def poll(self):
            return self.returncode

        def wait(self, timeout):
            clock[0] += 2
            raise subprocess.TimeoutExpired("fake agent", timeout)

    def terminate(process, **_kwargs):
        events.append("cleanup")
        assert orchestrator.engineering.list_jobs()[0]["status"] == "running"
        if cleanup_ok:
            process.returncode = -15
        return cleanup_ok

    monkeypatch.setattr(supervisor.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(supervisor.subprocess, "Popen", Process)
    monkeypatch.setattr(supervisor, "_terminate_deadline_wrapper", terminate)
    monkeypatch.setattr(supervisor, "_codex_runner_identity", lambda *_: {})
    monkeypatch.setattr(orchestrator, "_robot_telemetry_url", lambda: "disabled")
    monkeypatch.setattr(supervisor, "RobotCommunicationCapture", lambda *_a, **_k: None)
    monkeypatch.setattr(orchestrator, "_finalize_transcript", lambda *_: events.append("archive"))
    monkeypatch.setattr(orchestrator.provider, "materialize_output", lambda *_: "No model receipt")
    monkeypatch.setattr(supervisor, "workspace_snapshot", lambda *_: {"head": "abc"})
    monkeypatch.setattr(supervisor, "write_workspace_patch", lambda *_a, **_k: {"bytes": 0})
    monkeypatch.setattr(supervisor, "build_project_context", lambda *_: {"sha256": "c" * 64})
    monkeypatch.setattr(supervisor, "engineering_prompt", lambda *_: "test")
    if cleanup_ok:
        orchestrator._process_engineering(job)
        finished = orchestrator.engineering.list_jobs()[0]
        assert finished["status"] == "succeeded"
        assert finished["result"]["receipt_type"] == "supervisor_completed_handoff"
        assert events.index("cleanup") < events.index("archive")
        assert not orchestrator.processes
    else:
        with pytest.raises(supervisor.CodexCleanupError):
            orchestrator._process_engineering(job)
        assert orchestrator.engineering.list_jobs()[0]["status"] == "running"
        assert orchestrator.processes
        assert "archive" not in events


def test_publisher_rejects_plaintext_remote_or_credential_urls():
    for url in ["http://example.com", "https://user:pass@example.com", "https://example.com/?key=x"]:
        with pytest.raises(ValueError):
            LabPublisher(url, "secret")
