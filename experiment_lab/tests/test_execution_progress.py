from datetime import datetime, timedelta, timezone
import sqlite3

import pytest
from pydantic import ValidationError

from hexapod_lab import execution_progress
from hexapod_lab.db import Store
from hexapod_lab.execution_progress import ExecutionProgressIn, ExecutionProgressStore, execution_summary


def payload(**changes):
    return {"state": "preparing", "summary": "Verifying the timing fix", "next_action": "Run the offline timing tests", **changes}


@pytest.fixture
def reports(tmp_path, monkeypatch):
    clock = [datetime(2026, 9, 5, 10, tzinfo=timezone.utc)]
    monkeypatch.setattr(execution_progress, "_utcnow", lambda: clock[0])
    store = Store(tmp_path / "lab.sqlite3")
    return ExecutionProgressStore(store), store, clock


def test_reports_persist_with_server_timestamps_and_expire_at_ttl(reports):
    progress, store, clock = reports
    assert progress.latest() is None
    report = progress.record(payload(ttl_seconds=30), "runner")
    assert report["updated_at"] == clock[0].isoformat()
    assert report["expires_at"] == (clock[0] + timedelta(seconds=30)).isoformat()
    assert report["updated_by"] == "runner"
    assert report["stale"] is False
    clock[0] += timedelta(seconds=29)
    assert ExecutionProgressStore(store).latest()["stale"] is False
    clock[0] += timedelta(seconds=1)
    assert progress.latest()["stale"] is True


def test_every_report_appends_without_changing_experiment_state(reports):
    progress, store, clock = reports
    item = store.create({"name": "Queued hardware plan", "duration_seconds": 3, "execution_mode": "external_guarded"}, "operator")
    before = store.get(item["id"])
    first = progress.record(payload(experiment_id=item["id"]), "runner")
    clock[0] += timedelta(seconds=10)
    second = progress.record(payload(state="blocked", summary="The control software has changed", experiment_id=item["id"]), "runner")
    assert second["revision"] > first["revision"]
    assert progress.latest() == second
    assert store.get(item["id"]) == before
    with store.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM execution_progress_reports").fetchone()[0] == 2
        for sql in ("UPDATE execution_progress_reports SET updated_by='other'", "DELETE FROM execution_progress_reports"):
            with pytest.raises(sqlite3.IntegrityError, match="append-only"):
                connection.execute(sql)


@pytest.mark.parametrize("changes", [
    {"summary": " \n "}, {"next_action": " "}, {"summary": "x" * 601},
    {"detail": "x" * 2001}, {"next_action": "x" * 1001}, {"task_name": "x" * 201},
    {"ttl_seconds": 29}, {"ttl_seconds": 3601}, {"state": "ready"},
    {"updated_at": "2026-01-01T00:00:00+00:00"},
])
def test_report_validation_bounds_fields_and_rejects_forged_time(changes):
    with pytest.raises(ValidationError):
        ExecutionProgressIn.model_validate(payload(**changes))


def observed(*, fresh=True, busy=False):
    return {"health": {"fresh": fresh}, "robot": {"busy": busy, "activity": "rl" if busy else "limp"}}


def test_fresh_observed_control_takes_precedence_over_blocked_or_expired_report():
    report = {**payload(state="blocked"), "stale": True}
    summary = execution_summary(observed(busy=True), [], report)
    assert summary["state"] == "running"
    assert "active rl process" in summary["reason"]
    assert summary["report"] == report


def test_fresh_report_explains_specific_blocker_and_next_action():
    report = {**payload(state="blocked", summary="Installed controller hashes do not match the plan", next_action="Verify the new controller and record its hashes"), "stale": False}
    summary = execution_summary(observed(), [], report)
    assert summary["state"] == "blocked"
    assert summary["reason"] == report["summary"]
    assert summary["next_action"] == report["next_action"]


def test_preparation_can_progress_while_robot_is_idle():
    report = {**payload(), "stale": False}
    summary = execution_summary(observed(), [], report)
    assert summary["state"] == "preparing"
    assert summary["reason"] == "Verifying the timing fix"


def test_reported_running_does_not_override_fresh_idle_robot():
    summary = execution_summary(observed(), [], {**payload(state="running"), "stale": False})
    assert summary["state"] == "unknown"
    assert "Fresh robot readings show no active control process" in summary["reason"]


def test_expired_report_and_old_busy_telemetry_do_not_claim_current_work():
    summary = execution_summary(observed(fresh=False, busy=True), [], {**payload(state="running"), "stale": True})
    assert summary["state"] == "unknown"
    assert "stale" in summary["headline"]
    assert "unknown" in summary["reason"]


def test_waiting_without_report_explains_missing_runner_instead_of_permission():
    plans = [{"status": "waiting_for_operator"}, {"status": "succeeded"}]
    summary = execution_summary(observed(), plans, None)
    assert summary["headline"] == "Idle — no runner progress reported"
    assert "1 saved physical-test plan" in summary["reason"]
    assert "not started automatically" in summary["reason"]
    assert "permission" not in summary["reason"]


def test_malformed_or_undated_report_cannot_claim_work_is_running():
    for report in ({}, {**payload(state="running")}, {"state": "running", "stale": False}):
        assert execution_summary(observed(fresh=False), [], report)["state"] == "unknown"


def test_blocked_report_does_not_claim_an_offline_robot_is_idle():
    summary = execution_summary(observed(fresh=False), [], {**payload(state="blocked"), "stale": False})
    assert summary["state"] == "blocked"
    assert summary["headline"] == "Execution blocked — robot activity unverified"
    assert summary["reason"] == "Verifying the timing fix"


def test_waiting_plans_do_not_claim_an_offline_robot_is_idle():
    summary = execution_summary(observed(fresh=False), [{"status": "waiting_for_operator"}], None)
    assert summary["state"] == "unknown"
    assert "Idle" not in summary["headline"]
    assert "Live robot activity has not been verified" in summary["reason"]
    assert "saved physical-test plan" in summary["reason"]


def test_reported_idle_does_not_replace_unverified_robot_activity():
    summary = execution_summary(observed(fresh=False), [], {**payload(state="idle"), "stale": False})
    assert summary["state"] == "unknown"
    assert summary["headline"] == "Runner reports idle — robot activity unverified"


def test_fresh_physical_process_name_and_detail_are_reported():
    status = observed(busy=True)
    status["robot"].update(process_name="scripted walk", detail="Forward trial, 2 seconds elapsed")
    summary = execution_summary(status, [], None)
    assert summary["state"] == "running"
    assert "scripted walk" in summary["reason"]
    assert "2 seconds elapsed" in summary["reason"]
