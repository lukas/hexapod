"""BenchAPI route group: go_zero, set-zero-here, safe_zero, pinned-tip untrap.

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
            return self.standup(mode="step", speed=10.0,
                                direction="down")

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
                    result = self._safe_zero_sync(
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

    def set_zero_here(self) -> dict:
        """Feetech middle-calibrate: current pose becomes logical 0°.

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
                result = redefine_zero_here(d.bus)
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
        try:
            if hasattr(bus, "read_all_positions"):
                for j, v in (bus.read_all_positions() or {}).items():
                    if 0 <= j < N_JOINTS:
                        vals[j] = float(v)
        except Exception:
            pass
        for j in range(N_JOINTS):
            if vals[j] is None:
                try:
                    v = bus.read_position_deg(j)
                except Exception:
                    v = None
                vals[j] = None if v is None else float(v)
        return vals, [j for j, v in enumerate(vals) if v is None]

    def _safe_zero_sync(self, *, abort_check, on_progress=None) -> dict:
        """Plan + execute the collision-aware go-to-zero SYNCHRONOUSLY.

        Runs in the caller's worker thread; claims no job slot and
        paints no status — the caller owns those. No-ops when already
        at zero. Any anomaly during motion limps the robot
        (``run_safe_zero``) and returns ``ok=False`` — the caller must
        stop its own routine in that case.

        PINNED-TIP GATE (08-11 overheat lesson): when the read-only
        detector says the body is tipped over a folded knee, the
        low-torque untrap fold runs FIRST — driving 18 joints toward
        zero at working torque against a pinned leg is exactly the
        loop that stacked hips to 71 °C. Every motion path that
        acquires its start through here inherits the gate.
        """
        try:
            from safe_zero import (belly_ground_z_mm, plan_safe_zero,
                                   run_safe_zero)
        except ImportError as e:
            return {"ok": False, "error": str(e)}
        untrap = None
        try:
            from pinned_tip import check_pinned_tip, run_untrap_tuck
            verdict = check_pinned_tip(self.drive.bus)
        except Exception:
            verdict = {"pinned": False}
        if verdict.get("pinned"):
            try:
                from event_log import emit
                emit("pinned_tip", verdict.get("why", "pinned-leg tip"),
                     data=verdict, level="warn")
            except Exception:
                pass
            if on_progress:
                on_progress({"msg": "tipped on a trapped leg — "
                                    "low-torque untrap fold first"})
            untrap = run_untrap_tuck(self.drive.bus,
                                     abort_check=abort_check,
                                     on_progress=on_progress)
            if not untrap.get("ok"):
                return {"ok": False, "limp": bool(untrap.get("limp")),
                        "untrap": untrap, "pinned_tip": verdict,
                        "error": ("untrap failed: "
                                  + str(untrap.get("error") or "?"))}
        present, missing = self._present_pose18()
        if missing:
            return {"ok": False,
                    "error": ("no encoder reading from " + ", ".join(
                        joint_label(j, self.names) for j in missing))}
        plan = plan_safe_zero(present, ground_z_mm=belly_ground_z_mm())
        if not plan.get("ok"):
            if untrap is not None:
                plan["untrap"] = untrap
            return plan
        if not plan["stages"]:
            return {"ok": True, "already_at_zero": True,
                    **({"untrap": untrap} if untrap else {})}
        result = run_safe_zero(self.drive.bus, plan["stages"],
                               abort_check=abort_check,
                               on_progress=on_progress)
        if untrap is not None:
            result["untrap"] = untrap
        return result

    def _acquire_start(self, kind: str, *, gen: int,
                       on_progress=None) -> dict:
        """Safely bring the robot to a routine's required start pose.

        ``kind``: ``zero`` (belly down, legs out), ``stand`` (baked
        step stand), or ``stand_tuck`` (quad's slower step stand
        acquisition).
        Runs INSIDE the caller's worker thread — the caller must own
        the job slot (``gen``).

        Operator directive 08-11: stance-gated routines ACQUIRE their
        start instead of refusing. Strategy: collision-aware safe zero
        first, then the validated keyframe step stand-up when a stand
        is needed. On ANY failure the failing engine has
        already stopped the robot (hold or limp); this returns
        ``ok=False`` and the caller MUST NOT run its routine.
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

        raw_kind = str(kind).strip().lower()
        tuck_stand = raw_kind in ("stand_tuck", "tuck_stand",
                                  "quad_stand")
        kind = "stand" if raw_kind.startswith("stand") else "zero"
        d = self.drive
        acquired: list[str] = []
        if kind == "stand":
            present, missing = self._present_pose18()
            standing = (None if missing else
                        self._normal_standing_pose(present))
            if standing:
                res = (self._settle_stand_pose_sync(
                    abort_check=self._demo_abort.is_set,
                    on_progress=on_progress) if tuck_stand else
                    self._step_to_rl_walk_ready_start_sync(
                        abort_check=self._demo_abort.is_set,
                        on_progress=on_progress))
                if not res.get("ok"):
                    return {"ok": False, "acquired": acquired,
                            "error": str(res.get("error") or "failed")}
                tag = ("tuck_stand_adjusted" if tuck_stand
                       else "stand_adjusted")
                return {"ok": True, "acquired": [tag],
                        "standing": standing, **res}
        # Everything else goes through a safe zero first (no-op when
        # already there; plans around ground / leg collisions; limps
        # on stall or unexpected force).
        _prog({"msg": "acquiring start: safe zero…"})
        rz = self._safe_zero_sync(abort_check=self._demo_abort.is_set,
                                  on_progress=_prog)
        if not rz.get("ok"):
            why = (rz.get("error")
                   or ("aborted" if rz.get("aborted") else "failed"))
            return {"ok": False, "acquired": acquired,
                    "limp": bool(rz.get("limp")),
                    "error": f"could not reach zero start: {why}"}
        if not rz.get("already_at_zero"):
            acquired.append("safe_zero")
        if kind == "zero":
            return {"ok": True, "acquired": acquired}
        mode = "step"
        label = "STEP stand"
        _prog({"msg": f"acquiring start: stand-up to {label}…"})
        rs = self.standup(mode=mode, speed=(6.0 if tuck_stand else 10.0),
                          direction="up",
                          sync_gen=gen)
        if not rs.get("ok"):
            return {"ok": False, "acquired": acquired,
                    "error": ("could not reach stand start: "
                              + str(rs.get("error") or "aborted"))}
        acquired.append("standup_step")
        if not tuck_stand:
            # The baked step stand-up ends near the simulator's walk reset
            # pose. Re-hold/verify that explicit pose here; do not read
            # plant_pose.json, which is only a calibration artifact.
            _prog({"msg": "acquiring start: sim walk-ready pose…"})
            settle_result = self._step_to_rl_walk_ready_start_sync(
                abort_check=self._demo_abort.is_set,
                on_progress=_prog)
            if not settle_result.get("ok"):
                why = (settle_result.get("error")
                       or ("aborted" if settle_result.get("aborted")
                           else "failed"))
                return {"ok": False, "acquired": acquired,
                        "limp": bool(settle_result.get("limp")),
                        "error": f"could not reach walk-ready start: {why}"}
            acquired.append("sim_walk_start")
        return {"ok": True, "acquired": acquired}

    def pinned_tip_state(self) -> dict:
        """READ-ONLY pinned-leg-tip verdict (see pinned_tip.py).

        One IMU read on a level robot; when tipped it settles ~1.2 s
        and reads again before classifying. Never commands motion —
        safe to poll from the web UI.
        """
        try:
            from pinned_tip import check_pinned_tip
        except ImportError as e:
            return {"ok": False, "error": str(e)}
        if self.drive.dry_run or not self.drive.bus:
            return {"ok": False, "error": "no bus"}
        v = check_pinned_tip(self.drive.bus)
        return {"ok": "error" not in v, **v}

    def untrap(self, *, force: bool = False) -> dict:
        """Low-torque untrap fold (pinned_tip.run_untrap_tuck) as a job.

        Refuses unless the read-only detector confirms a pinned-leg
        tip (``force=true`` overrides for bench testing while the
        operator watches — the move is torque-bounded either way).
        Success leaves the robot level + folded, holding at the LOW
        limit; run safe_zero next. Failure/abort leaves it LIMP.
        """
        try:
            from pinned_tip import TUCK_TORQUE, check_pinned_tip, \
                run_untrap_tuck
        except ImportError as e:
            return {"ok": False, "error": str(e)}
        if self.drive.dry_run or not self.drive.bus:
            return {"ok": False, "error": "no bus"}

        verdict = check_pinned_tip(self.drive.bus)
        if not verdict.get("pinned") and not force:
            return {"ok": False, "pinned_tip": verdict,
                    "error": ("not a pinned-leg tip ("
                              + str(verdict.get("why")
                                    or verdict.get("error") or "?")
                              + ") — nothing to untrap. force=true "
                              "runs the fold anyway (watching!).")}

        if self._demo_thread and self._demo_thread.is_alive():
            if not self._preempt_demo_thread(reason="→ untrap",
                                             timeout=5.0):
                return {"ok": False,
                        "error": ("previous job did not stop — "
                                  "try Stop / E-STOP"),
                        "robot": self.robot_state()}

        self._demo_gen += 1
        gen = self._demo_gen
        self._demo_abort.clear()
        with self._lock:
            self._demo_name = "untrap"
            self._demo_status = "untrap: low-torque fold"
            self._demo_params = {"force": bool(force),
                                 "torque_limit": TUCK_TORQUE}
            self._cal_result = None
            self._cal_progress = {"msg": "untrap: starting"}
        self._set_activity("zeroing", "untrap (low-torque fold)")

        def _worker():
            d = self.drive
            with d._lock:
                d.mode = "demo"
                d.gait.stop()
            result: dict = {}
            try:
                from event_log import emit
                emit("untrap", "start", data=verdict, level="warn")
            except Exception:
                pass
            try:
                self._bus_hot_begin()

                def _prog(dct: dict) -> None:
                    with self._lock:
                        self._cal_progress = dict(dct)

                result = run_untrap_tuck(
                    d.bus, abort_check=self._demo_abort.is_set,
                    on_progress=_prog)
                result["pinned_tip"] = verdict
            except Exception as e:
                result = {"ok": False, "error": str(e)}
            finally:
                self._bus_hot_end()
                if gen != self._demo_gen:
                    return
                limp = bool(result.get("limp"))
                with self._lock:
                    self._cal_result = result
                    if result.get("ok"):
                        self._demo_status = ("done · level + folded "
                                             "(low torque) — safe zero "
                                             "next")
                    else:
                        self._demo_status = str(
                            result.get("error") or "error")
                    self._cal_progress = {"msg": self._demo_status}
                    st = self._demo_status
                with d._lock:
                    if d.mode == "demo":
                        d.mode = "idle"
                    if limp:
                        d.armed = False
                    else:
                        d.armed = True
                    d.status = st
                try:
                    from event_log import emit
                    emit("untrap", "done" if result.get("ok") else st,
                         data={k: result.get(k)
                               for k in ("ok", "limp", "tilt_deg",
                                         "trapped_names", "peak_a")
                               if k in result})
                except Exception:
                    pass
                self._set_activity(
                    "limp" if limp else "armed", st)

        self._demo_thread = threading.Thread(target=_worker, daemon=True)
        self._demo_thread.start()
        return {"ok": True, "started": True, "pinned_tip": verdict,
                "demo": self.demo_state(), "robot": self.robot_state()}

    def safe_zero(self, *, dry_run: bool = False,
                  force: bool = False) -> dict:
        """Smart go-to-zero with STEP-down for normal stance.

        If the robot is level and near a normal standing pose (captured
        plant or STEP's final stance), this endpoint delegates to
        STEP-down. That is the normal descent path.

        Otherwise this is the collision-aware untangle/recovery path:
        it plans staged waypoints from present encoders to logical 0°
        (``safe_zero.plan_safe_zero``: straighten → center yaws with feet
        lifted clear of the ground → extend flat) and REFUSES with an
        error when no ground/self-collision-free path exists. During
        motion, any servo reporting stall-fight current, sustained load,
        or "commanded but not turning" LIMPS the whole robot immediately
        (``run_safe_zero``).

        ``dry_run=True`` returns the plan without any motion.
        ``force`` bypasses only the IMU tilt gate — never the
        geometric feasibility or wrong-zero refusals.
        """
        try:
            import math as _math
            from safe_zero import belly_ground_z_mm, plan_safe_zero
        except ImportError as e:
            return {"ok": False, "error": str(e)}
        if self.drive.dry_run:
            return {"ok": True, "dry_run": True}
        bus = self.drive.bus
        if not bus:
            return {"ok": False, "error": "no bus"}
        if self._running_calibration_name():
            return self._calibration_busy_response("safe zero")

        present, missing = self._present_pose18()
        if missing:
            return {"ok": False,
                    "error": ("no encoder reading from " + ", ".join(
                        joint_label(j, self.names) for j in missing)
                        + " — safe zero needs all 18 joints")}

        # Tilt gate: the planner's ground model assumes a roughly
        # level body (belly-down or standing on its feet).
        tilt = None
        pinned = None
        try:
            if hasattr(bus, "read_imu"):
                imu = bus.read_imu()
                if imu:
                    ax = float(imu.get("ax_g", 0.0))
                    ay = float(imu.get("ay_g", 0.0))
                    az = float(imu.get("az_g", 0.0))
                    roll = _math.degrees(_math.atan2(ay, az))
                    pitch = _math.degrees(
                        _math.atan2(-ax, _math.hypot(ay, az)))
                    tilt = max(abs(roll), abs(pitch))
        except Exception:
            tilt = None
        if tilt is not None:
            # Tipped over a folded knee (THE post-fall state, 08-11)?
            # Then safe zero knows how to proceed: the worker runs the
            # low-torque untrap fold before any planned stage, so a
            # bare refusal here would just push the caller to retry
            # stand/walk against the pin instead. Classify on EVERY
            # call (pure math on data already in hand) — the first
            # live pinned test rested at only 13° tilt, well under
            # this endpoint's 20° hard gate, and a pinned pose can
            # also defeat the preview planner below.
            try:
                from pinned_tip import classify_pinned_tip
                pinned = classify_pinned_tip(present, roll, pitch)
            except Exception:
                pinned = None
            if (tilt > 20.0 and not (pinned and pinned.get("pinned"))
                    and not force):
                return {"ok": False, "tilt_deg": round(tilt, 1),
                        **({"pinned_tip": pinned} if pinned else {}),
                        "error": (f"body tilted {tilt:.0f}° with legs "
                                  "near straight — on a slope or "
                                  "hand-placed? Safe zero assumes "
                                  "roughly level. Right the robot (or "
                                  "force=true while watching).")}

        standing = self._normal_standing_pose(
            present, tilt_deg=tilt, pinned=pinned)
        if standing:
            # Safe zero is the tangled/unknown recovery path. A level,
            # normal standing robot should descend through the same STEP
            # lower used by all non-Experiments controls, not through the
            # collision-avoidance untangle planner.
            if dry_run:
                return {"ok": True, "dry_run": True,
                        "route": "step_lower",
                        "standing": standing,
                        "msg": "standing pose: would use STEP lower"}
            res = self.standup(mode="step", speed=10.0,
                               direction="down")
            res["route"] = "step_lower"
            res["standing"] = standing
            return res

        plan = plan_safe_zero(present, ground_z_mm=belly_ground_z_mm())
        plan["present_deg"] = [round(v, 2) for v in present]
        if tilt is not None:
            plan["tilt_deg"] = round(tilt, 1)
        if pinned and pinned.get("pinned"):
            plan["pinned_tip"] = pinned
            if not plan.get("ok"):
                # A tipped pose can defeat the preview planner (crossed
                # legs); the worker re-plans on fresh encoders AFTER the
                # untrap fold, so this preview must not block motion.
                plan = {"ok": True, "stages": [], "pinned_tip": pinned,
                        "present_deg": plan["present_deg"],
                        "tilt_deg": plan.get("tilt_deg"),
                        "notes": ["pinned-leg tip: low-torque untrap "
                                  "fold first, then re-plan"]}
        if dry_run or not plan.get("ok"):
            plan["dry_run"] = bool(dry_run)
            return plan
        if not plan["stages"] and not (pinned and pinned.get("pinned")):
            return {**plan, "msg": "already at zero"}

        if self._demo_thread and self._demo_thread.is_alive():
            if not self._preempt_demo_thread(reason="→ safe zero",
                                             timeout=5.0):
                return {"ok": False,
                        "error": ("previous job did not stop — "
                                  "try Stop / E-STOP"),
                        "robot": self.robot_state()}

        self._demo_gen += 1
        gen = self._demo_gen
        self._demo_abort.clear()
        with self._lock:
            self._demo_name = "safe_zero"
            self._demo_status = "safe zero"
            self._demo_params = {"stages": len(plan["stages"]),
                                 "force": bool(force)}
            self._cal_result = None
            self._cal_progress = {"msg": "safe zero: starting"}
        self._set_activity("zeroing", "safe zero")

        def _worker():
            d = self.drive
            with d._lock:
                d.mode = "demo"
                d.gait.stop()
                if not d.armed:
                    d._torque_all(True)
                    d.armed = True
            result: dict = {}
            try:
                from event_log import emit
                emit("safe_zero",
                     f"start ({len(plan['stages'])} stages, "
                     f"{plan.get('total_s')}s)",
                     data={"stages": [s["label"]
                                      for s in plan["stages"]]})
            except Exception:
                pass
            try:
                self._bus_hot_begin()

                def _prog(dct: dict) -> None:
                    with self._lock:
                        self._cal_progress = dct

                # _safe_zero_sync re-plans on fresh encoders: a limp
                # robot may have sagged between the HTTP call and
                # torque-on.
                result = self._safe_zero_sync(
                    abort_check=self._demo_abort.is_set,
                    on_progress=_prog)
                if result.get("already_at_zero"):
                    result.setdefault("msg", "already at zero")
            except Exception as e:
                result = {"ok": False, "error": str(e)}
            finally:
                self._bus_hot_end()
                if gen != self._demo_gen:
                    return
                limp = bool(result.get("limp"))
                with self._lock:
                    self._cal_result = result
                    if result.get("ok"):
                        self._demo_status = "done · at zero (safe)"
                    elif result.get("aborted"):
                        self._demo_status = "aborted (holding)"
                    else:
                        self._demo_status = str(
                            result.get("error") or "error")
                    self._cal_progress = {"msg": self._demo_status}
                    st = self._demo_status
                with d._lock:
                    if d.mode == "demo":
                        d.mode = "idle"
                    if limp:
                        d.armed = False
                        d.status = st
                try:
                    from event_log import emit
                    emit("safe_zero",
                         "done" if result.get("ok") else st,
                         data={k: result.get(k)
                               for k in ("ok", "limp", "stage", "peak_a",
                                         "peak_joint")
                               if k in result})
                except Exception:
                    pass
                self._set_activity(
                    "limp" if (limp or not d.armed) else "armed", st)

        self._demo_thread = threading.Thread(target=_worker, daemon=True)
        self._demo_thread.start()
        return {
            "ok": True, "started": True,
            "plan": {"stages": [{"label": s["label"],
                                 "seconds": s["seconds"]}
                                for s in plan["stages"]],
                     "total_s": plan.get("total_s"),
                     "notes": plan.get("notes") or []},
            "demo": self.demo_state(),
            "robot": self.robot_state(),
        }

