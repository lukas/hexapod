"""Opt-in hold-to-run ownership of the existing synchronous stand/lower jobs."""
from contextlib import contextmanager
import math
import threading
import time
import uuid

from drive_controller import GAMEPAD_LEASE_TIMEOUT_S
from hexapod_core.joint_frame import N_JOINTS


class PoseCancelled(RuntimeError):
    pass


class DeadlineAbort(threading.Event):
    """Expiration is sticky, including while a worker is blocked in a read."""

    def __init__(self, clock=time.monotonic):
        super().__init__()
        self.clock = clock
        self.deadline = clock() + GAMEPAD_LEASE_TIMEOUT_S

    def is_set(self):
        if self.clock() >= self.deadline:
            self.set()
        return super().is_set()

    def renew(self):
        if self.is_set():
            return False
        self.deadline = self.clock() + GAMEPAD_LEASE_TIMEOUT_S
        return True

    def wait(self, timeout=None):
        end = None if timeout is None else self.clock() + timeout
        while not self.is_set():
            now = self.clock()
            if end is not None and now >= end:
                return False
            remaining = max(0.0, self.deadline - now)
            super().wait(remaining if end is None else min(end - now, remaining))
            # A renewal may move the lease deadline during the wait. Keep
            # the caller's full replant dwell instead of returning early.
        return True


class GamepadPose:
    """Drive-lock admission; lock-independent cancellation and heartbeats."""

    def __init__(self, bench, *, clock=time.monotonic):
        self.bench, self.drive, self.clock = bench, bench.drive, clock
        self.job = None

    def busy_locked(self):
        self.tick_locked()
        return bool(self.job and (self.job["live"] or
                    (self.job["thread"] and self.job["thread"].is_alive())))

    def tick_locked(self):
        job = self.job
        if (job and not self.drive.armed and job["thread"] is not None
                and not job["thread"].is_alive()):
            job["live"] = False
        if job and job["live"] and job["abort"].is_set():
            job["state"] = "stopping"
            if job["thread"] is None:
                job["live"] = False
                job["state"] = "error"
                job["result"] = {"ok": False, "error": "pose reservation expired or stopped"}

    def cancel_locked(self):
        if self.job and self.job["live"]:
            self.job["abort"].set()
            self.tick_locked()

    def _reply(self, job):
        return {"ok": True, "token": job["token"], "state": job["state"],
                "timeout_s": GAMEPAD_LEASE_TIMEOUT_S, "result": job.get("result")}

    def request(self, data):
        if not isinstance(data, dict):
            return {"ok": False, "error": "Expected a JSON object"}
        action = data.get("action")
        d, b = self.drive, self.bench
        # Canonical motion sometimes holds the drive lock while reading
        # feedback. A heartbeat or stop must never wait for that read.
        # These paths only renew/set a sticky Event; they cannot launch.
        job = self.job
        if action in ("stop", "renew") and job and data.get("token") == job["token"]:
            if action == "stop":
                job["abort"].set()
                reply = self._reply(job)
                if job["live"]:
                    reply["state"] = "stopping"
                return reply
            if job["thread"] is not None:
                if job["state"] in ("done", "error", "stopping"):
                    return self._reply(job)
                if not job["abort"].renew() or b._demo_gen != job["gen"]:
                    job["abort"].set()
                    return {**self._reply(job), "state": "stopping"}
                return self._reply(job)
        with d._lock:
            self.tick_locked()
            if action == "prepare":
                pose = data.get("pose")
                if pose not in ("stand", "sit"):
                    return {"ok": False, "error": "pose must be stand or sit"}
                if (self.busy_locked() or d._gamepad_token is not None
                        or d._gamepad_settle_until is not None
                        or (b._demo_thread and b._demo_thread.is_alive())
                        or b._drive_active() or b._running_calibration_name()
                        or d.mode not in ("idle", "stand")):
                    return {"ok": False, "error": "Robot is busy or stopping; release controls and retry"}
                if d.dry_run or d.bus is None:
                    return {"ok": False, "error": "No motor bus connected"}
                if not callable(getattr(d.bus, "read_snapshot", None)):
                    return {"ok": False, "error": "Gamepad poses require the MCU bulk snapshot bus"}
                if not callable(getattr(d.bus, "enable_all_torque", None)):
                    return {"ok": False, "error": "Gamepad poses require bounded bulk torque control"}
                if pose == "sit" and not d.armed:
                    return {"ok": False, "error": "Sit requires an already armed robot"}
                self.job = dict(token=uuid.uuid4().hex, pose=pose,
                                abort=DeadlineAbort(self.clock), thread=None,
                                state="prepared", live=True, gen=b._demo_gen)
                return self._reply(self.job)
            job = self.job
            if not job or data.get("token") != job["token"]:
                return {"ok": False, "error": "Unknown pose token; release controls and prepare again"}
            if action == "stop":
                self.cancel_locked()
                return self._reply(job)
            if action != "renew":
                return {"ok": False, "error": "action must be prepare, renew, or stop"}
            if job["state"] in ("done", "error", "stopping"):
                return self._reply(job)
            if b._demo_gen != job["gen"] or not job["abort"].renew():
                self.cancel_locked()
                return self._reply(job)
            if job["thread"] is None:
                b._demo_gen += 1
                job["gen"] = b._demo_gen
                job["previous_abort"] = b._demo_abort
                b._demo_abort = job["abort"]
                b._demo_name = "gamepad:" + job["pose"]
                b._demo_status = "running"
                b._activity = "demo"
                job["state"] = "running"
                job["thread"] = threading.Thread(target=self._run, args=(job,), daemon=True)
                b._demo_thread = job["thread"]
                job["thread"].start()
            return self._reply(job)

    @contextmanager
    def _write_guard(self, job):
        # Only the few write packets hold the lock, never telemetry or waits.
        with self.drive._lock:
            if (job["abort"].is_set() or job["gen"] != self.bench._demo_gen
                    or not self.drive.armed):
                raise PoseCancelled("pose stopped or lease expired")
            yield

    def _finish_hold(self, job):
        d, b = self.drive, self.bench
        with d._lock:
            if job["gen"] != b._demo_gen or not d.armed:
                return
        # Complete measured positions only. Missing feedback must never turn
        # into the historical helper's synthetic zero-degree target.
        # MCU read_snapshot is one fresh transaction with a 0.5 s reply
        # timeout. Do not expand missing feedback into per-joint retries.
        failed_samples = 0
        seen_sequences = set()
        for _ in range(3):
            with d._lock:
                if job["gen"] != b._demo_gen or not d.armed:
                    return
            try:
                snapshot = d.bus.read_snapshot() or {}
                positions = snapshot.get("pos_deg") or {}
                pose = [positions.get(j) for j in range(N_JOINTS)]
                complete = (float(snapshot.get("pos_age_ms", math.inf)) <= 500
                            and all(v is not None and math.isfinite(v) for v in pose))
            except Exception:
                snapshot = {}
                complete = False
            if complete:
                with d._lock:
                    if job["gen"] != b._demo_gen or not d.armed:
                        return
                    d._write_pose(pose, speed=250, acc=30)
                    d.mode = "idle"
                    d.status = "gamepad pose stopped; measured hold"
                return
            # A fresh transaction may still contain the MCU's same cached
            # servo sweep. Never count that as another missing-ID vote.
            sequence = snapshot.get("seq")
            if not snapshot or (sequence is not None and sequence not in seen_sequences):
                failed_samples += 1
            seen_sequences.add(sequence)
        with d._lock:
            if job["gen"] != b._demo_gen or not d.armed:
                return
            # Three failed fresh samples OR feedback that never becomes
            # verifiable within the bounded reads: canonical limp path.
            d._handle_locked("X")
        reason = ("Three incomplete fresh snapshots" if failed_samples == 3 else
                  "Snapshot feedback did not become fresh and complete")
        raise RuntimeError(reason + "; stop unverified, limp requested")

    def _run(self, job):
        from inplace_demos import scripted_motion_scope
        d, b = self.drive, self.bench
        result = {"ok": False, "error": "pose stopped"}
        b._bus_hot_begin()
        try:
            # Renew only starts this wrapper. A delayed worker must recheck
            # ownership before its very first torque-enable operation.
            with d._lock:
                if job["abort"].is_set() or job["gen"] != b._demo_gen:
                    raise PoseCancelled("pose stopped before launch")
                if not d.armed:
                    if job["pose"] != "stand":
                        raise PoseCancelled("Sit requires an already armed robot")
                    try:
                        # One MCU transaction (1 s timeout); do not enter
                        # the generic arm helper's 18-servo retry fallback.
                        d.bus.enable_all_torque(True)
                    except Exception:
                        # A lost ACK may still have enabled hardware. The
                        # logical armed flag cannot certify torque is off.
                        d._handle_locked("X")
                        raise
                    d.armed = True
                d.mode = "demo"
                d.gait.stop()
            with scripted_motion_scope(lambda: self._write_guard(job)):
                if job["pose"] == "stand":
                    result = b._acquire_start("stand", gen=job["gen"])
                else:
                    result = b.standup(mode="step", speed=10.0, direction="down", sync_gen=job["gen"])
                result = result or {"ok": False, "error": "pose stopped"}
        except Exception as error:
            result = {"ok": False, "error": str(error)}
        finally:
            try:
                self._finish_hold(job)
            except Exception as error:
                result = {"ok": False, "error": str(error), "hold_unverified": True}
            with d._lock:
                if job["abort"].is_set():
                    result = {**result, "ok": False, "aborted": True}
                job["result"] = result
                job["state"] = "done" if result.get("ok") else "error"
                job["live"] = bool(result.get("hold_unverified") and d.armed)
                if b._demo_abort is job["abort"]:
                    b._demo_abort = job["previous_abort"]
                b._demo_status = "done" if result.get("ok") else str(result.get("error") or "stopped")
                b._activity = "armed" if d.armed else "limp"
            b._bus_hot_end()
