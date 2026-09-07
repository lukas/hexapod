"""Exercise browser polling and visible failure/recovery behavior without a server."""

import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from hexapod_lab.robot_status_page import robot_status_panel
from hexapod_lab.recovery_status import recovery_status
from hexapod_lab.service_recovery import ISSUES as RECOVERY_ISSUES


def run_page(*responses, frame_status=None):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for browser-script regression checks")
    html = robot_status_panel()
    payload = {
        "script": html.split("<script>", 1)[1].split("</script>", 1)[0],
        "node_names": re.findall(r'data-rn="([^"]+)"', html),
        "responses": responses, "frame_status": frame_status,
    }
    result = subprocess.run(
        [node, str(Path(__file__).with_name("robot_status_browser_harness.js"))],
        input=json.dumps(payload), text=True, capture_output=True, check=True, timeout=10,
    )
    return json.loads(result.stdout)


def status_body(*cameras):
    return {
        "health": {"state": "healthy", "fresh": True, "live_motors": 18,
                   "expected_motors": 18, "headline": "Motor health checks look normal"},
        "robot": {"busy": False}, "camera": {"fresh": False},
        "readiness": {}, "queue": {}, "cameras": list(cameras),
    }


def test_expired_sign_in_has_action_and_clears_after_success():
    result = run_page({"status": 401}, {"body": status_body()})
    expired, recovered = result["snapshots"]
    assert expired["nodes"]["service_headline"]["text"] == "Your Robot Lab sign-in has expired"
    assert expired["nodes"]["sign_in"]["hidden"] is False
    assert expired["nodes"]["sign_in"]["href"] == "/login?next=%2Fexperiments%2Fexample%3Fview%3Dlive"
    assert expired["health"] == "unknown"
    assert "offline" not in expired["nodes"]["headline"]["text"].lower()
    assert recovered["nodes"]["service_alert"]["hidden"] is True
    assert recovered["nodes"]["sign_in"]["hidden"] is True
    assert recovered["health"] == "healthy"


@pytest.mark.parametrize("response,headline,sign_in", [
    ({"status": 403}, "This account cannot read Robot Lab status", True),
    ({"status": 502}, "Robot Lab service is unavailable", False),
    ({"status": 503}, "Robot Lab service is unavailable", False),
    ({"error": "TypeError"}, "This browser cannot reach Robot Lab", False),
    ({"error": "AbortError"}, "Robot Lab is not responding", False),
    ({"invalid_json": True}, "Robot Lab status feed returned an error", False),
    ({"body": {}}, "Robot Lab status feed returned an error", False),
])
def test_service_failures_identify_the_failed_layer(response, headline, sign_in):
    view = run_page(response)["snapshots"][0]
    assert view["nodes"]["service_headline"]["text"] == headline
    assert view["nodes"]["service_alert"]["hidden"] is False
    assert view["nodes"]["sign_in"]["hidden"] is not sign_in
    assert view["health"] == "unknown"
    assert "private" not in json.dumps(view)


def test_successful_lab_response_can_report_physical_robot_unreachable():
    body = status_body()
    body["health"].update(state="offline", fresh=False,
                          headline="Robot controller unreachable",
                          detail="Robot Lab is online. The robot controller did not answer in time.")
    view = run_page({"body": body})["snapshots"][0]
    assert view["nodes"]["service_headline"]["text"] == "Robot controller unreachable"
    assert view["nodes"]["service_detail"]["text"].startswith("Robot Lab is online.")
    assert view["nodes"]["service_alert"]["hidden"] is False
    assert view["nodes"]["sign_in"]["hidden"] is True


def test_overview_separates_working_lab_idle_robot_partial_cameras_and_stale_report():
    body = status_body(*[{"id": f"robot-{i}", "fresh": i != 2, "available": i != 2}
                         for i in range(1, 5)])
    body["robot"].update(armed=False)
    body["execution"] = {"state": "unknown", "report": {"stale": True}}
    live, failed = run_page({"body": body}, {"status": 503})["snapshots"]
    assert live["nodes"]["overview_lab"]["text"] == "Online · live status received"
    assert live["nodes"]["overview_robot"]["text"] == "Stopped · motor power off"
    assert live["nodes"]["overview_cameras"]["text"] == "3 / 4 live · see issue below"
    assert live["nodes"]["overview_execution"]["text"] == "Stale · activity unconfirmed"
    assert failed["nodes"]["overview_lab"]["text"] == "Connection failed"
    assert failed["nodes"]["overview_robot"]["text"] == "Current state unknown"


def test_overview_identifies_expected_camera_reservation():
    body = status_body({"id": "robot-1", "status": "paused"})
    view = run_page({"body": body})["snapshots"][0]
    assert view["nodes"]["overview_cameras"]["text"] == "Reserved by a hardware task"


@pytest.mark.parametrize("camera,expected", [
    ({"permission_status": "denied", "issue_code": "macos_privacy_fd_exhaustion"}, "privacy service has run out of file handles"),
    ({"permission_status": "denied"}, "macOS denied camera access"),
    ({"permission_status": "restricted"}, "macOS restricts camera access"),
    ({"permission_status": "not_determined"}, "Camera permission has not been granted"),
    ({"status": "paused"}, "Preview capture is paused"),
    ({"status": "paused", "permission_status": "denied"}, "Preview capture is paused"),
    ({"status": "in_use"}, "in use by another application"),
    ({"status": "stale"}, "last camera frame is too old"),
    ({"status": "stopped"}, "Camera capture is stopped"),
    ({"status": "unavailable", "error": "Configured camera is disconnected or suspended"}, "disconnected or cannot be identified"),
    ({"issue_code": "vision_service_unavailable"}, "vision service is unreachable"),
])
def test_hidden_camera_images_keep_a_visible_reason(camera, expected):
    camera.update(id="robot-1", name="Front", available=False, fresh=False)
    result = run_page({"body": status_body(camera)})
    view = result["snapshots"][0]
    assert view["nodes"]["observation_cameras"]["hidden"] is False
    assert view["nodes"]["camera_notice"]["hidden"] is False
    assert view["nodes"]["camera_headline"]["text"] == "No live camera view is available"
    assert expected in view["nodes"]["camera_reasons"]["children"][0]
    assert result["calls"] == ["/api/robot-status"]
    assert view["health"] == "healthy"


def test_permission_problem_is_grouped_and_remains_visible_alongside_working_camera():
    live = {"id": "robot-1", "name": "Front", "available": True, "fresh": True,
            "frame_url": "/api/robot-status/cameras/robot-1/frame"}
    blocked = [{"id": f"robot-{i}", "name": name, "permission_status": "denied"}
               for i, name in enumerate(["Side", "Rear"], start=2)]
    view = run_page({"body": status_body(live, *blocked)})["snapshots"][0]
    assert view["nodes"]["camera_headline"]["text"] == "Some camera views are unavailable"
    assert len(view["nodes"]["camera_reasons"]["children"]) == 1
    assert view["nodes"]["camera_reasons"]["children"][0].startswith("Side, Rear:")


def test_camera_frame_auth_failure_shows_sign_in_and_clears_previews():
    live = {"id": "robot-1", "available": True, "fresh": True,
            "frame_url": "/api/robot-status/cameras/robot-1/frame"}
    view = run_page({"body": status_body(live)}, frame_status=401)["snapshots"][0]
    assert view["nodes"]["sign_in"]["hidden"] is False
    assert view["nodes"]["observation_cameras"]["hidden"] is True


def test_camera_image_failure_does_not_silently_hide_all_cameras():
    live = {"id": "robot-1", "available": True, "fresh": True,
            "frame_url": "/api/robot-status/cameras/robot-1/frame"}
    view = run_page({"body": status_body(live)}, frame_status=503)["snapshots"][0]
    assert view["nodes"]["camera_notice"]["hidden"] is False
    assert "could not deliver" in view["nodes"]["camera_reasons"]["children"][0]
    assert view["health"] == "healthy"


@pytest.mark.parametrize("state", ["blocked", "stale", "unverified"])
def test_imessage_alert_delivery_problem_is_visible_and_clears_on_recovery(state):
    body = status_body()
    body["alerts"] = {"status": state, "headline": "iMessage alerts cannot be sent",
                      "detail": "macOS is blocking Messages automation.",
                      "action": "Allow the alert application in Privacy & Security → Automation."}
    healthy = status_body()
    healthy["alerts"] = {"status": "ok"}
    problem, recovered = run_page({"body": body}, {"body": healthy})["snapshots"]
    assert problem["nodes"]["alert_delivery"]["hidden"] is False
    assert problem["nodes"]["alert_headline"]["text"] == "iMessage alerts cannot be sent"
    assert "Automation" in problem["nodes"]["alert_action"]["text"]
    assert recovered["nodes"]["alert_delivery"]["hidden"] is True


def test_service_failure_keeps_known_imessage_blocker_visible():
    body = status_body()
    body["alerts"] = {"status": "blocked", "headline": "iMessage alerts cannot be sent",
                      "detail": "macOS is blocking Messages automation."}
    failed = run_page({"body": body}, {"status": 503})["snapshots"][1]
    assert failed["nodes"]["alert_delivery"]["hidden"] is False
    assert failed["nodes"]["alert_headline"]["text"] == "iMessage alerts cannot be sent"


@pytest.mark.parametrize("state,prefix", [
    ("waiting", "Planned repair:"), ("attempting", "Repair:"),
    ("verifying", "Repair attempted:"), ("recovered", "Repair attempted:"),
    ("needs_attention", "Next:"),
])
def test_recovery_banner_explains_failure_action_and_attempt_count(state, prefix):
    body = status_body()
    body["recovery"] = {
        "status": state, "issue_code": "camera_capture_failed",
        "headline": "Recovery update", "summary": "Robot camera capture stopped.",
        "detail": "Waiting for fresh observations.", "action": "Restart the Robot Lab service.",
        "attempts": 2, "last_attempt_at": "2026-09-06T08:00:00+00:00",
        "verified_at": "2026-09-06T08:01:00+00:00" if state == "recovered" else None,
    }
    view = run_page({"body": body})["snapshots"][0]
    assert view["nodes"]["recovery"]["hidden"] is False
    assert view["nodes"]["recovery_summary"]["text"] == "Robot camera capture stopped."
    assert view["nodes"]["recovery_action"]["text"].startswith(prefix)
    assert "2 repair attempts" in view["nodes"]["recovery_meta"]["text"]
    assert ("Verified at" in view["nodes"]["recovery_meta"]["text"]) is (state == "recovered")


def test_recovery_banner_disappears_when_monitor_reports_no_issue():
    body = status_body()
    body["recovery"] = {"status": "waiting", "issue_code": "none", "reason_code": "none"}
    view = run_page({"body": body})["snapshots"][0]
    assert view["nodes"]["recovery"]["hidden"] is True


def test_recovery_disabled_remains_visible_even_without_an_active_failure():
    body = status_body()
    body["recovery"] = {"status": "waiting", "issue_code": "none", "reason_code": "disabled",
                        "headline": "Automatic recovery is waiting", "detail": "Automatic recovery is disabled."}
    view = run_page({"body": body})["snapshots"][0]
    assert view["nodes"]["recovery"]["hidden"] is False
    assert "disabled" in view["nodes"]["recovery_detail"]["text"]


def test_lost_status_feed_stops_claiming_a_repair_is_running():
    body = status_body()
    body["recovery"] = {"status": "attempting", "headline": "Automatic recovery is running",
                        "action": "Restart the Robot Lab service.", "attempts": 1}
    view = run_page({"body": body}, {"status": 503})["snapshots"][1]
    assert view["nodes"]["recovery_headline"]["text"] == "Automatic recovery status is unknown"
    assert view["nodes"]["recovery_action"]["hidden"] is True
    assert "cannot confirm" in view["nodes"]["recovery_detail"]["text"]


@pytest.mark.parametrize("issue", sorted(RECOVERY_ISSUES))
def test_every_recovery_engine_issue_has_a_visible_safe_browser_explanation(tmp_path, issue):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    action, _ = RECOVERY_ISSUES[issue]
    path = tmp_path / "recovery-state.json"
    path.write_text(json.dumps({
        "status": "attempting" if action else "needs_attention", "issue_code": issue,
        "action": action, "reason_code": "verification_pending" if action else "manual_action_required",
        "attempts": 1 if action else 0, "last_attempt_at": now.isoformat(),
        "updated_at": now.isoformat(), "detail": "private source error",
    }))
    report = recovery_status(path, now=now)
    assert report["status"] != "unknown", issue
    assert report["issue_code"] == issue
    assert report["action_code"] == action
    body = status_body()
    body["recovery"] = report
    view = run_page({"body": body})["snapshots"][0]
    assert view["nodes"]["recovery"]["hidden"] is False
    assert view["nodes"]["recovery_summary"]["text"] == report["summary"]
    assert report["action"] in view["nodes"]["recovery_action"]["text"]
    assert "private source error" not in json.dumps(view)
