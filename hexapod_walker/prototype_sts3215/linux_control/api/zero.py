"""BenchAPI route group: go_zero, set-zero-here, zero acquisition (settle + glide).

Moved verbatim from bench_api.py (2026-08-29 component-boundaries split);
mixed into ``bench_api.BenchAPI``. Route/JSON shapes are unchanged.
"""
from __future__ import annotations

from .common import *  # noqa: F401,F403


class ZeroApi:
    def go_zero(self, pose: str = "sit", *, force: bool = False) -> dict:
        """Go to sit zero (legs out) or stand zero (standing stance) — SAFELY.

        ``pose``: ``sit`` | ``stand``.  Stand keeps torque on (no limp).

        Neither direction refuses on a big delta any more (operator
        directives 08-10 sit / 08-11 stand): the robot ACQUIRES the
        pose instead. Current standard:
        - STAND while already upright adjusts/verifies plant height.
        - STAND while not upright runs safe-zero, then STEP stand-up.
        - SIT/LOWER while upright runs STEP-down.
        - SIT/LOWER while not upright/tangled runs safe-zero recovery.
        If acquisition fails the robot stops (hold or limp) and the job
        errors out.
        """
        pose = (pose or "sit").strip().lower()
        if pose in ("stand", "standing", "plant"):
            pose = "stand"
        else:
            pose = "sit"
        if self.drive.dry_run:
            return {"ok": True, "dry_run": True, "pose": pose}
        if not self.drive.bus:
            return {"ok": False, "error": "no bus"}
        if self._running_calibration_name():
            return self._calibration_busy_response(f"{pose} zero")
        if self._demo_thread and self._demo_thread.is_alive():
            if not self._preempt_demo_thread(
                    reason=f"→ {pose} zero", timeout=5.0):
                return {"ok": False,
                        "error": "previous demo did not stop — try Stop / E-STOP",
                        "robot": self.robot_state()}
        self._quad_reared = False

        if pose == "sit":
            present, missing = self._present_pose18()
            if not missing and self._normal_standing_pose(present):
                return self.standup(mode="step", speed=10.0,
                                    direction="down")
            # not standing (low, folded, odd): settle + guarded glide, as a job

        # Standard stand = the validated STEP keyframes at 10x. When the
        # robot is already near the first STEP frame (belly-down, legs
        # out), delegate straight to the keyframes. Otherwise the worker
        # below acquires safe zero first.
        try:
            kfs = self._load_standup()["modes"]["step"]["keyframes"]
            step_zero = [float(x) for x in kfs[0]["q_deg"]]
            d_zero, _ = self._delta_vs_present(step_zero)
            if (pose == "stand" and d_zero is not None
                    and d_zero <= 25.0):
                return self.standup(mode="step", speed=10.0,
                                    direction="up")
        except Exception:
            pass

        self._demo_gen += 1
        gen = self._demo_gen
        self._demo_abort.clear()
        with self._lock:
            self._demo_name = f"zero_{pose}"
            self._demo_status = "zeroing"
            self._demo_params = {"pose": pose, "force": bool(force)}
            self._cal_progress = {"msg": f"go to {pose} zero"}
        self._set_activity("zeroing", f"go to {pose} zero")

        def _worker():
            d = self.drive
            with d._lock:
                d.mode = "demo"
                if not d.armed:
                    d._torque_all(True)
                    d.armed = True
            result: dict = {}
            try:
                self._bus_hot_begin()

                def _prog(p: dict) -> None:
                    with self._lock:
                        self._cal_progress = dict(p)

                if pose == "stand":
                    result = self._acquire_start("stand", gen=gen,
                                                 on_progress=_prog)
                else:
                    result = self._zero_sync(
                        abort_check=self._demo_abort.is_set,
                        on_progress=_prog)
                if gen != self._demo_gen:
                    return
                with self._lock:
                    if result.get("ok"):
                        self._demo_status = "done"
                    elif result.get("aborted"):
                        self._demo_status = "aborted"
                    else:
                        self._demo_status = (
                            f"error: {result.get('error') or 'failed'}")
                    self._cal_progress = {"msg": self._demo_status}
            except Exception as e:
                if gen != self._demo_gen:
                    return
                with self._lock:
                    self._demo_status = f"error: {e}"
            finally:
                self._bus_hot_end()
                if gen != self._demo_gen:
                    return
                if result.get("limp"):
                    with d._lock:
                        d.armed = False
                with self._lock:
                    st = self._demo_status
                # Stand home must keep mode=stand so the drive loop re-holds
                # plant (otherwise stance droops after the one-shot glide).
                if st == "done" and pose == "stand":
                    self._enter_stand_hold()
                    self._set_activity("armed", "at stand zero")
                else:
                    with d._lock:
                        if d.mode == "demo":
                            d.mode = "idle"
                    if str(st).startswith("error"):
                        self._set_activity("armed" if d.armed else "limp", st)
                    else:
                        self._set_activity(
                            "armed" if d.armed else "limp",
                            f"at {pose} zero" if st == "done" else st)

        self._demo_thread = threading.Thread(target=_worker, daemon=True)
        self._demo_thread.start()
        return {"ok": True, "pose": pose, "demo": self.demo_state(),
                "robot": self.robot_state()}

    def set_zero_here(self, ids: list[int] | None = None) -> dict:
        """Feetech middle-calibrate: current pose becomes logical 0°.

        ``ids`` limits the calibrate to those servo ids (2..19); default is
        every live servo. Used to repair a single joint whose zero drifted
        (e.g. a horn re-seated) without touching the rest of the robot.

        This rewrites the absolute joint frame, so any learned plant/home pose
        from the previous frame is invalid and must be cleared immediately.
        """
        try:
            from urt2_bench import redefine_zero_here
        except ImportError as e:
            return {"ok": False, "error": str(e)}
        if self.drive.dry_run:
            return {"ok": True, "dry_run": True}
        if self._demo_thread and self._demo_thread.is_alive():
            return {"ok": False, "error": "stop the demo first"}
        if not self.drive.bus:
            return {"ok": False, "error": "no bus"}

        d = self.drive
        with d._lock:
            d.mode = "idle"
            d.gait.stop()
            d.armed = False
            try:
                d._torque_all(False)
            except Exception:
                pass
            try:
                result = redefine_zero_here(d.bus, ids=ids)
            except Exception as e:
                return {"ok": False, "error": str(e)}
            d.status = (f"zero-here {result.get('ok_n', 0)}/"
                        f"{result.get('count', 0)} (limp)")
        if result.get("ok"):
            try:
                from plant_calibrate import reset_plant_pose
                plant = reset_plant_pose()
                result["plant_reset"] = plant
                result["plant_cleared"] = bool(plant.get("cleared"))
            except Exception as e:
                result["plant_reset_error"] = str(e)
            try:
                from event_log import emit
                emit("zero",
                     "logical zero redefined; learned plant cleared",
                     src="bench",
                     data={
                         "count": result.get("count"),
                         "ok_n": result.get("ok_n"),
                         "plant_cleared": result.get("plant_cleared"),
                         "plant_reset_error": result.get(
                             "plant_reset_error"),
                     })
            except Exception:
                pass
        with self._lock:
            self._cal_result = None
            self._cal_progress = {}
        detail = (
            "zero redefined here; plant reset"
            if result.get("ok") else "zero redefine failed")
        self._set_activity("limp", detail)
        return result

    def _present_pose18(self) -> tuple[list, list[int]]:
        """All 18 present joint degrees (bulk read + per-joint retry).

        Returns ``(values, missing_joint_indices)`` — values contain
        None at the missing slots.
        """
        bus = self.drive.bus
        vals: list = [None] * N_JOINTS
        if bus is None:
            return vals, list(range(N_JOINTS))
        read_snapshot = getattr(bus, "read_snapshot", None)
        if callable(read_snapshot):
            snap = read_snapshot()
            for j, v in ((snap or {}).get("pos_deg") or {}).items():
                if 0 <= j < N_JOINTS:
                    vals[j] = float(v)
        for j in range(N_JOINTS):
            if vals[j] is None:
                try:
                    v = bus.read_position_deg(j)
                except Exception:
                    v = None
                vals[j] = None if v is None else float(v)
        return vals, [j for j, v in enumerate(vals) if v is None]

    # ---- zero: ONE way down, no planner (2026-09-22) ------------------------
    ZERO_AT_DEG = 8.0           # every joint within this of 0 = already at zero
    ZERO_GLIDE_TORQUE = 350     # torque limit while gliding the legs flat (body already on the floor)
    ZERO_GLIDE_DPS = 25.0       # glide rate
    ZERO_SETTLE_TORQUES = (500, 300, 180)   # hold-present ramp that lets an odd stance sink onto its belly
    ZERO_STALL_A = 3.0          # a hip/knee at this during the glide = jammed leg: stop and hold

    def _zero_sync(self, *, abort_check, on_progress=None, **_legacy) -> dict:
        """Bring the robot to zero (belly down, legs straight out) SYNCHRONOUSLY.

        Replaces the collision-aware safe_zero planner and the pinned-tip
        untrap fold (both removed 2026-09-22 as unreliable).  One policy:

        * within ZERO_AT_DEG of zero already: nothing to do;
        * a normal upright stance: the baked STEP sit-down, then the glide
          below for whatever is left;
        * anything else (low, folded, kneeling, odd): SETTLE first -- hold
          the MEASURED pose while the torque limit steps down so the body
          sinks onto its belly under its own weight (no servo pulls toward a
          target it has not reached) -- then ONE guarded low-torque glide to
          zero.  The glide stops on a hip/knee stall and the robot then holds
          the measured pose at STOP_HOLD_TORQUE: a jammed leg is for hands,
          not for more torque.

        Runs in the caller's worker thread; claims no job slot.  Returns
        ok / error / already_at_zero / limp like its predecessor.
        """
        try:
            from inplace_demos import (STOP_HOLD_TORQUE, CurrentPeakTracker, MotionGuard,
                                       _live_robot_ids, _read_pose, _set_torque_limit,
                                       _write_pose, ease_to_pose)
        except ImportError as e:
            return {"ok": False, "error": str(e)}
        bus = self.drive.bus
        if bus is None:
            return {"ok": False, "error": "no bus"}

        def _prog(msg: str) -> None:
            if on_progress:
                try:
                    on_progress({"msg": msg})
                except Exception:
                    pass

        present, missing = self._present_pose18()
        if missing:
            return {"ok": False, "error": "no encoder reading from " + ", ".join(
                joint_label(j, self.names) for j in missing)}
        if max(abs(float(v)) for v in present) <= self.ZERO_AT_DEG:
            return {"ok": True, "already_at_zero": True}
        live = _live_robot_ids(bus)
        if len(live) < N_JOINTS:
            return {"ok": False, "error": f"only {len(live)}/18 servos live"}

        standing = self._normal_standing_pose(present)
        if standing:
            _prog("zero: standing — STEP sit-down first")
            rs = self.standup(mode="step", speed=1.0, direction="down",
                              sync_gen=self._demo_gen)
            if not rs.get("ok"):
                return {"ok": False, "error": "STEP sit-down failed: "
                        + str(rs.get("error") or "aborted"), **({"aborted": True} if rs.get("aborted") else {})}
            present, missing = self._present_pose18()
            if missing:
                return {"ok": False, "error": "no encoder reading after the sit-down"}
            if max(abs(float(v)) for v in present) <= self.ZERO_AT_DEG:
                return {"ok": True, "route": "step_down"}
        else:
            # settle: re-command the measured pose at a falling torque limit
            for limit in self.ZERO_SETTLE_TORQUES:
                if abort_check():
                    return {"ok": False, "aborted": True, "error": "aborted during settle"}
                _prog(f"zero: settling onto the belly (torque limit {limit})")
                pose_now = _read_pose(bus, live)
                _set_torque_limit(bus, live, limit)
                _write_pose(bus, pose_now, live, speed=180, acc=25)
                time.sleep(0.8)

        # the guarded glide: legs to straight-out at low torque, stop on a stall
        present = _read_pose(bus, live)
        worst = max(abs(float(v)) for v in present)
        seconds = max(2.0, worst / self.ZERO_GLIDE_DPS)
        _prog(f"zero: gliding the legs flat over {seconds:.0f} s (worst {worst:.0f} deg)")
        _set_torque_limit(bus, live, self.ZERO_GLIDE_TORQUE)
        tracker = CurrentPeakTracker()
        try:
            ok = ease_to_pose(bus, [0.0] * N_JOINTS, abort_check=abort_check, seconds=seconds,
                              label="zero", current_tracker=tracker,
                              contact_current_a=self.ZERO_STALL_A)
        except Exception as e:  # noqa: BLE001
            ok = False
            _prog(f"zero: glide error {e}")
        after = _read_pose(bus, live)
        worst_after = max(abs(float(v)) for v in after)
        stalled = tracker.peak_a >= self.ZERO_STALL_A or tracker.peak_total_a > MotionGuard.TOTAL_CAP_A
        if not ok or stalled or worst_after > 12.0:
            # STOP MEANS STOP WHERE YOU ARE; the servo watch releases a sustained fight
            try:
                MotionGuard.stop_hold(bus, live)
            except Exception:
                pass
            why = ("aborted" if abort_check() else
                   f"stalled at {tracker.peak_a:.2f} A (joint {tracker.peak_joint}, bus {tracker.peak_total_a:.1f} A)"
                   if stalled else f"did not reach zero (worst joint {worst_after:.0f} deg off)")
            return {"ok": False, "aborted": bool(abort_check()),
                    "error": f"zero glide {why}; holding the measured pose at torque {STOP_HOLD_TORQUE} — "
                             "a leg is jammed: free it by hand, then retry",
                    "peak_a": round(tracker.peak_a, 2), "peak_total_a": round(tracker.peak_total_a, 2)}
        _set_torque_limit(bus, live, 1000)
        return {"ok": True, "route": "settle_glide" if not standing else "step_down_glide",
                "peak_a": round(tracker.peak_a, 2), "peak_total_a": round(tracker.peak_total_a, 2)}

    def _acquire_start(self, kind: str, *, gen: int,
                       on_progress=None) -> dict:
        """Bring the robot to a routine's start pose: ``zero`` (belly down,
        legs out) or ``stand`` (the baked STEP stand, finished at the sim
        walk-ready stance).  ``stand_tuck`` is accepted as ``stand`` (the tuck
        keyframes are gone).  Runs INSIDE the caller's worker (``gen``).
        On any failure the robot has already been stopped (hold or limp);
        returns ``ok=False`` and the caller MUST NOT run its routine.
        """
        def _prog(p: dict) -> None:
            if on_progress:
                try:
                    on_progress(dict(p))
                except Exception:
                    pass
            else:
                with self._lock:
                    self._cal_progress = dict(p)

        kind = "stand" if str(kind).strip().lower().startswith(("stand", "tuck", "quad")) else "zero"
        acquired: list[str] = []
        if kind == "stand":
            present, missing = self._present_pose18()
            standing = None if missing else self._normal_standing_pose(present)
            if standing:
                res = self._step_to_rl_walk_ready_start_sync(
                    abort_check=self._demo_abort.is_set, on_progress=on_progress)
                if not res.get("ok"):
                    return {"ok": False, "acquired": acquired,
                            "error": str(res.get("error") or "failed")}
                return {"ok": True, "acquired": ["stand_adjusted"], "standing": standing, **res}
        _prog({"msg": "acquiring start: zero…"})
        rz = self._zero_sync(abort_check=self._demo_abort.is_set, on_progress=_prog)
        if not rz.get("ok"):
            return {"ok": False, "acquired": acquired, "limp": bool(rz.get("limp")),
                    "error": "could not reach zero start: "
                             + str(rz.get("error") or ("aborted" if rz.get("aborted") else "failed"))}
        if not rz.get("already_at_zero"):
            acquired.append("zero")
        if kind == "zero":
            return {"ok": True, "acquired": acquired}
        _prog({"msg": "acquiring start: STEP stand-up…"})
        rs = self.standup(mode="step", speed=10.0, direction="up", sync_gen=gen)
        if not rs.get("ok"):
            return {"ok": False, "acquired": acquired,
                    "error": "could not reach stand start: " + str(rs.get("error") or "aborted")}
        acquired.append("standup_step")
        _prog({"msg": "acquiring start: sim walk-ready pose…"})
        settle_result = self._step_to_rl_walk_ready_start_sync(
            abort_check=self._demo_abort.is_set, on_progress=_prog)
        if not settle_result.get("ok"):
            why = settle_result.get("error") or ("aborted" if settle_result.get("aborted") else "failed")
            return {"ok": False, "acquired": acquired, "limp": bool(settle_result.get("limp")),
                    "error": f"could not reach walk-ready start: {why}"}
        acquired.append("sim_walk_start")
        return {"ok": True, "acquired": acquired}
