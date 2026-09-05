from datetime import datetime, timedelta, timezone
from pathlib import Path

from hexapod_lab.blocker_monitor import (
    BlockerMonitor,
    MonitorSettings,
    send_messages_text,
)


def configured(tmp_path):
    return MonitorSettings(
        recipient="+15555550123",
        state_path=tmp_path / "state.json",
        orchestrator_url="https://orchestrator.test/api/blockers",
        orchestrator_token="orchestrator-secret",
        robot_lab_url="http://lab.test/api/experiments",
        robot_lab_token="lab-secret",
        robot_lab_queue_url="http://lab.test/api/codex-queue",
        outage_threshold=2,
        stuck_grace_seconds=30,
    )


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
