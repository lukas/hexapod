from pathlib import Path

from fastapi.testclient import TestClient

from hexapod_lab.codex_transcripts import CodexTranscriptArchive
from hexapod_lab.config import Settings
from hexapod_lab.main import create_app


def test_monitor_status_is_authenticated_and_never_reads_historical_evidence(tmp_path, monkeypatch):
    settings = Settings(
        data_dir=tmp_path, api_keys="viewer:bob:read-only", driver="simulated",
        robot_command=(), camera_input="", bind="127.0.0.1", port=8767,
        public_base_url="", auto_worker=False, max_duration_seconds=2,
        codex_evidence_settle_seconds=0,
    )
    app = create_app(settings)
    store = app.state.store
    item = store.create({"name": "historical run", "duration_seconds": 1}, "test")
    store.finish(item["id"], "failed", "camera unavailable")
    store.seal_evidence(item["id"], "a" * 64)
    job = store.claim_codex_job("analysis", "test", lease_seconds=60)
    store.finish_codex_job(
        job["id"], "test", "succeeded", lease_token=job["lease_token"],
        result={"safety_disposition": "stop", "what_we_learned": "Physical inspection needed."},
    )
    store.pause_codex_queue(job["id"], "Physical inspection needed.")
    run_dir = tmp_path / "experiments" / item["id"]
    run_dir.mkdir(parents=True)
    (run_dir / "large-transcript.jsonl").write_text("evidence is deliberately unavailable to monitoring")

    def reject_enrichment(*_args, **_kwargs):
        raise AssertionError("Monitoring must not inspect historical evidence")

    monkeypatch.setattr(CodexTranscriptArchive, "attempts_for_job", reject_enrichment)
    monkeypatch.setattr(store, "events", reject_enrichment)
    monkeypatch.setattr(store, "learnings", reject_enrichment)
    original_iterdir = Path.iterdir

    def no_artifact_enumeration(path):
        if path == run_dir:
            reject_enrichment()
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", no_artifact_enumeration)
    with TestClient(app) as client:
        assert client.get("/api/monitor-status").status_code == 401
        response = client.get("/api/monitor-status", headers={"Authorization": "Bearer read-only"})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    payload = response.json()
    assert payload["control"] == store.codex_queue_control()
    assert payload["control"]["paused"] is True
    monitored = payload["experiments"][0]
    assert monitored["id"] == item["id"]
    assert monitored["status"] == "failed"
    assert monitored["error"] == "camera unavailable"
    analysis = next(entry for entry in monitored["codex_jobs"] if entry["kind"] == "analysis")
    assert analysis["result"]["safety_disposition"] == "stop"
    assert "transcript_attempts" not in analysis
    assert "lease_token" not in analysis
    assert "artifacts" not in monitored
    assert "events" not in monitored
