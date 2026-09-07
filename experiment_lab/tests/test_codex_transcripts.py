import hashlib
import json
import sqlite3
import subprocess
import sys

from fastapi.testclient import TestClient
import pytest

from hexapod_lab.codex_orchestrator import _redact_for_model, _redact_text
from hexapod_lab.codex_transcripts import finalize_codex_transcript
from hexapod_lab.config import Settings
from hexapod_lab.engineering_lane import EngineeringJobStore
from hexapod_lab.main import create_app


def configured(tmp_path):
    return Settings(
        data_dir=tmp_path,
        api_keys="admin:alice:secret,viewer:bob:read-only",
        driver="simulated",
        robot_command=(),
        camera_input="",
        bind="127.0.0.1",
        port=8767,
        public_base_url="",
        auto_worker=False,
        max_duration_seconds=30,
    )


def write_attempt(run_dir, *, experiment_id, job_id, kind="analysis", **limits):
    run_dir.mkdir(parents=True)
    (run_dir / "prompt.md").write_text(
        "Analyze evidence. api_key=prompt-super-secret\n", encoding="utf-8"
    )
    events = [
        {"type": "thread.started", "thread_id": "thread-1"},
        {
            "type": "item.completed",
            "item": {
                "type": "reasoning",
                "text": "Checked authorization: Bearer reasoning-secret-token",
            },
        },
        {
            "type": "item.completed",
            "item": {
                "type": "agent_message",
                "text": "The bounded test passed.",
                "credentials": "event-secret",
            },
        },
    ]
    (run_dir / ".events.raw.jsonl").write_text(
        "".join(json.dumps(event) + "\n" for event in events)
        + "stderr token=unparsed-secret-value\n",
        encoding="utf-8",
    )
    (run_dir / ".stderr.raw.log").write_text(
        "authorization=Bearer stderr-secret-token\n", encoding="utf-8"
    )
    manifest = finalize_codex_transcript(
        run_dir,
        job_id=job_id,
        experiment_id=experiment_id,
        kind=kind,
        attempt=1,
        redact=_redact_for_model,
        redact_text=_redact_text,
        **limits,
    )
    return manifest


def test_attempt_archive_preserves_full_event_stream_and_redacts_secrets(tmp_path):
    evidence_dir = tmp_path / "experiments" / "experiment-1"
    evidence_dir.mkdir(parents=True)
    evidence_manifest = evidence_dir / "manifest.json"
    evidence_manifest.write_text('{"sealed":true}\n')
    sealed_bytes = evidence_manifest.read_bytes()
    run_dir = tmp_path / "codex-runs" / "job-1" / "attempt-1"
    manifest = write_attempt(
        run_dir, experiment_id="experiment-1", job_id="job-1"
    )

    assert not (run_dir / ".events.raw.jsonl").exists()
    assert not (run_dir / ".stderr.raw.log").exists()
    events = [
        json.loads(line)
        for line in (run_dir / "events.jsonl").read_text().splitlines()
    ]
    assert [event["type"] for event in events] == [
        "thread.started",
        "item.completed",
        "item.completed",
        "unparsed_output",
    ]
    transcript = (run_dir / "transcript.md").read_text()
    assert "## Input prompt" in transcript
    assert "### Assistant reasoning summary" in transcript
    assert "### Assistant" in transcript
    assert "The bounded test passed." in transcript
    archived = "\n".join(
        (run_dir / name).read_text()
        for name in ("prompt.md", "events.jsonl", "stderr.log", "transcript.md")
    )
    for secret in (
        "prompt-super-secret",
        "reasoning-secret-token",
        "event-secret",
        "unparsed-secret-value",
        "stderr-secret-token",
    ):
        assert secret not in archived
    assert {entry["name"] for entry in manifest["files"]} == {
        "prompt.md",
        "events.jsonl",
        "transcript.md",
        "stderr.log",
    }
    for entry in manifest["files"]:
        path = run_dir / entry["name"]
        assert entry["bytes"] == path.stat().st_size
        assert entry["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert path.stat().st_mode & 0o777 == 0o400
    assert evidence_manifest.read_bytes() == sealed_bytes
    assert not (evidence_dir / "transcript.md").exists()


def test_experiment_exposes_authenticated_integrity_checked_attempts(tmp_path):
    app = create_app(configured(tmp_path))
    store = app.state.store
    experiment = store.create(
        {"name": "transcript source", "duration_seconds": 1}, "test"
    )
    store.finish(experiment["id"], "succeeded")
    analysis = next(
        job
        for job in store.codex_jobs_for_experiment(experiment["id"])
        if job["kind"] == "analysis"
    )
    # A real worker increments attempts before creating this directory.
    with store.connect() as connection:
        connection.execute(
            "UPDATE codex_jobs SET attempts=1 WHERE id=?", (analysis["id"],)
        )
    attempt_dir = (
        tmp_path / "codex-runs" / analysis["id"] / "attempt-1"
    )
    write_attempt(
        attempt_dir,
        experiment_id=experiment["id"],
        job_id=analysis["id"],
    )
    manifest_digest = hashlib.sha256(
        (attempt_dir / "transcript.manifest.json").read_bytes()
    ).hexdigest()
    store.register_codex_transcript_attempt(analysis["id"], 1, manifest_digest)

    viewer = {"Authorization": "Bearer read-only"}
    with TestClient(app) as client:
        item = client.get(
            f"/api/experiments/{experiment['id']}", headers=viewer
        ).json()
        job = next(job for job in item["codex_jobs"] if job["id"] == analysis["id"])
        attempt = job["transcript_attempts"][0]
        assert attempt["available"] is True
        assert attempt["state"] == "finalized"
        assert client.get(attempt["transcript_url"]).status_code == 401
        transcript = client.get(attempt["transcript_url"], headers=viewer)
        assert transcript.status_code == 200
        assert "The bounded test passed." in transcript.text
        assert transcript.headers["cache-control"] == "private, no-store"
        page = client.get(f"/experiments/{experiment['id']}", headers=viewer)
        assert page.status_code == 200
        assert attempt["transcript_url"] in page.text
        assert attempt["events_url"] in page.text
        machine = client.get(attempt["events_url"], headers=viewer)
        assert machine.status_code == 403
        machine = client.get(
            attempt["events_url"],
            headers={"Authorization": "Bearer secret"},
        )
        assert machine.status_code == 200
        assert len(machine.text.splitlines()) == 4

        # A transcript from another experiment/job cannot be selected by URL.
        assert client.get(
            attempt["transcript_url"].replace(experiment["id"], "not-this-run"),
            headers=viewer,
        ).status_code == 404

        events_path = attempt_dir / "events.jsonl"
        events_path.chmod(0o600)
        events_path.write_text("{}\n")
        changed = client.get(
            attempt["events_url"],
            headers={"Authorization": "Bearer secret"},
        )
        assert changed.status_code == 409
        refreshed = client.get(
            f"/api/experiments/{experiment['id']}", headers=viewer
        ).json()
        changed_job = next(
            job for job in refreshed["codex_jobs"] if job["id"] == analysis["id"]
        )
        assert changed_job["transcript_attempts"][0]["state"] == "integrity_error"


def test_transcript_receipt_is_idempotent_and_immutable(tmp_path):
    app = create_app(configured(tmp_path))
    store = app.state.store
    experiment = store.create({"name": "x", "duration_seconds": 1}, "test")
    store.finish(experiment["id"], "succeeded")
    job = next(
        item
        for item in store.codex_jobs_for_experiment(experiment["id"])
        if item["kind"] == "analysis"
    )
    with store.connect() as connection:
        connection.execute("UPDATE codex_jobs SET attempts=1 WHERE id=?", (job["id"],))
    digest = "a" * 64
    first = store.register_codex_transcript_attempt(job["id"], 1, digest)
    assert store.register_codex_transcript_attempt(job["id"], 1, digest) == first
    with pytest.raises(ValueError, match="sealed differently"):
        store.register_codex_transcript_attempt(job["id"], 1, "b" * 64)
    with store.connect() as connection:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE codex_transcript_attempts SET manifest_sha256=? "
                "WHERE job_id=? AND attempt=1",
                ("c" * 64, job["id"]),
            )


def test_event_line_cap_is_explicit_and_machine_readable(tmp_path):
    run_dir = tmp_path / "codex-runs" / "job-capped" / "attempt-1"
    write_attempt(
        run_dir,
        experiment_id="experiment-capped",
        job_id="job-capped",
        max_event_lines=2,
    )
    events = [
        json.loads(line)
        for line in (run_dir / "events.jsonl").read_text().splitlines()
    ]
    assert len(events) == 3
    assert events[-1] == {
        "type": "capture.truncated",
        "reason": "event_line_count_limit",
        "source_bytes_retained": sum(
            len((json.dumps(event) + "\n").encode())
            for event in [
                {"type": "thread.started", "thread_id": "thread-1"},
                {
                    "type": "item.completed",
                    "item": {
                        "type": "reasoning",
                        "text": "Checked authorization: Bearer reasoning-secret-token",
                    },
                },
            ]
        ),
        "source_lines_retained": 2,
    }


def test_kernel_file_limit_bounds_a_run_even_without_supervisor_polling(tmp_path):
    output = tmp_path / "bounded-output.log"
    with output.open("wb") as handle:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "hexapod_lab.deadline_exec",
                "--marker",
                "0" * 32,
                "--timeout-seconds",
                "5",
                "--max-file-bytes",
                str(64 * 1024),
                "--",
                sys.executable,
                "-c",
                "import os; [(os.write(1, b'x' * 65536)) for _ in range(32)]",
            ],
            stdout=handle,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
            start_new_session=True,
        )
    assert completed.returncode != 0
    assert output.stat().st_size <= 64 * 1024


def test_engineering_transcript_attaches_but_view_omits_prompt_and_reasoning(tmp_path):
    app = create_app(configured(tmp_path))
    store = app.state.store
    engineering = EngineeringJobStore(store)
    experiment = store.create({"name": "engineering source", "duration_seconds": 1}, "test")
    store.finish(experiment["id"], "succeeded")
    store.seal_evidence(experiment["id"], "a" * 64)
    analysis = store.claim_codex_job("analysis", "test-worker", lease_seconds=60)
    assert analysis is not None
    store.finish_codex_job(
        analysis["id"],
        "test-worker",
        "succeeded",
        result={"safety_disposition": "clear", "what_we_learned": "bounded"},
        lease_token=analysis["lease_token"],
    )
    assert engineering.reconcile() == 1
    job = engineering.claim("engineer", 60)
    assert job is not None
    attempt_dir = tmp_path / "codex-runs" / job["id"] / "attempt-1"
    write_attempt(
        attempt_dir,
        experiment_id=experiment["id"],
        job_id=job["id"],
        kind="engineering",
    )
    digest = hashlib.sha256(
        (attempt_dir / "transcript.manifest.json").read_bytes()
    ).hexdigest()
    store.register_codex_transcript_attempt(
        job["id"], 1, digest, kind="engineering"
    )

    viewer = {"Authorization": "Bearer read-only"}
    with TestClient(app) as client:
        item = client.get(
            f"/api/experiments/{experiment['id']}", headers=viewer
        ).json()
        surfaced = item["codex_engineering_jobs"][0]
        assert "lease_token" not in surfaced
        transcript_info = surfaced["transcript_attempts"][0]
        assert transcript_info["available"] is True
        transcript = client.get(
            transcript_info["transcript_url"], headers=viewer
        ).text
        assert "viewer-safe engineering transcript" in transcript
        assert "The bounded test passed." in transcript
        assert "Analyze evidence" not in transcript
        assert "Assistant reasoning summary" not in transcript
