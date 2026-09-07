import json
from datetime import datetime, timedelta, timezone

from hexapod_lab.alert_status import alert_monitor_status


def test_missing_or_stale_monitor_does_not_claim_alerts_work(tmp_path):
    path = tmp_path / "state.json"
    assert alert_monitor_status(path)["status"] == "stale"
    now = datetime.now(timezone.utc)
    path.write_text(json.dumps({"last_scan_at": (now - timedelta(minutes=4)).isoformat(),
                              "alert_delivery": {"status": "ok", "last_success_at": now.isoformat()}}))
    assert alert_monitor_status(path, now=now)["status"] == "stale"


def test_messages_denial_is_actionable_and_does_not_leak_private_state(tmp_path):
    now = datetime.now(timezone.utc)
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"last_scan_at": now.isoformat(), "recipient": "private-recipient",
                              "alert_delivery": {"status": "blocked", "error_code": "messages_automation_denied",
                                                 "action": "private-message", "last_success_at": None}}))
    result = alert_monitor_status(path, now=now)
    assert result["status"] == "blocked"
    assert "Automation" in result["action"]
    assert "Messages" in result["detail"]
    assert "private-" not in json.dumps(result)


def test_live_monitor_only_claims_submission_after_success(tmp_path):
    now = datetime.now(timezone.utc)
    path = tmp_path / "state.json"
    state = {"last_scan_at": now.isoformat(), "alert_delivery": {"status": "ok"}}
    path.write_text(json.dumps(state))
    assert alert_monitor_status(path, now=now)["status"] == "unverified"
    state["alert_delivery"]["last_success_at"] = now.isoformat()
    path.write_text(json.dumps(state))
    assert alert_monitor_status(path, now=now)["status"] == "ok"
