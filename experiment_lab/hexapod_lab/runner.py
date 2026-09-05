from datetime import datetime, timezone
import json
import hashlib
import math
from pathlib import Path
import random
import subprocess
import threading
import time
from typing import Any, Dict, Optional

from .config import Settings
from .db import Store


class ExperimentRunner:
    """Single-consumer worker: only one experiment may command the robot at once."""

    def __init__(
        self, store: Store, settings: Settings, layout_history: Optional[Any] = None
    ):
        self.store = store
        self.settings = settings
        self.layout_history = layout_history
        self.stop_event = threading.Event()
        self.wake_event = threading.Event()
        self.thread: Optional[threading.Thread] = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._loop, name="experiment-worker", daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.wake_event.set()
        if self.thread:
            self.thread.join(timeout=5)

    def wake(self):
        self.wake_event.set()

    def _loop(self):
        while not self.stop_event.is_set():
            experiment = self.store.claim_next()
            if experiment:
                self._execute(experiment)
            else:
                self.wake_event.wait(1)
                self.wake_event.clear()

    def _execute(self, experiment: Dict):
        run_dir = self.settings.data_dir / "experiments" / experiment["id"]
        run_dir.mkdir(parents=True, exist_ok=True)
        camera = None
        status = "failed"
        error = None
        result = {}
        try:
            if self.layout_history is not None:
                # Provenance must exist before camera capture begins. Analysis
                # of this run can then never silently use today's config.
                self.layout_history.pin_experiment(
                    experiment["id"],
                    recorded_at=datetime.now(timezone.utc).isoformat(),
                    pin_basis="recording_start",
                )
                self.layout_history.materialize_experiment(
                    run_dir, experiment["id"]
                )
            recorded = dict(experiment)
            if self.layout_history is not None:
                recorded["tag_layout_revision"] = (
                    self.layout_history.experiment_revision(experiment["id"])
                )
            (run_dir / "experiment.json").write_text(
                json.dumps(recorded, indent=2) + "\n"
            )
            camera = self._start_camera(run_dir)
            if self.settings.driver == "simulated":
                result = self._simulate(experiment, run_dir)
            elif self.settings.driver == "command":
                result = self._run_command(experiment, run_dir)
            else:
                raise RuntimeError("HEXAPOD_DRIVER must be simulated or command")
            current = self.store.get(experiment["id"])
            status = "cancelled" if current and current["cancel_requested"] else "succeeded"
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            result = {"error": error}
            status = "failed"
        finally:
            if camera is not None:
                try:
                    camera.terminate()
                    try:
                        camera.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        camera.kill()
                        camera.wait(timeout=5)
                except Exception as exc:
                    error = f"camera finalization failed: {type(exc).__name__}: {exc}"
                    status, result = "failed", {"error": error}
        # Publish terminal status only after the producer is closed and the
        # summary/manifest exist. Readers poll status as an evidence-ready
        # signal; publishing it earlier raced those artifact writes.
        finished_at = datetime.now(timezone.utc).isoformat()
        try:
            self._write_summary(experiment, run_dir, status, result,
                                finished_at=finished_at)
            self._write_manifest(run_dir)
        except Exception as exc:
            error = f"artifact finalization failed: {type(exc).__name__}: {exc}"
            status = "failed"
            # Best effort preserves a readable failure if only the first
            # serialization failed. Persistent filesystem errors remain in DB.
            try:
                self._write_summary(experiment, run_dir, status, {"error": error},
                                    finished_at=finished_at)
                self._write_manifest(run_dir)
            except Exception:
                pass
        self.store.finish(experiment["id"], status, error, finished_at=finished_at)

    def _start_camera(self, run_dir: Path):
        if not self.settings.camera_input:
            return None
        log = (run_dir / "camera.log").open("wb")
        command = ["ffmpeg", "-nostdin", "-y", "-i", self.settings.camera_input,
                   "-c:v", "libx264", "-preset", "veryfast", "-movflags", "+faststart",
                   str(run_dir / "video.mp4")]
        return subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)

    def _simulate(self, experiment: Dict, run_dir: Path):
        started = time.monotonic()
        samples = 0
        telemetry_path = run_dir / "telemetry.jsonl"
        duration = float(experiment["duration_seconds"])
        with telemetry_path.open("w") as telemetry:
            while time.monotonic() - started < duration:
                current = self.store.get(experiment["id"])
                if self.stop_event.is_set() or (current and current["cancel_requested"]):
                    break
                elapsed = time.monotonic() - started
                sample = {
                    "timestamp": datetime.now(timezone.utc).isoformat(), "elapsed_seconds": round(elapsed, 3),
                    "battery_volts": round(12.4 - elapsed * 0.002 + random.uniform(-0.02, 0.02), 3),
                    "body_roll_degrees": round(math.sin(elapsed * 2) * 1.5, 3),
                    "body_pitch_degrees": round(math.cos(elapsed * 1.7) * 1.2, 3),
                    "controller_temperature_c": round(41 + elapsed * 0.02, 2), "simulated": True,
                }
                telemetry.write(json.dumps(sample) + "\n")
                telemetry.flush()
                samples += 1
                time.sleep(min(0.1, max(0, duration - elapsed)))
        return {"telemetry_samples": samples, "driver": "simulated"}

    def _run_command(self, experiment: Dict, run_dir: Path):
        if not self.settings.robot_command:
            raise RuntimeError("HEXAPOD_ROBOT_COMMAND is required for command driver")
        env = {"HEXAPOD_EXPERIMENT_ID": experiment["id"], "HEXAPOD_RUN_DIR": str(run_dir)}
        import os
        process = subprocess.Popen(self.settings.robot_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, env={**os.environ, **env})
        deadline = time.monotonic() + float(experiment["duration_seconds"]) + 30
        payload = json.dumps(experiment)
        stdout = stderr = ""
        while True:
            try:
                stdout, stderr = process.communicate(payload, timeout=.25)
                break
            except subprocess.TimeoutExpired:
                payload = None
                current = self.store.get(experiment["id"])
                if self.stop_event.is_set() or (current and current["cancel_requested"]):
                    process.terminate()
                    try:
                        stdout, stderr = process.communicate(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill(); stdout, stderr = process.communicate()
                    break
                if time.monotonic() >= deadline:
                    process.kill(); stdout, stderr = process.communicate()
                    raise RuntimeError("robot command exceeded duration plus shutdown allowance")
        (run_dir / "telemetry.jsonl").write_text(stdout)
        (run_dir / "robot.stderr.log").write_text(stderr)
        if process.returncode:
            raise RuntimeError(f"robot command exited {process.returncode}")
        return {"telemetry_samples": len(stdout.splitlines()), "driver": "command"}

    def _write_summary(self, experiment: Dict, run_dir: Path, status: str, result: Dict,
                       *, finished_at: Optional[str] = None):
        artifacts = sorted(path.name for path in run_dir.iterdir() if path.is_file())
        stats = self._telemetry_stats(run_dir / "telemetry.jsonl")
        current = self.store.get(experiment["id"]) or experiment
        lines = [f"# {experiment['name']}", "", f"- Experiment ID: `{experiment['id']}`",
                 f"- Outcome: **{status}**", f"- Requested duration: {experiment['duration_seconds']} seconds",
                 f"- Driver: {result.get('driver', self.settings.driver)}",
                 f"- Started: {current.get('started_at') or 'not recorded'}",
                 f"- Finished: {finished_at or current.get('finished_at') or 'not recorded'}",
                 f"- Telemetry samples: {stats.get('samples', result.get('telemetry_samples', 0))}", "",
                 "## Intent", "", experiment.get("description") or "No description supplied.", "",
                 "## Parameters", "", "```json", json.dumps(experiment.get("parameters", {}), indent=2), "```", "",
                 "## Result", ""]
        if status == "failed":
            lines.append(f"The run failed: {result.get('error', 'unknown error')}")
        elif status == "cancelled":
            lines.append("The run stopped after a cancellation request.")
        else:
            lines.append("The runner completed without reporting an error.")
        if stats.get("fields"):
            lines += ["", "## Telemetry overview", "", "| Field | Min | Mean | Max |", "|---|---:|---:|---:|"]
            for field, values in stats["fields"].items():
                lines.append(f"| {field} | {values['min']:.4g} | {values['mean']:.4g} | {values['max']:.4g} |")
        lines += ["", "## Artifacts", ""] + [f"- `{name}`" for name in artifacts]
        (run_dir / "summary.md").write_text("\n".join(lines) + "\n")

    @staticmethod
    def _telemetry_stats(path: Path):
        fields = {}
        samples = 0
        if not path.exists():
            return {"samples": 0, "fields": {}}
        for line in path.read_text(errors="replace").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            samples += 1
            for key, value in row.items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    fields.setdefault(key, []).append(float(value))
        return {"samples": samples, "fields": {key: {"min": min(values), "max": max(values),
                "mean": sum(values) / len(values)} for key, values in fields.items()}}

    @staticmethod
    def _write_manifest(run_dir: Path):
        entries = []
        for path in sorted(run_dir.iterdir()):
            if path.is_file() and path.name != "manifest.json":
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                entries.append({"name": path.name, "bytes": path.stat().st_size, "sha256": digest})
        manifest = {"schema_version": 2, "artifacts": entries}
        context_path = run_dir / "vision-context.json"
        if context_path.is_file():
            try:
                manifest["vision_context"] = json.loads(
                    context_path.read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError(
                    "vision-context.json is unreadable; refusing an ambiguous manifest"
                ) from exc
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n"
        )
