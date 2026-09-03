"""Bounded robot telemetry recording with contact observation.

The recorder never runs an independent servo-bus poller. ``McuFeetechBus``
offers it data that a command/test already produced; ordinary sync writes can
periodically use the firmware's combined write+snapshot reply, which is still
one transaction. The timing-sensitive callback only does a bounded
``put_nowait``. JSON encoding, contact scoring, and disk I/O all happen on a
background thread. When that thread cannot keep up, samples are counted and
dropped instead of delaying motion.

This is an observer only.  Its planted estimate is archived for comparison
with real-robot evidence and is not connected to gait control.
"""
from __future__ import annotations

import json
import math
import os
import queue
import re
import statistics
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


HERE = Path(__file__).resolve().parent
DEFAULT_MODEL_PATH = HERE.parent / "rl_move" / "contact_predictor_model.json"
HIGH_RATE_KINDS = frozenset({"positions", "snapshot", "step", "sync_write"})


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _utc_iso(unix_ns: int | None = None) -> str:
    if unix_ns is None:
        instant = datetime.now(timezone.utc)
    else:
        instant = datetime.fromtimestamp(unix_ns / 1_000_000_000,
                                         tz=timezone.utc)
    return instant.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _clean_label(label: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(label).strip()).strip("-.")
    return (clean or "session")[:48]


class RollingContactObserver:
    """Score the simulation-trained model, then smooth over recent readings."""

    def __init__(self, model_path: Path = DEFAULT_MODEL_PATH, *,
                 history_samples: int = 5, confirm_samples: int = 3):
        self.model_path = Path(model_path)
        self.history_samples = max(3, int(history_samples))
        self.confirm_samples = max(1, int(confirm_samples))
        self._command: list[float | None] = [None] * 18
        self._previous: list[tuple[float, float] | None] = [None] * 6
        self._probability = [deque(maxlen=self.history_samples)
                             for _ in range(6)]
        self._planted = [False] * 6
        self._candidate: list[bool | None] = [None] * 6
        self._candidate_count = [0] * 6
        self.latest: dict | None = None
        self.error: str | None = None
        self._payload: dict | None = None
        try:
            payload = json.loads(self.model_path.read_text(encoding="utf-8"))
            model = payload["model"]
            names = tuple(str(x) for x in model["feature_names"])
            required = (
                "command_clearance_mm",
                "measured_clearance_mm",
                "abs_vertical_speed_mm_s",
                "vertical_speed_mm_s",
                "tracking_error_deg",
            )
            if names != required:
                raise ValueError(f"unexpected feature order: {names!r}")
            mean = tuple(float(x) for x in model["mean"])
            scale = tuple(float(x) for x in model["scale"])
            weights = tuple(float(x) for x in model["weights_intercept_first"])
            if len(mean) != 5 or len(scale) != 5 or len(weights) != 6:
                raise ValueError("model dimensions are not 5 features + intercept")
            self._payload = payload
            self._mean = mean
            self._scale = scale
            self._weights = weights
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"

    def info(self) -> dict:
        validation = (self._payload or {}).get("validation") or {}
        return {
            "ready": self.error is None,
            "path": str(self.model_path),
            "error": self.error,
            "history_samples": self.history_samples,
            "confirm_samples": self.confirm_samples,
            "purpose": (self._payload or {}).get("purpose"),
            "validation": validation,
        }

    @staticmethod
    def _foot_z_m(hip_deg: float, knee_deg: float) -> float:
        # Must match hexapod_core.tripod_gait.foot_rz_from_hip_knee and the
        # training feature extraction: 90 mm femur, 150 mm tibia.
        hip = math.radians(float(hip_deg))
        knee = math.radians(float(knee_deg))
        return -0.090 * math.sin(hip) - 0.150 * math.sin(knee)

    def _score(self, values: tuple[float, ...]) -> float:
        standardized = tuple(
            (x - mean) / scale
            for x, mean, scale in zip(values, self._mean, self._scale)
        )
        logit = self._weights[0] + sum(
            weight * value
            for weight, value in zip(self._weights[1:], standardized)
        )
        return 1.0 / (1.0 + math.exp(max(-40.0, min(40.0, -logit))))

    def _merge_command(self, command) -> None:
        if not isinstance(command, (list, tuple)) or len(command) != 18:
            return
        for joint, value in enumerate(command):
            if value is not None:
                self._command[joint] = float(value)

    def update(self, payload: dict, mono_s: float) -> dict | None:
        """Return six logged estimates when a fresh measured pose is present."""
        self._merge_command(payload.get("command_deg"))
        measured = payload.get("position_deg")
        if (self.error is not None
                or not isinstance(measured, (list, tuple))
                or len(measured) != 18):
            return None

        neutral_z_m = self._foot_z_m(20.0, 80.0)
        legs: list[dict] = []
        for leg in range(6):
            lo = 3 * leg
            cmd = self._command[lo:lo + 3]
            obs = measured[lo:lo + 3]
            if any(x is None for x in cmd) or any(x is None for x in obs):
                legs.append({
                    "leg": leg, "ready": False, "planted": False,
                    "reason": "missing command or encoder",
                })
                continue
            command = tuple(float(x) for x in cmd)
            actual = tuple(float(x) for x in obs)
            command_z_m = self._foot_z_m(command[1], command[2])
            measured_z_m = self._foot_z_m(actual[1], actual[2])

            vertical_speed_mm_s = 0.0
            previous = self._previous[leg]
            continuous = False
            if previous is not None:
                previous_t, previous_z_m = previous
                dt_s = float(mono_s) - previous_t
                if 0.002 <= dt_s <= 0.25:
                    vertical_speed_mm_s = (
                        1000.0 * (measured_z_m - previous_z_m) / dt_s)
                    continuous = True
                elif dt_s < 0.002:
                    # A full-feedback read followed immediately by a snapshot
                    # is one physical instant, not two votes.
                    legs.append({
                        "leg": leg,
                        "ready": len(self._probability[leg]) >= 3,
                        "planted": self._planted[leg],
                        "reason": "duplicate instant",
                    })
                    continue
                else:
                    self._probability[leg].clear()
                    self._candidate[leg] = None
                    self._candidate_count[leg] = 0
                    self._planted[leg] = False
            self._previous[leg] = (float(mono_s), measured_z_m)

            features = (
                1000.0 * (command_z_m - neutral_z_m),
                1000.0 * (measured_z_m - neutral_z_m),
                abs(vertical_speed_mm_s),
                vertical_speed_mm_s,
                max(abs(a - c) for a, c in zip(actual, command)),
            )
            probability = self._score(features)
            history = self._probability[leg]
            history.append(probability)
            filtered = float(statistics.median(history))
            ready = continuous and len(history) >= 3

            target: bool | None = None
            if ready and not self._planted[leg] and filtered >= 0.65:
                target = True
            elif ready and self._planted[leg] and filtered <= 0.35:
                target = False
            if target is None:
                self._candidate[leg] = None
                self._candidate_count[leg] = 0
            else:
                if self._candidate[leg] == target:
                    self._candidate_count[leg] += 1
                else:
                    self._candidate[leg] = target
                    self._candidate_count[leg] = 1
                if self._candidate_count[leg] >= self.confirm_samples:
                    self._planted[leg] = target
                    self._candidate[leg] = None
                    self._candidate_count[leg] = 0

            legs.append({
                "leg": leg,
                "ready": ready,
                "probability": round(probability, 5),
                "filtered_probability": round(filtered, 5),
                "planted": self._planted[leg],
                "history": len(history),
                "features": {
                    "command_clearance_mm": round(features[0], 4),
                    "measured_clearance_mm": round(features[1], 4),
                    "abs_vertical_speed_mm_s": round(features[2], 4),
                    "vertical_speed_mm_s": round(features[3], 4),
                    "tracking_error_deg": round(features[4], 4),
                },
            })

        result = {
            "observer_only": True,
            "gait_gating": False,
            "legs": legs,
            "planted": [bool(row.get("planted")) for row in legs],
            "ready_legs": sum(bool(row.get("ready")) for row in legs),
        }
        self.latest = result
        return result


class TelemetryRecorder:
    """One persistent JSONL session at a time, fed by a passive bus hook."""

    def __init__(self, log_directory: Path | None = None, *,
                 queue_max: int | None = None,
                 model_path: Path = DEFAULT_MODEL_PATH):
        self.log_directory = Path(log_directory or HERE / "logs")
        self.queue_max = max(128, int(queue_max or _env_int(
            "HEXAPOD_TELEMETRY_QUEUE", 4096)))
        self.model_path = Path(model_path)
        self._lock = threading.Lock()
        self._active = False
        self._bus = None
        self._queue: queue.Queue | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._path: Path | None = None
        self._started_unix_ns: int | None = None
        self._started_mono_ns: int | None = None
        self._max_hz = 0.0
        self._minimum_period_ns = 0
        self._rate_slack_ns = 0
        self._last_high_rate_ns = 0
        self._sequence = 0
        self._offered = 0
        self._written = 0
        self._rate_limited = 0
        self._queue_dropped = 0
        self._write_error: str | None = None
        self._latest_contact: dict | None = None
        self._observer: RollingContactObserver | None = None

    def _bus_setter(self, bus) -> Callable | None:
        setter = getattr(bus, "set_telemetry_sink", None)
        return setter if callable(setter) else None

    def start(self, bus, *, label: str = "session",
              max_hz: float | None = None) -> dict:
        with self._lock:
            if self._active:
                out = self.status()
                out.update({"ok": True, "already_active": True})
                return out
            if self._thread is not None and self._thread.is_alive():
                return {"ok": False,
                        "error": "previous telemetry session is still draining"}
            setter = self._bus_setter(bus)
            if setter is None:
                return {
                    "ok": False,
                    "error": "active bus does not provide passive telemetry hooks",
                }
            hz = float(max_hz if max_hz is not None else _env_float(
                "HEXAPOD_TELEMETRY_HZ", 50.0))
            hz = max(1.0, min(100.0, hz))
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
            self.log_directory.mkdir(parents=True, exist_ok=True)
            self._path = self.log_directory / (
                f"telemetry_{stamp}_{_clean_label(label)}.jsonl")
            self._queue = queue.Queue(maxsize=self.queue_max)
            self._stop = threading.Event()
            self._started_unix_ns = time.time_ns()
            self._started_mono_ns = time.monotonic_ns()
            self._max_hz = hz
            self._minimum_period_ns = int(1_000_000_000 / hz)
            self._rate_slack_ns = min(500_000, self._minimum_period_ns // 10)
            self._last_high_rate_ns = 0
            self._sequence = 0
            self._offered = 0
            self._written = 0
            self._rate_limited = 0
            self._queue_dropped = 0
            self._write_error = None
            self._latest_contact = None
            self._observer = RollingContactObserver(self.model_path)
            self._bus = bus
            self._active = True
            self._thread = threading.Thread(
                target=self._writer,
                name="telemetry-recorder",
                daemon=True,
            )
            self._thread.start()
            setter(self)
        self._emit_event("telemetry recorder started", data={
            "path": str(self._path), "max_hz": hz,
            "passive": True, "queue_max": self.queue_max,
        })
        out = self.status()
        out["ok"] = True
        return out

    def offer(self, kind: str, payload: dict) -> bool:
        """Timing-sensitive hook: bounded enqueue only; never waits."""
        if not self._active:
            return False
        mono_ns = time.monotonic_ns()
        kind = str(kind)
        if kind in HIGH_RATE_KINDS:
            previous = self._last_high_rate_ns
            if (previous and mono_ns + self._rate_slack_ns
                    < previous + self._minimum_period_ns):
                self._rate_limited += 1
                return False
            self._last_high_rate_ns = mono_ns
        q = self._queue
        if q is None:
            return False
        self._sequence += 1
        item = (self._sequence, time.time_ns(), mono_ns, kind, payload)
        try:
            q.put_nowait(item)
            self._offered += 1
            return True
        except queue.Full:
            self._queue_dropped += 1
            return False

    def __call__(self, kind: str, payload: dict) -> bool:
        return self.offer(kind, payload)

    def wants_snapshot(self) -> bool:
        """Whether a sync write should use the existing combined S reply.

        This reserves no timestamp and does no I/O. The subsequent ``step``
        offer performs the authoritative rate-limit check.
        """
        if not self._active:
            return False
        previous = self._last_high_rate_ns
        return (not previous or
                time.monotonic_ns() + self._rate_slack_ns
                >= previous + self._minimum_period_ns)

    def mark(self, label: str, data: dict | None = None) -> dict:
        if not self._active:
            return {"ok": False, "error": "telemetry recorder is not active"}
        accepted = self.offer("marker", {
            "label": str(label)[:120], "data": data or {},
        })
        return {"ok": accepted, "label": str(label)[:120], **self.status()}

    def stop(self, *, timeout: float = 2.0) -> dict:
        with self._lock:
            was_active = self._active
            self._active = False
            bus = self._bus
            self._bus = None
            setter = self._bus_setter(bus)
            if setter is not None:
                setter(None)
            self._stop.set()
            thread = self._thread
        if thread is not None:
            thread.join(timeout=max(0.0, float(timeout)))
        out = self.status()
        out.update({"ok": True, "was_active": was_active})
        self._emit_event("telemetry recorder stopped", data={
            "path": out.get("path"), "written": out.get("written"),
            "queue_dropped": out.get("queue_dropped"),
            "rate_limited": out.get("rate_limited"),
            "writer_alive": out.get("writer_alive"),
        })
        return out

    def status(self) -> dict:
        q = self._queue
        path = self._path
        try:
            size = path.stat().st_size if path is not None and path.exists() else 0
        except OSError:
            size = 0
        return {
            "active": self._active,
            "passive": True,
            "adds_bus_reads": False,
            "piggyback_snapshots": True,
            "observer_only": True,
            "gait_gating": False,
            "path": str(path) if path is not None else None,
            "bytes": size,
            "max_hz": self._max_hz,
            "queue": q.qsize() if q is not None else 0,
            "queue_max": self.queue_max,
            "offered": self._offered,
            "written": self._written,
            "rate_limited": self._rate_limited,
            "queue_dropped": self._queue_dropped,
            "write_error": self._write_error,
            "writer_alive": bool(
                self._thread is not None and self._thread.is_alive()),
            "contact": self._latest_contact,
            "model": (self._observer.info() if self._observer is not None
                      else {"ready": self.model_path.is_file(),
                            "path": str(self.model_path)}),
        }

    def _writer(self) -> None:
        q = self._queue
        path = self._path
        observer = self._observer
        if q is None or path is None or observer is None:
            return
        try:
            with path.open("x", encoding="utf-8", buffering=256 * 1024) as stream:
                metadata = {
                    "schema_version": 1,
                    "record_type": "session",
                    "ts": _utc_iso(self._started_unix_ns),
                    "time_unix_ns": self._started_unix_ns,
                    "mono_ns": self._started_mono_ns,
                    "passive": True,
                    "adds_bus_reads": False,
                    "piggyback_snapshots": True,
                    "max_hz": self._max_hz,
                    "queue_max": self.queue_max,
                    "contact_observer": observer.info(),
                }
                stream.write(json.dumps(metadata, separators=(",", ":")) + "\n")
                last_flush = time.monotonic()
                while not self._stop.is_set() or not q.empty():
                    try:
                        seq, unix_ns, mono_ns, kind, payload = q.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    record = {
                        "schema_version": 1,
                        "record_type": str(kind),
                        "seq": int(seq),
                        "ts": _utc_iso(int(unix_ns)),
                        "time_unix_ns": int(unix_ns),
                        "mono_s": round(int(mono_ns) / 1_000_000_000, 9),
                        **payload,
                    }
                    contact = observer.update(payload, int(mono_ns) / 1_000_000_000)
                    if contact is not None:
                        record["contact"] = contact
                        self._latest_contact = contact
                    stream.write(json.dumps(
                        record, default=str, separators=(",", ":")) + "\n")
                    self._written += 1
                    q.task_done()
                    if time.monotonic() - last_flush >= 1.0:
                        # Users asked to retain the logs. A periodic userspace
                        # flush limits loss on service failure without fsyncing
                        # or touching the control thread.
                        stream.flush()
                        last_flush = time.monotonic()
                stream.write(json.dumps({
                    "schema_version": 1,
                    "record_type": "session_end",
                    "ts": _utc_iso(),
                    "written": self._written,
                    "rate_limited": self._rate_limited,
                    "queue_dropped": self._queue_dropped,
                }, separators=(",", ":")) + "\n")
                stream.flush()
        except Exception as exc:
            self._write_error = f"{type(exc).__name__}: {exc}"
            self._active = False
            setter = self._bus_setter(self._bus)
            if setter is not None:
                try:
                    setter(None)
                except Exception:
                    pass
            self._emit_event("telemetry writer failed", level="error", data={
                "path": str(path), "error": self._write_error,
                "queue": q.qsize(), "queue_dropped": self._queue_dropped,
            })

    @staticmethod
    def _emit_event(message: str, *, data: dict,
                    level: str = "info") -> None:
        try:
            from event_log import emit
            emit("telemetry", message, src="telemetry_recorder", data=data,
                 level=level)
        except Exception:
            pass
