import hashlib
import json
import sqlite3
import subprocess
import sys

from fastapi.testclient import TestClient
import pytest

from hexapod_lab.codex_orchestrator import _redact_for_model, _redact_text
from hexapod_lab.codex_transcripts import (
    ROBOT_COMMUNICATION_MANIFEST,
    CodexTranscriptArchive,
    CodexTranscriptIntegrityError,
    CodexTranscriptNotFound,
    finalize_codex_transcript,
    finalize_robot_communication_manifest,
    verify_robot_communication_manifest,
)
from hexapod_lab.communication_capture import STATUS_NAME, TRANSCRIPT_NAME
from hexapod_lab.config import Settings
from hexapod_lab.engineering_lane import EngineeringJobStore
from hexapod_lab.main import _bounded_codex_text, create_app


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


def communication_marker(
    marker_id, label, *, experiment_id, job_id, attempt=1, seq,
):
    return {
        "schema_version": 2,
        "record_type": "marker",
        "marker_id": marker_id,
        "label": label,
        "seq": seq,
        "data": {
            "experiment_id": experiment_id,
            "job_id": job_id,
            "attempt": attempt,
        },
    }


def communication_recorder(marker_id, *, seq, checkpoint=0):
    path = "/robot/logs/telemetry_part_001.jsonl"
    return {
        "active": True,
        "communication_capture": True,
        "communication_scope": "host_mcu_serial",
        "communication_rate_limited": False,
        "piggyback_snapshots": False,
        "writer_alive": True,
        "write_error": None,
        "paths": [path],
        "flushed_marker": marker_id,
        "marker_ack": {
            "marker_id": marker_id,
            "path": path,
            "paths": [path],
            "seq": seq,
            "written": 1,
            "capture_checkpoint": {
                "queue_dropped": checkpoint,
                "communication_dropped": checkpoint,
                "uncaptured_bytes": checkpoint,
                "capture_errors": checkpoint,
            },
        },
    }


def write_communication(
    run_dir,
    *,
    experiment_id,
    job_id,
    attempt=1,
    complete=True,
    capture_state=None,
    include_transcript=True,
    rows=None,
    status_changes=None,
):
    begin_marker = "begin-marker"
    end_marker = "end-marker"
    rows = rows or [
        communication_marker(
            begin_marker,
            "robotlab_run_begin",
            experiment_id=experiment_id,
            job_id=job_id,
            attempt=attempt,
            seq=10,
        ),
        {
            "schema_version": 2,
            "record_type": "serial_tx",
            "seq": 11,
            "data_hex": "a55a",
        },
        communication_marker(
            end_marker,
            "robotlab_run_end",
            experiment_id=experiment_id,
            job_id=job_id,
            attempt=attempt,
            seq=12,
        ),
    ]
    transcript_path = run_dir / TRANSCRIPT_NAME
    if include_transcript:
        transcript_path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
        transcript_receipt = {
            "name": TRANSCRIPT_NAME,
            "bytes": transcript_path.stat().st_size,
            "sha256": hashlib.sha256(transcript_path.read_bytes()).hexdigest(),
        }
    else:
        transcript_path.unlink(missing_ok=True)
        transcript_receipt = None
    status = {
        "schema_version": 1,
        "complete": complete,
        "capture_state": capture_state or (
            "terminal_complete" if complete else "retryable"
        ),
        "scope": "host_mcu_serial",
        "experiment_id": experiment_id,
        "job_id": job_id,
        "attempt": attempt,
        "telemetry_url": "http://robot.test:8080/api/telemetry",
        "started_at": "2026-08-01T00:00:00+00:00",
        "finished_at": "2026-08-01T00:01:00+00:00",
        "begin_marker": begin_marker,
        "end_marker": end_marker,
        "loss_deltas": {
            "queue_dropped": 0,
            "communication_dropped": 0,
            "uncaptured_bytes": 0,
            "capture_errors": 0,
        },
        "errors": [],
        "transcript": transcript_receipt,
        "begin_recorder": communication_recorder(begin_marker, seq=10),
        "end_recorder": communication_recorder(end_marker, seq=12),
    }
    if status_changes:
        status.update(status_changes)
    (run_dir / STATUS_NAME).write_text(
        json.dumps(status) + "\n", encoding="utf-8"
    )
    return status


def write_attempt(
    run_dir, *, experiment_id, job_id, kind="analysis",
    communication=False, **limits,
):
    run_dir.mkdir(parents=True, exist_ok=True)
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
    if communication:
        write_communication(
            run_dir,
            experiment_id=experiment_id,
            job_id=job_id,
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


def test_bounded_jsonl_view_uses_full_budget_without_splitting_records(tmp_path):
    path = tmp_path / "large.jsonl"
    rows = [
        json.dumps({"index": index, "payload": "x" * 3000}) + "\n"
        for index in range(3)
    ]
    path.write_text("".join(rows), encoding="utf-8")

    result = _bounded_codex_text(path, 4096)

    assert result["view"] == "head_tail"
    returned = result["head"].splitlines() + result["tail"].splitlines()
    assert returned
    assert all(isinstance(json.loads(line), dict) for line in returned)
    assert result["omitted_bytes"] > 0


def test_communication_attachment_retries_without_resealing_legacy_manifest(tmp_path):
    run_dir = tmp_path / "codex-runs" / "job-retry" / "attempt-1"
    legacy = write_attempt(
        run_dir, experiment_id="experiment-retry", job_id="job-retry"
    )
    legacy_bytes = (run_dir / "transcript.manifest.json").read_bytes()
    assert {entry["name"] for entry in legacy["files"]} == {
        "prompt.md", "events.jsonl", "transcript.md", "stderr.log",
    }

    write_communication(
        run_dir,
        experiment_id="experiment-retry",
        job_id="job-retry",
        complete=False,
    )
    repeated = finalize_codex_transcript(
        run_dir,
        job_id="job-retry",
        experiment_id="experiment-retry",
        kind="analysis",
        attempt=1,
        redact=_redact_for_model,
        redact_text=_redact_text,
    )
    assert repeated == legacy
    assert not (run_dir / ROBOT_COMMUNICATION_MANIFEST).exists()
    assert (run_dir / STATUS_NAME).stat().st_mode & 0o200

    write_communication(
        run_dir,
        experiment_id="experiment-retry",
        job_id="job-retry",
    )
    finalize_codex_transcript(
        run_dir,
        job_id="job-retry",
        experiment_id="experiment-retry",
        kind="analysis",
        attempt=1,
        redact=_redact_for_model,
        redact_text=_redact_text,
    )

    assert (run_dir / "transcript.manifest.json").read_bytes() == legacy_bytes
    communication = verify_robot_communication_manifest(
        run_dir,
        expected_job_id="job-retry",
        expected_experiment_id="experiment-retry",
        expected_kind="analysis",
        expected_attempt=1,
    )
    assert {entry["name"] for entry in communication["files"]} == {
        STATUS_NAME, TRANSCRIPT_NAME,
    }
    for name in (
        *(entry["name"] for entry in communication["files"]),
        ROBOT_COMMUNICATION_MANIFEST,
    ):
        assert (run_dir / name).stat().st_mode & 0o777 == 0o400


def test_terminal_incomplete_status_only_is_sealed_as_diagnostic(tmp_path):
    run_dir = tmp_path / "attempt-1"
    run_dir.mkdir()
    status = write_communication(
        run_dir,
        experiment_id="experiment-diagnostic",
        job_id="job-diagnostic",
        complete=False,
        capture_state="terminal_incomplete",
        include_transcript=False,
        status_changes={
            "begin_marker": None,
            "end_marker": None,
            "begin_recorder": None,
            "end_recorder": None,
            "loss_deltas": {
                "queue_dropped": None,
                "communication_dropped": None,
                "uncaptured_bytes": None,
                "capture_errors": None,
            },
            "errors": ["begin: OSError: recorder offline"],
        },
    )
    assert status["transcript"] is None

    manifest = finalize_robot_communication_manifest(
        run_dir,
        expected_job_id="job-diagnostic",
        expected_experiment_id="experiment-diagnostic",
        expected_kind="engineering",
        expected_attempt=1,
    )

    assert manifest is not None
    assert manifest["capture_state"] == "terminal_incomplete"
    assert manifest["communication_complete"] is False
    assert manifest["integrity"] == {
        "status": "verified",
        "transcript": "absent",
    }
    assert [entry["name"] for entry in manifest["files"]] == [STATUS_NAME]
    assert not (run_dir / TRANSCRIPT_NAME).exists()
    verify_robot_communication_manifest(
        run_dir,
        expected_job_id="job-diagnostic",
        expected_experiment_id="experiment-diagnostic",
        expected_kind="engineering",
        expected_attempt=1,
    )


def test_archive_exposes_receipted_status_only_diagnostic_without_raw_url(tmp_path):
    run_dir = tmp_path / "codex-runs" / "job-diagnostic" / "attempt-1"
    run_dir.mkdir(parents=True)
    write_communication(
        run_dir,
        experiment_id="experiment-diagnostic",
        job_id="job-diagnostic",
        complete=False,
        capture_state="terminal_incomplete",
        include_transcript=False,
        status_changes={
            "begin_marker": None,
            "end_marker": None,
            "begin_recorder": None,
            "end_recorder": None,
            "loss_deltas": {name: None for name in (
                "queue_dropped", "communication_dropped",
                "uncaptured_bytes", "capture_errors",
            )},
            "errors": ["begin: OSError: recorder offline"],
        },
    )
    write_attempt(
        run_dir,
        experiment_id="experiment-diagnostic",
        job_id="job-diagnostic",
    )
    legacy_digest = hashlib.sha256(
        (run_dir / "transcript.manifest.json").read_bytes()
    ).hexdigest()
    communication_digest = hashlib.sha256(
        (run_dir / ROBOT_COMMUNICATION_MANIFEST).read_bytes()
    ).hexdigest()

    class ReceiptStore:
        @staticmethod
        def get_codex_transcript_source_job(_job_id):
            return {
                "id": "job-diagnostic",
                "experiment_id": "experiment-diagnostic",
                "kind": "analysis",
            }

        @staticmethod
        def codex_transcript_attempt(_job_id, _attempt):
            return {"manifest_sha256": legacy_digest}

        @staticmethod
        def codex_communication_attempt(_job_id, _attempt):
            return {"manifest_sha256": communication_digest}

    archive = CodexTranscriptArchive(tmp_path, ReceiptStore())
    job = ReceiptStore.get_codex_transcript_source_job("job-diagnostic")
    descriptor = archive.attempts_for_job("experiment-diagnostic", job)[0]

    assert descriptor["communication_available"] is True
    assert descriptor["communication_complete"] is False
    assert descriptor["communication_capture_state"] == "terminal_incomplete"
    assert descriptor["communication_status_url"].endswith(STATUS_NAME)
    assert "communication_url" not in descriptor
    assert archive.resolve(
        "experiment-diagnostic", "job-diagnostic", 1, STATUS_NAME
    ) == run_dir / STATUS_NAME
    with pytest.raises(CodexTranscriptNotFound):
        archive.resolve(
            "experiment-diagnostic", "job-diagnostic", 1, TRANSCRIPT_NAME
        )


def test_status_only_diagnostic_requires_explicit_incomplete_reason(tmp_path):
    run_dir = tmp_path / "attempt-1"
    run_dir.mkdir()
    write_communication(
        run_dir,
        experiment_id="experiment-no-reason",
        job_id="job-no-reason",
        complete=False,
        capture_state="terminal_incomplete",
        include_transcript=False,
    )

    with pytest.raises(CodexTranscriptIntegrityError, match="incomplete reason"):
        finalize_robot_communication_manifest(
            run_dir,
            expected_job_id="job-no-reason",
            expected_experiment_id="experiment-no-reason",
            expected_kind="engineering",
            expected_attempt=1,
        )


def test_terminal_incomplete_lossy_raw_is_sealed_as_diagnostic(tmp_path):
    run_dir = tmp_path / "attempt-1"
    run_dir.mkdir()
    end_recorder = communication_recorder("end-marker", seq=12)
    end_recorder["marker_ack"]["capture_checkpoint"][
        "communication_dropped"
    ] = 3
    write_communication(
        run_dir,
        experiment_id="experiment-lossy",
        job_id="job-lossy",
        complete=False,
        capture_state="terminal_incomplete",
        status_changes={
            "loss_deltas": {
                "queue_dropped": 0,
                "communication_dropped": 3,
                "uncaptured_bytes": 0,
                "capture_errors": 0,
            },
            "end_recorder": end_recorder,
        },
    )

    manifest = finalize_robot_communication_manifest(
        run_dir,
        expected_job_id="job-lossy",
        expected_experiment_id="experiment-lossy",
        expected_kind="engineering",
        expected_attempt=1,
    )

    assert manifest is not None
    assert manifest["communication_complete"] is False
    assert manifest["integrity"]["transcript"] == "verified_marker_bounded"
    assert {entry["name"] for entry in manifest["files"]} == {
        STATUS_NAME, TRANSCRIPT_NAME,
    }


@pytest.mark.parametrize("end_sequence", [10, 9])
def test_communication_manifest_requires_forward_marker_sequence(
    tmp_path, end_sequence,
):
    run_dir = tmp_path / "attempt-1"
    run_dir.mkdir()
    write_communication(
        run_dir,
        experiment_id="experiment-sequence",
        job_id="job-sequence",
        status_changes={
            "end_recorder": communication_recorder(
                "end-marker", seq=end_sequence
            ),
        },
    )

    with pytest.raises(CodexTranscriptIntegrityError, match="sequence"):
        finalize_robot_communication_manifest(
            run_dir,
            expected_job_id="job-sequence",
            expected_experiment_id="experiment-sequence",
            expected_kind="engineering",
            expected_attempt=1,
        )


def test_invalid_communication_does_not_block_legacy_transcript_seal(tmp_path):
    run_dir = tmp_path / "codex-runs" / "job-isolated" / "attempt-1"
    run_dir.mkdir(parents=True)
    write_communication(
        run_dir,
        experiment_id="experiment-isolated",
        job_id="wrong-job",
    )

    manifest = write_attempt(
        run_dir,
        experiment_id="experiment-isolated",
        job_id="job-isolated",
    )

    assert {entry["name"] for entry in manifest["files"]} == {
        "prompt.md", "events.jsonl", "transcript.md", "stderr.log",
    }
    assert (run_dir / "transcript.manifest.json").is_file()
    assert not (run_dir / ROBOT_COMMUNICATION_MANIFEST).exists()


def test_archive_isolates_unsealed_communication_integrity_error(tmp_path):
    app = create_app(configured(tmp_path))
    store = app.state.store
    experiment = store.create(
        {"name": "isolated attachment", "duration_seconds": 1}, "test"
    )
    store.finish(experiment["id"], "succeeded")
    job = next(
        item
        for item in store.codex_jobs_for_experiment(experiment["id"])
        if item["kind"] == "analysis"
    )
    with store.connect() as connection:
        connection.execute(
            "UPDATE codex_jobs SET attempts=1 WHERE id=?", (job["id"],)
        )
    run_dir = tmp_path / "codex-runs" / job["id"] / "attempt-1"
    run_dir.mkdir(parents=True)
    write_communication(
        run_dir,
        experiment_id=experiment["id"],
        job_id="wrong-job",
    )
    write_attempt(
        run_dir,
        experiment_id=experiment["id"],
        job_id=job["id"],
    )
    legacy_digest = hashlib.sha256(
        (run_dir / "transcript.manifest.json").read_bytes()
    ).hexdigest()
    store.register_codex_transcript_attempt(job["id"], 1, legacy_digest)

    with TestClient(app) as client:
        item = client.get(
            f"/api/experiments/{experiment['id']}",
            headers={"Authorization": "Bearer read-only"},
        ).json()

    surfaced = next(
        candidate for candidate in item["codex_jobs"] if candidate["id"] == job["id"]
    )["transcript_attempts"][0]
    assert surfaced["available"] is True
    assert surfaced["state"] == "finalized"
    assert surfaced["communication_available"] is False
    assert surfaced["communication_state"] == "integrity_error"
    assert "communication_status_url" not in surfaced


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"schema_version": 2}, "schema"),
        ({"job_id": "other-job"}, "identity"),
        ({"experiment_id": "other-experiment"}, "identity"),
        ({"attempt": 2}, "identity"),
        ({"complete": "yes"}, "completeness"),
        ({"capture_state": "done"}, "lifecycle"),
        ({"capture_state": "terminal_incomplete"}, "contradicts"),
        ({"scope": "all_telemetry"}, "scope"),
        ({"errors": ["capture failed"]}, "reports errors"),
        ({"loss_deltas": {
            "queue_dropped": 0,
            "communication_dropped": 1,
            "uncaptured_bytes": 0,
            "capture_errors": 0,
        }}, "loss accounting mismatch"),
    ],
)
def test_communication_manifest_rejects_invalid_complete_status(
    tmp_path, changes, message,
):
    run_dir = tmp_path / "attempt-1"
    run_dir.mkdir()
    write_communication(
        run_dir,
        experiment_id="experiment-status",
        job_id="job-status",
        status_changes=changes,
    )

    with pytest.raises(CodexTranscriptIntegrityError, match=message):
        finalize_robot_communication_manifest(
            run_dir,
            expected_job_id="job-status",
            expected_experiment_id="experiment-status",
            expected_kind="engineering",
            expected_attempt=1,
        )
    assert not (run_dir / ROBOT_COMMUNICATION_MANIFEST).exists()


@pytest.mark.parametrize(
    "rows",
    [
        [
            communication_marker(
                "wrong-begin", "robotlab_run_begin",
                experiment_id="experiment-raw", job_id="job-raw", seq=10,
            ),
            communication_marker(
                "end-marker", "robotlab_run_end",
                experiment_id="experiment-raw", job_id="job-raw", seq=12,
            ),
        ],
        [
            communication_marker(
                "begin-marker", "robotlab_run_begin",
                experiment_id="experiment-raw", job_id="job-raw", seq=10,
            ),
            communication_marker(
                "wrong-end", "robotlab_run_end",
                experiment_id="experiment-raw", job_id="job-raw", seq=12,
            ),
        ],
        [
            communication_marker(
                "begin-marker", "robotlab_run_begin",
                experiment_id="experiment-raw", job_id="job-raw", seq=10,
            ),
            communication_marker(
                "end-marker", "robotlab_run_end",
                experiment_id="experiment-raw", job_id="job-raw", seq=12,
            ),
            {"record_type": "serial_rx", "data_hex": "late"},
        ],
        [
            communication_marker(
                "begin-marker", "robotlab_run_begin",
                experiment_id="experiment-raw", job_id="job-raw", seq=9,
            ),
            communication_marker(
                "end-marker", "robotlab_run_end",
                experiment_id="experiment-raw", job_id="job-raw", seq=12,
            ),
        ],
        [
            communication_marker(
                "begin-marker", "robotlab_run_begin",
                experiment_id="experiment-raw", job_id="other-job", seq=10,
            ),
            communication_marker(
                "end-marker", "robotlab_run_end",
                experiment_id="experiment-raw", job_id="job-raw", seq=12,
            ),
        ],
    ],
)
def test_communication_manifest_rejects_invalid_raw_boundaries(tmp_path, rows):
    run_dir = tmp_path / "attempt-1"
    run_dir.mkdir()
    write_communication(
        run_dir,
        experiment_id="experiment-raw",
        job_id="job-raw",
        rows=rows,
    )

    with pytest.raises(CodexTranscriptIntegrityError, match="marker"):
        finalize_robot_communication_manifest(
            run_dir,
            expected_job_id="job-raw",
            expected_experiment_id="experiment-raw",
            expected_kind="engineering",
            expected_attempt=1,
        )
    assert not (run_dir / ROBOT_COMMUNICATION_MANIFEST).exists()


@pytest.mark.parametrize("field", ["name", "bytes", "sha256"])
def test_communication_manifest_rejects_status_transcript_receipt_mismatch(
    tmp_path, field,
):
    run_dir = tmp_path / "attempt-1"
    run_dir.mkdir()
    status = write_communication(
        run_dir,
        experiment_id="experiment-receipt",
        job_id="job-receipt",
    )
    status["transcript"][field] = {
        "name": "other.jsonl",
        "bytes": status["transcript"]["bytes"] + 1,
        "sha256": "f" * 64,
    }[field]
    (run_dir / STATUS_NAME).write_text(json.dumps(status) + "\n")

    with pytest.raises(CodexTranscriptIntegrityError, match="transcript"):
        finalize_robot_communication_manifest(
            run_dir,
            expected_job_id="job-receipt",
            expected_experiment_id="experiment-receipt",
            expected_kind="engineering",
            expected_attempt=1,
        )


def test_communication_manifest_rejects_malformed_raw_jsonl(tmp_path):
    run_dir = tmp_path / "attempt-1"
    run_dir.mkdir()
    status = write_communication(
        run_dir,
        experiment_id="experiment-jsonl",
        job_id="job-jsonl",
    )
    transcript_path = run_dir / TRANSCRIPT_NAME
    transcript_path.write_text(
        json.dumps(communication_marker(
            "begin-marker",
            "robotlab_run_begin",
            experiment_id="experiment-jsonl",
            job_id="job-jsonl",
            seq=10,
        ))
        + "\nnot-json\n"
        + json.dumps(communication_marker(
            "end-marker",
            "robotlab_run_end",
            experiment_id="experiment-jsonl",
            job_id="job-jsonl",
            seq=12,
        ))
        + "\n"
    )
    status["transcript"].update({
        "bytes": transcript_path.stat().st_size,
        "sha256": hashlib.sha256(transcript_path.read_bytes()).hexdigest(),
    })
    (run_dir / STATUS_NAME).write_text(json.dumps(status) + "\n")

    with pytest.raises(CodexTranscriptIntegrityError, match="valid JSONL"):
        finalize_robot_communication_manifest(
            run_dir,
            expected_job_id="job-jsonl",
            expected_experiment_id="experiment-jsonl",
            expected_kind="engineering",
            expected_attempt=1,
        )


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
        communication=True,
    )
    legacy_manifest = json.loads(
        (attempt_dir / "transcript.manifest.json").read_text()
    )
    assert {entry["name"] for entry in legacy_manifest["files"]} == {
        "prompt.md", "events.jsonl", "transcript.md", "stderr.log",
    }
    communication_manifest = json.loads(
        (attempt_dir / ROBOT_COMMUNICATION_MANIFEST).read_text()
    )
    assert {entry["name"] for entry in communication_manifest["files"]} == {
        STATUS_NAME, TRANSCRIPT_NAME,
    }
    manifest_digest = hashlib.sha256(
        (attempt_dir / "transcript.manifest.json").read_bytes()
    ).hexdigest()
    store.register_codex_transcript_attempt(analysis["id"], 1, manifest_digest)
    communication_digest = hashlib.sha256(
        (attempt_dir / ROBOT_COMMUNICATION_MANIFEST).read_bytes()
    ).hexdigest()

    viewer = {"Authorization": "Bearer read-only"}
    with TestClient(app) as client:
        pending_item = client.get(
            f"/api/experiments/{experiment['id']}", headers=viewer
        ).json()
        pending_job = next(
            job for job in pending_item["codex_jobs"] if job["id"] == analysis["id"]
        )
        pending = pending_job["transcript_attempts"][0]
        assert pending["available"] is True
        assert pending["communication_available"] is False
        assert pending["communication_state"] == "finalizing"
        assert "communication_status_url" not in pending
        base = (
            f"/api/experiments/{experiment['id']}/codex-runs/{analysis['id']}/"
            "attempts/1"
        )
        assert client.get(
            f"{base}/{STATUS_NAME}",
            headers={"Authorization": "Bearer secret"},
        ).status_code == 404
        assert client.get(
            f"{base}/{ROBOT_COMMUNICATION_MANIFEST}",
            headers={"Authorization": "Bearer secret"},
        ).status_code == 404

        store.register_codex_communication_attempt(
            analysis["id"], 1, communication_digest
        )
        item = client.get(
            f"/api/experiments/{experiment['id']}", headers=viewer
        ).json()
        job = next(job for job in item["codex_jobs"] if job["id"] == analysis["id"])
        attempt = job["transcript_attempts"][0]
        assert attempt["available"] is True
        assert attempt["state"] == "finalized"
        assert attempt["communication_status_url"].endswith(
            "/robot-communication.json"
        )
        assert attempt["communication_url"].endswith(
            "/robot-communication.jsonl"
        )
        assert attempt["communication_available"] is True
        assert attempt["communication_state"] == "finalized"
        assert attempt["communication_complete"] is True
        assert attempt["communication_capture_state"] == "terminal_complete"
        assert attempt["communication_status_access"] == "operator_or_automation"
        assert attempt["communication_manifest_sha256"] == hashlib.sha256(
            (attempt_dir / ROBOT_COMMUNICATION_MANIFEST).read_bytes()
        ).hexdigest()
        assert client.get(attempt["transcript_url"]).status_code == 401
        transcript = client.get(attempt["transcript_url"], headers=viewer)
        assert transcript.status_code == 200
        assert "The bounded test passed." in transcript.text
        assert transcript.headers["cache-control"] == "private, no-store"
        page = client.get(f"/experiments/{experiment['id']}", headers=viewer)
        assert page.status_code == 200
        assert attempt["transcript_url"] in page.text
        assert attempt["events_url"] in page.text
        assert attempt["communication_status_url"] in page.text
        assert attempt["communication_url"] in page.text
        communication_status = client.get(
            attempt["communication_status_url"], headers=viewer
        )
        assert communication_status.status_code == 403
        communication_status = client.get(
            attempt["communication_status_url"],
            headers={"Authorization": "Bearer secret"},
        )
        assert communication_status.status_code == 200
        assert communication_status.json()["complete"] is True
        assert client.get(
            attempt["communication_url"], headers=viewer
        ).status_code == 403
        communication = client.get(
            attempt["communication_url"],
            headers={"Authorization": "Bearer secret"},
        )
        assert communication.status_code == 200
        communication_rows = [
            json.loads(line) for line in communication.text.splitlines()
        ]
        assert [row["record_type"] for row in communication_rows] == [
            "marker", "serial_tx", "marker",
        ]
        restricted_arguments = {
            "experiment_id": experiment["id"],
            "job_id": analysis["id"],
            "attempt": 1,
        }
        for request_id, filename in enumerate(
            ("events.jsonl", STATUS_NAME, TRANSCRIPT_NAME), start=20
        ):
            denied = client.post("/mcp", headers=viewer, json={
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {
                    "name": "read_codex_run_file",
                    "arguments": {**restricted_arguments, "filename": filename},
                },
            }).json()["result"]
            assert denied["isError"] is True
            assert "Operator role required" in denied["content"][0]["text"]

        valid_arguments = {
            **restricted_arguments,
            "filename": "transcript.md",
        }
        malformed_arguments = [
            [],
            {**valid_arguments, "attempt": True},
            {**valid_arguments, "attempt": 1.5},
            {key: value for key, value in valid_arguments.items()
             if key != "attempt"},
            {**valid_arguments, "unexpected": "value"},
            {**valid_arguments, "max_bytes": True},
            {**valid_arguments, "max_bytes": 4095},
            {**valid_arguments, "max_bytes": 1_048_577},
        ]
        for request_id, arguments in enumerate(malformed_arguments, start=30):
            rejected = client.post(
                "/mcp",
                headers={"Authorization": "Bearer secret"},
                json={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "tools/call",
                    "params": {
                        "name": "read_codex_run_file",
                        "arguments": arguments,
                    },
                },
            ).json()["result"]
            assert rejected["isError"] is True
            assert "structuredContent" not in rejected

        mcp_status = client.post("/mcp", headers={
            "Authorization": "Bearer secret",
        }, json={
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "read_codex_run_file", "arguments": {
                "experiment_id": experiment["id"],
                "job_id": analysis["id"],
                "attempt": 1,
                "filename": "robot-communication.json",
            }},
        }).json()["result"]["structuredContent"]
        assert json.loads(mcp_status["data"])["complete"] is True
        mcp_raw = client.post(
            "/mcp",
            headers={"Authorization": "Bearer secret"},
            json={
                "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {"name": "read_codex_run_file", "arguments": {
                    "experiment_id": experiment["id"],
                    "job_id": analysis["id"],
                    "attempt": 1,
                    "filename": "robot-communication.jsonl",
                }},
            },
        ).json()["result"]["structuredContent"]
        assert [
            json.loads(line)["record_type"]
            for line in mcp_raw["data"].splitlines()
        ] == ["marker", "serial_tx", "marker"]
        machine = client.get(attempt["events_url"], headers=viewer)
        assert machine.status_code == 403
        machine = client.get(
            attempt["events_url"],
            headers={"Authorization": "Bearer secret"},
        )
        assert machine.status_code == 200
        assert len(machine.text.splitlines()) == 4

        communication_manifest_path = attempt_dir / ROBOT_COMMUNICATION_MANIFEST
        sealed_communication_manifest = communication_manifest_path.read_bytes()
        changed_manifest = json.loads(sealed_communication_manifest)
        changed_manifest["generated_at"] = "changed"
        communication_manifest_path.chmod(0o600)
        communication_manifest_path.write_text(json.dumps(changed_manifest) + "\n")
        assert client.get(
            attempt["communication_status_url"],
            headers={"Authorization": "Bearer secret"},
        ).status_code == 409
        communication_changed = client.get(
            f"/api/experiments/{experiment['id']}", headers=viewer
        ).json()
        communication_changed_job = next(
            candidate
            for candidate in communication_changed["codex_jobs"]
            if candidate["id"] == analysis["id"]
        )
        communication_changed_attempt = communication_changed_job[
            "transcript_attempts"
        ][0]
        assert communication_changed_attempt["available"] is True
        assert communication_changed_attempt["state"] == "finalized"
        assert communication_changed_attempt["communication_state"] == (
            "integrity_error"
        )
        communication_manifest_path.write_bytes(sealed_communication_manifest)
        communication_manifest_path.chmod(0o400)

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
