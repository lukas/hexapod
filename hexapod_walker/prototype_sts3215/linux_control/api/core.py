"""BenchAPI route group: lifecycle, status display, servo watch, robot state/status/pose, command_pose, stand hold.

Moved verbatim from bench_api.py (2026-08-29 component-boundaries split);
mixed into ``bench_api.BenchAPI``. Route/JSON shapes are unchanged.
"""
from __future__ import annotations

from .common import *  # noqa: F401,F403


class CoreApi:
    def __init__(self, drive: "DriveController"):
        self.drive = drive
        self.names = _load_names()
        self._demo_thread: threading.Thread | None = None
        self._demo_abort = threading.Event()
        self._demo_gen = 0  # bumps on each new demo/zero so stale workers exit
        self._demo_name: str | None = None
        self._demo_status = "idle"
        self._demo_params: dict = {}
        # LIVE tempo multiplier (web slider while a demo runs). Streamed
        # demos read it every tick; breathe at each half-breath.
        self._demo_speed_live = 1.0
        # What the robot is *trying* to do (UI-facing intent).
        # idle | limp | armed | demo | zeroing | stopping | calibrating
        self._activity = "idle"
        self._activity_detail = ""
        self._lock = threading.Lock()
        # Last / in-progress step-calibrate report (web Calibrate tab).
        self._cal_result: dict | None = None
        self._cal_progress: dict = {}
        # Last demo cmd-vs-actual telemetry (auto-logged from web demos).
        self._demo_telemetry: dict | None = None
        # Refcount while a motion/test job owns timing on the MCU link.
        # The TFT display thread must NOT transact then: even "display only"
        # DJ redraws hold the shared serial path long enough to pause motion.
        self._bus_hot = 0
        # Measure tab: finished run awaiting the operator's tape reading.
        self._meas_pending: dict | None = None
        self._status_display = None
        self._servo_watch = None
        self._tft_progress_lock = threading.Lock()
        self._tft_progress_thread: threading.Thread | None = None
        self._tft_progress_key = ""
        self._tft_progress_t = 0.0
        # Live drive session (rl_policy.DriveCommand) — set while an
        # rl_drive worker owns the demo slot, None otherwise.
        self._drive_cmd = None
        # Quad-mode session state. Split quad controls require the operator
        # to rear up first; walk/trot/down then run from that held stance.
        self._quad_reared = False

    def start_status_display(self) -> None:
        """Mirror web status + Σ motor current onto the MCU ST7789."""
        if self._status_display is not None:
            return
        try:
            from status_display import StatusDisplay
        except ImportError:
            return

        def _bus():
            return self.drive.bus

        self._status_display = StatusDisplay(
            _bus, lambda: self.robot_state(), period_s=1.8)
        self._status_display.start()
        if self._status_display._recovered:
            print("[web] TFT recovered (hard reinit OK)")
        else:
            err = self._status_display._last_err or "unknown"
            print(f"[web] TFT recover FAILED: {err}")

    def stop_status_display(self) -> None:
        if self._status_display is not None:
            self._status_display.stop()
            self._status_display = None

    def tft_ready(self) -> dict:
        """Clear a stale deploy/job banner with one normal TFT repaint.

        This is intentionally a one-shot endpoint for deploy scripts. The
        continuous status-display thread stays opt-in because screen redraws
        share the MCU serial link with robot motion.
        """
        d = self.drive
        bus = getattr(d, "bus", None)
        if getattr(d, "dry_run", False) or bus is None:
            return {"ok": False, "skipped": True, "error": "no bus"}
        with self._lock:
            busy = (
                self._bus_hot > 0
                or bool(self._demo_thread and self._demo_thread.is_alive())
                or self._activity in ("calibrating", "zeroing", "stopping", "demo")
            )
        if busy:
            return {
                "ok": False,
                "skipped": True,
                "error": "motion or calibration owns the MCU link",
            }
        push = getattr(bus, "display_push", None)
        if not callable(push):
            return {"ok": False, "skipped": True, "error": "no TFT display API"}
        lines = [
            "WEB READY",
            "control online",
            "servos unchanged",
            time.strftime("%H:%M:%S"),
        ]
        try:
            painted = push(lines, timeout=5.0)
        except Exception as e:
            return {"ok": False, "error": f"TFT ready repaint failed: {e}"}
        if painted is None:
            return {"ok": False, "error": "TFT ready repaint failed"}
        return {"ok": True, "mode": "tft_ready", "display": painted}

    def _bus_hot_begin(self) -> None:
        with self._lock:
            self._bus_hot = int(self._bus_hot) + 1

    def _bus_hot_end(self) -> None:
        with self._lock:
            self._bus_hot = max(0, int(self._bus_hot) - 1)

    def _calibration_tft_pct(self, progress: dict) -> int:
        idx, total = progress.get("index"), progress.get("total")
        if isinstance(idx, int) and isinstance(total, int) and total > 0:
            return int(round(100.0 * (idx + 0.5) / total))
        phase = str(progress.get("phase") or "").strip().lower()
        if phase in CAL_TFT_PHASE_ORDER:
            i = CAL_TFT_PHASE_ORDER.index(phase)
            return int(round(100.0 * (i + 0.5) / len(CAL_TFT_PHASE_ORDER)))
        return -1

    def _calibration_tft_lines(self, progress: dict, *,
                               final: bool = False) -> list[str]:
        try:
            from status_display import calibration_phase_title
        except ImportError:
            def calibration_phase_title(phase):
                return str(phase or "").replace("_", " ").upper()[:26]

        def wrap(text: str, width: int, max_lines: int) -> list[str]:
            words = str(text).split()
            lines: list[str] = []
            cur = ""
            for word in words:
                if not cur:
                    cur = word
                elif len(cur) + 1 + len(word) <= width:
                    cur += " " + word
                else:
                    lines.append(cur)
                    if len(lines) == max_lines:
                        return lines
                    cur = word
            if cur:
                lines.append(cur)
            return lines[:max_lines]

        msg = str(progress.get("msg") or "calibrating").replace("…", "...")
        low = msg.lower()
        if final:
            title = (
                "CALIBRATION STOPPED"
                if ("abort" in low or "error" in low or "failed" in low)
                else "CALIBRATION DONE"
            )
        else:
            title = "CALIBRATING"
        phase = str(progress.get("phase") or progress.get("mode") or "")
        phase_title = calibration_phase_title(phase) or "CHECKUP"
        body = [phase_title]
        body.extend(wrap(msg, 26, 2))
        while len(body) < 4:
            body.append("")
        armed = False
        try:
            with self.drive._lock:
                armed = bool(self.drive.armed)
        except Exception:
            pass
        footer = "ARMED" if armed else "limp"
        if not final and not armed:
            footer = "watch robot"
        return [title] + body[:4] + [footer]

    def _queue_calibration_tft(self, progress: dict, *, force: bool = False,
                               final: bool = False) -> None:
        """Opportunistic TFT progress hint; never waits to acquire the MCU lock."""
        if not _env_truthy("HEXAPOD_TFT_CAL_PROGRESS", True):
            return
        d = self.drive
        bus = None if getattr(d, "dry_run", False) else getattr(d, "bus", None)
        display = getattr(bus, "display_job_try", None)
        if not callable(display):
            return
        now = time.monotonic()
        phase = str(progress.get("phase") or progress.get("mode") or "")
        msg = str(progress.get("msg") or "")
        key = phase or msg[:40]
        with self._tft_progress_lock:
            busy = (
                self._tft_progress_thread is not None
                and self._tft_progress_thread.is_alive()
            )
            phase_changed = bool(key and key != self._tft_progress_key)
            rate_ok = now - self._tft_progress_t >= CAL_TFT_MIN_PERIOD_S
            if busy or not (force or phase_changed or rate_ok):
                return
            lines = self._calibration_tft_lines(progress, final=final)
            pct = self._calibration_tft_pct(progress)
            self._tft_progress_key = key
            self._tft_progress_t = now

            def _paint() -> None:
                try:
                    display(lines, pct=pct, timeout=1.8)
                except Exception:
                    pass

            thread = threading.Thread(
                target=_paint, name="hexapod-cal-tft", daemon=True)
            self._tft_progress_thread = thread
            thread.start()

    def start_servo_watch(self) -> None:
        """Liveness + over-temp watchdog (TFT error panel, 65C cutoff)."""
        if self._servo_watch is not None or self.drive.dry_run:
            return
        try:
            from servo_watch import ServoWatch
        except ImportError:
            return
        self._servo_watch = ServoWatch(
            lambda: self.drive.bus,
            lambda: bool(self._demo_thread and self._demo_thread.is_alive()),
            lambda j: joint_label(j, self.names),
            on_trip=self.thermal_panic)
        self._servo_watch.start()

    def thermal_panic(self, reason: str) -> None:
        """Kill ALL motion and limp the robot — the watchdog's overtemp
        response (08-11: two hips crossed shutoff mid-glide; the old
        single-servo cut would have left the job driving the other 17
        joints on a robot with one dead leg). Runs on the watchdog
        thread; never raises."""
        try:
            from event_log import emit
            emit("thermal_panic",
                 f"THERMAL PANIC: {reason} — stopping all motion, "
                 "torque off all", src="servo_watch", level="error")
        except Exception:
            print(f"[thermal_panic] {reason}")
        freed = self._preempt_demo_thread(reason=f"thermal: {reason}",
                                          timeout=4.0)
        d = self.drive
        with d._lock:
            d.mode = "idle"
            try:
                d.gait.stop()
            except Exception:
                pass
            d.armed = False
            if freed:
                # Bus rule (stop_demo): no writes while a stuck worker
                # might still be mid-SyncWrite — that hang cooked the MCU
                # bridge before. If the join timed out, the per-servo cut
                # + the servo's own EEPROM limit (~70C) stay the backstop.
                try:
                    d._torque_all(False)
                except Exception:
                    pass
        with self._lock:
            self._activity = "limp"
            self._activity_detail = f"thermal panic: {reason}"

    def stop_servo_watch(self) -> None:
        if self._servo_watch is not None:
            self._servo_watch.stop()
            self._servo_watch = None

    # -- robot / demo state --------------------------------------------------
    def _set_activity(self, activity: str, detail: str = "") -> None:
        with self._lock:
            self._activity = activity
            self._activity_detail = detail
        # Errors/refusals that only surface via status polling still get
        # a line in the event log + logs/errors.jsonl.
        low = (detail or "").lower()
        if "error" in low or "refused" in low:
            try:
                from event_log import emit
                emit("error", f"{activity}: {detail}", src="bench",
                     level="error", data={"activity": activity})
            except Exception:
                pass

    def demo_state(self) -> dict:
        with self._lock:
            return {
                "name": self._demo_name,
                "status": self._demo_status,
                "running": bool(self._demo_thread and self._demo_thread.is_alive()),
                "speed_live": self._demo_speed_live,
                "params": dict(self._demo_params),
                # Live worker progress (msg + optional joint/index/total) —
                # the TFT job panel renders counts/percent from this.
                "progress": dict(self._cal_progress)
                if self._cal_progress else None,
                "telemetry": dict(self._demo_telemetry)
                if self._demo_telemetry else None,
                "bus_hot": bool(
                    self._bus_hot and self._demo_thread
                    and self._demo_thread.is_alive()),
            }

    def robot_state(self, *, check_zero: bool = False) -> dict:
        """Global intent + drive mode (+ optional near-zero probe)."""
        d = self.drive
        with d._lock:
            armed = d.armed
            mode = d.mode
            dry = d.dry_run
            drive_status = d.status
        demo = self.demo_state()
        with self._lock:
            activity = self._activity
            detail = self._activity_detail
        # Derive a clearer activity if the worker hasn't set one yet.
        if demo["running"] and activity not in ("demo", "zeroing", "stopping"):
            activity = "demo"
        elif not demo["running"] and activity in ("demo", "zeroing", "stopping"):
            # Stale — worker finished without clearing (shouldn't happen).
            if demo["status"] in ("done", "aborted", "idle", "skipped"):
                activity = "armed" if armed else "limp"
                detail = demo["status"]
        if not armed and activity in ("idle", "armed"):
            activity = "limp"

        out = {
            "activity": activity,
            "detail": detail,
            "armed": armed,
            "mode": mode,
            "dry_run": dry,
            "drive_status": drive_status,
            "demo": demo,
            "air_demos_need_zero": True,
            "zero_tol_deg": ZERO_TOL_DEG,
        }
        if self._servo_watch is not None:
            out["servo"] = self._servo_watch.state()
        if check_zero:
            out["zero"] = self.check_near_zero()
        return out

    def check_near_zero(self, tol_deg: float = ZERO_TOL_DEG) -> dict:
        """Read present pose; ``at_zero`` if all live joints within tol of 0°."""
        d = self.drive
        if d.dry_run:
            return {"at_zero": True, "max_err_deg": 0.0, "live": 0, "tol_deg": tol_deg}
        if not d.bus:
            return {"at_zero": False, "max_err_deg": None, "live": 0,
                    "tol_deg": tol_deg, "error": "no bus"}
        # Avoid fighting an active demo thread on the serial bus.
        if self._demo_thread and self._demo_thread.is_alive():
            return {"at_zero": False, "max_err_deg": None, "live": 0,
                    "tol_deg": tol_deg, "error": "busy", "busy": True}
        max_err = 0.0
        n = 0
        try:
            with d._lock:
                bus = d.bus
                for joint in range(N_JOINTS):
                    deg = bus.read_position_deg(joint)
                    if deg is None:
                        continue
                    n += 1
                    max_err = max(max_err, abs(float(deg)))
        except Exception as e:
            return {"at_zero": False, "max_err_deg": None, "live": n,
                    "tol_deg": tol_deg, "error": str(e)}
        if n == 0:
            return {"at_zero": False, "max_err_deg": None, "live": 0,
                    "tol_deg": tol_deg, "error": "no feedback"}
        return {
            "at_zero": max_err <= float(tol_deg),
            "max_err_deg": round(max_err, 2),
            "live": n,
            "tol_deg": float(tol_deg),
        }

    # -- status (motors table) -----------------------------------------------
    def status(self) -> dict:
        d = self.drive
        with d._lock:
            port = d.port
            dry = d.dry_run
            armed = d.armed
            mode = d.mode
            bus = d.bus
            drive_status = d.status
        motors = []
        live: list[int] = []
        if bus is not None and not (self._demo_thread and self._demo_thread.is_alive()):
            try:
                from urt2_bench import read_servo_health
                live = sorted(bus.scan(range(1, 31)))
                for sid in live:
                    try:
                        h = read_servo_health(bus, sid)
                    except Exception as e:
                        motors.append({
                            "id": sid, "ok": False, "error": str(e),
                        })
                        continue
                    joint = sid - 2 if 2 <= sid <= 19 else None
                    motors.append({
                        "id": sid,
                        "ok": True,
                        "joint": joint,
                        "name": (joint_label(joint, self.names)
                                 if joint is not None
                                 else self.names.get(sid, f"ID{sid}")),
                        "deg": round(float(h.get("deg", 0.0)), 2),
                        "load_pct": round(float(h.get("load_pct", 0.0)), 1),
                        "current_a": round(float(h.get("current_a", 0.0)), 3),
                        "volt": round(float(h.get("volt", 0.0)), 2),
                        "temp_c": int(h.get("temp_c") or 0),
                        "moving": int(h.get("moving") or 0),
                        "torque": int(h.get("torque_enable") or 0),
                        "alarm": bool(h.get("alarm")),
                        "status_bits": [n for n, _ in (h.get("status_bits") or [])],
                        "volt_limit_max": h.get("volt_limit_max"),
                    })
            except Exception as e:
                return {
                    "port": port, "dry_run": dry, "armed": armed, "mode": mode,
                    "status": drive_status, "error": str(e),
                    "live_ids": [], "motors": [],
                    "demo": self.demo_state(),
                    "robot": self.robot_state(),
                }
        return {
            "port": port,
            "dry_run": dry,
            "armed": armed,
            "mode": mode,
            "status": drive_status,
            "live_ids": live,
            "motors": motors,
            "demo": self.demo_state(),
            "robot": self.robot_state(),
        }

    def pose(self) -> dict:
        """Fast present-angle snapshot for the live schematic (no health scan).

        Returns 18 logical joint degrees (yaw/hip/knee × 6).  Missing servos
        are ``null``.  Does **not** hold the drive lock across the whole scan
        (that starved stand/rise SyncWrites when Live was open).
        """
        d = self.drive
        with d._lock:
            dry = d.dry_run
            armed = d.armed
            mode = d.mode
            bus = d.bus
        geom = {
            "coxa_mm": 12.5,
            "femur_mm": 90.0,
            "tibia_mm": 150.0,
            "body_r_mm": 55.0,
        }
        demo = self.demo_state()
        if dry:
            # Sit-ish default so the page still draws something offline.
            deg = []
            for _ in range(6):
                deg.extend([0.0, 0.0, 0.0])
            return {
                "ok": True, "dry_run": True, "armed": armed, "mode": mode,
                "degrees": deg, "live": 0, "ts": time.time(), "geom": geom,
                "demo": demo,
            }
        if not bus:
            return {
                "ok": False, "error": "no bus", "degrees": [None] * N_JOINTS,
                "live": 0, "ts": time.time(), "geom": geom,
                "demo": demo,
            }
        degrees: list[float | None] = [None] * N_JOINTS
        live = 0
        try:
            # Bus has its own lock; avoid holding drive._lock here.
            for joint in range(N_JOINTS):
                try:
                    v = bus.read_position_deg(joint)
                except Exception:
                    v = None
                if v is None:
                    continue
                degrees[joint] = round(float(v), 2)
                live += 1
        except Exception as e:
            return {
                "ok": False, "error": str(e), "degrees": degrees,
                "live": live, "ts": time.time(), "geom": geom,
                "demo": demo,
            }
        return {
            "ok": True, "dry_run": False, "armed": armed, "mode": mode,
            "degrees": degrees, "live": live, "ts": time.time(), "geom": geom,
            "demo": demo,
        }

    def command_pose(self, q_deg, *, seconds: float = 2.0,
                     torque: int = 450, force: bool = False,
                     limp_after: bool = False,
                     label: str = "api_pose") -> dict:
        """Guarded direct 18-joint pose command.

        This is intentionally boring: one absolute target, one servo-side
        glide, one result.  It uses the bench/demo stop path first so API
        commands do not fight an existing streamed routine.
        """
        try:
            from inplace_demos import (
                CurrentPeakTracker, _enable_torque, _limp_all,
                _live_robot_ids, _set_torque_limit, ease_to_pose,
            )
            from drive_controller import MAX_SAFE_DELTA_DEG
        except ImportError as e:
            return {"ok": False, "error": str(e)}
        if self.drive.dry_run:
            return {"ok": True, "dry_run": True}
        if not self.drive.bus:
            return {"ok": False, "error": "no bus"}
        if not isinstance(q_deg, (list, tuple)) or len(q_deg) != N_JOINTS:
            return {"ok": False,
                    "error": f"q_deg must be a list of {N_JOINTS} numbers"}
        try:
            goal = [float(v) for v in q_deg]
            seconds = max(0.2, min(20.0, float(seconds)))
            torque = max(150, min(1000, int(round(float(torque)))))
            label = str(label or "api_pose")[:80]
        except (TypeError, ValueError):
            return {"ok": False, "error": "bad pose command value"}
        bad: list[dict] = []
        for j, v in enumerate(goal):
            if not math.isfinite(v):
                bad.append({"joint": j, "error": "not finite"})
                continue
            lo, hi = joint_limits(j)
            if v < lo or v > hi:
                bad.append({"joint": j, "deg": v, "min": lo, "max": hi})
        if bad:
            return {"ok": False, "error": "pose outside joint limits",
                    "bad": bad[:6]}
        if self._demo_thread and self._demo_thread.is_alive():
            if not self._preempt_demo_thread(reason=f"→ {label}",
                                             timeout=5.0):
                return {"ok": False, "error": "previous job still running",
                        "demo": self.demo_state(), "robot": self.robot_state()}

        worst, worst_joint = self._delta_vs_present(goal)
        if worst is None:
            return {"ok": False,
                    "error": ("no encoder readings — cannot check pose "
                              "delta; retry in a few seconds")}
        if not force and worst > MAX_SAFE_DELTA_DEG:
            return {"ok": False,
                    "error": (f"pose delta {worst:.1f}° on "
                              f"{_joint_label(worst_joint, self.names)}; "
                              "pass force=true for large deliberate moves"),
                    "worst_delta_deg": round(worst, 2),
                    "worst_joint": worst_joint,
                    "robot": self.robot_state()}

        self._demo_gen += 1
        gen = self._demo_gen
        self._demo_abort.clear()
        with self._lock:
            self._demo_name = "api_pose"
            self._demo_status = f"{label} · {seconds:.1f}s · τ{torque}"
            self._demo_params = {
                "label": label, "seconds": seconds, "torque": torque,
                "force": bool(force), "limp_after": bool(limp_after),
                "worst_delta_deg": round(worst, 2),
                "worst_joint": worst_joint,
            }
            self._demo_telemetry = None
        self._set_activity("demo", self._demo_status)

        d = self.drive
        live: set[int] = set()
        tracker = CurrentPeakTracker()
        ok = False
        try:
            with d._lock:
                d.mode = "demo"
                d.gait.stop()
                if not d.armed:
                    d._torque_all(True)
                    d.armed = True
            self._bus_hot_begin()
            live = _live_robot_ids(d.bus)
            if not live:
                with d._lock:
                    if d.mode == "demo":
                        d.mode = "idle"
                    d.armed = False
                self._set_activity("limp", "api_pose: no live servos")
                return {"ok": False, "error": "no live servos"}
            _set_torque_limit(d.bus, live, torque)
            _enable_torque(d.bus, live)
            ok = ease_to_pose(
                d.bus, goal,
                abort_check=self._demo_abort.is_set,
                seconds=seconds,
                label=label,
                current_tracker=tracker,
            )
            if gen != self._demo_gen:
                return {"ok": False, "aborted": True,
                        "error": "superseded by another job"}
            if limp_after:
                _limp_all(d.bus, live)
            with d._lock:
                d.armed = not limp_after
                if d.mode == "demo":
                    d.mode = "idle"
            with self._lock:
                self._demo_status = (
                    "done" if ok and not limp_after else
                    "done · limp" if ok else "aborted")
                self._demo_telemetry = {
                    "ok": bool(ok),
                    "label": label,
                    "goal_deg": [round(x, 2) for x in goal],
                    "peak_a": round(tracker.peak_a, 3),
                    "peak_joint": tracker.peak_joint,
                }
            self._set_activity("limp" if limp_after else "armed",
                               self._demo_status)
            return {
                "ok": bool(ok),
                "label": label,
                "seconds": seconds,
                "torque": torque,
                "limp_after": bool(limp_after),
                "worst_delta_deg": round(worst, 2),
                "worst_joint": worst_joint,
                "peak_a": round(tracker.peak_a, 3),
                "peak_joint": tracker.peak_joint,
                "live": sorted(live),
                "demo": self.demo_state(),
                "robot": self.robot_state(),
            }
        except Exception as e:
            try:
                if live:
                    _limp_all(d.bus, live)
            except Exception:
                pass
            with d._lock:
                if d.mode == "demo":
                    d.mode = "idle"
                d.armed = False
            with self._lock:
                self._demo_status = f"error: {e}"
            self._set_activity("limp", self._demo_status)
            return {"ok": False, "error": str(e),
                    "demo": self.demo_state(), "robot": self.robot_state()}
        finally:
            self._bus_hot_end()

    def _enter_stand_hold(self) -> None:
        """Keep re-holding the sim walk-ready stance after planted demos."""
        d = self.drive
        try:
            from rl_walk_start import walk_start_pose_degrees
            stand = walk_start_pose_degrees()
        except Exception:
            stand = None
        # Full torque for weight-bearing hold (demos leave soft limits on).
        try:
            from inplace_demos import (STAND_TORQUE_LIMIT, _live_robot_ids,
                                       _set_torque_limit)
            if d.bus is not None:
                _set_torque_limit(d.bus, _live_robot_ids(d.bus),
                                  STAND_TORQUE_LIMIT)
        except Exception:
            pass
        with d._lock:
            d.armed = True
            d.mode = "stand"
            d.gait.stop()
            if stand is not None:
                d._last_pose = list(stand)
            d.status = "standing"

