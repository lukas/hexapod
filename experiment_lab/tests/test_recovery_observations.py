from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import plistlib
import sqlite3
from types import SimpleNamespace

import pytest

from hexapod_lab.blocker_monitor import MonitorSettings
from hexapod_lab.macos_privacy_status import MacOSPrivacyStatus
from hexapod_lab.recovery_observations import (
    LAB_LABEL, TCCD_EXECUTABLE, RecoveryObservations, RecoveryPrivacyProbe,
    camera_facts, database_idle, physical_idle, runtime_preflight,
)


NOW = datetime(2026, 9, 6, 6, tzinfo=timezone.utc)


def idle_database(tmp_path):
    path = tmp_path / "data/lab.sqlite3"
    path.parent.mkdir(exist_ok=True)
    with sqlite3.connect(path) as con:
        con.executescript("""
            CREATE TABLE experiments (id TEXT, parameters_json TEXT, status TEXT);
            CREATE TABLE codex_jobs (kind TEXT, status TEXT, experiment_id TEXT);
            CREATE TABLE codex_hardware_lane (lease_expires_at TEXT);
            CREATE TABLE codex_engineering_jobs (source_context_json TEXT, status TEXT);
        """)
    return path


def robot():
    return {"dry_run": False, "armed": False, "activity": "idle", "torque_state": "off",
            "demo": {"running": False}, "servo": {"ts": NOW.timestamp(), "ok": True,
            "live": 18, "expected": 18, "missing": [], "hot": [], "tripped": [], "max_temp_c": 33}}


def installed_runtime(tmp_path):
    script = tmp_path / "run-hexapod-lab.sh"
    entrypoint = tmp_path / "venv/bin/hexapod-lab"
    entrypoint.parent.mkdir(parents=True, exist_ok=True)
    entrypoint.write_text("#!/usr/bin/env python\nfrom hexapod_lab.main import run\nrun()\n")
    script.write_text(f'#!/bin/sh\nexec "{entrypoint}"\n')
    entrypoint.chmod(0o700)
    script.chmod(0o700)
    package = tmp_path / "venv/lib/python3.12/site-packages/hexapod_lab"
    package.mkdir(parents=True)
    for name in ("__init__.py", "main.py", "config.py", "db.py", "robot_status.py", "observation_cameras.py"):
        (package / name).write_text("raise RuntimeError('preflight must never import this module')\n")
    launchagent = tmp_path / "lab.plist"
    launchagent.write_bytes(plistlib.dumps({"Label": LAB_LABEL, "ProgramArguments": [str(script)]}))
    return launchagent


def collector(tmp_path):
    database = idle_database(tmp_path)
    launchagent = installed_runtime(tmp_path)
    settings = MonitorSettings(
        recipient="private", state_path=database.parent / "state.json",
        orchestrator_url="unused", orchestrator_token="private-orchestrator",
        robot_lab_url="http://127.0.0.1:8767/api/monitor-status", robot_lab_token="private-viewer",
    )
    calls = []
    values = {
        "http://127.0.0.1:8767/healthz": {"ok": True},
        settings.public_website + "/healthz": {"ok": True},
        settings.robot_lab_status_url: {"observed_at": NOW.isoformat(), "observation_cameras": [
            {"fresh": True, "status": "streaming", "permission_status": "authorized"},
        ]},
        "http://127.0.0.1:8898/api/hub": {"service": "hexapod-hub", "targets": {"robot": {
            "available": True, "ok": True, "service": "hexapod-web", "url": "http://192.168.1.10:8080",
        }}},
        "http://192.168.1.10:8080/api/robot": robot(),
        "http://hexapod.local:8080/api/robot": robot(),
    }

    def fetcher(url, token):
        calls.append((url, token))
        value = values[url]
        if isinstance(value, Exception):
            raise value
        return value

    probe = SimpleNamespace(collect=lambda: {"state": "normal"})
    instance = RecoveryObservations(settings, fetcher, now=lambda: NOW,
                                    launchagent_path=launchagent, privacy_probe=probe)
    return instance, values, calls


def test_independent_idle_facts_survive_dead_lab_without_scanning_transcripts(tmp_path, monkeypatch):
    monitor, values, calls = collector(tmp_path)
    values["http://127.0.0.1:8767/healthz"] = TimeoutError("private failure")
    values[monitor.settings.robot_lab_status_url] = ConnectionError("private failure")
    monkeypatch.setattr(Path, "iterdir", lambda _self: (_ for _ in ()).throw(AssertionError("no artifact enumeration")))
    facts = monitor.collect()
    assert facts["idle_verified"] is True
    assert facts["local_api"] == {"ok": False}
    assert facts["public_api"] == {"ok": True}
    assert facts["robot"] == {"reachable": True, "fresh": True, "idle": True}
    assert facts["lab_runtime"]["ready"] is True
    assert facts["cameras"] == {"state": "unknown", "all_failed": False}
    assert facts["tcc"]["state"] == "unchecked"
    assert all(token == "" for url, token in calls if url != monitor.settings.robot_lab_status_url)
    assert "private" not in json.dumps(facts)


@pytest.mark.parametrize("statement,reason", [
    ("INSERT INTO experiments VALUES ('a','{}','running')", "experiment_active"),
    ("INSERT INTO experiments VALUES ('a','{}','cancelling')", "experiment_active"),
    ("INSERT INTO codex_hardware_lane VALUES ('2026-09-06T06:01:00+00:00')", "hardware_lease_active"),
    ("INSERT INTO codex_hardware_lane VALUES ('malformed')", "hardware_lease_active"),
    ("INSERT INTO codex_jobs VALUES ('advance','running',NULL)", "hardware_job_active"),
    ("INSERT INTO codex_engineering_jobs VALUES ('{}','running')", "hardware_engineering_active"),
    ("INSERT INTO codex_engineering_jobs VALUES ('not-json','running')", "ownership_unknown"),
])
def test_database_activity_and_ambiguous_ownership_block_recovery(tmp_path, statement, reason):
    path = idle_database(tmp_path)
    with sqlite3.connect(path) as con:
        con.execute(statement)
    assert database_idle(path, NOW) == {"verified": False, "reason": reason}


def test_offline_jobs_and_expired_hardware_lease_do_not_block_idle(tmp_path):
    path = idle_database(tmp_path)
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO codex_hardware_lane VALUES (?)", ((NOW - timedelta(minutes=1)).isoformat(),))
        con.execute("INSERT INTO experiments VALUES ('a',?, 'succeeded')", (json.dumps({"simulation_only": True}),))
        con.execute("INSERT INTO codex_jobs VALUES ('advance','running','a')")
        con.execute("INSERT INTO codex_jobs VALUES ('analysis','running',NULL)")
        con.execute("INSERT INTO codex_engineering_jobs VALUES (?,'running')",
                    (json.dumps({"experiment": {"parameters": {"robot_motion": False}}}),))
    assert database_idle(path, NOW)["verified"] is True


def test_missing_database_is_unknown_and_never_created(tmp_path):
    path = tmp_path / "missing.sqlite3"
    assert database_idle(path, NOW)["verified"] is False
    assert not path.exists()


@pytest.mark.parametrize("changes", [
    {"dry_run": True}, {"sim": True}, {"simulated": True}, {"armed": True},
    {"activity": "driving"}, {"torque_state": "unverified"}, {"demo": {"running": True}},
    {"bus_quarantined": True},
])
def test_robot_idle_requires_physical_disarmed_inactive_state(changes):
    value = robot()
    value.update(changes)
    assert physical_idle(value, NOW)["verified"] is False


@pytest.mark.parametrize("changes", [
    {"ts": NOW.timestamp() - 31}, {"ts": NOW.timestamp() + 10}, {"stale": True},
    {"live": 17}, {"expected": 17}, {"missing": [3]}, {"max_temp_c": 60}, {"ok": False},
])
def test_robot_idle_requires_fresh_complete_normal_motor_readings(changes):
    value = robot()
    value["servo"].update(changes)
    assert physical_idle(value, NOW)["verified"] is False


def test_runtime_preflight_does_not_import_and_rejects_broken_entrypoint(tmp_path):
    launchagent = installed_runtime(tmp_path)
    assert runtime_preflight(tmp_path, launchagent, NOW)["ready"] is True
    (tmp_path / "venv/bin/hexapod-lab").write_text("def broken(\n")
    assert runtime_preflight(tmp_path, launchagent, NOW)["ready"] is False
    launchagent.write_bytes(plistlib.dumps({"Label": LAB_LABEL, "ProgramArguments": ["/arbitrary/script"]}))
    assert runtime_preflight(tmp_path, launchagent, NOW)["ready"] is False


@pytest.mark.parametrize("camera,state,all_failed", [
    ({"fresh": True}, "healthy", False),
    ({"status": "paused"}, "paused", False),
    ({"status": "in_use"}, "in_use", False),
    ({"permission_status": "denied"}, "permission_denied", True),
    ({"permission_status": "authorized", "status": "stale"}, "capture_failed", True),
    ({"permission_status": "authorized", "error": "Configured camera stopped delivering frames"}, "capture_failed", True),
    ({"permission_status": "authorized", "error": "No native 420v frame received"}, "capture_failed", True),
    ({"permission_status": "authorized", "error": "Configured camera is disconnected or suspended"}, "unknown", False),
    ({"permission_status": "authorized", "error": "Camera image has no useful detail; view may be covered"}, "unknown", False),
    ({"permission_status": "not_determined", "status": "unavailable"}, "unknown", False),
])
def test_camera_recovery_excludes_physical_or_permission_conditions(camera, state, all_failed):
    assert camera_facts({"observed_at": NOW.isoformat(), "observation_cameras": [camera]}, NOW) == {
        "state": state, "all_failed": all_failed,
    }


def test_privacy_probe_runs_only_during_auth_failure_and_exceptions_are_unknown(tmp_path):
    instance, values, _ = collector(tmp_path)
    attempts = []

    def fail():
        attempts.append(True)
        raise RuntimeError("private probe error")

    instance.privacy_probe.collect = fail
    assert instance.collect()["tcc"]["state"] == "unchecked"
    assert attempts == []
    assert instance.collect({"error_code": "messages_automation_denied"})["tcc"]["state"] == "unknown"
    values[instance.settings.robot_lab_status_url]["observation_cameras"] = [{"permission_status": "denied"}]
    assert instance.collect()["tcc"]["state"] == "unknown"
    assert len(attempts) == 2


def test_privacy_verification_continues_after_camera_permission_recovers(tmp_path):
    instance, _, _ = collector(tmp_path)
    calls = []

    def probe():
        calls.append(True)
        return {"state": "normal", "pid": 999, "fd_count": 10, "observed_at": NOW.isoformat()}

    instance.privacy_probe.collect = probe
    assert instance.collect()["tcc"]["state"] == "unchecked"
    facts = instance.collect(verify_privacy=True)
    assert facts["tcc"]["pid"] == 999
    assert calls == [True]


def test_optional_phone_does_not_mask_or_cause_robot_camera_failure():
    status = {"observed_at": NOW.isoformat(), "observation_cameras": [
        {"id": "robot-1", "fresh": False, "status": "stale", "permission_status": "authorized"},
        {"id": "robot-2", "fresh": False, "status": "stale", "permission_status": "authorized"},
        {"id": "iphone", "fresh": False, "status": "unavailable", "permission_status": "denied"},
    ]}
    assert camera_facts(status, NOW) == {"state": "capture_failed", "all_failed": True}
    status["observation_cameras"][-1]["fresh"] = True
    assert camera_facts(status, NOW) == {"state": "capture_failed", "all_failed": True}
    status["observation_cameras"][0].update(fresh=True, status="streaming")
    assert camera_facts(status, NOW) == {"state": "healthy", "all_failed": False}


@pytest.mark.parametrize("target", [
    "https://external.test:8080", "http://user:secret@192.168.1.10:8080", "http://192.168.1.10:9090",
    "http://8.8.8.8:8080", "http://192.168.1.10:8080?key=secret", "http://192.168.1.10:8080/cmd",
])
def test_untrusted_hub_target_never_receives_requests_or_credentials(tmp_path, target):
    instance, values, calls = collector(tmp_path)
    values[instance.hub_url]["targets"]["robot"]["url"] = target
    assert instance.verify_idle() is True
    assert calls == [(instance.hub_url, ""), ("http://hexapod.local:8080/api/robot", "")]


def test_custom_external_hub_or_status_url_is_rejected_before_fetch(tmp_path):
    instance, _, calls = collector(tmp_path)
    with pytest.raises(ValueError):
        RecoveryObservations(instance.settings, instance.fetcher, hub_url="http://external.test:8898/api/hub")
    with pytest.raises(ValueError):
        RecoveryObservations(replace(instance.settings, robot_lab_status_url="https://external.test/api/robot-status"), instance.fetcher)
    assert calls == []


def test_immediate_idle_guard_rechecks_database_after_prior_idle_snapshot(tmp_path):
    instance, _, _ = collector(tmp_path)
    assert instance.collect()["idle_verified"] is True
    with sqlite3.connect(instance.data_dir / "lab.sqlite3") as con:
        con.execute("INSERT INTO experiments VALUES ('a','{}','running')")
    assert instance.verify_idle() is False


def test_documented_normal_limp_state_is_idle_without_optional_torque_field():
    value = robot()
    value.update(activity="limp", bus_available=True, bus_quarantined=False)
    value.pop("torque_state")
    assert physical_idle(value, NOW)["verified"] is True
    value["torque_state"] = "unverified"
    assert physical_idle(value, NOW)["verified"] is False


def test_action_guard_blocks_new_claims_and_releases_without_writing_rows(tmp_path):
    instance, _, _ = collector(tmp_path)
    path = instance.data_dir / "lab.sqlite3"
    before = path.read_bytes()
    with instance.action_guard() as allowed:
        assert allowed is True
        assert instance.idle_verified() is True
        with sqlite3.connect(path, timeout=0.01) as competing:
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                competing.execute("BEGIN IMMEDIATE")
    assert path.read_bytes() == before
    with sqlite3.connect(path, timeout=0.01) as competing:
        competing.execute("BEGIN IMMEDIATE")
        competing.rollback()


def test_action_guard_rejects_new_activity_and_never_creates_missing_database(tmp_path):
    instance, _, _ = collector(tmp_path)
    with sqlite3.connect(instance.data_dir / "lab.sqlite3") as con:
        con.execute("INSERT INTO experiments VALUES ('a','{}','running')")
    with pytest.raises(RuntimeError, match="verified idle"):
        with instance.action_guard():
            pytest.fail("busy recovery action was admitted")
    instance.data_dir = tmp_path / "missing"
    with pytest.raises(RuntimeError, match="verified idle"):
        with instance.action_guard():
            pytest.fail("missing ownership database was admitted")
    assert not instance.data_dir.exists()


@pytest.mark.parametrize("replacement", [False, True])
def test_privacy_identity_and_timestamped_error_are_required(monkeypatch, replacement):
    import os

    calls = []

    def run(arguments):
        calls.append(arguments)
        if arguments[0] == "/usr/bin/pgrep":
            return "844\n"
        if arguments[0] == "/bin/ps":
            count = sum(call[0] == "/bin/ps" for call in calls)
            stamp = "23:00:01" if replacement and count == 2 else "23:00:00"
            return f"{os.getuid()} Sat Sep 5 {stamp} 2026 {TCCD_EXECUTABLE}\n"
        if arguments[0] == "/usr/sbin/lsof":
            return "p844\n" + "\n".join(f"f{number}" for number in range(250))
        if arguments[0] == "/usr/bin/log":
            return "2026-09-05 23:00:00.000-0700 tccd SecStaticCodeCreateWithPath(file:///private/secret) fails: 100024\n"
        raise AssertionError(arguments)

    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr(MacOSPrivacyStatus, "_run", staticmethod(run))
    facts = RecoveryPrivacyProbe(now=lambda: NOW).collect()
    if replacement:
        assert facts == {"state": "unknown"}
    else:
        assert facts["pid"] == 844
        assert facts["executable"] == TCCD_EXECUTABLE
        assert facts["fd_count"] == 250
        assert facts["emfile"] is True
        assert datetime.fromisoformat(facts["emfile_observed_at"]) == NOW
        assert "secret" not in json.dumps(facts)
