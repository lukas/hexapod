"""BenchAPI route group: demo/dance catalog + run_demo/estop/stop + shared stand-pose and walk-ready helpers.

Moved verbatim from bench_api.py (2026-08-29 component-boundaries split);
mixed into ``bench_api.BenchAPI``. Route/JSON shapes are unchanged.
"""
from __future__ import annotations

from .common import *  # noqa: F401,F403


class DemosApi:
    def list_demos(self) -> list[dict]:
        try:
            from inplace_demos import DEMOS
        except ImportError:
            return []
        try:
            from inplace_demos import (STAND_STREAM_DEMOS,
                                       STREAM_POSE_FACTORIES)
            stand_stream = set(STAND_STREAM_DEMOS)
            live_names = set(STREAM_POSE_FACTORIES) | {"breathe"}
        except ImportError:
            stand_stream, live_names = set(), set()
        out = []
        for n, (t, _) in DEMOS.items():
            # breathe+ kept as alias; UI uses size slider on breathe.
            if n == "breathe+":
                continue
            if n in AIR_DEMO_NAMES:
                group = "air"
            elif n.startswith("quad"):
                group = "quad"      # own web tab (tip-back 4-leg walk)
            elif n in stand_stream:
                group = "stand"
            elif n.startswith("walk"):
                group = "walk"
            else:
                group = "plant"
            out.append({
                "name": n,
                "title": t,
                "air": n in AIR_DEMO_NAMES,
                "group": group,
                "live_speed": n in live_names,
                "has_size": n in ("breathe", "breathe_v", "dance",
                              "dance_walk"),
            })
        builtin = {d["name"] for d in out}
        try:
            scripts = self.list_dance_scripts()
        except AttributeError:
            # The laptop hub calls this unbound with a stub self just to
            # read the built-in catalog — no uploaded-script store there.
            scripts = []
        for meta in scripts:
            if meta["name"] in builtin:
                continue
            out.append({
                "name": meta["name"],
                "title": meta.get("title") or meta["name"],
                "air": True,            # scripts start AND end at sit zero
                "group": "uploaded",
                "live_speed": True,
                "has_size": False,
                "uploaded": True,
                "stands": bool(meta.get("stands")),
                "seconds": meta.get("seconds"),
            })
        return out

    # -- uploaded dance scripts (dances as data) -----------------------------
    # Portable JSON choreography (motor_setup/dance_script.py): baked from
    # any dance runner, uploaded over HTTP, replayed through the same
    # guarded primitives.  Stored OUTSIDE the deploy tree so code pushes
    # never wipe them; the same file can be pushed to any robot.

    DANCE_DIR = Path.home() / ".hexapod_dances"

    def _dance_path(self, name: str) -> Path | None:
        from hexapod_core import dance_script as DS
        if not isinstance(name, str) or not DS.NAME_RE.match(name):
            return None
        return self.DANCE_DIR / f"{name}.json"

    def list_dance_scripts(self) -> list[dict]:
        out = []
        try:
            paths = sorted(self.DANCE_DIR.glob("*.json"))
        except OSError:
            return out
        for p in paths:
            try:
                s = json.loads(p.read_text())
                out.append({"name": s["name"],
                            "title": s.get("title") or s["name"],
                            "stands": bool(s.get("stands")),
                            "seconds": s.get("seconds"),
                            "acts": len(s.get("acts") or []),
                            "bytes": p.stat().st_size,
                            "baked_from": s.get("baked_from")})
            except (OSError, ValueError, KeyError):
                continue
        return out

    def get_dance_script(self, name: str) -> dict | None:
        p = self._dance_path(name)
        if p is None or not p.is_file():
            return None
        try:
            return json.loads(p.read_text())
        except (OSError, ValueError):
            return None

    def save_dance_script(self, script) -> dict:
        from hexapod_core import dance_script as DS
        errs, stats = DS.validate_script(script)
        if errs:
            return {"ok": False, "error": "; ".join(errs[:5])}
        name = script["name"]
        try:
            from inplace_demos import DEMOS
            if name in DEMOS:
                return {"ok": False,
                        "error": f"{name!r} is a built-in demo name"}
        except ImportError:
            pass
        p = self._dance_path(name)
        try:
            self.DANCE_DIR.mkdir(parents=True, exist_ok=True)
            tmp = p.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(script))
            tmp.replace(p)
        except OSError as e:
            return {"ok": False, "error": f"save failed: {e}"}
        return {"ok": True, "name": name, "stats": stats,
                "bytes": p.stat().st_size}

    def delete_dance_script(self, name: str) -> dict:
        p = self._dance_path(name)
        if p is None or not p.is_file():
            return {"ok": False, "error": f"no uploaded dance {name!r}"}
        try:
            p.unlink()
        except OSError as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True, "deleted": name}

    def set_demo_speed(self, speed) -> dict:
        """LIVE tempo (web slider): takes effect on the running demo."""
        try:
            v = float(speed)
        except (TypeError, ValueError):
            return {"ok": False, "error": "bad speed"}
        v = max(0.25, min(3.0, v))
        with self._lock:
            self._demo_speed_live = v
            running = bool(self._demo_thread and self._demo_thread.is_alive())
            if running:
                self._demo_params = {**self._demo_params, "speed_live": v}
        return {"ok": True, "speed": v, "running": running,
                "demo": self.demo_state()}

    # -- actions -------------------------------------------------------------
    def wiggle(self, joint: int, amp: float = 8.0) -> dict:
        if not (0 <= joint < N_JOINTS):
            return {"ok": False, "error": "bad joint"}
        if self.drive.dry_run:
            return {"ok": True, "dry_run": True}
        if not self.drive.bus:
            return {"ok": False, "error": "no bus"}
        if self._demo_thread and self._demo_thread.is_alive():
            return {"ok": False, "error": "stop the demo first"}
        msg = self.drive.handle(f"Q {joint} {amp}")
        if msg == "need ARM":
            return {"ok": False, "error": "need ARM"}
        return {"ok": True, "result": msg, "joint": joint, "amp": amp}

    def _preempt_demo_thread(self, *, reason: str = "stop",
                             timeout: float = 5.0) -> bool:
        """Abort any running demo/zero worker. True if bus is free afterward."""
        t = self._demo_thread
        if t is None or not t.is_alive():
            return True
        self._demo_abort.set()
        with self._lock:
            self._demo_status = "stopping"
        self._set_activity("stopping", reason)
        t.join(timeout=float(timeout))
        still = bool(self._demo_thread and self._demo_thread.is_alive())
        if still:
            with self._lock:
                self._demo_status = "aborted"
                self._activity = "idle"
                self._activity_detail = "stop timed out — use E-STOP if stuck"
            return False
        with self.drive._lock:
            if self.drive.mode == "demo":
                self.drive.mode = "idle"
        return True

    def _running_calibration_name(self) -> str | None:
        t = self._demo_thread
        if t is None or not t.is_alive():
            return None
        with self._lock:
            name = self._demo_name or ""
        if name.startswith("calibrate:"):
            return name
        return None

    def _calibration_busy_response(self, action: str) -> dict:
        name = self._running_calibration_name() or "calibrate"
        bits = name.split(":")
        mode = bits[1] if len(bits) > 1 and bits[1] else "checkup"
        return {
            "ok": False,
            "busy": "calibration",
            "error": (
                f"calibration {mode} is running — press Stop in Calibrate "
                f"before {action}"
            ),
            "calibrate": self.calibrate_state(),
            "robot": self.robot_state(),
        }

    def stop_demo(self) -> dict:
        """Abort the demo thread. Do NOT touch the bus here — concurrent
        SyncWrite + HOLD was hanging the MCU bridge and leaving status at
        ``stopping`` forever."""
        prev = self._demo_name or ""
        ok = self._preempt_demo_thread(reason=prev or "stop", timeout=4.0)
        try:
            from inplace_demos import QUAD_STREAM_DEMOS
            if prev in QUAD_STREAM_DEMOS:
                # Generic abort is not a stable quad stop: it may catch the
                # gait mid-step. The Quad tab uses quad_hold for a deliberate
                # settle; after a generic stop require a fresh rear-up.
                self._quad_reared = False
        except ImportError:
            pass
        with self._lock:
            if self._demo_status in ("stopping",):
                self._demo_status = "aborted"
            if ok and self._activity == "stopping":
                self._activity = "armed" if self.drive.armed else "limp"
                self._activity_detail = (
                    "quad stop aborted; check robot"
                    if prev.startswith("quad_") else "aborted")
        return {"ok": True, "demo": self.demo_state(), "robot": self.robot_state()}

    def estop(self) -> dict:
        """TRUE emergency stop: kill the demo/RL worker AND limp, in order.

        Root cause of the 2026-08-18 scare: the web E-STOP sent a bare
        ``X`` to the DriveController, which limps the bus but never tells
        the demo thread — and every demo primitive re-enables torque at
        its next write, so the dance shrugged the limp off and kept going.
        This method is what ``/cmd X`` now routes through:

        1. abort event + gen bump — the worker exits at its next
           checkpoint (≤ ~0.1 s) without running outro glides;
        2. limp NOW (torque off) so the robot stops moving immediately;
        3. wait briefly for the worker to die (its bail path may write
           one last hold);
        4. limp AGAIN so the guaranteed final state is torque-off,
           no matter what the dying worker wrote in between.
        """
        self._demo_abort.set()
        self._quad_reared = False
        with self._lock:
            self._demo_gen += 1
            if self._demo_thread and self._demo_thread.is_alive():
                self._demo_status = "estopped"

        def _limp() -> None:
            try:
                self.drive.handle("X")
            except Exception:
                pass

        _limp()
        t = self._demo_thread
        joined = True
        if t is not None and t.is_alive():
            t.join(timeout=3.0)
            joined = not t.is_alive()
            _limp()
            if not joined:
                # Worker outlived the join window — keep a watcher that
                # limps once more the moment it finally dies, so a late
                # bail write can never leave torque on.
                def _watch(th: threading.Thread = t) -> None:
                    th.join()
                    _limp()
                threading.Thread(target=_watch, daemon=True).start()
        try:
            from event_log import emit
            emit("cmd", "EMERGENCY STOP (estop)", src="bench",
                 data={"worker_exited": joined})
        except Exception:
            pass
        self._set_activity(
            "limp",
            "EMERGENCY STOP" if joined else
            "EMERGENCY STOP — worker still exiting (bus limp; a watcher "
            "re-limps the instant it dies)")
        return {"ok": True, "worker_exited": joined,
                "demo": self.demo_state(), "robot": self.robot_state()}

    def run_demo(self, name: str, *, speed: float = 1.0,
                 size: float = 1.0, rate: float | None = None,
                 torque: int | None = None, softness: float = 1.0,
                 seconds: float | None = None,
                 motion_log: bool | None = None) -> dict:
        try:
            from inplace_demos import (
                DEMOS, QUAD_BALANCE_TRIM_DEMOS,
                QUAD_BLOCKED_HARDWARE_DEMOS, QUAD_DOWN_DEMOS,
                QUAD_REAR_DEMOS, QUAD_REQUIRES_REAR, QUAD_REARED_END_DEMOS,
                QUAD_STREAM_DEMOS, run_demo)
        except ImportError as e:
            return {"ok": False, "error": f"inplace_demos missing: {e}"}
        try:
            from inplace_demos import STREAM_POSE_FACTORIES
            streamable = set(STREAM_POSE_FACTORIES)
        except ImportError:
            streamable = set()
        # Alias: breathe+ → breathe at size 2.
        if name == "breathe+":
            name = "breathe"
            size = max(float(size), 2.0)
        script = None
        if name not in DEMOS:
            script = self.get_dance_script(name)
            if script is None:
                return {"ok": False, "error": f"unknown demo {name!r}",
                        "demos": [n for n in DEMOS if n != "breathe+"]}
        if name in QUAD_BLOCKED_HARDWARE_DEMOS:
            return {"ok": False,
                    "error": (
                        "aggressive quad walk/trot is blocked on hardware "
                        "after the forward fall; use pitched walk or "
                        "simulate aggressive in MuJoCo only"),
                    "demo": self.demo_state(), "robot": self.robot_state()}
        if self.drive.dry_run:
            return {"ok": False, "error": "dry-run — no bus"}
        if not self.drive.bus:
            return {"ok": False, "error": "no bus"}
        if self._running_calibration_name():
            return self._calibration_busy_response(f"starting {name}")

        def _f(val, default, lo, hi):
            try:
                x = float(val)
            except (TypeError, ValueError):
                x = default
            return max(lo, min(hi, x))

        speed = _f(speed, 1.0, 0.25, 3.0)
        size = _f(size, 1.0, 0.5, 3.0)
        softness = _f(softness, 1.0, 0.5, 3.0)
        if rate is not None:
            rate = _f(rate, 0.28, 0.08, 0.60)
        # ``seconds`` is a duration only for demos that take one (air +
        # streamed); planted shows/glides keep their choreographed times.
        duration_ok = name in AIR_DEMO_NAMES or name in streamable
        if seconds is not None:
            seconds = _f(seconds, 60.0, 5.0, 300.0) if duration_ok else None
        if torque is not None:
            try:
                torque = int(round(float(torque)))
            except (TypeError, ValueError):
                torque = None
            if torque is not None:
                torque = max(150, min(1000, torque))
        if motion_log is None:
            motion_log = _env_truthy("HEXAPOD_MOTION_LOG", False)
        else:
            motion_log = bool(motion_log)

        quad_any = name in QUAD_STREAM_DEMOS
        quad_balance = name in QUAD_BALANCE_TRIM_DEMOS
        quad_requires_rear = name in QUAD_REQUIRES_REAR
        quad_current = bool(
            self._demo_thread and self._demo_thread.is_alive()
            and self._demo_name in QUAD_STREAM_DEMOS)
        if quad_requires_rear and not (self._quad_reared or quad_current):
            return {"ok": False,
                    "error": "quad: rear up first, then walk/trot/down",
                    "demo": self.demo_state(), "robot": self.robot_state()}

        # Uploaded scripts start AND end at sit zero (like air demos).
        # Quad rear-up is the entry phase, so it acquires stand first; the
        # later split-quad commands consume the held reared stance directly.
        home = ("sit" if (name in AIR_DEMO_NAMES or script is not None)
                else "quad" if quad_requires_rear
                else "stand")
        quad_tuck_home = name in QUAD_REAR_DEMOS
        switched_from = None
        if self._demo_thread and self._demo_thread.is_alive():
            switched_from = self._demo_name
            if not self._preempt_demo_thread(
                    reason=f"{switched_from or '?'} → {name}", timeout=5.0):
                return {"ok": False,
                        "error": "previous demo did not stop — try Stop / E-STOP",
                        "demo": self.demo_state(), "robot": self.robot_state()}

        params = {"speed": speed,
                  "home": ("tuck stand" if quad_tuck_home else home)}
        if seconds is not None:
            params["seconds"] = seconds
        if name in ("breathe", "breathe_v", "dance", "dance_walk"):
            params.update({"size": size, "softness": softness})
            if rate is not None:
                params["rate"] = rate
        if torque is not None and name in AIR_DEMO_NAMES:
            params["torque"] = torque
        if motion_log:
            params["motion_log"] = True
        if quad_balance:
            params["balance_trim"] = True
        if switched_from:
            params["switched_from"] = switched_from

        self._demo_gen += 1
        gen = self._demo_gen
        self._demo_abort.clear()
        with self._lock:
            self._demo_name = name
            self._demo_status = "starting"
            self._demo_params = dict(params)
            self._demo_telemetry = None
            # Live tempo starts at the requested speed; /api/demo/speed
            # can change it while the demo runs.
            self._demo_speed_live = speed
        bits = [f"{name} @ {speed:.2f}×"]
        if switched_from:
            bits.insert(0, f"switch←{switched_from}")
        if name in ("breathe", "breathe_v", "dance", "dance_walk"):
            bits.append(f"size {size:.2f}×")
            if rate is not None:
                bits.append(f"{rate:.2f} Hz")
            bits.append(f"soft {softness:.2f}×")
        if torque is not None:
            bits.append(f"τ {torque}")
        if quad_balance:
            bits.append("balance trim")
        detail = " ".join(bits)
        self._set_activity("demo", detail)

        def _worker():
            d = self.drive
            with d._lock:
                d.mode = "demo"
                d.gait.stop()
                if not d.armed:
                    d._torque_all(True)
                    d.armed = True
            try:
                # Always home first (sit for air, stand for planted) so a
                # mid-demo switch — or starting from the wrong pose — just
                # works. 08-11 directive: acquire the start SAFELY
                # (collision-aware zero, validated step stand-up); if
                # that fails the robot is already stopped/limped and the
                # demo must NOT run.
                if home == "quad":
                    with self._lock:
                        self._demo_status = "using reared stance"
                    self._set_activity("demo", f"reared → {name}")
                    res_home = {"ok": True}
                else:
                    home_msg = "tuck stand" if quad_tuck_home else home
                    with self._lock:
                        self._demo_status = f"homing {home_msg}"
                    self._set_activity("zeroing",
                                       f"{home_msg} → {name}")

                    def _home_prog(p: dict) -> None:
                        with self._lock:
                            self._demo_status = str(p.get("msg")
                                                    or f"homing {home_msg}")

                    start_kind = ("zero" if home == "sit"
                                  else "stand_tuck" if quad_tuck_home
                                  else "stand")
                    res_home = self._acquire_start(
                        start_kind, gen=gen, on_progress=_home_prog)
                if gen != self._demo_gen:
                    return
                if self._demo_abort.is_set():
                    with self._lock:
                        self._demo_status = "aborted"
                    return
                if not res_home.get("ok"):
                    with self._lock:
                        self._demo_status = (
                            "error: start pose not reached — "
                            + str(res_home.get("error") or "aborted"))
                    return

                with self._lock:
                    self._demo_status = f"running @ {speed:.2f}×"
                self._set_activity("demo", detail)
                # Own the MCU link for the whole motion. Without this the
                # TFT job-panel repaint (~1.5 s serial hold every 1.6 s)
                # starved the 20 Hz demo stream to ~2 Hz — measured
                # 08-17: stand_wave turned into rare giant steps and
                # tipped the robot. Same bug rl_policy_move fixed 08-10.
                self._bus_hot_begin()
                try:
                    from event_log import emit
                    emit("demo", f"{name} start", src="bench", data=params)
                except Exception:
                    pass
                # Full cmd-vs-encoder CSV is diagnostic mode only. It reads
                # feedback during motion, so the reliable default is the
                # lightweight async event log plus start/finish breadcrumbs.
                log_path = None
                if motion_log:
                    log_dir = lc_dir() / "logs"
                    log_dir.mkdir(parents=True, exist_ok=True)
                    stamp = time.strftime("%Y%m%d_%H%M%S")
                    log_path = log_dir / f"demo_{name}_{stamp}.csv"
                    with self._lock:
                        self._demo_params = {
                            **dict(self._demo_params),
                            "log": log_path.name,
                        }
                def _live_status(msg: str) -> None:
                    if gen != self._demo_gen:
                        return
                    with self._lock:
                        self._demo_status = str(msg)

                if script is not None:
                    from hexapod_core import dance_script as DS
                    status = DS.run_dance_script(
                        d.bus, script,
                        abort_check=self._demo_abort.is_set,
                        speed=speed,
                        speed_fn=lambda: self._demo_speed_live,
                        status_cb=_live_status,
                        standup_fn=self._step_standup_fn(
                            gen=gen, speed=speed),
                        log_path=log_path)
                elif name == "dance_walk":
                    status = self._run_dance_walk(
                        gen=gen, speed=speed, size=size,
                        softness=softness, torque=torque,
                        status_cb=_live_status, log_path=log_path)
                else:
                    extra = {}
                    if name in ("dance", "dance_swarm_stand",
                                "dance_steeple", "dance_wild",
                                "dance_encore", "dance_swarm_encore",
                                "dance_swarm_up"):
                        extra["standup_fn"] = self._step_standup_fn(
                            gen=gen, speed=speed)
                    if quad_requires_rear:
                        extra["quad_reared"] = True
                    status = run_demo(
                        d.bus, name,
                        speed=speed,
                        seconds=seconds,
                        size=size,
                        rate=rate,
                        torque=torque,
                        softness=softness,
                        abort_check=self._demo_abort.is_set,
                        speed_fn=lambda: self._demo_speed_live,
                        status_cb=_live_status,
                        log_path=log_path,
                        **extra,
                    )
                telem = None
                if log_path is not None:
                    summary_path = log_path.with_name(
                        log_path.stem + "_summary.json")
                    if summary_path.is_file():
                        try:
                            telem = json.loads(summary_path.read_text())
                        except (OSError, ValueError):
                            telem = None
                    if telem is None and log_path.is_file():
                        telem = {
                            "ok": True,
                            "log": str(log_path),
                            "log_name": log_path.name,
                            "hint": "CSV written; summary pending",
                        }
                if gen != self._demo_gen:
                    return
                with self._lock:
                    self._demo_telemetry = telem
                    if self._demo_abort.is_set():
                        self._demo_status = "aborted"
                    else:
                        self._demo_status = status or "done"
                        if telem and telem.get("counts"):
                            c = telem["counts"]
                            self._demo_status = (
                                f"{status or 'done'} · "
                                f"{c.get('green', 0)}g/"
                                f"{c.get('yellow', 0)}y/"
                                f"{c.get('red', 0)}r"
                            )
                try:
                    from event_log import emit
                    emit("demo", f"{name} {status or 'done'}", src="bench",
                         data={
                             "name": name,
                             "status": status or "done",
                             "motion_log": bool(motion_log),
                             "log": log_path.name if log_path else None,
                         })
                except Exception:
                    pass
            except Exception as e:
                if gen != self._demo_gen:
                    return
                with self._lock:
                    self._demo_status = f"error: {e}"
            finally:
                self._bus_hot_end()
                if gen != self._demo_gen:
                    return
                with self._lock:
                    st = self._demo_status
                if st == "stopping":
                    st = "aborted"
                    with self._lock:
                        self._demo_status = st
                # Planted / rise demos finish at stand zero — keep re-holding.
                # Uploaded scripts end at sit zero like air demos. Split quad
                # mode keeps the reared pose until the explicit quad_down.
                if st == "done" and name in QUAD_REARED_END_DEMOS:
                    self._quad_reared = True
                    with d._lock:
                        if d.mode == "demo":
                            d.mode = "idle"
                        d.status = "quad reared hold"
                    self._set_activity(
                        "armed" if d.armed else "limp", "quad reared hold")
                elif st == "aborted" and quad_any:
                    self._quad_reared = False
                    with d._lock:
                        if d.mode == "demo":
                            d.mode = "idle"
                    self._set_activity(
                        "armed" if d.armed else "limp",
                        "quad aborted; check robot before next quad")
                elif st == "done" and name in QUAD_DOWN_DEMOS:
                    self._quad_reared = False
                    self._enter_stand_hold()
                    self._set_activity("armed", "quad down · at stand zero")
                elif quad_any:
                    self._quad_reared = False
                    with d._lock:
                        if d.mode == "demo":
                            d.mode = "idle"
                    self._set_activity(
                        "armed" if d.armed else "limp",
                        st if st else "quad stopped; check robot")
                elif (st == "done" and name not in AIR_DEMO_NAMES
                        and script is None):
                    self._quad_reared = False
                    self._enter_stand_hold()
                else:
                    if name in AIR_DEMO_NAMES or script is not None:
                        self._quad_reared = False
                    with d._lock:
                        if d.mode == "demo":
                            d.mode = "idle"
                    self._set_activity(
                        "armed" if d.armed else "limp",
                        st if st in ("done", "aborted", "skipped") else st)

        self._demo_thread = threading.Thread(target=_worker, daemon=True)
        self._demo_thread.start()
        return {"ok": True, "params": params, "home": home,
                "switched": bool(switched_from),
                "switched_from": switched_from,
                "demo": self.demo_state(), "robot": self.robot_state()}

    # Victory lap (operator 08-18): horse-prance OUT (open-loop tripod —
    # quick cadence, high knees), ABOUT-FACE (sim-calibrated 180° turn),
    # horse-prance HOME. Out and home share the same gait + duration, so
    # the return distance matches the out leg by symmetry regardless of
    # floor slip — no distance model needed. The old RL moonwalk +
    # pirouette finale was retired (turning for no reason read as
    # aimless; the moonwalk needed a slip-dependent distance guess).

    def _step_standup_fn(self, *, gen: int, speed: float):
        """Bound STEP stand-up for the dance's act IV (inline, same gen).

        The dance's own tempo never SLOWS the stand-up below 1x (the
        experiments-tab pacing the operator liked, 08-18); speeding
        the dance up speeds the stand-up too.
        """
        def fn(mode: str = "step") -> tuple[bool, str]:
            # Uploaded dance scripts may name another BAKED stand-up
            # lab mode; anything unknown refuses rather than improvises.
            try:
                known = set(self._load_standup()["modes"])
            except Exception:
                known = {"step"}
            if mode not in known:
                return False, f"unknown stand-up mode {mode!r}"
            res = self.standup(mode=mode,
                               speed=max(1.0, float(speed)),
                               direction="up", torque=700,
                               sync_gen=gen)
            return bool(res.get("ok")), str(res.get("error") or "")
        return fn

    def _run_dance_walk(self, *, gen: int, speed: float, size: float,
                        softness: float, torque: int | None,
                        status_cb, log_path: Path) -> str:
        """dance acts I–V → tripod victory lap → dance act VI.

        Runs inside the demo worker thread (slot already claimed, sit
        homing already done). A refused lap (tripod gait unavailable)
        is never fatal — the outro still plays so the robot always
        ends asleep at sit zero. A SAFETY-TRIPPED lap is
        fatal: the robot is limped and stays limped (no blind outro
        from an unknown pose — 2026-08-06 lesson).
        """
        from inplace_demos import run_dance_demo

        d = self.drive
        st = run_dance_demo(
            d.bus, part="show", speed=speed, size=size, softness=softness,
            torque=torque, abort_check=self._demo_abort.is_set,
            status_cb=status_cb, log_path=log_path,
            standup_fn=self._step_standup_fn(gen=gen, speed=speed))
        if st != "planted":
            return st

        lap_err = self._victory_lap(status_cb=status_cb)
        if self._demo_abort.is_set() or lap_err == "aborted":
            return "aborted"
        if lap_err:
            status_cb(f"lap skipped ({lap_err}) — descending anyway")

        outro_log = log_path.with_name(log_path.stem + "_outro.csv")
        return run_dance_demo(
            d.bus, part="outro", speed=speed, size=size, softness=softness,
            torque=torque, abort_check=self._demo_abort.is_set,
            status_cb=status_cb, log_path=outro_log)

    def _victory_lap(self, *, status_cb) -> str | None:
        """Prance out → about-face (180°) → prance home.

        Returns an error string, or None on success. All three phases
        are the same open-loop tripod, so if the gait is unavailable
        the whole lap is skipped in one place; if a later phase
        refuses, the lap stops there (never turn/return blindly).
        """
        d = self.drive
        try:
            from inplace_demos import run_dance_prance
        except ImportError as e:
            return f"inplace_demos missing: {e}"

        for phase in ("out", "halfturn", "home"):
            st = run_dance_prance(d.bus, phase,
                                  abort_check=self._demo_abort.is_set,
                                  status_cb=status_cb)
            if st == "aborted" or self._demo_abort.is_set():
                return "aborted"
            if st != "done":
                return f"lap {phase} unavailable ({st})"
        return None

    def _delta_vs_present(self, goal: list[float]
                          ) -> tuple[float | None, int | None]:
        """Like drive._max_delta_vs_present, but None-aware.

        The first MCU round-trip after a service restart can time out
        WHOLESALE (TFT reinit holds the link); drive's helper then
        compares against nothing and reports worst=0.0, which made
        pose gates pick wrong paths and silently defeated the delta
        guard (08-11: a standing robot 'passed' the belly-down
        guard). Retries once; returns (None, None) when the bus
        really has no readings — callers must treat that as UNKNOWN,
        not 'at the goal'."""
        pairs: list = []
        for attempt in range(2):
            with self.drive._lock:
                present = self.drive._read_present_pose()
            pairs = [(j, p) for j, p in enumerate(present)
                     if p is not None]
            if len(pairs) >= max(1, len(goal) - 4):
                worst, wj = 0.0, None
                for j, p in pairs:
                    dd = abs(float(goal[j]) - float(p))
                    if dd > worst:
                        worst, wj = dd, j
                return worst, wj
            time.sleep(0.4)
        return None, None

    @staticmethod
    def _pose_delta(present: list[float], goal: list[float]
                    ) -> float | None:
        if len(present) != N_JOINTS or len(goal) != N_JOINTS:
            return None
        try:
            return max(abs(float(a) - float(b))
                       for a, b in zip(present, goal))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _median(vals: list[float]) -> float:
        vals = sorted(float(v) for v in vals)
        n = len(vals)
        mid = n // 2
        return vals[mid] if n % 2 else (vals[mid - 1] + vals[mid]) / 2.0

    def _normal_standing_pose(self, present: list[float], *,
                              tilt_deg: float | None = None,
                              pinned: dict | None = None) -> dict | None:
        """Return a normal-upright verdict, or ``None`` for recovery poses.

        Motion routing rule, intentionally documented here because it is easy
        to forget:

        * Normal descent from a good upright stance uses baked STEP-down.
          This includes either the sim walk-ready stance or STEP's own final
          high-knee stance.
        * Safe zero is reserved for tangled, tipped, unknown, or already-low
          poses where the collision-aware planner is the right tool.
        * A stand command issued while already upright does not run another
          rise. It re-holds/adjusts the sim walk-ready stance instead.

        The classifier is deliberately conservative. Belly-zero can be only
        ~28 deg from the default plant knee, so pose delta alone would produce
        false "standing" hits; the median hip/knee shape gate keeps zero and
        folded/tangled postures on the recovery path.
        """
        if pinned and pinned.get("pinned"):
            return None
        if tilt_deg is not None and abs(float(tilt_deg)) > 20.0:
            return None
        if len(present) != N_JOINTS:
            return None
        try:
            hips = [float(present[3 * leg + 1]) for leg in range(6)]
            knees = [float(present[3 * leg + 2]) for leg in range(6)]
        except (TypeError, ValueError):
            return None
        hip_med = self._median(hips)
        knee_med = self._median(knees)
        if hip_med < 5.0 or knee_med < 12.0:
            return None

        refs: list[tuple[str, list[float], float]] = []
        try:
            from rl_walk_start import walk_start_pose_degrees
            refs.append(("sim_walk_start", [float(v) for v in
                                            walk_start_pose_degrees()], 25.0))
        except Exception:
            pass
        try:
            step = self._load_standup()["modes"]["step"]["keyframes"]
            refs.append(("step", [float(v) for v in
                                  step[-1]["q_deg"]], 35.0))
        except Exception:
            pass

        best: dict | None = None
        for name, goal, tol in refs:
            delta = self._pose_delta(present, goal)
            if delta is None or delta > tol:
                continue
            verdict = {
                "kind": name,
                "max_delta_deg": round(delta, 1),
                "tol_deg": tol,
                "hip_med_deg": round(hip_med, 1),
                "knee_med_deg": round(knee_med, 1),
            }
            if tilt_deg is not None:
                verdict["tilt_deg"] = round(float(tilt_deg), 1)
            if best is None or delta < float(best["max_delta_deg"]):
                best = verdict
        return best

    def _settle_stand_pose_sync(self, *, abort_check,
                                on_progress=None) -> dict:
        """Legacy tuck-stand adjust path for non-RL planted stand helpers."""
        try:
            from inplace_demos import CurrentPeakTracker, go_to_stand_pose
        except ImportError as e:
            return {"ok": False, "error": str(e)}

        def _prog(msg: str) -> None:
            if not on_progress:
                return
            try:
                on_progress({"msg": msg})
            except Exception:
                pass

        _prog("standing already: adjusting legs / plant height…")
        result: dict = {}
        tracker = CurrentPeakTracker()
        try:
            ok = go_to_stand_pose(
                self.drive.bus, abort_check=abort_check,
                seconds=4.5, current_tracker=tracker, result=result)
        except Exception as e:
            return {"ok": False,
                    "error": f"could not adjust standing pose: {e}"}
        if not ok:
            why = (result.get("error")
                   or ("aborted" if result.get("aborted") else "failed"))
            return {"ok": False, "error": f"standing adjust failed: {why}"}
        return {"ok": True, "settled_stand": True,
                "stand_check": result}

    def _step_to_rl_walk_ready_start_sync(self, *, abort_check,
                                          on_progress=None) -> dict:
        """Step or settle from the current upright pose to sim walk start.

        This intentionally ignores plant_pose.json. The RL walk policy start
        should match the simulator reset pose, while plant_pose.json is only a
        mutable calibration/contact artifact.
        """
        try:
            from inplace_demos import (
                CurrentPeakTracker, _enable_torque, _live_robot_ids,
                _set_torque_limit, _write_pose,
            )
            from rl_walk_start import walk_start_pose_degrees
            from hexapod_core.walk_ready_transition import build_tripod_plant_transition
        except ImportError as e:
            return {"ok": False, "error": str(e)}

        bus = self.drive.bus
        if bus is None:
            return {"ok": False, "error": "no bus"}
        present, missing = self._present_pose18()
        if missing:
            return {"ok": False,
                    "error": f"missing joints during walk-ready start: {missing}"}
        try:
            target = [float(v) for v in walk_start_pose_degrees()]
            delta = self._pose_delta(present, target)
            frames = ([] if delta is not None and delta <= 5.0
                      else build_tripod_plant_transition(present, target))
        except Exception as e:
            return {"ok": False,
                    "error": f"could not plan walk-ready start step: {e}"}

        def _prog(msg: str, **extra) -> None:
            if not on_progress:
                return
            try:
                on_progress({"msg": msg, **extra})
            except Exception:
                pass

        live = _live_robot_ids(bus)
        if len(live) < N_JOINTS:
            return {"ok": False,
                    "error": (f"only {len(live)}/18 servos live during "
                              "walk-ready start")}
        tracker = CurrentPeakTracker()
        _set_torque_limit(bus, live, 1000)
        _enable_torque(bus, live)
        started = time.monotonic()
        if not frames:
            _prog("walk-ready start: settle", phase="settle", stage=0,
                  frame=1, of=1, legs=[])
            try:
                _write_pose(bus, target, live, speed=180, acc=20)
            except Exception as e:
                return {"ok": False,
                        "error": f"walk-ready start write failed: {e}"}
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline:
                if abort_check():
                    return {"ok": False, "aborted": True,
                            "error": "walk-ready start aborted"}
                time.sleep(min(0.08, max(0.0, deadline - time.monotonic())))
                try:
                    tracker.sample(bus, live)
                except Exception:
                    pass
                if tracker.peak_a > 4.0:
                    return {"ok": False,
                            "error": (f"walk-ready start current trip "
                                      f"{tracker.peak_a:.2f} A on joint "
                                      f"{tracker.peak_joint}"),
                            "peak_a": round(tracker.peak_a, 2),
                            "peak_joint": tracker.peak_joint}
            try:
                _emit_servo_fb("walk-ready start: settle", tracker,
                               target=target)
            except Exception:
                pass
        for idx, frame in enumerate(frames, 1):
            if abort_check():
                return {"ok": False, "aborted": True,
                        "error": "walk-ready start aborted"}
            legs = ",".join(str(x) for x in frame.legs)
            label = (f"walk-ready start: {frame.phase}"
                     + (f" legs {legs}" if legs else ""))
            _prog(label, phase=frame.phase, stage=frame.stage,
                  frame=idx, of=len(frames), legs=list(frame.legs))
            speed = 360 if frame.phase == "lift" else 260
            acc = 45 if frame.phase == "lift" else 35
            if frame.phase == "swing":
                speed, acc = 320, 40
            if frame.phase == "support":
                speed, acc = 180, 25
            if frame.phase == "settle":
                speed, acc = 180, 20
            try:
                _write_pose(bus, frame.q_deg, live, speed=speed, acc=acc)
            except Exception as e:
                return {"ok": False,
                        "error": f"walk-ready start write failed: {e}"}
            deadline = time.monotonic() + max(0.05, float(frame.seconds))
            while time.monotonic() < deadline:
                if abort_check():
                    return {"ok": False, "aborted": True,
                            "error": "walk-ready start aborted"}
                time.sleep(min(0.08, max(0.0, deadline - time.monotonic())))
                try:
                    tracker.sample(bus, live)
                except Exception:
                    pass
                if tracker.peak_a > 4.0:
                    return {"ok": False,
                            "error": (f"walk-ready start current trip "
                                      f"{tracker.peak_a:.2f} A on joint "
                                      f"{tracker.peak_joint}"),
                            "peak_a": round(tracker.peak_a, 2),
                            "peak_joint": tracker.peak_joint}
            try:
                _emit_servo_fb(label, tracker, target=frame.q_deg)
            except Exception:
                pass

        # Final re-hold is the same target every leg already has; it refreshes
        # the servo target without introducing another stance change.
        try:
            _write_pose(bus, target, live, speed=180, acc=20)
        except Exception:
            pass
        time.sleep(0.3)
        verify_pose, verify_missing = self._present_pose18()
        if verify_missing and getattr(tracker, "last_fb", None):
            for fb in tracker.last_fb:
                try:
                    j = int(fb["joint"])
                    if 0 <= j < N_JOINTS:
                        verify_pose[j] = float(fb["deg"])
                except (KeyError, TypeError, ValueError):
                    pass
            verify_missing = [j for j, v in enumerate(verify_pose)
                              if v is None]
        worst, worst_j = 0.0, None
        for j, val in enumerate(verify_pose):
            if val is None:
                continue
            err = abs(float(target[j]) - float(val))
            if err >= worst:
                worst, worst_j = err, j
        check = {
            "ok": not verify_missing and worst <= 5.0,
            "max_err_deg": round(worst, 2),
            "worst_joint": worst_j,
            "worst_name": (joint_label(worst_j, self.names)
                           if worst_j is not None else None),
            "tol_deg": 5.0,
            "missing_joints": verify_missing,
            "goal": "sim_walk_start",
        }
        if not check["ok"]:
            if verify_missing:
                check["error"] = (
                    "walk-ready feedback missing joints "
                    + ",".join(str(j) for j in verify_missing))
            else:
                check["error"] = (
                    f"walk-ready pose is {worst:.1f}° off on "
                    f"{check['worst_name']} (need ≤5°)")
        result = {
            "ok": bool(check.get("ok")),
            "mode": "rl_walk_ready_start",
            "frames": len(frames) if frames else 1,
            "duration_s": round(time.monotonic() - started, 2),
            "peak_a": round(tracker.peak_a, 2),
            "peak_joint": tracker.peak_joint,
            "stand_check": check,
        }
        if not result["ok"]:
            result["error"] = ("walk-ready start failed verification: "
                               + str(check.get("error") or check))
        return result

