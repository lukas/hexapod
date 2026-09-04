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
    set targetAddress to item 1 of argv
    set messageText to item 2 of argv
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
    """Send without interpolating untrusted alert text into AppleScript."""
    try:
        result = subprocess.run(
            ["/usr/bin/osascript", "-", recipient, message],
            input=APPLE_SCRIPT,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "Messages automation timed out; allow the alert process to control Messages"
        ) from exc
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
    poll_seconds: float = 30.0
    outage_threshold: int = 3
    stuck_grace_seconds: float = 120.0

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
            poll_seconds=float(os.getenv("HEXAPOD_ALERT_POLL_SECONDS", "30")),
            outage_threshold=max(1, int(os.getenv("HEXAPOD_ALERT_OUTAGE_CHECKS", "3"))),
            stuck_grace_seconds=float(os.getenv("HEXAPOD_ALERT_STUCK_GRACE_SECONDS", "120")),
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
        except Exception as exc:
            self._source_failed(source, exc)
            return
        self._source_ok(source)
        failed = [item for item in experiments if item.get("status") == "failed"]
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
            self.state["robot_lab_initialized"] = True
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
