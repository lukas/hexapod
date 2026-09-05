from pathlib import Path

from hexapod_lab.codex_orchestrator import CodexOrchestrator
from hexapod_lab.config import Settings
from hexapod_lab.db import Store


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
