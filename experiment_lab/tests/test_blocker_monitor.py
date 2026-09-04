from datetime import datetime, timedelta, timezone

from hexapod_lab.blocker_monitor import BlockerMonitor, MonitorSettings


def configured(tmp_path):
    return MonitorSettings(
        recipient="+15555550123",
        state_path=tmp_path / "state.json",
        orchestrator_url="https://orchestrator.test/api/blockers",
        orchestrator_token="orchestrator-secret",
        robot_lab_url="http://lab.test/api/experiments",
        robot_lab_token="lab-secret",
        outage_threshold=2,
        stuck_grace_seconds=30,
    )


def test_new_blocker_failure_and_resolution_are_deduplicated(tmp_path):
    settings = configured(tmp_path)
    sent = []
    payloads = {
        settings.orchestrator_url: {"open": [], "recent": []},
        settings.robot_lab_url: [{"id": "old", "status": "failed"}],
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
        {"id": "new", "name": "hardware run", "status": "failed", "error": "camera lost"}
    )
    monitor.scan_once()
    monitor.scan_once()
    assert len(sent) == 2
    assert any("Need operator decision" in message for _, message in sent)
    assert any("camera lost" in message for _, message in sent)

    blocker.update({"resolved_at": "2026-09-04T12:00:00+00:00", "resolution": "picked A"})
    payloads[settings.orchestrator_url] = {"open": [], "recent": [blocker]}
    monitor.scan_once()
    assert len(sent) == 3
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
