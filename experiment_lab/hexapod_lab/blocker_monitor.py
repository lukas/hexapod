"""Text the operator only when Hexapod services need human intervention."""

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
from urllib.request import Request, urlopen


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
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def fetch_json(url: str, token: str, timeout: float = 15.0):
    headers = {"Accept": "application/json", "User-Agent": "hexapod-blocker-alerts/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(url, headers=headers), timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


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
                "HEXAPOD_ROBOT_LAB_EXPERIMENTS_URL",
                "http://127.0.0.1:8767/api/experiments",
            ),
            robot_lab_token=os.environ.get("HEXAPOD_LAB_VIEWER_TOKEN", "").strip(),
            robot_lab_queue_url=os.getenv(
                "HEXAPOD_ROBOT_LAB_CODEX_QUEUE_URL",
                "http://127.0.0.1:8767/api/codex-queue",
            ),
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
    ):
        self.settings = settings
        self.sender = sender
        self.fetcher = fetcher
        self.now = now
        self.state = self._load_state()

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
        try:
            self.sender(self.settings.recipient, message[:1500])
        except Exception as exc:  # keep pending so the next poll retries
            print(f"alert delivery failed ({type(exc).__name__}): {exc}", flush=True)
            return False
        self.state["sent"].append(fingerprint)
        self.state["sent"] = self.state["sent"][-2000:]
        print(f"alert delivered: {fingerprint}", flush=True)
        return True

    def _source_ok(self, source: str) -> None:
        outage = self.state["outages"].setdefault(source, {"count": 0, "alerted": False})
        if outage.get("alerted"):
            generation = int(outage.get("generation", 0))
            if self._deliver(
                f"recovered:{source}:{generation}",
                f"Hexapod alert resolved: {source} is reachable again.",
            ):
                outage["alerted"] = False
                outage["generation"] = generation + 1
        outage["count"] = 0

    def _source_failed(self, source: str, exc: Exception) -> None:
        outage = self.state["outages"].setdefault(
            source, {"count": 0, "alerted": False, "generation": 0}
        )
        outage["count"] = int(outage.get("count", 0)) + 1
        if outage["count"] < self.settings.outage_threshold or outage.get("alerted"):
            return
        generation = int(outage.get("generation", 0))
        if self._deliver(
            f"outage:{source}:{generation}",
            f"Hexapod BLOCKER: {source} has failed {outage['count']} consecutive checks. "
            f"Latest error: {type(exc).__name__}. Please inspect the service.",
        ):
            outage["alerted"] = True

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
            experiments = self.fetcher(self.settings.robot_lab_url, self.settings.robot_lab_token)
            if not isinstance(experiments, list):
                raise ValueError("experiment response is not a list")
            queue = self.fetcher(
                self.settings.robot_lab_queue_url, self.settings.robot_lab_token
            )
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
        self._scan_orchestrator()
        self._scan_robot_lab()
        self.state["initialized"] = True
        self._save_state()

    def run(self) -> None:
        while True:
            self.scan_once()
            time.sleep(self.settings.poll_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--send-test", action="store_true")
    args = parser.parse_args()
    settings = MonitorSettings.from_env()
    settings.validate()
    if args.send_test:
        send_messages_text(
            settings.recipient,
            "Hexapod blocker alerts are enabled. Only actionable operator blockers, "
            "new Robot Lab failures, stuck runs, and persistent service outages will text you.",
        )
        return 0
    monitor = BlockerMonitor(settings)
    if args.once:
        monitor.scan_once()
    else:
        monitor.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
