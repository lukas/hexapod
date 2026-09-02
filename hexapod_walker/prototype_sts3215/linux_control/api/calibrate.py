"""BenchAPI route group: calibration checkup, geometry/IMU/traction probes, reports, run/stop_calibrate.

Moved verbatim from bench_api.py (2026-08-29 component-boundaries split);
mixed into ``bench_api.BenchAPI``. Route/JSON shapes are unchanged.
"""
from __future__ import annotations

from .common import *  # noqa: F401,F403
from hexapod_core.joint_frame import FRAME_ROBOT_ABS, JOINT_CONTRACT


class CalibrateApi:
    # -- step calibrate (cmd vs encoder) -------------------------------------
    @staticmethod
    def _checkup_diagnostic_issues(phases: list[dict]) -> list[dict]:
        return [
            p for p in phases
            if isinstance(p, dict)
            and not p.get("ok")
            and not p.get("skipped")
            and p.get("non_blocking")
        ]

    @staticmethod
    def _checkup_blocking_problem(phases: list[dict]) -> dict | None:
        return (
            next((p for p in phases
                  if isinstance(p, dict)
                  and p.get("aborted")
                  and not p.get("recoverable")), None)
            or next((p for p in phases
                     if isinstance(p, dict)
                     and not p.get("ok")
                     and not p.get("skipped")
                     and not p.get("non_blocking")), None)
        )

    def _latest_calibration_report(self) -> dict | None:
        path = (lc_dir() / "logs"
                / "calibration_report_latest.json")
        if not path.is_file():
            return None
        try:
            report = json.loads(path.read_text())
        except (OSError, ValueError):
            return None
        if not isinstance(report, dict):
            return None
        report.setdefault("mode", "calibration_report")
        report.setdefault("latest", str(path))
        report.setdefault("path", str(path))
        report.setdefault("log_name", path.name)
        phases = report.get("phases") or []
        if phases and not any(
                isinstance(p, dict) and p.get("name") == "report"
                for p in phases):
            phases.append({
                "name": "report",
                "ok": True,
                "mode": "calibration_report",
                "log": report.get("path"),
                "log_name": report.get("log_name"),
                "summary": "sim-ready calibration report saved",
            })
            report["phases"] = phases
        for p in phases:
            if not isinstance(p, dict) or p.get("name") != "report":
                continue
            saved = bool(p.get("log") or p.get("log_name")
                         or report.get("path") or report.get("log_name"))
            if saved:
                p["ok"] = True
        geom = report.get("geometry")
        try:
            geom_schema = int((geom or {}).get("schema_version") or 0)
        except (TypeError, ValueError):
            geom_schema = 0
        # Keep status reads cheap.  Reports older than the current geometry
        # semantics are refreshed once on read so stale dimension-fit wording
        # does not survive a deploy.
        if not isinstance(geom, dict) or geom_schema < 5:
            try:
                report["geometry"] = self._geometry_report()
            except Exception:
                pass
        contact_sweep = (report.get("geometry") or {}).get("contact_sweep")
        if isinstance(contact_sweep, dict):
            for p in phases:
                if not isinstance(p, dict) or p.get("name") != "geometry_sweep":
                    continue
                p["ok"] = bool(contact_sweep.get("ok"))
                status = contact_sweep.get("status") or "unknown"
                n = contact_sweep.get("sample_count")
                summary = (
                    f"dimension sweep {status}; {n} accepted contacts"
                    if n is not None else f"dimension sweep {status}")
                manual_fit = contact_sweep.get("manual_link_fit")
                if (status in ("geometry_mismatch",
                               "manual_geometry_mismatch")
                        and isinstance(manual_fit, dict)):
                    bits = []
                    for key in ("femur", "tibia"):
                        row = manual_fit.get(key)
                        if not isinstance(row, dict):
                            continue
                        try:
                            bits.append(
                                f"{key} fit {float(row['fit_mm']):.1f}"
                                f" vs {float(row['manual_mm']):.1f}mm")
                        except (KeyError, TypeError, ValueError):
                            pass
                    if bits:
                        summary += "; " + "; ".join(bits)
                manual_height = contact_sweep.get("manual_height_fit")
                if (status == "manual_geometry_mismatch"
                        and isinstance(manual_height, dict)):
                    try:
                        summary += (
                            f"; FK/contact height "
                            f"{float(manual_height['fit_mm']):.1f}"
                            f" vs measured "
                            f"{float(manual_height['manual_mm']):.1f}mm")
                    except (KeyError, TypeError, ValueError):
                        pass
                    p["non_blocking"] = True
                p["summary"] = summary
        if phases:
            diagnostic_issues = self._checkup_diagnostic_issues(phases)
            report["diagnostic_issue_count"] = len(diagnostic_issues)
            report["ok"] = self._checkup_blocking_problem(phases) is None
            report["msg"] = (
                "checkup complete with diagnostic issues; see phases"
                if report["ok"] and diagnostic_issues else
                "checkup complete"
                if report["ok"] else
                "checkup complete with issues; see phases")
        return report

    def _latest_geometry_sweep_report(self) -> dict | None:
        path = (lc_dir() / "logs"
                / "geometry_sweep_latest.json")
        if not path.is_file():
            return None
        try:
            report = json.loads(path.read_text())
        except (OSError, ValueError):
            return None
        if not isinstance(report, dict):
            return None
        report.setdefault("mode", "geometry_sweep")
        report.setdefault("latest", str(path))
        report.setdefault("path", str(path))
        report.setdefault("log_name", path.name)
        return report

    def calibrate_state(self) -> dict:
        with self._lock:
            result = dict(self._cal_result) if self._cal_result else None
            progress = dict(self._cal_progress)
            demo_name = self._demo_name
        # rl_policy_* and rl_probe_* jobs share the same worker slot and
        # progress/result plumbing — report them as running too, or their
        # pollers see running=false mid-job and give up.
        running = bool(self._demo_thread and self._demo_thread.is_alive()
                       and (demo_name or "").startswith(
                           ("calibrate", "rl_", "standup_", "measure_")))
        latest_report = None if running else self._latest_calibration_report()
        if result is None and not running:
            result = latest_report
        elif (not running and latest_report is not None
              and not (demo_name or "").startswith(
                  ("calibrate", "rl_", "standup_", "measure_"))):
            result = latest_report
        plant = self.plant_state()
        imu = self.imu_state()
        return {
            "running": running,
            "name": demo_name,
            "progress": progress,
            "result": result,
            "latest_report": latest_report,
            "plant": plant,
            "imu": imu,
            "demo": self.demo_state(),
            "robot": self.robot_state(),
        }

    def plant_state(self) -> dict:
        try:
            from plant_calibrate import plant_state
        except ImportError as e:
            return {"ok": False, "error": str(e)}
        return plant_state()

    def imu_state(self) -> dict:
        try:
            from imu_calibrate import imu_state
        except ImportError as e:
            return {"ok": False, "error": str(e)}
        return imu_state()

    def reset_plant(self) -> dict:
        try:
            from plant_calibrate import reset_plant_pose
        except ImportError as e:
            return {"ok": False, "error": str(e)}
        out = reset_plant_pose()
        out["ok"] = True
        return out

    def reset_imu(self) -> dict:
        try:
            from imu_calibrate import reset_imu_calib
        except ImportError as e:
            return {"ok": False, "error": str(e)}
        out = reset_imu_calib()
        out["ok"] = True
        bus = getattr(self.drive, "bus", None)
        reload = getattr(bus, "reload_imu_calib", None) if bus else None
        if callable(reload):
            try:
                reload()
            except Exception:
                pass
        return out

    def _manual_geometry_path(self) -> Path:
        return lc_dir() / "logs" / "geometry_manual.json"

    def _touchdown_zero_path(self) -> Path:
        return lc_dir() / "logs" / "touchdown_zero.json"

    @staticmethod
    def _maybe_float(val) -> float | None:
        if val is None:
            return None
        if isinstance(val, str) and not val.strip():
            return None
        try:
            out = float(val)
        except (TypeError, ValueError):
            return None
        return out if math.isfinite(out) else None

    def manual_geometry_state(self) -> dict:
        """Operator-measured dimensions, separate from FK-derived estimates."""
        path = self._manual_geometry_path()
        if not path.is_file():
            return {
                "ok": True,
                "learned": False,
                "path": str(path),
                "log_name": path.name,
            }
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError) as e:
            return {"ok": False, "error": str(e), "path": str(path)}
        if not isinstance(data, dict):
            return {"ok": False, "error": "manual geometry is not an object",
                    "path": str(path)}
        out = dict(data)
        out.update({
            "ok": True,
            "learned": True,
            "path": str(path),
            "log_name": path.name,
        })
        for key in ("hip_pitch_height_mm", "hip_center_radius_mm",
                    "femur_mm", "tibia_mm"):
            val = self._maybe_float(out.get(key))
            if val is not None:
                out[key] = round(val, 2)
            else:
                out.pop(key, None)
        return out

    def set_manual_geometry(
            self, *, hip_pitch_height_mm=None,
            hip_center_radius_mm=None,
            femur_mm=None, tibia_mm=None) -> dict:
        """Save hand-measured geometry without moving the robot."""
        def _bounded(name: str, val, lo: float, hi: float) -> float | None:
            x = self._maybe_float(val)
            if x is None:
                return None
            if not (lo <= x <= hi):
                raise ValueError(
                    f"{name} must be {lo:g}..{hi:g} mm, got {x:g}")
            return round(x, 2)

        path = self._manual_geometry_path()
        current = self.manual_geometry_state()
        out = {
            "source": "operator_measurement",
            "notes": (
                "Hand measurements. hip_pitch_height_mm is floor to hip-pitch "
                "servo center at zero/stand reference; tibia_mm is knee-servo "
                "center to boot/contact end; hip_center_radius_mm is body "
                "center to hip-pitch axis in the leg yaw frame."
            ),
        }
        if current.get("ok") and current.get("learned"):
            for key in ("hip_pitch_height_mm", "hip_center_radius_mm",
                        "femur_mm", "tibia_mm", "source", "notes"):
                if current.get(key) is not None:
                    out[key] = current[key]
        try:
            updates = {
                "hip_pitch_height_mm": _bounded(
                    "hip_pitch_height_mm", hip_pitch_height_mm, 40.0, 180.0),
                "hip_center_radius_mm": _bounded(
                    "hip_center_radius_mm", hip_center_radius_mm, 50.0, 180.0),
                "femur_mm": _bounded("femur_mm", femur_mm, 40.0, 140.0),
                "tibia_mm": _bounded("tibia_mm", tibia_mm, 60.0, 220.0),
            }
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        touched = False
        for key, val in updates.items():
            if val is not None:
                out[key] = val
                touched = True
        if not touched:
            return {"ok": False, "error": "no geometry values supplied"}
        out["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, indent=2) + "\n")
        return self.manual_geometry_state()

    def touchdown_zero_state(self) -> dict:
        """Latest touchdown-derived software zero hints."""
        path = self._touchdown_zero_path()
        if not path.is_file():
            return {
                "ok": True,
                "learned": False,
                "path": str(path),
                "log_name": path.name,
            }
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError) as e:
            return {"ok": False, "error": str(e), "path": str(path)}
        if not isinstance(data, dict):
            return {"ok": False, "error": "touchdown zero is not an object",
                    "path": str(path)}
        out = dict(data)
        out.update({
            "ok": True,
            "learned": True,
            "path": str(path),
            "log_name": path.name,
        })
        return out

    def touchdown_zero_straight_pose(
            self, *, legs=None, torque=None, seconds=None, force=False) -> dict:
        """Move selected legs to touchdown-compensated straight-out pose."""
        state = self.touchdown_zero_state()
        if not state.get("ok"):
            return state
        if not state.get("learned"):
            return {"ok": False, "error": "no saved touchdown-zero hints"}

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

        try:
            leg_list = parse_legs(legs)
            torque_i = 320 if torque is None else int(round(float(torque)))
            torque_i = max(150, min(520, torque_i))
            seconds_f = 1.6 if seconds is None else float(seconds)
            seconds_f = max(0.5, min(5.0, seconds_f))
        except (TypeError, ValueError) as e:
            return {"ok": False, "error": str(e)}
        if not leg_list:
            return {"ok": False, "error": "no legs selected"}

        by_leg = {}
        for row in state.get("per_leg") or []:
            try:
                by_leg[int(row.get("leg"))] = row
            except (TypeError, ValueError):
                continue

        q, missing_pose = self._present_pose18()
        if missing_pose:
            return {
                "ok": False,
                "error": "missing encoder readings; cannot build safe pose",
                "missing_joints": missing_pose[:8],
            }

        targets: list[dict] = []
        missing_hints: list[str] = []
        too_large: list[dict] = []
        for leg in leg_list:
            row = by_leg.get(leg)
            if not isinstance(row, dict):
                missing_hints.append(f"L{leg}")
                continue
            for axis, offset in (("hip", 1), ("knee", 2)):
                hint = row.get(axis)
                comp = None
                if isinstance(hint, dict) and hint.get("ok"):
                    comp = self._maybe_float(
                        hint.get("command_compensation_deg"))
                    if comp is None:
                        comp = self._maybe_float(
                            hint.get("encoder_zero_error_deg"))
                if comp is None:
                    missing_hints.append(f"L{leg} {axis}")
                    continue
                if abs(comp) > 20.0 and not force:
                    too_large.append({
                        "leg": leg,
                        "axis": axis,
                        "target_deg": round(comp, 2),
                    })
                    continue
                joint = leg * 3 + offset
                q[joint] = float(comp)
                targets.append({
                    "leg": leg,
                    "axis": axis,
                    "joint": joint,
                    "target_deg": round(float(comp), 2),
                    "source_strength": hint.get("contact_strength"),
                })
        if missing_hints:
            return {
                "ok": False,
                "error": "missing touchdown hints for selected legs",
                "missing": missing_hints,
            }
        if too_large:
            return {
                "ok": False,
                "error": "straight hint is unusually large",
                "bad": too_large,
            }

        result = self.command_pose(
            q,
            seconds=seconds_f,
            torque=torque_i,
            force=bool(force),
            limp_after=False,
            label="touchdown straight")
        result.update({
            "mode": "touchdown_straight",
            "legs": leg_list,
            "targets": targets,
            "measurement_stamp": state.get("measurement_stamp"),
        })
        return result

    def _manual_zero_hypotheses(
            self, samples: list[dict], *,
            manual_height_mm: float | None,
            manual_femur_mm: float | None,
            manual_tibia_mm: float | None) -> dict | None:
        """Fit measured links/height against contact angles for zero clues."""
        if (
                manual_height_mm is None or manual_femur_mm is None
                or manual_tibia_mm is None):
            return None
        rows = []
        for s in samples or []:
            try:
                if (
                        not bool(s.get("accepted", False))
                        or not bool(s.get("contact_detected", False))):
                    continue
                reason = str(s.get("reason") or "").lower()
                if "without contact signal" in reason:
                    continue
                base_z = s.get("base_z_mm")
                nominal_z = s.get("nominal_z_mm")
                if base_z is not None and nominal_z is not None:
                    if float(nominal_z) > float(base_z) + 4.0:
                        continue
                rows.append({
                    "leg": int(s.get("leg", 0)),
                    "hip_deg": float(s["hip_deg"]),
                    "knee_deg": float(s["knee_deg"]),
                })
            except (KeyError, TypeError, ValueError):
                continue
        if len(rows) < 3:
            return {
                "ok": False,
                "status": "not_enough_contacts",
                "sample_count": len(rows),
                "target_height_mm": round(float(manual_height_mm), 2),
            }

        target = float(manual_height_mm)
        femur = float(manual_femur_mm)
        tibia = float(manual_tibia_mm)

        def _height(row: dict, hip_off: float, knee_off: float) -> float:
            hip = math.radians(float(row["hip_deg"]) + hip_off)
            knee = math.radians(float(row["knee_deg"]) + knee_off)
            return femur * math.sin(hip) + tibia * math.sin(knee)

        def _eval(hip_off: float, knee_off: float) -> dict:
            heights = [_height(r, hip_off, knee_off) for r in rows]
            errs = [h - target for h in heights]
            mean_h = sum(heights) / len(heights)
            rms = math.sqrt(sum(e * e for e in errs) / len(errs))
            spread = max(heights) - min(heights)
            penalty = 0.03 * (abs(hip_off) + abs(knee_off))
            return {
                "ok": True,
                "angle_convention": "knee_deg is absolute tibia angle",
                "angle_convention_key": "absolute_tibia",
                "hip_zero_deg": round(float(hip_off), 2),
                "knee_zero_deg": round(float(knee_off), 2),
                "mean_height_mm": round(mean_h, 2),
                "mean_error_mm": round(mean_h - target, 2),
                "height_spread_mm": round(spread, 2),
                "rms_error_mm": round(rms, 2),
                "score": round(rms + penalty, 3),
            }

        def _frange(lo: float, hi: float, step: float) -> list[float]:
            n = int(round((hi - lo) / step))
            return [round(lo + i * step, 4) for i in range(n + 1)]

        def _fit(hip_vals: list[float], knee_vals: list[float], *,
                 refine: bool = True) -> dict:
            best: dict | None = None
            for hip_off in hip_vals:
                for knee_off in knee_vals:
                    row = _eval(hip_off, knee_off)
                    if best is None or row["score"] < best["score"]:
                        best = row
            if refine and best is not None:
                hip0 = float(best["hip_zero_deg"])
                knee0 = float(best["knee_zero_deg"])
                for hip_off in _frange(hip0 - 0.6, hip0 + 0.6, 0.1):
                    for knee_off in _frange(knee0 - 0.6, knee0 + 0.6, 0.1):
                        row = _eval(hip_off, knee_off)
                        if row["score"] < best["score"]:
                            best = row
            return best or {
                "ok": False,
                "angle_convention": "absolute_tibia",
                "status": "no_candidates",
            }

        coarse = _frange(-30.0, 30.0, 1.0)
        fine = _frange(-30.0, 30.0, 0.5)
        zero = [0.0]
        models = {
            "no_offset": _eval(0.0, 0.0),
            "hip_only": _fit(fine, zero),
            "knee_only": _fit(zero, fine),
            "best_pair": _fit(coarse, coarse),
        }
        best_model = min(
            (row for row in models.values() if row.get("ok")),
            key=lambda r: float(r.get("score", 1e9)),
            default=None)
        return {
            "ok": True,
            "status": "fit_to_operator_measurements",
            "sample_count": len(rows),
            "target_height_mm": round(target, 2),
            "femur_mm": round(femur, 2),
            "tibia_mm": round(tibia, 2),
            "best_model": best_model,
            "joint_frame": FRAME_ROBOT_ABS,
            "joint_contract": JOINT_CONTRACT,
            "models": models,
            "note": "All fits use the absolute-tibia joint contract.",
        }

    def _geometry_report(
            self, *, geometry_sweep: dict | None = None,
            use_latest_sweep: bool = True) -> dict:
        try:
            from feetech_bus import AXIS_LIMITS_DEG, standing_pose_degrees
            from geometry_plant import fit_contact_sweep
            from hexapod_core.tripod_gait import (CHASSIS_FLAT_TO_FLAT_MM, COXA_MM,
                                     FEMUR_MM, TIBIA_MM)
        except ImportError as e:
            return {"ok": False, "error": str(e)}
        plant = self.plant_state()
        manual = self.manual_geometry_state()
        manual_height_mm = (
            self._maybe_float(manual.get("hip_pitch_height_mm"))
            if manual.get("ok") else None)
        manual_center_radius_mm = (
            self._maybe_float(manual.get("hip_center_radius_mm"))
            if manual.get("ok") else None)
        manual_femur_mm = (
            self._maybe_float(manual.get("femur_mm"))
            if manual.get("ok") else None)
        manual_tibia_mm = (
            self._maybe_float(manual.get("tibia_mm"))
            if manual.get("ok") else None)
        try:
            pose = [float(x) for x in (plant.get("pose")
                    or standing_pose_degrees())]
        except Exception:
            pose = []

        def foot_from(hip_deg: float, knee_deg: float) -> dict:
            hip = math.radians(float(hip_deg))
            knee = math.radians(float(knee_deg))
            reach = (COXA_MM + FEMUR_MM * math.cos(hip)
                     + TIBIA_MM * math.cos(knee))
            z = -FEMUR_MM * math.sin(hip) - TIBIA_MM * math.sin(knee)
            return {
                "radial_mm": round(reach, 2),
                "z_mm": round(z, 2),
            }

        per_leg = []
        if len(pose) == N_JOINTS:
            for leg in range(6):
                yaw, hip, knee = pose[leg * 3:leg * 3 + 3]
                foot = foot_from(hip, knee)
                per_leg.append({
                    "leg": leg,
                    "yaw_deg": round(yaw, 3),
                    "hip_deg": round(hip, 3),
                    "knee_deg": round(knee, 3),
                    **foot,
                })
        else:
            for leg in range(6):
                hip = float(plant.get("hip_deg", 19.0))
                knee = float(plant.get("knee_deg", 28.0))
                foot = foot_from(hip, knee)
                per_leg.append({
                    "leg": leg,
                    "yaw_deg": 0.0,
                    "hip_deg": round(hip, 3),
                    "knee_deg": round(knee, 3),
                    **foot,
                })

        z_vals = [float(row["z_mm"]) for row in per_leg]
        radial_vals = [float(row["radial_mm"]) for row in per_leg]
        hip_vals = [float(row["hip_deg"]) for row in per_leg]
        knee_vals = [float(row["knee_deg"]) for row in per_leg]
        mean_hip_deg = (
            None if not hip_vals else sum(hip_vals) / len(hip_vals))
        mean_knee_deg = (
            None if not knee_vals else sum(knee_vals) / len(knee_vals))
        plant_samples = [{
            "accepted": True,
            "contact_detected": bool(plant.get("contact_found", True)),
            "leg": row["leg"],
            "yaw_deg": row["yaw_deg"],
            "hip_deg": row["hip_deg"],
            "knee_deg": row["knee_deg"],
            "reason": "plant_snapshot",
        } for row in per_leg]
        plant_fit = fit_contact_sweep(plant_samples)
        sweep = (
            geometry_sweep if geometry_sweep is not None
            else (self._latest_geometry_sweep_report()
                  if use_latest_sweep else None))
        sweep_samples = []
        sweep_fit = None
        if isinstance(sweep, dict):
            sweep_samples = list(sweep.get("samples") or [])
            plan = sweep.get("target_plan") or []
            if plan:
                by_target = {}
                for t in plan:
                    try:
                        key = (
                            int(t.get("leg")),
                            round(float(t.get("hip_deg")), 3),
                            round(float(t.get("knee_deg")), 3),
                        )
                        by_target[key] = float(t.get("base_z_mm"))
                    except (TypeError, ValueError):
                        continue
                fixed = []
                for s in sweep_samples:
                    row = dict(s)
                    if row.get("base_z_mm") is None:
                        try:
                            key = (
                                int(row.get("leg")),
                                round(float(row.get("target_hip_deg")), 3),
                                round(float(row.get("target_knee_deg")), 3),
                            )
                            if key in by_target:
                                row["base_z_mm"] = round(by_target[key], 2)
                        except (TypeError, ValueError):
                            pass
                    fixed.append(row)
                sweep_samples = fixed
            sweep_fit = sweep.get("fit")
            if not isinstance(sweep_fit, dict):
                sweep_fit = fit_contact_sweep(sweep_samples)
            else:
                sweep_fit = fit_contact_sweep(sweep_samples)
        def compare_fit_to_manual(fit: dict | None) -> dict:
            """Compare a contact/FK diagnostic fit to operator measurements."""
            if not isinstance(fit, dict):
                return {
                    "link_fit": {},
                    "link_mismatch": False,
                    "height_fit": {},
                    "height_mismatch": False,
                    "mismatch": False,
                    "notes": [],
                }
            fit_summary0 = fit.get("summary") or {}
            seg0 = fit.get("segment_fit") or {}
            fit_links0 = seg0.get("link_lengths_mm") or {}
            link_fit: dict = {}
            link_mismatch = False
            notes = []
            for name, manual_value in (
                    ("femur", manual_femur_mm),
                    ("tibia", manual_tibia_mm)):
                fit_value = self._maybe_float(fit_links0.get(name))
                if manual_value is None or fit_value is None:
                    continue
                delta = round(fit_value - manual_value, 2)
                pct = round(100.0 * delta / manual_value, 1)
                link_fit[name] = {
                    "fit_mm": round(fit_value, 2),
                    "manual_mm": round(manual_value, 2),
                    "delta_mm": delta,
                    "delta_pct": pct,
                }
                if abs(pct) > 20.0:
                    link_mismatch = True
                    notes.append(
                        f"{name} model {fit_value:.1f}mm vs manual "
                        f"{manual_value:.1f}mm ({pct:+.1f}%)")
            height_fit: dict = {}
            height_mismatch = False
            model_height = self._maybe_float(
                fit_summary0.get("mean_servo_height_mm"))
            if model_height is not None and manual_height_mm is not None:
                delta = round(model_height - manual_height_mm, 2)
                pct = round(100.0 * delta / manual_height_mm, 1)
                height_fit = {
                    "fit_mm": round(model_height, 2),
                    "manual_mm": round(manual_height_mm, 2),
                    "delta_mm": delta,
                    "delta_pct": pct,
                }
                if abs(delta) > 15.0:
                    height_mismatch = True
                    notes.append(
                        f"contact/FK height {model_height:.1f}mm vs manual "
                        f"{manual_height_mm:.1f}mm ({delta:+.1f}mm)")
            mismatch = bool(link_mismatch or height_mismatch)
            return {
                "link_fit": link_fit,
                "link_mismatch": link_mismatch,
                "height_fit": height_fit,
                "height_mismatch": height_mismatch,
                "mismatch": mismatch,
                "notes": notes,
            }

        sweep_manual = compare_fit_to_manual(sweep_fit)
        using_sweep_fit = bool(
            isinstance(sweep_fit, dict)
            and sweep_fit.get("ok")
            and not sweep_manual["mismatch"])
        effective_fit = sweep_fit if using_sweep_fit else plant_fit
        effective_fit = dict(effective_fit or {})
        effective_fit["source"] = (
            "contact_sweep" if using_sweep_fit else "plant_only")
        if isinstance(sweep_fit, dict) and not using_sweep_fit:
            rejected_status = (
                "manual_geometry_mismatch" if sweep_manual["mismatch"]
                else sweep_fit.get("status"))
            effective_fit["rejected_contact_sweep_status"] = rejected_status
            if sweep_manual["link_fit"]:
                effective_fit["rejected_contact_sweep_manual_link_fit"] = (
                    sweep_manual["link_fit"])
            if sweep_manual["height_fit"]:
                effective_fit["rejected_contact_sweep_manual_height_fit"] = (
                    sweep_manual["height_fit"])
            if sweep_manual["notes"]:
                effective_fit.setdefault("notes", [])
                effective_fit["notes"] = list(effective_fit["notes"]) + [
                    "Contact sweep rejected as a dimension source because it "
                    "does not agree with operator measurements.",
                    "Manual mismatch: " + "; ".join(sweep_manual["notes"]),
                    "Likely causes include hip zero/reference offset, boot "
                    "edge first-contact, floor compliance, or measuring a "
                    "different physical reference point than the FK model.",
                ]
        effective_manual = compare_fit_to_manual(effective_fit)
        manual_link_fit = (
            sweep_manual["link_fit"] or effective_manual["link_fit"])
        manual_link_mismatch = bool(
            sweep_manual["link_mismatch"]
            or effective_manual["link_mismatch"])
        manual_height_fit = (
            sweep_manual["height_fit"] or effective_manual["height_fit"])
        manual_height_mismatch = bool(
            sweep_manual["height_mismatch"]
            or effective_manual["height_mismatch"])
        manual_geometry_mismatch = bool(
            manual_link_mismatch or manual_height_mismatch)
        fit_summary = (effective_fit or {}).get("summary") or {}
        seg = (effective_fit or {}).get("segment_fit") or {}
        fit_links = seg.get("link_lengths_mm") or {}
        per_leg_heights_m = {}
        if manual_height_mm is not None:
            per_leg_heights_m = {
                str(leg): round(manual_height_mm * 0.001, 5)
                for leg in range(6)
            }
        elif using_sweep_fit:
            for row in (effective_fit or {}).get("per_leg") or []:
                try:
                    if row.get("servo_height_mm") is not None:
                        per_leg_heights_m[str(int(row["leg"]))] = round(
                            float(row["servo_height_mm"]) * 0.001, 5)
                except (KeyError, TypeError, ValueError):
                    pass
        mean_foot_z_mm = (
            None if not z_vals else round(sum(z_vals) / len(z_vals), 2))
        model_height_mm = self._maybe_float(
            fit_summary.get("mean_servo_height_mm"))
        if model_height_mm is None and mean_foot_z_mm is not None:
            model_height_mm = round(-mean_foot_z_mm, 2)
        height_delta_mm = (
            None if model_height_mm is None or manual_height_mm is None
            else round(model_height_mm - manual_height_mm, 2))
        manual_absolute_height_mm = None
        if (manual_femur_mm is not None and manual_tibia_mm is not None
                and mean_hip_deg is not None and mean_knee_deg is not None):
            hip = math.radians(mean_hip_deg)
            knee = math.radians(mean_knee_deg)
            manual_absolute_height_mm = round(
                manual_femur_mm * math.sin(hip)
                + manual_tibia_mm * math.sin(knee), 2)
        manual_zero_hypotheses = self._manual_zero_hypotheses(
            sweep_samples,
            manual_height_mm=manual_height_mm,
            manual_femur_mm=manual_femur_mm,
            manual_tibia_mm=manual_tibia_mm)
        nominal_center_radius_mm = round(CHASSIS_FLAT_TO_FLAT_MM / 2.0
                                         + COXA_MM, 2)
        center_radius_delta_mm = (
            None if manual_center_radius_mm is None
            else round(manual_center_radius_mm - nominal_center_radius_mm, 2))
        neutral_foot_z_m = (
            round(-manual_height_mm * 0.001, 5)
            if manual_height_mm is not None
            else (None if mean_foot_z_mm is None
                  else round(mean_foot_z_mm * 0.001, 5)))
        manual_links_m = None
        if manual_femur_mm is not None or manual_tibia_mm is not None:
            manual_links_m = {
                "coxa": round(COXA_MM * 0.001, 5),
                "femur": (
                    None if manual_femur_mm is None
                    else round(manual_femur_mm * 0.001, 5)),
                "tibia": (
                    None if manual_tibia_mm is None
                    else round(manual_tibia_mm * 0.001, 5)),
            }
            if manual_center_radius_mm is not None:
                manual_links_m["hip_center_radius"] = round(
                    manual_center_radius_mm * 0.001, 5)
        return {
            "ok": True,
            "schema_version": 6,
            "nominal_mm": {
                "coxa": COXA_MM,
                "femur": FEMUR_MM,
                "tibia": TIBIA_MM,
                "chassis_flat_to_flat": CHASSIS_FLAT_TO_FLAT_MM,
            },
            "manual_measurements": manual,
            "axis_limits_deg": {
                k: [float(v[0]), float(v[1])]
                for k, v in AXIS_LIMITS_DEG.items()
            },
            "plant": plant,
            "plant_joint_deg": pose or None,
            "per_leg": per_leg,
            "summary": {
                "mean_foot_z_mm": mean_foot_z_mm,
                "foot_z_spread_mm": (
                    None if not z_vals else round(max(z_vals) - min(z_vals), 2)),
                "mean_radial_mm": (
                    None if not radial_vals
                    else round(sum(radial_vals) / len(radial_vals), 2)),
                "radial_spread_mm": (
                    None if not radial_vals
                    else round(max(radial_vals) - min(radial_vals), 2)),
                "mean_servo_height_mm": (
                    fit_summary.get("mean_servo_height_mm")),
                "servo_height_spread_mm": (
                    fit_summary.get("servo_height_spread_mm")),
                "max_zero_hint_deg": fit_summary.get("max_zero_hint_deg"),
                "model_hip_pitch_height_mm": model_height_mm,
                "manual_hip_pitch_height_mm": manual_height_mm,
                "nominal_hip_center_radius_mm": nominal_center_radius_mm,
                "manual_hip_center_radius_mm": manual_center_radius_mm,
                "manual_femur_mm": manual_femur_mm,
                "manual_tibia_mm": manual_tibia_mm,
                "model_minus_manual_height_mm": height_delta_mm,
                "manual_absolute_height_mm": manual_absolute_height_mm,
                "manual_active_height_mm": manual_absolute_height_mm,
                "manual_absolute_minus_manual_height_mm": (
                    None if (manual_absolute_height_mm is None
                             or manual_height_mm is None)
                    else round(manual_absolute_height_mm
                               - manual_height_mm, 2)),
                "manual_center_minus_nominal_mm": center_radius_delta_mm,
                "manual_link_fit": manual_link_fit or None,
                "manual_link_mismatch": manual_link_mismatch,
                "manual_height_fit": manual_height_fit or None,
                "manual_height_mismatch": manual_height_mismatch,
                "manual_geometry_mismatch": manual_geometry_mismatch,
                "manual_zero_hypotheses": manual_zero_hypotheses,
                "active_angle_convention": "absolute_tibia",
                "height_source": (
                    "manual_operator_measurement"
                    if manual_height_mm is not None
                    else effective_fit.get("source")),
            },
            "effective_fit": effective_fit,
            "plant_only_fit": plant_fit,
            "contact_sweep": (
                None if not isinstance(sweep, dict) else {
                    "ok": (
                        bool((sweep_fit or {}).get("ok"))
                        and not sweep_manual["mismatch"]),
                    "status": (
                        "manual_geometry_mismatch" if sweep_manual["mismatch"]
                        else (sweep_fit or {}).get("status")),
                    "sample_count": (
                        (sweep_fit or {}).get("sample_count")
                        if isinstance(sweep_fit, dict)
                        else len(sweep_samples)),
                    "raw_sample_count": len(sweep_samples),
                    "log_name": sweep.get("log_name"),
                    "path": sweep.get("path"),
                    "latest": sweep.get("latest"),
                    "samples": sweep_samples,
                    "fit": sweep_fit,
                    "manual_link_fit": sweep_manual["link_fit"] or None,
                    "manual_link_mismatch": sweep_manual["link_mismatch"],
                    "manual_height_fit": sweep_manual["height_fit"] or None,
                    "manual_height_mismatch": sweep_manual["height_mismatch"],
                    "manual_geometry_mismatch": sweep_manual["mismatch"],
                    "manual_mismatch_notes": sweep_manual["notes"] or None,
                }),
            "mujoco_hint": {
                "link_lengths_m": {
                    "coxa": round(COXA_MM * 0.001, 5),
                    "femur": round(FEMUR_MM * 0.001, 5),
                    "tibia": round(TIBIA_MM * 0.001, 5),
                },
                "manual_link_lengths_m": manual_links_m,
                "effective_link_lengths_m": (
                    None if not seg.get("ok") else {
                        "coxa": round(
                            float(fit_links.get("coxa", COXA_MM)) * 0.001, 5),
                        "femur": round(
                            float(fit_links.get("femur", FEMUR_MM)) * 0.001, 5),
                        "tibia": round(
                            float(fit_links.get("tibia", TIBIA_MM)) * 0.001, 5),
                    }),
                "per_leg_servo_height_m": per_leg_heights_m or None,
                "per_leg_servo_height_source": (
                    "manual_operator_measurement"
                    if manual_height_mm is not None
                    else ("contact_sweep" if using_sweep_fit else None)),
                "plant_joint_deg": pose or None,
                "neutral_foot_z_m": neutral_foot_z_m,
                "neutral_foot_z_source": (
                    "manual_operator_measurement"
                    if manual_height_mm is not None else "fk_model"),
                "angle_convention": "knee_deg is tibia absolute angle",
                "angle_convention_key": "absolute_tibia",
            },
        }

    def _geometry_plausibility_check(
            self, *, geometry_sweep: dict | None = None) -> dict:
        """Read-only sanity gate for geometry evidence.

        This deliberately does not move the robot.  It decides whether the
        contact/sweep math is plausible enough to use as a dimension source,
        and records why not when the data is weak.
        """
        geom = self._geometry_report(
            geometry_sweep=geometry_sweep, use_latest_sweep=False)
        if not geom.get("ok"):
            return {
                "ok": False,
                "non_blocking": True,
                "mode": "geometry_plausibility",
                "error": geom.get("error") or "geometry report unavailable",
                "msg": geom.get("error") or "geometry report unavailable",
            }
        summary = geom.get("summary") or {}
        manual = geom.get("manual_measurements") or {}
        contact = geom.get("contact_sweep") or {}
        issues: list[str] = []
        warnings: list[str] = []
        if not manual.get("learned"):
            warnings.append(
                "no hand measurements saved; using nominal CAD/contact model")
        if summary.get("manual_geometry_mismatch"):
            issues.append(
                "contact-derived geometry disagrees with hand measurements")
        status = str(contact.get("status") or "").lower()
        sample_count = int(contact.get("sample_count") or 0)
        raw_count = int(contact.get("raw_sample_count") or sample_count or 0)
        if status in ("partial", "no_contacts", "not_enough_contacts"):
            warnings.append(
                f"contact sweep weak ({sample_count}/{raw_count} accepted)")
        if summary.get("max_zero_hint_deg") is not None:
            try:
                max_zero = float(summary["max_zero_hint_deg"])
                if max_zero > 10.0:
                    warnings.append(
                        f"large relative zero hint ({max_zero:.1f} deg)")
            except (TypeError, ValueError):
                pass

        ok = not issues
        msg = (
            "geometry plausible"
            if ok and not warnings else
            "geometry plausible with warnings: " + "; ".join(warnings)
            if ok else
            "geometry not trusted: " + "; ".join(issues)
        )
        return {
            "ok": ok,
            "non_blocking": True,
            "mode": "geometry_plausibility",
            "error": None if ok else msg,
            "warning": "; ".join(warnings) if warnings else None,
            "msg": msg,
            "manual_geometry_mismatch": bool(
                summary.get("manual_geometry_mismatch")),
            "manual_measurements_saved": bool(manual.get("learned")),
            "contact_sweep_status": contact.get("status"),
            "contact_sample_count": sample_count,
            "contact_raw_sample_count": raw_count,
            "max_zero_hint_deg": summary.get("max_zero_hint_deg"),
            "benefit": (
                "prevents weak contact probes from silently becoming sim "
                "dimensions"),
        }

    def _imu_frame_validation_check(
            self, body_frame_result: dict | None = None) -> dict:
        """Read-only summary of whether the IMU body-frame map is usable."""
        imu = self.imu_state()
        bf = None
        if isinstance(body_frame_result, dict):
            bf = body_frame_result.get("body_frame")
        if not isinstance(bf, dict):
            bf = imu.get("body_frame")
        if not isinstance(bf, dict):
            return {
                "ok": False,
                "non_blocking": True,
                "mode": "imu_frame_validation",
                "error": "no saved IMU body-frame map",
                "msg": (
                    "no saved IMU body-frame map; trim can use raw tilt only"),
                "benefit": (
                    "confirms calibrated pitch/roll signs before balance trim "
                    "uses them"),
            }
        measured = self._maybe_float(bf.get("measured_lean_deg"))
        axis = str(bf.get("pitch_axis") or "?")
        source = str(bf.get("source") or "?")
        warnings: list[str] = []
        if measured is None:
            warnings.append("saved map has no measured lean magnitude")
        elif measured < 8.0:
            warnings.append(f"lean sample small ({measured:.1f} deg)")
        if isinstance(body_frame_result, dict) and body_frame_result.get("warning"):
            warnings.append(str(body_frame_result["warning"]))
        ok = measured is None or measured >= 6.0
        msg = (
            f"IMU body frame {axis}; rear-lean "
            f"{measured:.1f} deg" if measured is not None
            else f"IMU body frame {axis}"
        )
        if warnings:
            msg += "; " + "; ".join(warnings)
        return {
            "ok": ok,
            "non_blocking": True,
            "mode": "imu_frame_validation",
            "error": None if ok else msg,
            "warning": "; ".join(warnings) if warnings else None,
            "msg": msg,
            "body_frame": bf,
            "pitch_axis": axis,
            "source": source,
            "measured_lean_deg": measured,
            "benefit": (
                "checks that mounted IMU axes map to robot body pitch before "
                "quad balance correction"),
        }

    def _read_feedback_map(self, bus=None) -> dict[int, dict]:
        if bus is None:
            return {}
        fb: dict[int, dict] = {}
        read_all = getattr(bus, "read_all_feedback", None)
        if callable(read_all):
            try:
                bulk = read_all()
                if isinstance(bulk, dict):
                    for key, row in bulk.items():
                        try:
                            joint = int(key)
                        except (TypeError, ValueError):
                            continue
                        if 0 <= joint < N_JOINTS and isinstance(row, dict):
                            fb[joint] = row
            except Exception:
                fb = {}
        if len(fb) < N_JOINTS:
            read_one = getattr(bus, "read_feedback", None)
            if callable(read_one):
                for joint in range(N_JOINTS):
                    if joint in fb:
                        continue
                    try:
                        row = read_one(joint)
                    except Exception:
                        row = None
                    if isinstance(row, dict):
                        fb[joint] = row
        return fb

    def _actuator_report(self, bus=None) -> dict:
        log_dir = lc_dir() / "logs"
        model_paths = (
            log_dir / "motor_model.json",
            lc_dir().parent
            / "rl_move" / "hardware_traces" / "motor_model.json",
        )
        learned = None
        for path in model_paths:
            if not path.is_file():
                continue
            try:
                learned = json.loads(path.read_text())
                learned["path"] = str(path)
                break
            except (OSError, ValueError):
                continue
        out: dict = {
            "ok": True,
            "learned_model": learned,
            "snapshot": None,
        }
        if bus is None:
            return out
        fb = self._read_feedback_map(bus)
        rows = []
        volts = []
        temps = []
        currents = []
        for joint in range(N_JOINTS):
            row = fb.get(joint)
            if not row:
                continue
            sid = joint_to_servo_id(joint)
            cur = abs(float(row.get("current_a") or 0.0))
            volt = float(row.get("volt") or 0.0)
            temp = float(row.get("temp_c") or 0.0)
            if volt > 0.0:
                volts.append(volt)
            if temp > 0.0:
                temps.append(temp)
            currents.append(cur)
            rows.append({
                "joint": joint,
                "id": sid,
                "name": joint_label(joint, self.names),
                "axis": AXIS[joint % 3],
                "leg": joint // 3,
                "deg": round(float(row.get("deg") or 0.0), 3),
                "current_a": round(cur, 3),
                "speed_deg_s": round(float(row.get("speed_deg_s") or 0.0), 2),
                "load_pct": round(float(row.get("load_pct") or 0.0), 1),
                "volt": round(volt, 2),
                "temp_c": round(temp, 1),
            })
        out["snapshot"] = {
            "live_joints": len(rows),
            "joints": rows,
            "min_volt": None if not volts else round(min(volts), 2),
            "max_temp_c": None if not temps else round(max(temps), 1),
            "max_current_a": None if not currents else round(max(currents), 3),
        }
        return out

    def _bus_power_check(self, bus=None) -> dict:
        """Read-only bus/power/thermal check from the actuator snapshot."""
        if bus is None:
            return {
                "ok": False,
                "skipped": True,
                "non_blocking": True,
                "mode": "bus_power_health",
                "msg": "no bus; power health not available",
            }
        act = self._actuator_report(bus)
        snap = act.get("snapshot") or {}
        live = int(snap.get("live_joints") or 0)
        min_volt = self._maybe_float(snap.get("min_volt"))
        max_temp = self._maybe_float(snap.get("max_temp_c"))
        max_current = self._maybe_float(snap.get("max_current_a"))
        issues: list[str] = []
        warnings: list[str] = []
        if live < N_JOINTS:
            issues.append(f"{live}/{N_JOINTS} servos live")
        if min_volt is not None and min_volt < 10.8:
            warnings.append(f"low bus voltage {min_volt:.2f}V")
        if max_temp is not None and max_temp > 65.0:
            warnings.append(f"hot servo {max_temp:.1f}C")
        if max_current is not None and max_current > 2.8:
            warnings.append(f"high holding current {max_current:.2f}A")
        ok = not issues
        bits = [f"{live}/{N_JOINTS} servos live"]
        if min_volt is not None:
            bits.append(f"Vmin {min_volt:.2f}")
        if max_current is not None:
            bits.append(f"Ipeak {max_current:.2f}A")
        if max_temp is not None:
            bits.append(f"Tmax {max_temp:.1f}C")
        msg = "; ".join(bits)
        if issues:
            msg += "; " + "; ".join(issues)
        if warnings:
            msg += "; " + "; ".join(warnings)
        return {
            "ok": ok,
            "non_blocking": True,
            "mode": "bus_power_health",
            "error": None if ok else msg,
            "warning": "; ".join(warnings) if warnings else None,
            "msg": msg,
            "snapshot": snap,
            "benefit": (
                "separates bus/power/thermal problems from bad gaits or bad "
                "geometry"),
        }

    def _new_bus_quality_tracker(self, label: str) -> _BusQualityTracker:
        return _BusQualityTracker(label)

    def _bus_error_rate_probe(
            self, bus=None, *, label: str, mode: str,
            seconds: float = BUS_ERROR_RATE_STILL_SECONDS,
            hz: float = BUS_ERROR_RATE_HZ,
            abort_check=lambda: False) -> dict:
        """Run a short read-only 100 Hz bus error-rate probe."""
        if bus is None:
            return {
                "ok": False,
                "skipped": True,
                "non_blocking": True,
                "mode": mode,
                "label": label,
                "msg": "no bus; bus error rate not available",
            }
        method = "read_snapshot"
        if not callable(getattr(bus, method, None)):
            method = "read_all_positions"
        fn = getattr(bus, method, None)
        if not callable(fn):
            return {
                "ok": False,
                "skipped": True,
                "non_blocking": True,
                "mode": mode,
                "label": label,
                "msg": "bus has no bulk read path for error-rate probe",
            }

        tracker = self._new_bus_quality_tracker(label)
        tracked = tracker.wrap(bus)
        fn = getattr(tracked, method)
        seconds = max(0.2, min(10.0, float(seconds)))
        hz = max(1.0, min(250.0, float(hz)))
        period = 1.0 / hz
        deadline = time.monotonic() + seconds
        next_t = time.monotonic()
        late_ticks = 0
        while time.monotonic() < deadline:
            if abort_check():
                res = tracker.summary(
                    mode=mode, target_hz=hz, seconds_target=seconds)
                res["aborted"] = True
                res["ok"] = False
                res["error"] = "bus error-rate probe aborted"
                return res
            now = time.monotonic()
            if now < next_t:
                time.sleep(next_t - now)
            elif now - next_t > period:
                late_ticks += 1
            try:
                fn()
            except Exception:
                pass
            next_t += period
        res = tracker.summary(mode=mode, target_hz=hz,
                              seconds_target=seconds)
        res["read_method"] = method
        res["late_ticks"] = late_ticks
        return res

    def _proprioception_check(
            self, bus=None, *, expected_pose: list[float] | None = None,
            expected_name: str = "pose", tol_deg: float = 8.0,
            current_warn_a: float = 2.0) -> dict:
        """Score command-vs-encoder feedback for a pose already reached."""
        if bus is None:
            return {"ok": False, "mode": "proprioception_check",
                    "error": "no bus"}
        expected = None
        if expected_pose is not None and len(expected_pose) == N_JOINTS:
            expected = [float(v) for v in expected_pose]
        fb = self._read_feedback_map(bus)
        if not fb:
            return {"ok": False, "mode": "proprioception_check",
                    "error": "no servo feedback"}

        volts: list[float] = []
        temps: list[float] = []
        currents: list[float] = []
        errors: list[float] = []
        worst: list[dict] = []
        joints: list[dict] = []
        for joint in range(N_JOINTS):
            row = fb.get(joint)
            if not row:
                continue
            deg = float(row.get("deg") or 0.0)
            cur = abs(float(row.get("current_a") or 0.0))
            volt = float(row.get("volt") or 0.0)
            temp = float(row.get("temp_c") or 0.0)
            currents.append(cur)
            if volt > 0:
                volts.append(volt)
            if temp > 0:
                temps.append(temp)
            item = {
                "joint": joint,
                "id": joint_to_servo_id(joint),
                "name": joint_label(joint, self.names),
                "axis": AXIS[joint % 3],
                "leg": joint // 3,
                "deg": round(deg, 3),
                "current_a": round(cur, 3),
                "load_pct": round(float(row.get("load_pct") or 0.0), 1),
                "speed_deg_s": round(float(row.get("speed_deg_s") or 0.0), 2),
            }
            if expected is not None:
                cmd = expected[joint]
                err = deg - cmd
                abs_err = abs(err)
                errors.append(abs_err)
                item["expected_deg"] = round(cmd, 3)
                item["error_deg"] = round(err, 3)
                worst.append({
                    **item,
                    "abs_error_deg": round(abs_err, 3),
                })
            joints.append(item)

        live = len(fb)
        max_err = max(errors) if errors else None
        mean_err = (sum(errors) / len(errors)) if errors else None
        worst.sort(key=lambda r: float(r.get("abs_error_deg") or 0.0),
                   reverse=True)
        max_cur = max(currents) if currents else None
        ok = live == N_JOINTS
        if max_err is not None and max_err > tol_deg:
            ok = False
        if max_cur is not None and max_cur > current_warn_a:
            ok = False

        msg_bits = [f"{live}/{N_JOINTS} joints live"]
        if max_err is not None:
            label = worst[0]["name"] if worst else "joint"
            msg_bits.append(
                f"{expected_name} max err {max_err:.1f}deg ({label})")
        if max_cur is not None:
            msg_bits.append(f"Ipeak {max_cur:.2f}A")
        msg = "; ".join(msg_bits)
        out = {
            "ok": ok,
            "mode": "proprioception_check",
            "expected": expected_name if expected is not None else None,
            "live_joints": live,
            "max_abs_error_deg": (
                None if max_err is None else round(max_err, 3)),
            "mean_abs_error_deg": (
                None if mean_err is None else round(mean_err, 3)),
            "tol_deg": round(float(tol_deg), 3),
            "max_current_a": (
                None if max_cur is None else round(max_cur, 3)),
            "current_warn_a": round(float(current_warn_a), 3),
            "min_volt": None if not volts else round(min(volts), 2),
            "max_temp_c": None if not temps else round(max(temps), 1),
            "worst_joints": worst[:6],
            "joints": joints,
            "msg": msg,
            "notes": [
                "This compares the requested pose to encoder feedback; it "
                "does not prove where the feet are in the room.",
                "Camera or motion-capture evidence is needed to separate true "
                "body motion from slip/compliance.",
            ],
        }
        if not ok:
            out["error"] = msg
        return out

    def _camera_witness_check(self) -> dict:
        return {
            "ok": True,
            "skipped": True,
            "non_blocking": True,
            "mode": "camera_witness",
            "msg": (
                "camera witness not configured; use a synced bench video or "
                "future camera feed to compare visible body/foot motion "
                "against servo proprioception"),
            "requires": [
                "fixed camera view containing the whole robot",
                "timestamped frame/video tied to the checkup phase",
                "body/foot markers or a visual tracker before quantitative CV",
            ],
        }

    def _run_stability_margin_check(self, bus, *, abort_check,
                                    on_progress) -> dict:
        """Gentle stance-bias probe for tilt margin.

        This intentionally estimates a usable/reversible margin. It does not
        try to discover the true fall angle by knocking the robot over.
        """
        try:
            from feetech_bus import AXIS_LIMITS_DEG, standing_pose_degrees
            from imu_calibrate import imu_tilt_deg
            from inplace_demos import (
                _enable_torque, _hold_here, _live_robot_ids,
                _set_torque_limit, _write_pose, ease_to_pose,
            )
        except ImportError as e:
            return {"ok": False, "mode": "stability_margin",
                    "non_blocking": True, "error": str(e), "msg": str(e)}

        def progress(msg: str, **extra) -> None:
            on_progress({"msg": msg, "mode": "stability_margin", **extra})

        def clamp(x: float, lo: float, hi: float) -> float:
            return max(float(lo), min(float(hi), float(x)))

        def read_imu():
            fn = getattr(bus, "read_imu", None)
            if not callable(fn):
                return None
            try:
                return fn(apply_calib=True)
            except TypeError:
                try:
                    return fn()
                except Exception:
                    return None
            except Exception:
                return None

        def read_tilt() -> tuple[float, float] | None:
            imu = read_imu()
            if not isinstance(imu, dict):
                return None
            tilt = imu_tilt_deg(imu)
            if not tilt or tilt[0] is None or tilt[1] is None:
                return None
            return float(tilt[0]), float(tilt[1])

        def read_peak_current() -> float:
            fb = self._read_feedback_map(bus)
            vals = [abs(float((row or {}).get("current_a") or 0.0))
                    for row in fb.values()]
            return max(vals or [0.0])

        def recover_base(live: set[int], base: list[float]) -> None:
            try:
                _write_pose(bus, base, live, speed=120, acc=10)
                time.sleep(0.45)
                _hold_here(bus, live)
            except Exception:
                pass

        live = _live_robot_ids(bus)
        if len(live) < 12:
            return {"ok": False, "mode": "stability_margin",
                    "skipped": True, "non_blocking": True,
                    "msg": f"need more servos (live={len(live)})",
                    "live": sorted(live)}
        try:
            base = [float(x) for x in standing_pose_degrees()]
        except Exception as e:
            return {"ok": False, "mode": "stability_margin",
                    "skipped": True, "non_blocking": True,
                    "msg": f"stand pose unavailable: {e}"}
        if len(base) != N_JOINTS:
            return {"ok": False, "mode": "stability_margin",
                    "skipped": True, "non_blocking": True,
                    "msg": "stand pose is not 18 joints"}

        base_tilt = read_tilt()
        if base_tilt is None:
            return {
                "ok": False,
                "mode": "stability_margin",
                "skipped": True,
                "non_blocking": True,
                "msg": "no calibrated IMU tilt; margin probe skipped",
            }

        hip_lo, hip_hi = AXIS_LIMITS_DEG.get(1, (-80.0, 40.0))
        knee_lo, knee_hi = AXIS_LIMITS_DEG.get(2, (-20.0, 150.0))
        samples: list[dict] = []
        directions = [
            ("front", (1.0, 0.0)),
            ("rear", (-1.0, 0.0)),
            ("left", (0.0, 1.0)),
            ("right", (0.0, -1.0)),
        ]
        amps = (1.5, 3.0, 4.5, 6.0)
        soft_tilt = 14.0
        hard_tilt = 28.0
        current_warn = 2.3
        current_hard = 2.9

        def pose_for(vec: tuple[float, float], amp: float) -> list[float]:
            q = list(base)
            dx, dy = vec
            for leg in range(6):
                a = (leg + 0.5) * math.pi / 3.0
                weight = math.cos(a) * dx + math.sin(a) * dy
                j = leg * 3
                q[j + 1] = clamp(base[j + 1] + weight * amp, hip_lo, hip_hi)
                q[j + 2] = clamp(
                    base[j + 2] - weight * amp * 0.20, knee_lo, knee_hi)
            return q

        def sample(label: str, amp: float) -> dict:
            tilt = read_tilt()
            if tilt is None:
                roll_delta = pitch_delta = 0.0
            else:
                roll_delta = tilt[0] - base_tilt[0]
                pitch_delta = tilt[1] - base_tilt[1]
            row = {
                "direction": label,
                "cmd_amp_deg": round(float(amp), 2),
                "roll_delta_deg": round(float(roll_delta), 2),
                "pitch_delta_deg": round(float(pitch_delta), 2),
                "tilt_delta_deg": round(
                    max(abs(roll_delta), abs(pitch_delta)), 2),
                "max_current_a": round(read_peak_current(), 3),
            }
            samples.append(row)
            return row

        _enable_torque(bus, live)
        _set_torque_limit(bus, live, 650)
        try:
            progress("Stability: settle plant")
            if not ease_to_pose(bus, base, abort_check=abort_check,
                                seconds=1.8, label="stability plant"):
                _set_torque_limit(bus, live, 1000)
                return {"ok": False, "aborted": True,
                        "mode": "stability_margin",
                        "error": "plant settle aborted"}
            for label, vec in directions:
                direction_rows: list[dict] = []
                for amp in amps:
                    if abort_check():
                        _hold_here(bus, live)
                        return {"ok": False, "aborted": True,
                                "mode": "stability_margin",
                                "samples": samples}
                    progress(f"Stability: {label} bias {amp:.1f} deg")
                    _write_pose(bus, pose_for(vec, amp), live,
                                speed=105, acc=10)
                    time.sleep(0.38)
                    row = sample(label, amp)
                    direction_rows.append(row)
                    if float(row["max_current_a"]) > current_hard:
                        recover_base(live, base)
                        return {
                            "ok": False,
                            "recoverable": True,
                            "guard_stop": True,
                            "mode": "stability_margin",
                            "error": (
                                f"{label} current guard "
                                f"{row['max_current_a']:.2f}A"),
                            "samples": samples,
                        }
                    if float(row["tilt_delta_deg"]) > hard_tilt:
                        recover_base(live, base)
                        return {
                            "ok": False,
                            "recoverable": True,
                            "guard_stop": True,
                            "mode": "stability_margin",
                            "error": (
                                f"{label} hard tilt guard "
                                f"{row['tilt_delta_deg']:.1f} deg"),
                            "samples": samples,
                        }
                    if (float(row["tilt_delta_deg"]) >= soft_tilt
                            or float(row["max_current_a"]) >= current_warn):
                        break
                recover_base(live, base)
                if direction_rows:
                    last = direction_rows[-1]
                    progress(
                        f"Stability: {label} usable through "
                        f"{last['cmd_amp_deg']:.1f} deg")
        finally:
            _set_torque_limit(bus, live, 1000)

        max_tilt = max([float(r.get("tilt_delta_deg") or 0.0)
                        for r in samples] or [0.0])
        max_current = max([float(r.get("max_current_a") or 0.0)
                           for r in samples] or [0.0])
        by_direction: dict[str, dict] = {}
        for label, _vec in directions:
            rows = [r for r in samples if r.get("direction") == label]
            if not rows:
                continue
            by_direction[label] = {
                "max_cmd_amp_deg": max(
                    float(r.get("cmd_amp_deg") or 0.0) for r in rows),
                "max_tilt_delta_deg": max(
                    float(r.get("tilt_delta_deg") or 0.0) for r in rows),
                "max_current_a": max(
                    float(r.get("max_current_a") or 0.0) for r in rows),
            }
        msg = (
            f"stable through bias tests; max tilt {max_tilt:.1f} deg, "
            f"Ipeak {max_current:.2f}A")
        return {
            "ok": bool(samples),
            "mode": "stability_margin",
            "margin_is_lower_bound": True,
            "max_measured_tilt_delta_deg": round(max_tilt, 2),
            "max_current_a": round(max_current, 3),
            "by_direction": by_direction,
            "samples": samples,
            "msg": msg,
            "benefit": (
                "estimates reversible tilt margin for gait trim without "
                "intentionally falling"),
        }

    def _run_mass_shift_response_check(self, bus, *, abort_check,
                                       on_progress) -> dict:
        """Measure how lifted limb groups change steady pitch/roll."""
        try:
            from feetech_bus import AXIS_LIMITS_DEG, standing_pose_degrees
            from imu_calibrate import imu_tilt_deg
            from inplace_demos import (
                _enable_torque, _hold_here, _live_robot_ids,
                _set_torque_limit, _write_pose, ease_to_pose,
            )
        except ImportError as e:
            return {"ok": False, "mode": "mass_shift_response",
                    "non_blocking": True, "error": str(e), "msg": str(e)}

        def progress(msg: str, **extra) -> None:
            on_progress({"msg": msg, "mode": "mass_shift_response", **extra})

        def clamp(x: float, lo: float, hi: float) -> float:
            return max(float(lo), min(float(hi), float(x)))

        def read_imu():
            fn = getattr(bus, "read_imu", None)
            if not callable(fn):
                return None
            try:
                return fn(apply_calib=True)
            except TypeError:
                try:
                    return fn()
                except Exception:
                    return None
            except Exception:
                return None

        def read_tilt() -> tuple[float, float] | None:
            imu = read_imu()
            if not isinstance(imu, dict):
                return None
            tilt = imu_tilt_deg(imu)
            if not tilt or tilt[0] is None or tilt[1] is None:
                return None
            return float(tilt[0]), float(tilt[1])

        def read_peak_current() -> float:
            fb = self._read_feedback_map(bus)
            vals = [abs(float((row or {}).get("current_a") or 0.0))
                    for row in fb.values()]
            return max(vals or [0.0])

        def recover_base(live: set[int], base: list[float]) -> None:
            try:
                _write_pose(bus, base, live, speed=120, acc=10)
                time.sleep(0.45)
                _hold_here(bus, live)
            except Exception:
                pass

        live = _live_robot_ids(bus)
        if len(live) < 12:
            return {"ok": False, "mode": "mass_shift_response",
                    "skipped": True, "non_blocking": True,
                    "msg": f"need more servos (live={len(live)})",
                    "live": sorted(live)}
        try:
            base = [float(x) for x in standing_pose_degrees()]
        except Exception as e:
            return {"ok": False, "mode": "mass_shift_response",
                    "skipped": True, "non_blocking": True,
                    "msg": f"stand pose unavailable: {e}"}
        if len(base) != N_JOINTS:
            return {"ok": False, "mode": "mass_shift_response",
                    "skipped": True, "non_blocking": True,
                    "msg": "stand pose is not 18 joints"}

        base_tilt = read_tilt()
        if base_tilt is None:
            return {
                "ok": False,
                "mode": "mass_shift_response",
                "skipped": True,
                "non_blocking": True,
                "msg": "no calibrated IMU tilt; mass-shift probe skipped",
            }

        yaw_lo, yaw_hi = AXIS_LIMITS_DEG.get(0, (-35.0, 35.0))
        hip_lo, hip_hi = AXIS_LIMITS_DEG.get(1, (-80.0, 40.0))
        knee_lo, knee_hi = AXIS_LIMITS_DEG.get(2, (-20.0, 150.0))
        lift_hip = 8.0
        lift_knee = 18.0
        trials = [
            ("front_pair_up", (0, 5)),
            ("rear_pair_up", (2, 3)),
            ("left_pair_up", (1, 2)),
            ("right_pair_up", (3, 4)),
            ("tripod_024_up", (0, 2, 4)),
        ]
        samples: list[dict] = []
        hard_tilt = 28.0
        current_hard = 2.9

        def pose_for(legs: tuple[int, ...]) -> list[float]:
            q = list(base)
            for leg in legs:
                j = leg * 3
                q[j] = clamp(0.0, yaw_lo, yaw_hi)
                q[j + 1] = clamp(lift_hip, hip_lo, hip_hi)
                q[j + 2] = clamp(lift_knee, knee_lo, knee_hi)
            return q

        def sample(label: str, legs: tuple[int, ...]) -> dict:
            tilt = read_tilt()
            if tilt is None:
                roll_delta = pitch_delta = 0.0
            else:
                roll_delta = tilt[0] - base_tilt[0]
                pitch_delta = tilt[1] - base_tilt[1]
            row = {
                "pose": label,
                "legs": list(legs),
                "roll_delta_deg": round(float(roll_delta), 2),
                "pitch_delta_deg": round(float(pitch_delta), 2),
                "tilt_delta_deg": round(
                    max(abs(roll_delta), abs(pitch_delta)), 2),
                "max_current_a": round(read_peak_current(), 3),
            }
            samples.append(row)
            return row

        _enable_torque(bus, live)
        _set_torque_limit(bus, live, 650)
        try:
            progress("Mass shift: settle plant")
            if not ease_to_pose(bus, base, abort_check=abort_check,
                                seconds=1.8, label="mass shift plant"):
                _set_torque_limit(bus, live, 1000)
                return {"ok": False, "aborted": True,
                        "mode": "mass_shift_response",
                        "error": "plant settle aborted"}
            for label, legs in trials:
                if abort_check():
                    _hold_here(bus, live)
                    return {"ok": False, "aborted": True,
                            "mode": "mass_shift_response",
                            "samples": samples}
                progress(f"Mass shift: {label}")
                _write_pose(bus, pose_for(legs), live, speed=105, acc=10)
                time.sleep(0.75)
                row = sample(label, legs)
                recover_base(live, base)
                if float(row["max_current_a"]) > current_hard:
                    return {
                        "ok": False,
                        "recoverable": True,
                        "guard_stop": True,
                        "mode": "mass_shift_response",
                        "error": (
                            f"{label} current guard "
                            f"{row['max_current_a']:.2f}A"),
                        "samples": samples,
                    }
                if float(row["tilt_delta_deg"]) > hard_tilt:
                    return {
                        "ok": False,
                        "recoverable": True,
                        "guard_stop": True,
                        "mode": "mass_shift_response",
                        "error": (
                            f"{label} hard tilt guard "
                            f"{row['tilt_delta_deg']:.1f} deg"),
                        "samples": samples,
                    }
        finally:
            _set_torque_limit(bus, live, 1000)

        max_pitch = max([abs(float(r.get("pitch_delta_deg") or 0.0))
                         for r in samples] or [0.0])
        max_roll = max([abs(float(r.get("roll_delta_deg") or 0.0))
                        for r in samples] or [0.0])
        max_current = max([float(r.get("max_current_a") or 0.0)
                           for r in samples] or [0.0])
        largest = max(
            samples,
            key=lambda r: float(r.get("tilt_delta_deg") or 0.0),
            default=None)
        msg = (
            f"mass shift max pitch {max_pitch:.1f} deg, "
            f"max roll {max_roll:.1f} deg")
        if largest:
            msg += f"; largest {largest.get('pose')}"
        return {
            "ok": bool(samples),
            "mode": "mass_shift_response",
            "max_pitch_delta_deg": round(max_pitch, 2),
            "max_roll_delta_deg": round(max_roll, 2),
            "max_current_a": round(max_current, 3),
            "largest_response": largest,
            "samples": samples,
            "msg": msg,
            "benefit": (
                "estimates limb mass/center-of-mass coupling for MuJoCo mass "
                "distribution and dance/quad balance tuning"),
        }

    def _save_calibration_report(
            self, *, phases: list[dict] | None = None,
            bus=None, traction: dict | None = None,
            geometry_sweep: dict | None = None,
            geometry_check: dict | None = None,
            imu_frame_check: dict | None = None,
            stability_margin: dict | None = None,
            mass_shift: dict | None = None,
            proprioception: dict | None = None,
            camera_witness: dict | None = None,
            bus_power: dict | None = None,
            bus_error_rate: dict | None = None) -> dict:
        log_dir = lc_dir() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        path = log_dir / f"calibration_report_{stamp}.json"
        latest = log_dir / "calibration_report_latest.json"
        phase_rows = phases or []
        diagnostic_issues = self._checkup_diagnostic_issues(phase_rows)
        ok = (
            True if not phase_rows
            else self._checkup_blocking_problem(phase_rows) is None)
        report = {
            "ok": ok,
            "mode": "calibration_report",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "msg": (
                "checkup complete with diagnostic issues; see phases"
                if ok and diagnostic_issues else
                "checkup complete"
                if ok else "checkup complete with issues; see phases"),
            "diagnostic_issue_count": len(diagnostic_issues),
            "phases": phase_rows,
            "geometry": self._geometry_report(
                geometry_sweep=geometry_sweep,
                use_latest_sweep=(not phase_rows)),
            "geometry_check": geometry_check,
            "imu": self.imu_state(),
            "imu_frame_check": imu_frame_check,
            "stability_margin": stability_margin,
            "mass_shift": mass_shift,
            "traction": traction,
            "proprioception": proprioception,
            "camera_witness": camera_witness,
            "bus_power": bus_power,
            "bus_error_rate": bus_error_rate,
            "actuators": self._actuator_report(bus),
            "path": str(path),
            "log_name": path.name,
            "latest": str(latest),
            "notes": [
                "geometry.nominal_mm is the CAD/link model",
                "geometry.manual_measurements are operator tape/caliper "
                "values; they do not automatically change motion kinematics",
                "geometry.plant_joint_deg and geometry.per_leg are measured "
                "stand/ground-contact calibration outputs",
                "geometry.effective_fit is a contact-height consistency "
                "diagnostic; vertical floor contacts alone do not identify "
                "absolute femur/tibia lengths without independent height/scale",
                "geometry.contact_sweep samples are raw per-leg contact poses "
                "used to estimate contact-height residuals and zero hints",
                "geometry_check says whether contact/FK dimensions should be "
                "trusted as dimensions or treated as diagnostics only",
                "imu_frame_check validates the saved body-pitch axis/sign map; "
                "weak maps are warnings unless motion safety is involved",
                "stability_margin uses small reversible stance biases to "
                "estimate usable tilt margin; it is a lower bound, not a fall "
                "test",
                "mass_shift measures how lifted limb groups change steady "
                "pitch/roll, which helps tune sim mass distribution",
                "traction is an onboard planted shear slip signature during "
                "checkup; the standalone slip tool runs the heavier "
                "loaded-vs-hover drag, and neither is an exact coefficient of "
                "friction",
                "proprioception compares commanded joint angles with live "
                "encoder feedback; camera/vision is the independent witness "
                "needed to observe body/foot motion and slip",
                "camera_witness is currently a non-blocking hook unless a "
                "synced camera source is supplied",
                "bus_power is read-only health evidence: live servos, voltage, "
                "current, and temperature",
                "bus_error_rate records still 100Hz read-only snapshots and "
                "the moving-phase transactions observed during checkup; "
                "nonzero rates point to serial timing, wiring, or power "
                "margin before blaming policy behavior",
                "actuators.learned_model comes from the optional motor "
                "dynamics/sysid run when present",
            ],
        }
        path.write_text(json.dumps(report, indent=2) + "\n")
        latest.write_text(json.dumps(report, indent=2) + "\n")
        return report

    def calibration_report(self) -> dict:
        report = self._latest_calibration_report()
        if report is not None:
            return report
        bus = None if self.drive.dry_run else getattr(self.drive, "bus", None)
        return self._save_calibration_report(bus=bus)

    def _calibrate_quad_body_frame(self, bus, *, abort_check,
                                   on_progress) -> dict:
        try:
            from imu_calibrate import (load_imu_calib,
                                       imu_body_frame_from_roll_pitch,
                                       imu_tilt_deg, save_imu_body_frame)
            from inplace_demos import run_demo
            from hexapod_core.quad_walk import GAITS
        except ImportError as e:
            return {"ok": False, "mode": "imu_body_frame", "error": str(e)}

        def progress(msg: str) -> None:
            on_progress({"msg": msg, "mode": "imu_body_frame"})

        progress("IMU body frame: rear up")
        rear_status = run_demo(
            bus, "quad_rear", seconds=8.0, speed=0.75,
            abort_check=abort_check,
            status_cb=lambda s: on_progress({
                "msg": "IMU body frame: " + str(s),
                "mode": "imu_body_frame",
            }))
        if abort_check() or rear_status != "done":
            msg = f"quad rear interrupted ({rear_status})"
            return {
                "ok": False,
                "aborted": bool(abort_check()),
                "mode": "imu_body_frame",
                "error": msg,
                "msg": msg,
                "rear_status": rear_status,
            }

        samples: list[tuple[float, float]] = []
        read_imu = getattr(bus, "read_imu", None)
        if callable(read_imu):
            for _ in range(10):
                if abort_check():
                    break
                try:
                    imu = read_imu(apply_calib=True)
                except TypeError:
                    imu = read_imu()
                except Exception:
                    imu = None
                if isinstance(imu, dict):
                    rp = imu_tilt_deg(imu)
                    if rp is not None:
                        samples.append(rp)
                time.sleep(0.08)

        down_status = "skipped"
        try:
            progress("IMU body frame: come down")
            down_status = run_demo(
                bus, "quad_down", speed=0.75, abort_check=abort_check,
                quad_reared=True,
                status_cb=lambda s: on_progress({
                    "msg": "IMU body frame: " + str(s),
                    "mode": "imu_body_frame",
                }))
        finally:
            self._quad_reared = False

        if abort_check():
            msg = f"interrupted while coming down ({down_status})"
            return {
                "ok": False,
                "aborted": True,
                "mode": "imu_body_frame",
                "error": msg,
                "msg": msg,
                "rear_status": rear_status,
                "down_status": down_status,
            }
        if down_status != "done":
            msg = f"quad down did not finish ({down_status})"
            return {
                "ok": False,
                "mode": "imu_body_frame",
                "error": msg,
                "msg": msg,
                "rear_status": rear_status,
                "down_status": down_status,
            }
        if not samples:
            return {
                "ok": False,
                "mode": "imu_body_frame",
                "error": "no valid IMU samples while reared",
                "msg": "no valid IMU samples while reared",
                "rear_status": rear_status,
                "down_status": down_status,
            }
        roll = sum(r for r, _p in samples) / len(samples)
        pitch = sum(p for _r, p in samples) / len(samples)
        # Body attitude convention is independent from the quad IK command
        # sign: adjusted body pitch should be negative when the chassis is
        # correctly reared back, positive when it is falling forward.
        expected = -abs(math.degrees(float(GAITS["rear"]["pitch"])))
        body_frame = imu_body_frame_from_roll_pitch(
            roll, pitch, expected_pitch_deg=expected,
            samples=len(samples), source="quad_rear_body_frame")
        if not body_frame.get("ok"):
            existing = (load_imu_calib() or {}).get("body_frame")
            if existing:
                ts = existing.get("timestamp") or "saved calibration"
                return {
                    "ok": True,
                    "mode": "imu_body_frame",
                    "saved": False,
                    "reused_existing": True,
                    "warning": body_frame.get("error"),
                    "rear_status": rear_status,
                    "down_status": down_status,
                    "body_frame": existing,
                    "measured_roll_deg": body_frame.get("measured_roll_deg"),
                    "measured_pitch_deg": body_frame.get("measured_pitch_deg"),
                    "measured_lean_deg": body_frame.get("measured_lean_deg"),
                    "msg": (
                        "rear-lean sample too small; kept existing IMU "
                        f"body-frame map from {ts}"),
                }
            body_frame["mode"] = "imu_body_frame"
            body_frame["rear_status"] = rear_status
            body_frame["down_status"] = down_status
            body_frame["non_blocking"] = down_status == "done"
            return body_frame
        path = save_imu_body_frame(body_frame)
        reload = getattr(bus, "reload_imu_calib", None)
        if callable(reload):
            try:
                reload()
            except Exception:
                pass
        return {
            "ok": True,
            "mode": "imu_body_frame",
            "saved": True,
            "path": str(path),
            "log": str(path),
            "rear_status": rear_status,
            "down_status": down_status,
            "body_frame": body_frame,
            "msg": (
                f"body pitch axis {body_frame.get('pitch_axis')} "
                f"from roll {roll:+.1f} / pitch {pitch:+.1f} deg"),
        }

    def _run_traction_probe(self, bus, *, abort_check, on_progress) -> dict:
        """Gentle planted shear/yaw probe for floor traction.

        This is intentionally an onboard traction indicator, not a literal
        friction coefficient measurement.  If planted feet pin, small yaw
        pulses should build joint lag/current/load; if they slide freely,
        yaws track with little resistance.
        """
        try:
            from feetech_bus import AXIS_LIMITS_DEG, standing_pose_degrees
            from imu_calibrate import imu_tilt_deg
            from inplace_demos import (
                _enable_torque, _hold_here, _live_robot_ids,
                _set_torque_limit, _write_pose, ease_to_pose,
            )
        except ImportError as e:
            return {"ok": False, "mode": "traction_probe", "error": str(e)}

        def progress(msg: str, **extra) -> None:
            on_progress({"msg": msg, "mode": "traction_probe", **extra})

        def clamp(x: float, lo: float, hi: float) -> float:
            return max(float(lo), min(float(hi), float(x)))

        def read_imu():
            fn = getattr(bus, "read_imu", None)
            if not callable(fn):
                return None
            try:
                return fn(apply_calib=True)
            except TypeError:
                try:
                    return fn()
                except Exception:
                    return None
            except Exception:
                return None

        def read_feedback() -> dict[int, dict]:
            read_all = getattr(bus, "read_all_feedback", None)
            if callable(read_all):
                try:
                    got = read_all()
                    if isinstance(got, dict):
                        return got
                except Exception:
                    pass
            out: dict[int, dict] = {}
            for j in range(N_JOINTS):
                try:
                    row = bus.read_feedback(j)
                except Exception:
                    row = None
                if row is not None:
                    out[j] = row
            return out

        live = _live_robot_ids(bus)
        if len(live) < 12:
            return {"ok": False, "mode": "traction_probe",
                    "error": f"need more servos (live={len(live)})",
                    "live": sorted(live)}
        try:
            base = [float(x) for x in standing_pose_degrees()]
        except Exception as e:
            return {"ok": False, "mode": "traction_probe",
                    "error": f"stand pose unavailable: {e}"}
        if len(base) != N_JOINTS:
            return {"ok": False, "mode": "traction_probe",
                    "error": "stand pose is not 18 joints"}

        progress("Traction: settle planted stand")
        _enable_torque(bus, live)
        _set_torque_limit(bus, live, 700)
        if not ease_to_pose(bus, base, abort_check=abort_check, seconds=2.5,
                            label="traction planted stand"):
            _set_torque_limit(bus, live, 1000)
            return {"ok": False, "aborted": True, "mode": "traction_probe",
                    "error": "stand settle aborted"}
        time.sleep(0.35)
        if abort_check():
            _set_torque_limit(bus, live, 1000)
            return {"ok": False, "aborted": True, "mode": "traction_probe"}

        yaw_lo, yaw_hi = AXIS_LIMITS_DEG.get(0, (-35.0, 35.0))
        yaw_joints = [0, 3, 6, 9, 12, 15]
        # Alternating signs press neighboring feet in opposite tangential
        # directions without commanding a big body move.
        pattern = [1.0, -1.0, 1.0, -1.0, 1.0, -1.0]

        base_imu = read_imu()
        base_tilt = imu_tilt_deg(base_imu) if isinstance(base_imu, dict) else None
        base_fb = read_feedback()
        base_current = max(
            [abs(float((base_fb.get(j) or {}).get("current_a") or 0.0))
             for j in yaw_joints] or [0.0])
        base_load = max(
            [float((base_fb.get(j) or {}).get("load_pct") or 0.0)
             for j in yaw_joints] or [0.0])

        samples: list[dict] = []
        repeats = 2
        tilt_soft_limit = 16.0
        tilt_hard_limit = 32.0
        tilt_hold_samples = 3
        tilt_hot = 0
        tilt_stop_reason = None

        def probe_stop(reason: str) -> dict:
            stopped_by_operator = reason == "aborted" or abort_check()
            return {
                "ok": False,
                "aborted": stopped_by_operator,
                "recoverable": not stopped_by_operator,
                "guard_stop": not stopped_by_operator,
                "mode": "traction_probe",
                "error": reason,
                "samples": samples,
            }

        def shear_pose(amp: float) -> list[float]:
            q = list(base)
            for leg, sign in enumerate(pattern):
                j = leg * 3
                q[j] = clamp(base[j] + sign * float(amp), yaw_lo, yaw_hi)
            return q

        def sample(goal: list[float], amp: float, tag: str, cycle: int) -> bool:
            nonlocal tilt_hot, tilt_stop_reason
            fb = read_feedback()
            imu = read_imu()
            tilt = imu_tilt_deg(imu) if isinstance(imu, dict) else None
            yaw_lags = []
            yaw_currents = []
            yaw_loads = []
            yaw_track = []
            for j in yaw_joints:
                row = fb.get(j) or {}
                present = float(row.get("deg") or 0.0)
                yaw_lags.append(abs(float(goal[j]) - present))
                yaw_track.append(abs(present - float(base[j])))
                yaw_currents.append(abs(float(row.get("current_a") or 0.0)))
                yaw_loads.append(float(row.get("load_pct") or 0.0))
            roll_delta = pitch_delta = None
            if tilt is not None and base_tilt is not None:
                roll_delta = float(tilt[0] - base_tilt[0])
                pitch_delta = float(tilt[1] - base_tilt[1])
            row = {
                "tag": tag,
                "cycle": cycle,
                "cmd_amp_deg": round(float(amp), 2),
                "max_yaw_lag_deg": round(max(yaw_lags or [0.0]), 2),
                "mean_yaw_track_deg": round(
                    sum(yaw_track) / max(len(yaw_track), 1), 2),
                "max_current_a": round(max(yaw_currents or [0.0]), 3),
                "max_load_pct": round(max(yaw_loads or [0.0]), 1),
            }
            if tilt is not None:
                row["roll_deg"] = round(float(tilt[0]), 2)
                row["pitch_deg"] = round(float(tilt[1]), 2)
            if roll_delta is not None and pitch_delta is not None:
                row["roll_delta_deg"] = round(roll_delta, 2)
                row["pitch_delta_deg"] = round(pitch_delta, 2)
                row["tilt_delta_deg"] = round(
                    max(abs(roll_delta), abs(pitch_delta)), 2)
            samples.append(row)

            if roll_delta is not None and pitch_delta is not None:
                tilt_delta = max(abs(roll_delta), abs(pitch_delta))
                if tilt_delta > tilt_hard_limit:
                    _hold_here(bus, live)
                    tilt_stop_reason = (
                        f"hard tilt delta > {tilt_hard_limit:.0f} deg")
                    progress(
                        "Traction: hard tilt guard "
                        f"Δroll={roll_delta:+.1f}° Δpitch={pitch_delta:+.1f}°")
                    return False
                if tilt_delta > tilt_soft_limit:
                    tilt_hot += 1
                    if tilt_hot >= tilt_hold_samples:
                        _hold_here(bus, live)
                        tilt_stop_reason = (
                            f"sustained tilt delta > "
                            f"{tilt_soft_limit:.0f} deg")
                        progress(
                            "Traction: sustained tilt guard "
                            f"Δroll={roll_delta:+.1f}° "
                            f"Δpitch={pitch_delta:+.1f}°")
                        return False
                else:
                    tilt_hot = 0
            return True

        try:
            for cycle in range(repeats):
                for amp in (1.5, 3.0, 4.5):
                    for sign in (1.0, -1.0):
                        if abort_check():
                            return {"ok": False, "aborted": True,
                                    "mode": "traction_probe",
                                    "samples": samples}
                        cmd_amp = sign * amp
                        goal = shear_pose(cmd_amp)
                        progress(
                            f"Traction: shear {cmd_amp:+.1f}° "
                            f"trial {cycle + 1}/{repeats}")
                        _write_pose(bus, goal, live, speed=140, acc=18)
                        t0 = time.monotonic()
                        while time.monotonic() - t0 < 0.75:
                            if abort_check():
                                _hold_here(bus, live)
                                return {"ok": False, "aborted": True,
                                        "mode": "traction_probe",
                                        "samples": samples}
                            time.sleep(0.12)
                            if not sample(goal, cmd_amp, "shear", cycle + 1):
                                _set_torque_limit(bus, live, 1000)
                                return probe_stop(
                                    tilt_stop_reason
                                    or "tilt guard during traction probe")
            progress("Traction: return to plant")
            _write_pose(bus, base, live, speed=140, acc=18)
            time.sleep(0.5)
            _hold_here(bus, live)
        finally:
            _set_torque_limit(bus, live, 1000)

        def metric_range(key: str) -> dict:
            vals = [float(s.get(key) or 0.0) for s in samples]
            if not vals:
                return {"min": 0.0, "max": 0.0, "mean": 0.0, "spread": 0.0}
            return {
                "min": round(min(vals), 3),
                "max": round(max(vals), 3),
                "mean": round(sum(vals) / len(vals), 3),
                "spread": round(max(vals) - min(vals), 3),
            }

        max_lag = max([float(s.get("max_yaw_lag_deg") or 0.0)
                       for s in samples] or [0.0])
        max_current = max([float(s.get("max_current_a") or 0.0)
                           for s in samples] or [0.0])
        max_load = max([float(s.get("max_load_pct") or 0.0)
                        for s in samples] or [0.0])
        max_track = max([float(s.get("mean_yaw_track_deg") or 0.0)
                         for s in samples] or [0.0])
        max_tilt_delta = max([
            max(abs(float(s.get("roll_delta_deg") or 0.0)),
                abs(float(s.get("pitch_delta_deg") or 0.0)))
            for s in samples
        ] or [0.0])

        current_rise = max(0.0, max_current - base_current)
        load_rise = max(0.0, max_load - base_load)
        slip_suspected = (
            max_track >= 3.0 and max_lag <= 1.8
            and current_rise < 0.06 and load_rise < 6.0)
        if slip_suspected:
            grade = "low"
        elif max_lag >= 2.5 or current_rise >= 0.10 or load_rise >= 10.0:
            grade = "good"
        else:
            grade = "mixed"
        lag_range = metric_range("max_yaw_lag_deg")
        current_range = metric_range("max_current_a")
        load_range = metric_range("max_load_pct")
        tilt_range = {}
        tilt_vals = [
            max(abs(float(s.get("roll_delta_deg") or 0.0)),
                abs(float(s.get("pitch_delta_deg") or 0.0)))
            for s in samples
        ]
        if tilt_vals:
            tilt_range = {
                "min": round(min(tilt_vals), 3),
                "max": round(max(tilt_vals), 3),
                "mean": round(sum(tilt_vals) / len(tilt_vals), 3),
                "spread": round(max(tilt_vals) - min(tilt_vals), 3),
            }
        msg = (
            f"traction {grade}; yaw lag {max_lag:.1f}°, "
            f"current +{current_rise:.2f}A, load +{load_rise:.0f}%, "
            f"range lag {lag_range['min']:.1f}-{lag_range['max']:.1f}°")
        return {
            "ok": True,
            "mode": "traction_probe",
            "grade": grade,
            "slip_suspected": slip_suspected,
            "repeat_count": repeats,
            "max_yaw_lag_deg": round(max_lag, 2),
            "max_yaw_track_deg": round(max_track, 2),
            "max_current_a": round(max_current, 3),
            "current_rise_a": round(current_rise, 3),
            "max_load_pct": round(max_load, 1),
            "load_rise_pct": round(load_rise, 1),
            "max_tilt_delta_deg": round(max_tilt_delta, 2),
            "ranges": {
                "yaw_lag_deg": lag_range,
                "current_a": current_range,
                "load_pct": load_range,
                "tilt_delta_deg": tilt_range,
            },
            "samples": samples[-24:],
            "msg": msg,
        }

    def _run_leg_slip_probe(self, bus, *, abort_check, on_progress) -> dict:
        """Compare loaded foot drag against lifted/seated references.

        No tape-measure truth is available onboard, so this builds a
        repeatable slip signature: sweep one yaw joint with the foot lifted,
        then sweep the same joint with that foot lightly pressed into the
        floor while the other five feet support the robot.  The loaded/hover
        ratio is what we want to match in MuJoCo.
        """
        try:
            from feetech_bus import AXIS_LIMITS_DEG, standing_pose_degrees
            from imu_calibrate import imu_tilt_deg
            from inplace_demos import (
                _enable_torque, _hold_here, _live_robot_ids,
                _set_torque_limit, _write_pose, ease_to_pose,
            )
            from hexapod_core.tripod_gait import COXA_MM, FEMUR_MM, TIBIA_MM, LEG_RADIAL
        except ImportError as e:
            return {"ok": False, "mode": "traction_probe", "error": str(e)}

        def progress(msg: str, **extra) -> None:
            on_progress({"msg": msg, "mode": "traction_probe", **extra})

        def clamp(x: float, lo: float, hi: float) -> float:
            return max(float(lo), min(float(hi), float(x)))

        def mean(vals: list[float]) -> float:
            vals = [float(v) for v in vals]
            return sum(vals) / len(vals) if vals else 0.0

        def read_imu():
            fn = getattr(bus, "read_imu", None)
            if not callable(fn):
                return None
            try:
                return fn(apply_calib=True)
            except TypeError:
                try:
                    return fn()
                except Exception:
                    return None
            except Exception:
                return None

        def read_feedback() -> dict[int, dict]:
            read_all = getattr(bus, "read_all_feedback", None)
            if callable(read_all):
                try:
                    got = read_all()
                    if isinstance(got, dict):
                        return got
                except Exception:
                    pass
            out: dict[int, dict] = {}
            for j in range(N_JOINTS):
                try:
                    row = bus.read_feedback(j)
                except Exception:
                    row = None
                if row is not None:
                    out[j] = row
            return out

        def foot_radius_mm(q: list[float], leg: int) -> float:
            hip = math.radians(float(q[leg * 3 + 1]))
            knee = math.radians(float(q[leg * 3 + 2]))
            reach = (COXA_MM + FEMUR_MM * math.cos(hip)
                     + TIBIA_MM * math.cos(knee))
            return float(LEG_RADIAL * 1000.0 + reach)

        def arc_mm(q: list[float], leg: int, amp_deg: float) -> float:
            return round(
                2.0 * foot_radius_mm(q, leg)
                * math.sin(math.radians(abs(float(amp_deg)))), 1)

        def max_tilt_delta(rows: list[dict]) -> float:
            return max([
                max(abs(float(r.get("roll_delta_deg") or 0.0)),
                    abs(float(r.get("pitch_delta_deg") or 0.0)))
                for r in rows
            ] or [0.0])

        live = _live_robot_ids(bus)
        if len(live) < 12:
            return {"ok": False, "mode": "traction_probe",
                    "error": f"need more servos (live={len(live)})",
                    "live": sorted(live)}
        try:
            base = [float(x) for x in standing_pose_degrees()]
        except Exception as e:
            return {"ok": False, "mode": "traction_probe",
                    "error": f"stand pose unavailable: {e}"}
        if len(base) != N_JOINTS:
            return {"ok": False, "mode": "traction_probe",
                    "error": "stand pose is not 18 joints"}

        yaw_lo, yaw_hi = AXIS_LIMITS_DEG.get(0, (-35.0, 35.0))
        hip_lo, hip_hi = AXIS_LIMITS_DEG.get(1, (-80.0, 40.0))
        knee_lo, knee_hi = AXIS_LIMITS_DEG.get(2, (-20.0, 150.0))
        amp = 4.0
        tilt_hard_limit = 35.0
        tilt_hold_samples = 3
        samples: list[dict] = []

        def probe_stop(label: str, reason: str) -> dict:
            """Return a phase failure that can still be recovered to zero.

            A local traction guard means the probe learned "this motion is not
            safe enough to keep sweeping"; it is different from an operator
            stop / E-stop.  The checkup coordinator may still run safe-zero for
            these recoverable stops.
            """
            stopped_by_operator = reason == "aborted" or abort_check()
            return {
                "ok": False,
                "aborted": stopped_by_operator,
                "recoverable": not stopped_by_operator,
                "guard_stop": not stopped_by_operator,
                "mode": "traction_probe",
                "error": f"{label} stopped: {reason}",
                "samples": samples,
            }

        progress("Slip: settle plant")
        _enable_torque(bus, live)
        _set_torque_limit(bus, live, 650)
        if not ease_to_pose(bus, base, abort_check=abort_check, seconds=2.5,
                            label="slip plant"):
            _set_torque_limit(bus, live, 1000)
            return {"ok": False, "aborted": True, "mode": "traction_probe",
                    "error": "stand settle aborted"}
        base_imu = read_imu()
        base_tilt = imu_tilt_deg(base_imu) if isinstance(base_imu, dict) else None

        def pose_for(leg: int, yaw: float, mode: str,
                     center: list[float] | None = None) -> list[float]:
            q = list(center if center is not None else base)
            j = leg * 3
            q[j] = clamp(float((center or base)[j]) + float(yaw),
                         yaw_lo, yaw_hi)
            if mode == "hover":
                q[j + 1] = clamp(float(base[j + 1]) - 6.0, hip_lo, hip_hi)
                q[j + 2] = clamp(float(base[j + 2]) + 14.0,
                                 knee_lo, knee_hi)
            elif mode == "loaded":
                q[j + 1] = clamp(float(base[j + 1]) + 3.0, hip_lo, hip_hi)
            return q

        def sample(goal: list[float], leg: int, yaw: float,
                   subtest: str, center: list[float]) -> dict:
            fb = read_feedback()
            j = leg * 3
            rows = [fb.get(j + k) or {} for k in range(3)]
            present = float(rows[0].get("deg") or 0.0)
            currents = [abs(float(r.get("current_a") or 0.0)) for r in rows]
            loads = [float(r.get("load_pct") or 0.0) for r in rows]
            row = {
                "subtest": subtest,
                "leg": leg,
                "cmd_yaw_deg": round(float(yaw), 2),
                "present_yaw_deg": round(present, 2),
                "yaw_lag_deg": round(abs(float(goal[j]) - present), 2),
                "yaw_track_deg": round(abs(present - float(center[j])), 2),
                "yaw_current_a": round(currents[0], 3),
                "leg_current_a": round(sum(currents), 3),
                "max_leg_current_a": round(max(currents or [0.0]), 3),
                "yaw_load_pct": round(loads[0], 1),
                "max_leg_load_pct": round(max(loads or [0.0]), 1),
                "cmd_arc_mm": arc_mm(center, leg, yaw),
            }
            imu = read_imu()
            tilt = imu_tilt_deg(imu) if isinstance(imu, dict) else None
            if tilt is not None:
                row["roll_deg"] = round(float(tilt[0]), 2)
                row["pitch_deg"] = round(float(tilt[1]), 2)
                if base_tilt is not None:
                    row["roll_delta_deg"] = round(float(tilt[0] - base_tilt[0]), 2)
                    row["pitch_delta_deg"] = round(float(tilt[1] - base_tilt[1]), 2)
            samples.append(row)
            return row

        def run_pose(goal: list[float], *, sample_fn, seconds: float,
                     speed: int, acc: int, tilt_limit: float,
                     current_limit: float) -> tuple[bool, str | None]:
            _write_pose(bus, goal, live, speed=speed, acc=acc)
            rows: list[dict] = []
            tilt_hot = 0
            t0 = time.monotonic()
            while time.monotonic() - t0 < seconds:
                if abort_check():
                    _hold_here(bus, live)
                    return False, "aborted"
                time.sleep(0.09)
                row = sample_fn()
                rows.append(row)
                row_tilt = max(
                    abs(float(row.get("roll_delta_deg") or 0.0)),
                    abs(float(row.get("pitch_delta_deg") or 0.0)))
                if row_tilt > tilt_hard_limit:
                    _hold_here(bus, live)
                    return False, (
                        f"hard tilt delta > {tilt_hard_limit:.0f} deg")
                if row_tilt > tilt_limit:
                    tilt_hot += 1
                else:
                    tilt_hot = 0
                if tilt_hot >= tilt_hold_samples:
                    _hold_here(bus, live)
                    return False, (
                        f"sustained tilt delta > {tilt_limit:.0f} deg")
                if max(float(r.get("max_leg_current_a") or 0.0)
                       for r in rows) > current_limit:
                    _hold_here(bus, live)
                    return False, f"current > {current_limit:.1f} A"
            return True, None

        try:
            for leg in range(6):
                if abort_check():
                    _hold_here(bus, live)
                    return {"ok": False, "aborted": True,
                            "mode": "traction_probe", "samples": samples}
                hover_center = pose_for(leg, 0.0, "hover")
                progress(f"Slip: L{leg} lifted reference")
                _write_pose(bus, hover_center, live, speed=130, acc=14)
                time.sleep(0.35)
                for yaw in (-amp, amp, -amp, 0.0):
                    goal = pose_for(leg, yaw, "hover")
                    ok, reason = run_pose(
                        goal,
                        sample_fn=lambda g=goal, l=leg, y=yaw,
                                         c=hover_center: sample(
                                             g, l, y, "five_foot_hover", c),
                        seconds=0.34, speed=125, acc=12,
                        tilt_limit=18.0, current_limit=2.8)
                    if not ok:
                        return probe_stop(f"L{leg} hover", str(reason))

                drag_center = pose_for(leg, 0.0, "loaded")
                progress(f"Slip: L{leg} floor drag")
                _write_pose(bus, drag_center, live, speed=110, acc=12)
                time.sleep(0.35)
                for yaw in (-amp, amp, -amp, 0.0):
                    goal = pose_for(leg, yaw, "loaded")
                    ok, reason = run_pose(
                        goal,
                        sample_fn=lambda g=goal, l=leg, y=yaw,
                                         c=drag_center: sample(
                                             g, l, y, "five_foot_drag", c),
                        seconds=0.40, speed=105, acc=12,
                        tilt_limit=18.0, current_limit=2.8)
                    if not ok:
                        return probe_stop(f"L{leg} drag", str(reason))
                _write_pose(bus, base, live, speed=130, acc=14)
                time.sleep(0.25)

            progress("Slip: seated yaw reference")
            zero_res = self._safe_zero_sync(
                abort_check=abort_check,
                on_progress=lambda p: progress(
                    "Slip zero: " + str(p.get("msg") or "running"),
                    **{k: v for k, v in p.items() if k != "msg"}))
            if not zero_res.get("ok"):
                stopped = bool(abort_check() or zero_res.get("aborted"))
                return {
                    "ok": False,
                    "aborted": stopped,
                    "mode": "traction_probe",
                    "error": (
                        "sit reference interrupted"
                        if stopped else "sit reference failed: "
                        + str(zero_res.get("error") or "safe_zero failed")),
                    "zero_result": zero_res,
                    "samples": samples,
                }
            sit = [0.0] * N_JOINTS
            for leg in range(6):
                for yaw in (-amp, amp, 0.0):
                    goal = list(sit)
                    goal[leg * 3] = clamp(float(yaw), yaw_lo, yaw_hi)
                    ok, reason = run_pose(
                        goal,
                        sample_fn=lambda g=goal, l=leg, y=yaw: sample(
                            g, l, y, "seated_drag", sit),
                        seconds=0.28, speed=110, acc=12,
                        tilt_limit=24.0, current_limit=2.8)
                    if not ok:
                        return probe_stop(f"seated L{leg}", str(reason))
            progress("Slip: return to plant")
            ease_to_pose(bus, base, abort_check=abort_check, seconds=2.5,
                         label="slip return plant")
            _hold_here(bus, live)
        finally:
            _set_torque_limit(bus, live, 1000)

        def summarize(subtest: str, leg: int) -> dict:
            rows = [s for s in samples
                    if s.get("subtest") == subtest and s.get("leg") == leg]
            return {
                "samples": len(rows),
                "mean_yaw_current_a": round(mean([
                    float(r.get("yaw_current_a") or 0.0) for r in rows]), 3),
                "mean_leg_current_a": round(mean([
                    float(r.get("leg_current_a") or 0.0) for r in rows]), 3),
                "max_yaw_lag_deg": round(max([
                    float(r.get("yaw_lag_deg") or 0.0) for r in rows
                ] or [0.0]), 2),
                "mean_yaw_track_deg": round(mean([
                    float(r.get("yaw_track_deg") or 0.0) for r in rows]), 2),
                "max_leg_load_pct": round(max([
                    float(r.get("max_leg_load_pct") or 0.0) for r in rows
                ] or [0.0]), 1),
                "max_tilt_delta_deg": round(max_tilt_delta(rows), 2),
                "cmd_arc_mm": round(max([
                    float(r.get("cmd_arc_mm") or 0.0) for r in rows
                ] or [0.0]), 1),
            }

        per_leg = []
        ratios: list[float] = []
        extra_current: list[float] = []
        extra_lag: list[float] = []
        extra_load: list[float] = []
        for leg in range(6):
            hover = summarize("five_foot_hover", leg)
            loaded = summarize("five_foot_drag", leg)
            seated = summarize("seated_drag", leg)

            def score(row: dict) -> float:
                return (
                    float(row.get("mean_yaw_current_a") or 0.0) * 12.0
                    + float(row.get("max_yaw_lag_deg") or 0.0) * 1.2
                    + float(row.get("max_leg_load_pct") or 0.0) * 0.04
                    + float(row.get("max_tilt_delta_deg") or 0.0) * 0.35)

            ratio = score(loaded) / max(score(hover), 0.2)
            cur_excess = max(
                0.0, float(loaded["mean_yaw_current_a"])
                - float(hover["mean_yaw_current_a"]))
            lag_excess = max(
                0.0, float(loaded["max_yaw_lag_deg"])
                - float(hover["max_yaw_lag_deg"]))
            load_excess = max(
                0.0, float(loaded["max_leg_load_pct"])
                - float(hover["max_leg_load_pct"]))
            ratios.append(ratio)
            extra_current.append(cur_excess)
            extra_lag.append(lag_excess)
            extra_load.append(load_excess)
            per_leg.append({
                "leg": leg,
                "hover": hover,
                "loaded_drag": loaded,
                "seated": seated,
                "loaded_over_hover_score": round(ratio, 2),
                "yaw_current_excess_a": round(cur_excess, 3),
                "yaw_lag_excess_deg": round(lag_excess, 2),
                "load_excess_pct": round(load_excess, 1),
            })

        mean_ratio = mean(ratios)
        mean_cur = mean(extra_current)
        mean_lag = mean(extra_lag)
        mean_load = mean(extra_load)
        if mean_ratio < 1.35 and mean_cur < 0.06 and mean_lag < 0.8:
            grade = "low"
        elif (mean_ratio >= 2.0 or mean_cur >= 0.14
              or mean_lag >= 2.0 or mean_load >= 8.0):
            grade = "good"
        else:
            grade = "mixed"
        msg = (
            f"slip {grade}; loaded/hover x{mean_ratio:.2f}, "
            f"extra yaw +{mean_cur:.2f}A, extra lag +{mean_lag:.1f} deg")
        return {
            "ok": True,
            "mode": "traction_probe",
            "grade": grade,
            "slip_suspected": grade == "low",
            "leg_drag": {
                "mean_loaded_over_hover_score": round(mean_ratio, 2),
                "mean_yaw_current_excess_a": round(mean_cur, 3),
                "mean_yaw_lag_excess_deg": round(mean_lag, 2),
                "mean_load_excess_pct": round(mean_load, 1),
                "per_leg": per_leg,
            },
            "sample_count": len(samples),
            "samples": samples,
            "msg": msg,
            "notes": [
                "loaded/hover compares the same yaw path with the test foot "
                "dragging vs lifted while five other feet support the body",
                "low ratio means the floor interaction looks like unloaded "
                "motor motion, which is a strong slip hint",
                "this is a repeatable onboard traction signature, not an "
                "absolute distance or friction coefficient",
            ],
        }

    def _run_calibration_checkup(self, bus, *, clearance_mm: float,
                                 quad_body_frame: bool = True,
                                 abort_check, on_progress) -> dict:
        phases: list[dict] = []

        def phase(name: str, result: dict) -> None:
            phases.append({
                "name": name,
                "ok": bool(result.get("ok")),
                "aborted": bool(result.get("aborted")),
                "skipped": bool(result.get("skipped")),
                "mode": result.get("mode"),
                "error": result.get("error"),
                "log": result.get("log") or result.get("path"),
                "log_name": result.get("log_name"),
                "non_blocking": bool(result.get("non_blocking")),
                "recoverable": bool(result.get("recoverable")),
                "guard_stop": bool(result.get("guard_stop")),
                "warning": result.get("warning"),
                "summary": (
                    result.get("msg")
                    or result.get("hint")
                    or result.get("error")
                ),
            })

        def progress(msg: str, phase_id: str | None = None,
                     **extra) -> None:
            payload = {**extra, "msg": msg, "mode": "checkup"}
            if phase_id:
                payload["phase"] = phase_id
            on_progress(payload)

        try:
            from geometry_plant import (run_geometry_contact_sweep,
                                        run_geometry_plant)
            from imu_calibrate import run_imu_calibrate
        except ImportError as e:
            return {"ok": False, "mode": "checkup", "error": str(e)}

        def run_safe_zero_phase(phase_id: str, label: str) -> dict:
            progress(label, phase_id)
            res = self._safe_zero_sync(
                abort_check=abort_check,
                on_progress=lambda p: progress(
                    label + ": " + str(p.get("msg") or "running"),
                    phase_id,
                    **{k: v for k, v in p.items() if k != "msg"}))
            res.setdefault("mode", phase_id)
            if res.get("ok"):
                if res.get("already_at_zero"):
                    res["msg"] = "already at zero"
                else:
                    res["msg"] = (
                        f"zero pose ready; {res.get('stages_done', 0)} "
                        "safe stages")
            return res

        zero_res = run_safe_zero_phase("safe_zero", "Safe zero start pose")
        phase("safe_zero", zero_res)
        if (abort_check() or zero_res.get("aborted")
                or not zero_res.get("ok")):
            report = self._save_calibration_report(phases=phases, bus=bus)
            return {
                "ok": False,
                "aborted": bool(abort_check() or zero_res.get("aborted")),
                "mode": "checkup",
                "error": zero_res.get("error"),
                "phases": phases,
                "report": report,
                "path": report.get("path"),
                "log_name": report.get("log_name"),
            }

        bus_error_still_res = None
        bus_error_moving_res = None

        progress("Still bus error rate", "bus_error_rate_still")
        bus_error_still_res = self._bus_error_rate_probe(
            bus, label="still", mode="bus_error_rate_still",
            abort_check=abort_check)
        phase("bus_error_rate_still", bus_error_still_res)
        if abort_check() or bus_error_still_res.get("aborted"):
            report = self._save_calibration_report(
                phases=phases, bus=bus,
                bus_error_rate={"still": bus_error_still_res})
            return {"ok": False, "aborted": True, "mode": "checkup",
                    "phases": phases, "report": report,
                    "path": report.get("path"), "log_name": report.get("log_name")}

        moving_bus_quality = self._new_bus_quality_tracker("moving")
        moving_bus = moving_bus_quality.wrap(bus)

        progress("IMU rest/bias", "imu_rest")
        imu_res = run_imu_calibrate(
            bus, abort_check=abort_check,
            on_progress=lambda p: progress(
                "IMU rest: " + str(p.get("msg") or "sampling"),
                "imu_rest",
                **{k: v for k, v in p.items() if k != "msg"}))
        phase("imu_rest", imu_res)
        if abort_check() or imu_res.get("aborted"):
            report = self._save_calibration_report(
                phases=phases, bus=bus,
                bus_error_rate={"still": bus_error_still_res})
            return {"ok": False, "aborted": True, "mode": "checkup",
                    "phases": phases, "report": report,
                    "path": report.get("path"), "log_name": report.get("log_name")}

        progress("Ground contact / plant search", "geometry_plant")
        try:
            geo_res = run_geometry_plant(
                moving_bus, abort_check=abort_check,
                on_progress=lambda p: progress(
                    "Geo plant: " + str(p.get("msg") or "running"),
                    "geometry_plant",
                    **{k: v for k, v in p.items() if k != "msg"}),
                clearance_mm=clearance_mm)
        except RuntimeError as e:
            geo_res = {
                "ok": False,
                "aborted": True,
                "mode": "geometry_plant",
                "error": f"ground contact command failed: {e}",
            }
        phase("geometry_plant", geo_res)

        traction_res = None
        sweep_res = None
        geometry_check_res = None
        bf_res = None
        imu_frame_check_res = None
        stability_res = None
        mass_shift_res = None
        bus_power_res = None
        motion_ok = (not abort_check() and not geo_res.get("aborted")
                     and bool(geo_res.get("ok")))
        motion_block_reason = (
            "not run because ground contact geometry did not finish cleanly")
        body_ok = False
        body_non_blocking = False

        if motion_ok:
            progress("Geometry dimension sweep", "geometry_sweep")
            try:
                sweep_res = run_geometry_contact_sweep(
                    moving_bus, abort_check=abort_check,
                    on_progress=lambda p: progress(
                        "Geo sweep: " + str(p.get("msg") or "running"),
                        "geometry_sweep",
                        **{k: v for k, v in p.items() if k != "msg"}))
            except RuntimeError as e:
                sweep_res = {
                    "ok": False,
                    "aborted": True,
                    "mode": "geometry_sweep",
                    "error": f"dimension sweep command failed: {e}",
                }
            if sweep_res.get("status") == "manual_geometry_mismatch":
                sweep_res["non_blocking"] = True
            phase("geometry_sweep", sweep_res)
            if abort_check() or sweep_res.get("aborted"):
                motion_ok = False
                motion_block_reason = (
                    "not run because dimension sweep was aborted")
        else:
            phases.append({
                "name": "geometry_sweep",
                "ok": False,
                "aborted": bool(geo_res.get("aborted") or abort_check()),
                "skipped": True,
                "mode": "geometry_sweep",
                "summary": motion_block_reason,
            })

        progress("Geometry plausibility", "geometry_plausibility")
        geometry_check_res = self._geometry_plausibility_check(
            geometry_sweep=sweep_res)
        phase("geometry_plausibility", geometry_check_res)

        if motion_ok:
            progress("IMU body-frame map from quad rear", "imu_body_frame")
            bf_res = self._calibrate_quad_body_frame(
                moving_bus, abort_check=abort_check,
                on_progress=lambda p: progress(
                    str(p.get("msg") or "running"), "imu_body_frame",
                    **{k: v for k, v in p.items() if k != "msg"}))
            phase("imu_body_frame", bf_res)
            body_ok = bool(bf_res.get("ok")) and not bf_res.get("aborted")
            body_non_blocking = (
                bool(bf_res.get("non_blocking"))
                and not bf_res.get("aborted"))
        else:
            phases.append({
                "name": "imu_body_frame",
                "ok": False,
                "aborted": bool(abort_check()
                                or any(p.get("aborted") for p in phases)),
                "skipped": True,
                "mode": "imu_body_frame",
                "summary": motion_block_reason,
            })

        if motion_ok:
            progress("IMU frame validation", "imu_frame_validation")
            imu_frame_check_res = self._imu_frame_validation_check(bf_res)
            phase("imu_frame_validation", imu_frame_check_res)
        else:
            phases.append({
                "name": "imu_frame_validation",
                "ok": False,
                "skipped": True,
                "mode": "imu_frame_validation",
                "summary": motion_block_reason,
            })

        if motion_ok and (body_ok or body_non_blocking) and not abort_check():
            progress("Stability margin", "stability_margin")
            stability_res = self._run_stability_margin_check(
                moving_bus, abort_check=abort_check,
                on_progress=lambda p: progress(
                    str(p.get("msg") or "running"), "stability_margin",
                    **{k: v for k, v in p.items() if k != "msg"}))
            phase("stability_margin", stability_res)
            if (abort_check() or stability_res.get("aborted")
                    or stability_res.get("guard_stop")):
                motion_ok = False
                motion_block_reason = (
                    "not run because stability margin guard stopped motion")
        else:
            phases.append({
                "name": "stability_margin",
                "ok": False,
                "aborted": bool(abort_check()
                                or any(p.get("aborted") for p in phases)),
                "skipped": True,
                "mode": "stability_margin",
                "summary": (
                    "not run because IMU body-frame motion did not finish "
                    "cleanly"),
            })

        if motion_ok and (body_ok or body_non_blocking) and not abort_check():
            progress("Mass shift response", "mass_shift_response")
            mass_shift_res = self._run_mass_shift_response_check(
                moving_bus, abort_check=abort_check,
                on_progress=lambda p: progress(
                    str(p.get("msg") or "running"), "mass_shift_response",
                    **{k: v for k, v in p.items() if k != "msg"}))
            phase("mass_shift_response", mass_shift_res)
            if (abort_check() or mass_shift_res.get("aborted")
                    or mass_shift_res.get("guard_stop")):
                motion_ok = False
                motion_block_reason = (
                    "not run because mass-shift guard stopped motion")
        else:
            phases.append({
                "name": "mass_shift_response",
                "ok": False,
                "aborted": bool(abort_check()
                                or any(p.get("aborted") for p in phases)),
                "skipped": True,
                "mode": "mass_shift_response",
                "summary": motion_block_reason,
            })

        if motion_ok and (body_ok or body_non_blocking) and not abort_check():
            progress("Traction / slip probe", "traction_probe")
            traction_res = self._run_traction_probe(
                moving_bus, abort_check=abort_check,
                on_progress=lambda p: progress(
                    str(p.get("msg") or "running"), "traction_probe",
                    **{k: v for k, v in p.items() if k != "msg"}))
            phase("traction_probe", traction_res)
        else:
            phases.append({
                "name": "traction_probe",
                "ok": False,
                "aborted": bool(abort_check()
                                or any(p.get("aborted") for p in phases)),
                "skipped": True,
                "mode": "traction_probe",
                "summary": (
                    "not run because a prior motion phase did not finish "
                    "cleanly"),
            })

        progress("Moving bus error rate", "bus_error_rate_moving")
        bus_error_moving_res = moving_bus_quality.summary(
            mode="bus_error_rate_moving")
        phase("bus_error_rate_moving", bus_error_moving_res)

        motion_phase_names = {
            "geometry_plant",
            "geometry_sweep",
            "imu_body_frame",
            "stability_margin",
            "mass_shift_response",
            "traction_probe",
        }
        recoverable_measurement_names = {
            "geometry_sweep",
            "stability_margin",
            "mass_shift_response",
            "traction_probe",
        }
        returned_zero = False
        prior_motion_issue = any(
            p.get("name") in motion_phase_names
            and not p.get("ok")
            and not p.get("skipped")
            and not p.get("non_blocking")
            for p in phases)
        unrecoverable_abort = any(
            p.get("aborted") and not p.get("recoverable")
            for p in phases)
        unrecoverable_motion_issue = any(
            p.get("name") in motion_phase_names
            and not p.get("ok")
            and not p.get("skipped")
            and not p.get("non_blocking")
            and not p.get("recoverable")
            and not (
                p.get("name") in recoverable_measurement_names
                and not p.get("aborted"))
            for p in phases)
        if abort_check() or unrecoverable_abort:
            phases.append({
                "name": "return_zero",
                "ok": False,
                "aborted": True,
                "skipped": True,
                "mode": "return_zero",
                "summary": "not run because checkup was aborted",
            })
        elif prior_motion_issue and unrecoverable_motion_issue:
            phases.append({
                "name": "return_zero",
                "ok": False,
                "aborted": False,
                "skipped": True,
                "mode": "return_zero",
                "summary": (
                    "not run because a motion phase had issues; robot left "
                    "limp for inspection"),
            })
        else:
            return_zero_res = run_safe_zero_phase(
                "return_zero", "Return zero before torque-off")
            phase("return_zero", return_zero_res)
            returned_zero = bool(return_zero_res.get("ok"))

        proprio_res = None
        if returned_zero and not abort_check():
            progress("Proprioception consistency", "proprioception_check")
            proprio_res = self._proprioception_check(
                bus, expected_pose=[0.0] * N_JOINTS, expected_name="zero")
            phase("proprioception_check", proprio_res)
        else:
            phases.append({
                "name": "proprioception_check",
                "ok": False,
                "aborted": bool(abort_check()
                                or any(p.get("aborted") for p in phases)),
                "skipped": True,
                "mode": "proprioception_check",
                "summary": "not run because robot was not returned to zero",
            })

        progress("Camera witness", "camera_witness")
        camera_res = self._camera_witness_check()
        phase("camera_witness", camera_res)

        progress("Bus/power health", "bus_power_health")
        bus_power_res = self._bus_power_check(bus)
        phase("bus_power_health", bus_power_res)

        progress("Actuator health snapshot", "actuator_snapshot")
        phases.append({
            "name": "actuator_snapshot",
            "ok": True,
            "mode": "actuator_snapshot",
            "summary": "live actuator snapshot captured in report",
        })
        progress("Saving calibration report", "report")
        report = self._save_calibration_report(
            phases=phases, bus=bus, traction=traction_res,
            geometry_sweep=sweep_res, geometry_check=geometry_check_res,
            imu_frame_check=imu_frame_check_res,
            stability_margin=stability_res, mass_shift=mass_shift_res,
            proprioception=proprio_res,
            camera_witness=camera_res, bus_power=bus_power_res,
            bus_error_rate={
                "still": bus_error_still_res,
                "moving": bus_error_moving_res,
            })
        phases.append({
            "name": "report",
            "ok": bool(report.get("path") or report.get("log_name")),
            "mode": "calibration_report",
            "log": report.get("path"),
            "log_name": report.get("log_name"),
            "summary": "sim-ready calibration report saved",
        })
        problem = self._checkup_blocking_problem(phases)
        ok = not abort_check() and problem is None
        diagnostic_issues = self._checkup_diagnostic_issues(phases)
        problem_msg = None
        if not ok and isinstance(problem, dict):
            problem_msg = (
                str(problem.get("name") or "checkup")
                + ": "
                + str(problem.get("error") or problem.get("summary")
                      or "failed"))
        return {
            "ok": ok,
            "mode": "checkup",
            **({"error": problem_msg} if problem_msg else {}),
            "phases": phases,
            "report": report,
            "geometry": report.get("geometry"),
            "geometry_check": report.get("geometry_check"),
            "imu": report.get("imu"),
            "imu_frame_check": report.get("imu_frame_check"),
            "stability_margin": report.get("stability_margin"),
            "mass_shift": report.get("mass_shift"),
            "traction": report.get("traction"),
            "proprioception": report.get("proprioception"),
            "camera_witness": report.get("camera_witness"),
            "bus_power": report.get("bus_power"),
            "bus_error_rate": report.get("bus_error_rate"),
            "actuators": report.get("actuators"),
            "path": report.get("path"),
            "log_name": report.get("log_name"),
            "latest": report.get("latest"),
            "msg": (
                "checkup complete with diagnostic issues; see phases"
                if ok and diagnostic_issues else
                "checkup complete"
                if ok else "checkup complete with issues; see phases"),
            "diagnostic_issue_count": len(diagnostic_issues),
        }

    def run_calibrate(self, *, mode: str = "step",
                      step_deg: float = 10.0,
                      nudge_deg: float = 2.0,
                      axis: str = "all",
                      clearance_mm: float = 40.0,
                      quad_body_frame: bool = True,
                      force: bool = False) -> dict:
        """Background step, shake/hold, plant-height, geometry plant, or IMU."""
        mode = (mode or "step").strip().lower()
        if mode in ("hold", "hunt"):
            mode = "shake"
        if mode in ("plant", "plant_height", "height", "stand_height"):
            mode = "plant"
        if mode in ("geometry", "geometry_plant", "geo_plant", "rl_plant"):
            mode = "geometry"
        if mode in ("imu", "mpu", "gyro", "accel"):
            mode = "imu"
        if mode in ("checkup", "auto", "all", "calibration"):
            mode = "checkup"
        if mode == "checkup":
            quad_body_frame = True

        if mode == "plant":
            try:
                from plant_calibrate import run_plant_calibrate
            except ImportError as e:
                return {"ok": False, "error": f"plant_calibrate missing: {e}"}
        elif mode == "geometry":
            if not force:
                return {
                    "ok": False,
                    "error": (
                        "geometry plant disabled without force=true "
                        "(2026-08-06 incident). Prefer capture_plant."
                    ),
                }
            try:
                from geometry_plant import run_geometry_plant
            except ImportError as e:
                return {"ok": False, "error": f"geometry_plant missing: {e}"}
        elif mode == "imu":
            try:
                from imu_calibrate import run_imu_calibrate
            except ImportError as e:
                return {"ok": False, "error": f"imu_calibrate missing: {e}"}
        elif mode == "checkup":
            pass
        else:
            try:
                from joint_calibrate import run_calibrate
            except ImportError as e:
                return {"ok": False, "error": f"joint_calibrate missing: {e}"}

        if self.drive.dry_run:
            return {"ok": False, "error": "dry-run — no bus"}
        if not self.drive.bus:
            return {"ok": False, "error": "no bus"}
        if self._demo_thread and self._demo_thread.is_alive():
            if not self._preempt_demo_thread(
                    reason="→ calibrate", timeout=5.0):
                return {"ok": False,
                        "error": "previous demo did not stop — try Stop",
                        "calibrate": self.calibrate_state()}

        try:
            step_deg = float(step_deg)
        except (TypeError, ValueError):
            step_deg = 10.0
        try:
            nudge_deg = float(nudge_deg)
        except (TypeError, ValueError):
            nudge_deg = 2.0
        axis = (axis or "all").strip().lower()
        if mode not in ("step", "shake", "plant", "geometry", "imu",
                        "checkup"):
            mode = "step"
        try:
            clearance_mm = float(clearance_mm)
        except (TypeError, ValueError):
            clearance_mm = 40.0

        self._demo_gen += 1
        gen = self._demo_gen
        self._demo_abort.clear()
        if mode == "plant":
            label = "plant height (contact reach)"
        elif mode == "geometry":
            label = f"geometry plant (hip≈0 / knee≈90, +{clearance_mm:.0f}mm)"
        elif mode == "imu":
            label = "IMU rest (hold still)"
        elif mode == "checkup":
            label = (
                "calibration checkup "
                "(IMU + geometry + stability/mass + traction + report)")
        elif mode == "shake":
            label = f"shake +{nudge_deg:.1f}° hold ({axis})"
        else:
            label = f"step +{step_deg:.0f}° ({axis})"
        with self._lock:
            self._demo_name = f"calibrate:{mode}:{axis}"
            self._demo_status = "calibrating"
            self._demo_params = {
                "mode": mode, "step_deg": step_deg,
                "nudge_deg": nudge_deg, "axis": axis,
                "clearance_mm": clearance_mm,
                "quad_body_frame": bool(quad_body_frame),
            }
            self._cal_result = None
            self._cal_progress = {"msg": "starting…"}
        self._set_activity("calibrating", label)
        self._queue_calibration_tft(
            {"msg": label, "phase": mode, "mode": mode}, force=True)

        def _worker():
            d = self.drive
            with d._lock:
                d.mode = "demo"
                d.gait.stop()
                # IMU rest/checkup begin with stillness; active phases arm
                # themselves when they need servo torque.
                if mode not in ("imu", "checkup") and not d.armed:
                    d._torque_all(True)
                    d.armed = True

            def _on_progress(p: dict) -> None:
                with self._lock:
                    self._cal_progress = dict(p)
                    self._demo_status = str(p.get("msg") or "calibrating")
                self._queue_calibration_tft(p)

            try:
                self._bus_hot_begin()
                if mode == "plant":
                    result = run_plant_calibrate(
                        d.bus,
                        names=self.names,
                        abort_check=self._demo_abort.is_set,
                        on_progress=_on_progress,
                    )
                elif mode == "geometry":
                    result = run_geometry_plant(
                        d.bus,
                        abort_check=self._demo_abort.is_set,
                        on_progress=_on_progress,
                        clearance_mm=clearance_mm,
                    )
                elif mode == "imu":
                    result = run_imu_calibrate(
                        d.bus,
                        abort_check=self._demo_abort.is_set,
                        on_progress=_on_progress,
                    )
                elif mode == "checkup":
                    result = self._run_calibration_checkup(
                        d.bus,
                        clearance_mm=clearance_mm,
                        quad_body_frame=bool(quad_body_frame),
                        abort_check=self._demo_abort.is_set,
                        on_progress=_on_progress,
                    )
                else:
                    result = run_calibrate(
                        d.bus,
                        mode=mode,
                        step_deg=step_deg,
                        nudge_deg=nudge_deg,
                        axis=axis,
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
                    elif result.get("ok") and mode == "plant":
                        if result.get("saved"):
                            self._demo_status = (
                                f"done · plant hip {result.get('hip_deg')}° / "
                                f"knee {result.get('knee_deg')}°"
                            )
                        else:
                            self._demo_status = (
                                "done · no contact (plant not saved)"
                            )
                    elif result.get("ok") and mode == "geometry":
                        self._demo_status = (
                            f"done · geo plant hip {result.get('hip_deg')}° / "
                            f"knee {result.get('knee_deg')}°"
                        )
                    elif result.get("ok") and mode == "imu":
                        g = result.get("grade") or "?"
                        if result.get("saved"):
                            self._demo_status = f"done · IMU {g} (saved)"
                        else:
                            self._demo_status = f"done · IMU {g} (not saved)"
                    elif result.get("ok") and mode == "checkup":
                        self._demo_status = (
                            "done · checkup report "
                            + str(result.get("log_name") or "saved"))
                    elif result.get("ok"):
                        c = result.get("counts") or {}
                        self._demo_status = (
                            f"done · {c.get('green', 0)}g/"
                            f"{c.get('yellow', 0)}y/{c.get('red', 0)}r"
                        )
                    else:
                        self._demo_status = (
                            f"error: {result.get('error') or 'failed'}"
                        )
            except Exception as e:
                if gen != self._demo_gen:
                    return
                with self._lock:
                    self._cal_result = {"ok": False, "error": str(e)}
                    self._demo_status = f"error: {e}"
            finally:
                self._bus_hot_end()
                if gen != self._demo_gen:
                    return
                checkup_limped = False
                if mode == "checkup":
                    # Checkup is diagnostic, not a hold command.  Active
                    # phases may enable torque; always leave the robot limp so
                    # a partial report cannot keep servos loaded.
                    try:
                        d.handle("X")
                        checkup_limped = True
                    except Exception:
                        pass
                with d._lock:
                    if d.mode == "demo":
                        d.mode = "idle"
                with self._lock:
                    st = self._demo_status
                detail = (
                    (st + " · limp") if (st and checkup_limped) else
                    (st if st else (
                        "checkup done · limp" if checkup_limped
                        else "calibrate done")))
                self._set_activity(
                    "limp" if checkup_limped else (
                        "armed" if d.armed else "limp"),
                    detail)
                self._queue_calibration_tft(
                    {"msg": detail, "phase": "done", "mode": mode},
                    force=True, final=True)

        self._demo_thread = threading.Thread(target=_worker, daemon=True)
        self._demo_thread.start()
        return {"ok": True, "calibrate": self.calibrate_state()}

    def stop_calibrate(self) -> dict:
        """Alias for stop_demo (same worker slot)."""
        out = self.stop_demo()
        out["calibrate"] = self.calibrate_state()
        return out
