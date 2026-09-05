import uuid

import pytest

from hexapod_lab.db import Store, utcnow
from hexapod_lab.engineering_lane import EngineeringJobStore


def _receipt(**changes):
    return {"outcome": "no_change", "summary": "Unfinished work",
            "rl_orchestrator_requests": [], "operator_actions": [],
            "physical_motion_started": False, **changes}


def _plan(store, engineering, *, parameters=None, max_attempts=3):
    plan = store.create({"name": "bounded plan", "duration_seconds": 1,
                         "parameters": parameters or {},
                         "execution_mode": "external_guarded"}, "test")
    advance = store.enqueue_advance(uuid.uuid4().hex, "test", experiment_id=plan["id"])
    job = engineering.ensure_queue_handoff(advance, plan, max_attempts)
    return plan, advance, job


def _setup(tmp_path, **kwargs):
    store = Store(tmp_path / "lab.sqlite3")
    engineering = EngineeringJobStore(store)
    plan, advance, _ = _plan(store, engineering, **kwargs)
    return store, engineering, plan, advance, engineering.claim("owner", 60)


def _resume(store, plan):
    source = store.enqueue_advance(uuid.uuid4().hex, "test", experiment_id=plan["id"])
    # The API requires the job that paused the queue to have finished.
    with store.connect() as con:
        con.execute("UPDATE codex_jobs SET status='succeeded',finished_at=? WHERE kind='advance'",
                    (utcnow(),))
    store.pause_codex_queue(source["id"], "Observed blocker", created_by="test")
    return store.resume_codex_queue("Current evidence clears the blocker", created_by="test")


def _due(store, job):
    with store.connect() as con:
        con.execute("UPDATE codex_engineering_jobs SET not_before=? WHERE id=?",
                    ("2000-01-01T00:00:00+00:00", job["id"]))


@pytest.mark.parametrize("physical_motion_started", [False, True])
def test_blocked_handoff_needs_new_audited_resume_and_keeps_budget(tmp_path, physical_motion_started):
    store, engineering, plan, advance, job = _setup(tmp_path)
    old_resume = _resume(store, plan)
    blocked = engineering.finish(job, "owner", _receipt(
        outcome="blocked", physical_motion_started=physical_motion_started))
    assert blocked["result"]["blocked_control_sequence"] == old_resume["sequence"]
    for _ in range(2):
        assert engineering.ensure_queue_handoff(advance, plan, 99)["status"] == "blocked"
        assert engineering.claim("owner", 60) is None
    assert store.resume_codex_queue("Repeated request", created_by="test")["resumed"] is False
    assert engineering.ensure_queue_handoff(advance, plan)["status"] == "blocked"

    resume = _resume(store, plan)
    resumed = engineering.ensure_queue_handoff(advance, plan, 99)
    assert resumed["id"] == job["id"]
    assert resumed["attempts"] == 1 and resumed["max_attempts"] == 3
    assert resumed["source_context_sha256"] == job["source_context_sha256"]
    assert resumed["result"]["queue_resume_receipt"]["sequence"] == resume["sequence"]
    assert resumed["result"]["queue_resume_receipt"]["previous_finished_at"] == blocked["finished_at"]
    second = engineering.claim("owner", 60)
    assert second["attempts"] == 2
    assert second["continuation"]["completion_only"] is physical_motion_started
    engineering.finish(second, "owner", _receipt(outcome="blocked"))
    assert engineering.ensure_queue_handoff(advance, plan)["status"] == "blocked"
    assert len(engineering.list_jobs()) == 1


def test_new_sequence_with_old_timestamp_does_not_release_legacy_blocker(tmp_path):
    store, engineering, plan, advance, job = _setup(tmp_path)
    engineering.finish(job, "owner", _receipt(outcome="blocked"))
    resume = _resume(store, plan)
    with store.connect() as con:
        con.execute("UPDATE codex_queue_controls SET created_at=? WHERE sequence=?",
                    ("2000-01-01T00:00:00+00:00", resume["sequence"]))
    assert engineering.ensure_queue_handoff(advance, plan)["status"] == "blocked"
    assert engineering.claim("owner", 60) is None


def test_later_pause_prevents_older_resume_being_consumed(tmp_path):
    store, engineering, plan, advance, job = _setup(tmp_path)
    engineering.finish(job, "owner", _receipt(outcome="blocked"))
    resume = _resume(store, plan)
    store.pause_codex_queue(resume["advance_job_id"], "New blocker")
    assert engineering.ensure_queue_handoff(advance, plan)["status"] == "blocked"


@pytest.mark.parametrize("outcome,status", [("blocked", "blocked"), ("no_change", "dead")])
def test_resume_cannot_reset_exhausted_budget(tmp_path, outcome, status):
    store, engineering, plan, advance, job = _setup(tmp_path, max_attempts=1)
    engineering.finish(job, "owner", _receipt(outcome=outcome))
    _resume(store, plan)
    reused = engineering.ensure_queue_handoff(advance, plan, 99)
    assert (reused["id"], reused["status"], reused["attempts"], reused["max_attempts"]) == (
        job["id"], status, 1, 1)
    assert engineering.claim("owner", 60) is None


@pytest.mark.parametrize("completion_only", [False, True])
def test_retry_records_whether_invocation_might_have_moved(tmp_path, completion_only):
    store, engineering, _plan_value, _advance, job = _setup(tmp_path)
    first = engineering.retry(job, "owner", "Process output malformed", completion_only=completion_only)
    assert first["result"]["retry_receipt"]["completion_only"] is completion_only
    _due(store, job)
    claimed = engineering.claim("owner", 60)
    assert claimed["attempts"] == 2
    assert bool(claimed.get("continuation", {}).get("completion_only")) is completion_only
    finished = engineering.finish(claimed, "owner", _receipt())
    assert finished["result"]["previous_receipt"] == first["result"]
    assert finished["result"]["continuation"]["completion_only"] is completion_only


@pytest.mark.parametrize(
    "parameters, completion_only",
    [
        ({"simulation_only": False, "robot_motion": False}, False),
        ({"simulation_only": False, "robot_motion": True}, True),
        ({"simulation_only": False}, True),
    ],
)
def test_expired_unreceipted_attempt_uses_declared_robot_motion(
    tmp_path, parameters, completion_only
):
    store, engineering, _plan_value, _advance, job = _setup(
        tmp_path, parameters=parameters
    )
    assert engineering.expire_lease(job["id"], "Child exited without a receipt")
    assert engineering.recover_expired() == 1
    claimed = engineering.claim("owner", 60)
    assert claimed["attempts"] == 2
    assert bool(claimed.get("continuation", {}).get("completion_only")) is completion_only
    if completion_only:
        assert engineering.list_jobs()[0]["result"]["continuation"]["completion_only"] is True


def test_expired_later_attempt_does_not_trust_an_older_no_motion_receipt(tmp_path):
    store, engineering, _plan_value, _advance, job = _setup(tmp_path)
    engineering.finish(job, "owner", _receipt())
    _due(store, job)
    second = engineering.claim("owner", 60)
    assert second["continuation"]["completion_only"] is False
    engineering.expire_lease(second["id"], "Unknown second attempt outcome")
    engineering.recover_expired()
    third = engineering.claim("owner", 60)
    assert third["attempts"] == 3
    assert third["continuation"]["completion_only"] is True


@pytest.mark.parametrize("invalid_priority", [None, "100", 100.5, True])
def test_integer_priority_selects_repair_without_rewriting_retained_jobs(tmp_path, invalid_priority):
    store = Store(tmp_path / "lab.sqlite3")
    engineering = EngineeringJobStore(store)
    _, _, retained = _plan(store, engineering, parameters={"queue_priority": invalid_priority})
    _, _, repair = _plan(store, engineering, parameters={"queue_priority": 10})
    claimed = engineering.claim("owner", 60)
    assert claimed["id"] == repair["id"]
    saved = next(j for j in engineering.list_jobs() if j["id"] == retained["id"])
    assert saved["status"] == "queued" and saved["attempts"] == 0
