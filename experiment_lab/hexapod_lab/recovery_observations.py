"""Passive, independent preflight facts for bounded Robot Lab service recovery."""

import ast
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import plistlib
import re
import sqlite3
import sys
from urllib.parse import urlsplit, urlunsplit

from .macos_privacy_status import MacOSPrivacyStatus
from .robot_status import RobotStatusService


TCCD_EXECUTABLE = "/System/Library/PrivateFrameworks/TCC.framework/Support/tccd"
LAB_LABEL = "com.lbiewald.hexapod-lab"


def _time(value):
    try:
        if isinstance(value, (float, int)) and not isinstance(value, bool):
            return datetime.fromtimestamp(value, timezone.utc)
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result if result.tzinfo else result.replace(tzinfo=timezone.utc)
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None


def _fresh(value, now, seconds=30):
    stamp = _time(value)
    return stamp is not None and -2 <= (now - stamp).total_seconds() <= seconds


def _offline(parameters):
    return isinstance(parameters, dict) and (
        parameters.get("robot_motion") is False or
        ("robot_motion" not in parameters and parameters.get("simulation_only") is True)
    )


def _database_idle(con, now):
    if con.execute("SELECT 1 FROM experiments WHERE status IN ('running','cancelling') LIMIT 1").fetchone():
        return {"verified": False, "reason": "experiment_active"}
    lanes = con.execute("SELECT lease_expires_at FROM codex_hardware_lane").fetchall()
    if any(_time(row[0]) is None or _time(row[0]) >= now for row in lanes):
        return {"verified": False, "reason": "hardware_lease_active"}
    jobs = con.execute(
        "SELECT experiment.parameters_json FROM codex_jobs AS job "
        "LEFT JOIN experiments AS experiment ON experiment.id=job.experiment_id "
        "WHERE job.kind='advance' AND job.status='running'"
    ).fetchall()
    if any(not _offline(json.loads(row[0]) if row[0] else None) for row in jobs):
        return {"verified": False, "reason": "hardware_job_active"}
    has_engineering = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='codex_engineering_jobs'"
    ).fetchone()
    if has_engineering:
        engineering = con.execute(
            "SELECT source_context_json FROM codex_engineering_jobs WHERE status='running'"
        ).fetchall()
        for row in engineering:
            source = json.loads(row[0])
            experiment = source.get("experiment") if isinstance(source, dict) else None
            parameters = experiment.get("parameters") if isinstance(experiment, dict) else None
            if not _offline(parameters):
                return {"verified": False, "reason": "hardware_engineering_active"}
    return {"verified": True, "reason": None}


def database_idle(path, now):
    """Open SQLite read-only; never instantiate Store (which migrates/writes)."""
    try:
        with closing(sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True, timeout=2)) as con:
            con.execute("PRAGMA query_only=ON")
            con.execute("BEGIN")
            return _database_idle(con, now)
    except (OSError, sqlite3.Error, ValueError, TypeError):
        return {"verified": False, "reason": "ownership_unknown"}


def physical_idle(robot, now):
    if not isinstance(robot, dict):
        return {"verified": False, "reason": "robot_unavailable"}
    servo = robot.get("servo")
    physical = robot.get("dry_run") is False and robot.get("sim") is not True and robot.get("simulated") is not True
    if not physical or not isinstance(servo, dict):
        return {"verified": False, "reason": "physical_robot_unverified"}
    if not _fresh(servo.get("ts"), now) or servo.get("stale") is True:
        return {"verified": False, "reason": "robot_telemetry_stale"}
    temperature = servo.get("max_temp_c")
    warn = servo.get("warn_c", 55)
    normal_temperature = (isinstance(temperature, (int, float)) and not isinstance(temperature, bool)
                          and isinstance(warn, (int, float)) and not isinstance(warn, bool)
                          and math.isfinite(temperature) and 0 <= temperature < min(warn, 55))
    healthy = (servo.get("ok") is True and servo.get("live") == servo.get("expected") == 18
               and all(servo.get(field) == [] for field in ("missing", "hot", "tripped"))
               and normal_temperature and robot.get("bus_quarantined") is not True)
    if not healthy:
        return {"verified": False, "reason": "robot_health_unverified"}
    demo = robot.get("demo")
    # api/core.py emits limp for a disarmed inactive controller. Normal bus
    # state omits torque_state; quarantine/recovery emits unverified + error.
    limp = (robot.get("activity") == "limp" and robot.get("bus_available") is True
            and robot.get("bus_quarantined") is False and robot.get("torque_state") in {None, "off"})
    explicit_idle = robot.get("activity") == "idle" and robot.get("torque_state") == "off"
    if (robot.get("armed") is not False or not (limp or explicit_idle) or not isinstance(demo, dict)
            or demo.get("running") is not False):
        return {"verified": False, "reason": "robot_idle_unverified"}
    return {"verified": True, "reason": None, "sample_at": servo["ts"]}


def camera_facts(status, now):
    unknown = {"state": "unknown", "all_failed": False}
    if not isinstance(status, dict) or not _fresh(status.get("observed_at"), now):
        return unknown
    cameras = status.get("observation_cameras", status.get("cameras"))
    if not isinstance(cameras, list) or not cameras or any(not isinstance(item, dict) for item in cameras):
        return unknown
    robot_cameras = [item for item in cameras if str(item.get("id", "")).startswith("robot-")]
    if robot_cameras:
        cameras = robot_cameras
    if any(item.get("fresh") is True for item in cameras):
        return {"state": "healthy", "all_failed": False}
    for state in ("paused", "in_use"):
        if any(item.get("status") == state for item in cameras):
            return {"state": state, "all_failed": False}
    if any(item.get("permission_status") in {"denied", "restricted"} for item in cameras):
        return {"state": "permission_denied", "all_failed": True}
    for item in cameras:
        error = str(item.get("error") or "").lower()
        if (item.get("permission_status") != "authorized"
                or any(word in error for word in ("disconnected", "suspended", "ambiguous", "covered", "no useful detail"))):
            return unknown
        if item.get("status") != "stale" and not any(word in error for word in (
            "stopped delivering frames", "frame timeout", "capture failed", "encode observation frame", "no native 420v frame",
        )):
            return unknown
    return {"state": "capture_failed", "all_failed": True}


def runtime_preflight(runtime_dir, launchagent_path, now):
    runtime = Path(runtime_dir)
    script = runtime / "run-hexapod-lab.sh"
    entrypoint = runtime / "venv/bin/hexapod-lab"
    try:
        config = plistlib.loads(Path(launchagent_path).read_bytes())
        if config.get("Label") != LAB_LABEL or config.get("ProgramArguments") != [str(script)]:
            raise ValueError("unexpected launch target")
        if not all(path.is_file() and os.access(path, os.X_OK) for path in (script, entrypoint)):
            raise ValueError("missing executable")
        script_source = script.read_text()
        if f'exec "{entrypoint}"' not in script_source:
            raise ValueError("unexpected runtime entrypoint")
        ast.parse(entrypoint.read_text())
        packages = list((runtime / "venv/lib").glob("python*/site-packages/hexapod_lab"))
        if len(packages) != 1:
            raise ValueError("ambiguous installed package")
        for name in ("__init__.py", "main.py", "config.py", "db.py", "robot_status.py", "observation_cameras.py"):
            ast.parse((packages[0] / name).read_text())
        ready = True
    except (OSError, ValueError, SyntaxError, plistlib.InvalidFileException):
        ready = False
    return {"ready": ready, "observed_at": now.isoformat()}


class RecoveryPrivacyProbe(MacOSPrivacyStatus):
    """Reuse the bounded probe, retaining only identity and dated error facts."""

    def __init__(self, now=None):
        super().__init__()
        self.now = now or (lambda: datetime.now(timezone.utc))
        self._identity_before = None
        self._emfile_at = None

    def _identity(self, pid):
        fields = super()._run(["/bin/ps", "-p", str(pid), "-o", "uid=,lstart=,comm="]).strip().split(None, 6)
        if len(fields) != 7 or not fields[0].isdigit():
            raise ValueError("process identity unavailable")
        return {"pid": int(pid), "uid": int(fields[0]), "start_time": " ".join(fields[1:6]), "executable": fields[6]}

    def _run(self, arguments):
        output = super()._run(arguments)
        if arguments[0] == "/usr/bin/pgrep":
            pids = output.split()
            if len(pids) == 1 and pids[0].isdigit():
                self._identity_before = self._identity(pids[0])
        elif arguments[0] == "/usr/bin/log":
            for line in output.splitlines():
                if not ("too many open files" in line.lower() or
                        ("SecStaticCodeCreateWithPath" in line and re.search(r"\b100024\b", line))):
                    continue
                match = re.match(r"(\d{4}-\d\d-\d\d[ T]\d\d:\d\d:\d\d(?:\.\d+)?(?:[+-]\d\d:?\d\d)?)", line)
                if match:
                    stamp = datetime.fromisoformat(match[1])
                    if stamp.tzinfo is None:
                        stamp = stamp.replace(tzinfo=datetime.now().astimezone().tzinfo)
                    if self._emfile_at is None or stamp > self._emfile_at:
                        self._emfile_at = stamp
        return output

    def collect(self):
        if sys.platform != "darwin":
            return {"state": "unknown"}
        self._identity_before = None
        self._emfile_at = None
        try:
            status = self._probe()
            identity = self._identity_before
            if (not identity or identity["uid"] != os.getuid() or identity["executable"] != TCCD_EXECUTABLE
                    or self._identity(identity["pid"]) != identity):
                return {"state": "unknown"}
            return {**identity, "state": status["state"], "fd_count": status.get("open_file_count", 0),
                    "emfile": status["state"] == "exhausted", "observed_at": self.now().isoformat(),
                    "emfile_observed_at": self._emfile_at.isoformat() if self._emfile_at else None}
        except Exception:
            return {"state": "unknown"}


class RecoveryObservations:
    def __init__(self, settings, fetcher, *, now=None, data_dir=None, runtime_dir=None,
                 launchagent_path=None, hub_url="http://127.0.0.1:8898/api/hub", privacy_probe=None):
        self.settings, self.fetcher = settings, fetcher
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.data_dir = Path(data_dir or settings.state_path.parent)
        self.runtime_dir = Path(runtime_dir or self.data_dir.parent)
        self.launchagent_path = Path(launchagent_path or Path.home() / "Library/LaunchAgents" / (LAB_LABEL + ".plist"))
        parsed = urlsplit(hub_url)
        if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}
                or parsed.port != 8898 or parsed.path != "/api/hub" or parsed.username
                or parsed.password or parsed.query or parsed.fragment):
            raise ValueError("Recovery requires the fixed local robot hub")
        self.hub_url = hub_url
        status_url = urlsplit(settings.robot_lab_status_url)
        if (status_url.scheme != "http" or status_url.hostname not in {"127.0.0.1", "localhost"}
                or status_url.port != 8767 or status_url.path != "/api/robot-status" or status_url.username
                or status_url.password or status_url.query or status_url.fragment):
            raise ValueError("Recovery requires the fixed local Robot Lab status endpoint")
        self.privacy_probe = privacy_probe or RecoveryPrivacyProbe(self.now)

    def _read(self, url, token=""):
        try:
            payload = self.fetcher(url, token)
            return payload if isinstance(payload, dict) else None
        except Exception:
            return None

    def _robot(self):
        parsed = urlsplit(self.hub_url)
        service = RobotStatusService(vision_url=urlunsplit((parsed.scheme, parsed.netloc, "/api/vision/state", "", "")))
        service._fetch_json = lambda url: self._read(url)
        # This resolver accepts only verified physical targets on local IPv4 :8080
        # and otherwise retains the fixed hexapod.local status URL.
        return self._read(service._resolve_robot_url())

    def verify_idle(self):
        """Recheck ownership and fresh disarmed telemetry immediately before an action."""
        robot = self._robot()
        now = self.now()
        return (physical_idle(robot, now)["verified"]
                and database_idle(self.data_dir / "lab.sqlite3", now)["verified"])

    def idle_verified(self):
        return self.verify_idle()

    @contextmanager
    def action_guard(self):
        """Reserve scheduler admission without changing rows, for one short action."""
        path = self.data_dir / "lab.sqlite3"
        con = None
        try:
            con = sqlite3.connect(path.resolve().as_uri() + "?mode=rw", uri=True, timeout=2)
            con.execute("BEGIN IMMEDIATE")
            con.execute("PRAGMA query_only=ON")
            ownership = _database_idle(con, self.now())
            if not ownership["verified"] or not physical_idle(self._robot(), self.now())["verified"]:
                raise RuntimeError("Robot recovery requires verified idle ownership and telemetry")
        except Exception:
            if con is not None:
                con.rollback()
                con.close()
            raise RuntimeError("Robot recovery could not reserve a verified idle controller") from None
        try:
            yield True
        finally:
            con.rollback()
            con.close()

    def collect(self, alert_delivery=None, *, verify_privacy=False):
        started_at = self.now()
        parsed = urlsplit(self.settings.robot_lab_status_url)
        local_health = urlunsplit((parsed.scheme, parsed.netloc, "/healthz", "", ""))
        with ThreadPoolExecutor(max_workers=4) as pool:
            local_future = pool.submit(self._read, local_health)
            public_future = pool.submit(self._read, self.settings.public_website + "/healthz")
            status_future = pool.submit(self._read, self.settings.robot_lab_status_url, self.settings.robot_lab_token)
            robot_future = pool.submit(self._robot)
            local, public, status, robot = (future.result() for future in (local_future, public_future, status_future, robot_future))
        now = self.now()
        cameras = camera_facts(status, now)
        delivery_error = (alert_delivery or {}).get("error_code")
        tcc = {"state": "unchecked"}
        if verify_privacy or cameras["state"] == "permission_denied" or delivery_error == "messages_automation_denied":
            try:
                tcc = self.privacy_probe.collect()
            except Exception:
                tcc = {"state": "unknown"}
        now = self.now()
        ownership = database_idle(self.data_dir / "lab.sqlite3", now)
        robot_idle = physical_idle(robot, now)
        idle_verified = ownership["verified"] and robot_idle["verified"]
        return {
            # Date the aggregate at its oldest possible observation, so a slow
            # probe cannot relabel earlier API evidence as newly observed.
            "observed_at": started_at.isoformat(),
            "local_api": {"ok": isinstance(local, dict) and local.get("ok") is True},
            "public_api": {"ok": isinstance(public, dict) and public.get("ok") is True},
            "cameras": camera_facts(status, now),
            "robot": {"reachable": isinstance(robot, dict), "idle": robot_idle["verified"],
                      "fresh": isinstance(robot, dict) and robot.get("dry_run") is False
                      and robot.get("sim") is not True and robot.get("simulated") is not True
                      and isinstance(robot.get("servo"), dict) and robot["servo"].get("stale") is not True
                      and _fresh(robot["servo"].get("ts"), now)},
            "lab_runtime": runtime_preflight(self.runtime_dir, self.launchagent_path, now),
            "tcc": tcc, "idle_verified": idle_verified,
            "idle": {"verified": idle_verified, "reasons": [value["reason"] for value in (ownership, robot_idle) if value["reason"]],
                     "robot_sample_at": robot_idle.get("sample_at")},
        }
