"""Bounded Mac service recovery. No robot commands or privacy-setting changes.

The observer supplies fresh facts; this module owns durable action budgets.
Command success is never evidence of recovery: three subsequent healthy samples
are required. The singleton file lock spans both intent persistence and execution.
"""

from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from typing import Callable


TCCD = "/System/Library/PrivateFrameworks/TCC.framework/Support/tccd"
ACTIONS = {"restart_lab", "restart_camera_tunnel", "restart_user_tccd"}
ISSUES = {
    "lab_unavailable": ("restart_lab", "Robot Lab is not responding."),
    "public_lab_unavailable": ("restart_camera_tunnel", "The public Robot Lab connection is unavailable."),
    "camera_capture_failed": ("restart_lab", "All robot cameras have persistent capture failures."),
    "camera_permission_denied": (None, "macOS camera permission requires attention."),
    "robot_controller_unavailable": (None, "The robot controller's power or network connection needs attention."),
    "macos_privacy_fd_exhaustion": ("restart_user_tccd", "The user's macOS privacy service has exhausted file descriptors."),
}


def epoch(value) -> float | None:
    try:
        if isinstance(value, datetime):
            return value.timestamp() if value.tzinfo else None
        if isinstance(value, (float, int)) and not isinstance(value, bool):
            return float(value)
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.timestamp() if parsed.tzinfo else None
    except (ValueError, TypeError, OverflowError):
        return None


def stamp(value: float) -> str:
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def fresh(value, now: float) -> bool:
    observed = epoch(value)
    return observed is not None and 0 <= now - observed <= 30


def tcc_evidence(tcc: dict, now: float) -> bool:
    return (
        fresh(tcc.get("observed_at"), now) and fresh(tcc.get("emfile_observed_at"), now)
        and type(tcc.get("pid")) is int and tcc["pid"] > 1
        and tcc.get("uid") == os.getuid() and os.getuid() != 0
        and tcc.get("executable") == TCCD
        and isinstance(tcc.get("start_time"), str) and bool(tcc["start_time"])
        and type(tcc.get("fd_count")) is int and tcc["fd_count"] >= 240
        and tcc.get("emfile") is True
    )


def diagnose(observations: dict, now: float) -> str | None:
    """Pure classification; ambiguity and legitimate camera ownership are inert."""
    tcc = observations.get("tcc") or {}
    if tcc_evidence(tcc, now):
        return "macos_privacy_fd_exhaustion"
    if (observations.get("local_api") or {}).get("ok") is False:
        return "lab_unavailable"
    robot = observations.get("robot") or {}
    if ((observations.get("local_api") or {}).get("ok") is True
            and (robot.get("reachable") is False or robot.get("fresh") is False)):
        return "robot_controller_unavailable"
    cameras = observations.get("cameras") or {}
    if cameras.get("state") == "permission_denied":
        return "camera_permission_denied"
    if cameras.get("state") == "capture_failed" and cameras.get("all_failed") is True:
        return "camera_capture_failed"
    if ((observations.get("local_api") or {}).get("ok") is True
            and (observations.get("public_api") or {}).get("ok") is False):
        return "public_lab_unavailable"
    return None


def healthy(observations: dict, episode: dict, now: float) -> bool:
    if not ((observations.get("local_api") or {}).get("ok") is True
            and (observations.get("public_api") or {}).get("ok") is True
            and (observations.get("cameras") or {}).get("state") == "healthy"
            and (observations.get("robot") or {}).get("reachable") is True
            and (observations.get("robot") or {}).get("fresh") is True):
        return False
    # A privacy-daemon episode also needs independent proof the daemon recovered.
    if "macos_privacy_fd_exhaustion" in episode.get("budgets", {}):
        tcc = observations.get("tcc") or {}
        if not (fresh(tcc.get("observed_at"), now)
                and tcc.get("uid") == os.getuid() and tcc.get("executable") == TCCD
                and type(tcc.get("pid")) is int and tcc["pid"] > 1
                and isinstance(tcc.get("start_time"), str) and bool(tcc["start_time"])
                and tcc.get("pid") != episode.get("original_tcc_pid")
                and type(tcc.get("fd_count")) is int and 0 < tcc["fd_count"] < 160):
            return False
    return True


class MacRecoveryExecutor:
    """Only fixed user LaunchAgents and the exact verified user tccd are allowed."""

    LABELS = {"restart_lab": "com.lbiewald.hexapod-lab",
              "restart_camera_tunnel": "com.lbiewald.hexapod-camera-tunnel"}

    def __init__(self, idle_guard: Callable | None = None):
        self.idle_guard = idle_guard

    def _guard(self) -> None:
        if self.idle_guard is None or self.idle_guard() is not True:
            raise RuntimeError("hardware_active_or_unobserved")

    @staticmethod
    def _run(argv: list[str], timeout: float = 15) -> str:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        if result.returncode:
            # Raw subprocess output could contain secrets; never publish it.
            raise RuntimeError(f"{Path(argv[0]).name} exited {result.returncode}")
        return result.stdout

    def _identity(self, pid: int) -> dict | None:
        result = subprocess.run(["/bin/ps", "-p", str(pid), "-o", "uid=,lstart=,comm="],
                                capture_output=True, text=True, timeout=5)
        fields = result.stdout.strip().split(maxsplit=6)
        if result.returncode or len(fields) != 7:
            return None
        return {"pid": pid, "uid": int(fields[0]), "start_time": " ".join(fields[1:6]),
                "executable": fields[6]}

    def _preflight_lab(self) -> None:
        support = Path.home() / "Library/Application Support/Hexapod Lab"
        script = support / "run-hexapod-lab.sh"
        python = support / "venv/bin/python"
        uv = Path("/opt/homebrew/bin/uv")
        if not all(path.is_file() for path in (script, python, uv)):
            raise RuntimeError("fixed_lab_runtime_missing")
        # Import only; no app construction, camera acquisition or network access.
        self._run([str(uv), "run", "--no-project", "--offline", "--no-sync", "--python", str(python),
                   "python", "-c", "import hexapod_lab.main, uvicorn, AVFoundation, cv2; "
                   "from hexapod_tracker import avfoundation_capture"], timeout=20)

    def preflight(self, action: str, _context: dict) -> None:
        if action in {"restart_lab", "restart_user_tccd"}:
            self._preflight_lab()

    def _fd_count(self, pid: int) -> int:
        output = self._run(["/usr/sbin/lsof", "-nP", "-a", "-p", str(pid), "-Ff"], timeout=4)
        return sum(line.startswith("f") and line[1:].isdigit() for line in output.splitlines())

    def _confirm_pressure(self, expected: dict, identity: dict) -> None:
        if not tcc_evidence(expected, time.time()):
            raise RuntimeError("privacy_evidence_expired")
        if self._identity(expected["pid"]) != identity:
            raise RuntimeError("privacy_process_identity_changed")
        if self._fd_count(expected["pid"]) < 240:
            raise RuntimeError("privacy_pressure_no_longer_confirmed")
        if not tcc_evidence(expected, time.time()):
            raise RuntimeError("privacy_evidence_expired")
        if self._identity(expected["pid"]) != identity:
            raise RuntimeError("privacy_process_identity_changed")

    def _replacement(self, previous_pid: int) -> bool:
        result = subprocess.run(["/usr/bin/pgrep", "-u", str(os.getuid()), "-x", "tccd"],
                                capture_output=True, text=True, timeout=3)
        pids = [int(part) for part in result.stdout.split() if part.isdigit()]
        if len(pids) != 1 or pids[0] == previous_pid:
            return False
        identity = self._identity(pids[0])
        if not identity or identity["uid"] != os.getuid() or identity["executable"] != TCCD:
            return False
        count = self._fd_count(pids[0])
        return 0 < count < 160 and self._identity(pids[0]) == identity

    def __call__(self, action: str, context: dict) -> None:
        if action not in ACTIONS or sys.platform != "darwin" or os.getuid() == 0:
            raise RuntimeError("recovery_action_not_allowed")
        if action in self.LABELS:
            target = f"gui/{os.getuid()}/{self.LABELS[action]}"
            self._run(["/bin/launchctl", "print", target])
            self._guard()
            self._run(["/bin/launchctl", "kickstart", "-k", target], timeout=30)
            return
        expected = context.get("tcc") or {}
        if not tcc_evidence(expected, time.time()):
            raise RuntimeError("privacy_evidence_expired")
        identity = {key: expected.get(key) for key in ("pid", "uid", "start_time", "executable")}
        pid = expected["pid"]
        if self._identity(pid) != identity:
            raise RuntimeError("privacy_process_identity_changed")
        self._guard()
        self._confirm_pressure(expected, identity)
        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if self._identity(pid) != identity:
                break
            time.sleep(0.2)
        # SIGKILL is limited to the same independently reverified process.
        if self._identity(pid) == identity:
            self._guard()
            # A slow ownership check may outlive the original error sample.
            if self._identity(pid) == identity:
                self._confirm_pressure(expected, identity)
        if self._identity(pid) == identity:
            os.kill(pid, signal.SIGKILL)
        # Daemon replacement must be independently observed before clearing the
        # Lab's cached denial. This reads process metadata, never the privacy DB.
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self._replacement(pid):
                self._guard()
                self._run(["/bin/launchctl", "kickstart", "-k",
                           f"gui/{os.getuid()}/{self.LABELS['restart_lab']}"], timeout=30)
                return
            time.sleep(0.5)
        raise RuntimeError("privacy_replacement_not_verified")


class RecoveryManager:
    def __init__(self, state_path: Path, enabled: bool = False,
                 now: Callable = time.time, executor: Callable | None = None,
                 idle_guard: Callable | None = None, action_guard: Callable | None = None):
        self.state_path = Path(state_path)
        self.enabled = enabled
        self.now = now
        self.executor = executor if executor is not None else MacRecoveryExecutor(idle_guard)
        self.action_guard = action_guard

    def _read(self) -> dict:
        try:
            state = json.loads(self.state_path.read_text())
            if not isinstance(state, dict) or state.get("schema_version") != 1:
                raise ValueError("invalid recovery state")
            return state
        except FileNotFoundError:
            return {"schema_version": 1, "status": "waiting", "issue_code": "none",
                    "reason_code": "none", "summary": "No recoverable failure detected.",
                    "action": None, "attempts": 0, "last_attempt_at": None, "detail": "",
                    "verified_at": None, "last_error": None, "event_id": 0, "history": []}

    def _save(self, state: dict, now: float, **changes) -> dict:
        before = tuple(state.get(key) for key in ("status", "issue_code", "reason_code", "action", "attempts"))
        state.update(changes)
        after = tuple(state.get(key) for key in ("status", "issue_code", "reason_code", "action", "attempts"))
        if before != after:
            state["event_id"] = int(state.get("event_id", 0)) + 1
        state["updated_at"] = stamp(now)
        fd, temporary = tempfile.mkstemp(prefix=".recovery-", dir=self.state_path.parent)
        try:
            with os.fdopen(fd, "w") as handle:
                os.fchmod(handle.fileno(), 0o600)
                json.dump(state, handle, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.state_path)
            directory = os.open(self.state_path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return self.public(state)

    @staticmethod
    def public(state: dict) -> dict:
        return {key: value for key, value in state.items() if not key.startswith("_")}

    def requires_privacy_probe(self) -> bool:
        """Keep collecting replacement evidence after authorization errors clear."""
        episode = self._read().get("_episode") or {}
        return "macos_privacy_fd_exhaustion" in episode.get("budgets", {})

    def _clock(self) -> float:
        now = epoch(self.now())
        if now is None:
            raise ValueError("Recovery clock must return a timezone-aware date or epoch")
        return now

    def step(self, observations: dict, idle_verified: bool) -> dict:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.state_path.with_suffix(self.state_path.suffix + ".lock")
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(fd, "w") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return self.public(self._read())
            # Invalid/corrupt persistent state fails closed: never erase budgets.
            state = self._read()
            now = self._clock()
            return self._step(state, observations, idle_verified is True, now)

    def _step(self, state: dict, observations: dict, idle: bool, now: float) -> dict:
        if not isinstance(observations, dict) or not fresh(observations.get("observed_at"), now):
            episode = state.get("_episode")
            if episode:
                episode["confirm_count"] = 0
                episode["healthy_count"] = 0
            return self._save(state, now, status="waiting", reason_code="observations_stale",
                              detail="Fresh independent observations are required.")
        observed = epoch(observations["observed_at"])
        episode = state.get("_episode")
        if episode and observed <= episode.get("last_seen", 0):
            return self._save(state, now)
        issue = diagnose(observations, now)
        if episode is None:
            if issue is None:
                return self._save(state, now)
            episode = {"started_at": stamp(now), "budgets": {}, "confirm_code": None,
                       "confirm_count": 0, "healthy_count": 0, "last_seen": 0}
            state["_episode"] = episode
        episode["last_seen"] = observed
        if issue is None:
            episode["confirm_count"] = 0
            # Collection must start after the action finished, including failed
            # actions that may have partially restarted a service. A snapshot
            # acquired while execution was in progress cannot prove recovery.
            after_attempt = max(epoch(state.get("last_attempt_at")) or 0,
                                epoch(episode.get("verification_after")) or 0)
            if observed > after_attempt and healthy(observations, episode, now):
                episode["healthy_count"] += 1
                if episode["healthy_count"] >= 3:
                    record = {"started_at": episode["started_at"], "verified_at": stamp(now),
                              "issue_code": state["issue_code"], "attempts_by_issue": episode["budgets"]}
                    state["history"] = (state.get("history", []) + [record])[-10:]
                    del state["_episode"]
                    return self._save(state, now, status="recovered", reason_code="none",
                                      verified_at=stamp(now), summary="Fresh observations confirm the services recovered.",
                                      detail="Three distinct healthy observations verified recovery.", last_error=None)
            else:
                episode["healthy_count"] = 0
            return self._save(state, now, status="verifying" if state.get("last_attempt_at") else "waiting",
                              reason_code="verification_pending", detail="Waiting for three fresh healthy observations.")
        episode["healthy_count"] = 0
        if issue == episode.get("confirm_code"):
            episode["confirm_count"] += 1
        else:
            episode["confirm_code"] = issue
            episode["confirm_count"] = 1
        action, summary = ISSUES[issue]
        attempts = episode["budgets"].get(issue, 0)
        changes = {"issue_code": issue, "action": action, "summary": summary,
                   "attempts": attempts, "verified_at": None}
        if action is None:
            return self._save(state, now, **changes, status="needs_attention", reason_code="manual_action_required")
        if not self.enabled:
            return self._save(state, now, **changes, status="waiting", reason_code="disabled")
        if not idle:
            return self._save(state, now, **changes, status="waiting", reason_code="hardware_active_or_unobserved")
        if episode["confirm_count"] < 3:
            return self._save(state, now, **changes, status="waiting", reason_code="confirming_failure")
        if attempts >= 2:
            return self._save(state, now, **changes, status="needs_attention", reason_code="attempts_exhausted")
        last_attempt = epoch(state.get("last_attempt_at"))
        if last_attempt is not None and now - last_attempt < 300:
            return self._save(state, now, **changes,
                              status="verifying" if issue == episode.get("attempt_issue") else "waiting",
                              reason_code="verification_pending" if issue == episode.get("attempt_issue") else "cooldown")
        runtime = observations.get("lab_runtime") or {}
        if action in {"restart_lab", "restart_user_tccd"} and not (runtime.get("ready") is True and fresh(runtime.get("observed_at"), now)):
            return self._save(state, now, **changes, status="needs_attention", reason_code="runtime_preflight_failed")
        if self.action_guard is None:
            return self._save(state, now, **changes, status="waiting", reason_code="hardware_active_or_unobserved",
                              detail="An atomic hardware ownership guard is required.")
        context = {"observed_at": observations["observed_at"], "tcc": observations.get("tcc") or {}}
        try:
            preflight = getattr(self.executor, "preflight", None)
            if preflight is not None:
                preflight(action, context)
        except Exception as exc:
            return self._save(state, now, **changes, status="needs_attention", reason_code="runtime_preflight_failed",
                              last_error=type(exc).__name__)
        try:
            with self.action_guard() as reserved:
                if reserved is not True:
                    return self._save(state, now, **changes, status="waiting", reason_code="hardware_active_or_unobserved")
                action_now = self._clock()
                if not fresh(observations.get("observed_at"), action_now):
                    episode["confirm_count"] = 0
                    return self._save(state, action_now, **changes, status="waiting", reason_code="observations_stale",
                                      detail="The failure observations expired during preflight and ownership checks.")
                return self._attempt(state, episode, issue, action, context, changes, action_now)
        except Exception as exc:
            # Guard acquisition failed before intent/side effects. Preserve any
            # already-persisted intent if a guard's exit itself failed.
            latest = self._read()
            return self._save(latest, now, status="waiting", reason_code="hardware_active_or_unobserved",
                              last_error=type(exc).__name__)

    def _attempt(self, state: dict, episode: dict, issue: str, action: str,
                 context: dict, changes: dict, now: float) -> dict:
        attempts = episode["budgets"].get(issue, 0)
        episode["budgets"][issue] = attempts + 1
        episode["attempt_issue"] = issue
        if action == "restart_user_tccd":
            episode["original_tcc_pid"] = context["tcc"]["pid"]
        changes["attempts"] = attempts + 1
        # Persist the intent before anything that can restart/signal a service.
        self._save(state, now, **changes, status="attempting", reason_code="none",
                   last_attempt_at=stamp(now), last_error=None, detail="Executing a bounded service recovery action.")
        try:
            self.executor(action, context)
        except Exception as exc:
            completed_at = max(now, self._clock())
            episode["verification_after"] = stamp(completed_at)
            return self._save(state, completed_at, status="needs_attention", reason_code="action_failed",
                              last_error=type(exc).__name__, detail="The recovery command failed; budget and cooldown remain in effect.")
        completed_at = max(now, self._clock())
        episode["verification_after"] = stamp(completed_at)
        return self._save(state, completed_at, status="verifying", reason_code="verification_pending",
                          detail="Command completed; waiting for fresh observations to prove recovery.")
