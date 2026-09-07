from datetime import datetime, timedelta, timezone
import json

import pytest

from hexapod_lab.recovery_status import recovery_status


NOW = datetime(2026, 9, 6, 8, 0, tzinfo=timezone.utc)


def state_file(tmp_path, **values):
    state = {"status": "attempting", "issue_code": "camera_capture_failed",
             "reason_code": "verification_pending", "action": "restart_lab",
             "attempts": 1, "last_attempt_at": (NOW - timedelta(seconds=10)).isoformat(),
             "updated_at": NOW.isoformat(), "event_id": 3}
    state.update(values)
    path = tmp_path / "recovery-state.json"
    path.write_text(json.dumps(state))
    return path


def test_missing_corrupt_oversized_or_nonobject_state_never_claims_recovery(tmp_path):
    path = tmp_path / "recovery-state.json"
    assert recovery_status(path, now=NOW)["status"] == "unknown"
    for content in (b"{bad", b"[]", b"null", b"\xff", b" " * (16 * 1024 + 1)):
        path.write_bytes(content)
        assert recovery_status(path, now=NOW)["status"] == "unknown"


def test_public_report_uses_fixed_text_without_raw_private_state(tmp_path):
    path = state_file(tmp_path, summary="secret-recipient", detail="secret-URL",
                      last_error="secret-token", history=["secret-exception"])
    report = recovery_status(path, now=NOW)
    assert report["status"] == "attempting"
    assert report["headline"] == "Automatic recovery is running"
    assert report["action"] == "Restart the Robot Lab service."
    assert report["event_id"] == 3
    assert "secret" not in json.dumps(report)


@pytest.mark.parametrize("reason,phrase", [
    ("hardware_active_or_unobserved", "confirmed idle"),
    ("disabled", "disabled"),
    ("confirming_failure", "another fresh observation"),
    ("cooldown", "retry cooldown"),
    ("observations_stale", "fresh observations"),
])
def test_waiting_explains_why_no_repair_has_started(tmp_path, reason, phrase):
    report = recovery_status(state_file(tmp_path, status="waiting", reason_code=reason), now=NOW)
    assert report["status"] == "waiting"
    assert phrase in report["detail"]


@pytest.mark.parametrize("status", ["waiting", "attempting", "verifying"])
@pytest.mark.parametrize("updated", [None, "invalid", "2026-09-06T07:55:00+00:00", "2026-09-06T08:10:00+00:00"])
def test_stale_missing_or_future_heartbeat_does_not_claim_current_activity(tmp_path, status, updated):
    report = recovery_status(state_file(tmp_path, status=status, updated_at=updated), now=NOW)
    assert report["status"] == "unknown"
    assert "not reporting" in report["headline"]
    assert report["action"] is None


@pytest.mark.parametrize("verified", [None, "invalid", "2026-09-06T07:59:00+00:00", "2026-09-06T08:10:00+00:00"])
def test_recovered_requires_verification_after_latest_attempt(tmp_path, verified):
    report = recovery_status(state_file(tmp_path, status="recovered", verified_at=verified), now=NOW)
    assert report["status"] == "unknown"
    assert "not been verified" in report["headline"]
    assert report["verified_at"] is None


def test_verified_recovery_preserves_action_attempts_and_confirmation_time(tmp_path):
    report = recovery_status(state_file(tmp_path, status="recovered", verified_at=NOW.isoformat()), now=NOW)
    assert report["status"] == "recovered"
    assert report["verified_at"] == NOW.isoformat()
    assert report["attempts"] == 1
    assert report["action_code"] == "restart_lab"
    assert report["summary"].startswith("Earlier failure:")


@pytest.mark.parametrize("reason,phrase", [("attempts_exhausted", "retry limit"), ("manual_action_required", "manual fix")])
def test_exhaustion_and_manual_intervention_are_explicit(tmp_path, reason, phrase):
    report = recovery_status(state_file(tmp_path, status="needs_attention", reason_code=reason,
                                        issue_code="camera_permission_denied"), now=NOW)
    assert phrase in report["detail"]
    assert "allow camera access" in report["action"]
    assert report["action_code"] is None


@pytest.mark.parametrize("field,value", [("status", ["secret"]), ("issue_code", {"secret": 1})])
def test_invalid_enum_types_are_safe(tmp_path, field, value):
    report = recovery_status(state_file(tmp_path, **{field: value}), now=NOW)
    assert report["status"] == "unknown"


def test_unknown_actions_and_invalid_counters_are_not_published(tmp_path):
    report = recovery_status(state_file(tmp_path, action="run secret-command", reason_code=["secret"],
                                        attempts=True, event_id="secret", last_attempt_at="secret"), now=NOW)
    assert report["action"] is None
    assert report["reason_code"] is None
    assert report["attempts"] == 0
    assert report["event_id"] is None
    assert "secret" not in json.dumps(report)


def test_robot_controller_unavailable_explains_power_network_and_fresh_telemetry(tmp_path):
    report = recovery_status(state_file(
        tmp_path, status="needs_attention", issue_code="robot_controller_unavailable",
        reason_code="manual_action_required", action=None, attempts=0,
    ), now=NOW)
    assert report["status"] == "needs_attention"
    assert report["issue_code"] == "robot_controller_unavailable"
    assert "robot controller" in report["summary"]
    assert "robot power" in report["action"]
    assert "network connection" in report["action"]
    assert "fresh telemetry" in report["action"]
    assert report["action_code"] is None
