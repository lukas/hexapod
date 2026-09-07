from datetime import datetime, timezone
import fcntl
import json
import hashlib
import math
import os
from pathlib import Path
import random
import re
import signal
import subprocess
import sys
import threading
import time
from typing import Any, Dict, Optional
import uuid

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
        self.process_lock = threading.Lock()
        self.process_termination_lock = threading.Lock()
        self.active_process: Optional[subprocess.Popen] = None
        self.active_process_state_path: Optional[Path] = None
        self.runner_lock_fd: Optional[int] = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        if not self._acquire_runner_lock():
            raise RuntimeError(
                "Another process owns the experiment-runner lock; refusing to "
                "start without a single authoritative worker"
            )
        self.stop_event.clear()
        try:
            recovery_needed = bool(list(self.store.running_experiments())) or (
                self._has_unreconciled_process_marker()
            )
            if recovery_needed:
                # Persist the inspection gate before touching a process marker
                # or terminal row. A crash at any later recovery instruction
                # therefore cannot clear the gate on the next restart.
                self.store.latch_runner_safety(
                    "Robot Lab found unfinished experiment state after restart; "
                    "inspect the robot before resuming the built-in worker",
                    created_by="experiment-runner",
                )
            recovered_processes = self._recover_orphaned_command_wrappers()
            self._recover_pending_terminal_results()
            recovered_runs = self._recover_orphaned_running_experiments()
            if recovered_processes or recovered_runs:
                self.store.latch_runner_safety(
                    "Robot Lab recovered unfinished experiment processes; "
                    "inspect the robot before resuming the built-in worker",
                    created_by="experiment-runner",
                )
            if self.store.runner_safety_control()["latched"]:
                print(
                    "Experiment runner safety latch is set; automatic claiming "
                    "remains disabled pending live or hands-on inspection",
                    flush=True,
                )
                return
            self.thread = threading.Thread(
                target=self._loop, name="experiment-worker", daemon=True
            )
            self.thread.start()
        except Exception:
            self._release_runner_lock()
            raise

    def _has_unreconciled_process_marker(self) -> bool:
        root = self.settings.data_dir / "experiments"
        if not root.is_dir():
            return False
        state_paths = list(root.glob("*/.robot-process.json"))
        state_paths.extend(root.glob("*/.camera-process.json"))
        for state_path in state_paths:
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return True
            if not state.get("recovered_at"):
                return True
        return False

    def stop(self):
        self.stop_event.set()
        self.wake_event.set()
        cleanup_failed = False
        with self.process_lock:
            process = self.active_process
            process_state_path = self.active_process_state_path
        if process is not None:
            cleanup_failed = not self._terminate_command(
                process, process_state_path
            )
            if cleanup_failed:
                self.store.latch_runner_safety(
                    "Robot command cleanup could not be proven during service stop; "
                    "inspect the robot before resuming",
                    created_by="experiment-runner",
                )
        if self.thread:
            self.thread.join(timeout=12)
            if self.thread.is_alive():
                # Retaining the inter-process lock is safer than allowing a
                # second worker to start while this one may still be active.
                raise RuntimeError(
                    "Experiment worker did not stop; runner lock retained"
                )
        if cleanup_failed:
            # Keep the lock until process exit. A restarted service will then
            # adopt the retained marker and retry process-group recovery.
            raise RuntimeError(
                "Robot command process group could not be proven stopped; "
                "runner lock retained"
            )
        self._release_runner_lock()

    def wake(self):
        self.wake_event.set()

    def _loop(self):
        while not self.stop_event.is_set():
            if self.store.runner_safety_control()["latched"]:
                print(
                    "Experiment runner safety latch set while worker was active; "
                    "stopping automatic claims",
                    flush=True,
                )
                return
            self._recover_pending_terminal_results()
            experiment = self.store.claim_next(
                require_codex_clear=self.settings.driver == "command"
            )
            if experiment:
                try:
                    self._execute(experiment)
                except Exception as exc:
                    # A broken summary, manifest, or database write must not
                    # permanently kill the queue's single consumer.  The
                    # incomplete-evidence reconciler will independently latch
                    # and alert if a terminal outbox cannot be sealed.
                    print(
                        f"Experiment worker error for {experiment['id']}: "
                        f"{type(exc).__name__}: {exc}",
                        flush=True,
                    )
            else:
                self.wake_event.wait(1)
                self.wake_event.clear()

    def _execute(self, experiment: Dict):
        run_dir = self.settings.data_dir / "experiments" / experiment["id"]
        run_dir.mkdir(parents=True, exist_ok=True)
        camera = None
        status = "failed"
        result: Dict[str, Any] = {"error": "Experiment did not start"}
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
            self._write_experiment_snapshot(run_dir, experiment)
            camera = self._start_camera(run_dir, experiment)
            if self.settings.driver == "simulated":
                result = self._simulate(experiment, run_dir)
            elif self.settings.driver == "command":
                result = self._run_command(experiment, run_dir, camera)
            else:
                raise RuntimeError("HEXAPOD_DRIVER must be simulated or command")
            current = self.store.get(experiment["id"])
            if current and current["cancel_requested"]:
                status = "cancelled"
            elif result.pop("_interrupted", False):
                status = "failed"
                result["error"] = "Experiment runner stopped before the run completed"
            else:
                status = "succeeded"
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            status = "failed"
            result = {"error": message}
        finally:
            if camera is not None:
                try:
                    camera_state = run_dir / ".camera-process.json"
                    camera_failed = camera.poll() is not None
                    if self._terminate_command(camera, camera_state):
                        camera_state.unlink(missing_ok=True)
                    else:
                        self.store.latch_runner_safety(
                            "Camera process cleanup could not be proven; inspect "
                            "the robot and camera before resuming",
                            created_by="experiment-runner",
                        )
                        raise RuntimeError(
                            "Camera process group could not be proven stopped"
                        )
                    if camera_failed and status == "succeeded":
                        status = "failed"
                        result = {
                            "error": "Camera capture stopped before experiment finalization"
                        }
                except Exception as exc:
                    if status == "succeeded":
                        status = "failed"
                        result = {
                            "error": f"Camera shutdown failed: {type(exc).__name__}: {exc}"
                        }
            try:
                self._write_summary(experiment, run_dir, status, result)
            except Exception as exc:
                try:
                    (run_dir / "summary.md").write_text(
                        f"# {experiment['name']}\n\n"
                        f"- Experiment ID: `{experiment['id']}`\n"
                        f"- Outcome: **{status}**\n\n"
                        "The detailed summary could not be generated: "
                        f"{type(exc).__name__}: {exc}\n",
                        encoding="utf-8",
                    )
                except Exception as fallback_exc:
                    status = "failed"
                    result = {
                        "error": (
                            "Could not persist the required experiment summary: "
                            f"{type(fallback_exc).__name__}: {fallback_exc}"
                        )
                    }
            # Required evidence files are durable before the terminal state
            # and its Codex outbox commit.  A later seal failure leaves an
            # explicit awaiting-evidence job for reconciliation, not a false
            # success with no report.
            terminal_error = result.get("error") if status == "failed" else None
            self._commit_terminal_result(
                experiment["id"], run_dir, status, terminal_error
            )
            # The start-time snapshot is useful crash evidence, but it must not
            # be the version that is sealed after a normal completion. Refresh
            # both human- and machine-readable evidence from the committed
            # terminal row so status and timestamps cannot disagree.
            terminal = self.store.get(experiment["id"])
            if terminal is None or terminal.get("status") != status:
                raise RuntimeError(
                    "Committed terminal experiment state could not be reloaded"
                )
            self._write_experiment_snapshot(run_dir, terminal)
            self._write_summary(terminal, run_dir, status, result)
            try:
                self._record_default_learning(experiment, status, result)
            except Exception as exc:
                print(
                    f"Default learning deferred for {experiment['id']}: "
                    f"{type(exc).__name__}: {exc}",
                    flush=True,
                )
            try:
                self.store.finalize_evidence(
                    experiment["id"], run_dir, self.write_manifest
                )
            except Exception as exc:
                print(
                    f"Evidence sealing deferred for {experiment['id']}: "
                    f"{type(exc).__name__}: {exc}",
                    flush=True,
                )

    def _write_experiment_snapshot(
        self, run_dir: Path, experiment: Dict[str, Any]
    ) -> None:
        recorded = dict(experiment)
        if self.layout_history is not None:
            recorded["tag_layout_revision"] = (
                self.layout_history.experiment_revision(experiment["id"])
            )
        destination = run_dir / "experiment.json"
        temporary = destination.with_name(
            f".{destination.name}.{uuid.uuid4().hex}.tmp"
        )
        try:
            temporary.write_text(
                json.dumps(recorded, indent=2) + "\n", encoding="utf-8"
            )
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

    def _commit_terminal_result(
        self,
        experiment_id: str,
        run_dir: Path,
        status: str,
        error: Optional[str],
    ) -> None:
        pending = run_dir / ".terminal-result.pending.json"
        temporary = pending.with_name(f".{pending.name}.{uuid.uuid4().hex}.tmp")
        payload = {
            "schema_version": 1,
            "experiment_id": experiment_id,
            "status": status,
            "error": error,
        }
        try:
            temporary.write_text(
                json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8"
            )
            os.replace(temporary, pending)
        finally:
            temporary.unlink(missing_ok=True)
        last_error: Optional[Exception] = None
        for attempt in range(5):
            try:
                self.store.finish(experiment_id, status, error)
                pending.unlink(missing_ok=True)
                return
            except Exception as exc:
                last_error = exc
                if attempt < 4:
                    time.sleep(0.1 * (2 ** attempt))
        raise RuntimeError(
            "Could not commit the terminal experiment result; recovery marker retained"
        ) from last_error

    def _recover_pending_terminal_results(self) -> int:
        experiments_dir = self.settings.data_dir / "experiments"
        if not experiments_dir.is_dir():
            return 0
        recovered = 0
        for pending in experiments_dir.glob("*/.terminal-result.pending.json"):
            try:
                payload = json.loads(pending.read_text(encoding="utf-8"))
                experiment_id = payload["experiment_id"]
                status = payload["status"]
                error = payload.get("error")
                if pending.parent.name != experiment_id or status not in {
                    "succeeded", "failed", "cancelled"
                }:
                    raise ValueError("invalid terminal recovery marker")
                current = self.store.get(experiment_id)
                if current is None:
                    raise ValueError("terminal recovery experiment is missing")
                if current["status"] not in {"running", status}:
                    raise ValueError("terminal recovery marker conflicts with experiment")
                self.store.finish(experiment_id, status, error)
                pending.unlink(missing_ok=True)
                recovered += 1
            except Exception as exc:
                print(
                    "Could not recover a pending terminal experiment result: "
                    f"{type(exc).__name__}: {exc}",
                    flush=True,
                )
        return recovered

    def _start_camera(self, run_dir: Path, experiment: Dict[str, Any]):
        if not self.settings.camera_input:
            return None
        if self.settings.driver == "command" and not self._acquire_runner_lock():
            raise RuntimeError("Another process owns the physical experiment runner")
        log = (run_dir / "camera.log").open("wb")
        progress_path = run_dir / ".camera-progress"
        progress_path.unlink(missing_ok=True)
        marker = uuid.uuid4().hex
        timeout = (
            float(experiment["duration_seconds"])
            + max(0.1, float(self.settings.robot_command_shutdown_seconds))
        )
        command = [
            sys.executable,
            "-m",
            "hexapod_lab.deadline_exec",
            "--marker",
            marker,
            "--state-path",
            str(run_dir / ".camera-process.json"),
            "--timeout-seconds",
            str(timeout),
            "--",
            "ffmpeg", "-nostdin", "-y", "-i", self.settings.camera_input,
            "-stats_period", "0.25", "-progress", str(progress_path),
            "-c:v", "libx264", "-preset", "veryfast", "-movflags", "+faststart",
            str(run_dir / "video.mp4"),
        ]
        state_path = run_dir / ".camera-process.json"
        self._write_launch_intent(
            state_path,
            marker=marker,
            kind="camera",
            experiment_id=experiment["id"],
            deadline_seconds=timeout,
        )
        try:
            process = subprocess.Popen(
                command,
                stdout=log,
                stderr=subprocess.STDOUT,
                env=self._command_environment(),
                start_new_session=True,
                pass_fds=(self.runner_lock_fd,) if self.runner_lock_fd else (),
            )
            log.close()
            self._wait_for_camera_ready(process, run_dir, experiment)
            return process
        except Exception as error:
            log.close()
            group_stopped = True
            if "process" in locals():
                group_stopped = self._terminate_command(process, state_path)
            if group_stopped:
                state_path.unlink(missing_ok=True)
                raise
            self.store.latch_runner_safety(
                "Camera startup cleanup could not be proven; inspect the robot "
                "and camera before resuming",
                created_by="experiment-runner",
            )
            raise RuntimeError(
                "Camera startup failed and its process group could not be proven stopped"
            ) from error

    def _wait_for_camera_ready(
        self,
        process: subprocess.Popen,
        run_dir: Path,
        experiment: Dict[str, Any],
    ) -> None:
        deadline = time.monotonic() + max(
            0.1, float(self.settings.camera_ready_timeout_seconds)
        )
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(
                    f"Camera capture failed during startup with status {process.returncode}"
                )
            current = self.store.get(experiment["id"])
            if self.stop_event.is_set() or (current and current["cancel_requested"]):
                raise RuntimeError("Camera startup was cancelled")
            if self._camera_progress_is_fresh(run_dir):
                return
            time.sleep(0.05)
        raise RuntimeError("Camera did not produce a fresh frame before the readiness deadline")

    def _camera_progress_is_fresh(self, run_dir: Path) -> bool:
        progress_path = run_dir / ".camera-progress"
        try:
            age = time.time() - progress_path.stat().st_mtime
            if age > max(0.1, float(self.settings.camera_stale_seconds)):
                return False
            progress = progress_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False
        frames = re.findall(r"(?m)^frame=(\d+)\s*$", progress)
        return bool(frames and int(frames[-1]) > 0)

    def _simulate(self, experiment: Dict, run_dir: Path):
        started = time.monotonic()
        samples = 0
        telemetry_path = run_dir / "telemetry.jsonl"
        duration = float(experiment["duration_seconds"])
        interrupted = False
        with telemetry_path.open("w") as telemetry:
            while time.monotonic() - started < duration:
                current = self.store.get(experiment["id"])
                if self.stop_event.is_set():
                    interrupted = True
                    break
                if current and current["cancel_requested"]:
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
        return {
            "telemetry_samples": samples,
            "driver": "simulated",
            "_interrupted": interrupted,
        }

    def _run_command(
        self,
        experiment: Dict,
        run_dir: Path,
        camera: Optional[subprocess.Popen] = None,
    ):
        parameters = experiment.get("parameters")
        if isinstance(parameters, dict) and parameters.get("simulation_only") is True:
            raise RuntimeError(
                "Simulation-only experiment refused by the physical command driver"
            )
        if not self.settings.robot_command:
            raise RuntimeError("HEXAPOD_ROBOT_COMMAND is required for command driver")
        if camera is None or not self._camera_progress_is_fresh(run_dir):
            raise RuntimeError(
                "Physical command driver requires a verified fresh camera frame"
            )
        if not self._acquire_runner_lock():
            raise RuntimeError("Another process owns the physical experiment runner")
        env = {"HEXAPOD_EXPERIMENT_ID": experiment["id"], "HEXAPOD_RUN_DIR": str(run_dir)}
        telemetry_path = run_dir / "telemetry.jsonl"
        stderr_path = run_dir / "robot.stderr.log"
        process_state_path = run_dir / ".robot-process.json"
        process_marker = uuid.uuid4().hex
        command_deadline = (
            float(experiment["duration_seconds"])
            + max(0.1, float(self.settings.robot_command_shutdown_seconds))
        )
        wrapped_command = [
            sys.executable,
            "-m",
            "hexapod_lab.deadline_exec",
            "--marker",
            process_marker,
            "--state-path",
            str(process_state_path),
            "--timeout-seconds",
            str(command_deadline),
            "--",
            *self.settings.robot_command,
        ]
        self._write_launch_intent(
            process_state_path,
            marker=process_marker,
            kind="robot-command",
            experiment_id=experiment["id"],
            deadline_seconds=command_deadline,
        )
        interrupted = False
        current = None
        with telemetry_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr_handle:
            with self.process_lock:
                # This is the final parent-side launch fence. stop() sets the
                # flag before acquiring the same lock, so it either prevents
                # Popen entirely or observes and terminates the published
                # wrapper before returning.
                current = self.store.get(experiment["id"])
                if self.stop_event.is_set() or (
                    current and current["cancel_requested"]
                ):
                    process_state_path.unlink(missing_ok=True)
                    return {
                        "telemetry_samples": 0,
                        "driver": "command",
                        "_interrupted": self.stop_event.is_set(),
                    }
                try:
                    process = subprocess.Popen(
                        wrapped_command,
                        stdin=subprocess.PIPE,
                        stdout=stdout_handle,
                        stderr=stderr_handle,
                        text=True,
                        env={**self._command_environment(), **env},
                        start_new_session=True,
                        pass_fds=(self.runner_lock_fd,) if self.runner_lock_fd else (),
                    )
                except Exception:
                    process_state_path.unlink(missing_ok=True)
                    raise
                self.active_process = process
                self.active_process_state_path = process_state_path
            try:
                deadline = time.monotonic() + command_deadline + 5
                payload: Optional[str] = json.dumps(experiment)
                while True:
                    try:
                        process.communicate(payload, timeout=.25)
                        break
                    except subprocess.TimeoutExpired:
                        payload = None
                        current = self.store.get(experiment["id"])
                        if self.stop_event.is_set() or (current and current["cancel_requested"]):
                            interrupted = self.stop_event.is_set()
                            self._terminate_command(process, process_state_path)
                            break
                        if (
                            camera.poll() is not None
                            or not self._camera_progress_is_fresh(run_dir)
                        ):
                            self._terminate_command(process, process_state_path)
                            raise RuntimeError(
                                "Camera capture stopped or stopped producing fresh frames"
                            )
                        try:
                            output_bytes = (
                                telemetry_path.stat().st_size + stderr_path.stat().st_size
                            )
                        except OSError:
                            output_bytes = 0
                        if output_bytes > self.settings.max_experiment_artifact_bytes:
                            self._terminate_command(process, process_state_path)
                            raise RuntimeError(
                                "robot command output exceeded the experiment artifact quota"
                            )
                        if time.monotonic() >= deadline:
                            self._terminate_command(process, process_state_path)
                            raise RuntimeError("robot command exceeded duration plus shutdown allowance")
            finally:
                group_stopped = self._terminate_command(process, process_state_path)
                with self.process_lock:
                    if self.active_process is process:
                        self.active_process = None
                        self.active_process_state_path = None
                if group_stopped:
                    process_state_path.unlink(missing_ok=True)
                else:
                    self.store.latch_runner_safety(
                        "Robot command process cleanup could not be proven; inspect "
                        "the robot before resuming",
                        created_by="experiment-runner",
                    )
                    raise RuntimeError(
                        "Robot command process group could not be proven stopped"
                    )
        if process.returncode == 124:
            raise RuntimeError("robot command exceeded its independent deadline")
        if process.returncode and not (
            interrupted or (current and current["cancel_requested"])
        ):
            raise RuntimeError(f"robot command exited {process.returncode}")
        return {
            "telemetry_samples": self._telemetry_stats(telemetry_path)["samples"],
            "driver": "command",
            "_interrupted": interrupted,
        }

    def _recover_orphaned_command_wrappers(self) -> int:
        """Stop wrappers left by a crashed Lab service before claiming work."""
        root = self.settings.data_dir / "experiments"
        if not root.is_dir():
            return 0
        recovered = 0
        state_paths = list(root.glob("*/.robot-process.json"))
        state_paths.extend(root.glob("*/.camera-process.json"))
        for state_path in sorted(state_paths):
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if state.get("recovered_at"):
                continue
            pid = state.get("pid")
            marker = state.get("marker")
            if not isinstance(marker, str) or re.fullmatch(
                r"[0-9a-f]{32}", marker
            ) is None:
                continue
            if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 1:
                pid = self._find_deadline_wrapper(marker)
            live_match = False
            if pid is not None:
                try:
                    inspected = subprocess.run(
                        ["/bin/ps", "-p", str(pid), "-o", "command="],
                        capture_output=True,
                        text=True,
                        timeout=5,
                        check=False,
                    )
                    command_line = (
                        inspected.stdout if inspected.returncode == 0 else ""
                    )
                    live_match = (
                        "hexapod_lab.deadline_exec" in command_line
                        and marker in command_line
                    )
                except (OSError, subprocess.TimeoutExpired):
                    live_match = False
            started_unix = state.get("started_unix")
            deadline_seconds = state.get("deadline_seconds")
            recent_adopted_group = bool(
                isinstance(pid, int)
                and pid > 1
                and isinstance(started_unix, (int, float))
                and not isinstance(started_unix, bool)
                and isinstance(deadline_seconds, (int, float))
                and not isinstance(deadline_seconds, bool)
                and time.time() <= started_unix + deadline_seconds + 300
                and self._process_group_exists(pid)
            )
            if live_match or recent_adopted_group:
                try:
                    os.killpg(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                deadline = time.monotonic() + 5
                while self._process_group_exists(pid) and time.monotonic() < deadline:
                    time.sleep(0.05)
                if self._process_group_exists(pid):
                    try:
                        os.killpg(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                deadline = time.monotonic() + 2
                while self._process_group_exists(pid) and time.monotonic() < deadline:
                    time.sleep(0.05)
            group_stopped = pid is None or not self._process_group_exists(pid)
            if not group_stopped:
                # Retain the unfinished marker and the already-persisted
                # inspection latch. A later recovery attempt must not assume
                # this process group is harmless.
                continue
            state["recovered_at"] = datetime.now(timezone.utc).isoformat()
            state["recovered_process_match"] = bool(
                live_match or recent_adopted_group
            )
            temporary = state_path.with_name(
                f".{state_path.name}.{uuid.uuid4().hex}.tmp"
            )
            try:
                temporary.write_text(
                    json.dumps(state, sort_keys=True) + "\n", encoding="utf-8"
                )
                temporary.chmod(0o600)
                os.replace(temporary, state_path)
            finally:
                temporary.unlink(missing_ok=True)
            recovered += 1
        return recovered

    @staticmethod
    def _find_deadline_wrapper(marker: str) -> Optional[int]:
        try:
            inspected = subprocess.run(
                ["/bin/ps", "-axo", "pid=,command="],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        for line in inspected.stdout.splitlines():
            if "hexapod_lab.deadline_exec" not in line or marker not in line:
                continue
            fields = line.strip().split(maxsplit=1)
            if not fields:
                continue
            try:
                candidate = int(fields[0])
            except ValueError:
                continue
            if candidate > 1:
                return candidate
        return None

    def _recover_orphaned_running_experiments(self) -> int:
        """Fence pre-restart runs as failed and enqueue their evidence analysis."""
        recovered = 0
        for experiment in self.store.running_experiments():
            run_dir = self.settings.data_dir / "experiments" / experiment["id"]
            run_dir.mkdir(parents=True, exist_ok=True)
            experiment_path = run_dir / "experiment.json"
            if not experiment_path.is_file():
                experiment_path.write_text(
                    json.dumps(experiment, indent=2) + "\n", encoding="utf-8"
                )
            reason = (
                "Robot Lab restarted while this experiment was running; its "
                "independent process watchdog was stopped and live or hands-on inspection "
                "is required before later work"
            )
            result = {"error": reason, "recovered_after_service_restart": True}
            try:
                self._write_summary(experiment, run_dir, "failed", result)
                self._commit_terminal_result(
                    experiment["id"], run_dir, "failed", reason
                )
                self._record_default_learning(experiment, "failed", result)
                self.store.finalize_evidence(
                    experiment["id"], run_dir, self.write_manifest
                )
            except Exception as exc:
                print(
                    f"Could not fully reconcile orphaned experiment "
                    f"{experiment['id']}: {type(exc).__name__}: {exc}",
                    flush=True,
                )
            recovered += 1
        return recovered

    def _terminate_command(
        self, process: subprocess.Popen, state_path: Optional[Path] = None
    ) -> bool:
        with self.process_termination_lock:
            if self._process_group_exists(process.pid):
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            if self._process_group_exists(process.pid):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                return False
            deadline = time.monotonic() + 2
            while self._process_group_exists(process.pid) and time.monotonic() < deadline:
                time.sleep(0.05)
            stopped = not self._process_group_exists(process.pid)
            if stopped and state_path is not None:
                # Callers remove the marker only after this proof; keeping it
                # on any uncertainty lets startup recovery retry the sweep.
                return True
            return stopped

    @staticmethod
    def _process_group_exists(pgid: int) -> bool:
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    @staticmethod
    def _write_launch_intent(
        path: Path,
        *,
        marker: str,
        kind: str,
        experiment_id: str,
        deadline_seconds: float,
    ) -> None:
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        payload = {
            "schema_version": 1,
            "marker": marker,
            "kind": kind,
            "experiment_id": experiment_id,
            "intent_created_unix": time.time(),
            "deadline_seconds": deadline_seconds,
        }
        try:
            temporary.write_text(
                json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8"
            )
            temporary.chmod(0o600)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def _acquire_runner_lock(self) -> bool:
        if self.runner_lock_fd is not None:
            return True
        path = self.settings.data_dir / ".experiment-runner.lock"
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(descriptor)
            return False
        self.runner_lock_fd = descriptor
        return True

    def _release_runner_lock(self) -> None:
        descriptor = self.runner_lock_fd
        if descriptor is None:
            return
        self.runner_lock_fd = None
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)

    @staticmethod
    def _command_environment() -> Dict[str, str]:
        allowed = {
            "HOME", "USER", "LOGNAME", "PATH", "SHELL", "TMPDIR",
            "LANG", "LC_ALL", "LC_CTYPE", "SSL_CERT_FILE", "SSL_CERT_DIR",
            "VIRTUAL_ENV", "UV_CACHE_DIR", "PYTHONPATH",
            "HEXAPOD_HOST", "HEXAPOD_ROBOT_URL", "HEXAPOD_VISION_FRAME_URL",
        }
        return {name: os.environ[name] for name in allowed if os.environ.get(name)}

    def _write_summary(self, experiment: Dict, run_dir: Path, status: str, result: Dict):
        artifacts = sorted(path.name for path in run_dir.iterdir() if path.is_file())
        stats = self._telemetry_stats(run_dir / "telemetry.jsonl")
        current = self.store.get(experiment["id"]) or experiment
        lines = [f"# {experiment['name']}", "", f"- Experiment ID: `{experiment['id']}`",
                 f"- Outcome: **{status}**", f"- Requested duration: {experiment['duration_seconds']} seconds",
                 f"- Driver: {result.get('driver', self.settings.driver)}",
                 f"- Started: {current.get('started_at') or 'not recorded'}",
                 f"- Finished: {current.get('finished_at') or 'not recorded'}",
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

    def _record_default_learning(
        self, experiment: Dict, status: str, result: Dict
    ) -> None:
        if self.store.learnings(experiment["id"]) is None:
            simulated = result.get("driver", self.settings.driver) == "simulated"
            if simulated and status == "succeeded":
                learning = (
                    "The experiment-recording software completed this test using simulated readings. "
                    "It saved a report and sensor data. This checks the recording workflow; "
                    "it does not tell us how the physical robot would behave."
                )
            elif simulated:
                learning = (
                    "This simulated test did not finish normally. The report below records where it stopped. "
                    "It did not test the physical robot, and the partial results still need review."
                )
            elif status == "succeeded":
                learning = (
                    "The robot runner finished without reporting an error. The recorded measurements "
                    "still need review to determine whether the experiment achieved its aim."
                )
            else:
                learning = (
                    "This test did not finish normally. Its report and any partial measurements "
                    "still need review before we can say what we learned."
                )
            self.store.record_learnings(experiment["id"], learning, ["summary.md"], "robot-lab")

    @staticmethod
    def _telemetry_stats(path: Path):
        accumulators: Dict[str, Dict[str, float]] = {}
        samples = 0
        if not path.exists():
            return {"samples": 0, "fields": {}}
        with path.open(errors="replace") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                samples += 1
                for key, value in row.items():
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        number = float(value)
                        stats = accumulators.setdefault(key, {
                            "count": 0.0,
                            "sum": 0.0,
                            "min": number,
                            "max": number,
                        })
                        stats["count"] += 1
                        stats["sum"] += number
                        stats["min"] = min(stats["min"], number)
                        stats["max"] = max(stats["max"], number)
        fields = {
            key: {
                "min": values["min"],
                "max": values["max"],
                "mean": values["sum"] / values["count"],
            }
            for key, values in accumulators.items()
        }
        return {"samples": samples, "fields": fields}

    def write_manifest(self, run_dir: Path):
        return self._write_manifest(
            run_dir,
            max_artifacts=self.settings.max_experiment_artifacts,
            max_total_bytes=self.settings.max_experiment_artifact_bytes,
        )

    @staticmethod
    def _write_manifest(
        run_dir: Path,
        *,
        max_artifacts: Optional[int] = None,
        max_total_bytes: Optional[int] = None,
    ):
        entries = []
        total_bytes = 0
        for path in sorted(run_dir.iterdir()):
            if (
                path.is_file()
                and path.name != "manifest.json"
                and not path.name.startswith(".")
            ):
                if path.is_symlink():
                    raise RuntimeError(
                        f"Evidence artifacts may not be symbolic links: {path.name}"
                    )
                if max_artifacts is not None and len(entries) >= max_artifacts:
                    raise RuntimeError("Experiment artifact count exceeds configured limit")
                before = path.stat()
                total_bytes += before.st_size
                if max_total_bytes is not None and total_bytes > max_total_bytes:
                    raise RuntimeError("Experiment artifacts exceed configured aggregate size limit")
                digest = hashlib.sha256()
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                after = path.stat()
                if (
                    before.st_dev,
                    before.st_ino,
                    before.st_size,
                    before.st_mtime_ns,
                ) != (
                    after.st_dev,
                    after.st_ino,
                    after.st_size,
                    after.st_mtime_ns,
                ):
                    raise RuntimeError(
                        f"Evidence artifact changed while hashing: {path.name}"
                    )
                entries.append({
                    "name": path.name,
                    "bytes": before.st_size,
                    "sha256": digest.hexdigest(),
                })
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
        manifest_path = run_dir / "manifest.json"
        manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
        temporary = manifest_path.with_name(
            f".{manifest_path.name}.{uuid.uuid4().hex}.tmp"
        )
        try:
            with temporary.open("xb") as handle:
                handle.write(manifest_bytes)
            os.replace(temporary, manifest_path)
        finally:
            temporary.unlink(missing_ok=True)
        return hashlib.sha256(manifest_bytes).hexdigest()
