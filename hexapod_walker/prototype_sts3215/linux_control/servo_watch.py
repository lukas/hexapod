"""Background servo health watchdog: liveness + over-temperature.

Every few seconds it does ONE MCU round-trip (``read_all_feedback`` — a
single bulk transaction covering all 18 expected servos) and publishes:

- which expected servos are MISSING (drives the TFT error panel and the
  ``servo`` block in ``/api/robot``), and
- each servo's temperature. Any servo at/above ``SHUTOFF_C`` for three
  consecutive watchdog reads gets its torque cut and is latched ``tripped``
  until it cools below
  ``CLEAR_C``. Torque is never re-enabled automatically — that is the
  operator's call (ARM again once it has cooled).

The STS3215 also has its own EEPROM max-temp limit (~70 C default) that
unloads torque in firmware; this watchdog trips earlier (65 C, matching
``rl_move`` safety), logs the event, and puts it on the screen instead of
failing silently (2026-08-06: a knee cooked with no warning anywhere).

Bus contention: the MCU bus serializes transactions internally, so a
watch read only adds a brief latency blip to a running job's loop. While
a bench job owns the bus we still watch, just less often (``BUSY_PERIOD``)
— overheat risk is highest exactly when something is driving the motors.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable

from feetech_bus import N_JOINTS, joint_to_servo_id

WATCH_PERIOD_S = 3.0    # idle cadence
BUSY_PERIOD_S = 5.0     # while a demo/job owns the bus (10.0 until 08-11:
                        # with the old sparse debounce that meant long periods
                        # blind time exactly while motion makes heat — two
                        # hips sailed past shutoff mid-glide before anything
                        # bus-side noticed)
WARN_C = 55             # show on screen / web
SHUTOFF_C = 65          # cut that servo's torque (rl_move safety uses 65)
CLEAR_C = 50            # un-latch "tripped" once cooled below this
STALE_S = 30.0          # snapshot older than this counts as unknown
TEMP_TRIP_READS = 3     # same joint; rejects consecutive corrupt bus bytes

# Static strain (2026-09-22): a robot that is ARMED, has NO job running and is
# NOT MOVING must draw almost nothing -- a whole standing hold reads ~0.3 A
# total.  Sustained current at rest means the servos are fighting geometry or
# friction toward a target they cannot reach (hexapod2: 18 servos at 2-4 A for
# minutes after a stopped lower, hips at 60-70 % load, L5 hip to 56 C).  Two
# consecutive reads over either threshold -> on_strain(reason, info): the owner
# releases the robot gently (torque limit stepped down, then torque off).
STRAIN_TOTAL_A = 1.0    # sum over all servos (plausible readings only)
STRAIN_SERVO_A = 0.6    # or any single servo
STRAIN_STILL_DPS = 5.0  # every joint slower than this = static
STRAIN_READS = 2
IMPLAUSIBLE_A = 10.0    # STS3215 stalls at ~2.7 A; higher = corrupt byte


class ServoWatch:
    """Liveness + temperature monitor with a per-servo thermal cutoff."""

    def __init__(self, get_bus: Callable[[], Any],
                 is_busy: Callable[[], bool],
                 label: Callable[[int], str],
                 on_trip: Callable[[str], None] | None = None,
                 *, is_armed: Callable[[], bool] | None = None,
                 on_strain: Callable[[str, dict], None] | None = None):
        self._get_bus = get_bus
        self._is_busy = is_busy
        self._label = label  # joint index -> human name ("L5 knee")
        self._is_armed = is_armed
        self._on_strain = on_strain
        self._strain_reads = 0
        self._strain_released = False   # latched until the robot reads calm again
        self._strain: dict = {}
        # Motion killer (08-11): cutting torque on ONE hot servo while a
        # job keeps driving the other 17 is a fall, not a save. The owner
        # passes a callback that stops the whole robot (abort demo/RL
        # worker, gait stop, torque-all off).
        self._on_trip = on_trip
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._snap: dict = {"ok": False, "ts": 0.0}
        self._tripped: set[int] = set()   # joints we torqued off for heat
        # Per-joint consecutive hot counts. Corrupted bytes on the shared bus
        # produced phantom 70-102 C sequences that "cooled" to ~33 C within
        # seconds — thermally impossible. Real heat persists across reads.
        self._hot_counts: dict[int, int] = {}

    # -- public ---------------------------------------------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="servo-watch", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def last_feedback(self) -> tuple[dict, float] | None:
        """Most recent raw ``read_all_feedback`` result and its unix time (no bus traffic)."""
        with self._lock:
            return getattr(self, "_last_fb", None)

    def state(self) -> dict:
        """Latest snapshot (display-ready; no bus traffic)."""
        with self._lock:
            snap = dict(self._snap)
        if snap.get("ts") and time.time() - snap["ts"] > STALE_S:
            snap["ok"] = False
            snap["stale"] = True
        return snap

    # -- internals ------------------------------------------------------
    def _run(self) -> None:
        while not self._stop.is_set():
            busy = False
            try:
                busy = bool(self._is_busy())
                self._tick()
            except Exception as e:
                with self._lock:
                    self._snap = {"ok": False, "ts": time.time(),
                                  "error": str(e)}
            self._stop.wait(BUSY_PERIOD_S if busy else WATCH_PERIOD_S)

    def _tick(self) -> None:
        bus = self._get_bus()
        if bus is None or not hasattr(bus, "read_all_feedback"):
            with self._lock:
                self._snap = {"ok": False, "ts": time.time(),
                              "error": "no bus"}
            return

        fb = bus.read_all_feedback()  # {joint: {temp_c, current_a, ...}}
        now = time.time()

        # IMU liveness piggybacks on the same tick: one cheap MCU round
        # trip. None = bus can't probe it (USB adapter mode), not a fault.
        imu_ok = None
        read_imu = getattr(bus, "read_imu", None)
        if callable(read_imu):
            try:
                imu_ok = read_imu(timeout=0.6, apply_calib=False) is not None
            except Exception:
                imu_ok = False

        missing = sorted(j for j in range(N_JOINTS) if j not in fb)
        hot: list[dict] = []
        max_t, max_j = -1, None
        for j, f in sorted(fb.items()):
            t = int(f.get("temp_c") or 0)
            if t > max_t:
                max_t, max_j = t, j
            if t >= SHUTOFF_C and j not in self._tripped:
                self._hot_counts[j] = self._hot_counts.get(j, 0) + 1
                if self._hot_counts[j] >= TEMP_TRIP_READS:
                    self._trip(bus, j, t)
            elif t < SHUTOFF_C:
                self._hot_counts.pop(j, None)
            if j in self._tripped and t <= CLEAR_C:
                self._tripped.discard(j)
                self._emit("servo_cooled",
                           f"{self._label(j)} cooled to {t}C "
                           "(still torque-off; ARM to re-enable)",
                           {"joint": j, "temp_c": t})
            if t >= WARN_C:
                hot.append({"joint": j, "name": self._label(j), "temp_c": t,
                            "tripped": j in self._tripped})

        self._check_static_strain(fb)

        with self._lock:
            # raw per-joint feedback for /api/feedback while a job owns the bus (no extra bus traffic)
            self._last_fb = ({j: dict(f) for j, f in fb.items()}, now)
            self._snap = {
                "ok": True,
                "ts": now,
                "expected": N_JOINTS,
                "live": len(fb),
                "missing": missing,
                "missing_names": [self._label(j) for j in missing],
                "max_temp_c": max_t if max_t >= 0 else None,
                "hottest": self._label(max_j) if max_j is not None else None,
                "hot": hot,
                "tripped": sorted(self._tripped),
                "tripped_names": [self._label(j)
                                  for j in sorted(self._tripped)],
                "warn_c": WARN_C,
                "shutoff_c": SHUTOFF_C,
                "temp_trip_reads": TEMP_TRIP_READS,
                "imu_ok": imu_ok,
                "strain": dict(self._strain),
            }

    def _check_static_strain(self, fb: dict) -> None:
        """Armed + idle + still + drawing current = fighting.  Two reads -> release."""
        cur = {j: abs(float(f.get("current_a") or 0.0)) for j, f in fb.items()}
        cur = {j: a for j, a in cur.items() if a < IMPLAUSIBLE_A}
        total = sum(cur.values())
        worst_j = max(cur, key=cur.get) if cur else None
        worst = cur[worst_j] if worst_j is not None else 0.0
        speeds = [abs(float(f.get("speed_deg_s") or 0.0)) for f in fb.values()]
        still = bool(speeds) and max(speeds) < STRAIN_STILL_DPS
        armed = bool(self._is_armed()) if self._is_armed is not None else False
        busy = bool(self._is_busy())
        strained = armed and not busy and still and (total > STRAIN_TOTAL_A or worst > STRAIN_SERVO_A)
        self._strain = {"total_a": round(total, 3), "worst_a": round(worst, 3),
                        "worst": self._label(worst_j) if worst_j is not None else None,
                        "still": still, "armed": armed, "busy": busy,
                        "reads": self._strain_reads, "released": self._strain_released}
        if not strained:
            self._strain_reads = 0
            if total < STRAIN_TOTAL_A * 0.5:
                self._strain_released = False
            self._strain.update(reads=0, released=self._strain_released)
            return
        self._strain_reads += 1
        self._strain["reads"] = self._strain_reads
        if self._strain_reads < STRAIN_READS or self._strain_released or self._on_strain is None:
            return
        self._strain_released = True
        reason = (f"static strain: {total:.2f} A total, worst {self._label(worst_j)} {worst:.2f} A "
                  f"while armed, idle and still for {self._strain_reads} reads")
        self._emit("static_strain", reason + " — releasing", dict(self._strain), level="warn")
        try:
            self._on_strain(reason, dict(self._strain))
        except Exception as e:
            self._emit("static_strain", f"release FAILED: {e}", dict(self._strain), level="warn")

    def _trip(self, bus: Any, joint: int, temp_c: int) -> None:
        """Cut torque on one over-temperature servo (never re-enables)."""
        sid = joint_to_servo_id(joint)
        try:
            bus.torque(sid, False)
            ok = True
        except Exception:
            ok = False
        self._tripped.add(joint)
        self._emit("servo_overtemp",
                   f"OVERTEMP {self._label(joint)} {temp_c}C >= {SHUTOFF_C}C"
                   f" — torque {'CUT' if ok else 'cut FAILED'}",
                   {"joint": joint, "servo_id": sid, "temp_c": temp_c,
                    "torque_cut_ok": ok}, level="warn")
        if self._on_trip is not None:
            try:
                self._on_trip(f"overtemp {self._label(joint)} {temp_c}C")
            except Exception as e:
                self._emit("servo_overtemp",
                           f"on_trip panic-stop FAILED: {e}",
                           {"joint": joint}, level="warn")

    @staticmethod
    def _emit(kind: str, msg: str, data: dict, *, level: str = "info"):
        try:
            from event_log import emit
            emit(kind, msg, src="servo_watch", data=data, level=level)
        except Exception:
            print(f"[servo_watch] {msg}")
