"""Queue-control races at the engineering worker's process boundary.

All state is a temporary SQLite database. Provider execution, robot evidence
capture and process signals are replaced with local fakes; no service is used.
"""

import io
import json
import signal
import subprocess
from types import SimpleNamespace
import uuid

import pytest

import hexapod_lab.codex_orchestrator as runtime
from hexapod_lab.agent_providers import AgentLaunch
from hexapod_lab.config import Settings
from hexapod_lab.db import Store
from hexapod_lab.engineering_lane import (
    ENGINEERING_LANE_HARDWARE,
    ENGINEERING_LANE_OFFLINE,
)


@pytest.fixture
def lab(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    settings = Settings(
        data_dir=tmp_path / "data", api_keys="", driver="simulated",
        robot_command=(), camera_input="", bind="127.0.0.1", port=8767,
        public_base_url="", auto_worker=False, max_duration_seconds=30,
        codex_engineering=True, codex_engineering_workdir=workspace,
        codex_engineering_timeout_seconds=30,
    )
    store = Store(tmp_path / "lab.sqlite3")
    worker = runtime.CodexOrchestrator(store, settings)
    monkeypatch.setattr(runtime, "build_project_context", lambda *a: {"sha256": "a" * 64})
    monkeypatch.setattr(runtime, "workspace_snapshot", lambda *a: {"head": "b" * 40})
    monkeypatch.setattr(runtime, "engineering_prompt", lambda *a: "Synthetic bounded work")
    monkeypatch.setattr(runtime, "write_workspace_patch", lambda *a, **k: {})
    monkeypatch.setattr(runtime, "_codex_runner_identity", lambda *a: {})
    monkeypatch.setattr(worker, "_finalize_transcript", lambda *a: None)
    monkeypatch.setattr(worker, "_robot_telemetry_url", lambda: "http://unused.invalid")

    class NoRobotCapture:
        def __init__(self, *args, **kwargs):
            pass

        def begin(self):
            pass

        def finish(self):
            pass

    monkeypatch.setattr(runtime, "RobotCommunicationCapture", NoRobotCapture)
    return SimpleNamespace(store=store, worker=worker, workspace=workspace, settings=settings)


def _plan(lab, *, offline=False):
    parameters = {"simulation_only": True, "robot_motion": False} if offline else {}
    plan = lab.store.create({
        "name": "Synthetic guarded plan", "duration_seconds": 1,
        "execution_mode": "external_guarded", "parameters": parameters,
    }, "test")
    advance = lab.store.enqueue_advance(uuid.uuid4().hex, "test", experiment_id=plan["id"])
    job = lab.worker.engineering.ensure_queue_handoff(advance, plan, 3)
    return plan, advance, job


def _pause(lab):
    return lab.store.pause_codex_queue_for_operator("Test pause", created_by="test")


def _row(lab, job):
    return next(row for row in lab.worker.engineering.list_jobs() if row["id"] == job["id"])


def _attempt_dir(lab, job, attempt=1):
    return lab.settings.data_dir / "codex-runs" / job["id"] / f"attempt-{attempt}"


class _FakeProvider:
    name = "fake"
    label = "Fake"
    model = "test-only"
    reasoning_effort = "none"

    def __init__(self, before_launch=None):
        self.before_launch = before_launch

    def build(self, role, **kwargs):
        kwargs["output_path"].write_text("{}")
        if self.before_launch:
            self.before_launch()
        return AgentLaunch(["never-executed-test-provider"], b"", {}, kwargs["workdir"])

    def usage(self, run_dir):
        return {}

    def materialize_output(self, run_dir, output_path):
        return ""


def _mock_native_process(lab, monkeypatch, during_wait, *, exits=False):
    """Exercise real group-cleanup logic with a process that cannot signal OS PIDs."""
    calls = SimpleNamespace(launches=[], signals=[], waits=0, group_alive=True)

    class FakeProcess:
        pid = 424242
        returncode = None
        stdin = io.BytesIO()

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            if self.returncode is not None:
                return self.returncode
            calls.waits += 1
            if calls.waits == 1:
                during_wait()
            if exits:
                self.returncode = 0
                calls.group_alive = False
                return 0
            raise subprocess.TimeoutExpired("fake-provider", timeout)

    process = FakeProcess()

    def popen(command, **kwargs):
        calls.launches.append((command, kwargs))
        assert kwargs["start_new_session"] is True
        return process

    def group_exists(pgid):
        assert pgid == process.pid
        return calls.group_alive

    def killpg(pgid, sig):
        assert pgid == process.pid
        calls.signals.append((pgid, sig))
        process.returncode = -int(sig)
        calls.group_alive = False

    lab.worker.provider = _FakeProvider()
    monkeypatch.setattr(runtime.subprocess, "Popen", popen)
    monkeypatch.setattr(runtime, "_process_group_exists", group_exists)
    monkeypatch.setattr(runtime.os, "killpg", killpg)
    return process, calls


def test_pause_after_claim_defers_without_invoking_or_spending_attempt(lab, monkeypatch):
    _, _, job = _plan(lab)
    invocations = []
    lab.worker.invoker = lambda *args: invocations.append(args)
    real_claim = lab.worker.engineering.claim

    def claim_then_pause(*args, **kwargs):
        claimed = real_claim(*args, **kwargs)
        assert claimed is not None
        _pause(lab)
        return claimed

    monkeypatch.setattr(lab.worker.engineering, "claim", claim_then_pause)
    assert lab.worker._process_one_engineering(ENGINEERING_LANE_HARDWARE)
    assert invocations == []
    stored = _row(lab, job)
    assert stored["status"] == "retry"
    assert stored["attempts"] == 0
    assert stored["lease_owner"] is None
    assert stored["result"]["unstarted_defer_receipt"]["child_started"] is False
    assert not _attempt_dir(lab, job).exists()
    assert not lab.worker.stop_event.is_set()


def test_invoke_checks_pause_before_custom_invoker(lab):
    _plan(lab)
    job = lab.worker.engineering.claim(lab.worker.owner, 60)
    _pause(lab)
    calls = []
    lab.worker.invoker = lambda *args: calls.append(args)
    with pytest.raises(runtime.EngineeringExecutionRevoked):
        lab.worker._invoke("engineering", job, "prompt", {})
    assert calls == []
    assert not job.get("_engineering_launch_attempted")
    assert not job.get("_engineering_actions_started")


def test_pause_during_preparation_archives_unstarted_attempt_before_refund(lab, monkeypatch):
    _, _, job = _plan(lab)
    lab.worker.provider = _FakeProvider(before_launch=lambda: _pause(lab))
    launches = []
    monkeypatch.setattr(runtime.subprocess, "Popen", lambda *a, **k: launches.append(a))
    assert lab.worker._process_one_engineering(ENGINEERING_LANE_HARDWARE)
    assert launches == []
    stored = _row(lab, job)
    assert stored["status"] == "retry" and stored["attempts"] == 0
    assert not _attempt_dir(lab, job).exists()
    archived = list(_attempt_dir(lab, job).parent.glob("unstarted-attempt-1-*"))
    assert len(archived) == 1
    receipt = json.loads((archived[0] / "unstarted.json").read_text())
    assert receipt["provider_launch_attempted"] is False
    assert lab.worker.engineering.claim(lab.worker.owner, 60) is None


@pytest.mark.parametrize("resume_before_poll", [False, True])
def test_running_pause_cleans_owned_group_and_parks_without_replay(lab, monkeypatch, resume_before_poll):
    plan, advance, job = _plan(lab)

    def interrupt():
        _pause(lab)
        if resume_before_poll:
            assert lab.store.resume_codex_queue("Resume after inspection", created_by="test")["resumed"]

    process, calls = _mock_native_process(lab, monkeypatch, interrupt)
    assert lab.worker._process_one_engineering(ENGINEERING_LANE_HARDWARE)
    assert len(calls.launches) == 1 and calls.waits == 1
    assert calls.signals == [(process.pid, signal.SIGTERM)]
    assert not calls.group_alive and lab.worker.processes == {}
    marker = json.loads((_attempt_dir(lab, job) / "process.json").read_text())
    assert marker["pgid"] == process.pid and marker["assignment_revoked"] is True
    assert "finished_at" in marker
    stored = _row(lab, job)
    assert stored["status"] == "blocked" and stored["attempts"] == 1
    assert stored["lease_owner"] is None
    assert stored["result"]["execution_revocation"]["execution_may_have_started"] is True
    assert stored["result"]["continuation"]["completion_only"] is True
    assert not stored["result"].get("physical_motion_started")
    assert lab.worker.progress.latest()["state"] == "blocked"
    assert lab.worker.engineering.ensure_queue_handoff(advance, plan)["status"] == "blocked"
    assert lab.worker.engineering.claim(lab.worker.owner, 60) is None
    assert not lab.worker.stop_event.is_set()


def test_cancellation_at_process_exit_discards_successful_provider_result(lab, monkeypatch):
    plan, _, job = _plan(lab)
    process, calls = _mock_native_process(
        lab, monkeypatch, lambda: lab.store.cancel(plan["id"]), exits=True,
    )
    assert lab.worker._process_one_engineering(ENGINEERING_LANE_HARDWARE)
    assert process.returncode == 0 and len(calls.launches) == 1
    stored = _row(lab, job)
    assert stored["status"] == "blocked" and stored["attempts"] == 1
    marker = json.loads((_attempt_dir(lab, job) / "process.json").read_text())
    assert marker["assignment_revoked"] is True
    assert not (_attempt_dir(lab, job) / "final.json").exists()


@pytest.mark.parametrize("failed_archive", ["process_marker", "transcript"])
def test_revocation_survives_evidence_archive_failure(lab, monkeypatch, failed_archive):
    plan, advance, job = _plan(lab)

    def pause_and_resume():
        _pause(lab)
        lab.store.resume_codex_queue("Inspection complete", created_by="test")

    _, calls = _mock_native_process(lab, monkeypatch, pause_and_resume)
    if failed_archive == "process_marker":
        real_atomic_json = runtime._atomic_json

        def write_json(path, payload):
            if path.name == "process.json" and "returncode" in payload:
                raise OSError("Synthetic final process marker failure")
            return real_atomic_json(path, payload)

        monkeypatch.setattr(runtime, "_atomic_json", write_json)
    else:
        def fail_transcript(*args):
            raise OSError("Synthetic transcript archive failure")

        monkeypatch.setattr(lab.worker, "_finalize_transcript", fail_transcript)

    assert lab.worker._process_one_engineering(ENGINEERING_LANE_HARDWARE)
    assert not calls.group_alive and lab.worker.processes == {}
    stored = _row(lab, job)
    assert stored["status"] == "blocked" and stored["attempts"] == 1
    assert stored["result"]["continuation"]["completion_only"] is True
    assert lab.worker.engineering.ensure_queue_handoff(advance, plan)["status"] == "blocked"
    assert lab.worker.engineering.claim(lab.worker.owner, 60) is None
    assert not lab.worker.stop_event.is_set()


def test_explicit_offline_invocation_remains_allowed_while_physical_queue_paused(lab):
    _plan(lab, offline=True)
    _pause(lab)
    job = lab.worker.engineering.claim(lab.worker.owner, 60, lane=ENGINEERING_LANE_OFFLINE)
    assert job is not None
    calls = []

    def invoke(*args):
        calls.append(args)
        return {"offline_result": "done"}

    lab.worker.invoker = invoke
    assert lab.worker._invoke(
        "engineering", job, "prompt", {}, engineering_lane=ENGINEERING_LANE_OFFLINE,
    ) == {"offline_result": "done"}
    assert len(calls) == 1
    assert not job.get("_engineering_actions_started")
    assert lab.worker.engineering.execution_revocation_reason(job, lab.worker.owner) is None


def test_cleanup_failure_overrides_workspace_archive_failure_and_keeps_lease(lab, monkeypatch):
    _, _, job = _plan(lab)
    process, calls = _mock_native_process(lab, monkeypatch, lambda: _pause(lab))
    monkeypatch.setattr(runtime, "_terminate_deadline_wrapper", lambda *a, **k: False)
    snapshots = []

    def snapshot(*args):
        snapshots.append(None)
        if len(snapshots) > 1:
            raise OSError("Synthetic workspace archive failure")
        return {"head": "b" * 40}

    monkeypatch.setattr(runtime, "workspace_snapshot", snapshot)
    assert lab.worker._process_one_engineering(ENGINEERING_LANE_HARDWARE)
    stored = _row(lab, job)
    assert stored["status"] == "running" and stored["attempts"] == 1
    assert stored["lease_owner"] == lab.worker.owner and stored["lease_token"]
    assert stored["result"] is None
    assert process.pid in lab.worker.processes and calls.group_alive
    assert lab.worker.stop_event.is_set() and lab.worker.fatal_cleanup_event.is_set()
    assert lab.worker.service_exit_code() == 75
    marker = json.loads((_attempt_dir(lab, job) / "process.json").read_text())
    assert marker["assignment_revoked"] is True and "cleanup_failed_at" in marker
    assert "finished_at" not in marker
    assert lab.worker.engineering.claim("replacement-owner", 60) is None
