"""The cameras for one run, without a daemon.

``hexapod-cameras session`` (in the tracker checkout) opens the cameras the
registry assigns to the wanted roles, records real video with per-frame
capture times, and publishes detections and floor poses into a directory:

    <run_dir>/camera/state.json         seq, per-camera detections, poses (old server shapes)
    <run_dir>/camera/latest_<role>.jpg  the newest frame, for the look and the recovery stills
    <run_dir>/camera/vision.jsonl       one line per state
    <run_dir>/camera/<role>.mov         native video with embedded frame timestamps
    <run_dir>/camera/<role>.mp4         older/fallback video + <role>_timestamps.csv

The loop starts one before the pre-run look and stops it after the run's
video has been described. The child is tied to our stdin pipe, so if this
process dies the cameras are released anyway; that is the whole point of not
having an always-on server (see hexapod-tracker's ``cameras.py``).
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from .config import Settings

CAMERA_DIR_NAME = "camera"


class CameraSession:
    def __init__(self, settings: Settings, run_dir: Path, *, roles: Optional[str] = None,
                 popen: Optional[Callable[..., Any]] = None, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep, log: Callable[[str], None] = print):
        self.settings = settings
        self.dir = Path(run_dir) / CAMERA_DIR_NAME
        self.roles = roles or settings.camera_roles
        self.popen, self.clock, self.sleep, self.log = popen or subprocess.Popen, clock, sleep, log   # resolved late so tests can patch it
        self.proc: Any = None
        self.ready = False
        self.reason = ""

    # -- lifecycle
    def command(self) -> list[str]:
        return ["uv", "run", "hexapod-cameras", "session", "--out", str(self.dir), "--roles", self.roles,
                "--hz", f"{self.settings.camera_state_hz:g}", "--fps", f"{self.settings.camera_fps:g}"]

    def start(self) -> bool:
        """Spawn the session and wait for its first state.json. False (with ``reason``) when it did not come."""
        if not self.settings.camera_session:
            self.reason = "camera session disabled in settings"
            return False
        self.dir.mkdir(parents=True, exist_ok=True)
        stale = self.dir / "state.json"
        if stale.exists():
            stale.unlink()
        log_file = open(self.dir / "session.log", "ab")
        try:
            self.proc = self.popen(self.command(), cwd=str(self.settings.tracker_checkout), stdin=subprocess.PIPE,
                                   stdout=log_file, stderr=subprocess.STDOUT)
        except OSError as exc:
            self.reason = f"could not start hexapod-cameras: {exc}"
            self.log("camera: " + self.reason)
            return False
        t0 = self.clock()
        while self.clock() - t0 < self.settings.camera_start_budget_s:
            if stale.exists() and self.state() is not None:
                self.ready = True
                return True
            if self.proc.poll() is not None:
                self.reason = f"hexapod-cameras exited {self.proc.returncode} before its first frame (see camera/session.log)"
                self.log("camera: " + self.reason)
                return False
            self.sleep(0.25)
        self.reason = f"no camera state after {self.settings.camera_start_budget_s:.0f} s (see camera/session.log)"
        self.log("camera: " + self.reason)
        self.stop()
        return False

    def stop(self, wait_s: float = 20.0) -> None:
        if self.proc is None:
            return
        try:
            (self.dir / "STOP").write_text("")
            if self.proc.stdin:
                self.proc.stdin.close()
            try:
                self.proc.wait(timeout=wait_s)
            except subprocess.TimeoutExpired:
                self.proc.terminate()
                self.proc.wait(timeout=5)
        except Exception:  # noqa: BLE001 - never let camera teardown hide the run's result
            pass
        finally:
            self.proc = None

    def __enter__(self) -> "CameraSession":
        self.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.stop()

    # -- reads
    def state(self) -> Optional[Dict[str, Any]]:
        try:
            return json.loads((self.dir / "state.json").read_text())
        except (OSError, ValueError):
            return None

    def latest_path(self, role: Optional[str] = None) -> Path:
        return self.dir / f"latest_{role or self.roles.split(',')[0].strip()}.jpg"

    def latest(self, role: Optional[str] = None) -> bytes:
        return self.latest_path(role).read_bytes()

    def video_path(self, role: Optional[str] = None) -> Optional[Path]:
        name = role or self.roles.split(',')[0].strip()
        for suffix in ("mov", "mp4"):
            p = self.dir / f"{name}.{suffix}"
            if p.exists():
                return p
        return None

    @property
    def camera_dir(self) -> Optional[Path]:
        """The directory for readers (walk.Session, zero check, run_hw), or None when not running."""
        return self.dir if self.ready else None
