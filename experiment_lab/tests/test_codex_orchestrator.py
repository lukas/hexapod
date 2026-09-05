import hashlib
import json
import os
import plistlib
from datetime import datetime, timedelta, timezone
import signal
import subprocess
import sys
import threading
import time
import uuid

from fastapi.testclient import TestClient
import pytest

from hexapod_lab import deadline_exec
import hexapod_lab.codex_orchestrator as codex_module
from hexapod_lab.codex_orchestrator import (
    CodexCleanupError,
    CodexOrchestrator,
    CodexRunError,
    _codex_no_tool_arguments,
    _codex_runner_identity,
    _redact_for_model,
    _redact_text,
    _safe_environment,
    _terminate_deadline_wrapper,
)
from hexapod_lab.config import Settings
from hexapod_lab.db import Store
from hexapod_lab.main import create_app
from hexapod_lab.runner import ExperimentRunner


def test_codex_runner_identity_captures_hash_version_and_app_bundle(
    tmp_path, monkeypatch
):
    app = tmp_path / "ChatGPT.app"
    runner = app / "Contents" / "Resources" / "codex"
    runner.parent.mkdir(parents=True)
    runner.write_bytes(b"exact runner bytes")
    info_path = app / "Contents" / "Info.plist"
    with info_path.open("wb") as target:
        plistlib.dump(
            {
                "CFBundleShortVersionString": "26.901.1",
                "CFBundleVersion": "7001",
            },
            target,
        )

    class VersionResult:
        returncode = 0
        stdout = "codex-cli 0.153.0\n"
        stderr = ""

    monkeypatch.setattr(
        codex_module.subprocess, "run", lambda *_a, **_k: VersionResult()
    )

    identity = _codex_runner_identity(runner)

    assert identity["runner_path"] == str(runner)
    assert identity["runner_resolved_path"] == str(runner.resolve())
    assert identity["runner_sha256"] == hashlib.sha256(
        b"exact runner bytes"
    ).hexdigest()
    assert identity["runner_bytes"] == len(b"exact runner bytes")
    assert identity["runner_version"] == "codex-cli 0.153.0"
    assert identity["bundle_version"] == {
        "path": str(app),
        "short_version": "26.901.1",
        "build_version": "7001",
    }
    assert identity["capture_source"] == "prelaunch_local_binary"


def test_codex_runner_identity_retains_explicit_capture_failure(tmp_path):
    identity = _codex_runner_identity(tmp_path / "missing-codex")

    assert identity["runner_sha256"] is None
    assert identity["runner_version"] is None
    assert identity["capture_errors"] == ["binary capture: FileNotFoundError"]


def configured(tmp_path, **overrides):
    values = dict(
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
        codex_evidence_settle_seconds=0,
        codex_poll_seconds=0.01,
    )
    values.update(overrides)
    return Settings(**values)


def test_missing_offline_checkout_never_restores_shared_engineering_lane(
    tmp_path, monkeypatch
):
    settings = configured(
        tmp_path,
        codex_engineering=True,
        codex_engineering_workdir=tmp_path,
        codex_offline_engineering_workdir=None,
    )
    orchestrator = CodexOrchestrator(
        Store(tmp_path / "lab.sqlite3"), settings, invoker=lambda *_: {}
    )
    started = []

    class FakeThread:
        def __init__(self, *, target, args=(), name, daemon):
            self.name = name

        def is_alive(self):
            return False

        def start(self):
            started.append(self.name)

    monkeypatch.setattr(codex_module, "build_project_context", lambda *_: {})
    monkeypatch.setattr(codex_module.threading, "Thread", FakeThread)

    orchestrator.start()

    assert "codex-engineering-hardware" in started
    assert "codex-engineering" not in started
    assert "codex-engineering-offline" not in started


def test_hardware_worker_never_dispatches_offline_rl_outbox(
    tmp_path, monkeypatch
):
    orchestrator = CodexOrchestrator(
        Store(tmp_path / "lab.sqlite3"),
        configured(tmp_path),
        invoker=lambda *_: {},
    )
    dispatches = []
    monkeypatch.setattr(orchestrator.engineering, "claim", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        orchestrator.engineering,
        "dispatch_one",
        lambda *_args, **_kwargs: dispatches.append(True) or True,
    )

    assert orchestrator.process_one("engineering-hardware") is False
    assert dispatches == []
    assert orchestrator.process_one("engineering-offline") is True
    assert dispatches == [True]


def test_offline_cleanup_failure_quarantines_only_offline_worker(
    tmp_path, monkeypatch
):
    orchestrator = CodexOrchestrator(
        Store(tmp_path / "lab.sqlite3"),
        configured(tmp_path),
        invoker=lambda *_: {},
    )
    offline_job = {
        "id": "offline-job",
        "attempts": 1,
        "max_attempts": 2,
        "source_context": {"trigger_kind": "experiment_analysis"},
    }
    monkeypatch.setattr(
        orchestrator.engineering,
        "claim",
        lambda *_args, **kwargs: (
            offline_job
            if kwargs.get("lane") == codex_module.ENGINEERING_LANE_OFFLINE
            else None
        ),
    )
    monkeypatch.setattr(
        orchestrator,
        "_process_engineering",
        lambda _job: (_ for _ in ()).throw(
            CodexCleanupError("offline child could not be reaped")
        ),
    )

    assert orchestrator.process_one("engineering-offline") is True
    assert orchestrator.offline_stop_event.is_set()
    assert not orchestrator.stop_event.is_set()
    assert not orchestrator.fatal_cleanup_event.is_set()
    assert orchestrator.process_one("engineering-hardware") is False


def complete_with_evidence(store, settings, *, name="completed", parameters=None):
    item = store.create(
        {
            "name": name,
            "duration_seconds": 1,
            "parameters": parameters or {},
        },
        "test",
    )
    store.finish(item["id"], "succeeded")
    run_dir = settings.data_dir / "experiments" / item["id"]
    run_dir.mkdir(parents=True)
    (run_dir / "experiment.json").write_text(json.dumps(item) + "\n")
    (run_dir / "summary.md").write_text("# Result\n\nMeasured result.\n")
    digest = ExperimentRunner._write_manifest(run_dir)
    store.seal_evidence(item["id"], digest)
    return store.get(item["id"])


def analysis_result(experiment, *, followups=None):
    return {
        "schema_version": 1,
        "experiment_id": experiment["id"],
        "evidence_manifest_sha256": experiment["evidence_manifest_sha256"],
        "verdict": "pass",
        "safety_disposition": "clear",
        "what_we_learned": "The recorded measurement completed and supports a bounded follow-up.",
        "sources": ["summary.md"],
        "findings": ["The summary contains a measured result."],
        "recommended_experiments": followups or [],
    }


def test_codex_output_schemas_are_strict_for_every_object():
    def assert_strict(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False
            for value in node.values():
                assert_strict(value)
        elif isinstance(node, list):
            for value in node:
                assert_strict(value)

    assert_strict(codex_module.ANALYSIS_SCHEMA)
    assert_strict(codex_module.ADVANCE_SCHEMA)


def test_followup_accepts_schema_encoded_parameters_json(tmp_path):
    orchestrator = CodexOrchestrator(
        Store(tmp_path / "lab.sqlite3"), configured(tmp_path), invoker=lambda *_: {}
    )
    normalized = orchestrator._normalize_followup({
        "recommendation_key": "sim-check",
        "name": "Simulation check",
        "description": "Bounded synthetic follow-up",
        "duration_seconds": 1,
        "parameters": json.dumps({"simulation_only": True, "load_kg": 0.1}),
        "execution_mode": "builtin",
        "rationale": "Separate trial noise from a repeatable effect.",
        "dependencies": [],
        "stop_conditions": [],
    })
    assert normalized["spec"]["parameters"]["simulation_only"] is True
    assert normalized["spec"]["execution_mode"] == "external_guarded"
    assert normalized["spec"]["parameters"]["robot_motion"] is False


def test_analysis_accepts_only_its_own_generated_video_contact_sheet(tmp_path):
    settings = configured(tmp_path)
    store = Store(tmp_path / "lab.sqlite3")
    experiment = complete_with_evidence(store, settings)
    job = store.claim_codex_job("analysis", "reviewer", lease_seconds=60)
    assert job is not None
    manifest = json.loads(
        (tmp_path / "experiments" / experiment["id"] / "manifest.json").read_text()
    )
    result = analysis_result(experiment)
    result["sources"] = ["video-contact-sheet.jpg"]
    attempt_dir = tmp_path / "codex-runs" / job["id"] / "attempt-1"
    attempt_dir.mkdir(parents=True)
    (attempt_dir / "video-contact-sheet.jpg").write_bytes(b"derived")
    orchestrator = CodexOrchestrator(store, settings, invoker=lambda *_: {})

    normalized = orchestrator._validate_analysis(
        result,
        job,
        experiment,
        tmp_path / "experiments" / experiment["id"],
        manifest,
    )
    assert normalized["sources"] == ["video-contact-sheet.jpg"]

    (attempt_dir / "video-contact-sheet.jpg").unlink()
    with pytest.raises(CodexRunError, match="unknown artifact"):
        orchestrator._validate_analysis(
            result,
            job,
            experiment,
            tmp_path / "experiments" / experiment["id"],
            manifest,
        )


def test_analysis_evidence_bundle_fairly_includes_late_text_artifacts(tmp_path):
    artifacts = [
        ("a_air_summary.json", b"a" * (200 * 1024)),
        ("b_air_telemetry.csv", b"b" * (200 * 1024)),
        ("c_air_vision.jsonl", b"c" * (200 * 1024)),
        ("z_ground_summary.md", b"decisive planted result\n"),
    ]
    manifest = {"artifacts": []}
    for name, payload in artifacts:
        (tmp_path / name).write_bytes(payload)
        manifest["artifacts"].append({
            "name": name,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        })

    bundle = CodexOrchestrator._analysis_evidence_bundle(tmp_path, manifest)
    by_name = {record["name"]: record for record in bundle}

    assert by_name["z_ground_summary.md"]["excerpt"] == "full"
    assert by_name["z_ground_summary.md"]["content"] == (
        "decisive planted result\n"
    )
    assert all(
        by_name[name]["excerpt"] == "head_tail"
        and by_name[name]["content"].startswith(payload[:64].decode())
        and by_name[name]["content"].endswith(payload[-64:].decode())
        for name, payload in artifacts[:-1]
    )


def process_is_running(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    inspected = subprocess.run(
        ["/bin/ps", "-p", str(pid), "-o", "stat="],
        capture_output=True,
        text=True,
        check=False,
    )
    state = inspected.stdout.strip()
    return inspected.returncode == 0 and bool(state) and not state.startswith("Z")


def wait_for_path(path, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            return
        time.sleep(0.02)
    raise AssertionError(f"Timed out waiting for {path}")


def wait_until_stopped(pid, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not process_is_running(pid):
            return
        time.sleep(0.02)
    raise AssertionError(f"Process {pid} remained alive")


def test_deadline_exec_kills_its_spawned_child_process_group(tmp_path):
    pids_path = tmp_path / "child-pids.txt"
    marker = uuid.uuid4().hex
    child_script = (
        "import os,pathlib,subprocess,sys,time;"
        "desc=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']);"
        "pathlib.Path(sys.argv[1]).write_text(f'{os.getpid()} {desc.pid}');"
        "time.sleep(60)"
    )
    command = [
        sys.executable,
        "-m",
        "hexapod_lab.deadline_exec",
        "--marker",
        marker,
        "--timeout-seconds",
        "0.25",
        "--",
        sys.executable,
        "-c",
        child_script,
        str(pids_path),
    ]
    wrapper = subprocess.Popen(command, start_new_session=True)
    child_pids = []
    try:
        wait_for_path(pids_path)
        child_pids = [int(value) for value in pids_path.read_text().split()]
        assert len(child_pids) == 2
        assert all(process_is_running(pid) for pid in child_pids)
        assert wrapper.wait(timeout=5) == 124
        for pid in child_pids:
            wait_until_stopped(pid)
    finally:
        if wrapper.poll() is None:
            try:
                os.killpg(wrapper.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            wrapper.wait(timeout=5)
        for pid in child_pids:
            if process_is_running(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


def test_deadline_stop_handler_closes_launch_gate_and_signals_child(monkeypatch):
    go_read, go_write = os.pipe()
    signalled = []
    monkeypatch.setattr(deadline_exec, "_stop_signal", None)
    monkeypatch.setattr(deadline_exec, "_launch_gate_fd", go_write)
    monkeypatch.setattr(deadline_exec, "_launch_child_pid", 424242)
    monkeypatch.setattr(
        deadline_exec.os,
        "kill",
        lambda pid, signum: signalled.append((pid, signum)),
    )
    try:
        deadline_exec._request_stop(signal.SIGTERM, None)
        assert os.read(go_read, 1) == b""
        assert deadline_exec._stop_signal == signal.SIGTERM
        assert deadline_exec._launch_gate_fd is None
        assert signalled == [(424242, signal.SIGTERM)]
    finally:
        os.close(go_read)


def test_live_supervisor_sweeps_group_when_deadline_wrapper_was_sigkilled(
    tmp_path,
):
    marker = uuid.uuid4().hex
    child_path = tmp_path / "orphaned-codex-child.pid"
    child_script = (
        "import os,pathlib,sys,time;"
        "pathlib.Path(sys.argv[1]).write_text(str(os.getpid()));"
        "time.sleep(60)"
    )
    wrapper = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "hexapod_lab.deadline_exec",
            "--marker",
            marker,
            "--timeout-seconds",
            "60",
            "--",
            sys.executable,
            "-c",
            child_script,
            str(child_path),
        ],
        start_new_session=True,
    )
    child_pid = None
    try:
        wait_for_path(child_path)
        child_pid = int(child_path.read_text())
        os.kill(wrapper.pid, signal.SIGKILL)
        wrapper.wait(timeout=5)
        assert process_is_running(child_pid)

        assert _terminate_deadline_wrapper(wrapper, grace_seconds=0.1) is True
        wait_until_stopped(child_pid)
    finally:
        if wrapper.poll() is None:
            try:
                os.killpg(wrapper.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            wrapper.wait(timeout=5)
        if child_pid and process_is_running(child_pid):
            try:
                os.kill(child_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_startup_recovers_marker_backed_advisory_as_retry_without_pause(tmp_path):
    settings = configured(tmp_path)
    store = Store(tmp_path / "lab.sqlite3")
    target = store.create(
        {
            "name": "orphaned physical plan",
            "duration_seconds": 1,
            "execution_mode": "external_guarded",
        },
        "test",
    )
    claimed = store.claim_codex_job("advance", "old-worker", lease_seconds=60)
    assert claimed and claimed["experiment_id"] == target["id"]
    assert store.acquire_hardware_lane(
        claimed["id"],
        target["id"],
        "old-worker",
        lease_seconds=60,
        lease_token=claimed["lease_token"],
    )

    marker = uuid.uuid4().hex
    ready_path = tmp_path / "orphan-child-ready.txt"
    child_script = (
        "import os,pathlib,sys,time;"
        "pathlib.Path(sys.argv[1]).write_text(str(os.getpid()));"
        "time.sleep(60)"
    )
    wrapper = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "hexapod_lab.deadline_exec",
            "--marker",
            marker,
            "--timeout-seconds",
            "60",
            "--",
            sys.executable,
            "-c",
            child_script,
            str(ready_path),
        ],
        start_new_session=True,
    )
    reaper = None
    orchestrator = CodexOrchestrator(store, settings, invoker=lambda *_: {})
    try:
        wait_for_path(ready_path)
        state_path = (
            settings.data_dir
            / "codex-runs"
            / claimed["id"]
            / "attempt-1"
            / "process.json"
        )
        state_path.parent.mkdir(parents=True)
        state_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "job_id": claimed["id"],
                    "role": "advance",
                    "attempt": 1,
                    "pid": wrapper.pid,
                    "marker": marker,
                    "started_at": "2026-09-05T00:00:00+00:00",
                }
            )
        )
        # Reap concurrently so startup's PID liveness check can observe the
        # wrapper disappear instead of waiting on a zombie owned by pytest.
        reaper = threading.Thread(target=wrapper.wait, daemon=True)
        reaper.start()

        assert orchestrator._recover_orphaned_processes() == 1
        assert store.recover_expired_codex_jobs() == 1
        recovered_state = json.loads(state_path.read_text())
        assert recovered_state["recovered_process_match"] is True
        assert recovered_state["recovered_at"]
        wait_until_stopped(wrapper.pid)
        wait_until_stopped(int(ready_path.read_text()))
        recovered_job = store.get_codex_job(claimed["id"])
        assert recovered_job["status"] == "retry"
        assert "Supervisor restarted" in recovered_job["error"]
        control = store.codex_queue_control()
        assert control["paused"] is False
        assert store.automation_assignment_active(target["id"]) is False
    finally:
        orchestrator.stop()
        if wrapper.poll() is None:
            try:
                os.killpg(wrapper.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                wrapper.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(wrapper.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                wrapper.wait(timeout=3)
        child_pid = int(ready_path.read_text()) if ready_path.is_file() else None
        if child_pid and process_is_running(child_pid):
            try:
                os.kill(child_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if reaper is not None:
            reaper.join(timeout=3)


def test_startup_recovers_adopted_codex_group_after_wrapper_sigkill(tmp_path):
    settings = configured(tmp_path)
    store = Store(tmp_path / "lab.sqlite3")
    target = store.create(
        {
            "name": "adopted Codex process",
            "duration_seconds": 1,
            "execution_mode": "external_guarded",
        },
        "test",
    )
    claimed = store.claim_codex_job("advance", "old-worker", lease_seconds=60)
    assert claimed and claimed["experiment_id"] == target["id"]
    marker = uuid.uuid4().hex
    ready_path = tmp_path / "adopted-child.pid"
    child_script = (
        "import os,pathlib,sys,time;"
        "pathlib.Path(sys.argv[1]).write_text(str(os.getpid()));"
        "time.sleep(60)"
    )
    wrapper = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "hexapod_lab.deadline_exec",
            "--marker",
            marker,
            "--timeout-seconds",
            "60",
            "--",
            sys.executable,
            "-c",
            child_script,
            str(ready_path),
            claimed["id"],
        ],
        start_new_session=True,
    )
    child_pid = None
    try:
        wait_for_path(ready_path)
        child_pid = int(ready_path.read_text())
        state_path = (
            settings.data_dir
            / "codex-runs"
            / claimed["id"]
            / "attempt-1"
            / "process.json"
        )
        state_path.parent.mkdir(parents=True)
        state_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "job_id": claimed["id"],
                    "role": "advance",
                    "attempt": 1,
                    "pid": wrapper.pid,
                    "pgid": wrapper.pid,
                    "marker": marker,
                    "started_unix": time.time(),
                    "deadline_seconds": 60,
                }
            )
        )
        os.kill(wrapper.pid, signal.SIGKILL)
        wrapper.wait(timeout=5)
        assert process_is_running(child_pid)

        orchestrator = CodexOrchestrator(store, settings, invoker=lambda *_: {})
        assert orchestrator._recover_orphaned_processes() == 1
        assert store.recover_expired_codex_jobs() == 1
        wait_until_stopped(child_pid)
        recovered_state = json.loads(state_path.read_text())
        assert recovered_state["recovered_process_match"] is True
        assert store.get_codex_job(claimed["id"])["status"] == "retry"
    finally:
        if wrapper.poll() is None:
            try:
                os.killpg(wrapper.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            wrapper.wait(timeout=5)
        if child_pid and process_is_running(child_pid):
            try:
                os.kill(child_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_terminal_transition_writes_two_jobs_and_seal_releases_them(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    item = store.create({"name": "x", "duration_seconds": 1}, "test")

    store.finish(item["id"], "succeeded")
    waiting = store.codex_jobs_for_experiment(item["id"])
    assert {job["kind"] for job in waiting} == {"analysis", "advance"}
    assert {job["status"] for job in waiting} == {"awaiting_evidence"}
    analysis = next(job for job in waiting if job["kind"] == "analysis")
    advance = next(job for job in waiting if job["kind"] == "advance")
    assert advance["depends_on_job_id"] == analysis["id"]

    digest = "a" * 64
    store.seal_evidence(item["id"], digest)
    released = store.codex_jobs_for_experiment(item["id"])
    assert {job["status"] for job in released} == {"queued"}
    assert {job["evidence_manifest_sha256"] for job in released} == {digest}

    store.finish(item["id"], "succeeded")
    store.seal_evidence(item["id"], digest)
    assert len(store.codex_jobs_for_experiment(item["id"])) == 2


def test_unproven_codex_cleanup_keeps_running_lease_and_stops_supervisor(
    tmp_path, monkeypatch
):
    settings = configured(tmp_path)
    store = Store(tmp_path / "lab.sqlite3")
    complete_with_evidence(store, settings)
    orchestrator = CodexOrchestrator(store, settings)

    class UnprovenProcess:
        pid = 424242

        def communicate(self, _payload, timeout):
            raise OSError("active invocation failure")

        def poll(self):
            return None

    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: UnprovenProcess())
    monkeypatch.setattr(
        "hexapod_lab.codex_orchestrator._terminate_deadline_wrapper",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        orchestrator,
        "_process_analysis",
        lambda job: orchestrator._invoke(
            "analysis", job, "bounded prompt", {"type": "object"}
        ),
    )

    assert orchestrator.process_one("analysis") is True

    jobs = [job for job in store.list_codex_jobs() if job["kind"] == "analysis"]
    assert len(jobs) == 1
    assert jobs[0]["status"] == "running"
    assert jobs[0]["lease_owner"] == orchestrator.owner
    assert jobs[0]["lease_expires_at"]
    assert orchestrator.stop_event.is_set()
    assert orchestrator.service_exit_code() == 75


def test_unproven_cleanup_overrides_final_process_marker_write_failure(
    tmp_path, monkeypatch
):
    settings = configured(tmp_path)
    store = Store(tmp_path / "lab.sqlite3")
    complete_with_evidence(store, settings)
    orchestrator = CodexOrchestrator(store, settings)

    class UnprovenProcess:
        pid = 424243
        returncode = None

        def communicate(self, _payload, timeout):
            return (None, None)

        def poll(self):
            return None

    real_atomic_json = codex_module._atomic_json

    def fail_final_marker(path, payload):
        if path.name == "process.json" and "returncode" in payload:
            raise OSError("final marker persistence failed")
        return real_atomic_json(path, payload)

    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: UnprovenProcess())
    monkeypatch.setattr(codex_module, "_atomic_json", fail_final_marker)
    monkeypatch.setattr(codex_module, "_terminate_deadline_wrapper", lambda *_a, **_k: False)
    monkeypatch.setattr(
        orchestrator,
        "_process_analysis",
        lambda job: orchestrator._invoke(
            "analysis", job, "bounded prompt", {"type": "object"}
        ),
    )

    assert orchestrator.process_one("analysis") is True
    job = next(job for job in store.list_codex_jobs() if job["kind"] == "analysis")
    assert job["status"] == "running"
    assert job["lease_owner"] == orchestrator.owner
    assert orchestrator.stop_event.is_set()
    assert orchestrator.service_exit_code() == 75


def test_cancelled_plan_gets_the_same_completion_outbox(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    item = store.create(
        {
            "name": "cancel me",
            "duration_seconds": 1,
            "execution_mode": "external_guarded",
        },
        "test",
    )
    assert store.cancel(item["id"])["status"] == "cancelled"
    assert {job["kind"] for job in store.codex_jobs_for_experiment(item["id"])} == {
        "analysis",
        "advance",
    }


def test_analysis_records_learning_and_queues_bounded_deduplicated_followup(tmp_path):
    settings = configured(tmp_path)
    store = Store(tmp_path / "lab.sqlite3")
    source = complete_with_evidence(store, settings)
    recommendation = {
        "recommendation_key": "repeat-with-load",
        "name": "Repeat with bounded load",
        "description": "Measure whether the result changes under a small load.",
        "duration_seconds": 2,
        "parameters": {
            "load_kg": 0.1,
            "simulation_only": True,
            "robot_motion": False,
        },
        "execution_mode": "builtin",
        "rationale": "This separates load sensitivity from trial noise.",
        "dependencies": ["Use the same fixture."],
        "stop_conditions": ["unexpected force", "hot motor"],
    }

    def invoke(role, _job, _request):
        assert role == "analysis"
        return analysis_result(source, followups=[recommendation])

    orchestrator = CodexOrchestrator(store, settings, invoker=invoke)
    assert orchestrator.process_one("advance") is False
    assert orchestrator.process_one("analysis") is True

    analysis_job = next(
        job for job in store.codex_jobs_for_experiment(source["id"])
        if job["kind"] == "analysis"
    )
    assert analysis_job["status"] == "succeeded"
    assert store.learnings(source["id"])["created_by"] == "codex-analysis"
    children = [item for item in store.list() if item["id"] != source["id"]]
    assert len(children) == 1
    child = children[0]
    assert child["execution_mode"] == "external_guarded"
    assert child["status"] == "waiting_for_operator"
    assert child["parameters"]["_automation"]["parent_experiment_id"] == source["id"]

    receipts = store.apply_analysis_followups(
        analysis_job["id"],
        source["id"],
        analysis_job["result"]["recommended_experiments"],
        max_depth=4,
        max_per_root=20,
    )
    assert receipts["accepted"][0]["child_experiment_id"] == child["id"]
    assert len([item for item in store.list() if item["id"] != source["id"]]) == 1
    assert len([job for job in store.list_codex_jobs() if job["kind"] == "advance"]) == 1


@pytest.mark.parametrize("disposition", ["needs_inspection", "stop"])
@pytest.mark.parametrize(
    "driver, requested_mode, simulation_only, accepted",
    [
        ("simulated", "builtin", True, True),
        ("simulated", "builtin", 1, False),
        ("simulated", "builtin", "true", False),
        ("simulated", "builtin", False, False),
        ("simulated", "external_guarded", True, True),
        ("command", "builtin", True, True),
    ],
)
def test_uncleared_analysis_routes_explicit_offline_work_to_engineering(
    tmp_path, disposition, driver, requested_mode, simulation_only, accepted
):
    settings = configured(tmp_path, driver=driver)
    store = Store(tmp_path / "lab.sqlite3")
    source = complete_with_evidence(store, settings)
    recommendation = {
        "recommendation_key": "bounded-check",
        "name": "Bounded follow-up",
        "description": "Separate a recorded anomaly from a repeatable effect.",
        "duration_seconds": 1,
        "parameters": json.dumps({"simulation_only": simulation_only}),
        "execution_mode": requested_mode,
        "rationale": "Reduce uncertainty without assuming current robot health.",
        "dependencies": [],
        "stop_conditions": ["unexpected force"],
    }

    def invoke(role, _job, _request):
        assert role == "analysis"
        result = analysis_result(source, followups=[recommendation])
        result["safety_disposition"] = disposition
        return result

    orchestrator = CodexOrchestrator(store, settings, invoker=invoke)
    assert orchestrator.process_one("analysis") is True
    job = next(job for job in store.codex_jobs_for_experiment(source["id"])
               if job["kind"] == "analysis")
    assert job["status"] == "succeeded"
    assert store.codex_queue_control()["paused"] is (disposition == "stop")
    receipts = job["result"]["followup_receipts"]
    children = [item for item in store.list() if item["id"] != source["id"]]
    if accepted:
        assert len(receipts["accepted"]) == len(children) == 1
        assert receipts["rejected"] == []
        child = children[0]
        assert child["execution_mode"] == "external_guarded"
        assert child["parameters"]["simulation_only"] is True
        assert child["parameters"]["robot_motion"] is False
        assert child["status"] == "waiting_for_operator"
        assert store.claim_next() is None
        assert store.next_external_experiment()["id"] == child["id"]
    else:
        assert receipts["accepted"] == children == []
        assert len(receipts["rejected"]) == 1
        assert receipts["rejected"][0]["disposition_reason"] == (
            "source analysis did not clear safety: " + disposition
        )


@pytest.mark.parametrize(
    "parameters, disposition, paused",
    [
        (
            {"simulation_only": True, "robot_motion": False},
            "needs_inspection",
            False,
        ),
        (
            {"simulation_only": False, "robot_motion": True},
            "needs_inspection",
            False,
        ),
        (
            {"simulation_only": True, "robot_motion": False},
            "stop",
            False,
        ),
        (
            {"simulation_only": False, "robot_motion": True},
            "stop",
            True,
        ),
        (
            {"simulation_only": True, "robot_motion": True},
            "stop",
            True,
        ),
    ],
)
def test_analysis_pause_policy_only_stops_queue_for_stop(
    tmp_path, parameters, disposition, paused
):
    settings = configured(tmp_path)
    store = Store(tmp_path / "lab.sqlite3")
    source = complete_with_evidence(store, settings, parameters=parameters)

    def invoke(role, _job, _request):
        assert role == "analysis"
        result = analysis_result(source)
        result["safety_disposition"] = disposition
        return result

    orchestrator = CodexOrchestrator(store, settings, invoker=invoke)
    assert orchestrator.process_one("analysis") is True
    assert store.codex_queue_control()["paused"] is paused


def test_clear_analysis_saves_nonready_external_plan_but_rejects_forbidden_plan(
    tmp_path,
):
    settings = configured(tmp_path, codex_workdir=tmp_path / "missing-workspace")
    store = Store(tmp_path / "lab.sqlite3")
    source = complete_with_evidence(store, settings)
    parameters = {
        "current_compatibility": {"ready": False, "reason": "review pending"},
        "leg": 5,
        "comparison": "Repeat the same bounded measurement for leg 5.",
        "excluded": ["learned rise"],
    }

    def recommendation(key, extra_parameters=None):
        return {
            "recommendation_key": key,
            "name": f"External follow-up {key}",
            "description": "A bounded external guarded measurement.",
            "duration_seconds": 3,
            "parameters": {**parameters, **(extra_parameters or {})},
            "execution_mode": "external_guarded",
            "rationale": "This would reduce remaining measurement uncertainty.",
            "dependencies": [],
            "stop_conditions": ["unexpected force"],
        }

    def invoke(role, _job, _request):
        assert role == "analysis"
        return analysis_result(
            source,
            followups=[
                recommendation("waiting-plan"),
                recommendation(
                    "forbidden-plan",
                    {"excluded": {"command": ["robot", "--learned-rise"]}},
                ),
            ],
        )

    orchestrator = CodexOrchestrator(store, settings, invoker=invoke)
    assert orchestrator.process_one("analysis") is True

    analysis_job = next(
        job for job in store.codex_jobs_for_experiment(source["id"])
        if job["kind"] == "analysis"
    )
    receipts = analysis_job["result"]["followup_receipts"]
    assert len(receipts["accepted"]) == 1
    assert len(receipts["rejected"]) == 1
    child = store.get(receipts["accepted"][0]["child_experiment_id"])
    assert child["status"] == "waiting_for_operator"
    admission = child["parameters"]["_adaptive_admission"]
    assert admission["ready"] is False
    assert "compatibility" in admission["reason"]
    assert "deterministic executor" in admission["reason"]
    assert "forbidden" in receipts["rejected"][0]["disposition_reason"]


def test_adaptive_offline_work_executes_real_command_and_seals_output(tmp_path, monkeypatch):
    from test_engineering_lane import engineering_receipt

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    settings = configured(tmp_path, codex_engineering=True,
                          codex_engineering_workdir=workspace)
    store = Store(tmp_path / "lab.sqlite3")
    source = complete_with_evidence(store, settings)
    proposal = {
        "recommendation_key": "offline-replay", "name": "Offline replay",
        "description": "Run the fixture command and retain its actual output.",
        "duration_seconds": 1, "parameters": {"simulation_only": True},
        "execution_mode": "builtin", "rationale": "Reproduce a recorded fault.",
        "dependencies": [], "stop_conditions": [],
    }
    monkeypatch.setattr(codex_module, "build_project_context", lambda *_: {"sha256": "a" * 64})
    monkeypatch.setattr(codex_module, "workspace_snapshot", lambda *_: {"head": "b" * 40})
    calls = []

    def invoke(role, job, request):
        calls.append(role)
        if role == "analysis":
            result = analysis_result(source, followups=[proposal])
            result["safety_disposition"] = "needs_inspection"
            return result
        assert role == "engineering"
        assert 'simulation_only' in request["prompt"]
        assert 'Do not contact, move, or deploy to the robot' in request["prompt"]
        item = store.get(job["experiment_id"])
        directory = settings.data_dir / "experiments" / item["id"]
        directory.mkdir(parents=True)
        # A real command produces the retained output; the demo runner is never claimed.
        command = ["/bin/sh", "-c", "printf 'injected_delay_ms=50\\n' > replay.txt"]
        subprocess.run(command, cwd=directory, check=True)
        (directory / "experiment.json").write_text(json.dumps(item))
        (directory / "summary.md").write_text("Offline fixture completed.")
        store.finish(item["id"], "succeeded")
        store.seal_evidence(item["id"], ExperimentRunner._write_manifest(directory))
        receipt = engineering_receipt(job, "a" * 64)
        receipt["commands_run"] = [{"command": "fixture replay", "purpose": "Offline regression",
                                     "outcome": "passed", "summary": "Wrote replay.txt"}]
        receipt["artifacts"] = ["replay.txt"]
        return receipt

    orchestrator = CodexOrchestrator(store, settings, invoker=invoke)
    assert orchestrator.process_one("analysis")
    child = next(item for item in store.list() if item["id"] != source["id"])
    assert child["execution_mode"] == "external_guarded"
    assert store.claim_next() is None
    assert orchestrator.process_one("advance")
    assert orchestrator.process_one("engineering")
    finished = store.get(child["id"])
    assert finished["status"] == "succeeded"
    assert finished["evidence_sealed_at"]
    output = settings.data_dir / "experiments" / child["id"] / "replay.txt"
    assert output.read_text().strip() == "injected_delay_ms=50"
    assert calls == ["analysis", "engineering"]
    engineering = next(job for job in orchestrator.engineering.list_jobs()
                       if job["experiment_id"] == child["id"])
    assert engineering["result"]["commands_run"][0]["outcome"] == "passed"


def test_analysis_retry_reuses_checkpoint_instead_of_invoking_analyzer_twice(
    tmp_path, monkeypatch
):
    settings = configured(tmp_path)
    store = Store(tmp_path / "lab.sqlite3")
    source = complete_with_evidence(store, settings)
    invocations = []

    def invoke(role, _job, _request):
        assert role == "analysis"
        invocations.append(role)
        return analysis_result(source)

    original_record = store.record_learnings
    fail_after_side_effect = True

    def record_then_fail(*args, **kwargs):
        nonlocal fail_after_side_effect
        recorded = original_record(*args, **kwargs)
        if fail_after_side_effect:
            fail_after_side_effect = False
            raise RuntimeError("crash after durable learning write")
        return recorded

    monkeypatch.setattr(store, "record_learnings", record_then_fail)
    orchestrator = CodexOrchestrator(store, settings, invoker=invoke)
    assert orchestrator.process_one("analysis") is True
    analysis = next(
        job for job in store.codex_jobs_for_experiment(source["id"])
        if job["kind"] == "analysis"
    )
    assert analysis["status"] == "retry"
    assert analysis["result"] == analysis_result(source)
    assert invocations == ["analysis"]

    with store.connect() as con:
        con.execute(
            "UPDATE codex_jobs SET not_before=? WHERE id=?",
            ("1970-01-01T00:00:00+00:00", analysis["id"]),
        )
    assert orchestrator.process_one("analysis") is True
    finished = store.get_codex_job(analysis["id"])
    assert finished["status"] == "succeeded"
    assert invocations == ["analysis"]
    with store.connect() as con:
        learning_count = con.execute(
            "SELECT COUNT(*) FROM experiment_learnings WHERE experiment_id=?",
            (source["id"],),
        ).fetchone()[0]
    assert learning_count == 1


def test_empty_queue_advance_receipt_requires_read_only_semantics(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    job = store.enqueue_advance("empty-queue-check", "operator_resume")
    receipt = {
        "schema_version": 1,
        "trigger_job_id": job["id"],
        "selected_experiment_id": None,
        "action": "queue_empty",
        "summary": "No external guarded experiment is waiting.",
        "blocker": "",
        "safety_disposition": "clear",
        "motion_started": False,
        "retryable": False,
        "retry_after_seconds": 0,
    }
    normalized = CodexOrchestrator._validate_advance(receipt, job, None)
    assert normalized["action"] == "queue_empty"

    invalid_changes = (
        {"safety_disposition": "needs_inspection"},
        {"motion_started": True},
        {"retryable": True},
        {"retry_after_seconds": 1},
        {"action": "progressing"},
    )
    for change in invalid_changes:
        with pytest.raises(CodexRunError, match="empty-queue receipt"):
            CodexOrchestrator._validate_advance(
                {**receipt, **change}, job, None
            )


def test_analysis_followup_caps_lineage_depth(tmp_path):
    settings = configured(tmp_path)
    store = Store(tmp_path / "lab.sqlite3")
    source = complete_with_evidence(store, settings)
    job = next(
        job for job in store.codex_jobs_for_experiment(source["id"])
        if job["kind"] == "analysis"
    )
    proposal = {
        "recommendation_key": "too-deep",
        "rationale": "test",
        "spec": {
            "name": "too deep",
            "description": "",
            "duration_seconds": 1,
            "parameters": {"stop_conditions": ["tip"]},
            "execution_mode": "external_guarded",
        },
    }
    receipts = store.apply_analysis_followups(
        job["id"], source["id"], [proposal], max_depth=0, max_per_root=20
    )
    assert receipts["accepted"] == []
    assert "depth" in receipts["rejected"][0]["disposition_reason"]


def test_evidence_reconcile_waits_for_quiet_period_then_seals(tmp_path):
    slow = configured(tmp_path, codex_evidence_settle_seconds=3600)
    store = Store(tmp_path / "lab.sqlite3")
    item = store.create({"name": "external", "duration_seconds": 1}, "test")
    store.finish(item["id"], "succeeded")
    run_dir = tmp_path / "experiments" / item["id"]
    run_dir.mkdir(parents=True)
    (run_dir / "experiment.json").write_text(json.dumps(item) + "\n")
    (run_dir / "summary.md").write_text("fresh upload")
    assert CodexOrchestrator(store, slow, invoker=lambda *_: {}).reconcile_evidence() == 0
    assert store.get(item["id"])["evidence_sealed_at"] is None

    immediate = configured(tmp_path, codex_evidence_settle_seconds=0)
    assert CodexOrchestrator(store, immediate, invoker=lambda *_: {}).reconcile_evidence() == 1
    assert store.get(item["id"])["evidence_sealed_at"] is not None


def test_advance_hard_block_is_durable_and_releases_lane(tmp_path):
    settings = configured(tmp_path)
    store = Store(tmp_path / "lab.sqlite3")
    target = store.create(
        {
            "name": "physical plan",
            "duration_seconds": 1,
            "execution_mode": "external_guarded",
            "parameters": {"hard_blockers": ["stale IMU"]},
        },
        "test",
    )
    job = next(
        job for job in store.codex_jobs_for_experiment(target["id"])
        if job["kind"] == "advance"
    )

    def invoke(role, claimed, _request):
        assert role == "advance"
        return {
            "schema_version": 1,
            "trigger_job_id": claimed["id"],
            "selected_experiment_id": target["id"],
            "action": "blocked",
            "summary": "The learned-policy timing stream is stale.",
            "blocker": "Obtain three fresh advancing IMU samples before motion.",
            "safety_disposition": "needs_inspection",
            "motion_started": False,
            "retryable": False,
            "retry_after_seconds": 0,
        }

    orchestrator = CodexOrchestrator(store, settings, invoker=invoke)
    assert orchestrator.process_one("advance") is True
    assert store.get_codex_job(job["id"])["status"] == "blocked"
    with store.connect() as con:
        assert con.execute(
            "SELECT COUNT(*) FROM codex_hardware_lane"
        ).fetchone()[0] == 0

    resumed = store.resume_codex_queue(
        "The reported blocker was inspected", created_by="operator"
    )
    retry = store.claim_codex_job("advance", "other", lease_seconds=60)
    assert retry["id"] == resumed["advance_job_id"]
    assert store.acquire_hardware_lane(
        retry["id"],
        target["id"],
        "other",
        lease_seconds=60,
        lease_token=retry["lease_token"],
    )


def test_api_stages_external_artifacts_then_seals_and_exposes_jobs(tmp_path):
    app = create_app(configured(tmp_path))
    operator = {"Authorization": "Bearer secret"}
    with TestClient(app) as client:
        plan = {
            "name": "staged result",
            "description": "external",
            "duration_seconds": 1,
            "parameters": {"runner": "bounded"},
            "execution_mode": "external_guarded",
        }
        item = client.post("/api/experiments", headers=operator, json=plan).json()
        staged = client.put(
            f"/api/experiments/{item['id']}/artifacts/telemetry.csv",
            headers=operator,
            content=b"t,value\n0,1\n",
        )
        assert staged.status_code == 201
        result = {key: value for key, value in plan.items() if key != "execution_mode"}
        result["summary_markdown"] = "# Result\n\nMeasured.\n"
        completed = client.post(
            f"/api/experiments/{item['id']}/result", headers=operator, json=result
        )
        assert completed.status_code == 200
        completion_jobs = [
            job for job in completed.json()["codex_jobs"]
            if job["trigger_kind"] == "experiment_terminal"
        ]
        assert len(completion_jobs) == 2
        assert {job["status"] for job in completion_jobs} == {"awaiting_evidence"}

        sealed = client.post(
            f"/api/experiments/{item['id']}/evidence-seal", headers=operator
        )
        assert sealed.status_code == 200
        assert sealed.json()["evidence_sealed_at"]
        assert {job["status"] for job in sealed.json()["codex_jobs"]} == {"queued"}
        jobs = client.get("/api/codex-jobs", headers=operator)
        assert jobs.status_code == 200
        assert len(jobs.json()) == 3
        assert client.put(
            f"/api/experiments/{item['id']}/artifacts/late.txt",
            headers=operator,
            content=b"late",
        ).status_code == 409


def test_child_process_environment_is_token_free(monkeypatch):
    monkeypatch.setenv("HEXAPOD_LAB_TOKEN", "lab-secret")
    monkeypatch.setenv("HEXAPOD_ORCHESTRATOR_TOKEN", "must-not-leak")
    monkeypatch.setenv("UNRELATED_SECRET", "must-not-leak")
    environment = _safe_environment()
    assert "HEXAPOD_LAB_TOKEN" not in environment
    assert "HEXAPOD_ORCHESTRATOR_TOKEN" not in environment
    assert "UNRELATED_SECRET" not in environment


def test_codex_argv_explicitly_disables_network_and_local_tools():
    arguments = _codex_no_tool_arguments()
    overrides = {
        arguments[index + 1]
        for index, value in enumerate(arguments[:-1])
        if value == "-c"
    }
    disabled = {
        arguments[index + 1]
        for index, value in enumerate(arguments[:-1])
        if value == "--disable"
    }
    assert 'web_search="disabled"' in overrides
    assert "tools.web_search=false" in overrides
    assert {"shell_tool", "unified_exec", "browser_use", "computer_use"} <= disabled


def test_model_inputs_redact_structured_and_inline_credentials():
    private_key = (
        "-----BEGIN PRIVATE KEY-----\nvery-secret\n"
        "-----END PRIVATE KEY-----"
    )
    value = {
        "api_token": "top-secret-token",
        "accessToken": "camel-case-secret",
        "aws_secret_access_key": "aws-secret-value",
        "nested": {
            "url": "https://alice:hunter2@example.test/path",
            "log": "Authorization: Bearer abcdefghijklmnop\n" + private_key,
        },
    }

    redacted = _redact_for_model(value)
    serialized = json.dumps(redacted)
    assert "top-secret-token" not in serialized
    assert "camel-case-secret" not in serialized
    assert "aws-secret-value" not in serialized
    assert "hunter2" not in serialized
    assert "abcdefghijklmnop" not in serialized
    assert "very-secret" not in serialized
    assert serialized.count("REDACTED") >= 4
    assert "secret=do-not-send" not in _redact_text("secret=do-not-send")
    quoted = _redact_text(
        'TOKEN="env secret"\napi_key: \'yaml secret\'\n'
        'HEXAPOD_LAB_TOKEN=lab-token\nclient_secret: oauth-secret\n'
        'aws_secret_access_key=aws-value\n'
        '{"password": "json secret", "authorization": "Bearer auth secret", '
        '"accessToken": "json-access-token"}'
    )
    assert "env secret" not in quoted
    assert "yaml secret" not in quoted
    assert "json secret" not in quoted
    assert "auth secret" not in quoted
    assert "lab-token" not in quoted
    assert "oauth-secret" not in quoted
    assert "aws-value" not in quoted
    assert "json-access-token" not in quoted
    assert 'TOKEN="[REDACTED]"' in quoted
    assert '"password": "[REDACTED]"' in quoted
    assert _redact_text("monkey=value\npublic_key_id=visible").endswith(
        "public_key_id=visible"
    )


def test_analysis_snapshot_excludes_unsealed_files_and_is_removed(tmp_path):
    settings = configured(tmp_path)
    store = Store(tmp_path / "lab.sqlite3")
    second = store.create({"name": "snapshot", "duration_seconds": 1}, "test")
    store.finish(second["id"], "succeeded")
    second_dir = tmp_path / "experiments" / second["id"]
    second_dir.mkdir(parents=True)
    (second_dir / "experiment.json").write_text(json.dumps(second))
    (second_dir / "summary.md").write_text("Measured result.")
    (second_dir / "AGENTS.md").write_text("untrusted artifact")
    (second_dir / ".unsealed.mov").write_bytes(b"hidden")
    (second_dir / "nested-skill").mkdir()
    manifest_digest = ExperimentRunner._write_manifest(second_dir)
    store.seal_evidence(second["id"], manifest_digest)
    seen = {}

    def invoke(role, job, payload):
        snapshot_root = tmp_path / "codex-evidence-snapshots" / job["id"]
        snapshot = next(snapshot_root.iterdir())
        seen["names"] = sorted(path.name for path in snapshot.iterdir())
        seen["prompt"] = payload["prompt"]
        return analysis_result(store.get(second["id"]))

    orchestrator = CodexOrchestrator(store, settings, invoker=invoke)
    assert orchestrator.process_one("analysis") is True
    assert seen["names"] == ["AGENTS.md", "experiment.json", "manifest.json", "summary.md"]
    assert "untrusted artifact" in seen["prompt"]
    assert not list((tmp_path / "codex-evidence-snapshots").glob("*/*"))


def test_video_preprocessor_environment_excludes_lab_token(tmp_path, monkeypatch):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "camera.mov").write_bytes(b"video")
    (evidence / "manifest.json").write_text(json.dumps({
        "artifacts": [{"name": "camera.mov", "bytes": 5, "sha256": "0" * 64}],
    }))
    monkeypatch.setenv("HEXAPOD_LAB_TOKEN", "must-not-leak")
    captured = {}

    class Completed:
        returncode = 1

    def fake_run(*_args, **kwargs):
        captured["command"] = _args[0]
        captured["environment"] = kwargs["env"]
        return Completed()

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert CodexOrchestrator._video_contact_sheet(evidence, tmp_path) is None
    assert "HEXAPOD_LAB_TOKEN" not in captured["environment"]
    filter_value = captured["command"][captured["command"].index("-vf") + 1]
    assert "scale=320:240" in filter_value
    assert "pad=320:240" in filter_value
    assert "scale=320:-1" not in filter_value
    assert "-max_alloc" in captured["command"]


def test_advisory_target_completed_during_review_is_superseded(tmp_path):
    settings = configured(tmp_path)
    store = Store(tmp_path / "lab.sqlite3")
    target = store.create({
        "name": "manual race",
        "duration_seconds": 1,
        "execution_mode": "external_guarded",
    }, "test")

    def invoke(_role, job, _payload):
        store.cancel(target["id"])
        return {
            "schema_version": 1,
            "trigger_job_id": job["id"],
            "selected_experiment_id": target["id"],
            "action": "blocked",
            "summary": "Review was in progress.",
            "blocker": "read only",
            "safety_disposition": "clear",
            "motion_started": False,
            "retryable": False,
            "retry_after_seconds": 0,
        }

    orchestrator = CodexOrchestrator(store, settings, invoker=invoke)
    assert orchestrator.process_one("advance") is True
    job = next(job for job in store.list_codex_jobs(20)
               if job["trigger_kind"] == "experiment_submission")
    assert job["status"] == "succeeded"
    assert store.codex_queue_control()["paused"] is False


def test_evidence_that_never_becomes_quiet_hits_hard_deadline(tmp_path):
    settings = configured(
        tmp_path,
        codex_evidence_settle_seconds=60,
        codex_evidence_deadline_seconds=1,
    )
    store = Store(tmp_path / "lab.sqlite3")
    item = store.create({"name": "flapping evidence", "duration_seconds": 1}, "test")
    store.finish(item["id"], "succeeded")
    run_dir = tmp_path / "experiments" / item["id"]
    run_dir.mkdir(parents=True)
    (run_dir / "experiment.json").write_text(json.dumps(item))
    summary = run_dir / "summary.md"
    summary.write_text("still changing")
    future = datetime.now(timezone.utc).timestamp() + 3600
    os.utime(summary, (future, future))
    old = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    with store.connect() as connection:
        connection.execute(
            "UPDATE experiments SET finished_at=? WHERE id=?", (old, item["id"])
        )

    orchestrator = CodexOrchestrator(store, settings, invoker=lambda *_: {})
    assert orchestrator.reconcile_evidence() == 0
    jobs = store.codex_jobs_for_experiment(item["id"])
    assert {job["status"] for job in jobs} == {"blocked", "dead"}
    assert store.codex_queue_control()["paused"] is True
