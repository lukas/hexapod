from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time
import pytest

import hexapod_lab.codex_orchestrator as codex_module
from hexapod_lab.codex_orchestrator import (
    QUEUE_STOP_ASSESS_S, QUEUE_STOP_MAX_ATTEMPTS, CodexOrchestrator)
from hexapod_lab.config import Settings
from hexapod_lab.db import Store
from hexapod_lab.engineering_lane import (
    DEPLOYMENT_SOURCE_GUARD,
    DisabledRLDispatcher,
    ENGINEERING_LANE_HARDWARE,
    ENGINEERING_LANE_OFFLINE,
    EngineeringJobStore,
    EngineeringLaneError,
    PROJECT_CONTEXT_FILES,
    build_project_context,
    engineering_job_lane,
    engineering_prompt,
    validate_engineering_result,
    validate_rl_request,
)


def configured(tmp_path, workspace, **overrides):
    values = dict(
        data_dir=tmp_path / "data",
        api_keys="",
        driver="simulated",
        robot_command=(),
        camera_input="",
        bind="127.0.0.1",
        port=8767,
        public_base_url="",
        auto_worker=False,
        max_duration_seconds=30,
        codex_engineering=True,
        codex_engineering_workdir=workspace,
        codex_engineering_timeout_seconds=123,
    )
    values.update(overrides)
    return Settings(**values)


def succeeded_analysis(
    store, *, verdict="pass", safety_disposition="clear", parameters=None,
    experiment_status="succeeded", started_at=None,
):
    experiment = store.create(
        {
            "name": "measured gait",
            "duration_seconds": 1,
            "parameters": {} if parameters is None else parameters,
        },
        "test",
    )
    if experiment_status == "cancelled":
        store.cancel(experiment["id"])
    else:
        store.finish(experiment["id"], experiment_status)
    if started_at is not None:
        with store.connect() as con:
            con.execute(
                "UPDATE experiments SET started_at=? WHERE id=?",
                (started_at, experiment["id"]),
            )
    store.seal_evidence(experiment["id"], "a" * 64)
    analysis = store.claim_codex_job("analysis", "analyzer", lease_seconds=60)
    assert analysis is not None
    result = {
        "schema_version": 1,
        "experiment_id": experiment["id"],
        "evidence_manifest_sha256": "a" * 64,
        "verdict": verdict,
        "safety_disposition": safety_disposition,
        "what_we_learned": "The gait was repeatable.",
        "sources": ["summary.md"],
        "findings": ["Stable in the measured window."],
        "recommended_experiments": [],
    }
    store.finish_codex_job(
        analysis["id"],
        "analyzer",
        "succeeded",
        result=result,
        lease_token=analysis["lease_token"],
    )
    return experiment, analysis


def engineering_receipt(job, project_context_sha256):
    return {
        "schema_version": 1,
        "engineering_job_id": job["id"],
        "source_analysis_job_id": job["source_analysis_job_id"],
        "experiment_id": job["experiment_id"],
        "project_context_sha256": project_context_sha256,
        "outcome": "changed",
        "mission_alignment": "Prepared one bounded improvement.",
        "summary": "The completed work has a structured receipt.",
        "changed_files": ["bounded.py"],
        "commands_run": [],
        "artifacts": [],
        "rl_orchestrator_requests": [],
        "buildviz_summary": "",
        "next_steps": ["Continue the guarded plan."],
        "operator_actions": [],
        "safety_checks": ["No physical motion started."],
        "physical_motion_started": False,
        "robot_contacted": False,
        "network_used": False,
    }


def test_hardware_and_offline_jobs_claim_independently(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    engineering = EngineeringJobStore(store)
    replay = store.create(
        {
            "name": "explicit offline replay",
            "duration_seconds": 1,
            "parameters": {"simulation_only": True, "robot_motion": False},
            "execution_mode": "external_guarded",
        },
        "test",
    )
    replay_advance = store.enqueue_advance(
        "explicit-offline-replay", "test", experiment_id=replay["id"]
    )
    replay_handoff = engineering.ensure_queue_handoff(replay_advance, replay)

    offline = engineering.claim(
        "offline-worker", lease_seconds=60, lane=ENGINEERING_LANE_OFFLINE
    )
    assert offline is not None
    assert offline["id"] == replay_handoff["id"]
    assert offline["lane"] == ENGINEERING_LANE_OFFLINE

    guarded = store.create(
        {
            "name": "bounded physical gait",
            "duration_seconds": 3,
            "parameters": {"robot_motion": True, "queue_priority": -999},
            "execution_mode": "external_guarded",
        },
        "test",
    )
    advance = store.enqueue_advance(
        "hardware-arrived-later", "test", experiment_id=guarded["id"]
    )
    handoff = engineering.ensure_queue_handoff(advance, guarded)

    hardware = engineering.claim(
        "hardware-worker", lease_seconds=60, lane=ENGINEERING_LANE_HARDWARE
    )
    assert hardware is not None
    assert hardware["id"] == handoff["id"]
    assert hardware["lane"] == ENGINEERING_LANE_HARDWARE
    assert hardware["lease_owner"] == "hardware-worker"
    assert offline["lease_owner"] == "offline-worker"


@pytest.mark.parametrize(
    ("parameters", "expected_lane"),
    [
        ({"robot_motion": False}, ENGINEERING_LANE_OFFLINE),
        ({"simulation_only": True}, ENGINEERING_LANE_OFFLINE),
        (
            {"robot_motion": False, "simulation_only": True},
            ENGINEERING_LANE_OFFLINE,
        ),
        ({"robot_motion": True}, ENGINEERING_LANE_HARDWARE),
        ({}, ENGINEERING_LANE_HARDWARE),
        ({"robot_motion": 1}, ENGINEERING_LANE_HARDWARE),
        ({"simulation_only": 1}, ENGINEERING_LANE_HARDWARE),
        (
            {"robot_motion": True, "simulation_only": True},
            ENGINEERING_LANE_HARDWARE,
        ),
    ],
)
def test_analysis_followthrough_only_reopens_physical_repairs(
    tmp_path, parameters, expected_lane
):
    store = Store(tmp_path / "lab.sqlite3")
    _, analysis = succeeded_analysis(
        store, verdict="fail", parameters=parameters
    )
    engineering = EngineeringJobStore(store)
    if expected_lane == ENGINEERING_LANE_OFFLINE:
        assert engineering.reconcile() == 0
        assert engineering.list_jobs() == []
        return
    assert engineering.reconcile() == 1

    other_lane = (
        ENGINEERING_LANE_OFFLINE
        if expected_lane == ENGINEERING_LANE_HARDWARE
        else ENGINEERING_LANE_HARDWARE
    )
    assert engineering.claim("wrong-worker", 60, lane=other_lane) is None
    claimed = engineering.claim("right-worker", 60, lane=expected_lane)
    assert claimed is not None
    assert claimed["source_analysis_job_id"] == analysis["id"]
    assert claimed["lane"] == expected_lane


def test_missing_or_invalid_source_context_stays_on_hardware_lane():
    assert engineering_job_lane(None) == ENGINEERING_LANE_HARDWARE
    assert engineering_job_lane({}) == ENGINEERING_LANE_HARDWARE


@pytest.mark.parametrize(
    "parameters, verdict, disposition, needs_repair",
    [
        ({"robot_motion": False}, "fail", "stop", False),
        ({"simulation_only": True}, "inconclusive", "needs_inspection", False),
        ({"simulation_only": True}, "pass", "clear", False),
        ({"robot_motion": True}, "pass", "clear", False),
        ({"robot_motion": True}, "inconclusive", "clear", False),
        ({"robot_motion": True}, "fail", "clear", True),
        ({"robot_motion": True}, "inconclusive", "needs_inspection", True),
        ({"robot_motion": True}, "pass", "stop", True),
    ],
)
def test_analysis_followthrough_keeps_repairs_without_repeated_offline_reviews(
    tmp_path, parameters, verdict, disposition, needs_repair
):
    store = Store(tmp_path / "lab.sqlite3")
    succeeded_analysis(
        store, parameters=parameters, verdict=verdict,
        safety_disposition=disposition,
    )
    engineering = EngineeringJobStore(store)

    assert engineering.reconcile() == int(needs_repair)
    assert engineering.reconcile() == 0
    assert len(engineering.list_jobs()) == int(needs_repair)


@pytest.mark.parametrize("status", ["queued", "retry"])
def test_existing_offline_analysis_reviews_retire_without_another_worker(
    tmp_path, monkeypatch, status
):
    store = Store(tmp_path / "lab.sqlite3")
    succeeded_analysis(
        store, verdict="fail", safety_disposition="needs_inspection",
        parameters={"simulation_only": True},
    )
    engineering = EngineeringJobStore(store)
    # Seed a review created under the former policy, then reconcile after upgrade.
    with monkeypatch.context() as previous_policy:
        previous_policy.setattr(
            EngineeringJobStore, "_analysis_needs_no_engineering",
            staticmethod(lambda *_: False),
        )
        assert engineering.reconcile() == 1
    job = engineering.list_jobs()[0]
    with store.connect() as con:
        con.execute(
            "UPDATE codex_engineering_jobs SET status=? WHERE id=?",
            (status, job["id"]),
        )

    assert engineering.reconcile() == 1
    assert engineering.claim("engineer", 60) is None
    retired = engineering.list_jobs()[0]
    assert retired["id"] == job["id"]
    assert retired["status"] == "succeeded"
    assert retired["result"]["outcome"] == "no_change"
    assert retired["result"]["commands_run"] == []


@pytest.mark.parametrize(
    "status,started_at,disposition,needs_repair",
    [
        ("cancelled", None, "clear", False),
        ("failed", None, "clear", True),
        ("cancelled", "2026-09-06T03:00:00+00:00", "clear", True),
        ("cancelled", None, "stop", True),
        ("cancelled", None, "needs_inspection", True),
    ],
)
def test_cancelled_unstarted_invalid_analysis_does_not_reopen_hardware_work(
    tmp_path, status, started_at, disposition, needs_repair
):
    store = Store(tmp_path / "lab.sqlite3")
    succeeded_analysis(
        store, verdict="invalid", safety_disposition=disposition,
        parameters={"robot_motion": True}, experiment_status=status,
        started_at=started_at,
    )
    engineering = EngineeringJobStore(store)

    assert engineering.reconcile() == int(needs_repair)
    assert engineering.reconcile() == 0
    claimed = engineering.claim("engineer", 60, lane=ENGINEERING_LANE_HARDWARE)
    assert (claimed is not None) == needs_repair


@pytest.mark.parametrize("status", ["queued", "retry"])
@pytest.mark.parametrize("entrypoint", ["reconcile", "claim"])
def test_legacy_cancelled_analysis_job_retires_before_another_worker_runs(
    tmp_path, monkeypatch, status, entrypoint
):
    store = Store(tmp_path / "lab.sqlite3")
    experiment, _ = succeeded_analysis(
        store, verdict="invalid", parameters={"robot_motion": True},
        experiment_status="cancelled",
    )
    engineering = EngineeringJobStore(store)
    with monkeypatch.context() as old_policy:
        old_policy.setattr(
            EngineeringJobStore, "_analysis_needs_no_engineering",
            staticmethod(lambda *_: False),
        )
        assert engineering.reconcile() == 1
    job = engineering.list_jobs()[0]
    # The old prompt snapshot need not contain the new cancellation fields:
    # retirement must consult the current experiment record.
    source = job["source_context"]
    source["experiment"].pop("status", None)
    source["experiment"].pop("cancel_requested", None)
    source["experiment"].pop("started_at", None)
    with store.connect() as con:
        con.execute(
            "UPDATE codex_engineering_jobs SET status=?,source_context_json=? "
            "WHERE id=?",
            (status, json.dumps(source), job["id"]),
        )

    if entrypoint == "reconcile":
        assert engineering.reconcile() == 1
    assert engineering.claim("engineer", 60) is None
    retired = engineering.list_jobs()[0]
    assert retired["id"] == job["id"]
    assert retired["status"] == "succeeded"
    assert retired["attempts"] == 0
    assert retired["result"]["outcome"] == "no_change"
    assert retired["result"]["physical_motion_started"] is False
    assert retired["result"]["commands_run"] == []
    assert store.get(experiment["id"])["status"] == "cancelled"


def test_scoped_cancelled_analysis_retirement_preserves_other_jobs(
    tmp_path, monkeypatch
):
    store = Store(tmp_path / "lab.sqlite3")
    engineering = EngineeringJobStore(store)
    first, _ = succeeded_analysis(
        store, verdict="invalid", parameters={"robot_motion": True},
        experiment_status="cancelled",
    )
    second, _ = succeeded_analysis(
        store, verdict="invalid", parameters={"robot_motion": True},
        experiment_status="cancelled",
    )
    active, _ = succeeded_analysis(
        store, verdict="fail", parameters={"robot_motion": True},
        experiment_status="failed",
    )
    with monkeypatch.context() as old_policy:
        old_policy.setattr(
            EngineeringJobStore, "_analysis_needs_no_engineering",
            staticmethod(lambda *_: False),
        )
        assert engineering.reconcile() == 3
    with store.connect() as con:
        con.execute(
            "UPDATE codex_engineering_jobs SET status='running',"
            "lease_owner='active-worker',lease_token='preserve-token' "
            "WHERE experiment_id=?", (active["id"],),
        )
        con.execute("BEGIN IMMEDIATE")
        assert engineering._retire_redundant_analysis_jobs(
            con, "2026-09-06T04:00:00+00:00", experiment_id=first["id"]
        ) == 1
        con.execute("COMMIT")
    jobs = {job["experiment_id"]: job for job in engineering.list_jobs()}
    assert jobs[first["id"]]["status"] == "succeeded"
    assert jobs[second["id"]]["status"] == "queued"
    assert jobs[active["id"]]["status"] == "running"
    assert jobs[active["id"]]["lease_owner"] == "active-worker"
    assert jobs[active["id"]]["lease_token"] == "preserve-token"


@pytest.mark.parametrize("handoff_state", ["running", "unknown", "motion_receipt"])
def test_cancelled_external_plan_keeps_recovery_when_motion_may_have_started(
    tmp_path, handoff_state
):
    store = Store(tmp_path / "lab.sqlite3")
    experiment, _ = succeeded_analysis(
        store, verdict="invalid", parameters={"robot_motion": True},
        experiment_status="cancelled",
    )
    engineering = EngineeringJobStore(store)
    advance = store.enqueue_advance(
        "existing-handoff", "test", experiment_id=experiment["id"]
    )
    handoff = engineering.ensure_queue_handoff(advance, experiment)
    receipt = (
        {"previous_receipt": {"physical_motion_started": True}}
        if handoff_state == "motion_receipt" else None
    )
    with store.connect() as con:
        con.execute(
            "UPDATE codex_engineering_jobs SET status=?,attempts=1,result_json=? "
            "WHERE id=?",
            (
                "running" if handoff_state == "running" else "dead",
                json.dumps(receipt) if receipt is not None else None,
                handoff["id"],
            ),
        )

    assert engineering.reconcile() == 1
    repair = next(job for job in engineering.list_jobs()
                  if job["source_context"]["trigger_kind"] == "experiment_analysis")
    assert repair["status"] == "queued"
    assert engineering.claim("recovery-worker", 60)["id"] == repair["id"]


@pytest.mark.parametrize(
    "parameters",
    [
        {"robot_motion": False, "simulation_only": True},
    ],
)
def test_explicit_offline_handoff_never_reaches_hardware_lane(
    tmp_path, parameters
):
    store = Store(tmp_path / "lab.sqlite3")
    guarded = store.create(
        {
            "name": "offline replay",
            "duration_seconds": 1,
            "parameters": parameters,
            "execution_mode": "external_guarded",
        },
        "test",
    )
    advance = store.enqueue_advance(
        "offline-handoff", "test", experiment_id=guarded["id"]
    )
    engineering = EngineeringJobStore(store)
    handoff = engineering.ensure_queue_handoff(advance, guarded)

    assert engineering.claim(
        "hardware-worker", lease_seconds=60, lane=ENGINEERING_LANE_HARDWARE
    ) is None
    offline = engineering.claim(
        "offline-worker", lease_seconds=60, lane=ENGINEERING_LANE_OFFLINE
    )
    assert offline["id"] == handoff["id"]


@pytest.mark.parametrize(
    "parameters",
    [
        {},
        {"robot_motion": False},
        {"simulation_only": True},
        {"robot_motion": False, "simulation_only": False},
        {"robot_motion": 0},
        {"simulation_only": 1},
        {"robot_motion": True, "simulation_only": True},
        {"robot_motion": 1, "simulation_only": True},
    ],
)
def test_legacy_ambiguous_handoff_stays_on_hardware_lane(tmp_path, parameters):
    store = Store(tmp_path / "lab.sqlite3")
    guarded = store.create(
        {
            "name": "legacy guarded plan",
            "duration_seconds": 1,
            "parameters": parameters,
            "execution_mode": "external_guarded",
        },
        "test",
    )
    advance = store.enqueue_advance(
        "legacy-handoff", "test", experiment_id=guarded["id"]
    )
    engineering = EngineeringJobStore(store)
    handoff = engineering.ensure_queue_handoff(advance, guarded)

    assert engineering.claim(
        "offline-worker", lease_seconds=60, lane=ENGINEERING_LANE_OFFLINE
    ) is None
    hardware = engineering.claim(
        "hardware-worker", lease_seconds=60, lane=ENGINEERING_LANE_HARDWARE
    )
    assert hardware["id"] == handoff["id"]


def test_motionless_live_health_gate_uses_hardware_lane(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    guarded = store.create(
        {
            "name": "motionless live health gate",
            "duration_seconds": 30,
            "parameters": {
                "simulation_only": False,
                "robot_motion": False,
                "live_camera_required": True,
                "required_live_motor_count": 18,
                "minimum_advancing_samples": 3,
            },
            "execution_mode": "external_guarded",
        },
        "test",
    )
    advance = store.enqueue_advance(
        "live-health-handoff", "test", experiment_id=guarded["id"]
    )
    engineering = EngineeringJobStore(store)
    handoff = engineering.ensure_queue_handoff(advance, guarded)

    assert engineering.claim(
        "offline-worker", lease_seconds=60, lane=ENGINEERING_LANE_OFFLINE
    ) is None
    hardware = engineering.claim(
        "hardware-worker", lease_seconds=60, lane=ENGINEERING_LANE_HARDWARE
    )
    assert hardware["id"] == handoff["id"]


def test_succeeded_analysis_reconciles_once_and_rl_outbox_is_validated(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    experiment, analysis = succeeded_analysis(store, verdict="fail")
    engineering = EngineeringJobStore(store)

    assert engineering.reconcile(max_attempts=2) == 1
    assert engineering.reconcile(max_attempts=2) == 0
    job = engineering.claim("engineer", lease_seconds=60)
    assert job["source_analysis_job_id"] == analysis["id"]
    request = {
        "request_key": "gait-followup-1",
        "action": "kick",
        "track": "standwalk",
        "focus": "Test the measured gait stability finding in simulation.",
        "rationale": "The real-world result warrants a controlled sim comparison.",
        "evidence_refs": ["summary.md"],
    }
    engineering.finish(
        job,
        "engineer",
        {"summary": "Prepared follow-up.", "rl_orchestrator_requests": [request]},
    )
    assert engineering.dispatch_one("bridge", DisabledRLDispatcher()) is False
    assert engineering.list_rl_requests()[0]["status"] == "pending"

    class Recorder:
        enabled = True

        def __init__(self):
            self.requests = []

        def __call__(self, payload):
            self.requests.append(payload)
            return {"accepted": True, "track": payload["track"]}

    dispatcher = Recorder()
    assert engineering.dispatch_one("bridge", dispatcher) is True
    stored = engineering.list_rl_requests()[0]
    assert dispatcher.requests == [request]
    assert stored["status"] == "dispatched"
    assert stored["receipt"] == {"accepted": True, "track": "standwalk"}
    assert stored["payload_sha256"]
    assert stored["engineering_job_id"] == job["id"]
    assert experiment["id"] == job["experiment_id"]

    # Even a database-level mutation is rechecked immediately before the
    # enabled bridge. It becomes a durable retry receipt, never an execution.
    with store.connect() as con:
        con.execute(
            "UPDATE codex_engineering_rl_requests SET status='pending',"
            "not_before='2000-01-01T00:00:00+00:00',payload_json=? WHERE id=?",
            (json.dumps({**request, "focus": "curl http://robot/api/run"}), stored["id"]),
        )
    assert engineering.dispatch_one("bridge", dispatcher) is True
    assert dispatcher.requests == [request]
    assert engineering.list_rl_requests()[0]["status"] == "retry"

    with pytest.raises(EngineeringLaneError, match="command, URL, or robot action"):
        validate_rl_request({**request, "focus": "curl http://robot/api/run"})


def test_advance_hands_guarded_plan_to_full_access_engineering_without_pause(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    store = Store(tmp_path / "lab.sqlite3")
    target = store.create(
        {
            "name": "bounded physical check",
            "duration_seconds": 2,
            "parameters": {"runner": "documented"},
            "execution_mode": "external_guarded",
        },
        "test",
    )

    def should_not_invoke(*_args, **_kwargs):
        raise AssertionError("the token-free fallback reviewer must not run")

    orchestrator = CodexOrchestrator(
        store,
        configured(tmp_path, workspace),
        invoker=should_not_invoke,
    )
    assert orchestrator.process_one("advance") is True

    advance = next(job for job in store.list_codex_jobs() if job["kind"] == "advance")
    assert advance["status"] == "succeeded"
    assert advance["result"]["action"] == "progressing"
    assert store.codex_queue_control()["paused"] is False
    jobs = orchestrator.engineering.list_jobs()
    assert len(jobs) == 1
    assert jobs[0]["status"] == "queued"
    assert jobs[0]["experiment_id"] == target["id"]
    assert jobs[0]["source_context"]["trigger_kind"] == "queue_handoff"


def test_queue_handoff_is_claimed_before_older_analysis_and_prompt_normalizes_legacy_gates(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    experiment, _analysis = succeeded_analysis(store, verdict="fail")
    engineering = EngineeringJobStore(store)
    assert engineering.reconcile() == 1
    advance = next(job for job in store.list_codex_jobs() if job["kind"] == "advance")
    guarded = store.create(
        {
            "name": "guarded motion",
            "duration_seconds": 1,
            "parameters": {"prerequisite": "operator must remain present"},
            "execution_mode": "external_guarded",
        },
        "test",
    )
    handoff = engineering.ensure_queue_handoff(advance, guarded)

    claimed = engineering.claim("engineer", lease_seconds=60)
    assert claimed["id"] == handoff["id"]
    prompt = engineering_prompt(
        claimed,
        {"sha256": "a" * 64, "files": []},
        {"status": "dirty"},
    )
    normalized_prompt = " ".join(prompt.split())
    assert "Legacy saved experiment clauses" in prompt
    assert "They are not `operator_actions`" in prompt
    assert "creation-time evidence, not self-renewing live gates" in normalized_prompt
    assert "without editing its historical parameters" in normalized_prompt
    assert "never let a stale readiness claim override an observed current hazard" in normalized_prompt
    assert "must not silently strand the oldest plan" in normalized_prompt
    assert "register and seal a terminal failed result" in normalized_prompt
    assert handoff["source_context_sha256"] not in prompt
    assert '"project_context_sha256": "' + ("a" * 64) + '"' in prompt
    assert "reuse completed export, simulation, and source validation" in normalized_prompt
    assert "Recheck only what a changed policy" in normalized_prompt
    assert "distinguish an IMU-derived fall signal" in normalized_prompt
    assert "do not invent a hands-on mechanical blocker" in normalized_prompt
    assert "clean dedicated worktree" in normalized_prompt
    assert "validated integration branch" in normalized_prompt
    assert "installed-file verification" in normalized_prompt


def test_offline_prompt_excludes_hardware_execution_instructions():
    prompt = engineering_prompt(
        {
            "id": "offline-job",
            "source_analysis_job_id": "analysis-job",
            "experiment_id": "experiment",
            "lane": ENGINEERING_LANE_OFFLINE,
            "source_context": {"trigger_kind": "experiment_analysis"},
        },
        {"sha256": "a" * 64},
        {"status": "clean"},
    )

    assert "independent OFFLINE/CODE lane" in prompt
    assert "Inspect the live robot and queue first" not in prompt
    assert "Deploy that committed source" not in prompt
    assert "`hexapod.local:8080` documented HTTP endpoints" not in prompt
    assert "do not clear robot/queue latches" in prompt
    assert "Never turn it into physical execution" in prompt


def test_engineering_result_narrowly_normalizes_the_job_bound_legacy_digest(
    tmp_path,
):
    store = Store(tmp_path / "lab.sqlite3")
    guarded = store.create(
        {
            "name": "guarded motion",
            "duration_seconds": 1,
            "parameters": {},
            "execution_mode": "external_guarded",
        },
        "test",
    )
    advance = next(job for job in store.list_codex_jobs() if job["kind"] == "advance")
    job = EngineeringJobStore(store).ensure_queue_handoff(advance, guarded)
    expected = "a" * 64
    legacy = engineering_receipt(job, job["source_context_sha256"])

    normalized = validate_engineering_result(legacy, job, expected)

    assert normalized["project_context_sha256"] == expected
    arbitrary = engineering_receipt(job, "b" * 64)
    with pytest.raises(EngineeringLaneError, match="identity"):
        validate_engineering_result(arbitrary, job, expected)
    wrong_job = dict(legacy, engineering_job_id="other")
    with pytest.raises(EngineeringLaneError, match="identity"):
        validate_engineering_result(wrong_job, job, expected)


def test_recovered_receipt_then_intentional_continuation_invokes_new_work_and_seals(
    tmp_path, monkeypatch,
):
    workspace = tmp_path / "project"
    workspace.mkdir()
    settings = configured(tmp_path, workspace)
    store = Store(tmp_path / "lab.sqlite3")
    guarded = store.create(
        {
            "name": "guarded motion",
            "duration_seconds": 1,
            "parameters": {},
            "execution_mode": "external_guarded",
        },
        "test",
    )
    advance = next(job for job in store.list_codex_jobs() if job["kind"] == "advance")
    engineering = EngineeringJobStore(store)
    queued = engineering.ensure_queue_handoff(advance, guarded)
    attempt = engineering.claim("first", lease_seconds=60)
    expected_context = "a" * 64
    receipt = engineering_receipt(attempt, attempt["source_context_sha256"])
    attempt_dir = settings.data_dir / "codex-runs" / queued["id"] / "attempt-1"
    attempt_dir.mkdir(parents=True)
    prompt = (
        "Pinned project mission/goals/context "
        f"(hash {expected_context}):\n"
    )
    (attempt_dir / "prompt.md").write_text(prompt, encoding="utf-8")
    (attempt_dir / "final.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )
    (attempt_dir / "workspace-before.json").write_text(
        json.dumps({"head": "before"}), encoding="utf-8"
    )
    (attempt_dir / "workspace-after.json").write_text(
        json.dumps({"head": "after"}), encoding="utf-8"
    )
    patch = b""
    (attempt_dir / "workspace.patch").write_bytes(patch)
    patch_receipt = {
        "path": "workspace.patch",
        "bytes": 0,
        "sha256": hashlib.sha256(patch).hexdigest(),
    }
    (attempt_dir / "workspace-patch.json").write_text(
        json.dumps(patch_receipt), encoding="utf-8"
    )
    process = {
        "job_id": queued["id"],
        "role": "engineering",
        "attempt": 1,
        "returncode": 0,
        "finished_at": "2026-09-05T00:00:00+00:00",
    }
    metadata = {
        "job_id": queued["id"],
        "kind": "engineering",
        "attempt": 1,
        "returncode": 0,
    }
    manifest = {
        "job_id": queued["id"],
        "kind": "engineering",
        "attempt": 1,
        "files": [{
            "name": "prompt.md",
            "sha256": hashlib.sha256(
                prompt.encode("utf-8")
            ).hexdigest(),
        }],
    }
    for name, value in (
        ("process.json", process),
        ("metadata.json", metadata),
        ("transcript.manifest.json", manifest),
    ):
        (attempt_dir / name).write_text(json.dumps(value), encoding="utf-8")
    engineering.retry(attempt, "first", "legacy identity mismatch")
    with store.connect() as con:
        con.execute(
            "UPDATE codex_engineering_jobs SET not_before=? WHERE id=?",
            ("2000-01-01T00:00:00+00:00", queued["id"]),
        )

    def must_not_invoke(*_args, **_kwargs):
        raise AssertionError("a completed action-capable attempt must not repeat")

    orchestrator = CodexOrchestrator(store, settings, invoker=must_not_invoke)
    assert orchestrator.process_one("engineering") is True
    recovered = next(
        item for item in orchestrator.engineering.list_jobs()
        if item["id"] == queued["id"]
    )
    assert recovered["status"] == "retry"
    assert recovered["attempts"] == 2
    assert recovered["result"]["project_context_sha256"] == expected_context
    assert recovered["result"]["recovered_completed_attempt"] == 1
    assert recovered["result"]["observed_workspace"]["after"] == {"head": "after"}
    assert recovered["result"]["continuation"]["attempts_used"] == 2
    assert not (attempt_dir.parent / "attempt-2").exists()
    assert orchestrator.progress.latest()["state"] == "preparing"

    # The valid completed attempt-1 files still exist. An intentionally
    # continued job must perform new work instead of replaying them again and
    # exhausting its last attempt without completing the saved experiment.
    invocations = []
    def continue_work(role, next_job, request):
        invocations.append(next_job["id"])
        assert role == "engineering"
        assert next_job["attempts"] == 3
        assert next_job["result"] == recovered["result"]
        assert '"recovered_completed_attempt": 1' in request["prompt"]
        assert '"attempts_remaining": 1' in request["prompt"]
        store.finish(guarded["id"], "succeeded")
        store.seal_evidence(guarded["id"], "c" * 64)
        completed = engineering_receipt(next_job, expected_context)
        completed["summary"] = "Completed the exact experiment and sealed its evidence."
        return completed

    monkeypatch.setattr(codex_module, "build_project_context",
                        lambda *_: {"sha256": expected_context})
    monkeypatch.setattr(codex_module, "workspace_snapshot",
                        lambda *_: {"head": "after", "status": "", "changed_files": []})
    orchestrator.invoker = continue_work
    _make_continuation_due(store, recovered)
    assert orchestrator.process_one("engineering") is True
    assert invocations == [queued["id"]]
    finished = orchestrator.engineering.list_jobs()[0]
    assert finished["status"] == "succeeded"
    assert finished["attempts"] == 3
    assert finished["result"]["previous_receipt"] == recovered["result"]
    assert "Completed the exact experiment" in finished["result"]["summary"]
    progress = orchestrator.progress.latest()
    assert progress["state"] == "idle"
    assert progress["experiment_id"] == guarded["id"]
    assert "complete and sealed" in progress["summary"]


def test_project_context_carries_fail_closed_deployment_source_guard(tmp_path):
    workspace = tmp_path / "project"
    (workspace / ".git").mkdir(parents=True)
    for relative in PROJECT_CONTEXT_FILES:
        path = workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"context for {relative}\n", encoding="utf-8")

    context = build_project_context(workspace, max_bytes=1_000_000)

    assert context["deployment_source_guard"] == DEPLOYMENT_SOURCE_GUARD
    guard_text = json.dumps(context["deployment_source_guard"])
    assert "Never deploy uncommitted or untracked controller sources" in guard_text
    assert "currently installed on the robot" in guard_text
    assert "Never roll the robot back" in guard_text
    assert "installed-file verification" in guard_text

    offline_context = build_project_context(
        workspace,
        max_bytes=1_000_000,
        lane=ENGINEERING_LANE_OFFLINE,
    )
    assert context["capability_boundary"][
        "physical_robot_via_documented_guarded_paths"
    ] is True
    assert offline_context["capability_boundary"][
        "physical_robot_via_documented_guarded_paths"
    ] is False
    assert offline_context["capability_boundary"]["robot_deployment"] is False
    assert offline_context["capability_boundary"][
        "robot_lab_result_registration"
    ] is True
    assert offline_context["sha256"] != context["sha256"]


def test_project_context_accepts_git_pointer_checkout(tmp_path):
    workspace = tmp_path / "linked-worktree"
    git_dir = tmp_path / "linked-worktree-git"
    subprocess.run(
        [
            "git",
            "init",
            "--quiet",
            f"--separate-git-dir={git_dir}",
            str(workspace),
        ],
        check=True,
    )
    assert (workspace / ".git").is_file()
    for relative in PROJECT_CONTEXT_FILES:
        path = workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"context for {relative}\n", encoding="utf-8")

    context = build_project_context(workspace, max_bytes=1_000_000)

    assert context["documents"][0]["path"] == PROJECT_CONTEXT_FILES[0]


def test_queue_handoff_reuses_active_job_for_same_experiment(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    guarded = store.create(
        {
            "name": "guarded motion",
            "duration_seconds": 1,
            "parameters": {},
            "execution_mode": "external_guarded",
        },
        "test",
    )
    first_advance = store.enqueue_advance(
        "first-queue-kick", "bootstrap", experiment_id=guarded["id"]
    )
    second_advance = store.enqueue_advance(
        "second-queue-kick", "bootstrap", experiment_id=guarded["id"]
    )
    engineering = EngineeringJobStore(store)

    first = engineering.ensure_queue_handoff(first_advance, guarded)
    second = engineering.ensure_queue_handoff(second_advance, guarded)

    assert second["id"] == first["id"]
    assert len(engineering.list_jobs()) == 1


def test_queue_kick_bypasses_unresolved_dependent_advance_without_duplicates(
    tmp_path,
):
    workspace = tmp_path / "project"
    workspace.mkdir()
    store = Store(tmp_path / "lab.sqlite3")
    guarded = store.create(
        {
            "name": "pre-existing guarded plan",
            "duration_seconds": 1,
            "parameters": {},
            "execution_mode": "external_guarded",
        },
        "test",
    )
    submission = store.claim_codex_job(
        "advance", "earlier-advance-worker", lease_seconds=60
    )
    store.finish_codex_job(
        submission["id"],
        "earlier-advance-worker",
        "succeeded",
        lease_token=submission["lease_token"],
    )

    completed = store.create(
        {"name": "new terminal result", "duration_seconds": 1}, "test"
    )
    store.finish(completed["id"], "succeeded")
    store.seal_evidence(completed["id"], "a" * 64)
    analysis = store.claim_codex_job(
        "analysis", "analysis-worker", lease_seconds=60
    )
    dependent = next(
        job
        for job in store.codex_jobs_for_experiment(completed["id"])
        if job["kind"] == "advance"
    )
    assert analysis["status"] == "running"
    assert dependent["status"] == "queued"

    orchestrator = CodexOrchestrator(
        store,
        configured(tmp_path, workspace),
        invoker=lambda *_args, **_kwargs: {},
    )
    kick = orchestrator.ensure_queue_kick()
    assert kick is not None
    assert kick["depends_on_job_id"] is None
    assert kick["experiment_id"] == guarded["id"]
    assert orchestrator.ensure_queue_kick() is None

    assert orchestrator.process_one("advance") is True
    handoffs = [
        job
        for job in orchestrator.engineering.list_jobs()
        if job["experiment_id"] == guarded["id"]
        and job["source_context"]["trigger_kind"] == "queue_handoff"
    ]
    assert len(handoffs) == 1
    assert handoffs[0]["status"] == "queued"
    assert store.get_codex_job(analysis["id"])["status"] == "running"
    assert store.get_codex_job(dependent["id"])["status"] == "queued"
    assert orchestrator.ensure_queue_kick() is None
    assert len(
        [
            job
            for job in store.list_codex_jobs()
            if job["trigger_kind"] == "queue_reconcile"
        ]
    ) == 1


def test_analysis_waits_for_same_experiment_engineering_archive(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    plan = store.create(
        {
            "name": "physical handoff still recording",
            "duration_seconds": 1,
            "parameters": {"robot_motion": True},
            "execution_mode": "external_guarded",
        },
        "test",
    )
    trigger = store.enqueue_advance(
        "physical-handoff", "bootstrap", experiment_id=plan["id"]
    )
    engineering = EngineeringJobStore(store)
    handoff = engineering.ensure_queue_handoff(trigger, plan)
    running = engineering.claim(
        "hardware-worker", lease_seconds=60, lane=ENGINEERING_LANE_HARDWARE
    )
    assert running and running["id"] == handoff["id"]

    store.finish(plan["id"], "succeeded")
    store.seal_evidence(plan["id"], "a" * 64)
    assert store.claim_codex_job(
        "analysis", "analysis-worker", lease_seconds=60
    ) is None

    with store.connect() as connection:
        connection.execute(
            "UPDATE codex_engineering_jobs SET status='succeeded' WHERE id=?",
            (handoff["id"],),
        )
    analysis = store.claim_codex_job(
        "analysis", "analysis-worker", lease_seconds=60
    )
    assert analysis and analysis["experiment_id"] == plan["id"]


def test_non_motion_engineering_progress_continues_same_job_with_receipt_and_budget(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    store = Store(tmp_path / "lab.sqlite3")
    guarded = store.create(
        {
            "name": "guarded motion",
            "duration_seconds": 1,
            "parameters": {},
            "execution_mode": "external_guarded",
        },
        "test",
    )
    orchestrator = CodexOrchestrator(
        store,
        configured(tmp_path, workspace),
        invoker=lambda *_args, **_kwargs: {},
    )

    assert orchestrator.process_one("advance") is True
    first = orchestrator.engineering.claim("engineer", lease_seconds=60)
    assert first is not None
    receipt = {
        "outcome": "changed",
        "summary": "Controller fix tested and committed; deployment remains.",
        "physical_motion_started": False,
        "operator_actions": [],
        "rl_orchestrator_requests": [],
    }
    finished = orchestrator.engineering.finish(
        first,
        "engineer",
        receipt,
    )
    assert finished["status"] == "retry"
    assert finished["finished_at"] is None
    assert finished["result"]["summary"] == receipt["summary"]
    assert finished["result"]["continuation"]["attempts_remaining"] == 2
    assert finished["result"]["continuation"]["completion_only"] is False
    assert orchestrator.engineering.claim("engineer", 60) is None
    assert orchestrator.ensure_queue_kick() is None
    with store.connect() as con:
        con.execute("UPDATE codex_engineering_jobs SET not_before=? WHERE id=?",
                    ("2000-01-01T00:00:00+00:00", first["id"]))
    second = orchestrator.engineering.claim("engineer", 60)
    assert second["id"] == first["id"]
    assert second["attempts"] == 2
    assert second["result"] == finished["result"]
    prompt = engineering_prompt(second, {"sha256": "a" * 64}, {})
    assert receipt["summary"] in prompt
    assert '"attempts": 2' in prompt
    assert "not a new physical-run" in prompt
    assert "Commit and push focused fixes you authored" in prompt
    assert "Do not reset git, force-push" in prompt
    assert len(orchestrator.engineering.list_jobs()) == 1


def _blocked_handoff(orchestrator, store):
    """Drive one guarded plan through a handoff that reports a blocker."""
    assert orchestrator.process_one("advance") is True
    handoff = orchestrator.engineering.claim("engineer", lease_seconds=60)
    orchestrator.engineering.finish(
        handoff,
        "engineer",
        {
            "outcome": "blocked",
            "physical_motion_started": False,
            "operator_actions": ["Inspect the hip."],
            "rl_orchestrator_requests": [],
        },
    )


def _age_handoffs(store, seconds):
    """Backdate every handoff so the 30 s assessment window has elapsed."""
    stamp = datetime.fromtimestamp(
        time.time() - seconds, tz=timezone.utc
    ).isoformat()
    with store.connect() as con:
        con.execute(
            "UPDATE codex_engineering_jobs SET finished_at=?, updated_at=?",
            (stamp, stamp),
        )


def _guarded_orchestrator(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    store = Store(tmp_path / "lab.sqlite3")
    store.create(
        {
            "name": "guarded motion",
            "duration_seconds": 1,
            "parameters": {},
            "execution_mode": "external_guarded",
        },
        "test",
    )
    return store, CodexOrchestrator(
        store,
        configured(tmp_path, workspace),
        invoker=lambda *_args, **_kwargs: {},
    )


def test_a_blocked_handoff_retries_after_the_assessment_window(tmp_path):
    """One stop is a reading, not the end of the campaign.

    A blocked handoff used to park the queue until an operator clicked. It
    must now wait out the 30 s assessment and then take another attempt,
    which re-reads the robot's live health.
    """
    store, orchestrator = _guarded_orchestrator(tmp_path)
    _blocked_handoff(orchestrator, store)

    assert orchestrator.ensure_queue_kick() is None, "must not retry instantly"

    _age_handoffs(store, QUEUE_STOP_ASSESS_S + 1)
    assert orchestrator.ensure_queue_kick() is not None


def test_three_consecutive_blocked_handoffs_stop_the_campaign(tmp_path):
    """Three stops in a row is real, and waits for a human."""
    store, orchestrator = _guarded_orchestrator(tmp_path)
    for attempt in range(QUEUE_STOP_MAX_ATTEMPTS):
        _blocked_handoff(orchestrator, store)
        _age_handoffs(store, QUEUE_STOP_ASSESS_S + 1)
        kick = orchestrator.ensure_queue_kick()
        if attempt < QUEUE_STOP_MAX_ATTEMPTS - 1:
            assert kick is not None, f"attempt {attempt + 1} must be allowed"
        else:
            assert kick is None, "the third stop must hold for an operator"


def _sealed_experiment(store, name="sealed run"):
    item = store.create({"name": name, "duration_seconds": 1}, "test")
    store.finish(item["id"], "succeeded")
    store.seal_evidence(item["id"], "a" * 64)
    return item


def _drain_terminal_jobs(store):
    """Clear the analysis/advance pair a terminal experiment creates."""
    for job in store.list_codex_jobs(500):
        if job["status"] in {"queued", "running", "retry", "awaiting_evidence"}:
            with store.connect() as con:
                con.execute(
                    "UPDATE codex_jobs SET status='succeeded' WHERE id=?",
                    (job["id"],),
                )


def _prompt_queue_note(store, tmp_path, workspace):
    """Build the analysis prompt and return just its queue-depth line."""
    orchestrator = CodexOrchestrator(
        store, configured(tmp_path, workspace),
        invoker=lambda *_a, **_k: {},
    )
    experiment = _sealed_experiment(store, "prompt source")
    prompt = orchestrator._analysis_prompt(
        {"id": "job", "experiment_id": experiment["id"]},
        store.get(experiment["id"]),
        tmp_path / "missing-run-dir",
        {"artifacts": []},
    )
    return prompt


def test_the_card_shows_why_before_it_runs_and_the_finding_after():
    """A queue of method paragraphs reads as work with no reason or result.

    Both the hypothesis and the measured finding are already written and
    stored; neither was rendered anywhere.
    """
    from hexapod_lab.main import experiment_point

    queued = {
        "status": "waiting_for_operator",
        "parameters": {"_automation": {"rationale": (
            "Hypothesis: L4's loop width is a stable per-leg constant. "
            "Concrete open question on the path to smooth joystick walking: "
            "a gait can only compensate per-leg backlash if every stance leg "
            "has a number, and L4 has none."
        )}},
        "what_we_learned": {"status": "pending", "text": "has not run yet"},
    }
    label, point = experiment_point(queued)
    assert label == "Why"
    assert point.startswith("Hypothesis: L4's loop width")

    done = dict(queued, status="succeeded", what_we_learned={
        "text": "The run completed on physical hardware.\n\n"
                "Measured result: L3's loop width is -0.703 deg = exactly "
                "8.0 encoder counts, within-run sd 0.000.",
    })
    label, point = experiment_point(done)
    assert label == "Found"
    # The finding, not the runner-completed preamble.
    assert point.startswith("Measured result:")
    assert "completed on physical hardware" not in point


def test_the_card_falls_back_quietly_without_a_rationale():
    from hexapod_lab.main import experiment_point

    assert experiment_point({"status": "queued", "parameters": {}}) == ("", "")
    assert experiment_point({"status": "queued"}) == ("", "")


def test_the_analyst_is_told_the_queue_depth_and_asked_to_fill_it(tmp_path):
    """A one-item queue leaves the robot idle while the agent thinks.

    Each physical run occupies the robot for a couple of minutes; the
    analysis around it takes far longer. The machinery already accepts
    three follow-ups per analysis, so the prompt must ask for depth
    rather than for a single next step.
    """
    workspace = tmp_path / "project"
    workspace.mkdir()
    store = Store(tmp_path / "lab.sqlite3")
    prompt = _prompt_queue_note(store, tmp_path, workspace)
    assert "Queue depth right now: 0" in prompt
    assert "room for 3 more" in prompt
    assert "MUST return at least one experiment" in prompt
    assert "Return up to 3 experiments, not just one" in prompt
    assert "at most one next physical experiment" not in prompt


def test_a_stocked_queue_is_not_asked_to_pad(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    store = Store(tmp_path / "lab.sqlite3")
    for index in range(3):
        store.create(
            {
                "name": f"queued {index}",
                "duration_seconds": 1,
                "parameters": {},
                "execution_mode": "external_guarded",
            },
            "test",
        )
    prompt = _prompt_queue_note(store, tmp_path, workspace)
    assert "room for 0 more" in prompt
    assert "The queue is stocked" in prompt
    assert "MUST return at least one experiment" not in prompt


def test_an_empty_queue_with_a_ready_robot_asks_for_a_new_proposal(tmp_path):
    """Ten experiments then eight idle hours: an empty queue must self-refill."""
    workspace = tmp_path / "project"
    workspace.mkdir()
    store = Store(tmp_path / "lab.sqlite3")
    source = _sealed_experiment(store)
    orchestrator = CodexOrchestrator(
        store,
        configured(tmp_path, workspace),
        invoker=lambda *_args, **_kwargs: {},
    )
    _drain_terminal_jobs(store)
    orchestrator._robot_guarded_ready = lambda: (True, "")

    job = orchestrator.ensure_queue_refill()
    assert job is not None
    assert job["kind"] == "analysis"
    assert job["trigger_kind"] == "queue_refill"
    assert job["experiment_id"] == source["id"]

    # One sealed result buys one proposal pass, not an unbounded number.
    _drain_terminal_jobs(store)
    assert orchestrator.ensure_queue_refill() is None


def test_a_refill_is_not_requested_while_the_robot_is_not_ready(tmp_path):
    """A dark room or a faulted robot must not buy analysis passes."""
    workspace = tmp_path / "project"
    workspace.mkdir()
    store = Store(tmp_path / "lab.sqlite3")
    _sealed_experiment(store)
    orchestrator = CodexOrchestrator(
        store,
        configured(tmp_path, workspace),
        invoker=lambda *_args, **_kwargs: {},
    )
    _drain_terminal_jobs(store)
    orchestrator._robot_guarded_ready = lambda: (False, "18/18 servos missing")

    assert orchestrator.ensure_queue_refill() is None


def test_a_refill_is_not_requested_while_work_is_queued(tmp_path):
    """The floor only applies to a genuinely empty queue."""
    workspace = tmp_path / "project"
    workspace.mkdir()
    store = Store(tmp_path / "lab.sqlite3")
    _sealed_experiment(store)
    store.create(
        {
            "name": "still waiting",
            "duration_seconds": 1,
            "parameters": {},
            "execution_mode": "external_guarded",
        },
        "test",
    )
    orchestrator = CodexOrchestrator(
        store,
        configured(tmp_path, workspace),
        invoker=lambda *_args, **_kwargs: {},
    )
    _drain_terminal_jobs(store)
    orchestrator._robot_guarded_ready = lambda: (True, "")

    assert orchestrator.ensure_queue_refill() is None


def test_three_exhausted_plans_in_a_row_pause_the_queue(tmp_path):
    """A dark room must not cost three agent attempts per queued plan."""
    workspace = tmp_path / "project"
    workspace.mkdir()
    store = Store(tmp_path / "lab.sqlite3")
    for index in range(QUEUE_STOP_MAX_ATTEMPTS):
        store.create(
            {
                "name": f"guarded motion {index}",
                "duration_seconds": 1,
                "parameters": {},
                "execution_mode": "external_guarded",
            },
            "test",
        )
    orchestrator = CodexOrchestrator(
        store,
        configured(tmp_path, workspace),
        invoker=lambda *_args, **_kwargs: {},
    )

    for _ in range(QUEUE_STOP_MAX_ATTEMPTS):
        for _attempt in range(QUEUE_STOP_MAX_ATTEMPTS):
            assert orchestrator.process_one("advance") is True
            handoff = orchestrator.engineering.claim("engineer", lease_seconds=60)
            assert handoff is not None
            orchestrator.engineering.finish(
                handoff,
                "engineer",
                {
                    "outcome": "blocked",
                    "physical_motion_started": False,
                    "operator_actions": ["The robot is unplugged."],
                    "rl_orchestrator_requests": [],
                },
            )
            _age_handoffs(store, QUEUE_STOP_ASSESS_S + 1)
            orchestrator.ensure_queue_kick()

    assert store.codex_queue_control()["paused"] is True
    assert "Campaign budget spent" in store.codex_queue_control()["reason"]
    assert orchestrator.ensure_queue_kick() is None


def test_the_attempt_budget_does_not_reset_on_a_new_queue_trigger(tmp_path):
    """The retry loop must be able to end itself overnight.

    The handoff job is reused across attempts, so a fresh queue trigger
    cannot hand it a new budget. Without that, a plan the robot keeps
    refusing would retry forever.
    """
    store, orchestrator = _guarded_orchestrator(tmp_path)
    seen = set()
    for _ in range(QUEUE_STOP_MAX_ATTEMPTS):
        assert orchestrator.process_one("advance") is True
        handoff = orchestrator.engineering.claim("engineer", lease_seconds=60)
        assert handoff is not None
        seen.add(handoff["id"])
        orchestrator.engineering.finish(
            handoff,
            "engineer",
            {
                "outcome": "blocked",
                "physical_motion_started": False,
                "operator_actions": ["Inspect the hip."],
                "rl_orchestrator_requests": [],
            },
        )
        _age_handoffs(store, QUEUE_STOP_ASSESS_S + 1)
        orchestrator.ensure_queue_kick()

    assert len(seen) == 1, "attempts must reuse one handoff, not fork budgets"
    job = orchestrator.engineering.list_jobs()[0]
    assert job["status"] == "blocked"
    assert job["attempts"] == job["max_attempts"] == QUEUE_STOP_MAX_ATTEMPTS
    assert orchestrator.ensure_queue_kick() is None
    assert orchestrator.process_one("advance") is False


@pytest.mark.parametrize(
    ("outcome", "physical_motion_started", "operator_actions"),
    [
        ("blocked", False, []),
        ("no_change", False, []),
        ("changed", True, []),
        ("changed", False, ["Remove a physical obstruction."]),
        # A guard trip mid-stand: the robot moved and then stopped.
        ("blocked", True, ["Inspect the hip."]),
    ],
)
def test_queue_reconcile_never_creates_a_new_job_to_reset_motion_or_blocker_budget(
    tmp_path, outcome, physical_motion_started, operator_actions
):
    workspace = tmp_path / "project"
    workspace.mkdir()
    store = Store(tmp_path / "lab.sqlite3")
    store.create(
        {
            "name": "guarded motion",
            "duration_seconds": 1,
            "parameters": {},
            "execution_mode": "external_guarded",
        },
        "test",
    )
    orchestrator = CodexOrchestrator(
        store,
        configured(tmp_path, workspace),
        invoker=lambda *_args, **_kwargs: {},
    )
    assert orchestrator.process_one("advance") is True
    handoff = orchestrator.engineering.claim("engineer", lease_seconds=60)
    orchestrator.engineering.finish(
        handoff,
        "engineer",
        {
            "outcome": outcome,
            "physical_motion_started": physical_motion_started,
            "operator_actions": operator_actions,
            "rl_orchestrator_requests": [],
        },
    )

    assert orchestrator.ensure_queue_kick() is None
    finished = orchestrator.engineering.list_jobs()[0]
    assert finished["status"] == ("blocked" if outcome == "blocked" or operator_actions else "retry")
    assert finished["result"]["operator_actions"] == operator_actions
    if physical_motion_started:
        stopped = outcome == "blocked" or bool(operator_actions)
        # A run that moved and finished cleanly has a result to register, so
        # the next attempt must not move the robot again. A run that moved and
        # then stopped has no result -- it keeps the right to re-run the
        # complete failed step from a verified safe pose.
        assert finished["result"]["continuation"]["completion_only"] is not stopped


@pytest.mark.parametrize("handoff_state", ["queued", "retry"])
def test_reconcile_retires_terminal_queue_handoff_without_rerun(
    tmp_path, handoff_state
):
    store = Store(tmp_path / "lab.sqlite3")
    plan = {
        "name": "guarded motion",
        "description": "bounded run",
        "duration_seconds": 1,
        "parameters": {"runner": "documented"},
        "execution_mode": "external_guarded",
    }
    guarded = store.create(plan, "test")
    advance = store.enqueue_advance(
        "terminal-handoff", "bootstrap", experiment_id=guarded["id"]
    )
    engineering = EngineeringJobStore(store)
    handoff = engineering.ensure_queue_handoff(advance, guarded)
    if handoff_state == "retry":
        claimed = engineering.claim("engineer", lease_seconds=60)
        handoff = engineering.retry(claimed, "engineer", "interrupted")
        assert handoff["status"] == "retry"

    store.import_result(
        {key: value for key, value in plan.items() if key != "execution_mode"},
        "operator",
        "succeeded",
        experiment_id=guarded["id"],
    )
    store.seal_evidence(guarded["id"], "b" * 64)

    assert engineering.reconcile() == 0
    retired = next(
        item for item in engineering.list_jobs() if item["id"] == handoff["id"]
    )
    assert retired["status"] == "succeeded"
    assert retired["result"]["outcome"] == "no_change"
    assert retired["result"]["physical_motion_started"] is False
    assert retired["result"]["robot_contacted"] is False
    assert retired["result"]["network_used"] is False
    assert "already succeeded" in retired["result"]["summary"]
    assert engineering.claim("engineer", lease_seconds=60) is None
    assert any(
        event["kind"] == "engineering_handoff_retired"
        for event in store.events(guarded["id"])
    )


def test_claim_defensively_skips_terminal_queue_handoff_before_reconcile(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    plan = {
        "name": "already completed guarded motion",
        "duration_seconds": 1,
        "parameters": {},
        "execution_mode": "external_guarded",
    }
    guarded = store.create(plan, "test")
    advance = store.enqueue_advance(
        "stale-terminal-handoff", "bootstrap", experiment_id=guarded["id"]
    )
    engineering = EngineeringJobStore(store)
    engineering.ensure_queue_handoff(advance, guarded)
    store.import_result(
        {key: value for key, value in plan.items() if key != "execution_mode"},
        "operator",
        "cancelled",
        experiment_id=guarded["id"],
    )
    store.seal_evidence(guarded["id"], "b" * 64)

    assert engineering.claim("engineer", lease_seconds=60) is None


def _claimed_guarded_job(tmp_path, *, max_attempts=3):
    store = Store(tmp_path / "lab.sqlite3")
    plan = store.create({"name": "bounded walk", "duration_seconds": 1,
                         "parameters": {}, "execution_mode": "external_guarded"}, "test")
    advance = next(j for j in store.list_codex_jobs() if j["kind"] == "advance")
    engineering = EngineeringJobStore(store)
    engineering.ensure_queue_handoff(advance, plan, max_attempts=max_attempts)
    return store, plan, engineering, engineering.claim("engineer", 60)


def _make_continuation_due(store, job):
    with store.connect() as con:
        con.execute("UPDATE codex_engineering_jobs SET not_before=? WHERE id=?",
                    ("2000-01-01T00:00:00+00:00", job["id"]))


@pytest.mark.parametrize("terminal_status", ["succeeded", "failed", "cancelled"])
def test_queue_handoff_success_requires_exact_terminal_sealed_experiment(tmp_path, terminal_status):
    store, plan, engineering, job = _claimed_guarded_job(tmp_path)
    receipt = engineering_receipt(job, "a" * 64)
    store.finish(plan["id"], terminal_status)
    unsealed = engineering.finish(job, "engineer", receipt)
    assert unsealed["status"] == "retry"
    assert unsealed["result"]["continuation"]["completion_only"] is True
    assert engineering.reconcile() == 0
    assert engineering.list_jobs()[0]["status"] == "retry"
    _make_continuation_due(store, job)
    continuation = engineering.claim("engineer", 60)
    assert continuation["id"] == job["id"]
    assert continuation["continuation"]["completion_only"] is True
    assert continuation["continuation"]["experiment_status"] == terminal_status
    store.seal_evidence(plan["id"], "b" * 64)
    completed = engineering.finish(continuation, "engineer", receipt)
    assert completed["status"] == "succeeded"
    assert completed["result"]["previous_receipt"] == unsealed["result"]


@pytest.mark.parametrize("outcome,operator_actions,status", [
    ("changed", [], "dead"),
    ("no_change", [], "dead"),
    ("blocked", [], "blocked"),
    ("changed", ["Clear the observed physical obstruction."], "blocked"),
])
def test_unfinished_handoff_exhaustion_and_hazards_cannot_get_a_fresh_budget(
    tmp_path, outcome, operator_actions, status
):
    store, plan, engineering, job = _claimed_guarded_job(tmp_path, max_attempts=1)
    receipt = engineering_receipt(job, "a" * 64)
    receipt.update(outcome=outcome, operator_actions=operator_actions)
    completed = engineering.finish(job, "engineer", receipt)
    assert completed["status"] == status
    assert completed["finished_at"]
    assert completed["result"]["operator_actions"] == operator_actions
    assert completed["result"]["continuation"]["attempts_remaining"] == 0
    assert engineering.claim("engineer", 60) is None
    another_advance = store.enqueue_advance("new-trigger", "test", experiment_id=plan["id"])
    reused = engineering.ensure_queue_handoff(another_advance, plan)
    assert reused["id"] == job["id"]
    assert reused["status"] == status
    assert reused["attempts"] == reused["max_attempts"] == 1
    assert len(engineering.list_jobs()) == 1


def test_physical_attempt_receipt_survives_evidence_only_continuations(tmp_path):
    store, plan, engineering, job = _claimed_guarded_job(tmp_path)
    receipt = engineering_receipt(job, "a" * 64)
    receipt.update(physical_motion_started=True, robot_contacted=True,
                   summary="Bounded motion stopped; result upload remains.")
    first = engineering.finish(job, "engineer", receipt)
    assert first["result"]["continuation"]["completion_only"] is True
    _make_continuation_due(store, job)
    second = engineering.claim("engineer", 60)
    next_receipt = engineering_receipt(second, "a" * 64)
    next_receipt.update(physical_motion_started=False, summary="Evidence uploaded; sealing remains.")
    continued = engineering.finish(second, "engineer", next_receipt)
    assert continued["result"]["continuation"]["physical_motion_started"] is True
    assert continued["result"]["continuation"]["completion_only"] is True
    assert continued["result"]["previous_receipt"] == first["result"]
    store.finish(plan["id"], "failed")
    store.seal_evidence(plan["id"], "c" * 64)
    engineering.reconcile()
    retired = engineering.list_jobs()[0]
    assert retired["status"] == "succeeded"
    assert retired["result"]["previous_receipt"] == continued["result"]
    assert engineering.claim("engineer", 60) is None


@pytest.mark.parametrize("invalid", ["owner", "expired", "reclaimed"])
def test_finish_cannot_overwrite_a_lost_engineering_lease(tmp_path, invalid):
    store, _plan, engineering, job = _claimed_guarded_job(tmp_path)
    receipt = engineering_receipt(job, "a" * 64)
    owner = "engineer"
    if invalid == "owner":
        owner = "other"
    elif invalid == "expired":
        with store.connect() as con:
            con.execute("UPDATE codex_engineering_jobs SET lease_expires_at=? WHERE id=?",
                        ("2000-01-01T00:00:00+00:00", job["id"]))
    else:
        engineering.finish(job, owner, receipt)
        _make_continuation_due(store, job)
        replacement = engineering.claim(owner, 60)
        assert replacement["lease_token"] != job["lease_token"]
    before = engineering.list_jobs()[0]
    with pytest.raises(EngineeringLaneError, match="lease is no longer owned"):
        engineering.finish(job, owner, receipt)
    assert engineering.list_jobs()[0] == before
    assert engineering.list_rl_requests() == []


@pytest.mark.parametrize("outcome,expected_status", [("blocked", "blocked"), ("no_change", "dead")])
def test_blocked_or_exhausted_engineering_publishes_progress_with_empty_next_steps(
    tmp_path, outcome, expected_status
):
    store, plan, _engineering, job = _claimed_guarded_job(tmp_path, max_attempts=1)
    orchestrator = CodexOrchestrator(store, configured(tmp_path, tmp_path))
    orchestrator.owner = "engineer"
    receipt = engineering_receipt(job, "a" * 64)
    receipt.update(outcome=outcome, next_steps=[], operator_actions=[])
    orchestrator._finish_engineering(job, receipt)
    assert orchestrator.engineering.list_jobs()[0]["status"] == expected_status
    progress = orchestrator.progress.latest()
    assert progress is not None
    assert progress["state"] == "blocked"
    assert progress["experiment_id"] == plan["id"]
    assert progress["next_action"].strip()


def test_engineering_invoke_uses_real_workspace_tools_environment_and_timeout(
    tmp_path, monkeypatch
):
    workspace = tmp_path / "isolated-checkout"
    workspace.mkdir()
    captured = {}

    class FakeStdin:
        """Minimal writable stdin: the orchestrator owns it from a writer thread."""

        def __init__(self):
            self.data = b""

        def write(self, payload):
            self.data += payload
            return len(payload)

        def flush(self):
            pass

        def close(self):
            pass

    class FakeProcess:
        pid = 424242
        returncode = 0

        def __init__(self, command, **kwargs):
            captured["command"] = command
            captured["env"] = kwargs["env"]
            self.stdin = FakeStdin()
            output_index = command.index("-o") + 1
            Path(command[output_index]).write_text('{"ok": true}\n')

        def wait(self, timeout=None):
            captured["wait_timeout"] = timeout
            return self.returncode

        def poll(self):
            return self.returncode

    monkeypatch.setattr(codex_module.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(codex_module, "_terminate_deadline_wrapper", lambda *_a, **_k: True)
    monkeypatch.setenv("HEXAPOD_LAB_TOKEN", "mcp-only-lab-token")
    monkeypatch.setenv("HEXAPOD_ORCHESTRATOR_TOKEN", "mcp-only-rl-token")
    monkeypatch.setenv("SSH_AUTH_SOCK", "/tmp/hardware-agent.sock")
    monkeypatch.setenv("KUBECONFIG", "/tmp/hardware-kubeconfig")
    settings = configured(tmp_path, workspace, codex_bin=Path("/opt/codex"))
    orchestrator = CodexOrchestrator(Store(tmp_path / "lab.sqlite3"), settings)
    # This transport fixture supplies synthetic IDs; durable pause/lease
    # admission is exercised with real jobs in test_lab_engineering_pause_*.
    monkeypatch.setattr(orchestrator.engineering, "execution_revocation_reason", lambda *_a: None)
    monkeypatch.setattr(orchestrator, "_finalize_transcript", lambda *_a, **_k: None)

    result = orchestrator._invoke(
        "engineering",
        {"id": "engineering-job", "attempts": 1, "experiment_id": "experiment"},
        "Make one offline change.",
        {"type": "object"},
    )

    assert result == {"ok": True}
    command = captured["command"]
    assert command[command.index("--ask-for-approval") + 1] == "never"
    assert command[command.index("--sandbox") + 1] == "danger-full-access"
    assert "--search" in command
    shell_policy = next(
        command[index + 1]
        for index, value in enumerate(command[:-1])
        if value == "-c" and command[index + 1].startswith(
            "shell_environment_policy.exclude="
        )
    )
    assert "HEXAPOD_LAB_TOKEN" in shell_policy
    assert "HEXAPOD_ORCHESTRATOR_TOKEN" in shell_policy
    assert "--ignore-user-config" not in command
    assert "--strict-config" in command
    assert "--ignore-rules" not in command
    assert command[command.index("-C") + 1] == str(workspace.resolve())
    assert captured["env"]["HOME"] == __import__("os").environ["HOME"]
    assert captured["env"]["PWD"] == str(workspace.resolve())
    # Codex itself receives the two bearer values so its configured MCP
    # clients can authenticate. The command-line shell policy above removes
    # them from every model-generated shell process.
    assert captured["env"]["HEXAPOD_LAB_TOKEN"] == "mcp-only-lab-token"
    assert captured["env"]["HEXAPOD_ORCHESTRATOR_TOKEN"] == "mcp-only-rl-token"
    assert captured["env"]["SSH_AUTH_SOCK"] == "/tmp/hardware-agent.sock"
    assert captured["env"]["KUBECONFIG"] == "/tmp/hardware-kubeconfig"
    assert captured["env"]["HEXAPOD_ENGINEERING_LANE"] == "hardware"
    process_state = json.loads(
        (settings.data_dir / "codex-runs" / "engineering-job" / "attempt-1" / "process.json").read_text()
    )
    assert process_state["deadline_seconds"] == 123
    assert process_state["runner_identity"]["runner_path"] == "/opt/codex"
    assert process_state["runner_identity"]["capture_errors"] == [
        "binary capture: FileNotFoundError"
    ]
    metadata = json.loads(
        (settings.data_dir / "codex-runs" / "engineering-job" / "attempt-1" / "metadata.json").read_text()
    )
    assert metadata["runner_identity"] == process_state["runner_identity"]

    captured.clear()
    offline = orchestrator._invoke(
        "engineering",
        {"id": "offline-job", "attempts": 1, "experiment_id": "experiment"},
        "Run the offline replay in parallel.",
        {"type": "object"},
        engineering_workdir=workspace,
        engineering_lane=ENGINEERING_LANE_OFFLINE,
    )

    assert offline == {"ok": True}
    offline_command = captured["command"]
    assert offline_command[offline_command.index("--sandbox") + 1] == "danger-full-access"
    assert "sandbox_workspace_write.network_access=true" not in offline_command
    assert "--search" in offline_command
    assert captured["env"]["HEXAPOD_ENGINEERING_LANE"] == "offline"
    assert "SSH_AUTH_SOCK" not in captured["env"]
    assert "KUBECONFIG" not in captured["env"]
    assert captured["env"]["HEXAPOD_LAB_TOKEN"] == "mcp-only-lab-token"
    assert captured["env"]["HEXAPOD_ORCHESTRATOR_TOKEN"] == "mcp-only-rl-token"
