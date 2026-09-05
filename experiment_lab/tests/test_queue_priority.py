from pathlib import Path

from hexapod_lab.codex_orchestrator import CodexOrchestrator
from hexapod_lab.config import Settings
from hexapod_lab.db import Store
from hexapod_lab.engineering_lane import (
    ENGINEERING_LANE_HARDWARE,
    ENGINEERING_LANE_OFFLINE,
)


def test_explicit_next_plan_preserves_older_work_and_fifo_ties(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")

    def add(name, priority=None):
        return store.create({
            "name": name,
            "duration_seconds": 1,
            "execution_mode": "external_guarded",
            "parameters": {} if priority is None else {"queue_priority": priority},
        }, "operator")

    older = add("L5 measurement")
    add("Metric repeat")
    malformed = add("String priority is not a priority", "999")
    first = add("Repair timing first", 10)
    second = add("Later urgent plan", 10)
    assert store.next_external_experiment()["id"] == first["id"]
    store.finish(first["id"], "succeeded")
    assert store.next_external_experiment()["id"] == second["id"]
    store.finish(second["id"], "succeeded")
    assert store.next_external_experiment()["id"] == older["id"]
    assert store.get(older["id"])["status"] == "waiting_for_operator"
    assert store.get(malformed["id"])["status"] == "waiting_for_operator"


def test_hardware_resource_class_precedes_offline_priority(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    offline = store.create({
        "name": "urgent offline replay",
        "duration_seconds": 1,
        "execution_mode": "external_guarded",
        "parameters": {
            "simulation_only": True,
            "robot_motion": False,
            "queue_priority": 999,
        },
    }, "operator")
    hardware = store.create({
        "name": "low-priority bounded hardware check",
        "duration_seconds": 1,
        "execution_mode": "external_guarded",
        "parameters": {"robot_motion": True, "queue_priority": -999},
    }, "operator")

    assert store.next_external_experiment()["id"] == hardware["id"]
    store.finish(hardware["id"], "succeeded")
    assert store.next_external_experiment()["id"] == offline["id"]


def test_conflicting_motion_flags_stay_in_hardware_resource_class(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    conflicting = store.create({
        "name": "malformed but motion-capable plan",
        "duration_seconds": 1,
        "execution_mode": "external_guarded",
        "parameters": {
            "simulation_only": True,
            "robot_motion": True,
            "queue_priority": -999,
        },
    }, "legacy-import")
    offline = store.create({
        "name": "offline replay",
        "duration_seconds": 1,
        "execution_mode": "external_guarded",
        "parameters": {
            "simulation_only": True,
            "robot_motion": False,
            "queue_priority": 999,
        },
    }, "operator")

    assert store.next_external_experiment()["id"] == conflicting["id"]
    source_job_id = next(
        job["id"] for job in store.list_codex_jobs()
        if job["experiment_id"] == conflicting["id"]
    )
    store.pause_codex_queue(source_job_id, "inspection required")
    claimed = store.claim_codex_job("advance", "worker", lease_seconds=60)
    assert claimed is not None
    assert claimed["experiment_id"] == offline["id"]


def test_each_submission_creates_its_own_parallel_resource_handoff(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    settings = Settings(
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
        codex_engineering_workdir=Path(tmp_path),
    )
    orchestrator = CodexOrchestrator(store, settings, invoker=lambda *_: {})
    hardware = store.create({
        "name": "hardware plan",
        "duration_seconds": 1,
        "execution_mode": "external_guarded",
        "parameters": {"robot_motion": True, "queue_priority": 100},
    }, "operator")
    offline = store.create({
        "name": "offline plan",
        "duration_seconds": 1,
        "execution_mode": "external_guarded",
        "parameters": {"simulation_only": True, "robot_motion": False},
    }, "operator")

    assert orchestrator.process_one("advance") is True
    assert orchestrator.process_one("advance") is True
    handoffs = [
        job for job in orchestrator.engineering.list_jobs()
        if job["source_context"]["trigger_kind"] == "queue_handoff"
    ]
    assert {job["experiment_id"] for job in handoffs} == {
        hardware["id"], offline["id"],
    }
    assert orchestrator.engineering.claim(
        "hardware", 60, lane=ENGINEERING_LANE_HARDWARE
    )["experiment_id"] == hardware["id"]
    assert orchestrator.engineering.claim(
        "offline", 60, lane=ENGINEERING_LANE_OFFLINE
    )["experiment_id"] == offline["id"]


def test_paused_physical_queue_still_hands_off_explicit_offline_work(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    physical = store.create({
        "name": "physical plan",
        "duration_seconds": 1,
        "execution_mode": "external_guarded",
        "parameters": {"robot_motion": True},
    }, "operator")
    offline = store.create({
        "name": "offline plan",
        "duration_seconds": 1,
        "execution_mode": "external_guarded",
        "parameters": {"simulation_only": True, "robot_motion": False},
    }, "operator")
    advances = {
        job["experiment_id"]: job
        for job in store.list_codex_jobs()
        if job["kind"] == "advance"
    }
    store.pause_codex_queue(
        advances[physical["id"]]["id"], "physical inspection required"
    )

    claimed = store.claim_codex_job("advance", "worker", lease_seconds=60)
    assert claimed is not None
    assert claimed["experiment_id"] == offline["id"]


def test_blocked_handoff_yields_to_next_plan_then_resumes_same_job(tmp_path):
    store = Store(tmp_path / "lab.sqlite3")
    settings = Settings(
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
        codex_engineering_workdir=Path(tmp_path),
    )

    def no_model_call(*_args, **_kwargs):
        raise AssertionError("advance should hand plans to engineering directly")

    orchestrator = CodexOrchestrator(store, settings, invoker=no_model_call)
    first = store.create({
        "name": "temporarily blocked priority plan",
        "duration_seconds": 1,
        "execution_mode": "external_guarded",
        "parameters": {"queue_priority": 10},
    }, "operator")
    assert orchestrator.process_one("advance") is True
    first_advance = next(
        job for job in store.codex_jobs_for_experiment(first["id"])
        if job["kind"] == "advance"
    )
    assert first_advance["result"]["selected_experiment_id"] == first["id"]
    first_job = orchestrator.engineering.claim(orchestrator.owner, 60)
    blocked = orchestrator.engineering.finish(first_job, orchestrator.owner, {
        "outcome": "blocked",
        "summary": "A concrete fixture correction is still required.",
        "operator_actions": ["Correct the observed fixture placement."],
        "rl_orchestrator_requests": [],
        "physical_motion_started": False,
    })
    assert blocked["status"] == "blocked"

    second = store.create({
        "name": "independent runnable plan",
        "duration_seconds": 1,
        "execution_mode": "external_guarded",
        "parameters": {},
    }, "operator")
    assert store.next_external_experiment()["id"] == second["id"]

    # A later pause/resume for another experiment is not permission to retry
    # this blocked handoff, even though it is the latest global queue control.
    unrelated_source = store.enqueue_advance(
        "unrelated-inspection", "test", experiment_id=second["id"]
    )
    with store.connect() as con:
        con.execute(
            "UPDATE codex_jobs SET status='succeeded',finished_at=updated_at "
            "WHERE id=?",
            (unrelated_source["id"],),
        )
    store.pause_codex_queue(
        unrelated_source["id"],
        "Independent plan needs inspection",
        created_by="test",
    )
    unrelated_resume = store.resume_codex_queue(
        "Independent plan was inspected", created_by="test"
    )
    assert unrelated_resume["resumed"] is True
    assert store.next_external_experiment()["id"] == second["id"]

    assert orchestrator.process_one("advance") is True
    second_advance = next(
        job for job in store.codex_jobs_for_experiment(second["id"])
        if job["kind"] == "advance"
    )
    assert second_advance["result"]["selected_experiment_id"] == second["id"]
    assert store.get(first["id"])["status"] == "waiting_for_operator"
    assert next(
        job for job in orchestrator.engineering.list_jobs()
        if job["id"] == first_job["id"]
    )["status"] == "blocked"

    # A later explicit inspection/resume receipt makes the original priority
    # plan runnable again. Its existing handoff and attempt budget are reused.
    store.pause_codex_queue(
        first_advance["id"], "Fixture correction must be acknowledged", created_by="test"
    )
    resume = store.resume_codex_queue(
        "Fixture placement was corrected and inspected", created_by="test"
    )
    assert resume["resumed"] is True
    assert store.next_external_experiment()["id"] == first["id"]
    assert orchestrator.process_one("advance") is True
    resumed = next(
        job for job in orchestrator.engineering.list_jobs()
        if job["id"] == first_job["id"]
    )
    assert resumed["status"] == "retry"
    assert resumed["attempts"] == 1
    assert resumed["max_attempts"] == first_job["max_attempts"]
    assert resumed["result"]["queue_resume_receipt"]["sequence"] == resume["sequence"]
