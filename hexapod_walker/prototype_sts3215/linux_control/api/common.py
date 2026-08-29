"""JSON bench helpers for the web UI: status, wiggle, demos.

Uses the same Feetech bus as ``DriveController`` (shared lock).
"""
# NOTE (2026-08-29 split): this module is the former bench_api.py header —
# imports, route-wide constants, and the bus-quality trackers — shared by
# every route-group mixin in this package via ``from .common import *``.
# bench_api.py re-exports all of it, so the legacy module surface
# (bench_api.REGISTRY_CANDIDATES, bench_api._BusQualityTracker, ...) is
# unchanged.
from __future__ import annotations

import json
import math
import os
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

# rl_move lives one level above linux_control (repo and robot alike);
# web_drive only puts linux_control itself on sys.path, and the policy
# upload route needs rl_move.np_policy before any RL button has run
# rl_policy.py's own path shim.
_PARENT = str(Path(__file__).resolve().parents[2])
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from motor_setup.feetech_bus import N_JOINTS, joint_limits, joint_to_servo_id

if TYPE_CHECKING:
    from drive_controller import DriveController

AXIS = ("yaw", "hip", "knee")
REGISTRY_CANDIDATES = (
    Path(__file__).resolve().parents[2] / "motor_setup" / "motor_setup_registry.json",
    Path(__file__).resolve().parents[1] / "motor_setup_registry.json",
    Path.home() / "hexapod_sts" / "motor_setup" / "motor_setup_registry.json",
)

# Air demos must start near logical 0°. Planted/rise demos start from a stand.
AIR_DEMO_NAMES = frozenset({
    "breathe", "breathe_v", "heartbeat", "twinkle", "shimmy", "ripple",
    "conductor", "arms_up", "rock",
    "air_meet", "air_pendulum", "air_orbits", "air_trident",
    "air_weave", "air_gearbox", "air_tides", "dance_swarm",
    # stands mid-song but starts AND ends at sit zero (limp), like dance
    "dance_swarm_stand",
    # stands AND rears up mid-song; starts and ends at sit zero (limp)
    "dance_swarm_encore",
    # vertical variant: body-elevator choruses, same skeleton
    "dance_swarm_up",
    # stands mid-show but starts AND ends at sit zero (limp)
    "dance_steeple",
    # stands AND rears up mid-show; starts and ends at sit zero (limp)
    "dance_wild",
    # stands, no-slip turns AND quad-walks mid-show; sit zero at both ends
    "dance_encore",
    # dance goes planted mid-routine but starts AND ends at sit zero
    # (limp), so it homes like an air demo and must not stand-hold after.
    "dance",
    "dance_walk",
})
ZERO_TOL_DEG = 6.0
CAL_TFT_MIN_PERIOD_S = 10.0
CAL_TFT_PHASE_ORDER = (
    "safe_zero",
    "bus_error_rate_still",
    "imu_rest",
    "geometry_plant",
    "geometry_sweep",
    "geometry_plausibility",
    "imu_body_frame",
    "imu_frame_validation",
    "stability_margin",
    "mass_shift_response",
    "traction_probe",
    "bus_error_rate_moving",
    "return_zero",
    "proprioception_check",
    "camera_witness",
    "bus_power_health",
    "actuator_snapshot",
    "report",
)
BUS_ERROR_RATE_HZ = 100.0
BUS_ERROR_RATE_STILL_SECONDS = 2.0
BUS_ERROR_RATE_OK_MAX = 0.01


def _env_truthy(name: str, default: bool = False) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on", "full", "csv")

# Sit-from-stand exemption to the MAX_SAFE_DELTA_DEG guard: the present
# pose counts as "at stand" when every live joint is within this many
# degrees of the captured stand pose. Must tolerate a gait stopped
# mid-stride: the loaded tripod freezes in its push posture, measured
# up to 17.4 deg from the old plant gate (tape session 08-10, leg2b —
# 15 deg refused the Sit button after EVERY walk). A wrong-zero pose
# reads knees ~160 deg off the plant, so 30 deg is still unambiguous.

def _emit_servo_fb(tag: str, tracker, target: list[float] | None = None,
                   ) -> None:
    """Log the tracker's last full feedback sweep to the event stream.

    One ``servo_fb`` event per sweep: per-joint present deg, current,
    speed, load, temp — "what all the servos are saying" — plus the
    commanded target at that moment. Lands in logs/events.jsonl and
    the /api/events ring.
    """
    try:
        from event_log import emit
    except ImportError:
        return
    try:
        data: dict = {"joints": [
            {"j": fb["joint"], "id": fb["id"],
             "deg": round(fb["deg"], 1),
             "a": round(fb["current_a"], 2),
             "dps": round(fb["speed_deg_s"]),
             "load_pct": fb["load_pct"],
             "temp_c": fb["temp_c"]} for fb in tracker.last_fb]}
        if target is not None:
            data["target_deg"] = [round(x, 1) for x in target]
        emit("servo_fb", tag, data=data)
    except Exception:
        pass


def _load_names() -> dict[int, str]:
    for path in REGISTRY_CANDIDATES:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        out: dict[int, str] = {}
        for entry in (data.get("servos") or {}).values():
            try:
                out[int(entry["id"])] = str(entry.get("name") or f"ID{entry['id']}")
            except (KeyError, TypeError, ValueError):
                continue
        if out:
            return out
    return {}


def joint_label(joint: int, names: dict[int, str]) -> str:
    sid = joint_to_servo_id(joint)
    if sid in names:
        return names[sid]
    leg, axis = divmod(joint, 3)
    return f"L{leg} {AXIS[axis]}"


class _BusQualityTracker:
    """Collect bus transaction success/failure without changing call sites."""

    TRACKED_METHODS = {
        "read_snapshot",
        "step_all",
        "read_all_positions",
        "read_all_feedback",
        "read_imu",
        "read_position_deg",
        "read_feedback",
        "write_all",
        "write_joint",
        "enable_all_torque",
        "safe_stop",
        "scan",
    }
    TRACKED_PKT_METHODS = {
        "WritePosEx",
        "write1ByteTxRx",
        "write2ByteTxRx",
        "read1ByteTxRx",
        "read2ByteTxRx",
        "ping",
    }

    def __init__(self, label: str, *,
                 expected_joints: int = N_JOINTS,
                 ok_error_rate: float = BUS_ERROR_RATE_OK_MAX):
        self.label = label
        self.expected_joints = int(expected_joints)
        self.ok_error_rate = float(ok_error_rate)
        self.attempts = 0
        self.failures = 0
        self.ok_count = 0
        self.durations: list[float] = []
        self.by_method: dict[str, dict[str, int]] = {}
        self.first_errors: list[dict] = []
        self.min_live: int | None = None
        self.max_live: int | None = None
        self._first_t: float | None = None
        self._last_t: float | None = None

    def wrap(self, bus):
        return _TrackedBus(bus, self)

    def record(self, method: str, elapsed_s: float, *,
               result=None, exc: BaseException | None = None) -> None:
        now = time.monotonic()
        if self._first_t is None:
            self._first_t = now
        self._last_t = now
        self.attempts += 1
        self.durations.append(float(elapsed_s))
        row = self.by_method.setdefault(method, {"attempts": 0, "failures": 0})
        row["attempts"] += 1
        ok, live = self._result_ok(method, result, exc)
        if live is not None:
            self.min_live = live if self.min_live is None else min(self.min_live, live)
            self.max_live = live if self.max_live is None else max(self.max_live, live)
        if ok:
            self.ok_count += 1
            return
        self.failures += 1
        row["failures"] += 1
        if len(self.first_errors) < 8:
            err = repr(exc) if exc is not None else self._short_result(result)
            self.first_errors.append({
                "method": method,
                "error": err,
                **({"live_joints": live} if live is not None else {}),
            })

    def _result_ok(self, method: str, result,
                   exc: BaseException | None) -> tuple[bool, int | None]:
        if exc is not None:
            return False, None
        short = method.rsplit(".", 1)[-1]
        if short in ("read_snapshot", "step_all"):
            live = 0
            if isinstance(result, dict):
                live = len(result.get("pos_deg") or {})
            return live >= self.expected_joints, live
        if short in ("read_all_positions", "read_all_feedback"):
            live = len(result) if isinstance(result, dict) else 0
            return live >= self.expected_joints, live
        if short in ("read_position_deg", "read_feedback"):
            return result is not None, None
        if short == "read_imu":
            return isinstance(result, dict), None
        if short == "scan":
            live = len(result) if isinstance(result, (list, tuple, set)) else 0
            return live >= self.expected_joints, live
        if short in ("write_all", "write_joint", "enable_all_torque",
                     "safe_stop", "txPacket"):
            return True, None
        if short == "WritePosEx":
            try:
                return int(result) == 0, None
            except (TypeError, ValueError):
                return result is not False, None
        if short in self.TRACKED_PKT_METHODS:
            if isinstance(result, tuple) and len(result) >= 2:
                try:
                    return int(result[1]) == 0, None
                except (TypeError, ValueError):
                    return False, None
            if isinstance(result, int):
                return result == 0, None
            return result is not False, None
        return result is not False, None

    def _short_result(self, result) -> str:
        if isinstance(result, dict):
            keys = ",".join(list(result.keys())[:5])
            if "pos_deg" in result:
                return f"dict(pos_deg={len(result.get('pos_deg') or {})})"
            return f"dict({keys})"
        if isinstance(result, (list, tuple, set)):
            return f"{type(result).__name__}(len={len(result)})"
        return repr(result)

    def summary(self, *, mode: str, target_hz: float | None = None,
                seconds_target: float | None = None,
                non_blocking: bool = True) -> dict:
        if self.attempts <= 0:
            return {
                "ok": False,
                "skipped": True,
                "non_blocking": non_blocking,
                "mode": mode,
                "label": self.label,
                "msg": f"{self.label} bus error rate unavailable",
            }
        error_rate = self.failures / self.attempts
        elapsed = None
        if self._first_t is not None and self._last_t is not None:
            elapsed = max(0.0, self._last_t - self._first_t)
        durs = sorted(self.durations)

        def pct(q: float) -> float | None:
            if not durs:
                return None
            i = min(len(durs) - 1,
                    max(0, int(round((q / 100.0) * (len(durs) - 1)))))
            return durs[i] * 1000.0

        pct_rate = error_rate * 100.0
        ok = error_rate <= self.ok_error_rate
        msg = (
            f"{self.label} bus errors {self.failures}/{self.attempts} "
            f"({pct_rate:.2f}%)")
        if self.max_live is not None:
            msg += (
                f"; live {self.min_live}-{self.max_live}/"
                f"{self.expected_joints}")
        if target_hz:
            msg += f"; target {target_hz:.0f}Hz"
        return {
            "ok": ok,
            "non_blocking": non_blocking,
            "mode": mode,
            "label": self.label,
            "error": None if ok else msg,
            "warning": msg if self.failures else None,
            "msg": msg,
            "attempts": self.attempts,
            "ok_count": self.ok_count,
            "fail_count": self.failures,
            "error_rate": round(error_rate, 6),
            "error_rate_pct": round(pct_rate, 3),
            "ok_error_rate_max": self.ok_error_rate,
            "target_hz": target_hz,
            "seconds_target": seconds_target,
            "elapsed_s": None if elapsed is None else round(elapsed, 3),
            "attempt_rate_hz": (
                None if not elapsed else round(self.attempts / elapsed, 2)),
            "mean_ms": (
                None if not self.durations
                else round(sum(self.durations) * 1000.0 / len(self.durations), 3)),
            "p50_ms": None if pct(50) is None else round(pct(50), 3),
            "p95_ms": None if pct(95) is None else round(pct(95), 3),
            "p99_ms": None if pct(99) is None else round(pct(99), 3),
            "max_ms": (
                None if not self.durations
                else round(max(self.durations) * 1000.0, 3)),
            "min_live_joints": self.min_live,
            "max_live_joints": self.max_live,
            "by_method": [
                {
                    "method": k,
                    "attempts": v["attempts"],
                    "failures": v["failures"],
                }
                for k, v in sorted(self.by_method.items())
            ],
            "first_errors": list(self.first_errors),
            "benefit": (
                "separates serial/bus reliability from geometry, traction, "
                "or policy behavior"),
        }


class _TrackedBus:
    def __init__(self, bus, tracker: _BusQualityTracker):
        object.__setattr__(self, "_bus", bus)
        object.__setattr__(self, "_tracker", tracker)
        object.__setattr__(self, "_pkt", None)

    def __getattr__(self, name: str):
        if name == "pkt":
            pkt = object.__getattribute__(self, "_pkt")
            if pkt is None:
                pkt = _TrackedPkt(
                    getattr(object.__getattribute__(self, "_bus"), "pkt"),
                    object.__getattribute__(self, "_tracker"))
                object.__setattr__(self, "_pkt", pkt)
            return pkt
        attr = getattr(object.__getattribute__(self, "_bus"), name)
        tracker = object.__getattribute__(self, "_tracker")
        if callable(attr) and name in _BusQualityTracker.TRACKED_METHODS:
            def wrapped(*args, **kwargs):
                t0 = time.monotonic()
                try:
                    result = attr(*args, **kwargs)
                except Exception as e:
                    tracker.record(name, time.monotonic() - t0, exc=e)
                    raise
                tracker.record(name, time.monotonic() - t0, result=result)
                return result
            return wrapped
        return attr

    def __setattr__(self, name: str, value) -> None:
        setattr(object.__getattribute__(self, "_bus"), name, value)


class _TrackedPkt:
    def __init__(self, pkt, tracker: _BusQualityTracker):
        self._pkt = pkt
        self._tracker = tracker
        self._group = None

    def __getattr__(self, name: str):
        if name == "groupSyncWrite":
            if self._group is None:
                self._group = _TrackedGroupSyncWrite(
                    getattr(self._pkt, "groupSyncWrite"), self._tracker)
            return self._group
        attr = getattr(self._pkt, name)
        if callable(attr) and name in _BusQualityTracker.TRACKED_PKT_METHODS:
            def wrapped(*args, **kwargs):
                t0 = time.monotonic()
                try:
                    result = attr(*args, **kwargs)
                except Exception as e:
                    self._tracker.record(f"pkt.{name}",
                                         time.monotonic() - t0, exc=e)
                    raise
                self._tracker.record(f"pkt.{name}",
                                     time.monotonic() - t0, result=result)
                return result
            return wrapped
        return attr


class _TrackedGroupSyncWrite:
    def __init__(self, group, tracker: _BusQualityTracker):
        self._group = group
        self._tracker = tracker

    def __getattr__(self, name: str):
        attr = getattr(self._group, name)
        if name == "txPacket" and callable(attr):
            def wrapped(*args, **kwargs):
                t0 = time.monotonic()
                try:
                    result = attr(*args, **kwargs)
                except Exception as e:
                    self._tracker.record("pkt.groupSyncWrite.txPacket",
                                         time.monotonic() - t0, exc=e)
                    raise
                self._tracker.record("pkt.groupSyncWrite.txPacket",
                                     time.monotonic() - t0, result=result)
                return result
            return wrapped
        return attr




# linux_control/ — the bench server's home dir. logs/, policies/ and
# standup_modes.json anchor here. A function (not a constant) so tests can
# patch ``common._LC_DIR`` and redirect report/log writes everywhere at once
# (the pre-split equivalent was patching bench_api.__file__).
_LC_DIR = Path(__file__).resolve().parents[1]


def lc_dir() -> Path:
    return _LC_DIR


# Re-export everything, including underscore names: the trackers and helpers
# are part of the legacy bench_api module surface that tests rely on.
__all__ = [n for n in list(globals()) if not n.startswith("__")]
