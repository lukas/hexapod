"""BenchAPI route group: RL surface: state/plant/policies/roles/drive/preflight/sysid.

Moved verbatim from bench_api.py (2026-08-29 component-boundaries split);
mixed into ``bench_api.BenchAPI``. Route/JSON shapes are unchanged.
"""
from __future__ import annotations

from .common import *  # noqa: F401,F403
from async_bus_guard import AsyncSamplerCleanupError


class RlApi:
    # -- RL / agent HTTP surface (prefer this over SSH) ---------------------
    def rl_state(self) -> dict:
        """Pose + plant + activity in one JSON blob for agents / UI."""
        bus_state = self.bus_access_state(recover=True)
        return {
            "ok": not bus_state.get("bus_quarantined", False),
            "service": "hexapod-web",
            **bus_state,
            "pose": self.pose(),
            "plant": self.plant_state(),
            "imu": self.imu_state(),
            "calibrate": self.calibrate_state(),
            "robot": self.robot_state(),
            "drive": self.rl_drive_state(),
        }

    def rl_find_plant(self, *, clearance_mm: float = 40.0,
                      force: bool = False) -> dict:
        """Start geometry+contact plant finder (async). Poll ``rl_state``.

        Disabled unless ``force=true`` — 2026-08-06 unsupervised plant
        blends tipped/browned-out and cooked a knee servo.
        """
        if not force:
            return {
                "ok": False,
                "error": (
                    "find_plant disabled without force=true. "
                    "Hand-set a low stance, set-zero-here if needed, "
                    "capture_plant — do not auto-stand."
                ),
            }
        blocked = self._bus_admission_error()
        if blocked is not None:
            return blocked
        return self.run_calibrate(mode="geometry", clearance_mm=clearance_mm)

    def rl_capture_plant(self) -> dict:
        """Save current 18-joint pose as plant (no motion)."""
        from feetech_bus import save_plant_pose
        import statistics as _stats

        if self._demo_thread and self._demo_thread.is_alive():
            return {"ok": False, "error": "stop the running job first"}
        d = self.drive
        if d.dry_run or not d.bus:
            return {"ok": False, "error": "no bus"}
        blocked = self._bus_admission_error()
        if blocked is not None:
            return blocked
        samples: list[list[float]] = []
        for _ in range(6):
            row: list[float] = []
            ok = True
            with d._lock:
                bus = d.bus
            for j in range(18):
                try:
                    v = bus.read_position_deg(j)
                except Exception:
                    v = None
                if v is None:
                    ok = False
                    break
                row.append(float(v))
            if ok:
                samples.append(row)
            time.sleep(0.04)
        if not samples:
            return {"ok": False, "error": "could not read joints"}
        q = []
        for j in range(18):
            q.append(float(_stats.median([s[j] for s in samples])))
        hips = [q[i] for i in range(1, 18, 3)]
        knees = [q[i] for i in range(2, 18, 3)]
        path = save_plant_pose(
            float(_stats.median(hips)), float(_stats.median(knees)),
            extra={
                "joints_deg": [round(x, 3) for x in q],
                "source": "api_capture",
                "contact_found": True,
            },
        )
        return {
            "ok": True,
            "path": str(path),
            "hip_deg": round(float(_stats.median(hips)), 3),
            "knee_deg": round(float(_stats.median(knees)), 3),
            "joints_deg": [round(x, 3) for x in q],
            "plant": self.plant_state(),
        }

    def rl_stop(self) -> dict:
        """Abort calibrate / find_plant / demo worker."""
        return self.stop_calibrate()

    def rl_probe_dynamics(self, *, amp_deg: float = 10.0,
                          axis: str = "all",
                          soft_torque: int = 350) -> dict:
        """Air-only per-joint step probe → motor_model.json (async)."""
        try:
            from motor_dynamics import run_motor_dynamics
        except ImportError as e:
            return {"ok": False, "error": f"motor_dynamics missing: {e}"}
        if self.drive.dry_run or not self.drive.bus:
            return {"ok": False, "error": "no bus"}
        blocked = self._bus_admission_error()
        if blocked is not None:
            return blocked
        if self._demo_thread and self._demo_thread.is_alive():
            if not self._preempt_demo_thread(reason="→ dynamics", timeout=5.0):
                return {"ok": False, "error": "previous job still running"}

        try:
            amp_deg = float(amp_deg)
        except (TypeError, ValueError):
            amp_deg = 10.0
        try:
            soft_torque = int(soft_torque)
        except (TypeError, ValueError):
            soft_torque = 450
        axis = (axis or "all").strip().lower()

        self._demo_gen += 1
        gen = self._demo_gen
        self._demo_abort.clear()
        with self._lock:
            self._demo_name = "rl_probe_dynamics"
            self._demo_status = f"dynamics ±{amp_deg:.0f}° ({axis})"
            self._demo_params = {
                "amp_deg": amp_deg, "axis": axis,
                "soft_torque": soft_torque,
            }
            self._cal_result = None
            self._cal_progress = {"msg": self._demo_status}
        self._set_activity("calibrating", self._demo_status)

        def _worker():
            d = self.drive

            def _on_progress(p: dict) -> None:
                with self._lock:
                    self._cal_progress = dict(p)
                    self._demo_status = str(p.get("msg") or "dynamics")

            try:
                with d._lock:
                    d.mode = "demo"
                    d.gait.stop()
                # run_motor_dynamics owns the safety ordering: discover and
                # read the present pose, apply the soft torque limit, then
                # enable only the live IDs.  Never pre-enable full torque here.
                self._bus_hot_begin()
                with d._lock:
                    # The runner enables torque internally; mirror that owner
                    # intent without performing a wrapper-level bus write.
                    d.armed = True
                result = run_motor_dynamics(
                    d.bus,
                    amp_deg=amp_deg,
                    axis=axis,
                    soft_torque=soft_torque,
                    names=self.names,
                    abort_check=self._demo_abort.is_set,
                    on_progress=_on_progress,
                )
                if gen != self._demo_gen:
                    return
                with self._lock:
                    self._cal_result = result
                    if self._demo_abort.is_set() or result.get("aborted"):
                        self._demo_status = "aborted"
                    elif result.get("ok"):
                        self._demo_status = (
                            f"done · {result.get('joints_ok')}/"
                            f"{result.get('joints_tested')} ok"
                        )
                    else:
                        self._demo_status = (
                            f"error: {result.get('error') or result.get('msg')}"
                        )
            except Exception as e:
                if gen != self._demo_gen:
                    return
                with self._lock:
                    self._cal_result = {"ok": False, "error": str(e),
                                       "mode": "dynamics"}
                    self._demo_status = f"error: {e}"
            finally:
                self._bus_hot_end()
                if gen != self._demo_gen:
                    return
                torque_state = "unverified"
                torque_error = None
                try:
                    d._torque_all(False)
                    torque_state = "off"
                except Exception as e:
                    torque_error = str(e)
                with self._lock:
                    result = dict(self._cal_result or {
                        "ok": False, "mode": "dynamics",
                        "error": "dynamics worker ended without a result",
                    })
                    result.update({
                        "limped": torque_state == "off",
                        "torque_state": torque_state,
                    })
                    if torque_error is not None:
                        result["ok"] = False
                        prior = str(result.get("error") or "").strip()
                        result["error"] = (
                            f"{prior}; " if prior else "") + (
                            "torque disable unverified: " + torque_error)
                        self._demo_status = (
                            "error: torque disable unverified: " + torque_error)
                    self._cal_result = result
                with d._lock:
                    d.armed = False
                    d.status = (
                        "dynamics complete; disarmed (limp)"
                        if torque_state == "off" else
                        "dynamics stopped; torque unverified")
                    if d.mode == "demo":
                        d.mode = "idle"
                with self._lock:
                    st = self._demo_status
                self._set_activity(
                    "limp" if torque_state == "off" else "error",
                    st or "dynamics done")

        self._demo_thread = threading.Thread(target=_worker, daemon=True)
        self._demo_thread.start()
        return {"ok": True, "calibrate": self.calibrate_state()}

    def sysid_run(self, protocol: dict, *, force: bool = False) -> dict:
        """Run a sysid protocol (deterministic command stream, async).

        Body-supplied protocol JSON (see ``sysid_protocol.py``); logged
        to ``logs/sysid_<name>_<stamp>.csv`` with per-tick send/recv
        timestamps. Whole-body ``traj`` segments additionally require
        ``force=true`` (and the runner's own start-pose gate).
        """
        try:
            from sysid_protocol import duration_s, validate
            from sysid_runner import run_sysid_protocol
        except ImportError as e:
            return {"ok": False, "error": f"sysid modules missing: {e}"}
        if self.drive.dry_run or not self.drive.bus:
            return {"ok": False, "error": "no bus"}
        blocked = self._bus_admission_error()
        if blocked is not None:
            return blocked
        if not isinstance(protocol, dict):
            return {"ok": False, "error": "protocol must be a JSON object"}
        errs = validate(protocol)
        if errs:
            return {"ok": False,
                    "error": "invalid protocol: " + "; ".join(errs)}
        if self._demo_thread and self._demo_thread.is_alive():
            if not self._preempt_demo_thread(reason="→ sysid", timeout=5.0):
                return {"ok": False, "error": "previous job still running"}

        name = str(protocol.get("name", "unnamed"))
        secs = duration_s(protocol)
        self._demo_gen += 1
        gen = self._demo_gen
        self._demo_abort.clear()
        with self._lock:
            self._demo_name = "sysid_run"
            self._demo_status = f"sysid '{name}' ({secs:.0f}s)"
            self._demo_params = {"name": name, "force": bool(force),
                                 "duration_s": round(secs, 1),
                                 "segments": len(protocol.get("segments",
                                                              []))}
            self._cal_result = None
            self._cal_progress = {"msg": self._demo_status}
        self._set_activity("calibrating", self._demo_status)

        def _worker():
            d = self.drive

            def _on_progress(p: dict) -> None:
                with self._lock:
                    self._cal_progress = dict(p)
                    self._demo_status = str(p.get("msg") or "sysid")

            try:
                with d._lock:
                    d.mode = "demo"
                    d.gait.stop()
                # The runner applies its soft limit before enabling live IDs
                # and holds the encoder-derived present pose.  A wrapper-level
                # full-torque enable would violate that ordering.
                self._bus_hot_begin()
                with d._lock:
                    # The runner enables torque internally; mirror that owner
                    # intent without performing a wrapper-level bus write.
                    d.armed = True
                result = run_sysid_protocol(
                    d.bus,
                    protocol,
                    force=bool(force),
                    abort_check=self._demo_abort.is_set,
                    on_progress=_on_progress,
                )
                if gen != self._demo_gen:
                    return
                with self._lock:
                    self._cal_result = result
                    if self._demo_abort.is_set() or result.get("aborted"):
                        self._demo_status = "aborted"
                    elif result.get("ok"):
                        self._demo_status = (
                            f"done · {result.get('ticks_done')}/"
                            f"{result.get('ticks_planned')} ticks")
                    else:
                        self._demo_status = f"error: {result.get('error')}"
            except Exception as e:
                if gen != self._demo_gen:
                    return
                with self._lock:
                    self._cal_result = {"ok": False, "error": str(e),
                                       "mode": "sysid"}
                    self._demo_status = f"error: {e}"
            finally:
                self._bus_hot_end()
                if gen != self._demo_gen:
                    return
                torque_state = "unverified"
                torque_error = None
                try:
                    d._torque_all(False)
                    torque_state = "off"
                except Exception as e:
                    torque_error = str(e)
                with self._lock:
                    result = dict(self._cal_result or {
                        "ok": False, "mode": "sysid",
                        "error": "sysid worker ended without a result",
                    })
                    result.update({
                        "limped": torque_state == "off",
                        "torque_state": torque_state,
                    })
                    if torque_error is not None:
                        result["ok"] = False
                        prior = str(result.get("error") or "").strip()
                        result["error"] = (
                            f"{prior}; " if prior else "") + (
                            "torque disable unverified: " + torque_error)
                        self._demo_status = (
                            "error: torque disable unverified: " + torque_error)
                    self._cal_result = result
                with d._lock:
                    d.armed = False
                    d.status = (
                        "sysid complete; disarmed (limp)"
                        if torque_state == "off" else
                        "sysid stopped; torque unverified")
                    if d.mode == "demo":
                        d.mode = "idle"
                with self._lock:
                    st = self._demo_status
                self._set_activity(
                    "limp" if torque_state == "off" else "error",
                    st or "sysid done")

        self._demo_thread = threading.Thread(target=_worker, daemon=True)
        self._demo_thread.start()
        return {"ok": True, "name": name, "duration_s": round(secs, 1),
                "calibrate": self.calibrate_state()}

    def rl_preflight(self, *, mode: str = "stand") -> dict:
        """Read-only readiness check for the RL stand/lower/walk buttons."""
        mode = (mode or "stand").strip().lower()
        if mode not in ("stand", "lower", "walk"):
            return {"ok": False, "error": f"bad mode {mode!r}"}
        if self.drive.dry_run or not self.drive.bus:
            return {"ok": False, "error": "no bus"}
        blocked = self._bus_admission_error()
        if blocked is not None:
            return blocked
        try:
            from rl_policy import preflight
        except ImportError as e:
            return {"ok": False, "error": f"rl_policy missing: {e}"}
        ok, reason, details = preflight(self.drive.bus, mode)
        out = {"ok": ok, "mode": mode, **details}
        if not ok:
            out["error"] = reason
        return out

    def rl_feedback(self) -> dict:
        """One-shot telemetry: 18-joint bulk feedback + IMU tilt. Read-only.

        ONE MCU bulk transaction (``read_all_feedback``) + one IMU read —
        a few Hz sustainable even while the drive loop walks, unlike
        ``/api/status`` whose 1..31 scan takes seconds. Built for external
        telemetry loggers (``rl_move/scripts/tape_measure_walk.py``).
        ``joints`` is indexed 0..17; missing servos are null.
        """
        import math as _math

        d = self.drive
        if d.dry_run or not d.bus:
            return {"ok": False, "error": "no bus"}
        blocked = self._bus_admission_error()
        if blocked is not None:
            return blocked
        bus = d.bus
        try:
            fb = bus.read_all_feedback()
        except Exception as e:
            return {"ok": False, "error": f"feedback: {e}"}
        joints: list[dict | None] = []
        for j in range(N_JOINTS):
            f = fb.get(j)
            joints.append(None if f is None else {
                "deg": round(float(f.get("deg", 0.0)), 2),
                "cur_a": round(float(f.get("current_a", 0.0)), 3),
                "temp_c": int(f.get("temp_c") or 0),
                "load_pct": round(float(f.get("load_pct", 0.0)), 1),
                "volt": round(float(f.get("volt", 0.0)), 2),
            })
        out: dict = {"ok": True, "t_unix": round(time.time(), 3),
                     "live": len(fb), "joints": joints}
        try:
            imu = bus.read_imu(apply_calib=True)
        except Exception:
            imu = None
        if isinstance(imu, dict) and "ax_g" in imu:
            roll = _math.degrees(_math.atan2(imu["ay_g"], imu["az_g"]))
            pitch = _math.degrees(_math.atan2(
                -imu["ax_g"], _math.hypot(imu["ay_g"], imu["az_g"])))
            out["roll_deg"] = round(roll, 2)
            out["pitch_deg"] = round(pitch, 2)
            if imu.get("body_pitch_deg") is not None:
                out["body_pitch_deg"] = round(float(imu["body_pitch_deg"]), 2)
            if imu.get("body_roll_deg") is not None:
                out["body_roll_deg"] = round(float(imu["body_roll_deg"]), 2)
            if imu.get("body_pitch_target_deg") is not None:
                out["body_pitch_target_deg"] = round(
                    float(imu["body_pitch_target_deg"]), 2)
            if imu.get("body_frame_calibrated") is not None:
                out["body_frame_calibrated"] = bool(
                    imu.get("body_frame_calibrated"))
            out["gyro_dps"] = [round(float(imu.get(k, 0.0)), 2)
                               for k in ("gx_dps", "gy_dps", "gz_dps")]
        return out

    def rl_policy_info(self) -> dict:
        """Metadata of the deployed policy weights (no bus traffic)."""
        try:
            from rl_policy import WEIGHTS_PATH, WALK_WEIGHTS_PATH
            meta = json.loads(Path(WEIGHTS_PATH).read_text())["meta"]
            out = {"ok": True, **meta}
            try:
                walk = json.loads(
                    Path(WALK_WEIGHTS_PATH).read_text())["meta"]
                out["walk"] = walk
            except Exception as e:
                out["walk"] = {"error": str(e)}
            return out
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def rl_timing_probe(self, *, samples: int = 200,
                        read_samples: int = 8) -> dict:
        """No-motion timing probe for the selected drive walk policy."""
        blocked = self._bus_admission_error()
        if blocked is not None:
            return blocked
        if self._demo_thread and self._demo_thread.is_alive():
            return {"ok": False, "error": "stop the running job first"}
        try:
            from rl_policy import benchmark_drive_hot_path
        except ImportError as e:
            return {"ok": False, "error": f"rl_policy missing: {e}"}
        return benchmark_drive_hot_path(
            self.drive,
            walk_weights=self._role_weights("walk"),
            samples=samples,
            read_samples=read_samples)

    # Swappable policy registry (operator request 08-10): exported
    # weight JSONs live in linux_control/policies/; selecting one
    # atomically copies it over the live rl_policy_weights.json /
    # rl_walk_weights.json. No restart needed — run_policy_move loads
    # weights fresh at every episode start. Slot is inferred from the
    # obs dim (68 = stance stand/lower, 72/74/93 = walk).
    POLICIES_DIR = lc_dir() / "policies"
    # Uploaded policies (rl_move/np_policy.py, POST /api/rl/policies)
    # live OUTSIDE the deploy tree so code pushes never wipe them —
    # same convention as ~/.hexapod_dances. On a name clash the upload
    # wins (robot-local state beats the repo).
    UPLOAD_POLICIES_DIR = Path.home() / ".hexapod_policies"
    # obs 74 = walk + phase clock; obs 93 = AMP walk with phase,
    # yaw-rate command, and all-healthy fault-health tail. Same walk slot.
    _SLOT_OBS = {68: "stance", 72: "walk", 74: "walk", 93: "walk"}
    def _find_policy_file(self, file: str) -> Path | None:
        """Resolve a picker file name to a path (uploads shadow repo)."""
        name = Path(str(file)).name          # forbid path traversal
        for d in (self.UPLOAD_POLICIES_DIR, self.POLICIES_DIR):
            p = d / name
            if p.is_file():
                return p
        return None

    def _policy_slot_targets(self) -> dict:
        from rl_policy import WALK_WEIGHTS_PATH, WEIGHTS_PATH
        return {"stance": Path(WEIGHTS_PATH), "walk": Path(WALK_WEIGHTS_PATH)}

    def rl_policies(self) -> dict:
        """List swappable policies + which one is live in each slot."""
        import hashlib

        def _md5(p: Path):
            try:
                return hashlib.md5(p.read_bytes()).hexdigest()
            except Exception:
                return None

        active = {slot: _md5(p)
                  for slot, p in self._policy_slot_targets().items()}
        out = []
        seen = set()
        for d, uploaded in ((self.UPLOAD_POLICIES_DIR, True),
                            (self.POLICIES_DIR, False)):
            try:
                files = sorted(d.glob("*.json"))
            except OSError:
                continue
            for f in files:
                if f.name in seen:       # upload shadows the repo copy
                    continue
                seen.add(f.name)
                try:
                    obj = json.loads(f.read_text())
                    meta = obj["meta"]
                except Exception as e:
                    out.append({"file": f.name, "error": str(e)})
                    continue
                try:
                    from rl_move.np_policy import validate_np_policy
                    errors, _ = validate_np_policy(obj)
                except Exception as e:
                    errors = [str(e)]
                slot = self._SLOT_OBS.get(meta.get("obs_dim"))
                out.append({
                    "file": f.name,
                    "name": meta.get("name") or f.stem,
                    "slot": slot,
                    "obs_dim": meta.get("obs_dim"),
                    "source": (meta.get("source") or "").rsplit("/", 1)[-1],
                    "notes": meta.get("notes", ""),
                    "uploaded": uploaded,
                    "runnable": not errors,
                    **({"error": "; ".join(errors[:3])} if errors else {}),
                    "active": (slot is not None
                               and not errors
                               and _md5(f) == active.get(slot)),
                })
        out.sort(key=lambda r: r["file"])
        return {"ok": True, "dir": str(self.POLICIES_DIR), "policies": out}

    def rl_policy_select(self, *, file: str = "") -> dict:
        """Make policies/<file> the live policy for its slot (no motion)."""
        import os

        if self._demo_thread and self._demo_thread.is_alive():
            return {"ok": False, "error": "stop the running job first"}
        name = Path(str(file)).name          # forbid path traversal
        src = self._find_policy_file(name)
        if src is None:
            return {"ok": False, "error": f"no such policy file: {name}"}
        try:
            payload = src.read_text()
            obj = json.loads(payload)
            meta = obj["meta"]
            from rl_move.np_policy import validate_np_policy
            errors, _ = validate_np_policy(obj)
            if errors:
                return {"ok": False,
                        "error": "invalid v2 policy: " + "; ".join(errors[:3])}
        except Exception as e:
            return {"ok": False, "error": f"unreadable policy: {e}"}
        slot = self._SLOT_OBS.get(meta.get("obs_dim"))
        if slot is None:
            return {"ok": False,
                    "error": (f"obs_dim {meta.get('obs_dim')} fits no slot "
                              f"(68 = stance, 72/74/93 = walk)")}
        dst = self._policy_slot_targets()[slot]
        tmp = dst.with_name(dst.name + ".tmp")
        tmp.write_text(payload)
        os.replace(tmp, dst)
        try:
            from event_log import emit
            emit("rl_policy_select", f"{slot} <- {name}", src="bench",
                 data={"slot": slot, "file": name,
                       "source": meta.get("source", "")})
        except Exception:
            pass
        return {"ok": True, "slot": slot, "file": name,
                "name": meta.get("name") or src.stem,
                "source": (meta.get("source") or "").rsplit("/", 1)[-1]}

    # Role registry (operator 08-11, MuJoCo-style driving): which
    # policies/<file> serves each FUNCTION. One file can hold several
    # roles — a walk champion that stops cleanly can be both "walk" and
    # "hold"; the rise specialist and the stance champion can split
    # "stand" and "lower". Stored on the board's home dir (like
    # ~/.hexapod_cal.json), NOT in the repo. A role of None keeps the
    # pre-roles behavior: the live slot file (rl_policy_select). The
    # special hold value "walk" is the legacy built-in joint-hold
    # fallback: keep the last commanded pose and do not run the walk
    # policy at zero joystick command. It is no longer the default for
    # drive, because hardware stop tests showed it can sink/fall after a
    # walking phase.
    ROLES_FILE = Path.home() / ".hexapod_rl_roles.json"
    _ROLE_OBS = {"walk": (72, 74, 93), "hold": (68, 72, 74, 93),
                 "stand": (68,), "lower": (68,)}

    def _roles(self) -> dict:
        roles = {"walk": None, "hold": "walk",
                 "stand": None, "lower": None}
        try:
            d = json.loads(self.ROLES_FILE.read_text())
            for k in roles:
                if k in d:
                    roles[k] = d[k]
        except Exception:
            pass
        return roles

    def _role_weights(self, role: str) -> Path | None:
        """Weights-file override for a role; None = default behavior
        (the live slot file, or built-in joint hold for the hold role)."""
        v = self._roles().get(role)
        if not v or v == "walk":
            return None
        return self._find_policy_file(v)

    def rl_roles(self) -> dict:
        """Current role assignments + what each resolves to (no bus)."""
        roles = self._roles()
        out = {}
        for role, v in roles.items():
            p = self._role_weights(role)
            if p is not None:
                try:
                    meta = json.loads(p.read_text())["meta"]
                    resolved = meta.get("name") or p.stem
                except Exception:
                    resolved = p.name
            elif role == "hold" and v == "walk":
                resolved = "built-in joint hold"
            elif role == "hold" and v:
                resolved = f"missing hold policy: {v}"
            else:
                slot = "walk" if role == "walk" else "stance"
                resolved = f"live {slot} slot"
            out[role] = {"file": v, "resolved": resolved}
        return {"ok": True, "roles": out,
                "allowed_obs": {k: list(v)
                                for k, v in self._ROLE_OBS.items()}}

    def rl_role_set(self, *, role: str = "", file: str = "") -> dict:
        """Assign policies/<file> to a role (no motion; takes effect at
        the next episode / session start). file="" resets to default;
        file="walk" (hold role only) = legacy built-in joint hold."""
        role = (role or "").strip().lower()
        if role not in self._ROLE_OBS:
            return {"ok": False,
                    "error": f"bad role {role!r} (walk/hold/stand/lower)"}
        val: str | None
        if not file:
            val = "walk" if role == "hold" else None
        elif file == "walk":
            if role != "hold":
                return {"ok": False,
                        "error": "'walk' shorthand is hold-role only"}
            val = "walk"
        else:
            name = Path(str(file)).name        # forbid path traversal
            p = self._find_policy_file(name)
            if p is None:
                return {"ok": False, "error": f"no such policy: {name}"}
            try:
                obj = json.loads(p.read_text())
                meta = obj["meta"]
                from rl_move.np_policy import validate_np_policy
                errors, _ = validate_np_policy(obj)
                if errors:
                    return {"ok": False,
                            "error": "invalid v2 policy: "
                                     + "; ".join(errors[:3])}
            except Exception as e:
                return {"ok": False, "error": f"unreadable policy: {e}"}
            if meta.get("obs_dim") not in self._ROLE_OBS[role]:
                return {"ok": False,
                        "error": (f"{name} (obs {meta.get('obs_dim')}) "
                                  f"does not fit role {role} "
                                  f"(needs obs {self._ROLE_OBS[role]})")}
            val = name
        roles = self._roles()
        roles[role] = val
        try:
            tmp = self.ROLES_FILE.with_name(self.ROLES_FILE.name + ".tmp")
            tmp.write_text(json.dumps(roles, indent=1))
            tmp.replace(self.ROLES_FILE)
        except OSError as e:
            return {"ok": False, "error": f"could not save roles: {e}"}
        try:
            from event_log import emit
            emit("rl_role_set", f"{role} <- {val or 'default'}",
                 src="bench", data={"role": role, "file": val})
        except Exception:
            pass
        return {"ok": True, **self.rl_roles()}

    # -- Uploaded RL policies (policies as data) -------------------------
    # rl_move/np_policy.py: the export_policy_np.py JSON is an
    # uploadable artifact.  POST /api/rl/policies stores it in
    # ~/.hexapod_policies (deploys never wipe it); it then appears in
    # the picker and can be slot-selected / role-assigned and run by
    # the normal /api/rl/* buttons.  Same file works in the MuJoCo sim.

    def save_rl_policy(self, obj, *, name: str = "") -> dict:
        from rl_move.np_policy import (safe_policy_name,
                                       validate_np_policy)
        errs, info = validate_np_policy(obj)
        if errs:
            return {"ok": False, "error": "; ".join(errs[:5])}
        stem = safe_policy_name(name or info.get("name") or "")
        if stem is None:
            return {"ok": False,
                    "error": "need a name ([A-Za-z0-9._-]{1,64}) — "
                             "?name=... or meta.name"}
        try:
            self.UPLOAD_POLICIES_DIR.mkdir(parents=True, exist_ok=True)
            p = self.UPLOAD_POLICIES_DIR / f"{stem}.json"
            tmp = p.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(obj))
            tmp.replace(p)
        except OSError as e:
            return {"ok": False, "error": f"save failed: {e}"}
        try:
            from event_log import emit
            emit("rl_policy_upload", f"{stem}.json (obs {info['obs_dim']})",
                 src="bench", data=info)
        except Exception:
            pass
        return {"ok": True, "file": p.name, "obs_dim": info["obs_dim"],
                "slot": self._SLOT_OBS.get(info["obs_dim"]),
                "hidden": info.get("hidden"), "bytes": p.stat().st_size}

    def get_rl_policy(self, file: str) -> str | None:
        """Raw JSON text of a picker policy (push it to another robot)."""
        p = self._find_policy_file(file if str(file).endswith(".json")
                                   else f"{file}.json")
        try:
            return p.read_text() if p is not None else None
        except OSError:
            return None

    def delete_rl_policy(self, file: str) -> dict:
        name = Path(str(file)).name
        if not name.endswith(".json"):
            name += ".json"
        p = self.UPLOAD_POLICIES_DIR / name
        if not p.is_file():
            return {"ok": False,
                    "error": f"no uploaded policy {name!r} (repo-shipped "
                             f"policies can't be deleted here)"}
        try:
            p.unlink()
        except OSError as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True, "deleted": name}

    # -- Live drive session (held-arrow-key driving, operator 08-11) ----
    def _drive_active(self) -> bool:
        with self._lock:
            name = self._demo_name
        return (self._drive_cmd is not None
                and self._demo_thread is not None
                and self._demo_thread.is_alive()
                and name == "rl_drive")

    def rl_drive_state(self) -> dict:
        """Session snapshot for the UI (no bus traffic)."""
        active = self._drive_active()
        out: dict = {"ok": True, "active": active}
        cmd = self._drive_cmd
        if cmd is not None:
            out["live"] = cmd.live
        with self._lock:
            if active:
                out["status"] = self._demo_status
            elif self._demo_name == "rl_drive":
                out["result"] = self._cal_result
        return out

    def rl_drive_cmd(self, *, vx: float = 0.0, vy: float = 0.0,
                     wz: float = 0.0, dh: float = 0.0) -> dict:
        """Heartbeat from the browser: body-frame (vx, vy) m/s and yaw
        rate wz rad/s while keys are held, plus dh in [-1, 1] (D-pad
        body-height nudge; tracked only while HOLDING with an obs-68
        stance hold policy). Never touches the bus — the 25 Hz session
        loop reads it. Stale heartbeats (> 0.6 s) decay to zero
        server-side, so this must keep streaming."""
        if not self._drive_active():
            return {"ok": False, "error": "no drive session", "active": False}
        self._drive_cmd.set(float(vx), float(vy), float(wz), float(dh))
        with self._lock:
            status = self._demo_status
        return {"ok": True, "active": True, "status": status,
                "live": self._drive_cmd.live}

    def rl_drive_stop(self) -> dict:
        """Graceful end: refs ramp to zero, robot HOLDS the pose."""
        if self._drive_cmd is not None:
            self._drive_cmd.request_stop()
        return self.rl_drive_state()

    def rl_drive_start(self, *, vx: float = 0.0, vy: float = 0.0,
                       wz: float = 0.0, dh: float = 0.0) -> dict:
        """Start a persistent RL drive session (async, demo slot).

        Motion-free start contract: read-only preflight accepts the
        sim walk-ready pose, then the loop runs until stop /
        heartbeat silence / cap / safety trip, driven live by
        rl_drive_cmd. It must not surprise-glide to another stance before
        keys are pressed. THE OPERATOR MUST BE WATCHING.
        """
        if self.drive.dry_run or not self.drive.bus:
            return {"ok": False, "error": "no bus"}
        blocked = self._bus_admission_error()
        if blocked is not None:
            return blocked
        try:
            from rl_policy import DriveCommand, preflight, run_drive_session
        except ImportError as e:
            return {"ok": False, "error": f"rl_policy missing: {e}"}
        with self.drive._lock:
            armed = bool(self.drive.armed)
        if not armed:
            return {"ok": False,
                    "error": ("robot is limp/disarmed; use RL Stand Up / "
                              "Walk Ready first")}
        if self._demo_thread and self._demo_thread.is_alive():
            if self._drive_active():
                return {"ok": True, "already": True,
                        **self.rl_drive_state()}
            return {"ok": False, "error": "stop the running job first"}

        walk_w = self._role_weights("walk")
        hold_w = self._role_weights("hold")
        if hold_w is None:
            hold_role = self._roles().get("hold")
            if hold_role and hold_role != "walk":
                error = (
                    f"configured hold policy {hold_role!r} is not available "
                    "on this robot; select the MuJoCo default complete "
                    "policy or assign Hold to an available stance policy."
                )
            else:
                error = (
                    "drive needs an explicit learned hold role; the legacy "
                    f"{hold_role or 'default'} joint-hold fallback is not "
                    "safe after walking. Select the MuJoCo default complete "
                    "policy or assign Hold to a stance policy."
                )
            return {
                "ok": False,
                "error": error,
            }

        ok, reason, details = preflight(self.drive.bus, "walk")
        if not ok:
            try:
                from event_log import emit
                emit("rl_debug", "drive preflight failed", src="bench",
                     level="warn",
                     data={"reason": reason, "preflight": details})
            except Exception:
                pass
            return {"ok": False,
                    "error": (f"preflight: {reason}. Start Driving no "
                              "longer auto-moves to a walk start; use "
                              "Policy moves → RL Stand Up / Walk Ready "
                              "first if needed."),
                    **details}
        try:
            from event_log import emit
            emit("rl_debug", "drive preflight ok", src="bench",
                 data={"preflight": details})
        except Exception:
            pass

        self._demo_gen += 1
        gen = self._demo_gen
        self._demo_abort.clear()
        cmd = DriveCommand()
        cmd.set(float(vx), float(vy), float(wz), float(dh))
        self._drive_cmd = cmd
        with self._lock:
            self._demo_name = "rl_drive"
            self._demo_status = "drive session starting"
            self._demo_params = {
                "walk": walk_w.name if walk_w else "slot",
                "hold": hold_w.name if hold_w else "joint_hold"}
            self._cal_result = None
            self._cal_progress = {"msg": self._demo_status}
        self._set_activity("rl_policy", "RL drive")

        def _worker():
            d = self.drive

            def _on_progress(p: dict) -> None:
                with self._lock:
                    self._cal_progress = dict(p)
                    self._demo_status = str(p.get("msg") or "RL drive")

            try:
                self._bus_hot_begin()
                result = run_drive_session(
                    d, cmd, on_progress=_on_progress,
                    abort_check=self._demo_abort.is_set,
                    walk_weights=walk_w, hold_weights=hold_w)
                if gen != self._demo_gen:
                    return
                with self._lock:
                    self._cal_result = result
                    if result.get("ok"):
                        self._demo_status = (
                            "drive session ended"
                            + (f" — {result['ended']}"
                               if result.get("ended") else "")
                            + f" · maxI {result.get('max_current_a', 0):.2f}A")
                    else:
                        self._demo_status = (
                            f"RL drive: {result.get('error')}")
            except AsyncSamplerCleanupError as e:
                if gen != self._demo_gen:
                    return
                with self._lock:
                    self._cal_result = {
                        "ok": False,
                        "error": str(e),
                        "mode": "drive",
                        "bus_quarantined": True,
                        "bus_available": False,
                        "torque_state": "unverified",
                    }
                    self._demo_status = f"bus quarantined: {e}"
            except Exception as e:
                if gen != self._demo_gen:
                    return
                torque_state = "unverified"
                try:
                    d._torque_all(False)
                    torque_state = "off"
                except Exception:
                    pass
                with self._lock:
                    self._cal_result = {
                        "ok": False, "error": str(e), "mode": "drive",
                        "limped": torque_state == "off",
                        "torque_state": torque_state,
                    }
                    self._demo_status = f"error: {e}"
            finally:
                self._bus_hot_end()
                if gen != self._demo_gen:
                    return
                res = self._cal_result or {}
                limped = bool(res.get("limped"))
                quarantined = bool(res.get("bus_quarantined"))
                torque_unverified = res.get("torque_state") == "unverified"
                with d._lock:
                    if quarantined or torque_unverified:
                        d.armed = False
                        d.status = (
                            "rl drive bus quarantined; torque unverified"
                            if quarantined else
                            "rl drive error; torque unverified")
                    else:
                        d.armed = not limped
                    if not quarantined and not torque_unverified and limped:
                        d.status = "rl drive disarmed after trip"
                    elif (not quarantined and not torque_unverified
                          and d.mode == "demo"):
                        d.status = "rl drive holding"
                    if d.mode == "demo":
                        d.mode = "idle"
                with self._lock:
                    st = self._demo_status
                activity = ("error" if quarantined or torque_unverified else
                            "limp" if limped else "holding")
                self._set_activity(activity, st or "drive session done")

        self._demo_thread = threading.Thread(target=_worker, daemon=True)
        self._demo_thread.start()
        return {"ok": True, "mode": "drive",
                "walk": walk_w.name if walk_w else "live slot",
                "hold": hold_w.name if hold_w else "joint_hold"}

    def _rl_walk_ready_stand(self) -> dict:
        """RL-tab Stand Up: STEP stand, then visible sim walk-start settle.

        The deployed walk policy should start where the simulator's normal
        walk episodes start, not at whatever mutable plant_pose.json currently
        says. STEP stand-up already ends close to that high-knee stance; this
        route re-holds/verifies it before Start Driving.
        """
        if self.drive.dry_run or not self.drive.bus:
            return {"ok": False, "error": "no bus"}
        blocked = self._bus_admission_error()
        if blocked is not None:
            return blocked
        if self._demo_thread and self._demo_thread.is_alive():
            if self._drive_active():
                if not self._preempt_demo_thread(
                        reason="drive → walk-ready stand", timeout=8.0):
                    return {"ok": False,
                            "error": "drive session did not stop"}
            else:
                return {"ok": False, "error": "stop the running job first"}

        self._demo_gen += 1
        gen = self._demo_gen
        self._demo_abort.clear()
        with self._lock:
            self._demo_name = "rl_policy_stand"
            self._demo_status = "STEP stand → sim walk-ready starting"
            self._demo_params = {"mode": "stand", "route": "walk_ready"}
            self._cal_result = None
            self._cal_progress = {"msg": self._demo_status}
        self._set_activity("rl_policy", "STEP stand → sim walk-ready")

        def _worker():
            d = self.drive

            def _on_progress(p: dict) -> None:
                with self._lock:
                    self._cal_progress = dict(p)
                    self._demo_status = str(
                        p.get("msg") or "STEP stand → sim walk-ready")

            result: dict = {}
            try:
                self._bus_hot_begin()
                with d._lock:
                    d.mode = "demo"
                    d._torque_all(True)
                    d.armed = True
                    d.status = "rl stand armed"
                result = self._acquire_start(
                    "stand", gen=gen, on_progress=_on_progress)
                if gen != self._demo_gen:
                    return
                with self._lock:
                    self._cal_result = result
                    self._demo_status = (
                        "done · sim walk-ready"
                        if result.get("ok") else
                        f"error: {result.get('error') or 'failed'}")
                    self._cal_progress = {"msg": self._demo_status}
            except Exception as e:
                if gen != self._demo_gen:
                    return
                result = {"ok": False, "error": str(e)}
                with self._lock:
                    self._cal_result = result
                    self._demo_status = f"error: {e}"
                    self._cal_progress = {"msg": self._demo_status}
            finally:
                self._bus_hot_end()
                if gen != self._demo_gen:
                    return
                if result.get("ok"):
                    self._enter_stand_hold()
                    self._set_activity("armed", "sim walk-ready")
                else:
                    with d._lock:
                        if d.mode == "demo":
                            d.mode = "idle"
                    self._set_activity("armed" if d.armed else "limp",
                                       self._demo_status)

        self._demo_thread = threading.Thread(target=_worker, daemon=True)
        self._demo_thread.start()
        return {"ok": True, "mode": "stand", "route": "walk_ready",
                "calibrate": self.calibrate_state(),
                "robot": self.robot_state()}

    def rl_policy_move(self, *, mode: str = "stand", vx: float = 0.03,
                       vy: float = 0.0, duration_s: float = 6.0,
                       rot60: bool = True, turn: str | None = None,
                       tilt_trip_deg: float | None = None,
                       extra_hold_s: float = 0.0,
                       learned: bool = False) -> dict:
        """Run RL walk; stand/lower use baked STEP outside Experiments.

        Async (demo-thread slot, poll ``rl_state``, abort via ``rl_stop``).
        Read-only preflight refuses to move unless all 18 servos answer,
        the IMU is alive, and the present pose matches the expected start
        (sim walk-ready pose for walk).
        ``mode="stand"`` and ``mode="lower"`` deliberately delegate to
        the STEP stand-up keyframes instead of the experimental learned
        stance policies — unless ``learned=True`` (operator opt-in,
        08-25): that runs the learned stance-policy episode via
        run_policy_move using the stand/lower role weights (stand starts
        belly-down legs-straight; lower starts from the sim walk-ready
        stand). EXPERIMENTAL on hardware — keep a hand ready.
        Safety layer trips (tilt / sustained over-current / temp) limp
        immediately. Walk extras: body-frame vx/vy (m/s, clamped to the
        trained 0.06 band) and duration_s (clamped 3..20 s).
        ``turn`` (walk only): "left"/"right" = mirror-selection arc
        turn, "hold" = heading hold; None = the unchanged naked path.
        The OPERATOR MUST BE WATCHING — this is the explicit order.
        """
        mode = (mode or "stand").strip().lower()
        if mode not in ("stand", "lower", "walk"):
            return {"ok": False, "error": f"bad mode {mode!r}"}
        if self.drive.bus is not None:
            blocked = self._bus_admission_error()
            if blocked is not None:
                return blocked
        if mode == "stand" and not learned:
            return self._rl_walk_ready_stand()
        if mode == "lower" and not learned:
            return self.standup(mode="step", speed=10.0,
                                direction="down")
        weights_path = self._role_weights(mode)
        if learned and mode in ("stand", "lower"):
            raw_role = self._roles().get(mode)
            action = "rise" if mode == "stand" else "lower"
            if not raw_role:
                return {
                    "ok": False,
                    "error": (
                        f"learned RL {action} is disabled for the default "
                        "composed policy. Use Tuck Stand/Tuck Lower, or "
                        "select a learned-stance bundle / explicit role first."
                    ),
                }
            if weights_path is None:
                return {
                    "ok": False,
                    "error": (
                        f"learned RL {action} role is set to {raw_role!r}, "
                        "but that policy file is not available."
                    ),
                }
        try:
            from rl_policy import preflight, run_policy_move
        except ImportError as e:
            return {"ok": False, "error": f"rl_policy missing: {e}"}
        if self.drive.dry_run or not self.drive.bus:
            return {"ok": False, "error": "no bus"}
        if self._demo_thread and self._demo_thread.is_alive():
            if self._drive_active():
                # Stand/Sit during a drive session flips models
                # (operator 08-11): end the session — the robot holds
                # its pose — then run the episode from there.
                if not self._preempt_demo_thread(
                        reason=f"drive → {mode}", timeout=8.0):
                    return {"ok": False,
                            "error": "drive session did not stop"}
            else:
                return {"ok": False, "error": "stop the running job first"}

        # Preflight before claiming the worker slot so refusals are
        # instant and motion-free.
        ok, reason, details = preflight(self.drive.bus, mode)
        acquire_first: str | None = None
        if not ok:
            return {"ok": False,
                    "error": (f"preflight: {reason}. Walk no longer "
                              "auto-moves to a walk start; use Policy "
                              "moves → RL Stand Up / Walk Ready first if "
                              "needed."),
                    **details}

        self._demo_gen += 1
        gen = self._demo_gen
        self._demo_abort.clear()
        label = {"stand": "learned RL rise", "lower": "learned RL lower",
                 "walk": "RL walk"}[mode]
        with self._lock:
            self._demo_name = f"rl_policy_{mode}"
            self._demo_status = f"{label} starting"
            self._demo_params = {"mode": mode}
            if learned:
                self._demo_params["learned"] = True
            if mode == "walk":
                self._demo_params.update(
                    vx=float(vx), vy=float(vy),
                    duration_s=float(duration_s), rot60=bool(rot60))
                if turn:
                    self._demo_params["turn"] = str(turn)
            else:
                if tilt_trip_deg:
                    self._demo_params["tilt_trip_deg"] = float(tilt_trip_deg)
                if extra_hold_s:
                    self._demo_params["extra_hold_s"] = float(extra_hold_s)
            self._cal_result = None
            self._cal_progress = {"msg": self._demo_status}
        self._set_activity("rl_policy", label)

        def _worker():
            d = self.drive

            def _on_progress(p: dict) -> None:
                with self._lock:
                    self._cal_progress = dict(p)
                    self._demo_status = str(p.get("msg") or label)

            try:
                # 08-12 operator-observed freezes during the RL stand:
                # this worker was the ONLY motion path that never set
                # _bus_hot, so the TFT panel kept repainting mid-episode
                # (a DJ redraw holds the MCU link ~1.5 s — the measured
                # "big pause in the middle of standing"). Same guard as
                # every other motion worker.
                self._bus_hot_begin()
                if acquire_first:
                    with d._lock:
                        d.mode = "demo"
                        # Force torque-enable; d.armed may be stale after a
                        # previous stop even when the bus is physically limp.
                        d._torque_all(True)
                        d.armed = True
                        d.status = "rl policy armed"
                    _on_progress({"msg": (f"acquiring {acquire_first} "
                                          "start pose first…")})
                    res_a = self._acquire_start(
                        acquire_first, gen=gen,
                        on_progress=_on_progress)
                    if not res_a.get("ok"):
                        raise RuntimeError(
                            "could not reach the start pose — "
                            + str(res_a.get("error") or "aborted"))
                    ok2, reason2, _d2 = preflight(d.bus, mode)
                    if not ok2:
                        raise RuntimeError(
                            f"still failing preflight after acquiring "
                            f"{acquire_first}: {reason2}")
                result = run_policy_move(
                    d, mode, on_progress=_on_progress,
                    abort_check=self._demo_abort.is_set,
                    vx=float(vx), vy=float(vy),
                    duration_s=float(duration_s), rot60=bool(rot60),
                    turn=(str(turn) if turn else None),
                    weights_path=weights_path,
                    tilt_trip_deg=(float(tilt_trip_deg)
                                   if tilt_trip_deg else None),
                    extra_hold_s=float(extra_hold_s or 0.0))
                if gen != self._demo_gen:
                    return
                if result.get("ok") and mode == "stand":
                    # Honesty check: the policy 'finishing' its
                    # episode is not the same as standing (08-11: a
                    # nominally-ok run ended legs-flailed at 0.16 A).
                    try:
                        kfs = (self._load_standup()["modes"]["tuck"]
                               ["keyframes"])
                        stance = [float(x) for x in
                                  kfs[-1]["q_deg"]]
                        w_st, _ = self._delta_vs_present(stance)
                        if w_st is not None and w_st > 30.0:
                            result["stood"] = False
                            result["stance_err_deg"] = round(w_st, 1)
                        else:
                            result["stood"] = True
                    except Exception:
                        pass
                with self._lock:
                    self._cal_result = result
                    if result.get("ok") and result.get("stood") is False:
                        self._demo_status = (
                            f"{label} finished but NOT standing "
                            f"(pose {result['stance_err_deg']:.0f} deg "
                            "from stance) — use the scripted stand")
                    elif result.get("ok"):
                        self._demo_status = (
                            f"{label} done · maxI "
                            f"{result.get('max_current_a', 0):.2f}A")
                    else:
                        self._demo_status = (
                            f"{label}: {result.get('error')}")
            except AsyncSamplerCleanupError as e:
                if gen != self._demo_gen:
                    return
                with self._lock:
                    self._cal_result = {
                        "ok": False,
                        "error": str(e),
                        "mode": mode,
                        "bus_quarantined": True,
                        "bus_available": False,
                        "torque_state": "unverified",
                    }
                    self._demo_status = f"bus quarantined: {e}"
            except Exception as e:
                if gen != self._demo_gen:
                    return
                torque_state = "unverified"
                try:
                    d._torque_all(False)
                    torque_state = "off"
                except Exception:
                    pass
                with self._lock:
                    self._cal_result = {
                        "ok": False, "error": str(e), "mode": mode,
                        "limped": torque_state == "off",
                        "torque_state": torque_state,
                    }
                    self._demo_status = f"error: {e}"
            finally:
                self._bus_hot_end()
                if gen != self._demo_gen:
                    return
                res = self._cal_result or {}
                limped = bool(res.get("limped"))
                quarantined = bool(res.get("bus_quarantined"))
                torque_unverified = res.get("torque_state") == "unverified"
                with d._lock:
                    if quarantined or torque_unverified:
                        d.armed = False
                        d.status = (
                            "rl policy bus quarantined; torque unverified"
                            if quarantined else
                            "rl policy error; torque unverified")
                    else:
                        d.armed = not limped
                    if d.mode == "demo":
                        d.mode = "idle"
                with self._lock:
                    st = self._demo_status
                activity = ("error" if quarantined or torque_unverified else
                            "limp" if limped else "holding")
                self._set_activity(activity, st or f"{label} done")

        self._demo_thread = threading.Thread(target=_worker, daemon=True)
        self._demo_thread.start()
        return {"ok": True, "mode": mode, "calibrate": self.calibrate_state()}

    def rl_set_stance(self, *, hip_deg: float = -20.0, knee_deg: float = 55.0,
                      seconds: float = 10.0, yaw_deg: float = 0.0,
                      force: bool = False) -> dict:
        """Slow ease to a shared hip/knee stance (async).

        A large Δq from present no longer refuses (08-11 directive):
        the worker first ACQUIRES the zero start safely (collision-
        aware, limps on stall) and eases to the stance from there. If
        acquisition fails the job errors out and the ease never runs.
        Under the active absolute-tibia convention, hip≈0°+knee≈80° is
        stilts — not a low plant.
        """
        try:
            from inplace_demos import (
                _enable_torque, _live_robot_ids, _set_torque_limit, ease_to_pose,
            )
            from drive_controller import MAX_SAFE_DELTA_DEG
        except ImportError as e:
            return {"ok": False, "error": str(e)}
        if self.drive.dry_run or not self.drive.bus:
            return {"ok": False, "error": "no bus"}
        blocked = self._bus_admission_error()
        if blocked is not None:
            return blocked
        if self._demo_thread and self._demo_thread.is_alive():
            if not self._preempt_demo_thread(reason="→ set_stance", timeout=5.0):
                return {"ok": False, "error": "previous job still running"}

        hip_deg = max(-80.0, min(30.0, float(hip_deg)))
        knee_deg = max(-20.0, min(150.0, float(knee_deg)))
        yaw_deg = max(-35.0, min(35.0, float(yaw_deg)))
        seconds = max(2.0, min(30.0, float(seconds)))
        goal: list[float] = []
        for _ in range(6):
            goal.extend([yaw_deg, hip_deg, knee_deg])
        acquire_zero_first = False
        if not force:
            worst, j = self._delta_vs_present(goal)
            if worst is None:
                return {"ok": False,
                        "error": ("no encoder readings — cannot check "
                                  "the start pose; retry in a few "
                                  "seconds")}
            if worst > MAX_SAFE_DELTA_DEG:
                # 08-11 directive: acquire the start instead of
                # refusing — safe zero first, then the ease.
                acquire_zero_first = True

        self._demo_gen += 1
        gen = self._demo_gen
        self._demo_abort.clear()
        with self._lock:
            self._demo_name = "rl_set_stance"
            self._demo_status = (
                f"stance hip {hip_deg:+.0f}° / knee {knee_deg:+.0f}°")
            self._demo_params = {
                "hip_deg": hip_deg, "knee_deg": knee_deg,
                "yaw_deg": yaw_deg, "seconds": seconds,
            }
            self._cal_result = None
            self._cal_progress = {"msg": self._demo_status}
        self._set_activity("calibrating", self._demo_status)

        def _worker():
            d = self.drive
            with d._lock:
                d.mode = "demo"
                d.gait.stop()
                if not d.armed:
                    d._torque_all(True)
                    d.armed = True
            live = _live_robot_ids(d.bus)
            try:
                self._bus_hot_begin()
                if acquire_zero_first:
                    res_a = self._acquire_start("zero", gen=gen)
                    if gen != self._demo_gen:
                        return
                    if not res_a.get("ok"):
                        with self._lock:
                            self._demo_status = (
                                "error: start pose not reached — "
                                + str(res_a.get("error") or "aborted"))
                            self._cal_result = {
                                "ok": False, "mode": "set_stance",
                                "error": self._demo_status}
                            self._cal_progress = {
                                "msg": self._demo_status}
                        return
                _set_torque_limit(d.bus, live, 550)
                _enable_torque(d.bus, live)
                ok = ease_to_pose(
                    d.bus, goal, abort_check=self._demo_abort.is_set,
                    seconds=seconds, label="rl_stance")
                if gen != self._demo_gen:
                    return
                with self._lock:
                    if self._demo_abort.is_set() or not ok:
                        self._demo_status = "aborted"
                        self._cal_result = {
                            "ok": False, "aborted": True,
                            "mode": "set_stance",
                        }
                    else:
                        self._demo_status = (
                            f"done · hip {hip_deg:+.0f}° / knee {knee_deg:+.0f}°")
                        self._cal_result = {
                            "ok": True, "mode": "set_stance",
                            "hip_deg": hip_deg, "knee_deg": knee_deg,
                            "yaw_deg": yaw_deg, "goal": goal,
                        }
                        self._cal_progress = {"msg": self._demo_status}
            except Exception as e:
                if gen != self._demo_gen:
                    return
                with self._lock:
                    self._demo_status = f"error: {e}"
                    self._cal_result = {"ok": False, "error": str(e),
                                       "mode": "set_stance"}
            finally:
                self._bus_hot_end()
                if gen != self._demo_gen:
                    return
                try:
                    _set_torque_limit(d.bus, live, 1000)
                except Exception:
                    pass
                with d._lock:
                    if d.mode == "demo":
                        d.mode = "idle"
                with self._lock:
                    st = self._demo_status
                self._set_activity(
                    "armed" if d.armed else "limp", st or "stance done")

        self._demo_thread = threading.Thread(target=_worker, daemon=True)
        self._demo_thread.start()
        return {"ok": True, "calibrate": self.calibrate_state(),
                "target": {"hip_deg": hip_deg, "knee_deg": knee_deg,
                           "seconds": seconds}}
