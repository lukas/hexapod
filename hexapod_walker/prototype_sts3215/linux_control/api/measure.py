"""BenchAPI route group: measurement routes (walk/hold/quad-pitch/touchdown/axis-geometry/slip) + telemetry.

Moved verbatim from bench_api.py (2026-08-29 component-boundaries split);
mixed into ``bench_api.BenchAPI``. Route/JSON shapes are unchanged.
"""
from __future__ import annotations

from .common import *  # noqa: F401,F403


class MeasureApi:
    def _meas_dir(self) -> Path:
        from event_log import log_dir
        return log_dir()

    def _meas_file(self) -> Path:
        return self._meas_dir() / "measurements.jsonl"

    def _meas_finalize(self, rec: dict) -> dict:
        rec["saved_unix"] = round(time.time(), 3)
        with self._lock:
            self._meas_pending = None
        with self._meas_file().open("a") as f:
            f.write(json.dumps(rec) + "\n")
        try:
            from event_log import emit
            emit("measurement", rec.get("kind", "?"), src="bench",
                 data={k: rec[k] for k in ("kind", "stamp") if k in rec})
        except Exception:
            pass
        return {"ok": True, "record": rec}

    def measure_list(self, n: int = 20) -> dict:
        """Recent saved measurements + the pending (unannotated) one."""
        recs: list[dict] = []
        try:
            lines = self._meas_file().read_text().strip().splitlines()
            for ln in lines[-int(n):]:
                try:
                    recs.append(json.loads(ln))
                except ValueError:
                    pass
        except OSError:
            pass
        with self._lock:
            pending = dict(self._meas_pending) if getattr(
                self, "_meas_pending", None) else None
        return {"ok": True, "records": list(reversed(recs)),
                "pending": pending,
                "fetch": ("HTTP: GET /api/logs (list) + "
                          "/api/logs/<name> (download); or scp "
                          "arduino@hexapod.local:hexapod_sts/"
                          "linux_control/logs/{measurements.jsonl,"
                          "meas_*.csv} rl_move/hardware_traces/")}

    def _meas_telemetry(self, stamp: str, seconds: float,
                        stop_early=None) -> dict:
        """Sample rl_feedback at ~3 Hz for `seconds` into CSVs.

        Returns aggregates (per-joint mean current, bus totals, tilt
        peaks). `stop_early()` (optional) ends the loop; a tilt beyond
        MEAS_TILT_STOP_DEG sets aggregate["tilt_alert"] and ends it too.
        """
        import csv as _csv

        servo_csv = self._meas_dir() / f"meas_{stamp}_servo.csv"
        imu_csv = self._meas_dir() / f"meas_{stamp}_imu.csv"
        agg: dict = {"servo_csv": servo_csv.name, "imu_csv": imu_csv.name,
                     "samples": 0, "tilt_alert": False,
                     "per_joint_mean_a": None, "bus_a_mean": None,
                     "bus_a_max": None, "max_abs_roll_deg": 0.0,
                     "max_abs_pitch_deg": 0.0}
        sums = [0.0] * N_JOINTS
        counts = [0] * N_JOINTS
        totals: list[float] = []
        hdr = ["t_unix", "live"]
        for j in range(N_JOINTS):
            hdr += [f"q{j}_deg", f"cur{j}_a", f"temp{j}_c"]
        t_end = time.monotonic() + seconds
        with servo_csv.open("w", newline="") as fs, \
                imu_csv.open("w", newline="") as fi:
            ws = _csv.writer(fs)
            ws.writerow(hdr)
            wi = _csv.writer(fi)
            wi.writerow(["t_unix", "roll_deg", "pitch_deg",
                         "gx_dps", "gy_dps", "gz_dps"])
            while time.monotonic() < t_end:
                if self._demo_abort.is_set():
                    break
                if stop_early is not None and stop_early():
                    break
                t0 = time.monotonic()
                fb = self.rl_feedback()
                if fb.get("ok"):
                    t = fb.get("t_unix")
                    joints = fb.get("joints") or []
                    row: list = [t, fb.get("live", 0)]
                    total = 0.0
                    for j in range(N_JOINTS):
                        m = (joints[j]
                             if j < len(joints) and joints[j] else None)
                        if m is None:
                            row += ["", "", ""]
                            continue
                        cur = abs(float(m.get("cur_a", 0.0) or 0.0))
                        sums[j] += cur
                        counts[j] += 1
                        total += cur
                        row += [m.get("deg", ""), m.get("cur_a", ""),
                                m.get("temp_c", "")]
                    ws.writerow(row)
                    fs.flush()
                    totals.append(total)
                    agg["samples"] += 1
                    roll, pitch = fb.get("roll_deg"), fb.get("pitch_deg")
                    if roll is not None and pitch is not None:
                        g = fb.get("gyro_dps") or ["", "", ""]
                        wi.writerow([t, roll, pitch, *g])
                        fi.flush()
                        agg["max_abs_roll_deg"] = max(
                            agg["max_abs_roll_deg"], abs(float(roll)))
                        agg["max_abs_pitch_deg"] = max(
                            agg["max_abs_pitch_deg"], abs(float(pitch)))
                        if (abs(float(roll)) > self.MEAS_TILT_STOP_DEG or
                                abs(float(pitch)) > self.MEAS_TILT_STOP_DEG):
                            agg["tilt_alert"] = True
                            break
                time.sleep(max(0.0, self.MEAS_POLL_S
                               - (time.monotonic() - t0)))
        if totals:
            agg["bus_a_mean"] = round(sum(totals) / len(totals), 3)
            agg["bus_a_max"] = round(max(totals), 3)
        agg["per_joint_mean_a"] = [
            round(sums[j] / counts[j], 3) if counts[j] else None
            for j in range(N_JOINTS)]
        agg["max_abs_roll_deg"] = round(agg["max_abs_roll_deg"], 1)
        agg["max_abs_pitch_deg"] = round(agg["max_abs_pitch_deg"], 1)
        return agg

    def measure_walk(self, *, vx_mm: float = 30.0, vy_mm: float = 0.0,
                     omega: float = 0.0, duration_s: float = 20.0) -> dict:
        """Scripted-gait measured run (tape distance / turn sign).

        Drives the tripod gait (`J vx vy omega`) for duration_s while
        logging telemetry, then stops to a planted stand (torque stays
        on) and leaves a PENDING record — enter the tape reading via
        measure_annotate. Same caps as tape_measure_walk.py. If the
        robot is not already ARMED + STANDING the worker ACQUIRES the
        stand first (08-11 directive: safe zero → step stand-up);
        acquisition failure stops everything and the walk never runs.
        MOTION: operator must be watching.
        """
        d = self.drive
        if d.dry_run or not d.bus:
            return {"ok": False, "error": "no bus"}
        if self._demo_thread and self._demo_thread.is_alive():
            return {"ok": False, "error": "stop the running job first"}
        with self._lock:
            if getattr(self, "_meas_pending", None):
                return {"ok": False,
                        "error": "pending measurement — save or discard "
                                 "it first"}
        vx = max(-self.MEAS_MAX_VX_MM, min(self.MEAS_MAX_VX_MM,
                                           float(vx_mm)))
        vy = max(-self.MEAS_MAX_VY_MM, min(self.MEAS_MAX_VY_MM,
                                           float(vy_mm)))
        om = max(-self.MEAS_MAX_OMEGA, min(self.MEAS_MAX_OMEGA,
                                           float(omega)))
        secs = min(max(float(duration_s), 3.0), self.MEAS_MAX_WALK_S)
        stamp = time.strftime("%Y%m%d_%H%M%S")

        self._demo_gen += 1
        gen = self._demo_gen
        self._demo_abort.clear()
        label = (f"measure walk vx={vx:.0f} vy={vy:.0f} "
                 f"w={om:+.2f} {secs:.0f}s")
        with self._lock:
            self._demo_name = "measure_walk"
            self._demo_status = label
            self._demo_params = {"vx_mm": vx, "vy_mm": vy, "omega": om,
                                 "duration_s": secs}
            self._cal_result = None
            self._cal_progress = {"msg": label}
        self._set_activity("measure", label)

        def _worker():
            import math as _math
            rec: dict = {
                "kind": "turn_sign" if (om and not vx and not vy)
                        else "walk_tape",
                "stamp": stamp,
                "vx_mm_s": vx, "vy_mm_s": vy, "omega_rad_s": om,
                "planned_s": secs,
                "cmd_smoothing_note": ("gait vel low-pass tau=0.15s; "
                                       "commanded path ~|v|*0.15s "
                                       "shorter than |v|*T"),
            }
            try:
                self._bus_hot_begin()
                # Acquire ARM + planted stand when missing (08-11):
                # safe zero → validated step stand-up → stand hold.
                need_stand = True
                try:
                    from feetech_bus import standing_pose_degrees
                    w_st, _ = self._delta_vs_present(
                        standing_pose_degrees())
                    need_stand = w_st is None or w_st > 30.0
                except Exception:
                    need_stand = True
                if need_stand or not d.armed:
                    if need_stand:
                        with self._lock:
                            self._demo_status = (
                                "acquiring stand before walk…")
                        res_a = self._acquire_start("stand", gen=gen)
                        if gen != self._demo_gen:
                            return
                        if not res_a.get("ok"):
                            with self._lock:
                                self._cal_result = {
                                    "ok": False,
                                    "error": (
                                        "start pose not reached — "
                                        + str(res_a.get("error")
                                              or "aborted"))}
                                self._demo_status = (
                                    self._cal_result["error"])
                            return
                    self._enter_stand_hold()
                    time.sleep(0.5)
                    with self._lock:
                        self._demo_status = label
                r = d.handle(f"J {vx:.1f} {vy:.1f} {om:.3f}")
                if r != "J":
                    with self._lock:
                        self._cal_result = {"ok": False,
                                            "error": f"J refused: {r}"}
                        self._demo_status = f"refused: {r}"
                    return
                t0 = time.monotonic()
                agg = self._meas_telemetry(stamp, secs)
                walked = time.monotonic() - t0
                d.handle("J 0 0 0")   # planted stand, torque stays on
                time.sleep(1.0)
                speed = _math.hypot(vx, vy)
                rec.update(
                    walked_s=round(walked, 2),
                    commanded_mm=round(speed * walked, 1),
                    commanded_rot_deg=round(
                        _math.degrees(om * walked), 1),
                    stopped=("tilt_alert" if agg["tilt_alert"] else
                             "abort" if self._demo_abort.is_set()
                             else "duration"),
                    **agg)
                if gen != self._demo_gen:
                    return
                with self._lock:
                    self._meas_pending = rec
                    self._cal_result = {"ok": True, "pending": True,
                                        **rec}
                    self._demo_status = (
                        f"walked {walked:.1f}s (commanded "
                        f"~{rec['commanded_mm']:.0f} mm) — read the "
                        "tape and save in the Measure tab")
                    self._cal_progress = {"msg": self._demo_status}
            except Exception as e:
                d.handle("J 0 0 0")
                if gen != self._demo_gen:
                    return
                with self._lock:
                    self._cal_result = {"ok": False, "error": str(e)}
                    self._demo_status = f"error: {e}"
            finally:
                self._bus_hot_end()
                if gen == self._demo_gen:
                    with self._lock:
                        st = self._demo_status
                    self._set_activity(
                        "armed" if d.armed else "limp", st)

        self._demo_thread = threading.Thread(target=_worker, daemon=True)
        self._demo_thread.start()
        return {"ok": True, "stamp": stamp, "duration_s": secs}

    def measure_hold(self, *, label: str = "planted",
                     duration_s: float = 30.0) -> dict:
        """Static holding-current measurement (NO commanded motion).

        Torques on and HOLDS the PRESENT pose (never yanks), then logs
        per-servo currents for duration_s and saves the record
        immediately. Run once with the feet planted ("planted") and
        once with the robot propped so the feet hang free ("hover") —
        the delta is the load-dependent current the sim's effort
        pricing is missing.
        """
        d = self.drive
        if d.dry_run or not d.bus:
            return {"ok": False, "error": "no bus"}
        if self._demo_thread and self._demo_thread.is_alive():
            return {"ok": False, "error": "stop the running job first"}
        label = str(label or "planted").strip().lower()
        if label not in ("planted", "hover"):
            return {"ok": False,
                    "error": "label must be 'planted' or 'hover'"}
        secs = min(max(float(duration_s), 5.0), self.MEAS_MAX_HOLD_S)
        stamp = time.strftime("%Y%m%d_%H%M%S")

        self._demo_gen += 1
        gen = self._demo_gen
        self._demo_abort.clear()
        title = f"measure hold ({label}) {secs:.0f}s"
        with self._lock:
            self._demo_name = "measure_hold"
            self._demo_status = title
            self._demo_params = {"label": label, "duration_s": secs}
            self._cal_result = None
            self._cal_progress = {"msg": title}
        self._set_activity("measure", title)

        def _worker():
            rec: dict = {"kind": "hold_current", "label": label,
                         "stamp": stamp, "planned_s": secs}
            try:
                self._bus_hot_begin()
                # Hold the PRESENT pose: same never-yank arm sequence
                # the RL runner uses.
                with d._lock:
                    d.mode = "demo"
                    d.gait.stop()
                    if not d.armed:
                        d._torque_all(True)
                        d.armed = True
                    d._hold_here()
                time.sleep(0.5)   # let currents settle after torque-on
                agg = self._meas_telemetry(stamp, secs)
                rec.update(**agg)
                if gen != self._demo_gen:
                    return
                out = self._meas_finalize(rec)
                with self._lock:
                    self._cal_result = out
                    self._demo_status = (
                        f"{label} hold: bus mean "
                        f"{agg['bus_a_mean'] or '?'} A over "
                        f"{agg['samples']} samples — saved")
                    self._cal_progress = {"msg": self._demo_status}
            except Exception as e:
                if gen != self._demo_gen:
                    return
                with self._lock:
                    self._cal_result = {"ok": False, "error": str(e)}
                    self._demo_status = f"error: {e}"
            finally:
                self._bus_hot_end()
                if gen == self._demo_gen:
                    with d._lock:
                        if d.mode == "demo":
                            d.mode = "idle"
                    with self._lock:
                        st = self._demo_status
                    self._set_activity(
                        "armed" if d.armed else "limp", st)

        self._demo_thread = threading.Thread(target=_worker, daemon=True)
        self._demo_thread.start()
        return {"ok": True, "stamp": stamp, "label": label,
                "duration_s": secs}

    def measure_quad_pitch(
            self, *, pitches=None, gait: str = "rear_safe",
            settle_s: float = 1.0, roll_guard_deg: float = 6.0,
            current_guard_a: float = 2.0) -> dict:
        """Four-support quad pitch sweep with calibrated IMU feedback.

        This is a small live sign/authority test: acquire the safer
        tuck-stand start, keep the same four support feet, command a list
        of body pitch angles, and record the adjusted IMU pitch/roll plus
        currents after each settle. Quad IK uses negative body pitch for
        rear-up, while adjusted IMU body pitch should become
        more negative when the physical body leans the intended way.
        """
        d = self.drive
        if d.dry_run or not d.bus:
            return {"ok": False, "error": "no bus"}
        if self._demo_thread and self._demo_thread.is_alive():
            return {"ok": False, "error": "stop the running job first"}
        try:
            targets = [float(x) for x in (pitches or
                       [0.0, -4.0, -8.0, -12.0, -16.0, -20.0])]
        except (TypeError, ValueError):
            return {"ok": False, "error": "pitches must be numbers"}
        targets = [max(-32.0, min(4.0, x)) for x in targets[:12]]
        if not targets:
            return {"ok": False, "error": "no pitch targets"}
        settle = max(0.4, min(3.0, float(settle_s)))
        roll_guard = max(3.0, min(18.0, float(roll_guard_deg)))
        current_guard = max(0.8, min(4.0, float(current_guard_a)))
        stamp = time.strftime("%Y%m%d_%H%M%S")

        self._demo_gen += 1
        gen = self._demo_gen
        self._demo_abort.clear()
        title = ("quad pitch sweep "
                 + " ".join(f"{p:+.0f}" for p in targets) + "deg")
        with self._lock:
            self._demo_name = "measure_quad_pitch"
            self._demo_status = title
            self._demo_params = {
                "pitches_deg": targets,
                "gait": gait,
                "settle_s": settle,
                "roll_guard_deg": roll_guard,
                "current_guard_a": current_guard,
            }
            self._cal_result = None
            self._cal_progress = {"msg": title}
        self._set_activity("measure", title)

        def _imu_snapshot(bus) -> dict:
            imu = None
            try:
                imu = bus.read_imu(apply_calib=True)
            except TypeError:
                try:
                    imu = bus.read_imu()
                except Exception:
                    imu = None
            except Exception:
                imu = None
            if not isinstance(imu, dict):
                return {"ok": False}
            out = {"ok": True}
            for k in ("roll_deg", "pitch_deg", "body_roll_deg",
                      "body_pitch_deg", "body_pitch_target_deg",
                      "body_frame_calibrated"):
                if k not in imu:
                    continue
                v = imu.get(k)
                out[k] = round(float(v), 3) if isinstance(v, (int, float)) else v
            return out

        def _worker():
            rec: dict = {
                "kind": "quad_pitch_sweep",
                "stamp": stamp,
                "gait": gait,
                "targets_deg": targets,
                "samples": [],
            }
            try:
                self._bus_hot_begin()
                with self._lock:
                    self._demo_status = "quad pitch: acquiring tuck stand"
                    self._cal_progress = {"msg": self._demo_status}
                res_a = self._acquire_start("stand_tuck", gen=gen)
                if gen != self._demo_gen:
                    return
                if not res_a.get("ok"):
                    with self._lock:
                        self._cal_result = {
                            "ok": False,
                            "error": ("start pose not reached — "
                                      + str(res_a.get("error")
                                            or "aborted")),
                        }
                        self._demo_status = self._cal_result["error"]
                    return

                from inplace_demos import (
                    CurrentPeakTracker, _enable_torque, _hold_here,
                    _live_robot_ids, _read_pose, _set_torque_limit,
                    ease_to_pose, _stand_zero_pose)
                from hexapod_core.quad_walk import FRONT_LEGS, TUCK_DEG, QuadRearWalk

                live = _live_robot_ids(d.bus)
                if len(live) < N_JOINTS:
                    with self._lock:
                        self._cal_result = {
                            "ok": False,
                            "error": f"only {len(live)}/18 servos live",
                        }
                        self._demo_status = self._cal_result["error"]
                    return
                with d._lock:
                    d.mode = "demo"
                    d.gait.stop()
                    if not d.armed:
                        d._torque_all(True)
                        d.armed = True
                _enable_torque(d.bus, live)
                _set_torque_limit(d.bus, live, 850)

                base = _stand_zero_pose()
                quad = QuadRearWalk(base, max(30.0, len(targets) * 2.0),
                                    gait=gait)
                front = list(base)
                for leg in FRONT_LEGS:
                    front[3 * leg: 3 * leg + 3] = TUCK_DEG
                feet = quad._support_feet(press=quad.rear_press)

                def pose_for(pitch_deg: float) -> list[float]:
                    return quad._solve(
                        quad.body_dx, 0.0, math.radians(pitch_deg),
                        feet, front, bz=quad.body_z)

                tracker = CurrentPeakTracker()
                last_good = None
                aborted = None
                for idx, pitch_deg in enumerate(targets):
                    if self._demo_abort.is_set():
                        aborted = "aborted"
                        break
                    with self._lock:
                        self._demo_status = (
                            f"quad pitch target {pitch_deg:+.0f}deg")
                        self._cal_progress = {"msg": self._demo_status}
                    goal = pose_for(pitch_deg)
                    ok = ease_to_pose(
                        d.bus, goal,
                        abort_check=self._demo_abort.is_set,
                        seconds=1.8 if idx == 0 else 1.1,
                        label=f"quad pitch {pitch_deg:+.0f}",
                        current_tracker=tracker)
                    time.sleep(settle)
                    tracker.sample(d.bus, live)
                    imu = _imu_snapshot(d.bus)
                    present = _read_pose(d.bus, live)
                    total_a = 0.0
                    for fb in tracker.last_fb:
                        total_a += abs(float(fb.get("current_a", 0.0)))
                    sample = {
                        "cmd_pitch_deg": round(pitch_deg, 2),
                        "imu": imu,
                        "peak_a": round(float(tracker.peak_a), 3),
                        "peak_joint": tracker.peak_joint,
                        "bus_a": round(total_a, 3),
                        "pose_deg": [round(float(x), 2) for x in present],
                    }
                    rec["samples"].append(sample)
                    last_good = sample
                    body_roll = imu.get("body_roll_deg", imu.get("roll_deg"))
                    if not ok:
                        aborted = "motion aborted"
                        break
                    if body_roll is not None and abs(float(body_roll)) > roll_guard:
                        aborted = f"roll guard {body_roll:+.1f}deg"
                        break
                    if tracker.peak_a > current_guard:
                        aborted = f"current guard {tracker.peak_a:.2f}A"
                        break

                _hold_here(d.bus, live)
                rec["ok"] = aborted is None
                rec["aborted"] = aborted
                rec["last"] = last_good
                out = self._meas_finalize(rec)
                with self._lock:
                    self._cal_result = out
                    if aborted:
                        self._demo_status = f"quad pitch stopped: {aborted}"
                    else:
                        self._demo_status = "quad pitch sweep done; holding"
                    self._cal_progress = {"msg": self._demo_status}
            except Exception as e:
                try:
                    from inplace_demos import _hold_here, _live_robot_ids
                    _hold_here(d.bus, _live_robot_ids(d.bus))
                except Exception:
                    pass
                if gen != self._demo_gen:
                    return
                with self._lock:
                    self._cal_result = {"ok": False, "error": str(e)}
                    self._demo_status = f"error: {e}"
            finally:
                self._bus_hot_end()
                if gen == self._demo_gen:
                    with d._lock:
                        if d.mode == "demo":
                            d.mode = "idle"
                    with self._lock:
                        st = self._demo_status
                    self._set_activity(
                        "armed" if d.armed else "limp", st)

        self._demo_thread = threading.Thread(target=_worker, daemon=True)
        self._demo_thread.start()
        return {"ok": True, "stamp": stamp, "targets_deg": targets}

    def measure_touchdown_zero(
            self, *, zero_tip_clearance_mm=None, femur_mm=None,
            tibia_mm=None, boot_diameter_mm=None, legs=None, axes=None,
            torque=None, settle_s=None, save=True,
            extra_accurate=False, show_straight_after=False,
            simultaneous=False) -> dict:
        """Tap requested legs down and save software zero hints.

        This does not call ``set_zero_here`` or rewrite servo EEPROM centers.
        It records where low-torque contact starts relative to measured
        geometry and saves encoder-frame errors for later review/application.
        """
        d = self.drive
        if d.dry_run or not d.bus:
            return {"ok": False, "error": "no bus"}
        if self._demo_thread and self._demo_thread.is_alive():
            return {"ok": False, "error": "stop the running job first"}
        try:
            from touchdown_zero import (
                analysis_dict, analyze_touch_rows, expected_dicts,
                expected_touch_angles, make_sweep_angles,
                fit_zero_tip_height_from_contacts,
                make_refine_sweep_angles,
                merge_repeat_analyses,
            )
        except ImportError as e:
            return {"ok": False, "error": f"touchdown_zero missing: {e}"}

        manual = self.manual_geometry_state()
        height = self._maybe_float(zero_tip_clearance_mm)
        if height is None:
            height = self._maybe_float(manual.get("hip_pitch_height_mm"))
        femur = self._maybe_float(femur_mm)
        if femur is None:
            femur = self._maybe_float(manual.get("femur_mm")) or 90.0
        tibia = self._maybe_float(tibia_mm)
        if tibia is None:
            tibia = self._maybe_float(manual.get("tibia_mm")) or 150.0
        boot = self._maybe_float(boot_diameter_mm)
        if height is None:
            return {
                "ok": False,
                "error": (
                    "zero_tip_clearance_mm is required unless manual "
                    "hip_pitch_height_mm is saved"),
                "manual": manual,
            }
        try:
            expected = expected_touch_angles(
                zero_tip_clearance_mm=height,
                femur_mm=femur,
                tibia_mm=tibia,
                boot_diameter_mm=boot)
        except (TypeError, ValueError) as e:
            return {"ok": False, "error": str(e)}

        def parse_legs(val) -> list[int]:
            if val is None:
                return list(range(6))
            raw = val
            if isinstance(val, str):
                raw = [x for x in val.replace(",", " ").split() if x]
            if not isinstance(raw, (list, tuple, set)):
                raw = [raw]
            out: list[int] = []
            for item in raw:
                try:
                    leg = int(item)
                except (TypeError, ValueError):
                    raise ValueError(f"bad leg {item!r}")
                if not 0 <= leg < 6:
                    raise ValueError(f"leg must be 0..5, got {leg}")
                if leg not in out:
                    out.append(leg)
            return out

        def parse_axes(val) -> list[str]:
            if val is None:
                return ["hip", "knee"]
            raw = val
            if isinstance(val, str):
                raw = [x for x in val.replace(",", " ").split() if x]
            if not isinstance(raw, (list, tuple, set)):
                raw = [raw]
            out: list[str] = []
            for item in raw:
                axis = str(item).strip().lower()
                if axis not in ("hip", "knee"):
                    raise ValueError(f"axis must be hip or knee, got {item!r}")
                if axis not in out:
                    out.append(axis)
            return out

        def truthy(val, default: bool = True) -> bool:
            if val is None:
                return default
            if isinstance(val, str):
                return val.strip().lower() in ("1", "true", "yes", "on")
            return bool(val)

        try:
            leg_list = parse_legs(legs)
            axis_list = parse_axes(axes)
            torque_i = 220 if torque is None else int(round(float(torque)))
            torque_i = max(150, min(520, torque_i))
            settle = 0.42 if settle_s is None else float(settle_s)
            settle = max(0.18, min(1.5, settle))
            save_result = truthy(save, True)
            extra_accurate_result = truthy(extra_accurate, False)
            show_straight_after_result = truthy(show_straight_after, False)
            simultaneous_result = truthy(
                simultaneous,
                show_straight_after_result and len(leg_list) > 1)
        except (TypeError, ValueError) as e:
            return {"ok": False, "error": str(e)}
        if not leg_list or not axis_list:
            return {"ok": False, "error": "no legs/axes requested"}

        stamp = time.strftime("%Y%m%d_%H%M%S")
        self._demo_gen += 1
        gen = self._demo_gen
        self._demo_abort.clear()
        with self._lock:
            self._demo_name = "measure_touchdown_zero"
            self._demo_status = "touchdown zero"
            self._demo_params = {
                "zero_tip_clearance_mm": height,
                "femur_mm": femur,
                "tibia_mm": tibia,
                "boot_diameter_mm": boot,
                "legs": leg_list,
                "axes": axis_list,
                "torque": torque_i,
                "save": save_result,
                "extra_accurate": bool(extra_accurate_result),
                "show_straight_after": bool(show_straight_after_result),
                "simultaneous": bool(simultaneous_result),
            }
            self._cal_result = None
            self._cal_progress = {"msg": "touchdown zero"}
        self._set_activity("measure", "touchdown zero")

        def _worker():
            result: dict = {"ok": False, "mode": "touchdown_zero"}
            live: set[int] = set()
            hold_after_success = False
            rec: dict = {
                "kind": "touchdown_zero",
                "stamp": stamp,
                "input_measurements": {
                    "zero_tip_clearance_mm": round(float(height), 3),
                    "femur_mm": round(float(femur), 3),
                    "tibia_mm": round(float(tibia), 3),
                    "boot_diameter_mm": (
                        None if boot is None else round(float(boot), 3)),
                },
                "requested": {"legs": leg_list, "axes": axis_list},
                "torque": torque_i,
                "settle_s": round(settle, 3),
                "refine_mode": (
                    "always" if extra_accurate_result else "auto"),
                "show_straight_after": bool(show_straight_after_result),
                "sweep_mode": (
                    "simultaneous" if simultaneous_result else "serial"),
                "expected": expected_dicts(expected),
                "samples": [],
                "per_leg": [],
                "notes": [
                    "Low-torque touchdown zero hints only; servo logical "
                    "zero is not rewritten.",
                    "encoder_zero_error_deg = observed_touch_deg - "
                    "expected_touch_deg.",
                    "Approx physical angle ~= encoder_deg - "
                    "encoder_zero_error_deg; command compensation adds the "
                    "same error to a desired physical angle.",
                ],
            }

            def progress(msg: str, **extra) -> None:
                with self._lock:
                    self._cal_progress = {
                        "msg": msg,
                        "mode": "touchdown_zero",
                        **extra,
                    }
                    self._demo_status = msg

            def zero_pose() -> list[float]:
                return [0.0] * N_JOINTS

            def pose_for(leg: int, axis: str, angle: float) -> list[float]:
                q = zero_pose()
                j = int(leg) * 3
                if axis == "hip":
                    q[j + 1] = float(angle)
                elif axis == "knee":
                    q[j + 2] = float(angle)
                return q

            def pose_for_axis_targets(
                    axis: str, targets: dict[int, float]) -> list[float]:
                q = zero_pose()
                offset = 1 if axis == "hip" else 2
                for leg, angle in targets.items():
                    q[int(leg) * 3 + offset] = float(angle)
                return q

            def fb_float(row: dict, key: str) -> float:
                try:
                    return float(row.get(key) or 0.0)
                except (TypeError, ValueError):
                    return 0.0

            def sample_row_from_feedback(
                    fb: dict[int, dict], leg: int, axis: str,
                    cmd_deg: float, baseline: dict[int, dict]) -> dict:
                jh = int(leg) * 3 + 1
                jk = int(leg) * 3 + 2
                rh = fb.get(jh) or {}
                rk = fb.get(jk) or {}
                bh = baseline.get(jh) or {}
                bk = baseline.get(jk) or {}
                hdeg = self._maybe_float(rh.get("deg"))
                kdeg = self._maybe_float(rk.get("deg"))
                hcur = abs(fb_float(rh, "current_a"))
                kcur = abs(fb_float(rk, "current_a"))
                hload = fb_float(rh, "load_pct")
                kload = fb_float(rk, "load_pct")
                hcur0 = abs(fb_float(bh, "current_a"))
                kcur0 = abs(fb_float(bk, "current_a"))
                hload0 = fb_float(bh, "load_pct")
                kload0 = fb_float(bk, "load_pct")
                encoder = hdeg if axis == "hip" else kdeg
                current_delta = max(0.0, hcur - hcur0, kcur - kcur0)
                load_delta = max(0.0, hload - hload0, kload - kload0)
                return {
                    "leg": int(leg),
                    "axis": axis,
                    "cmd_deg": round(float(cmd_deg), 2),
                    "encoder_deg": (
                        None if encoder is None else round(encoder, 2)),
                    "hip_deg": None if hdeg is None else round(hdeg, 2),
                    "knee_deg": None if kdeg is None else round(kdeg, 2),
                    "hip_current_a": round(hcur, 3),
                    "knee_current_a": round(kcur, 3),
                    "hip_load_pct": round(hload, 1),
                    "knee_load_pct": round(kload, 1),
                    "current_delta_a": round(current_delta, 3),
                    "load_delta_pct": round(load_delta, 1),
                }

            def sample_row(leg: int, axis: str, cmd_deg: float,
                           baseline: dict[int, dict]) -> dict:
                fb = self._read_feedback_map(d.bus)
                return sample_row_from_feedback(
                    fb, leg, axis, cmd_deg, baseline)

            try:
                from feetech_bus import AXIS_LIMITS_DEG
                from inplace_demos import (
                    CurrentPeakTracker, _enable_torque, _limp_all,
                    _live_robot_ids, _set_torque_limit, _write_pose,
                    ease_to_pose,
                )
            except ImportError as e:
                result = {"ok": False, "mode": "touchdown_zero",
                          "error": str(e)}
            else:
                guard_error = None
                contact_count = 0
                requested_count = len(leg_list) * len(axis_list)
                reset_torque_i = min(650, max(520, torque_i))
                zero_tolerance_deg = 2.5
                repeat_tolerance_deg = 3.0
                local_repeat_tolerance_deg = 2.0
                local_refine_trigger_deg = 6.0
                leg_rows: dict[int, dict] = {
                    int(leg): {"leg": int(leg)} for leg in leg_list
                }

                def leg_zero_snapshot(leg: int) -> dict:
                    fb = self._read_feedback_map(d.bus)
                    j = int(leg) * 3
                    rh = fb.get(j + 1) or {}
                    rk = fb.get(j + 2) or {}
                    hdeg = self._maybe_float(rh.get("deg"))
                    kdeg = self._maybe_float(rk.get("deg"))
                    vals = [abs(v) for v in (hdeg, kdeg) if v is not None]
                    return {
                        "hip_deg": None if hdeg is None else round(hdeg, 2),
                        "knee_deg": None if kdeg is None else round(kdeg, 2),
                        "max_abs_deg": (
                            None if not vals else round(max(vals), 2)),
                    }

                def leg_axis_snapshot(
                        leg: int, axis: str,
                        target_cmd_deg: float | None = None) -> dict:
                    fb = self._read_feedback_map(d.bus)
                    j = int(leg) * 3
                    rh = fb.get(j + 1) or {}
                    rk = fb.get(j + 2) or {}
                    hdeg = self._maybe_float(rh.get("deg"))
                    kdeg = self._maybe_float(rk.get("deg"))
                    axis_deg = hdeg if axis == "hip" else kdeg
                    out = {
                        "hip_deg": None if hdeg is None else round(hdeg, 2),
                        "knee_deg": None if kdeg is None else round(kdeg, 2),
                        "axis_deg": (
                            None if axis_deg is None else round(axis_deg, 2)),
                    }
                    if target_cmd_deg is not None and axis_deg is not None:
                        out["target_cmd_deg"] = round(float(target_cmd_deg), 2)
                        out["target_error_deg"] = round(
                            axis_deg - float(target_cmd_deg), 2)
                    return out

                def settle_leg_zero(
                        leg: int, axis: str, label: str
                ) -> tuple[bool, dict[int, dict], dict]:
                    initial = leg_zero_snapshot(leg)
                    initial_err = float(initial.get("max_abs_deg") or 0.0)
                    timeout_s = max(3.5, min(8.0, 1.2 + initial_err / 9.0))
                    zrec = {
                        "leg": int(leg),
                        "axis": axis,
                        "label": label,
                        "torque": reset_torque_i,
                        "tolerance_deg": zero_tolerance_deg,
                        "timeout_s": round(timeout_s, 2),
                        "initial": initial,
                        "samples": [],
                    }
                    progress(
                        f"touchdown zero: L{leg} {axis} settle zero",
                        leg=leg, axis=axis)
                    _set_torque_limit(d.bus, live, reset_torque_i)
                    start = time.monotonic()
                    deadline = start + timeout_s
                    next_write = 0.0
                    ok = False
                    last = {}
                    while time.monotonic() < deadline:
                        if self._demo_abort.is_set():
                            break
                        now = time.monotonic()
                        if now >= next_write:
                            _write_pose(
                                d.bus, zero_pose(), live, speed=180, acc=18)
                            next_write = now + 0.35
                        time.sleep(0.16)
                        snap = leg_zero_snapshot(leg)
                        snap["t_s"] = round(time.monotonic() - start, 2)
                        zrec["samples"].append(snap)
                        last = snap
                        err = snap.get("max_abs_deg")
                        if err is not None and float(err) <= zero_tolerance_deg:
                            ok = True
                            break
                    zrec["ok"] = bool(ok)
                    if last:
                        zrec["final"] = last
                    _set_torque_limit(d.bus, live, torque_i)
                    time.sleep(0.12)
                    return ok, self._read_feedback_map(d.bus), zrec

                def settle_leg_near(
                        leg: int, axis: str, label: str,
                        target_cmd_deg: float, *,
                        axis_limits: tuple[float, float],
                        min_axis_deg: float | None = None,
                        max_axis_deg: float | None = None
                ) -> tuple[bool, dict[int, dict], dict]:
                    lo, hi = axis_limits
                    base_target = max(
                        float(lo), min(float(hi), float(target_cmd_deg)))
                    nrec = {
                        "leg": int(leg),
                        "axis": axis,
                        "label": label,
                        "target_cmd_deg": round(float(base_target), 2),
                        "min_axis_deg": (
                            None if min_axis_deg is None
                            else round(float(min_axis_deg), 2)),
                        "max_axis_deg": (
                            None if max_axis_deg is None
                            else round(float(max_axis_deg), 2)),
                        "position_tolerance_deg": 3.0,
                        "torque": torque_i,
                        "samples": [],
                        "attempts": [],
                    }
                    last = {}
                    ok = False
                    extra_backoff = 0.0
                    for attempt_i in range(1, 5):
                        target = max(
                            float(lo),
                            min(float(hi), base_target - extra_backoff))
                        arec = {
                            "attempt": attempt_i,
                            "target_cmd_deg": round(float(target), 2),
                            "samples": [],
                        }
                        progress(
                            f"touchdown zero: L{leg} {axis} near lift-off",
                            leg=leg, axis=axis, angle_deg=target,
                            attempt=attempt_i)
                        _set_torque_limit(d.bus, live, torque_i)
                        start = time.monotonic()
                        deadline = start + 1.25
                        next_write = 0.0
                        while time.monotonic() < deadline:
                            if self._demo_abort.is_set():
                                break
                            now = time.monotonic()
                            if now >= next_write:
                                _write_pose(
                                    d.bus,
                                    pose_for(leg, axis, target),
                                    live,
                                    speed=120,
                                    acc=12)
                                next_write = now + 0.26
                            time.sleep(0.14)
                            snap = leg_axis_snapshot(leg, axis, target)
                            snap["t_s"] = round(time.monotonic() - start, 2)
                            snap["attempt"] = attempt_i
                            arec["samples"].append(snap)
                            nrec["samples"].append(snap)
                            last = snap
                        axis_deg = self._maybe_float(last.get("axis_deg"))
                        target_error = (
                            None if axis_deg is None
                            else abs(axis_deg - float(target)))
                        positioned = (
                            axis_deg is not None
                            and (
                                min_axis_deg is None
                                or axis_deg >= float(min_axis_deg)
                                or (
                                    target_error is not None
                                    and target_error <= 3.0)))
                        unloaded = (
                            axis_deg is not None
                            and (
                                max_axis_deg is None
                                or axis_deg <= float(max_axis_deg)))
                        arec["ok"] = bool(
                            positioned
                            and unloaded
                            and not self._demo_abort.is_set())
                        arec["positioned"] = bool(positioned)
                        arec["unloaded"] = bool(unloaded)
                        if last:
                            arec["final"] = last
                        nrec["attempts"].append(arec)
                        if arec["ok"]:
                            ok = True
                            break
                        if self._demo_abort.is_set():
                            break
                        if (axis_deg is not None
                                and max_axis_deg is not None
                                and axis_deg > float(max_axis_deg)):
                            extra_backoff += 4.0
                    nrec["ok"] = bool(ok)
                    if last:
                        nrec["final"] = last
                        axis_deg = self._maybe_float(last.get("axis_deg"))
                        final_target = self._maybe_float(
                            last.get("target_cmd_deg"))
                        target_error = (
                            None if axis_deg is None or final_target is None
                            else abs(axis_deg - final_target))
                        nrec["positioned"] = bool(
                            axis_deg is not None
                            and (
                                min_axis_deg is None
                                or axis_deg >= float(min_axis_deg)
                                or (
                                    target_error is not None
                                    and target_error <= 3.0)))
                        nrec["unloaded"] = bool(
                            axis_deg is not None
                            and (
                                max_axis_deg is None
                                or axis_deg <= float(max_axis_deg)))
                    time.sleep(0.08)
                    return ok, self._read_feedback_map(d.bus), nrec

                def leg_zero_snapshot_many(legs: list[int]) -> dict:
                    fb = self._read_feedback_map(d.bus)
                    per_leg: dict[str, dict] = {}
                    max_vals: list[float] = []
                    for leg in legs:
                        j = int(leg) * 3
                        rh = fb.get(j + 1) or {}
                        rk = fb.get(j + 2) or {}
                        hdeg = self._maybe_float(rh.get("deg"))
                        kdeg = self._maybe_float(rk.get("deg"))
                        vals = [
                            abs(v) for v in (hdeg, kdeg)
                            if v is not None
                        ]
                        if vals:
                            max_vals.append(max(vals))
                        per_leg[str(int(leg))] = {
                            "hip_deg": (
                                None if hdeg is None else round(hdeg, 2)),
                            "knee_deg": (
                                None if kdeg is None else round(kdeg, 2)),
                            "max_abs_deg": (
                                None if not vals
                                else round(max(vals), 2)),
                        }
                    return {
                        "per_leg": per_leg,
                        "max_abs_deg": (
                            None if not max_vals
                            else round(max(max_vals), 2)),
                    }

                def settle_legs_zero(
                        legs: list[int], axis: str, label: str
                ) -> tuple[bool, dict[int, dict], dict]:
                    leg_ints = [int(leg) for leg in legs]
                    initial = leg_zero_snapshot_many(leg_ints)
                    initial_err = float(initial.get("max_abs_deg") or 0.0)
                    timeout_s = max(3.5, min(8.0, 1.2 + initial_err / 9.0))
                    zrec = {
                        "legs": leg_ints,
                        "axis": axis,
                        "label": label,
                        "torque": reset_torque_i,
                        "tolerance_deg": zero_tolerance_deg,
                        "timeout_s": round(timeout_s, 2),
                        "initial": initial,
                        "samples": [],
                        "mode": "simultaneous",
                    }
                    progress(
                        f"touchdown zero: all {axis} settle zero",
                        axis=axis, legs=leg_ints)
                    _set_torque_limit(d.bus, live, reset_torque_i)
                    start = time.monotonic()
                    deadline = start + timeout_s
                    next_write = 0.0
                    ok = False
                    last = {}
                    while time.monotonic() < deadline:
                        if self._demo_abort.is_set():
                            break
                        now = time.monotonic()
                        if now >= next_write:
                            _write_pose(
                                d.bus, zero_pose(), live, speed=180, acc=18)
                            next_write = now + 0.35
                        time.sleep(0.16)
                        snap = leg_zero_snapshot_many(leg_ints)
                        snap["t_s"] = round(time.monotonic() - start, 2)
                        zrec["samples"].append(snap)
                        last = snap
                        err = snap.get("max_abs_deg")
                        if err is not None and float(err) <= zero_tolerance_deg:
                            ok = True
                            break
                    zrec["ok"] = bool(ok)
                    if last:
                        zrec["final"] = last
                    _set_torque_limit(d.bus, live, torque_i)
                    time.sleep(0.12)
                    return ok, self._read_feedback_map(d.bus), zrec

                def settle_legs_near(
                        legs: list[int], axis: str, label: str,
                        target_by_leg: dict[int, float], *,
                        axis_limits: tuple[float, float],
                        min_by_leg: dict[int, float],
                        max_by_leg: dict[int, float]
                ) -> tuple[bool, dict[int, dict], dict]:
                    leg_ints = [int(leg) for leg in legs]
                    lo, hi = axis_limits
                    targets = {
                        int(leg): max(
                            float(lo),
                            min(float(hi), float(target_by_leg[int(leg)])))
                        for leg in leg_ints
                    }
                    nrec = {
                        "legs": leg_ints,
                        "axis": axis,
                        "label": label,
                        "target_cmd_deg": {
                            str(leg): round(float(targets[leg]), 2)
                            for leg in leg_ints
                        },
                        "min_axis_deg": {
                            str(leg): round(float(min_by_leg[leg]), 2)
                            for leg in leg_ints
                        },
                        "max_axis_deg": {
                            str(leg): round(float(max_by_leg[leg]), 2)
                            for leg in leg_ints
                        },
                        "position_tolerance_deg": 3.0,
                        "torque": torque_i,
                        "samples": [],
                        "attempts": [],
                        "mode": "simultaneous",
                    }
                    last_by_leg: dict[int, dict] = {}
                    ok = False
                    for attempt_i in range(1, 6):
                        progress(
                            f"touchdown zero: all {axis} near lift-off",
                            axis=axis, attempt=attempt_i,
                            legs=leg_ints)
                        _set_torque_limit(d.bus, live, torque_i)
                        start = time.monotonic()
                        deadline = start + 1.35
                        next_write = 0.0
                        arec = {
                            "attempt": attempt_i,
                            "targets": {
                                str(leg): round(float(targets[leg]), 2)
                                for leg in leg_ints
                            },
                            "samples": [],
                        }
                        while time.monotonic() < deadline:
                            if self._demo_abort.is_set():
                                break
                            now = time.monotonic()
                            if now >= next_write:
                                _write_pose(
                                    d.bus,
                                    pose_for_axis_targets(axis, targets),
                                    live,
                                    speed=120,
                                    acc=12)
                                next_write = now + 0.26
                            time.sleep(0.14)
                            fb = self._read_feedback_map(d.bus)
                            snap = {
                                "t_s": round(time.monotonic() - start, 2),
                                "attempt": attempt_i,
                                "per_leg": {},
                            }
                            for leg in leg_ints:
                                j = int(leg) * 3
                                rh = fb.get(j + 1) or {}
                                rk = fb.get(j + 2) or {}
                                hdeg = self._maybe_float(rh.get("deg"))
                                kdeg = self._maybe_float(rk.get("deg"))
                                axis_deg = hdeg if axis == "hip" else kdeg
                                row = {
                                    "hip_deg": (
                                        None if hdeg is None
                                        else round(hdeg, 2)),
                                    "knee_deg": (
                                        None if kdeg is None
                                        else round(kdeg, 2)),
                                    "axis_deg": (
                                        None if axis_deg is None
                                        else round(axis_deg, 2)),
                                    "target_cmd_deg": round(
                                        float(targets[leg]), 2),
                                }
                                if axis_deg is not None:
                                    row["target_error_deg"] = round(
                                        axis_deg - float(targets[leg]), 2)
                                snap["per_leg"][str(leg)] = row
                                last_by_leg[leg] = row
                            arec["samples"].append(snap)
                            nrec["samples"].append(snap)
                        per_leg_status: dict[str, dict] = {}
                        all_ok = not self._demo_abort.is_set()
                        for leg in leg_ints:
                            last = last_by_leg.get(leg) or {}
                            axis_deg = self._maybe_float(last.get("axis_deg"))
                            target = targets[leg]
                            target_error = (
                                None if axis_deg is None
                                else abs(axis_deg - float(target)))
                            positioned = (
                                axis_deg is not None
                                and (
                                    axis_deg >= float(min_by_leg[leg])
                                    or (
                                        target_error is not None
                                        and target_error <= 3.0)))
                            unloaded = (
                                axis_deg is not None
                                and axis_deg <= float(max_by_leg[leg]))
                            leg_ok = bool(
                                positioned and unloaded
                                and not self._demo_abort.is_set())
                            all_ok = all_ok and leg_ok
                            per_leg_status[str(leg)] = {
                                "ok": leg_ok,
                                "positioned": bool(positioned),
                                "unloaded": bool(unloaded),
                                "final": last,
                            }
                            if not leg_ok and axis_deg is not None:
                                if axis_deg > float(max_by_leg[leg]):
                                    targets[leg] = max(
                                        float(lo), targets[leg] - 4.0)
                        arec["per_leg_status"] = per_leg_status
                        arec["ok"] = bool(all_ok)
                        nrec["attempts"].append(arec)
                        if all_ok:
                            ok = True
                            break
                        if self._demo_abort.is_set():
                            break
                    nrec["ok"] = bool(ok)
                    nrec["final_by_leg"] = {
                        str(leg): last_by_leg.get(leg, {})
                        for leg in leg_ints
                    }
                    if nrec["attempts"]:
                        nrec["final_status"] = (
                            nrec["attempts"][-1].get("per_leg_status", {}))
                    time.sleep(0.08)
                    return ok, self._read_feedback_map(d.bus), nrec

                def run_touch_repeat_many(
                        legs: list[int], axis: str, exp: float,
                        axis_limits: tuple[float, float], repeat_i: int, *,
                        refine_center_cmd: dict[int, float] | None = None,
                        refine_center_observed: (
                            dict[int, float | None] | None) = None
                ) -> tuple[dict[int, dict], str | None]:
                    leg_ints = [int(leg) for leg in legs]
                    stop_error = None
                    refine = refine_center_cmd is not None
                    rows_by_leg: dict[int, list[dict]] = {
                        leg: [] for leg in leg_ints
                    }
                    analyses: dict[int, object] = {}
                    sweep_by_leg: dict[int, list[float]] = {}
                    center_obs_by_leg: dict[int, float] = {}
                    if refine:
                        refine_backoff_deg = (
                            12.0 if axis == "knee" else 8.0)
                        for leg in leg_ints:
                            center_cmd = float(
                                refine_center_cmd.get(leg, exp))
                            sweep = make_refine_sweep_angles(
                                center_cmd,
                                backoff_deg=refine_backoff_deg,
                                limit=axis_limits)
                            if not sweep:
                                return {
                                    leg: {
                                        "ok": False,
                                        "axis": axis,
                                        "status": "bad_refine_sweep",
                                        "expected_touch_deg": exp,
                                        "repeat": repeat_i,
                                        "samples": 0,
                                        "note": (
                                            "local refine sweep is empty"),
                                    }
                                    for leg in leg_ints
                                }, "bad_refine_sweep"
                            sweep_by_leg[leg] = sweep
                            obs = (
                                None if refine_center_observed is None
                                else refine_center_observed.get(leg))
                            center_obs_by_leg[leg] = (
                                exp if obs is None else float(obs))
                        unload_margin_deg = (
                            4.0 if axis == "knee" else 3.0)
                        near_ok, baseline, near_rec = settle_legs_near(
                            leg_ints,
                            axis,
                            f"repeat_{repeat_i}_near",
                            {leg: sweep_by_leg[leg][0]
                             for leg in leg_ints},
                            axis_limits=axis_limits,
                            min_by_leg={
                                leg: max(
                                    float(axis_limits[0]),
                                    float(sweep_by_leg[leg][0]) - 3.0)
                                for leg in leg_ints
                            },
                            max_by_leg={
                                leg: center_obs_by_leg[leg]
                                - unload_margin_deg
                                for leg in leg_ints
                            })
                        rec.setdefault("near_settles", []).append(near_rec)
                        if not near_ok:
                            return {
                                leg: {
                                    "ok": False,
                                    "axis": axis,
                                    "status": "near_settle_failed",
                                    "expected_touch_deg": exp,
                                    "repeat": repeat_i,
                                    "samples": 0,
                                    "note": (
                                        f"all {axis} near lift-off failed"),
                                    "near_settle": near_rec,
                                }
                                for leg in leg_ints
                            }, "near_settle_failed"
                        angle_i_by_leg = {leg: 0 for leg in leg_ints}
                    else:
                        zero_ok, baseline, zero_rec = settle_legs_zero(
                            leg_ints, axis, f"repeat_{repeat_i}_pre")
                        rec.setdefault("zero_settles", []).append(zero_rec)
                        if not zero_ok:
                            return {
                                leg: {
                                    "ok": False,
                                    "axis": axis,
                                    "status": "zero_settle_failed",
                                    "expected_touch_deg": exp,
                                    "repeat": repeat_i,
                                    "samples": 0,
                                    "note": (
                                        f"all {axis} zero settle failed"),
                                    "zero_settle": zero_rec,
                                }
                                for leg in leg_ints
                            }, "zero_settle_failed"
                        search_overrun_deg = (
                            14.0 if axis == "hip" else 22.0)
                        common_sweep = make_sweep_angles(
                            exp,
                            overrun_deg=search_overrun_deg,
                            limit=axis_limits)
                        sweep_by_leg = {
                            leg: list(common_sweep) for leg in leg_ints
                        }
                        center_obs_by_leg = {
                            leg: float(exp) for leg in leg_ints
                        }
                        angle_i_by_leg = {leg: 0 for leg in leg_ints}
                    last_angle_by_leg = {
                        leg: (sweep_by_leg[leg][0]
                              if sweep_by_leg[leg] else 0.0)
                        for leg in leg_ints
                    }
                    hold_cmd_by_leg: dict[int, float] = {}
                    done: set[int] = set()
                    completed_hold_backoff_deg = (
                        4.0 if axis == "knee" else 3.0)
                    no_contact_hold_backoff_deg = (
                        8.0 if axis == "knee" else 6.0)
                    no_contact_overrun_deg = (
                        14.0 if axis == "hip" else 22.0)
                    encoder_done_by_leg = {
                        leg: min(
                            float(axis_limits[1]),
                            max(float(exp) + 5.0,
                                center_obs_by_leg[leg] + 4.0)
                            if refine else float(exp) + no_contact_overrun_deg)
                        for leg in leg_ints
                    }
                    touch_kwargs = {"expected_touch_deg": exp}
                    if refine:
                        touch_kwargs.update({
                            "weak_current_delta_a": 0.008,
                            "weak_load_delta_pct": 1.9,
                        })
                    max_samples = (
                        18 if refine and axis == "hip"
                        else 24 if refine
                        else 24 if axis == "hip"
                        else 32)
                    while len(done) < len(leg_ints):
                        if self._demo_abort.is_set():
                            stop_error = "aborted"
                            break
                        if any(
                                len(rows_by_leg[leg]) >= max_samples
                                for leg in leg_ints
                                if leg not in done):
                            break
                        active = [leg for leg in leg_ints if leg not in done]
                        cmd_by_leg: dict[int, float] = {}
                        for leg in leg_ints:
                            if leg in done:
                                cmd_by_leg[leg] = hold_cmd_by_leg.get(
                                    leg, last_angle_by_leg[leg])
                                continue
                            sweep = sweep_by_leg[leg]
                            idx = angle_i_by_leg[leg]
                            if idx < len(sweep):
                                angle = sweep[idx]
                                angle_i_by_leg[leg] = idx + 1
                                last_angle_by_leg[leg] = angle
                            else:
                                angle = last_angle_by_leg[leg]
                            cmd_by_leg[leg] = float(angle)
                        active_angles = [cmd_by_leg[leg] for leg in active]
                        if active_angles:
                            angle_msg = (
                                f"{active_angles[0]:+.1f} deg"
                                if (max(active_angles)
                                    - min(active_angles) < 0.05)
                                else (
                                    f"{min(active_angles):+.1f}"
                                    f"..{max(active_angles):+.1f} deg"))
                        else:
                            angle_msg = ""
                        progress(
                            f"touchdown zero: all {axis} "
                            f"{'local tap' if refine else 'tap'} "
                            f"{repeat_i} {angle_msg}",
                            axis=axis,
                            repeat=repeat_i,
                            active=len(active),
                            total=len(leg_ints))
                        _write_pose(
                            d.bus,
                            pose_for_axis_targets(axis, cmd_by_leg),
                            live,
                            speed=72,
                            acc=8)
                        time.sleep(settle)
                        fb = self._read_feedback_map(d.bus)
                        for leg in active:
                            row = sample_row_from_feedback(
                                fb, leg, axis, cmd_by_leg[leg], baseline)
                            row["repeat"] = repeat_i
                            row["simultaneous"] = True
                            if refine:
                                row["mode"] = "local_refine"
                            rows_by_leg[leg].append(row)
                            rec["samples"].append(row)
                            max_cur = max(
                                float(row.get("hip_current_a") or 0.0),
                                float(row.get("knee_current_a") or 0.0))
                            max_load = max(
                                float(row.get("hip_load_pct") or 0.0),
                                float(row.get("knee_load_pct") or 0.0))
                            if max_cur >= 0.75:
                                stop_error = (
                                    f"L{leg} {axis} current guard "
                                    f"{max_cur:.2f}A")
                                break
                            if max_load >= 45.0:
                                stop_error = (
                                    f"L{leg} {axis} load guard "
                                    f"{max_load:.0f}%")
                                break
                            analysis = analyze_touch_rows(
                                axis, rows_by_leg[leg], **touch_kwargs)
                            analyses[leg] = analysis
                            if analysis.ok:
                                done.add(leg)
                                observed_axis = self._maybe_float(
                                    getattr(
                                        analysis, "observed_touch_deg", None))
                                if observed_axis is None:
                                    observed_axis = self._maybe_float(
                                        row.get("encoder_deg"))
                                if observed_axis is None:
                                    observed_axis = float(row["cmd_deg"])
                                hold_cmd_by_leg[leg] = max(
                                    float(axis_limits[0]),
                                    observed_axis - completed_hold_backoff_deg)
                                continue
                            max_encoder = analysis.max_encoder_deg
                            if (max_encoder is not None
                                    and max_encoder
                                    >= encoder_done_by_leg[leg]):
                                done.add(leg)
                                observed_axis = self._maybe_float(
                                    row.get("encoder_deg"))
                                if observed_axis is None:
                                    observed_axis = float(row["cmd_deg"])
                                hold_cmd_by_leg[leg] = max(
                                    float(axis_limits[0]),
                                    float(observed_axis)
                                    - no_contact_hold_backoff_deg)
                        if stop_error:
                            break
                    reps: dict[int, dict] = {}
                    for leg in leg_ints:
                        analysis = analyses.get(leg)
                        if analysis is None:
                            analysis = analyze_touch_rows(
                                axis, rows_by_leg[leg], **touch_kwargs)
                        rep = analysis_dict(analysis)
                        rep["repeat"] = repeat_i
                        rep["simultaneous"] = True
                        if refine:
                            rep["mode"] = "local_refine"
                            rep["refine_center_cmd_deg"] = round(
                                float(refine_center_cmd.get(leg, exp)), 3)
                            rep["refine_center_observed_deg"] = round(
                                float(center_obs_by_leg[leg]), 3)
                            rep["detection"] = touch_kwargs
                        rep["planned_sweep_deg"] = sweep_by_leg[leg]
                        rep["sweep_deg"] = [
                            r.get("cmd_deg") for r in rows_by_leg[leg]
                        ]
                        rep["encoder_done_deg"] = round(
                            encoder_done_by_leg[leg], 3)
                        rep["max_samples"] = max_samples
                        rep["completed_hold_backoff_deg"] = (
                            completed_hold_backoff_deg)
                        rep["no_contact_hold_backoff_deg"] = (
                            no_contact_hold_backoff_deg)
                        rep["completed_hold_reference"] = "encoder_deg"
                        reps[leg] = rep

                    if not refine and not self._demo_abort.is_set():
                        post_ok, _baseline, post_rec = settle_legs_zero(
                            leg_ints, axis, f"repeat_{repeat_i}_post")
                        rec.setdefault("zero_settles", []).append(post_rec)
                        for rep in reps.values():
                            rep["post_zero_settle"] = post_rec
                        if not post_ok and stop_error is None:
                            stop_error = (
                                f"all {axis} post-zero settle failed")
                    return reps, stop_error

                def run_touch_repeat(
                        leg: int, axis: str, exp: float,
                        axis_limits: tuple[float, float], repeat_i: int, *,
                        refine_center_cmd: float | None = None,
                        refine_center_observed: float | None = None
                ) -> tuple[dict, str | None]:
                    stop_error = None
                    refine = refine_center_cmd is not None
                    if refine:
                        refine_backoff_deg = (
                            12.0 if axis == "knee" else 8.0)
                        sweep = make_refine_sweep_angles(
                            float(refine_center_cmd),
                            backoff_deg=refine_backoff_deg,
                            limit=axis_limits)
                        if not sweep:
                            return {
                                "ok": False,
                                "axis": axis,
                                "status": "bad_refine_sweep",
                                "expected_touch_deg": exp,
                                "repeat": repeat_i,
                                "samples": 0,
                                "note": "local refine sweep is empty",
                            }, "bad_refine_sweep"
                        center_observed = (
                            exp if refine_center_observed is None
                            else float(refine_center_observed))
                        unload_margin_deg = (
                            4.0 if axis == "knee" else 3.0)
                        min_axis_deg = max(
                            float(axis_limits[0]), float(sweep[0]) - 3.0)
                        max_axis_deg = center_observed - unload_margin_deg
                        near_ok, baseline, near_rec = settle_leg_near(
                            leg, axis, f"repeat_{repeat_i}_near",
                            sweep[0],
                            axis_limits=axis_limits,
                            min_axis_deg=min_axis_deg,
                            max_axis_deg=max_axis_deg)
                        rec.setdefault("near_settles", []).append(near_rec)
                        if not near_ok:
                            final = near_rec.get("final") or {}
                            return {
                                "ok": False,
                                "axis": axis,
                                "status": "near_settle_failed",
                                "expected_touch_deg": exp,
                                "repeat": repeat_i,
                                "samples": 0,
                                "note": (
                                    f"L{leg} {axis} near lift-off failed "
                                    f"hip={final.get('hip_deg')} "
                                    f"knee={final.get('knee_deg')} "
                                    f"min={near_rec.get('min_axis_deg')} "
                                    f"limit={near_rec.get('max_axis_deg')}"),
                                "near_settle": near_rec,
                            }, "near_settle_failed"
                        angle_i = 0
                    else:
                        zero_ok, baseline, zero_rec = settle_leg_zero(
                            leg, axis, f"repeat_{repeat_i}_pre")
                        rec.setdefault("zero_settles", []).append(zero_rec)
                        if not zero_ok:
                            final = zero_rec.get("final") or {}
                            return {
                                "ok": False,
                                "axis": axis,
                                "status": "zero_settle_failed",
                                "expected_touch_deg": exp,
                                "repeat": repeat_i,
                                "samples": 0,
                                "note": (
                                    f"L{leg} {axis} zero settle failed "
                                    f"hip={final.get('hip_deg')} "
                                    f"knee={final.get('knee_deg')}"),
                                "zero_settle": zero_rec,
                            }, "zero_settle_failed"
                        search_overrun_deg = (
                            14.0 if axis == "hip" else 22.0)
                        sweep = make_sweep_angles(
                            exp,
                            overrun_deg=search_overrun_deg,
                            limit=axis_limits)
                        angle_i = 0
                    rows: list[dict] = []
                    analysis = None
                    last_angle = sweep[0] if sweep else 0.0
                    center_observed = (
                        exp if refine_center_observed is None
                        else float(refine_center_observed))
                    encoder_done = min(
                        float(axis_limits[1]),
                        max(exp + 5.0, center_observed + 4.0)
                        if refine else exp + search_overrun_deg)
                    touch_kwargs = {
                        "expected_touch_deg": exp,
                    }
                    if refine:
                        touch_kwargs.update({
                            "weak_current_delta_a": 0.008,
                            "weak_load_delta_pct": 1.9,
                        })
                    max_samples = (
                        18 if refine and axis == "hip"
                        else 24 if refine
                        else 24 if axis == "hip"
                        else 32)
                    while len(rows) < max_samples:
                        if self._demo_abort.is_set():
                            stop_error = "aborted"
                            break
                        if angle_i < len(sweep):
                            angle = sweep[angle_i]
                            angle_i += 1
                            last_angle = angle
                        else:
                            angle = last_angle
                        progress(
                            f"touchdown zero: L{leg} {axis} "
                            f"{'local tap' if refine else 'tap'} "
                            f"{repeat_i} {angle:+.1f} deg",
                            leg=leg, axis=axis, repeat=repeat_i,
                            angle_deg=angle)
                        _write_pose(
                            d.bus, pose_for(leg, axis, angle),
                            live, speed=72, acc=8)
                        time.sleep(settle)
                        row = sample_row(leg, axis, angle, baseline)
                        row["repeat"] = repeat_i
                        if refine:
                            row["mode"] = "local_refine"
                        rows.append(row)
                        rec["samples"].append(row)
                        max_cur = max(
                            float(row.get("hip_current_a") or 0.0),
                            float(row.get("knee_current_a") or 0.0))
                        max_load = max(
                            float(row.get("hip_load_pct") or 0.0),
                            float(row.get("knee_load_pct") or 0.0))
                        if max_cur >= 0.75:
                            stop_error = (
                                f"L{leg} {axis} current guard "
                                f"{max_cur:.2f}A")
                            break
                        if max_load >= 45.0:
                            stop_error = (
                                f"L{leg} {axis} load guard {max_load:.0f}%")
                            break
                        analysis = analyze_touch_rows(
                            axis, rows, **touch_kwargs)
                        if analysis.ok:
                            break
                        max_encoder = analysis.max_encoder_deg
                        if (max_encoder is not None
                                and max_encoder >= encoder_done):
                            break
                    if analysis is None:
                        analysis = analyze_touch_rows(
                            axis, rows, **touch_kwargs)
                    rep = analysis_dict(analysis)
                    rep["repeat"] = repeat_i
                    if refine:
                        rep["mode"] = "local_refine"
                        rep["refine_center_cmd_deg"] = round(
                            float(refine_center_cmd), 3)
                        rep["refine_center_observed_deg"] = round(
                            float(center_observed), 3)
                    rep["planned_sweep_deg"] = sweep
                    rep["sweep_deg"] = [r.get("cmd_deg") for r in rows]
                    rep["encoder_done_deg"] = round(encoder_done, 3)
                    rep["max_samples"] = max_samples
                    if refine:
                        rep["detection"] = touch_kwargs

                    if not refine and not self._demo_abort.is_set():
                        post_ok, _baseline, post_rec = settle_leg_zero(
                            leg, axis, f"repeat_{repeat_i}_post")
                        rec.setdefault("zero_settles", []).append(post_rec)
                        rep["post_zero_settle"] = post_rec
                        if not post_ok and stop_error is None:
                            final = post_rec.get("final") or {}
                            stop_error = (
                                f"L{leg} {axis} post-zero settle failed "
                                f"hip={final.get('hip_deg')} "
                                f"knee={final.get('knee_deg')}")
                    return rep, stop_error

                def contact_values(
                        reps: list[dict], key: str) -> list[float]:
                    vals: list[float] = []
                    for rep in reps:
                        if not rep.get("ok") or rep.get(key) is None:
                            continue
                        try:
                            vals.append(float(rep[key]))
                        except (TypeError, ValueError):
                            pass
                    return vals

                def median_value(vals: list[float]) -> float | None:
                    if not vals:
                        return None
                    ordered = sorted(vals)
                    mid = len(ordered) // 2
                    if len(ordered) % 2:
                        return ordered[mid]
                    return 0.5 * (ordered[mid - 1] + ordered[mid])

                def refine_center_command(
                        center_cmd: float | None,
                        center_obs: float | None
                ) -> tuple[float | None, str]:
                    if center_obs is None:
                        return center_cmd, "observed_cmd_deg"
                    if (center_cmd is None
                            or abs(float(center_cmd)
                                   - float(center_obs)) > 4.0):
                        return float(center_obs), "observed_touch_deg"
                    return float(center_cmd), "observed_cmd_deg"

                def refine_center_observation(
                        reps: list[dict]) -> tuple[float | None, str]:
                    contacts: list[tuple[float, int, int, str]] = []
                    strength_score = {"weak": 1, "edge": 2, "firm": 3}
                    for idx, rep in enumerate(reps):
                        if not rep.get("ok"):
                            continue
                        obs = self._maybe_float(rep.get("observed_touch_deg"))
                        if obs is None:
                            continue
                        strength = str(rep.get("contact_strength") or "weak")
                        score = strength_score.get(strength, 1)
                        contacts.append((float(obs), score, idx, strength))
                    if not contacts:
                        return None, "none"
                    vals = [c[0] for c in contacts]
                    spread = max(vals) - min(vals)
                    if spread > local_refine_trigger_deg:
                        obs, _score, _idx, strength = max(
                            contacts, key=lambda c: c[0])
                        return float(obs), f"upper_{strength}"
                    return median_value(vals), "median_observed_touch_deg"

                def should_refine(merged: dict) -> bool:
                    if merged.get("status") != "repeat_mismatch":
                        return False
                    spread = self._maybe_float(merged.get("repeat_spread_deg"))
                    return (
                        spread is not None
                        and repeat_tolerance_deg < spread)

                def straight_pose_from_record() -> tuple[
                        list[float], list[dict], list[str]]:
                    q = zero_pose()
                    targets: list[dict] = []
                    missing: list[str] = []
                    requested_axes = set(axis_list)
                    for row in rec.get("per_leg") or []:
                        try:
                            leg_i = int(row.get("leg"))
                        except (TypeError, ValueError):
                            continue
                        for axis, offset in (("hip", 1), ("knee", 2)):
                            if axis not in requested_axes:
                                continue
                            hint = row.get(axis)
                            comp = None
                            if isinstance(hint, dict) and hint.get("ok"):
                                comp = self._maybe_float(
                                    hint.get("command_compensation_deg"))
                                if comp is None:
                                    comp = self._maybe_float(
                                        hint.get("encoder_zero_error_deg"))
                            if comp is None:
                                missing.append(f"L{leg_i} {axis}")
                                continue
                            if abs(float(comp)) > 20.0:
                                missing.append(
                                    f"L{leg_i} {axis} large "
                                    f"{float(comp):+.1f}°")
                                continue
                            joint = leg_i * 3 + offset
                            q[joint] = float(comp)
                            targets.append({
                                "leg": leg_i,
                                "axis": axis,
                                "joint": joint,
                                "target_deg": round(float(comp), 3),
                                "source_strength": (
                                    hint.get("contact_strength")
                                    if isinstance(hint, dict) else None),
                            })
                    return q, targets, missing

                def run_axis_simultaneous(
                        axis: str) -> tuple[str | None, int]:
                    axis_index = 1 if axis == "hip" else 2
                    exp = expected[axis].expected_touch_deg
                    axis_limits = AXIS_LIMITS_DEG[axis_index]
                    repeat_results_by_leg: dict[int, list[dict]] = {
                        int(leg): [] for leg in leg_list
                    }
                    axis_results: dict[int, dict] = {}
                    for repeat_i in (1, 2):
                        reps_by_leg, stop_error = run_touch_repeat_many(
                            [int(leg) for leg in leg_list],
                            axis,
                            exp,
                            axis_limits,
                            repeat_i)
                        for leg, rep in reps_by_leg.items():
                            repeat_results_by_leg[int(leg)].append(rep)
                        if stop_error:
                            return stop_error, 0

                    initial_results: dict[int, dict] = {}
                    for leg in leg_list:
                        leg_i = int(leg)
                        initial_results[leg_i] = merge_repeat_analyses(
                            axis,
                            repeat_results_by_leg[leg_i],
                            expected_touch_deg=exp,
                            repeat_tolerance_deg=repeat_tolerance_deg)
                        axis_results[leg_i] = initial_results[leg_i]

                    refine_legs: list[int] = []
                    for leg in leg_list:
                        leg_i = int(leg)
                        reps = repeat_results_by_leg[leg_i]
                        force_refine = (
                            bool(extra_accurate_result)
                            and len(contact_values(
                                reps, "observed_touch_deg")) >= 2
                            and bool(contact_values(
                                reps, "observed_cmd_deg")))
                        if should_refine(axis_results[leg_i]) or force_refine:
                            refine_legs.append(leg_i)

                    refinement_by_leg: dict[int, dict] = {}
                    local_results_by_leg: dict[int, list[dict]] = {
                        leg: [] for leg in refine_legs
                    }
                    used_local_by_leg: dict[int, bool] = {
                        leg: False for leg in refine_legs
                    }
                    center_cmd_by_leg: dict[int, float] = {}
                    center_obs_by_leg: dict[int, float | None] = {}
                    for leg in refine_legs:
                        reps = repeat_results_by_leg[leg]
                        center_cmd = median_value(
                            contact_values(reps, "observed_cmd_deg"))
                        center_obs, center_obs_source = (
                            refine_center_observation(reps))
                        center_cmd, center_source = refine_center_command(
                            center_cmd, center_obs)
                        if center_cmd is None:
                            continue
                        center_cmd_by_leg[leg] = float(center_cmd)
                        center_obs_by_leg[leg] = center_obs
                        force_refine = bool(extra_accurate_result)
                        refinement_by_leg[leg] = {
                            "mode": "near_contact",
                            "requested_by": (
                                "always" if force_refine else "mismatch"),
                            "trigger_spread_deg": (
                                axis_results[leg].get(
                                    "repeat_spread_deg")),
                            "center_cmd_deg": round(float(center_cmd), 3),
                            "center_cmd_source": center_source,
                            "center_observed_deg": (
                                None if center_obs is None
                                else round(float(center_obs), 3)),
                            "center_observed_source": center_obs_source,
                            "max_local_repeats": 3,
                            "local_repeat_tolerance_deg": (
                                local_repeat_tolerance_deg),
                            "simultaneous": True,
                        }

                    active = [
                        leg for leg in refine_legs
                        if leg in center_cmd_by_leg
                    ]
                    for local_i in range(3):
                        if not active:
                            break
                        repeat_i = 3 + local_i
                        reps_by_leg, stop_error = run_touch_repeat_many(
                            active,
                            axis,
                            exp,
                            axis_limits,
                            repeat_i,
                            refine_center_cmd={
                                leg: center_cmd_by_leg[leg]
                                for leg in active
                            },
                            refine_center_observed={
                                leg: center_obs_by_leg.get(leg)
                                for leg in active
                            })
                        for leg, rep in reps_by_leg.items():
                            repeat_results_by_leg[int(leg)].append(rep)
                            local_results_by_leg[int(leg)].append(rep)
                        if stop_error:
                            return stop_error, 0

                        next_active: list[int] = []
                        for leg in active:
                            locals_for_leg = local_results_by_leg[leg]
                            if len(locals_for_leg) < 2:
                                next_active.append(leg)
                                continue
                            local_merged = merge_repeat_analyses(
                                axis,
                                locals_for_leg,
                                expected_touch_deg=exp,
                                repeat_tolerance_deg=(
                                    local_repeat_tolerance_deg))
                            if local_merged.get("ok"):
                                axis_results[leg] = local_merged
                                used_local_by_leg[leg] = True
                            elif len(locals_for_leg) < 3:
                                next_active.append(leg)
                        active = next_active

                    for leg in refine_legs:
                        locals_for_leg = local_results_by_leg.get(leg, [])
                        refinement = refinement_by_leg.get(leg)
                        if not refinement:
                            continue
                        refinement["local_repeat_count"] = len(
                            locals_for_leg)
                        refinement["used_local_result"] = bool(
                            used_local_by_leg.get(leg, False))
                        refinement["local_observed_deg"] = [
                            r.get("observed_touch_deg")
                            for r in locals_for_leg
                        ]
                        if not axis_results[leg].get("ok"):
                            axis_results[leg] = merge_repeat_analyses(
                                axis,
                                repeat_results_by_leg[leg],
                                expected_touch_deg=exp,
                                repeat_tolerance_deg=repeat_tolerance_deg)
                        axis_results[leg]["refinement"] = refinement
                        if (axis_results[leg].get("ok")
                                and used_local_by_leg.get(leg, False)):
                            axis_results[leg]["note"] = (
                                "near-contact repeat-confirmed touchdown")

                    axis_contacts = 0
                    first_error = None
                    for leg in leg_list:
                        leg_i = int(leg)
                        axis_result = axis_results[leg_i]
                        leg_rows[leg_i][axis] = axis_result
                        if axis_result.get("ok"):
                            axis_contacts += 1
                        elif (first_error is None
                              and axis_result.get("status")
                              == "repeat_mismatch"):
                            first_error = (
                                f"L{leg_i} {axis} touchdown repeats "
                                "disagree")
                        elif first_error is None:
                            first_error = (
                                f"L{leg_i} {axis} "
                                f"{axis_result.get('status') or 'failed'}")
                    return first_error, axis_contacts

                try:
                    self._bus_hot_begin()
                    with d._lock:
                        d.mode = "demo"
                        d.gait.stop()
                    live = _live_robot_ids(d.bus)
                    if len(live) < 12:
                        result = {
                            "ok": False,
                            "mode": "touchdown_zero",
                            "error": f"need more servos (live={len(live)})",
                            "live": sorted(live),
                        }
                    else:
                        progress("touchdown zero: safe zero")
                        zero_start = self._safe_zero_sync(
                            abort_check=self._demo_abort.is_set,
                            on_progress=lambda p: progress(
                                "touchdown zero safe-zero: "
                                + str(p.get("msg") or "running")))
                        rec["zero_start"] = zero_start
                        if (gen != self._demo_gen
                                or self._demo_abort.is_set()
                                or not zero_start.get("ok")):
                            result = {
                                "ok": False,
                                "mode": "touchdown_zero",
                                "aborted": bool(self._demo_abort.is_set()
                                                or zero_start.get("aborted")),
                                "error": (zero_start.get("error")
                                          or "safe zero failed"),
                                "record": rec,
                            }
                        else:
                            _enable_torque(d.bus, live)
                            _set_torque_limit(d.bus, live, torque_i)
                            if simultaneous_result and len(leg_list) > 1:
                                for axis in axis_list:
                                    if (guard_error
                                            or self._demo_abort.is_set()):
                                        break
                                    guard_error, axis_contacts = (
                                        run_axis_simultaneous(axis))
                                    contact_count += axis_contacts
                            for leg in (
                                    [] if (
                                        simultaneous_result
                                        and len(leg_list) > 1)
                                    else leg_list):
                                if guard_error or self._demo_abort.is_set():
                                    break
                                for axis in axis_list:
                                    if (guard_error
                                            or self._demo_abort.is_set()):
                                        break
                                    axis_index = 1 if axis == "hip" else 2
                                    exp = expected[axis].expected_touch_deg
                                    axis_limits = AXIS_LIMITS_DEG[axis_index]
                                    repeat_results: list[dict] = []
                                    for repeat_i in (1, 2, 3):
                                        if repeat_i == 3 and repeat_results:
                                            pending = merge_repeat_analyses(
                                                axis, repeat_results,
                                                expected_touch_deg=exp,
                                                repeat_tolerance_deg=(
                                                    repeat_tolerance_deg))
                                            if (should_refine(pending)
                                                    or (
                                                        extra_accurate_result
                                                        and len(contact_values(
                                                            repeat_results,
                                                            "observed_touch_deg"))
                                                        >= 2)):
                                                break
                                        rep, stop_error = run_touch_repeat(
                                            int(leg), axis, exp, axis_limits,
                                            repeat_i)
                                        repeat_results.append(rep)
                                        if stop_error:
                                            guard_error = (
                                                stop_error if stop_error
                                                != "zero_settle_failed"
                                                else str(rep.get("note")))
                                            break
                                        if len(repeat_results) < 2:
                                            continue
                                        merged = merge_repeat_analyses(
                                            axis, repeat_results,
                                            expected_touch_deg=exp,
                                            repeat_tolerance_deg=(
                                                repeat_tolerance_deg))
                                        if (merged.get("ok")
                                                or should_refine(merged)
                                                or repeat_i == 3):
                                            break
                                    axis_result = merge_repeat_analyses(
                                        axis, repeat_results,
                                        expected_touch_deg=exp,
                                        repeat_tolerance_deg=(
                                            repeat_tolerance_deg))
                                    force_refine = (
                                        bool(extra_accurate_result)
                                        and len(contact_values(
                                            repeat_results,
                                            "observed_touch_deg")) >= 2
                                        and bool(contact_values(
                                            repeat_results,
                                            "observed_cmd_deg")))
                                    if (not guard_error
                                            and (
                                                should_refine(axis_result)
                                                or force_refine)):
                                        trigger_spread = (
                                            axis_result.get(
                                                "repeat_spread_deg"))
                                        center_cmd = median_value(
                                            contact_values(
                                                repeat_results,
                                                "observed_cmd_deg"))
                                        center_obs, center_obs_source = (
                                            refine_center_observation(
                                                repeat_results))
                                        center_cmd, center_source = (
                                            refine_center_command(
                                                center_cmd, center_obs))
                                        local_results: list[dict] = []
                                        used_local_result = False
                                        refinement = {
                                            "mode": "near_contact",
                                            "requested_by": (
                                                "always" if force_refine
                                                else "mismatch"),
                                            "trigger_spread_deg": (
                                                trigger_spread),
                                            "center_cmd_deg": (
                                                None if center_cmd is None
                                                else round(center_cmd, 3)),
                                            "center_cmd_source": (
                                                center_source),
                                            "center_observed_deg": (
                                                None if center_obs is None
                                                else round(center_obs, 3)),
                                            "center_observed_source": (
                                                center_obs_source),
                                            "max_local_repeats": 3,
                                            "local_repeat_tolerance_deg": (
                                                local_repeat_tolerance_deg),
                                        }
                                        if center_cmd is not None:
                                            for _local_i in range(3):
                                                repeat_i = (
                                                    len(repeat_results) + 1)
                                                rep, stop_error = (
                                                    run_touch_repeat(
                                                        int(leg), axis, exp,
                                                        axis_limits, repeat_i,
                                                        refine_center_cmd=(
                                                            center_cmd),
                                                        refine_center_observed=(
                                                            center_obs)))
                                                repeat_results.append(rep)
                                                local_results.append(rep)
                                                if stop_error:
                                                    guard_error = stop_error
                                                    break
                                                if len(local_results) < 2:
                                                    continue
                                                local_merged = (
                                                    merge_repeat_analyses(
                                                        axis, local_results,
                                                        expected_touch_deg=exp,
                                                        repeat_tolerance_deg=(
                                                            local_repeat_tolerance_deg)))
                                                if local_merged.get("ok"):
                                                    axis_result = local_merged
                                                    used_local_result = True
                                                    break
                                        if local_results:
                                            refinement["local_repeat_count"] = (
                                                len(local_results))
                                            refinement["used_local_result"] = (
                                                bool(used_local_result))
                                            refinement["local_observed_deg"] = [
                                                r.get("observed_touch_deg")
                                                for r in local_results
                                            ]
                                            if not axis_result.get("ok"):
                                                axis_result = (
                                                    merge_repeat_analyses(
                                                        axis,
                                                        repeat_results,
                                                        expected_touch_deg=exp,
                                                        repeat_tolerance_deg=(
                                                            repeat_tolerance_deg)))
                                            axis_result["refinement"] = (
                                                refinement)
                                            if (axis_result.get("ok")
                                                    and used_local_result):
                                                axis_result["note"] = (
                                                    "near-contact "
                                                    "repeat-confirmed "
                                                    "touchdown")
                                    leg_rows[int(leg)][axis] = axis_result
                                    if axis_result.get("ok"):
                                        contact_count += 1
                                    elif (not guard_error
                                          and axis_result.get("status")
                                          == "repeat_mismatch"):
                                        guard_error = (
                                            f"L{leg} {axis} touchdown repeats "
                                            "disagree")

                            rec["per_leg"] = [
                                leg_rows[int(leg)] for leg in leg_list
                            ]
                            rec["height_fit"] = (
                                fit_zero_tip_height_from_contacts(
                                    rec["per_leg"],
                                    input_height_mm=float(height),
                                    femur_mm=float(femur),
                                    tibia_mm=float(tibia),
                                    boot_diameter_mm=boot)
                            )
                            complete = (
                                guard_error is None
                                and not self._demo_abort.is_set()
                                and contact_count == requested_count)
                            rec["summary"] = {
                                "requested": requested_count,
                                "contacts": contact_count,
                                "complete": bool(complete),
                                "saved": False,
                                "guard_error": guard_error,
                            }

                            if save_result and complete:
                                payload = {
                                    "timestamp": (
                                        time.strftime("%Y-%m-%dT%H:%M:%S")),
                                    "source": "touchdown_zero",
                                    "learned": True,
                                    "input_measurements": (
                                        rec["input_measurements"]),
                                    "expected": rec["expected"],
                                    "per_leg": rec["per_leg"],
                                    "height_fit": rec.get("height_fit"),
                                    "convention": rec["notes"][1:],
                                    "measurement_stamp": stamp,
                                }
                                path = self._touchdown_zero_path()
                                path.parent.mkdir(parents=True, exist_ok=True)
                                path.write_text(
                                    json.dumps(payload, indent=2) + "\n")
                                rec["summary"]["saved"] = True
                                rec["touchdown_zero_path"] = str(path)

                            straight_after_failed = False
                            if (show_straight_after_result and complete
                                    and not self._demo_abort.is_set()):
                                q_straight, targets, missing = (
                                    straight_pose_from_record())
                                rec["straight_after"] = {
                                    "requested": True,
                                    "ok": False,
                                    "targets": targets,
                                    "missing": missing,
                                }
                                if missing:
                                    straight_after_failed = True
                                    rec["straight_after"]["error"] = (
                                        "missing or unsafe straight targets")
                                else:
                                    progress(
                                        "touchdown zero: show calibrated "
                                        "straight")
                                    tracker = CurrentPeakTracker()
                                    straight_torque_i = max(220, torque_i)
                                    _set_torque_limit(
                                        d.bus, live, straight_torque_i)
                                    _enable_torque(d.bus, live)
                                    ok_hold = ease_to_pose(
                                        d.bus,
                                        q_straight,
                                        abort_check=(
                                            self._demo_abort.is_set),
                                        seconds=2.0,
                                        label=(
                                            "touchdown calibrated straight"),
                                        current_tracker=tracker)
                                    hold_after_success = (
                                        bool(ok_hold)
                                        and not self._demo_abort.is_set())
                                    rec["straight_after"].update({
                                        "ok": bool(hold_after_success),
                                        "seconds": 2.0,
                                        "torque": straight_torque_i,
                                        "peak_a": round(tracker.peak_a, 3),
                                        "peak_joint": tracker.peak_joint,
                                        "goal_deg": [
                                            round(float(x), 3)
                                            for x in q_straight
                                        ],
                                    })
                                    if not hold_after_success:
                                        straight_after_failed = True
                                        rec["straight_after"]["error"] = (
                                            "straight move aborted or failed")
                                rec["summary"]["straight_after"] = bool(
                                    hold_after_success)
                                if straight_after_failed:
                                    rec["summary"][
                                        "straight_after_error"] = (
                                            rec.get("straight_after", {})
                                            .get("error")
                                            or "straight_after_failed")

                            if not hold_after_success:
                                progress("touchdown zero: return zero")
                            if (not hold_after_success
                                    and not self._demo_abort.is_set()):
                                _write_pose(
                                    d.bus, zero_pose(), live,
                                    speed=100, acc=8)
                                time.sleep(0.5)

                            if guard_error or straight_after_failed:
                                finalized = self._meas_finalize(rec)
                                result = {
                                    "ok": False,
                                    "mode": "touchdown_zero",
                                    "recoverable": True,
                                    "guard_stop": bool(
                                        guard_error
                                        and guard_error != "aborted"),
                                    "aborted": guard_error == "aborted",
                                    "error": (
                                        guard_error
                                        or rec.get("straight_after", {})
                                        .get("error")
                                        or "straight_after_failed"),
                                    "record": finalized.get("record", rec),
                                }
                            else:
                                result = self._meas_finalize(rec)
                                result["mode"] = "touchdown_zero"
                except Exception as e:
                    result = {"ok": False, "mode": "touchdown_zero",
                              "error": str(e), "record": rec}
                finally:
                    try:
                        if live and not hold_after_success:
                            _set_torque_limit(d.bus, live, 1000)
                    except Exception:
                        pass
                    try:
                        if live and not hold_after_success:
                            _limp_all(d.bus, live)
                    except Exception:
                        try:
                            if not hold_after_success:
                                d.handle("X")
                        except Exception:
                            pass
                    self._bus_hot_end()

            if gen != self._demo_gen:
                return
            with d._lock:
                if d.mode == "demo":
                    d.mode = "idle"
                d.armed = bool(hold_after_success)
            with self._lock:
                self._cal_result = result
                if result.get("ok"):
                    summ = (result.get("record") or {}).get("summary") or {}
                    self._demo_status = (
                        "done · touchdown zero "
                        f"{summ.get('contacts')}/{summ.get('requested')}"
                        + (" saved" if summ.get("saved") else "")
                        + (" · straight" if summ.get("straight_after")
                           else ""))
                else:
                    self._demo_status = (
                        "error: " + str(result.get("error") or "failed"))
                self._cal_progress = {"msg": self._demo_status}
            self._set_activity(
                "armed" if hold_after_success else "limp",
                self._demo_status)

        self._demo_thread = threading.Thread(target=_worker, daemon=True)
        self._demo_thread.start()
        return {"ok": True, "stamp": stamp, "mode": "touchdown_zero"}

    def measure_axis_geometry(
            self, *, knee_height_mm: float | None = None,
            knee_to_boot_tip_mm: float | None = None,
            boot_diameter_mm: float | None = None) -> dict:
        """Run simple hip/knee isolation sweeps for geometry sanity.

        This is intentionally simpler than the dimension sweep: all yaw joints
        stay at zero, then the robot runs two static families from safe zero:
        hip=0 with increasing knee, and knee=0 with increasing hip.  The output
        records where current/load first rises, which is the practical contact
        envelope for the real boot/footpad rather than a pin-foot FK fantasy.
        MOTION: operator must be watching.
        """
        d = self.drive
        if d.dry_run or not d.bus:
            return {"ok": False, "error": "no bus"}
        if self._demo_thread and self._demo_thread.is_alive():
            return {"ok": False, "error": "stop the running job first"}
        stamp = time.strftime("%Y%m%d_%H%M%S")
        title = "measure axis geometry"

        self._demo_gen += 1
        gen = self._demo_gen
        self._demo_abort.clear()
        with self._lock:
            self._demo_name = "measure_axis_geometry"
            self._demo_status = title
            self._demo_params = {}
            self._cal_result = None
            self._cal_progress = {"msg": title}
        self._set_activity("measure", title)

        def _worker():
            result: dict = {"ok": False, "mode": "axis_geometry"}
            live: set[int] = set()
            rec: dict = {
                "kind": "axis_geometry",
                "stamp": stamp,
                "samples": [],
                "input_measurements": {
                    "knee_height_mm": knee_height_mm,
                    "knee_to_boot_tip_mm": knee_to_boot_tip_mm,
                    "boot_diameter_mm": boot_diameter_mm,
                },
                "notes": [
                    "All yaw joints stay at zero.",
                    "knee_only keeps hip at zero and increases knee.",
                    "hip_only keeps knee at zero and increases hip.",
                    "Contact is inferred from current/load rise; the boot "
                    "makes this a contact envelope, not a pin-foot endpoint.",
                ],
            }

            def progress(msg: str, **extra) -> None:
                with self._lock:
                    self._cal_progress = {
                        "msg": msg,
                        "mode": "axis_geometry",
                        **extra,
                    }
                    self._demo_status = msg

            try:
                from feetech_bus import AXIS_LIMITS_DEG
                from imu_calibrate import imu_tilt_deg
                from inplace_demos import (
                    _enable_torque, _hold_here, _limp_all, _live_robot_ids,
                    _set_torque_limit, _write_pose,
                )
            except ImportError as e:
                result = {"ok": False, "mode": "axis_geometry",
                          "error": str(e)}
            else:
                def clamp_axis(axis: int, value: float) -> float:
                    lo, hi = AXIS_LIMITS_DEG.get(axis, (-180.0, 180.0))
                    return max(float(lo), min(float(hi), float(value)))

                def pose(hip: float, knee: float) -> list[float]:
                    q: list[float] = []
                    h = clamp_axis(1, hip)
                    k = clamp_axis(2, knee)
                    for _leg in range(6):
                        q.extend([0.0, h, k])
                    return q

                def read_tilt() -> tuple[float, float] | None:
                    try:
                        imu = d.bus.read_imu(apply_calib=True)
                    except TypeError:
                        try:
                            imu = d.bus.read_imu()
                        except Exception:
                            imu = None
                    except Exception:
                        imu = None
                    if not isinstance(imu, dict):
                        return None
                    try:
                        tilt = imu_tilt_deg(imu)
                    except Exception:
                        return None
                    if not tilt or tilt[0] is None or tilt[1] is None:
                        return None
                    return float(tilt[0]), float(tilt[1])

                def expected_angles() -> dict:
                    manual = self.manual_geometry_state()
                    h_mm = self._maybe_float(
                        manual.get("hip_pitch_height_mm"))
                    femur = self._maybe_float(manual.get("femur_mm"))
                    tibia = self._maybe_float(manual.get("tibia_mm"))
                    out = {"manual": manual if manual.get("learned") else None}
                    kh = self._maybe_float(knee_height_mm)
                    kt = self._maybe_float(knee_to_boot_tip_mm)
                    boot = self._maybe_float(boot_diameter_mm)
                    try:
                        if kh is not None and kt is not None and 0.0 < kh < kt:
                            out["knee_only_tip_contact_deg"] = round(
                                math.degrees(math.asin(kh / kt)), 2)
                            if boot is not None and boot > 0.0:
                                radius = boot * 0.5
                                center_drop = max(0.0, kh - radius)
                                effective_len = max(1.0, kt - radius)
                                if center_drop < effective_len:
                                    out["knee_only_boot_radius_deg"] = round(
                                        math.degrees(
                                            math.asin(
                                                center_drop / effective_len)),
                                        2)
                                    out["knee_only_boot_formula"] = (
                                        "(tip_mm - boot_radius_mm) * "
                                        "sin(theta) + boot_radius_mm")
                        if h_mm is None or femur is None or tibia is None:
                            return out
                        if 0.0 < h_mm < tibia:
                            out["knee_only_ideal_deg"] = round(
                                math.degrees(math.asin(h_mm / tibia)), 2)
                        if 0.0 < h_mm < (femur + tibia):
                            out["hip_only_ideal_deg"] = round(
                                math.degrees(math.asin(
                                    h_mm / (femur + tibia))), 2)
                    except ValueError:
                        pass
                    return out

                def sample_once(label: str, hip: float, knee: float,
                                baseline: dict[int, dict],
                                base_tilt: tuple[float, float] | None
                                ) -> dict:
                    fb = self._read_feedback_map(d.bus)
                    per_leg = []
                    hip_knee_currents: list[float] = []
                    hip_knee_loads: list[float] = []
                    current_excess = 0.0
                    load_excess = 0.0
                    hip_vals: list[float] = []
                    knee_vals: list[float] = []
                    for leg in range(6):
                        jh = leg * 3 + 1
                        jk = leg * 3 + 2
                        rh = fb.get(jh) or {}
                        rk = fb.get(jk) or {}
                        bh = baseline.get(jh) or {}
                        bk = baseline.get(jk) or {}
                        hcur = abs(float(rh.get("current_a") or 0.0))
                        kcur = abs(float(rk.get("current_a") or 0.0))
                        hload = float(rh.get("load_pct") or 0.0)
                        kload = float(rk.get("load_pct") or 0.0)
                        hip_knee_currents.extend([hcur, kcur])
                        hip_knee_loads.extend([hload, kload])
                        current_excess = max(
                            current_excess,
                            hcur - abs(float(bh.get("current_a") or 0.0)),
                            kcur - abs(float(bk.get("current_a") or 0.0)))
                        load_excess = max(
                            load_excess,
                            hload - float(bh.get("load_pct") or 0.0),
                            kload - float(bk.get("load_pct") or 0.0))
                        hdeg = self._maybe_float(rh.get("deg"))
                        kdeg = self._maybe_float(rk.get("deg"))
                        if hdeg is not None:
                            hip_vals.append(hdeg)
                        if kdeg is not None:
                            knee_vals.append(kdeg)
                        per_leg.append({
                            "leg": leg,
                            "hip_deg": None if hdeg is None else round(hdeg, 2),
                            "knee_deg": None if kdeg is None else round(kdeg, 2),
                            "hip_current_a": round(hcur, 3),
                            "knee_current_a": round(kcur, 3),
                            "hip_load_pct": round(hload, 1),
                            "knee_load_pct": round(kload, 1),
                        })
                    tilt = read_tilt()
                    roll_delta = pitch_delta = None
                    if tilt is not None and base_tilt is not None:
                        roll_delta = tilt[0] - base_tilt[0]
                        pitch_delta = tilt[1] - base_tilt[1]
                    weak_contact = (
                        current_excess >= 0.012 or load_excess >= 2.4)
                    firm_contact = (
                        current_excess >= 0.055 or load_excess >= 5.5)
                    row = {
                        "family": label,
                        "cmd_hip_deg": round(float(hip), 2),
                        "cmd_knee_deg": round(float(knee), 2),
                        "mean_hip_deg": (
                            None if not hip_vals else
                            round(sum(hip_vals) / len(hip_vals), 2)),
                        "mean_knee_deg": (
                            None if not knee_vals else
                            round(sum(knee_vals) / len(knee_vals), 2)),
                        "max_hip_knee_current_a": round(
                            max(hip_knee_currents or [0.0]), 3),
                        "mean_hip_knee_current_a": round(
                            sum(hip_knee_currents)
                            / max(1, len(hip_knee_currents)), 3),
                        "max_hip_knee_load_pct": round(
                            max(hip_knee_loads or [0.0]), 1),
                        "current_excess_a": round(max(0.0, current_excess), 3),
                        "load_excess_pct": round(max(0.0, load_excess), 1),
                        "contact_hint": bool(weak_contact),
                        "firm_contact_hint": bool(firm_contact),
                        "per_leg": per_leg,
                    }
                    if firm_contact:
                        row["contact_strength"] = "firm"
                    elif weak_contact:
                        row["contact_strength"] = "weak"
                    if tilt is not None:
                        row["roll_deg"] = round(tilt[0], 2)
                        row["pitch_deg"] = round(tilt[1], 2)
                    if roll_delta is not None and pitch_delta is not None:
                        row["roll_delta_deg"] = round(roll_delta, 2)
                        row["pitch_delta_deg"] = round(pitch_delta, 2)
                        row["tilt_delta_deg"] = round(
                            max(abs(roll_delta), abs(pitch_delta)), 2)
                    return row

                def summarize(rows: list[dict], angle_key: str) -> dict:
                    first = next(
                        (r for r in rows if r.get("contact_hint")), None)
                    first_firm = next(
                        (r for r in rows if r.get("firm_contact_hint")), None)
                    return {
                        "samples": len(rows),
                        "first_contact_hint_deg": (
                            None if first is None else first.get(angle_key)),
                        "first_contact_strength": (
                            None if first is None
                            else first.get("contact_strength")),
                        "first_firm_contact_deg": (
                            None if first_firm is None
                            else first_firm.get(angle_key)),
                        "max_current_a": round(max([
                            float(r.get("max_hip_knee_current_a") or 0.0)
                            for r in rows
                        ] or [0.0]), 3),
                        "max_load_pct": round(max([
                            float(r.get("max_hip_knee_load_pct") or 0.0)
                            for r in rows
                        ] or [0.0]), 1),
                        "max_tilt_delta_deg": round(max([
                            float(r.get("tilt_delta_deg") or 0.0)
                            for r in rows
                        ] or [0.0]), 2),
                    }

                try:
                    self._bus_hot_begin()
                    with d._lock:
                        d.mode = "demo"
                        d.gait.stop()
                    live = _live_robot_ids(d.bus)
                    if len(live) < 12:
                        result = {
                            "ok": False,
                            "mode": "axis_geometry",
                            "error": f"need more servos (live={len(live)})",
                            "live": sorted(live),
                        }
                    else:
                        rec["expected"] = expected_angles()
                        progress("axis geometry: safe zero")
                        zero_start = self._safe_zero_sync(
                            abort_check=self._demo_abort.is_set,
                            on_progress=lambda p: progress(
                                "axis geometry zero: "
                                + str(p.get("msg") or "running")))
                        rec["zero_start"] = zero_start
                        if (gen != self._demo_gen
                                or self._demo_abort.is_set()
                                or not zero_start.get("ok")):
                            result = {
                                "ok": False,
                                "aborted": bool(self._demo_abort.is_set()
                                                or zero_start.get("aborted")),
                                "mode": "axis_geometry",
                                "error": (zero_start.get("error")
                                          or "safe zero failed"),
                                "record": rec,
                            }
                        else:
                            _enable_torque(d.bus, live)
                            _set_torque_limit(d.bus, live, 520)
                            time.sleep(0.25)
                            base_tilt = read_tilt()
                            baseline = self._read_feedback_map(d.bus)
                            baseline_row = sample_once(
                                "baseline", 0.0, 0.0, baseline, base_tilt)
                            rec["baseline"] = baseline_row
                            families = [
                                ("knee_only", "cmd_knee_deg", [
                                    (0.0, 0.0), (0.0, 10.0),
                                    (0.0, 15.0), (0.0, 20.0),
                                    (0.0, 25.0), (0.0, 30.0),
                                    (0.0, 35.0), (0.0, 40.0),
                                    (0.0, 45.0), (0.0, 48.0),
                                    (0.0, 50.0), (0.0, 52.0),
                                    (0.0, 54.0), (0.0, 56.0),
                                    (0.0, 58.0), (0.0, 60.0),
                                ]),
                                ("hip_only", "cmd_hip_deg", [
                                    (0.0, 0.0), (8.0, 0.0),
                                    (12.0, 0.0), (16.0, 0.0),
                                    (20.0, 0.0), (23.0, 0.0),
                                    (25.0, 0.0), (28.0, 0.0),
                                    (30.0, 0.0), (32.0, 0.0),
                                    (34.0, 0.0),
                                ]),
                            ]
                            guard_error = None
                            by_family: dict[str, dict] = {}
                            for family, angle_key, targets in families:
                                if guard_error or self._demo_abort.is_set():
                                    break
                                progress(f"axis geometry: {family} sweep")
                                # Return to the real zero between families so
                                # any load in the second family is not inherited.
                                _write_pose(
                                    d.bus, pose(0.0, 0.0), live,
                                    speed=120, acc=10)
                                time.sleep(0.55)
                                rows: list[dict] = []
                                for hip, knee in targets:
                                    if self._demo_abort.is_set():
                                        guard_error = "aborted"
                                        break
                                    progress(
                                        f"axis geometry: {family} "
                                        f"hip {hip:+.0f} / knee {knee:+.0f}")
                                    _write_pose(
                                        d.bus, pose(hip, knee), live,
                                        speed=90, acc=8)
                                    time.sleep(0.48)
                                    row = sample_once(
                                        family, hip, knee,
                                        baseline, base_tilt)
                                    rec["samples"].append(row)
                                    rows.append(row)
                                    max_cur = float(
                                        row.get("max_hip_knee_current_a")
                                        or 0.0)
                                    tilt_delta = float(
                                        row.get("tilt_delta_deg") or 0.0)
                                    if max_cur >= 2.2:
                                        guard_error = (
                                            f"{family} current guard "
                                            f"{max_cur:.2f}A")
                                        break
                                    if tilt_delta >= 14.0:
                                        guard_error = (
                                            f"{family} tilt guard "
                                            f"{tilt_delta:.1f} deg")
                                        break
                                by_family[family] = summarize(rows, angle_key)
                            rec["summary"] = by_family
                            rec["guard_error"] = guard_error

                            progress("axis geometry: return zero")
                            zero_end = (
                                {"ok": False, "skipped": True,
                                 "error": "operator aborted"}
                                if self._demo_abort.is_set() else
                                self._safe_zero_sync(
                                    abort_check=self._demo_abort.is_set,
                                    on_progress=lambda p: progress(
                                        "axis geometry return zero: "
                                        + str(p.get("msg") or "running"))))
                            rec["zero_end"] = zero_end

                            log_dir = self._meas_dir()
                            log_dir.mkdir(parents=True, exist_ok=True)
                            path = log_dir / f"axis_geometry_{stamp}.json"
                            rec["log_name"] = path.name
                            rec["path"] = str(path)
                            path.write_text(json.dumps(rec, indent=2) + "\n")
                            if guard_error:
                                result = {
                                    "ok": False,
                                    "mode": "axis_geometry",
                                    "recoverable": True,
                                    "guard_stop": guard_error != "aborted",
                                    "aborted": guard_error == "aborted",
                                    "error": guard_error,
                                    "record": rec,
                                }
                            else:
                                result = self._meas_finalize(rec)
                                result["mode"] = "axis_geometry"
                except Exception as e:
                    result = {"ok": False, "mode": "axis_geometry",
                              "error": str(e), "record": rec}
                finally:
                    try:
                        if live:
                            _set_torque_limit(d.bus, live, 1000)
                    except Exception:
                        pass
                    try:
                        if live:
                            _limp_all(d.bus, live)
                    except Exception:
                        try:
                            d.handle("X")
                        except Exception:
                            pass
                    self._bus_hot_end()

            if gen != self._demo_gen:
                return
            with d._lock:
                if d.mode == "demo":
                    d.mode = "idle"
                d.armed = False
            with self._lock:
                self._cal_result = result
                if result.get("ok"):
                    summ = (result.get("record") or {}).get("summary") or {}
                    k = (summ.get("knee_only") or {}).get(
                        "first_contact_hint_deg")
                    h = (summ.get("hip_only") or {}).get(
                        "first_contact_hint_deg")
                    self._demo_status = (
                        f"done · knee contact ~{k}°, hip contact ~{h}°")
                else:
                    self._demo_status = (
                        "error: " + str(result.get("error") or "failed"))
                self._cal_progress = {"msg": self._demo_status}
            self._set_activity("limp", self._demo_status)

        self._demo_thread = threading.Thread(target=_worker, daemon=True)
        self._demo_thread.start()
        return {"ok": True, "stamp": stamp, "mode": "axis_geometry"}

    def measure_slip(self) -> dict:
        """Run the onboard loaded-vs-hover slip probe and save immediately."""
        d = self.drive
        if d.dry_run or not d.bus:
            return {"ok": False, "error": "no bus"}
        if self._demo_thread and self._demo_thread.is_alive():
            return {"ok": False, "error": "stop the running job first"}
        stamp = time.strftime("%Y%m%d_%H%M%S")

        self._demo_gen += 1
        gen = self._demo_gen
        self._demo_abort.clear()
        title = "measure onboard slip"
        with self._lock:
            self._demo_name = "measure_slip"
            self._demo_status = title
            self._demo_params = {}
            self._cal_result = None
            self._cal_progress = {"msg": title}
        self._set_activity("measure", title)

        def _worker():
            try:
                self._bus_hot_begin()
                with d._lock:
                    d.mode = "demo"
                    d.gait.stop()

                def on_progress(p: dict) -> None:
                    with self._lock:
                        self._cal_progress = dict(p)
                        self._demo_status = str(p.get("msg") or title)

                result = self._run_leg_slip_probe(
                    d.bus, abort_check=self._demo_abort.is_set,
                    on_progress=on_progress)
                if gen != self._demo_gen:
                    return
                rec = {
                    "kind": "onboard_slip",
                    "stamp": stamp,
                    "result": result,
                    "grade": result.get("grade"),
                    "slip_suspected": result.get("slip_suspected"),
                    "summary": result.get("msg"),
                }
                if result.get("ok"):
                    out = self._meas_finalize(rec)
                    with self._lock:
                        self._cal_result = out
                        self._demo_status = result.get("msg") or "slip saved"
                        self._cal_progress = {"msg": self._demo_status}
                else:
                    with self._lock:
                        self._cal_result = result
                        self._demo_status = (
                            "error: " + str(result.get("error") or "failed"))
            except Exception as e:
                if gen != self._demo_gen:
                    return
                with self._lock:
                    self._cal_result = {"ok": False, "error": str(e)}
                    self._demo_status = f"error: {e}"
            finally:
                self._bus_hot_end()
                if gen == self._demo_gen:
                    with d._lock:
                        if d.mode == "demo":
                            d.mode = "idle"
                    with self._lock:
                        st = self._demo_status
                    self._set_activity(
                        "armed" if d.armed else "limp", st)

        self._demo_thread = threading.Thread(target=_worker, daemon=True)
        self._demo_thread.start()
        return {"ok": True, "stamp": stamp}

    def measure_annotate(self, *, fields: dict | None = None) -> dict:
        """Merge operator readings into the pending record and save it.

        Accepted fields (all optional): measured_mm, lateral_drift_mm,
        measured_rot_deg (+ = CW), observed_turn ("cw"/"ccw"/"none"),
        notes. Computes slip ratio when measured_mm arrives.
        """
        with self._lock:
            rec = getattr(self, "_meas_pending", None)
        if not rec:
            return {"ok": False, "error": "no pending measurement"}
        fields = fields or {}
        for k in ("measured_mm", "lateral_drift_mm", "measured_rot_deg"):
            if fields.get(k) not in (None, ""):
                try:
                    rec[k] = float(fields[k])
                except (TypeError, ValueError):
                    return {"ok": False, "error": f"bad number for {k}"}
        if fields.get("observed_turn") in ("cw", "ccw", "none"):
            rec["observed_turn"] = fields["observed_turn"]
        if fields.get("notes"):
            rec["notes"] = str(fields["notes"])[:500]
        if (rec.get("measured_mm") is not None
                and rec.get("commanded_mm", 0) > 1e-6):
            rec["slip_ratio_measured_over_commanded"] = round(
                rec["measured_mm"] / rec["commanded_mm"], 3)
        return self._meas_finalize(rec)

    def measure_discard(self) -> dict:
        """Drop the pending measurement without saving."""
        with self._lock:
            had = getattr(self, "_meas_pending", None) is not None
            self._meas_pending = None
        return {"ok": True, "discarded": had}

    def measure_note(self, *, kind: str = "note",
                     fields: dict | None = None) -> dict:
        """Standalone operator record (no run). kind='rl_walk_tape'
        auto-attaches the newest rl_walk episode CSV so the tape
        reading lines up with its 25 Hz trace."""
        kind = str(kind or "note").strip()[:40]
        rec: dict = {"kind": kind,
                     "stamp": time.strftime("%Y%m%d_%H%M%S")}
        fields = fields or {}
        for k, v in fields.items():
            if k in ("measured_mm", "lateral_drift_mm",
                     "measured_rot_deg", "commanded_mm"):
                try:
                    rec[k] = float(v)
                except (TypeError, ValueError):
                    pass
            elif k == "notes":
                rec["notes"] = str(v)[:500]
        if kind == "rl_walk_tape":
            try:
                latest = max(self._meas_dir().glob("rl_walk_*.csv"),
                             key=lambda p: p.stat().st_mtime)
                rec["rl_episode_csv"] = latest.name
            except (ValueError, OSError):
                rec["rl_episode_csv"] = None
        if (rec.get("measured_mm") is not None
                and rec.get("commanded_mm", 0) > 1e-6):
            rec["slip_ratio_measured_over_commanded"] = round(
                rec["measured_mm"] / rec["commanded_mm"], 3)
        # Standalone records skip the pending slot entirely.
        rec["saved_unix"] = round(time.time(), 3)
        with self._meas_file().open("a") as f:
            f.write(json.dumps(rec) + "\n")
        return {"ok": True, "record": rec}
