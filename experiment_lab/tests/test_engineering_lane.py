import hashlib
import json
from pathlib import Path
import subprocess
import pytest

import hexapod_lab.codex_orchestrator as codex_module
from hexapod_lab.codex_orchestrator import CodexOrchestrator
from hexapod_lab.config import Settings
from hexapod_lab.db import Store
from hexapod_lab.engineering_lane import (
    DEPLOYMENT_SOURCE_GUARD,
    DisabledRLDispatcher,
    EngineeringJobStore,
    EngineeringLaneError,
    PROJECT_CONTEXT_FILES,
    build_project_context,
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


def succeeded_analysis(store):
    experiment = store.create(
        {"name": "measured gait", "duration_seconds": 1, "parameters": {}},
        "test",
    )
    store.finish(experiment["id"], "succeeded")
    store.seal_evidence(experiment["id"], "a" * 64)
    analysis = store.claim_codex_job("analysis", "analyzer", lease_seconds=60)
    assert analysis is not None
    result = {
        "schema_version": 1,
        "experiment_id": experiment["id"],
        "evidence_manifest_sha256": "a" * 64,
        "verdict": "pass",
        "safety_disposition": "clear",
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


def test_succeeded_analysis_reconciles_once_and_rl_outbox_is_validated(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    experiment, analysis = succeeded_analysis(store)
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
    experiment, _analysis = succeeded_analysis(store)
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
    assert "shared workspace, not as deployment" in normalized_prompt
    assert "latest sealed successful physical-hardware provenance" in normalized_prompt
    assert "clean dedicated worktree" in normalized_prompt
    assert "documented validated integration branch" in normalized_prompt
    assert "staged and remote deploy-manifest hashes must agree" in normalized_prompt


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


def test_retry_recovers_a_completed_prior_engineering_attempt_without_reinvoking(
    tmp_path,
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
    assert recovered["status"] == "succeeded"
    assert recovered["attempts"] == 2
    assert recovered["result"]["project_context_sha256"] == expected_context
    assert recovered["result"]["recovered_completed_attempt"] == 1
    assert recovered["result"]["observed_workspace"]["after"] == {"head": "after"}
    assert not (attempt_dir.parent / "attempt-2").exists()


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
    assert "latest sealed successful physical-hardware provenance" in guard_text
    assert "currently installed on the robot" in guard_text
    assert "linux_control/deploy_manifest.sh" in guard_text
    assert "newer than or differs" in guard_text
    assert "missing, incomplete, or mismatched" in guard_text


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


def test_non_motion_engineering_progress_gets_one_serialized_continuation(tmp_path):
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
    orchestrator.engineering.finish(
        first,
        "engineer",
        {
            "outcome": "changed",
            "physical_motion_started": False,
            "operator_actions": [],
            "rl_orchestrator_requests": [],
        },
    )

    continuation = orchestrator.ensure_queue_kick()
    assert continuation is not None
    assert continuation["experiment_id"] == guarded["id"]
    assert continuation["trigger_kind"] == "queue_reconcile"
    # The deterministic marker makes concurrent/periodic reconciliation
    # idempotent while this continuation is waiting.
    assert orchestrator.ensure_queue_kick() is None
    assert orchestrator.process_one("advance") is True
    jobs = [
        item for item in orchestrator.engineering.list_jobs()
        if item["experiment_id"] == guarded["id"]
    ]
    assert len(jobs) == 2
    assert jobs[-1]["status"] == "queued"
    assert orchestrator.ensure_queue_kick() is None


@pytest.mark.parametrize(
    ("outcome", "physical_motion_started", "operator_actions"),
    [
        ("blocked", False, []),
        ("no_change", False, []),
        ("changed", True, []),
        ("changed", False, ["Remove a physical obstruction."]),
    ],
)
def test_queue_reconcile_never_retries_a_blocker_operator_action_or_motion(
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

    assert engineering.claim("engineer", lease_seconds=60) is None


def test_engineering_invoke_uses_real_workspace_tools_environment_and_timeout(
    tmp_path, monkeypatch
):
    workspace = tmp_path / "isolated-checkout"
    workspace.mkdir()
    captured = {}

    class FakeProcess:
        pid = 424242
        returncode = 0

        def __init__(self, command, **kwargs):
            captured["command"] = command
            captured["env"] = kwargs["env"]
            output_index = command.index("-o") + 1
            Path(command[output_index]).write_text('{"ok": true}\n')

        def communicate(self, _payload, timeout):
            captured["communicate_timeout"] = timeout
            return b"", b""

        def poll(self):
            return self.returncode

    monkeypatch.setattr(codex_module.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(codex_module, "_terminate_deadline_wrapper", lambda *_a, **_k: True)
    monkeypatch.setenv("HEXAPOD_LAB_TOKEN", "mcp-only-lab-token")
    monkeypatch.setenv("HEXAPOD_ORCHESTRATOR_TOKEN", "mcp-only-rl-token")
    settings = configured(tmp_path, workspace, codex_bin=Path("/opt/codex"))
    orchestrator = CodexOrchestrator(Store(tmp_path / "lab.sqlite3"), settings)
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
    process_state = json.loads(
        (settings.data_dir / "codex-runs" / "engineering-job" / "attempt-1" / "process.json").read_text()
    )
    assert process_state["deadline_seconds"] == 123
