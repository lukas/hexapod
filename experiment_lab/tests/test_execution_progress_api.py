"""An agent's progress note is authenticated context, not a robot command."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
import pytest

from hexapod_lab.config import Settings
from hexapod_lab import execution_progress
from hexapod_lab.main import create_app


OPERATOR = {"Authorization": "Bearer operator-secret"}
VIEWER = {"Authorization": "Bearer viewer-secret"}
ENDPOINT = "/api/execution-progress"


def progress(**overrides):
    return {
        "state": "preparing",
        "summary": "Checking the next saved experiment.",
        "detail": "Reviewing the existing results and required software.",
        "next_action": "Finish the review before an operator starts a physical test.",
        "task_name": "Review saved experiment",
        "ttl_seconds": 300,
        **overrides,
    }


@pytest.fixture
def lab(tmp_path, monkeypatch):
    settings = Settings(
        data_dir=tmp_path,
        api_keys="operator:alice:operator-secret,viewer:bob:viewer-secret",
        driver="simulated",
        robot_command=(),
        camera_input="",
        bind="127.0.0.1",
        port=8767,
        public_base_url="",
        auto_worker=False,
        max_duration_seconds=2,
    )
    app = create_app(settings)
    status = {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "health": {"state": "healthy", "fresh": True, "age_seconds": 0.5},
        "robot": {
            "busy": False,
            "activity": "limp",
            "armed": False,
            "headline": "Stopped · motor power disabled",
            "last_issue": None,
        },
        "camera": {"available": True, "fresh": True, "pose_review_required": False},
        "readiness": {"state": "operator_checks", "can_start_from_website": False},
        "queue": {"waiting": 0, "software_blocked": 0},
        "refresh_seconds": 5,
    }
    monkeypatch.setattr(app.state.robot_status, "snapshot", lambda experiments=(): deepcopy(status))
    with TestClient(app) as client:
        yield client, status


def test_progress_reports_require_authentication_and_viewers_cannot_publish(lab):
    client, _ = lab
    assert client.get(ENDPOINT).status_code == 401
    assert client.post(ENDPOINT, json=progress()).status_code == 401
    assert client.get(ENDPOINT, headers=VIEWER).json() is None
    assert client.post(ENDPOINT, headers=VIEWER, json=progress()).status_code == 403
    assert client.get(ENDPOINT, headers=VIEWER).json() is None
    response = client.post(ENDPOINT, headers=OPERATOR, json=progress())
    assert response.status_code in {200, 201}, response.text
    read = client.get(ENDPOINT, headers=VIEWER)
    assert read.status_code == 200
    assert read.json()["summary"] == progress()["summary"]


def test_progress_for_unknown_experiment_is_rejected_without_saving_a_report(lab):
    client, _ = lab
    response = client.post(ENDPOINT, headers=OPERATOR, json=progress(experiment_id="missing-experiment"))
    assert response.status_code == 404
    assert client.get(ENDPOINT, headers=VIEWER).json() is None


def test_publishing_progress_does_not_change_experiment_state_or_start_a_run(lab):
    client, _ = lab
    response = client.post(
        "/api/experiments",
        headers=OPERATOR,
        json={"name": "Guarded comparison", "duration_seconds": 1, "execution_mode": "external_guarded"},
    )
    assert response.status_code == 202
    experiment_id = response.json()["id"]
    before = client.app.state.store.get(experiment_id)
    events_before = client.app.state.store.events(experiment_id)
    report = client.post(
        ENDPOINT,
        headers=OPERATOR,
        json=progress(state="running", experiment_id=experiment_id),
    )
    assert report.status_code in {200, 201}, report.text
    after = client.app.state.store.get(experiment_id)
    assert after == before
    assert after["status"] == "waiting_for_operator"
    assert after["started_at"] is None
    assert client.app.state.store.events(experiment_id) == events_before


def test_report_identity_timestamps_and_revision_are_server_assigned_not_spoofable(lab, monkeypatch):
    client, _ = lab
    now = datetime(2026, 9, 5, 20, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(execution_progress, "_utcnow", lambda: now)
    spoofed = client.post(
        ENDPOINT,
        headers=OPERATOR,
        json=progress(
            updated_by="another-operator",
            updated_at="2099-01-01T00:00:00+00:00",
            expires_at="2099-01-01T01:00:00+00:00",
            revision=999,
            stale=False,
        ),
    )
    assert spoofed.status_code == 422
    assert client.get(ENDPOINT, headers=VIEWER).json() is None
    response = client.post(ENDPOINT, headers=OPERATOR, json=progress())
    assert response.status_code == 201, response.text
    report = response.json()
    assert report["updated_by"] == "alice"
    assert datetime.fromisoformat(report["updated_at"]) == now
    assert datetime.fromisoformat(report["expires_at"]) == now + timedelta(seconds=300)
    assert report["revision"] == 1
    assert report["stale"] is False
    assert client.get(ENDPOINT, headers=VIEWER).json() == report


def test_live_busy_robot_overrides_an_earlier_blocked_progress_report(lab):
    client, status = lab
    report = client.post(
        ENDPOINT,
        headers=OPERATOR,
        json=progress(state="blocked", summary="Waiting for the required software."),
    )
    assert report.status_code == 201
    status["robot"].update(busy=True, activity="demo")
    response = client.get("/api/robot-status", headers=VIEWER)
    assert response.status_code == 200
    execution = response.json()["execution"]
    assert execution["state"] == "running"
    assert execution["report"]["state"] == "blocked"
    assert "active" in execution["reason"].lower()


def test_offline_robot_does_not_confirm_a_self_reported_run_or_old_busy_flag(lab):
    client, status = lab
    report = client.post(
        ENDPOINT,
        headers=OPERATOR,
        json=progress(state="running", summary="The runner reports that a test has started."),
    )
    assert report.status_code == 201
    status["health"].update(state="offline", fresh=False, age_seconds=None)
    status["robot"].update(busy=True, activity="demo")
    response = client.get("/api/robot-status", headers=VIEWER)
    assert response.status_code == 200
    execution = response.json()["execution"]
    assert execution["state"] == "unknown"
    assert execution["report"]["state"] == "running"
    assert "not been verified" in execution["reason"].lower()
    assert response.json()["readiness"]["can_start_from_website"] is False
