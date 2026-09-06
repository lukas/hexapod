#!/usr/bin/env python3
"""Run the fixed gait-1 alpha/speed shaking comparison on hardware.

Reuses the proven hardware Trial recorder, raw communication markers, health
sampling, and STEP rise/lower. It does not invoke the legacy scripted-suite
main or change gait generation, bus cadence, or servo profiles.
"""
from __future__ import annotations

import argparse
import json
import signal
import time
from pathlib import Path

from rl_move.scripts.run_rl_walk_trial import ConfirmedHealthTrip, Trial, _request


CONDITIONS = (
    {"name": "low_alpha_30", "alpha": 0.25, "vx_mm_s": 30.0},
    {"name": "high_alpha_30", "alpha": 1.0, "vx_mm_s": 30.0},
    {"name": "high_alpha_40", "alpha": 1.0, "vx_mm_s": 40.0},
    {"name": "low_alpha_40", "alpha": 0.25, "vx_mm_s": 40.0},
)
CONDITIONS_BY_NAME = {condition["name"]: condition for condition in CONDITIONS}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--robot-url", default="http://192.168.4.39:8080")
    parser.add_argument(
        "--vision-frame-url", default="",
        help="optional HTTP fallback; empty uses native AVFoundation capture",
    )
    parser.add_argument(
        "--camera-index", type=int, default=1,
        help="native AVFoundation camera index when no HTTP URL is supplied",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--walk-s", type=float, default=8.0)
    parser.add_argument("--stationary-s", type=float, default=3.0)
    parser.add_argument(
        "--condition", action="append", choices=tuple(CONDITIONS_BY_NAME),
        help=(
            "fixed comparison cell to run; repeat to select an ordered subset "
            "(default: all four proven cells)"
        ),
    )
    parser.add_argument(
        "--resume-walk-ready", action="store_true",
        help="reuse a camera-verified armed walk-ready pose after three fresh samples",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def _selected_conditions(names: list[str] | None) -> tuple[dict, ...]:
    if not names:
        return CONDITIONS
    if len(names) != len(set(names)):
        raise ValueError("duplicate --condition values are not allowed")
    return tuple(CONDITIONS_BY_NAME[name] for name in names)


def _trial_args(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        robot_url=args.robot_url, vision_frame_url=args.vision_frame_url,
        camera_index=args.camera_index, temp_trip_c=55.0, speed_m_s=0.04,
        learned_rise=False, learned_rise_tilt_trip_deg=8.0,
        resume_walk_ready=False, acquire_current=False, tuck_recovery=False,
        keep_current_walk_ready=False,
    )


class Guard:
    """Apply the existing physical thresholds to every feedback sample."""

    def __init__(self, trial: Trial) -> None:
        self.trial = trial
        self.low_live = self.high_current = self.high_tilt = self.high_temp = 0

    def sample(self) -> dict:
        if self.trial.stop_requested:
            raise RuntimeError("operator stop requested")
        metrics = self.trial.sample()
        self.low_live = self.low_live + 1 if metrics["live"] < 18 else 0
        self.high_current = self.high_current + 1 if metrics["max_current_a"] >= 2.4 else 0
        tilt = max(abs(metrics["roll_deg"]), abs(metrics["pitch_deg"]))
        self.high_tilt = self.high_tilt + 1 if tilt >= 22.0 else 0
        self.high_temp = self.high_temp + 1 if metrics["max_temp_c"] >= 55.0 else 0
        if self.low_live >= 3:
            raise ConfirmedHealthTrip("persistent incomplete feedback")
        if metrics["max_current_a"] >= 3.0:
            raise ConfirmedHealthTrip(f"hard current {metrics['max_current_a']:.2f} A")
        if self.high_current >= 2:
            raise ConfirmedHealthTrip(f"sustained current {metrics['max_current_a']:.2f} A")
        if metrics["min_voltage_v"] < 9.5:
            raise ConfirmedHealthTrip(f"bus voltage {metrics['min_voltage_v']:.2f} V")
        if self.high_tilt >= 3:
            raise ConfirmedHealthTrip(f"sustained tilt {tilt:.1f} deg")
        if self.high_temp >= 3:
            raise ConfirmedHealthTrip(f"confirmed temperature {metrics['max_temp_c']:.1f} C")
        return metrics

    def wait(self, seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.trial.recorder.assert_live()
            self.sample()
            time.sleep(min(0.18, max(0.0, deadline - time.monotonic())))


def _command(trial: Trial, line: str) -> str:
    response = _request(trial.base, "/cmd", text_body=line, timeout=5.0)
    trial.event("command", {"line": line, "response": response})
    return str(response)


def _stop_walk(trial: Trial, guard: Guard, label: str) -> None:
    response = _command(trial, "GAITSTOP")
    if not response.startswith("gaitstop_s="):
        raise ConfirmedHealthTrip(f"{label} settle refused: {response}")
    try:
        settle_s = float(response.split("=", 1)[1])
    except ValueError as error:
        raise ConfirmedHealthTrip(f"invalid settle duration: {response}") from error
    trial.event("neutral_settle_start", {"seconds": settle_s})
    guard.wait(settle_s)
    if _command(trial, "J 0 0 0") != "J":
        raise ConfirmedHealthTrip(f"{label} neutral hold refused")
    trial.event("neutral_settle_done")


def _verified_zero(trial: Trial) -> None:
    pose = trial.request("/api/pose")
    degrees = pose.get("degrees") if isinstance(pose, dict) else None
    if not isinstance(degrees, list) or len(degrees) != 18:
        raise RuntimeError(f"logical pose unavailable: {pose}")
    if max(abs(float(value)) for value in degrees if value is not None) > 6.0:
        raise RuntimeError(f"not at verified logical zero: {degrees}")
    trial.event("logical_zero_verified", {"degrees": degrees})
    trial.three_fresh_health_samples(require_armed=False)


def _stand(trial: Trial) -> None:
    trial.phase = "stand"
    trial.motion_started = True
    reply = trial.request("/api/rl/stand", {})
    trial.event("step_stand_start", reply)
    if not isinstance(reply, dict) or not reply.get("ok"):
        raise RuntimeError(f"STEP stand refused: {reply}")
    result = trial.wait_job("step_stand", 45.0)
    if not result.get("ok"):
        raise RuntimeError(f"STEP stand failed: {result}")
    preflight = trial.request("/api/rl/preflight?mode=walk")
    trial.event("walk_ready_preflight", preflight)
    if not isinstance(preflight, dict) or not preflight.get("ok"):
        raise RuntimeError(f"walk-ready preflight failed: {preflight}")
    trial.three_fresh_health_samples(require_armed=True)
    trial.snapshot("walk_ready")


def _verified_walk_ready(trial: Trial) -> None:
    preflight = trial.request("/api/rl/preflight?mode=walk")
    trial.event("resume_walk_ready_preflight", preflight)
    if not isinstance(preflight, dict) or not preflight.get("ok"):
        raise RuntimeError(f"resume pose is not walk-ready: {preflight}")
    trial.three_fresh_health_samples(require_armed=True)
    trial.snapshot("walk_ready_resumed")
    trial.motion_started = True


def _run_condition(trial: Trial, guard: Guard, condition: dict,
                   walk_s: float, stationary_s: float) -> None:
    name, alpha, vx = str(condition["name"]), float(condition["alpha"]), float(condition["vx_mm_s"])
    trial.phase = f"{name}_select"
    selected = _command(trial, f"GAIT 1 {alpha:.3f}")
    if selected.lower().startswith(("bad", "refused", "unknown")):
        raise RuntimeError(f"{name} gait selection refused: {selected}")
    trial.event("condition_selected", {**condition, "response": selected})
    trial.three_fresh_health_samples(require_armed=True)
    trial.phase = f"{name}_stationary_before"
    guard.wait(stationary_s)
    trial.snapshot(f"{name}_before")
    trial.phase = f"{name}_walk"
    trial.communication_mark(f"{name}_walk_begin")
    started_mono, started_unix = time.monotonic(), time.time()
    if _command(trial, f"J {vx:.1f} 0.0 0 1") != "J":
        raise RuntimeError(f"{name} walk refused")
    guard.wait(walk_s)
    trial.phase = f"{name}_settle"
    _stop_walk(trial, guard, name)
    stopped_mono = time.monotonic()
    trial.communication_mark(f"{name}_walk_end")
    trial.phase = f"{name}_stationary_after"
    guard.wait(stationary_s)
    trial.snapshot(f"{name}_after")
    trial.three_fresh_health_samples(require_armed=True)
    trial.event("condition_complete", {
        **condition, "command_started_monotonic": started_mono,
        "command_started_unix": started_unix,
        "neutral_hold_monotonic": stopped_mono, "requested_walk_s": walk_s,
    })


def _pause_in_place(trial: Trial, guard: Guard, reason: str) -> None:
    trial.event("failure_pause_in_place_start", reason)
    try:
        state = trial.request("/api/robot")
        if not state.get("armed"):
            trial.event("failure_pause_already_limp")
        elif state.get("mode") == "walk":
            _stop_walk(trial, guard, "failure pause")
            trial.event("failure_pause_holding_walk_pose")
        elif (state.get("demo") or {}).get("running"):
            trial.event("failure_pause_job_stop", trial.request("/api/rl/stop", {}))
        else:
            trial.event("failure_pause_holding_stationary_pose")
    except Exception as stop_error:
        trial.event("failure_pause_stop_failed", str(stop_error))
        try:
            trial.event("EMERGENCY_STOP", _command(trial, "X"))
        except Exception as limp_error:
            trial.event("emergency_stop_error", str(limp_error))


def main() -> int:
    args = _parser().parse_args()
    if not 3.0 <= args.walk_s <= 8.0:
        raise SystemExit("--walk-s must be in [3, 8]")
    if not 0.0 <= args.stationary_s <= 5.0:
        raise SystemExit("--stationary-s must be in [0, 5]")
    try:
        conditions = _selected_conditions(args.condition)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    fixed = {
        "gait": "NoSlipGait.gait1", "period_s": 3.2, "lift_mm": 28,
        "control_hz": 100, "servo_speed_counts_s": 2000,
        "servo_acc_units": 80, "stance": "STEP walk-ready 20/80 physical contract",
    }
    config = {
        "schema": "hexapod.programmed_alpha_shaking.v1",
        "conditions": conditions, "walk_s": args.walk_s,
        "stationary_before_s": args.stationary_s,
        "stationary_after_s": args.stationary_s, "fixed": fixed,
    }
    if args.dry_run:
        print(json.dumps(config, indent=2))
        return 0

    stamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir / f"programmed_alpha_shake_{stamp}"
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    trial = Trial(_trial_args(args), output_dir)
    trial.stop_requested = False
    guard = Guard(trial)
    error: str | None = None
    exit_code = 0

    def request_stop(_signum: int, _frame: object) -> None:
        trial.stop_requested = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    print(f"OUTPUT_DIR={output_dir}", flush=True)
    try:
        trial.start_communication_capture()
        if trial.communication_capture["errors"]:
            raise RuntimeError(f"communication capture unavailable: {trial.communication_capture}")
        trial.recorder.start()
        trial.event("recorder_ready", {"fps": trial.recorder.OUTPUT_FPS})
        if args.resume_walk_ready:
            _verified_walk_ready(trial)
        else:
            _verified_zero(trial)
            _stand(trial)
        for condition in conditions:
            _run_condition(trial, guard, condition, args.walk_s, args.stationary_s)
        trial.communication_mark("planned_lower_begin")
        trial.planned_lower()
        trial.event("experiment_complete")
    except ConfirmedHealthTrip as issue:
        error = str(issue)
        trial.event("EMERGENCY_STOP", error)
        try:
            _command(trial, "X")
        except Exception as limp_error:
            trial.event("emergency_stop_error", str(limp_error))
        exit_code = 2
    except Exception as issue:
        error = str(issue)
        trial.event("experiment_error", error)
        if trial.motion_started:
            _pause_in_place(trial, guard, error)
        exit_code = 1
    finally:
        try:
            trial.snapshot("final")
        except Exception as camera_error:
            trial.event("final_camera_error", str(camera_error))
        try:
            trial.recorder.stop()
        except Exception as recorder_error:
            trial.recorder.error = trial.recorder.error or str(recorder_error)
        trial.event("recorder_stopped", {"frames": trial.recorder.frames, "error": trial.recorder.error})
        if trial.recorder.error:
            error = error or f"camera recording failed: {trial.recorder.error}"
            exit_code = exit_code or 1
        trial.collect_communication_capture()
        (output_dir / "run_summary.json").write_text(json.dumps({
            "ok": error is None and trial.completed, "error": error,
            "motion_started": trial.motion_started or trial.completed,
            "completed": trial.completed, "camera_frames": trial.recorder.frames,
            "camera_error": trial.recorder.error,
            "communication_capture": trial.communication_capture,
            "config": config,
        }, indent=2) + "\n")
        trial.close()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
