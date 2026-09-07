"""Diagnose lab outages, attempt bounded service recovery, and text the operator."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Callable, Optional
from urllib.error import HTTPError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


APPLE_SCRIPT = r'''
on run argv
    set targetAddress to read POSIX file (item 1 of argv) as «class utf8»
    set messageText to read POSIX file (item 2 of argv) as «class utf8»
    tell application "Messages"
        set targetService to first service whose service type = iMessage
        set targetBuddy to buddy targetAddress of targetService
        send messageText to targetBuddy
    end tell
end run
'''


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        raise HTTPError(request.full_url, code, "Monitor endpoint redirected", headers, fp)


def fetch_json(url: str, token: str, timeout: float = 15.0):
    headers = {"Accept": "application/json", "User-Agent": "hexapod-blocker-alerts/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    # Keep credentials on the configured endpoint, including during outages.
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    with opener.open(Request(url, headers=headers), timeout=timeout) as response:
        body = response.read(8 * 1024 * 1024 + 1)
        if len(body) > 8 * 1024 * 1024:
            raise ValueError("Monitor response exceeds size limit")
        return json.loads(body.decode("utf-8"))


def send_messages_text(recipient: str, message: str) -> None:
    """Send without putting private alert contents in script source or argv."""
    with tempfile.TemporaryDirectory(prefix="hexapod-alert-") as temporary:
        recipient_path = Path(temporary) / "recipient"
        message_path = Path(temporary) / "message"
        recipient_path.write_text(recipient, encoding="utf-8")
        message_path.write_text(message, encoding="utf-8")
        recipient_path.chmod(0o600)
        message_path.chmod(0o600)
        try:
            result = subprocess.run(
                [
                    "/usr/bin/osascript",
                    "-",
                    str(recipient_path),
                    str(message_path),
                ],
                input=APPLE_SCRIPT,
                text=True,
                capture_output=True,
                timeout=20,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                "Messages automation timed out; allow the alert process to control Messages"
            ) from None
    if result.returncode:
        detail = (result.stderr or result.stdout or "Messages rejected the send").strip()
        raise RuntimeError(detail[:500])


@dataclass(frozen=True)
class MonitorSettings:
    recipient: str
    state_path: Path
    orchestrator_url: str
    orchestrator_token: str
    robot_lab_url: str
    robot_lab_token: str
    robot_lab_queue_url: str = "http://127.0.0.1:8767/api/codex-queue"
    poll_seconds: float = 30.0
    outage_threshold: int = 3
    stuck_grace_seconds: float = 120.0
    codex_stuck_seconds: float = 1800.0
    robot_lab_status_url: str = "http://127.0.0.1:8767/api/robot-status"
    robot_lab_public_url: str = "https://robot-lab.cwd1f0-new-cluster.coreweave.app"
    auto_recovery: bool = False

    @property
    def public_website(self) -> str:
        # A configured URL may contain a first-visit key. Never text credentials.
        parsed = urlsplit(self.robot_lab_public_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return "https://robot-lab.cwd1f0-new-cluster.coreweave.app"
        host = parsed.hostname
        if ":" in host:
            host = f"[{host}]"
        if parsed.port:
            host += f":{parsed.port}"
        return urlunsplit((parsed.scheme, host, parsed.path.rstrip("/"), "", ""))

    @classmethod
    def from_env(cls) -> "MonitorSettings":
        data_dir = Path(
            os.getenv(
                "HEXAPOD_DATA_DIR",
                "~/Library/Application Support/Hexapod Lab/data",
            )
        ).expanduser()
        return cls(
            recipient=os.environ.get("HEXAPOD_ALERT_RECIPIENT", "").strip(),
            state_path=Path(
                os.getenv("HEXAPOD_ALERT_STATE", str(data_dir / "blocker-alert-state.json"))
            ).expanduser(),
            orchestrator_url=os.getenv(
                "HEXAPOD_ORCHESTRATOR_BLOCKERS_URL",
                "https://hexapod.cwd1f0-new-cluster.coreweave.app/api/blockers",
            ),
            orchestrator_token=os.environ.get("HEXAPOD_ORCHESTRATOR_TOKEN", "").strip(),
            robot_lab_url=os.getenv(
                "HEXAPOD_ROBOT_LAB_MONITOR_URL",
                os.getenv(
                    "HEXAPOD_ROBOT_LAB_EXPERIMENTS_URL",
                    "http://127.0.0.1:8767/api/monitor-status",
                ),
            ),
            robot_lab_token=os.environ.get("HEXAPOD_LAB_VIEWER_TOKEN", "").strip(),
            robot_lab_queue_url=os.getenv(
                "HEXAPOD_ROBOT_LAB_CODEX_QUEUE_URL",
                "http://127.0.0.1:8767/api/codex-queue",
            ),
            robot_lab_status_url=os.getenv(
                "HEXAPOD_ROBOT_LAB_STATUS_URL", "http://127.0.0.1:8767/api/robot-status"
            ),
            robot_lab_public_url=os.getenv(
                "HEXAPOD_ROBOT_LAB_PUBLIC_URL",
                "https://robot-lab.cwd1f0-new-cluster.coreweave.app",
            ),
            auto_recovery=os.getenv("HEXAPOD_AUTO_RECOVERY", "0").lower() in {"1", "true", "yes"},
            poll_seconds=float(os.getenv("HEXAPOD_ALERT_POLL_SECONDS", "30")),
            outage_threshold=max(1, int(os.getenv("HEXAPOD_ALERT_OUTAGE_CHECKS", "3"))),
            stuck_grace_seconds=float(os.getenv("HEXAPOD_ALERT_STUCK_GRACE_SECONDS", "120")),
            codex_stuck_seconds=float(os.getenv(
                "HEXAPOD_ALERT_CODEX_STUCK_SECONDS", "1800"
            )),
        )

    def validate(self) -> None:
        missing = []
        if not self.recipient:
            missing.append("HEXAPOD_ALERT_RECIPIENT")
        if not self.orchestrator_token:
            missing.append("HEXAPOD_ORCHESTRATOR_TOKEN")
        if not self.robot_lab_token:
            missing.append("HEXAPOD_LAB_VIEWER_TOKEN")
        if missing:
            raise RuntimeError("missing alert settings: " + ", ".join(missing))


class BlockerMonitor:
    def __init__(
        self,
        settings: MonitorSettings,
        sender: Callable[[str, str], None] = send_messages_text,
        fetcher: Callable[[str, str], object] = fetch_json,
        now: Callable[[], datetime] = _utcnow,
        recovery_manager=None,
        recovery_observer=None,
    ):
        self.settings = settings
        self.sender = sender
        self.fetcher = fetcher
        self.now = now
        self.state = self._load_state()
        self._send_failed_this_scan = False
        self.recovery_manager = recovery_manager
        self.recovery_observer = recovery_observer
        if settings.auto_recovery:
            try:
                from .recovery_observations import RecoveryObservations
                from .service_recovery import RecoveryManager
                if self.recovery_observer is None:
                    self.recovery_observer = RecoveryObservations(settings, fetcher, now=now)
                if self.recovery_manager is None:
                    self.recovery_manager = RecoveryManager(
                        settings.state_path.parent / "recovery-state.json", enabled=True, now=now,
                        idle_guard=self.recovery_observer.idle_verified,
                        action_guard=self.recovery_observer.action_guard,
                    )
            except Exception as exc:
                self.recovery_manager = None
                self.recovery_observer = None
                print(
                    f"automatic recovery setup failed ({type(exc).__name__}); "
                    "check the fixed local recovery endpoints and runtime; outage alerts remain active",
                    flush=True,
                )

    def _load_state(self) -> dict:
        try:
            value = json.loads(self.settings.state_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            value = {}
        return {
            "initialized": bool(value.get("initialized")),
            "robot_lab_initialized": bool(value.get("robot_lab_initialized")),
            "sent": list(value.get("sent", [])),
            "baseline_failed": list(value.get("baseline_failed", [])),
            "baseline_stuck": list(value.get("baseline_stuck", [])),
            "baseline_codex": list(value.get("baseline_codex", [])),
            "baseline_codex_stuck": list(
                value.get("baseline_codex_stuck", [])
            ),
            "baseline_codex_stops": list(
                value.get("baseline_codex_stops", [])
            ),
            "outages": dict(value.get("outages", {})),
            "alert_delivery": {
                "status": "unknown", "last_attempt_at": None, "last_success_at": None,
                "error_code": None, "action": None,
                **dict(value.get("alert_delivery", {})),
            },
            "last_scan_at": value.get("last_scan_at"),
        }

    def _save_state(self) -> None:
        path = self.settings.state_path
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self.state, handle, indent=2, sort_keys=True)
                handle.write("\n")
            os.replace(temporary, path)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass

    def _deliver(self, fingerprint: str, message: str) -> bool:
        if fingerprint in self.state["sent"]:
            return True
        if self._send_failed_this_scan:
            return False
        delivery = self.state["alert_delivery"]
        delivery["last_attempt_at"] = self.now().isoformat()
        try:
            self.sender(self.settings.recipient, message[:1500])
        except Exception as exc:  # keep pending so the next poll retries
            detail = str(exc).lower()
            if "-1743" in detail or "not authorized to send apple events" in detail:
                code = "messages_automation_denied"
                action = "Allow the alert process to control Messages in macOS Privacy & Security > Automation."
            elif isinstance(exc, subprocess.TimeoutExpired) or "timed out" in detail:
                code = "delivery_timeout"
                action = "Check Messages sign-in and allow the alert process to control Messages."
            else:
                code = "delivery_failed"
                action = "Check Messages sign-in, network access, and the alert process's Automation permission."
            delivery.update(status="blocked", error_code=code, action=action)
            self._send_failed_this_scan = True
            # Publish delivery failure before any remaining service probes.
            # One blocked Messages attempt per poll is enough; keep gathering
            # outage observations so failed automation cannot stall monitoring.
            self._save_state()
            print(f"alert delivery failed ({type(exc).__name__}); will retry", flush=True)
            return False
        delivery.update(
            status="ok", last_success_at=self.now().isoformat(), error_code=None, action=None
        )
        self.state["sent"].append(fingerprint)
        self.state["sent"] = self.state["sent"][-2000:]
        print(f"alert delivered: {fingerprint}", flush=True)
        return True

    def _source_ok(self, source: str, detail: str = "is reachable again") -> None:
        outage = self.state["outages"].setdefault(source, {"count": 0, "alerted": False})
        if outage.get("alerted"):
            generation = int(outage.get("generation", 0))
            if self._deliver(
                f"recovered:{source}:{generation}",
                f"Hexapod alert resolved: {source} {detail}.\n{self.settings.public_website}",
            ):
                outage["alerted"] = False
                outage["generation"] = generation + 1
        outage["count"] = 0

    def _source_unobserved(self, source: str) -> None:
        """Interrupt consecutive failures without inventing a recovery."""
        if source in self.state["outages"]:
            self.state["outages"][source]["count"] = 0

    def _source_failed(
        self, source: str, exc: Optional[Exception] = None, *, cause: str = "", action: str = ""
    ) -> None:
        outage = self.state["outages"].setdefault(
            source, {"count": 0, "alerted": False, "generation": 0}
        )
        outage["count"] = int(outage.get("count", 0)) + 1
        if outage["count"] < self.settings.outage_threshold or outage.get("alerted"):
            return
        generation = int(outage.get("generation", 0))
        if not cause:
            cause, action = self._service_failure(source, exc)
        if self._deliver(
            f"outage:{source}:{generation}",
            f"Hexapod BLOCKER: {source} has failed {outage['count']} consecutive checks. "
            f"{cause} {action}\n{self.settings.public_website}",
        ):
            outage["alerted"] = True

    @staticmethod
    def _service_failure(source: str, exc: Optional[Exception]) -> tuple[str, str]:
        public = source == "Robot Lab public website"
        if isinstance(exc, HTTPError) and exc.code in {401, 403}:
            if public:
                return (
                    "The public health endpoint unexpectedly requires sign-in.",
                    "Check the gateway authentication and restore the public health route.",
                )
            return (
                "The monitor's access was rejected; this does not prove the robot is offline.",
                "Restore the monitor's API credential and verify its read access.",
            )
        if public:
            if isinstance(exc, HTTPError) and exc.code in {502, 503, 504}:
                return (
                    "The public gateway cannot reach Robot Lab on the Mac.",
                    "Check the Mac Robot Lab service and restore its SSH tunnel.",
                )
            return (
                "The public website is unavailable or did not return a healthy response.",
                "Check the public gateway, SSH tunnel, and Mac network connection.",
            )
        if isinstance(exc, (ValueError, json.JSONDecodeError)):
            return (
                "The service returned an invalid monitoring response.",
                "Inspect the service log and restore its API response.",
            )
        if source.startswith("Robot Lab"):
            return (
                "The local Robot Lab API is not responding.",
                "Check the Mac Robot Lab LaunchAgent and its service log.",
            )
        return (
            "The service is not responding to the monitor.",
            "Check the orchestrator service and its network connection.",
        )

    def _scan_public_robot_lab(self) -> None:
        if not self.settings.robot_lab_public_url:
            return
        source = "Robot Lab public website"
        try:
            # /healthz is public; never forward private tokens to this probe.
            payload = self.fetcher(self.settings.public_website + "/healthz", "")
            if not isinstance(payload, dict) or payload.get("ok") is not True:
                raise ValueError("public service health check failed")
        except Exception as exc:
            self._source_failed(source, exc)
            return
        self._source_ok(source)

    def _scan_robot_status(self) -> None:
        if not self.settings.robot_lab_status_url:
            return
        source = "Robot Lab status API"
        robot_source = "Robot Lab robot telemetry"
        cameras_source = "Robot Lab observation cameras"
        try:
            payload = self.fetcher(self.settings.robot_lab_status_url, self.settings.robot_lab_token)
            if not isinstance(payload, dict) or not isinstance(payload.get("health"), dict):
                raise ValueError("robot status response has no health object")
            health = payload["health"]
            if type(health.get("fresh")) is not bool:
                raise ValueError("robot status response has no freshness observation")
        except Exception as exc:
            self._source_failed(source, exc)
            self._source_unobserved(robot_source)
            self._source_unobserved(cameras_source)
            return
        self._source_ok(source)
        observed_at = _parse_time(payload.get("observed_at"))
        expired = observed_at is not None and (self.now() - observed_at).total_seconds() > 45
        if health["fresh"] and not expired:
            self._source_ok(robot_source, "has fresh physical robot readings again")
        else:
            causes = {
                "dns_failure": "Robot Lab is online, but the robot controller's network name cannot be resolved.",
                "timeout": "Robot Lab is online, but the robot controller is timing out.",
                "connection_refused": "Robot Lab is online, but the robot controller is refusing connections.",
                "physical_robot_unverified": "Robot Lab is online, but its telemetry source is not a verified physical robot.",
            }
            self._source_failed(
                robot_source,
                cause=causes.get(health.get("issue_code"),
                    "Robot Lab is online, but the physical robot connection is unavailable."
                    if health.get("state") == "offline"
                    else "Robot Lab is online, but physical robot readings are stale or missing."),
                action="Check robot power, its network connection, and the robot web service before another test.",
            )

        cameras = payload.get("observation_cameras", payload.get("cameras", []))
        if not isinstance(cameras, list) or not cameras:
            self._source_unobserved(cameras_source)
            return
        cameras = [camera for camera in cameras if isinstance(camera, dict)]
        if not cameras:
            self._source_unobserved(cameras_source)
        elif any(camera.get("fresh") is True for camera in cameras) and not expired:
            self._source_ok(cameras_source, "has a fresh live camera view again")
        elif any(camera.get("status") in {"paused", "in_use"} for camera in cameras):
            # Capture intentionally yields to the hardware owner. It is unknown,
            # not an outage or a confirmed recovery of a previous camera failure.
            self._source_unobserved(cameras_source)
        else:
            denied = any(camera.get("permission_status") in {"denied", "restricted"}
                         for camera in cameras)
            self._source_failed(
                cameras_source,
                cause=("macOS camera permission is denied or restricted; no configured observation camera is live."
                       if denied else "No configured observation camera is providing a fresh image."),
                action=("Restore Camera access for the Robot Lab capture process in macOS Privacy & Security, then restart capture."
                        if denied else "Check camera connections and the Robot Lab capture service before another physical test."),
            )

    def _scan_orchestrator(self) -> None:
        source = "RL orchestrator"
        try:
            payload = self.fetcher(
                self.settings.orchestrator_url, self.settings.orchestrator_token
            )
            if not isinstance(payload, dict):
                raise ValueError("blocker response is not an object")
        except Exception as exc:
            self._source_failed(source, exc)
            return
        self._source_ok(source)
        for item in payload.get("open", []):
            blocker_id = str(item.get("id", "")).strip()
            if not blocker_id:
                continue
            summary = str(item.get("summary", "operator action required"))
            details = str(item.get("details", "")).strip()
            text = f"Hexapod RL BLOCKER: {summary}"
            if details:
                text += f"\n{details}"
            self._deliver(f"blocker:{blocker_id}", text)
        for item in payload.get("recent", []):
            blocker_id = str(item.get("id", "")).strip()
            if not blocker_id or not item.get("resolved_at"):
                continue
            if f"blocker:{blocker_id}" not in self.state["sent"]:
                continue
            resolution = str(item.get("resolution", "resolved")).strip() or "resolved"
            self._deliver(
                f"resolved:{blocker_id}",
                f"Hexapod RL blocker resolved: {item.get('summary', blocker_id)}\n{resolution}",
            )

    def _scan_robot_lab(self) -> None:
        source = "Robot Lab"
        try:
            payload = self.fetcher(self.settings.robot_lab_url, self.settings.robot_lab_token)
            if isinstance(payload, dict):
                experiments = payload.get("experiments")
                queue = payload
            else:
                # Retain explicitly configured legacy experiment/queue endpoints.
                experiments = payload
                queue = self.fetcher(
                    self.settings.robot_lab_queue_url, self.settings.robot_lab_token
                )
            if not isinstance(experiments, list):
                raise ValueError("experiment response is not a list")
            if not isinstance(queue, dict) or not isinstance(queue.get("control"), dict):
                raise ValueError("Codex queue response has no control object")
            queue_paused = queue["control"].get("paused")
            if type(queue_paused) is not bool:
                raise ValueError("Codex queue control.paused is not a boolean")
        except Exception as exc:
            self._source_failed(source, exc)
            return
        self._source_ok(source)
        failed = [item for item in experiments if item.get("status") == "failed"]
        codex_blocked = []
        codex_stuck = []
        codex_stops = []
        for item in experiments:
            jobs = item.get("codex_jobs") or []
            jobs_by_id = {
                str(job.get("id")): job
                for job in jobs
                if isinstance(job, dict) and job.get("id")
            }
            for job in jobs:
                result = job.get("result")
                if (
                    job.get("kind") == "analysis"
                    and job.get("status") == "succeeded"
                    and isinstance(result, dict)
                    and result.get("safety_disposition") == "stop"
                ):
                    codex_stops.append((item, job))
                if job.get("status") in {"blocked", "dead"}:
                    codex_blocked.append((item, job))
                    continue
                status = job.get("status")
                stale = False
                if status in {"queued", "retry"}:
                    if job.get("kind") == "advance" and queue_paused:
                        continue
                    dependency = jobs_by_id.get(str(job.get("depends_on_job_id")))
                    if dependency and dependency.get("status") in {
                        "awaiting_evidence", "queued", "running", "retry"
                    }:
                        continue
                    eligible_at = _parse_time(job.get("not_before")) or _parse_time(
                        job.get("updated_at")
                    )
                    stale = bool(
                        eligible_at
                        and self.now()
                        > eligible_at
                        + timedelta(seconds=self.settings.codex_stuck_seconds)
                    )
                elif status == "awaiting_evidence":
                    created_at = _parse_time(job.get("created_at"))
                    stale = bool(
                        created_at
                        and self.now()
                        > created_at
                        + timedelta(
                            seconds=max(
                                self.settings.codex_stuck_seconds,
                                1800 + self.settings.stuck_grace_seconds,
                            )
                        )
                    )
                elif status == "running":
                    lease_expires = _parse_time(job.get("lease_expires_at"))
                    stale = bool(
                        lease_expires
                        and self.now()
                        > lease_expires
                        + timedelta(seconds=self.settings.stuck_grace_seconds)
                    )
                if stale:
                    codex_stuck.append((item, job))
        now = self.now()
        stuck = []
        for item in experiments:
            if item.get("status") != "running":
                continue
            started = _parse_time(item.get("started_at"))
            duration = float(item.get("duration_seconds") or 0)
            if started and now > started + timedelta(
                seconds=duration + self.settings.stuck_grace_seconds
            ):
                stuck.append(item)
        if not self.state["robot_lab_initialized"]:
            self.state["baseline_failed"] = [str(item.get("id")) for item in failed]
            self.state["baseline_stuck"] = [str(item.get("id")) for item in stuck]
            self.state["baseline_codex"] = [str(job.get("id")) for _, job in codex_blocked]
            self.state["baseline_codex_stuck"] = [
                str(job.get("id")) for _, job in codex_stuck
            ]
            self.state["baseline_codex_stops"] = [
                str(job.get("id")) for _, job in codex_stops
            ]
            self.state["robot_lab_initialized"] = True
            return
        # Safety stops go first so the most actionable signal receives the
        # first Messages delivery attempt when macOS automation is unavailable.
        for item, job in codex_stops:
            job_id = str(job.get("id", ""))
            if not job_id or job_id in self.state["baseline_codex_stops"]:
                continue
            result = job["result"]
            learned = " ".join(str(result.get("what_we_learned") or "").split())
            findings_value = result.get("findings")
            findings = []
            if isinstance(findings_value, list):
                findings = [
                    " ".join(str(finding).split())
                    for finding in findings_value
                    if str(finding).strip()
                ]
            summary = learned[:600] or "Codex found evidence requiring a physical stop."
            if findings:
                summary += "\nKey findings: " + "; ".join(findings[:3])[:600]
            delivered = self._deliver(
                f"lab-codex-stop:{job_id}",
                f"Hexapod Robot Lab SAFETY STOP: Codex analysis for "
                f"{item.get('name', item.get('id', 'an experiment'))!r} requires "
                f"operator action.\n{summary}\nDo not run the next physical experiment. "
                "Inspect the robot and evidence, then explicitly resolve the Robot Lab "
                "Codex queue pause before resuming.",
            )
            if not delivered:
                # Do not queue several 20-second Messages automation timeouts
                # behind the highest-priority alert. The next poll retries it;
                # lower-priority alerts proceed after the stop is delivered.
                return
        for item in failed:
            experiment_id = str(item.get("id", ""))
            if not experiment_id or experiment_id in self.state["baseline_failed"]:
                continue
            error = str(item.get("error") or "unknown runner failure")
            self._deliver(
                f"lab-failed:{experiment_id}",
                f"Hexapod Robot Lab BLOCKER: experiment {item.get('name', experiment_id)!r} "
                f"failed. {error}",
            )
        for item in stuck:
            experiment_id = str(item.get("id", ""))
            if not experiment_id or experiment_id in self.state["baseline_stuck"]:
                continue
            self._deliver(
                f"lab-stuck:{experiment_id}",
                f"Hexapod Robot Lab BLOCKER: experiment {item.get('name', experiment_id)!r} "
                "is still running beyond its duration and shutdown allowance.",
            )
        for item, job in codex_blocked:
            job_id = str(job.get("id", ""))
            if not job_id or job_id in self.state["baseline_codex"]:
                continue
            reason = str(job.get("error") or "manual inspection is required")
            self._deliver(
                f"lab-codex:{job_id}:{job.get('status')}",
                f"Hexapod Robot Lab BLOCKER: Codex {job.get('kind', 'automation')} "
                f"for {item.get('name', item.get('id', 'an experiment'))!r} "
                f"is {job.get('status')}. {reason}",
            )
        for item, job in codex_stuck:
            job_id = str(job.get("id", ""))
            if (
                not job_id
                or job_id in self.state["baseline_codex_stuck"]
            ):
                continue
            self._deliver(
                f"lab-codex-stuck:{job_id}:{job.get('status')}",
                f"Hexapod Robot Lab BLOCKER: Codex {job.get('kind', 'automation')} "
                f"for {item.get('name', item.get('id', 'an experiment'))!r} "
                f"has remained {job.get('status')} past its expected deadline. "
                "Inspect the Codex supervisor and its log before assuming the "
                "experiment queue is advancing.",
            )

    def scan_once(self) -> None:
        self._send_failed_this_scan = False
        self._scan_recovery()
        self._scan_orchestrator()
        self._scan_robot_lab()
        self._scan_public_robot_lab()
        if not self.state["outages"].get("Robot Lab", {}).get("count"):
            self._scan_robot_status()
        else:
            for source in ("Robot Lab status API", "Robot Lab robot telemetry", "Robot Lab observation cameras"):
                self._source_unobserved(source)
        self.state["initialized"] = True
        self.state["last_scan_at"] = self.now().isoformat()
        self._save_state()

    def _scan_recovery(self) -> None:
        if not self.settings.auto_recovery or self.recovery_manager is None or self.recovery_observer is None:
            return
        try:
            verify_privacy = getattr(self.recovery_manager, "requires_privacy_probe", lambda: False)()
            observations = self.recovery_observer.collect(
                alert_delivery=self.state["alert_delivery"], verify_privacy=verify_privacy,
            )
            result = self.recovery_manager.step(
                observations, idle_verified=observations.get("idle_verified") is True,
            )
        except Exception as exc:
            # Failure of a recovery check must not take outage alerts down with it.
            print(f"automatic recovery check failed ({type(exc).__name__}); will retry", flush=True)
            return
        if not isinstance(result, dict) or not result.get("event_id") or result.get("issue_code") in {None, "none"}:
            return
        if result.get("status") not in {"waiting", "attempting", "verifying", "recovered", "needs_attention"}:
            return
        from .recovery_status import recovery_status
        view = recovery_status(self.settings.state_path.parent / "recovery-state.json", now=self.now())
        headline = view.get("headline") or view.get("summary") or "Robot Lab recovery update"
        details = [headline, view.get("summary"), view.get("detail"), view.get("action"), self.settings.public_website]
        self._deliver(
            f"recovery:{result['event_id']}",
            "Robot Lab: " + "\n".join(str(value) for value in details if value),
        )

    def run(self) -> None:
        while True:
            started = time.monotonic()
            self.scan_once()
            time.sleep(max(0, self.settings.poll_seconds - (time.monotonic() - started)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--send-test", action="store_true")
    args = parser.parse_args()
    settings = MonitorSettings.from_env()
    settings.validate()
    monitor = BlockerMonitor(settings)
    if args.send_test:
        delivered = monitor._deliver(
            f"send-test:{time.time_ns()}",
            "Robot Lab iMessage test. This checks the current Messages delivery path for outage alerts.",
        )
        monitor._save_state()
        return 0 if delivered else 1
    if args.once:
        monitor.scan_once()
    else:
        monitor.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
