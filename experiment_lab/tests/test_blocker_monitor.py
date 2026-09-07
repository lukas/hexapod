from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import io
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import BaseHandler, build_opener as real_build_opener
from urllib.response import addinfourl

import pytest

from hexapod_lab.blocker_monitor import (
    BlockerMonitor,
    MonitorSettings,
    fetch_json,
    send_messages_text,
)


def injected_http_transport(monkeypatch, responder):
    """Exercise urllib's real redirect/error chain without opening a socket."""
    requests = []

    class Transport(BaseHandler):
        handler_order = 100

        def http_open(self, request):
            requests.append((request.full_url, request.get_header("Authorization")))
            code, headers, stream = responder(request)
            response = addinfourl(stream, headers, request.full_url, code)
            response.msg = "Injected HTTP response"
            return response

        https_open = http_open

    monkeypatch.setattr("hexapod_lab.blocker_monitor.build_opener",
                        lambda *handlers: real_build_opener(*handlers, Transport()))
    return requests


@pytest.mark.parametrize("code", [301, 302, 303, 307, 308])
@pytest.mark.parametrize("destination", ["https://unrelated.test/collect", "http://unrelated.test/collect", "/different-endpoint"])
def test_fetch_json_rejects_redirect_before_token_leaves_configured_endpoint(monkeypatch, code, destination):
    configured_url = "https://configured.test/api/robot-status"
    token = "private-monitor-token"

    def responder(request):
        headers = Message()
        if request.full_url == configured_url:
            headers["Location"] = destination
            return code, headers, io.BytesIO(b"redirect")
        return 200, headers, io.BytesIO(b'{"ok": true}')

    requests = injected_http_transport(monkeypatch, responder)
    with pytest.raises(HTTPError) as failure:
        fetch_json(configured_url, token)
    assert failure.value.code == code
    assert requests == [(configured_url, "Bearer " + token)]
    assert token not in str(failure.value)


@pytest.mark.parametrize("extra", [0, 1])
def test_fetch_json_reads_a_bounded_body_and_rejects_oversize_before_parsing(monkeypatch, extra):
    limit = 8 * 1024 * 1024

    class CountedStream(io.BytesIO):
        requested = []
        bytes_read = 0

        def read(self, size=-1):
            self.requested.append(size)
            data = super().read(size)
            self.bytes_read += len(data)
            return data

    stream = CountedStream(b'"' + b'x' * (limit - 2 + extra) + b'"')
    injected_http_transport(monkeypatch, lambda request: (200, Message(), stream))
    if extra:
        with pytest.raises(ValueError, match="response exceeds size limit"):
            fetch_json("https://configured.test/api/robot-status", "private-token")
    else:
        assert len(fetch_json("https://configured.test/api/robot-status", "private-token")) == limit - 2
    assert stream.requested == [limit + 1]
    assert stream.bytes_read <= limit + 1
    assert stream.closed


def configured(tmp_path):
    return MonitorSettings(
        recipient="+15555550123",
        state_path=tmp_path / "state.json",
        orchestrator_url="https://orchestrator.test/api/blockers",
        orchestrator_token="orchestrator-secret",
        robot_lab_url="http://lab.test/api/experiments",
        robot_lab_token="lab-secret",
        robot_lab_queue_url="http://lab.test/api/codex-queue",
        robot_lab_status_url="",
        robot_lab_public_url="",
        outage_threshold=2,
        stuck_grace_seconds=30,
    )


def test_recovery_events_text_cause_action_and_verified_result_once(tmp_path):
    settings = replace(configured(tmp_path), auto_recovery=True)
    current = datetime(2026, 9, 6, tzinfo=timezone.utc)
    state = {
        "status": "verifying", "issue_code": "lab_unavailable", "action": "restart_lab",
        "reason_code": "verification_pending", "attempts": 1, "event_id": 1,
        "last_attempt_at": current.isoformat(), "updated_at": current.isoformat(),
        "detail": "private raw exception and credentials must not be texted",
    }
    observations = {"idle_verified": True}
    calls, sent = [], []
    class Observer:
        def collect(self, alert_delivery=None, verify_privacy=False):
            return observations
    class Manager:
        def step(self, facts, idle_verified):
            calls.append((facts, idle_verified))
            (tmp_path / "recovery-state.json").write_text(json.dumps(state))
            return dict(state)
    monitor = BlockerMonitor(
        settings, sender=lambda _, message: sent.append(message), now=lambda: current,
        recovery_manager=Manager(), recovery_observer=Observer(),
    )
    monitor._scan_recovery()
    monitor._scan_recovery()
    assert len(sent) == 1
    assert "Restart the Robot Lab service" in sent[0]
    assert "The Robot Lab service is not responding" in sent[0]
    assert "not yet verified" in sent[0]
    assert "private raw" not in sent[0]
    assert calls == [(observations, True), (observations, True)]
    state.update(status="recovered", verified_at=current.isoformat(), event_id=2)
    monitor._scan_recovery()
    assert len(sent) == 2 and "verified" in sent[1]


def test_recovery_check_failure_does_not_stop_outage_monitor(tmp_path):
    settings = replace(configured(tmp_path), auto_recovery=True)
    class Observer:
        def collect(self, alert_delivery=None, verify_privacy=False):
            raise TimeoutError("private source address")
    sent = []
    def fetcher(url, token):
        if url == settings.orchestrator_url:
            return {"open": [{"id": "blocked", "summary": "Test blocker"}], "recent": []}
        if url == settings.robot_lab_queue_url:
            return {"control": {"paused": True}}
        return []
    monitor = BlockerMonitor(
        settings, sender=lambda _, message: sent.append(message), fetcher=fetcher,
        recovery_observer=Observer(), recovery_manager=object(),
    )
    monitor.scan_once()
    assert len(sent) == 1 and "Test blocker" in sent[0]
    assert monitor.state["last_scan_at"]


def test_recovery_is_explicitly_enabled_in_environment(monkeypatch):
    monkeypatch.delenv("HEXAPOD_AUTO_RECOVERY", raising=False)
    assert MonitorSettings.from_env().auto_recovery is False
    monkeypatch.setenv("HEXAPOD_AUTO_RECOVERY", "1")
    assert MonitorSettings.from_env().auto_recovery is True


def test_invalid_recovery_setup_preserves_outage_alert_monitor(tmp_path, capsys):
    settings = replace(configured(tmp_path), auto_recovery=True,
                       robot_lab_status_url="https://custom.test/api/robot-status?key=private-config")
    sent = []

    def fetcher(url, _token):
        if url == settings.orchestrator_url:
            return {"open": [{"id": "live-blocker", "summary": "A real operator blocker"}], "recent": []}
        if url == settings.robot_lab_queue_url:
            return {"control": {"paused": True}}
        if url == settings.robot_lab_status_url:
            return {"health": {"fresh": True, "state": "healthy"}, "observation_cameras": []}
        return []

    monitor = BlockerMonitor(settings, sender=lambda _recipient, text: sent.append(text), fetcher=fetcher)
    assert monitor.settings.auto_recovery is True
    assert monitor.recovery_manager is None
    assert monitor.recovery_observer is None
    monitor.scan_once()
    assert len(sent) == 1 and "real operator blocker" in sent[0]
    assert monitor.state["last_scan_at"]
    assert not (tmp_path / "recovery-state.json").exists()
    log = capsys.readouterr().out
    assert "automatic recovery setup failed (ValueError)" in log
    assert "outage alerts remain active" in log
    assert "private-config" not in log


def test_messages_sender_keeps_recipient_and_alert_out_of_process_arguments(
    monkeypatch,
):
    recipient = "+15555550123"
    message = "private robot alert"

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(arguments, **kwargs):
        assert recipient not in arguments
        assert message not in arguments
        assert Path(arguments[2]).read_text(encoding="utf-8") == recipient
        assert Path(arguments[3]).read_text(encoding="utf-8") == message
        assert kwargs["input"]
        return Completed()

    monkeypatch.setattr("subprocess.run", fake_run)
    send_messages_text(recipient, message)


def test_new_blocker_failure_and_resolution_are_deduplicated(tmp_path):
    settings = configured(tmp_path)
    sent = []
    payloads = {
        settings.orchestrator_url: {"open": [], "recent": []},
        settings.robot_lab_url: [{"id": "old", "status": "failed"}],
        settings.robot_lab_queue_url: {"control": {"paused": False}},
    }
    monitor = BlockerMonitor(
        settings,
        sender=lambda recipient, message: sent.append((recipient, message)),
        fetcher=lambda url, token: payloads[url],
    )
    monitor.scan_once()
    assert sent == []  # historical Robot Lab failures are baselined

    blocker = {
        "id": "blk_1",
        "source": "watcher",
        "summary": "Need operator decision",
        "details": "Choose A or B",
        "resolved_at": None,
    }
    payloads[settings.orchestrator_url] = {"open": [blocker], "recent": [blocker]}
    payloads[settings.robot_lab_url].append(
        {
            "id": "new",
            "name": "hardware run",
            "status": "failed",
            "error": "camera lost",
            "codex_jobs": [{
                "id": "job-1",
                "kind": "advance",
                "status": "blocked",
                "error": "IMU samples are stale",
            }],
        }
    )
    monitor.scan_once()
    monitor.scan_once()
    assert len(sent) == 3
    assert any("Need operator decision" in message for _, message in sent)
    assert any("camera lost" in message for _, message in sent)
    assert any("IMU samples are stale" in message for _, message in sent)

    blocker.update({"resolved_at": "2026-09-04T12:00:00+00:00", "resolution": "picked A"})
    payloads[settings.orchestrator_url] = {"open": [], "recent": [blocker]}
    monitor.scan_once()
    assert len(sent) == 4
    assert "resolved" in sent[-1][1]


def test_stuck_run_and_persistent_outage(tmp_path):
    settings = configured(tmp_path)
    now = datetime(2026, 9, 4, 12, tzinfo=timezone.utc)
    sent = []
    calls = {"orchestrator": 0}

    def fetcher(url, token):
        if url == settings.orchestrator_url:
            calls["orchestrator"] += 1
            if calls["orchestrator"] <= 2:
                raise TimeoutError("offline")
            return {"open": [], "recent": []}
        if url == settings.robot_lab_queue_url:
            return {"control": {"paused": False}}
        return [{
            "id": "run1",
            "name": "stuck walk",
            "status": "running",
            "started_at": (now - timedelta(minutes=5)).isoformat(),
            "duration_seconds": 10,
        }]

    monitor = BlockerMonitor(
        settings,
        sender=lambda recipient, message: sent.append(message),
        fetcher=fetcher,
        now=lambda: now,
    )
    monitor.scan_once()  # baseline the already-stuck run
    monitor.state["baseline_stuck"] = []  # model a newly stuck transition
    monitor.scan_once()
    assert any("failed 2 consecutive checks" in message for message in sent)
    assert any("stuck walk" in message for message in sent)
    monitor.scan_once()
    assert any("reachable again" in message for message in sent)


def test_stale_eligible_codex_job_alerts_when_supervisor_is_not_advancing(tmp_path):
    settings = configured(tmp_path)
    now = datetime(2026, 9, 4, 12, tzinfo=timezone.utc)
    sent = []
    experiments = []

    def fetcher(url, _token):
        if url == settings.orchestrator_url:
            return {"open": [], "recent": []}
        if url == settings.robot_lab_queue_url:
            return {"control": {"paused": False}}
        return experiments

    monitor = BlockerMonitor(
        settings,
        sender=lambda _recipient, message: sent.append(message),
        fetcher=fetcher,
        now=lambda: now,
    )
    monitor.scan_once()
    experiments.append({
        "id": "exp-codex",
        "name": "needs analysis",
        "status": "succeeded",
        "codex_jobs": [{
            "id": "analysis-stale",
            "kind": "analysis",
            "status": "queued",
            "not_before": (now - timedelta(hours=1)).isoformat(),
            "updated_at": (now - timedelta(hours=1)).isoformat(),
            "created_at": (now - timedelta(hours=1)).isoformat(),
            "depends_on_job_id": None,
        }],
    })

    monitor.scan_once()
    monitor.scan_once()

    assert len(sent) == 1
    assert "Codex analysis" in sent[0]
    assert "past its expected deadline" in sent[0]


def analysis_job(job_id, safety_disposition):
    return {
        "id": job_id,
        "kind": "analysis",
        "status": "succeeded",
        "result": {
            "safety_disposition": safety_disposition,
            "what_we_learned": "Bus voltage sagged during lowering.",
            "findings": [
                "Peak current was 5.5 A.",
                "Voltage reached 10.0 V.",
            ],
        },
    }


def test_new_monitor_baselines_existing_stop_without_alerting(tmp_path):
    settings = configured(tmp_path)
    sent = []
    experiments = [{
        "id": "old-run",
        "name": "old physical walk",
        "status": "succeeded",
        "codex_jobs": [
            analysis_job("old-stop", "stop"),
            analysis_job("old-inspection", "needs_inspection"),
        ],
    }]
    monitor = BlockerMonitor(
        settings,
        sender=lambda _recipient, message: sent.append(message),
        fetcher=lambda url, _token: (
            {"open": [], "recent": []}
            if url == settings.orchestrator_url
            else {"control": {"paused": False}}
            if url == settings.robot_lab_queue_url
            else experiments
        ),
    )

    monitor.scan_once()

    assert sent == []
    assert monitor.state["baseline_codex_stops"] == ["old-stop"]


def test_new_stop_alert_is_actionable_deduplicated_and_inspection_stays_quiet(tmp_path):
    settings = configured(tmp_path)
    sent = []
    experiments = []
    monitor = BlockerMonitor(
        settings,
        sender=lambda _recipient, message: sent.append(message),
        fetcher=lambda url, _token: (
            {"open": [], "recent": []}
            if url == settings.orchestrator_url
            else {"control": {"paused": False}}
            if url == settings.robot_lab_queue_url
            else experiments
        ),
    )
    monitor.scan_once()
    experiments.append({
        "id": "walk-run",
        "name": "bounded walking canary",
        "status": "succeeded",
        "codex_jobs": [
            analysis_job("stop-analysis", "stop"),
            analysis_job("inspection-analysis", "needs_inspection"),
            {
                "id": "blocked-advance",
                "kind": "advance",
                "status": "blocked",
                "error": "operator gate remains closed",
            },
        ],
    })

    monitor.scan_once()
    monitor.scan_once()

    assert len(sent) == 2
    assert "SAFETY STOP" in sent[0]
    assert "bounded walking canary" in sent[0]
    assert "Bus voltage sagged during lowering" in sent[0]
    assert "Peak current was 5.5 A" in sent[0]
    assert "Do not run the next physical experiment" in sent[0]
    assert "operator gate remains closed" in sent[1]
    assert all("needs_inspection" not in message for message in sent)
    assert "lab-codex-stop:stop-analysis" in monitor.state["sent"]


def test_failed_stop_delivery_defers_lower_priority_alerts(tmp_path):
    settings = configured(tmp_path)
    attempts = []
    experiments = []

    def sender(_recipient, message):
        attempts.append(message)
        raise RuntimeError("Messages permission missing")

    monitor = BlockerMonitor(
        settings,
        sender=sender,
        fetcher=lambda url, _token: (
            {"open": [], "recent": []}
            if url == settings.orchestrator_url
            else {"control": {"paused": True}}
            if url == settings.robot_lab_queue_url
            else experiments
        ),
    )
    monitor.scan_once()
    experiments.append({
        "id": "walk-run",
        "name": "bounded walking canary",
        "status": "succeeded",
        "codex_jobs": [
            analysis_job("stop-analysis", "stop"),
            {
                "id": "blocked-advance",
                "kind": "advance",
                "status": "blocked",
                "error": "operator gate remains closed",
            },
        ],
    })

    monitor.scan_once()

    assert len(attempts) == 1
    assert "SAFETY STOP" in attempts[0]
    assert "operator gate remains closed" not in attempts[0]
    assert monitor.state["sent"] == []


def test_initialized_legacy_state_alerts_existing_unsent_stop(tmp_path):
    settings = configured(tmp_path)
    settings.state_path.write_text(
        '{"initialized": true, "robot_lab_initialized": true, "sent": []}',
        encoding="utf-8",
    )
    sent = []
    experiments = [{
        "id": "legacy-run",
        "name": "legacy walk",
        "status": "succeeded",
        "codex_jobs": [analysis_job("legacy-stop", "stop")],
    }]
    monitor = BlockerMonitor(
        settings,
        sender=lambda _recipient, message: sent.append(message),
        fetcher=lambda url, _token: (
            {"open": [], "recent": []}
            if url == settings.orchestrator_url
            else {"control": {"paused": False}}
            if url == settings.robot_lab_queue_url
            else experiments
        ),
    )

    monitor.scan_once()

    assert len(sent) == 1
    assert "legacy walk" in sent[0]
    assert monitor.state["baseline_codex_stops"] == []


def test_paused_queue_suppresses_only_queued_or_retry_advance_staleness(tmp_path):
    settings = configured(tmp_path)
    now = datetime(2026, 9, 4, 12, tzinfo=timezone.utc)
    sent = []
    experiments = []
    queue = {"control": {"paused": True}}

    def fetcher(url, _token):
        if url == settings.orchestrator_url:
            return {"open": [], "recent": []}
        if url == settings.robot_lab_queue_url:
            return queue
        return experiments

    monitor = BlockerMonitor(
        settings,
        sender=lambda _recipient, message: sent.append(message),
        fetcher=fetcher,
        now=lambda: now,
    )
    monitor.scan_once()
    old = (now - timedelta(hours=1)).isoformat()
    expired = (now - timedelta(minutes=5)).isoformat()
    experiments.append({
        "id": "paused-queue",
        "name": "paused adaptive queue",
        "status": "succeeded",
        "codex_jobs": [
            {
                "id": "queued-advance",
                "kind": "advance",
                "status": "queued",
                "not_before": old,
                "updated_at": old,
                "created_at": old,
            },
            {
                "id": "queued-analysis",
                "kind": "analysis",
                "status": "retry",
                "not_before": old,
                "updated_at": old,
                "created_at": old,
            },
            {
                "id": "running-advance",
                "kind": "advance",
                "status": "running",
                "lease_expires_at": expired,
            },
        ],
    })

    monitor.scan_once()

    assert "lab-codex-stuck:queued-advance:queued" not in monitor.state["sent"]
    assert "lab-codex-stuck:queued-analysis:retry" in monitor.state["sent"]
    assert "lab-codex-stuck:running-advance:running" in monitor.state["sent"]

    queue["control"]["paused"] = False
    monitor.scan_once()

    assert "lab-codex-stuck:queued-advance:queued" in monitor.state["sent"]
    assert len(sent) == 3


def test_queue_status_failure_counts_as_robot_lab_outage(tmp_path):
    settings = configured(tmp_path)
    sent = []

    def fetcher(url, _token):
        if url == settings.orchestrator_url:
            return {"open": [], "recent": []}
        if url == settings.robot_lab_url:
            return []
        raise TimeoutError("queue endpoint unavailable")

    monitor = BlockerMonitor(
        settings,
        sender=lambda _recipient, message: sent.append(message),
        fetcher=fetcher,
    )

    monitor.scan_once()
    monitor.scan_once()

    assert len(sent) == 1
    assert "Robot Lab has failed 2 consecutive checks" in sent[0]
    assert monitor.state["robot_lab_initialized"] is False


def live_monitor(tmp_path, *, sender=None, outage_threshold=3):
    settings = replace(
        configured(tmp_path),
        robot_lab_status_url="http://lab.test/api/robot-status",
        robot_lab_public_url="https://public-lab.test",
        outage_threshold=outage_threshold,
    )
    sent = []
    payloads = {
        settings.orchestrator_url: {"open": [], "recent": []},
        settings.robot_lab_url: [],
        settings.robot_lab_queue_url: {"control": {"paused": False}},
        settings.public_website + "/healthz": {"ok": True, "driver": "command"},
        settings.robot_lab_status_url: {
            "health": {"fresh": True, "state": "healthy"},
            "observation_cameras": [{"fresh": True, "status": "streaming"}],
        },
    }

    def fetcher(url, token):
        if url == settings.public_website + "/healthz":
            assert token == ""  # Public probes never receive either private token.
        value = payloads[url]
        if isinstance(value, Exception):
            raise value
        return value

    monitor = BlockerMonitor(
        settings,
        sender=sender or (lambda _recipient, message: sent.append(message)),
        fetcher=fetcher,
    )
    return monitor, payloads, sent


def test_live_outages_need_three_checks_and_recover_once_across_restart(tmp_path):
    monitor, payloads, sent = live_monitor(tmp_path)
    status = payloads[monitor.settings.robot_lab_status_url]
    status["health"] = {"fresh": False, "state": "offline", "issue_code": "dns_failure"}
    status["observation_cameras"] = [
        {"fresh": False, "status": "unavailable", "permission_status": "denied"},
        {"fresh": False, "status": "unavailable", "permission_status": "restricted"},
    ]
    for _ in range(2):
        monitor.scan_once()
    assert sent == []
    monitor.scan_once()
    assert len(sent) == 2
    assert "network name cannot be resolved" in sent[0]
    assert "Check robot power" in sent[0]
    assert "macOS camera permission is denied or restricted" in sent[1]
    assert "Privacy & Security" in sent[1]
    assert all("https://public-lab.test" in message for message in sent)

    monitor = BlockerMonitor(monitor.settings, sender=monitor.sender, fetcher=monitor.fetcher)
    monitor.scan_once()
    assert len(sent) == 2
    status["health"] = {"fresh": True, "state": "checking"}
    status["observation_cameras"][1].update(fresh=True, status="streaming", permission_status="authorized")
    monitor.scan_once()
    monitor.scan_once()
    assert len(sent) == 4
    assert "fresh physical robot readings again" in sent[2]
    assert "fresh live camera view again" in sent[3]
    status["health"]["fresh"] = False
    for _ in range(3):
        monitor.scan_once()
    assert len(sent) == 5  # A distinct outage after recovery gets a new alert.


@pytest.mark.parametrize("intentional_status", ["paused", "in_use"])
def test_owned_cameras_do_not_alert_or_falsely_resolve_an_existing_outage(tmp_path, intentional_status):
    monitor, payloads, sent = live_monitor(tmp_path, outage_threshold=2)
    cameras = payloads[monitor.settings.robot_lab_status_url]["observation_cameras"]
    cameras[0].update(fresh=False, status="unavailable", permission_status="denied")
    monitor.scan_once()
    cameras[0]["status"] = intentional_status
    for _ in range(3):
        monitor.scan_once()
    assert sent == []
    cameras[0]["status"] = "unavailable"
    monitor.scan_once()
    assert sent == []  # The interrupted failure sequence starts again.
    monitor.scan_once()
    assert len(sent) == 1
    cameras[0]["status"] = intentional_status
    monitor.scan_once()
    assert len(sent) == 1  # Ownership is not evidence that capture recovered.


def test_only_total_camera_loss_alerts_and_idle_unconfigured_camera_is_quiet(tmp_path):
    monitor, payloads, sent = live_monitor(tmp_path, outage_threshold=2)
    status = payloads[monitor.settings.robot_lab_status_url]
    status["camera"] = {"fresh": False, "status": "stopped"}
    status["observation_cameras"] = []
    monitor.scan_once()
    monitor.scan_once()
    assert sent == []
    status["observation_cameras"] = [
        {"fresh": False, "status": "unavailable"},
        {"fresh": True, "status": "streaming"},
    ]
    monitor.scan_once()
    monitor.scan_once()
    assert sent == []
    status["observation_cameras"][1].update(fresh=False, status="stale")
    monitor.scan_once()
    monitor.scan_once()
    assert len(sent) == 1
    assert "No configured observation camera is providing a fresh image" in sent[0]
    assert "Check camera connections" in sent[0]


def test_public_tunnel_outage_is_separate_from_healthy_local_robot(tmp_path):
    monitor, payloads, sent = live_monitor(tmp_path, outage_threshold=2)
    public = monitor.settings.public_website + "/healthz"
    payloads[public] = HTTPError(public + "?key=SECRET", 502, "SECRET gateway detail", {}, None)
    monitor.scan_once()
    monitor.scan_once()
    monitor.scan_once()
    assert len(sent) == 1
    assert "public gateway cannot reach Robot Lab on the Mac" in sent[0]
    assert "restore its SSH tunnel" in sent[0]
    assert "SECRET" not in sent[0]
    assert monitor.state["outages"]["Robot Lab robot telemetry"]["count"] == 0


def test_local_auth_failure_is_not_reported_as_robot_connection_loss(tmp_path):
    monitor, payloads, sent = live_monitor(tmp_path, outage_threshold=2)
    local = monitor.settings.robot_lab_url
    payloads[local] = HTTPError(local, 401, "Bearer SECRET", {}, None)
    monitor.scan_once()
    monitor.scan_once()
    assert len(sent) == 1
    assert "monitor's access was rejected" in sent[0]
    assert "does not prove the robot is offline" in sent[0]
    assert "SECRET" not in sent[0]
    assert "Robot Lab robot telemetry" not in monitor.state["outages"]


def test_failed_camera_text_is_retried_and_delivery_permission_status_is_safe(tmp_path, capsys):
    attempts = []

    def sender(_recipient, message):
        attempts.append(message)
        if len(attempts) == 1:
            raise RuntimeError("SECRET Not authorized to send Apple events to Messages. (-1743)")

    monitor, payloads, _ = live_monitor(tmp_path, sender=sender, outage_threshold=2)
    camera = payloads[monitor.settings.robot_lab_status_url]["observation_cameras"][0]
    camera.update(fresh=False, status="unavailable", permission_status="denied")
    monitor.scan_once()
    monitor.scan_once()
    state = json.loads(monitor.settings.state_path.read_text())
    assert state["alert_delivery"]["status"] == "blocked"
    assert state["alert_delivery"]["error_code"] == "messages_automation_denied"
    assert state["alert_delivery"]["last_attempt_at"]
    assert "Automation" in state["alert_delivery"]["action"]
    assert state["last_scan_at"]
    assert "SECRET" not in json.dumps(state)
    assert "SECRET" not in capsys.readouterr().out
    assert "outage:Robot Lab observation cameras:0" not in state["sent"]
    monitor.scan_once()
    assert len(attempts) == 2
    assert monitor.state["alert_delivery"]["status"] == "ok"
    assert monitor.state["alert_delivery"]["last_success_at"]
    assert monitor.state["alert_delivery"]["error_code"] is None
    monitor.scan_once()
    assert len(attempts) == 2


def test_stale_status_response_cannot_resolve_robot_or_camera_outages(tmp_path):
    monitor, payloads, sent = live_monitor(tmp_path, outage_threshold=2)
    status = payloads[monitor.settings.robot_lab_status_url]
    status["observed_at"] = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    monitor.scan_once()
    monitor.scan_once()
    assert len(sent) == 2
    assert all("BLOCKER" in message for message in sent)


def test_public_probe_and_alert_link_strip_credentials(tmp_path):
    settings = replace(configured(tmp_path), robot_lab_public_url="https://user:SECRET@public-lab.test/?key=SECRET#SECRET")
    assert settings.public_website == "https://public-lab.test"


def test_default_outage_monitoring_is_enabled_every_thirty_seconds(tmp_path, monkeypatch):
    for key in ("HEXAPOD_ALERT_POLL_SECONDS", "HEXAPOD_ALERT_OUTAGE_CHECKS",
                "HEXAPOD_ROBOT_LAB_STATUS_URL", "HEXAPOD_ROBOT_LAB_PUBLIC_URL",
                "HEXAPOD_ROBOT_LAB_MONITOR_URL", "HEXAPOD_ROBOT_LAB_EXPERIMENTS_URL"):
        monkeypatch.delenv(key, raising=False)
    settings = MonitorSettings.from_env()
    assert settings.poll_seconds == 30
    assert settings.outage_threshold == 3
    assert settings.robot_lab_status_url.endswith("/api/robot-status")
    assert settings.robot_lab_url.endswith("/api/monitor-status")
    assert settings.robot_lab_public_url == "https://robot-lab.cwd1f0-new-cluster.coreweave.app"


def test_lightweight_monitor_response_combines_experiments_and_queue_in_one_fetch(tmp_path):
    settings = replace(configured(tmp_path), robot_lab_url="http://lab.test/api/monitor-status")
    payload = {"experiments": [{"id": "old", "status": "failed"}], "control": {"paused": True}}
    calls = []
    sent = []

    def fetcher(url, _token):
        calls.append(url)
        if url == settings.orchestrator_url:
            return {"open": [], "recent": []}
        assert url == settings.robot_lab_url
        return payload

    monitor = BlockerMonitor(settings, fetcher=fetcher, sender=lambda _recipient, message: sent.append(message))
    monitor.scan_once()
    assert sent == []
    assert calls == [settings.orchestrator_url, settings.robot_lab_url]
    payload["experiments"].append({
        "id": "new", "name": "new experiment", "status": "failed", "error": "camera unavailable",
        "codex_jobs": [analysis_job("new-stop", "stop")],
    })
    monitor.scan_once()
    assert len(sent) == 2
    assert "SAFETY STOP" in sent[0]
    assert "camera unavailable" in sent[1]
    assert settings.robot_lab_queue_url not in calls


def test_monitor_url_retains_legacy_environment_override(monkeypatch):
    monkeypatch.delenv("HEXAPOD_ROBOT_LAB_MONITOR_URL", raising=False)
    monkeypatch.setenv("HEXAPOD_ROBOT_LAB_EXPERIMENTS_URL", "http://legacy.test/api/experiments")
    assert MonitorSettings.from_env().robot_lab_url == "http://legacy.test/api/experiments"
    monkeypatch.setenv("HEXAPOD_ROBOT_LAB_MONITOR_URL", "http://new.test/api/monitor-status")
    assert MonitorSettings.from_env().robot_lab_url == "http://new.test/api/monitor-status"


def test_failed_sender_attempts_once_per_poll_without_skipping_outage_checks(tmp_path):
    attempts = []
    blocked = True

    def sender(_recipient, message):
        attempts.append(message)
        if blocked:
            raise RuntimeError("Not authorized to send Apple events to Messages. (-1743)")

    monitor, payloads, _ = live_monitor(tmp_path, sender=sender, outage_threshold=1)
    payloads[monitor.settings.orchestrator_url]["open"] = [
        {"id": "first", "summary": "First blocker"},
        {"id": "second", "summary": "Second blocker"},
    ]
    payloads[monitor.settings.public_website + "/healthz"] = TimeoutError("offline")
    status = payloads[monitor.settings.robot_lab_status_url]
    status["health"].update(fresh=False, state="offline")
    status["observation_cameras"][0].update(fresh=False, status="unavailable")
    fetcher = monitor.fetcher

    def observe_persistence(url, token):
        if url == monitor.settings.robot_lab_url and blocked:
            saved = json.loads(monitor.settings.state_path.read_text())
            assert saved["alert_delivery"]["status"] == "blocked"
        return fetcher(url, token)

    monitor.fetcher = observe_persistence
    monitor.scan_once()
    assert len(attempts) == 1
    assert monitor.state["sent"] == []
    sources = ["Robot Lab public website", "Robot Lab robot telemetry", "Robot Lab observation cameras"]
    assert all(monitor.state["outages"][source]["count"] == 1 for source in sources)
    monitor.scan_once()
    assert len(attempts) == 2
    assert all(monitor.state["outages"][source]["count"] == 2 for source in sources)
    blocked = False
    monitor.scan_once()
    assert len(attempts) == 7  # Both unsent blockers and all three outages remain pending.
    assert len(monitor.state["sent"]) == 5
    assert monitor.state["alert_delivery"]["status"] == "ok"


@pytest.mark.parametrize("fails", [False, True])
def test_send_test_records_actual_imessage_attempt_status(tmp_path, monkeypatch, fails):
    from hexapod_lab import blocker_monitor

    settings = configured(tmp_path)
    messages = []

    def sender(_recipient, message):
        messages.append(message)
        if fails:
            raise RuntimeError("Not authorized to send Apple events to Messages. (-1743)")

    original_monitor = BlockerMonitor
    monkeypatch.setattr(blocker_monitor.MonitorSettings, "from_env", lambda: settings)
    monkeypatch.setattr(blocker_monitor, "BlockerMonitor", lambda configured: original_monitor(configured, sender=sender))
    monkeypatch.setattr("sys.argv", ["hexapod-blocker-monitor", "--send-test"])
    assert blocker_monitor.main() == (1 if fails else 0)
    assert len(messages) == 1
    assert "iMessage test" in messages[0]
    assert "enabled" not in messages[0]
    state = json.loads(settings.state_path.read_text())
    assert state["alert_delivery"]["status"] == ("blocked" if fails else "ok")
    assert bool(state["alert_delivery"]["last_success_at"]) is not fails
    assert len(state["sent"]) == (0 if fails else 1)
