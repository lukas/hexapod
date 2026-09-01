#!/usr/bin/env python3
"""Replay the hardware scripted-gait protocol in MuJoCo without a viewer.

The output is deliberately shaped for comparison with
``run_scripted_gait_suite.py``: every physics tick records the gait,
direction, body motion, joint state, estimated servo current, and foot sites.
Physics runs as fast as the CPU allows; ``sim_t_s`` is the comparison clock.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rl_move.sim.web_server import (
    DEFAULT_LOG_DIR,
    DEFAULT_STANCE_POLICY,
    DEFAULT_WALK_POLICY,
)
from rl_move.sim.web_session import SimWebConfig, SimWebSession
from hexapod_core.joint_frame import (
    FRAME_ROBOT_ABS,
    JOINT_CONTRACT,
    mujoco_rel_rad_to_robot_abs_deg,
    robot_abs_deg_to_mujoco_rel_rad,
)


GAITS = {
    0: "tripod_drag",
    1: "noslip_tripod",
    2: "noslip_ripple",
    3: "noslip_wave",
    4: "se2_tetrapod",
    5: "se2_wave",
    6: "se2_cpg_robust120",
    7: "noslip_clamp_fit",
    8: "middle_tuck_quad",
}


def _resolve(policy_dir: Path, path: Path | None) -> Path | None:
    if path is None:
        return None
    raw = str(path)
    if raw.startswith("scripted:"):
        return Path(raw.removeprefix("scripted:"))
    return path if path.is_absolute() else policy_dir / path


def _json(values: Any) -> str:
    return json.dumps(values, separators=(",", ":"))


def main() -> int:
    parser = argparse.ArgumentParser()
    root = ROOT
    policy_dir = root / "rl_move" / "sim" / "policies"
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--gaits", type=int, nargs="+", default=list(GAITS))
    parser.add_argument("--speed-mm-s", type=float, default=30.0)
    parser.add_argument("--direction-s", type=float, default=10.0)
    parser.add_argument("--settle-s", type=float, default=1.5)
    parser.add_argument("--plant-hip-abs-deg", type=float, default=20.0)
    parser.add_argument("--plant-knee-abs-deg", type=float, default=80.0)
    parser.add_argument("--cpg", default="cpg_controller_robust120_yawtrim.json")
    parser.add_argument("--policy-dir", type=Path, default=policy_dir)
    parser.add_argument("--stance", type=Path, default=DEFAULT_STANCE_POLICY)
    parser.add_argument("--walk", type=Path, default=DEFAULT_WALK_POLICY)
    parser.add_argument(
        "--recover",
        type=Path,
        default=Path("ppo_goal_cw_recover_any21_pop3_B14.zip"),
    )
    args = parser.parse_args()
    bad = [gait for gait in args.gaits if gait not in GAITS]
    if bad:
        parser.error(f"unknown gait IDs: {bad}")

    args.output_dir.mkdir(parents=True, exist_ok=False)
    cfg = SimWebConfig(
        policy_dir=args.policy_dir,
        stance=_resolve(args.policy_dir, args.stance),
        walk=_resolve(args.policy_dir, args.walk),
        recover=_resolve(args.policy_dir, args.recover),
        log_dir=DEFAULT_LOG_DIR,
        realtime=0.0,
        viewer=True,       # prevents the background realtime tick thread
        web_frames=False,
        phase_obs=True,
    )
    session = SimWebSession(cfg)
    session.armed = True
    # Hardware telemetry and gait code use an ABSOLUTE-tibia knee, while the
    # MuJoCo hinge is relative to the femur. A hardware 20/80 plant is thus a
    # MuJoCo 20/60 plant, not the legacy policy plant 20/80 (which is 20/100
    # in the hardware frame). This replay is a physical-parity experiment,
    # never a legacy-checkpoint compatibility replay, so make the conversion
    # explicit and fail closed if the round trip ever drifts.
    plant_robot_abs_deg = np.asarray([
        0.0, args.plant_hip_abs_deg, args.plant_knee_abs_deg,
    ] * 6, dtype=float)
    plant_model_rel_rad = robot_abs_deg_to_mujoco_rel_rad(
        plant_robot_abs_deg
    )
    posed = session.sim_pose(
        plant_robot_abs_deg.tolist(),
        source="hardware-absolute parity plant",
    )
    if not posed.get("ok"):
        raise RuntimeError(f"could not install hardware parity plant: {posed}")
    plant_roundtrip_deg = np.asarray(
        mujoco_rel_rad_to_robot_abs_deg(session.q_plant), dtype=float
    )
    if not np.allclose(plant_roundtrip_deg, plant_robot_abs_deg, atol=0.05):
        raise RuntimeError(
            "joint-frame parity failure: requested hardware-absolute plant "
            f"{plant_robot_abs_deg[:3].tolist()}, MuJoCo installed "
            f"{np.degrees(plant_model_rel_rad[:3]).tolist()}, round-trip "
            f"{plant_roundtrip_deg[:3].tolist()}"
        )
    unavailable: list[dict] = []
    if 6 in args.gaits:
        cpg = session.cmd(f"CPGLOAD {args.cpg}")
        if not cpg.get("ok"):
            unavailable.append({
                "gait": 6,
                "name": GAITS[6],
                "reason": cpg.get("error", "CPG artifact unavailable"),
            })
            args.gaits = [gait for gait in args.gaits if gait != 6]

    csv_path = args.output_dir / "sim_telemetry.csv"
    summaries: list[dict[str, Any]] = []
    with csv_path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow([
            "sim_t_s", "phase", "gait", "gait_name", "direction",
            "chassis_x_m", "chassis_y_m", "chassis_z_m",
            "vx_body_mps", "vy_body_mps", "roll_deg", "pitch_deg",
            "max_joint_current_a", "bus_current_a", "joint_degrees",
            "joint_command_degrees", "joint_currents_a", "foot_xyz_m",
            "joint_frame", "joint_contract", "downed", "status",
        ])

        def sample(phase: str, gait: int, direction: str) -> None:
            live = session._live()
            state = session.env._state
            currents = (
                np.abs(np.asarray(state.servo_current, dtype=float))
                if state is not None and state.servo_current is not None
                else np.zeros(18, dtype=float)
            )
            command = (
                np.degrees(np.asarray(
                    state.commanded_position, dtype=float)).tolist()
                if state is not None else [None] * 18
            )
            xyz = live["chassis_xyz_m"]
            writer.writerow([
                round(session.sim_t, 4), phase, gait, GAITS[gait], direction,
                xyz[0], xyz[1], xyz[2], live["vx_body"], live["vy_body"],
                live["roll_deg"], live["pitch_deg"],
                round(float(np.max(currents)), 5),
                round(float(np.sum(currents)), 5),
                _json(live["joint_deg"]), _json(command),
                _json(np.round(currents, 5).tolist()),
                _json(live["foot_xyz_m"]), FRAME_ROBOT_ABS, JOINT_CONTRACT,
                int(session.downed), live["status"],
            ])

        def advance(seconds: float, phase: str, gait: int,
                    direction: str) -> None:
            ticks = int(round(seconds / session.env.dt))
            for _ in range(ticks):
                with session.lock:
                    session._tick_locked()
                    sample(phase, gait, direction)

        for gait in args.gaits:
            selected = session.cmd(f"GAIT {gait}")
            if not selected.get("ok"):
                raise RuntimeError(selected)
            start = np.asarray(session._live()["chassis_xyz_m"], dtype=float)
            gait_peak_current = 0.0
            gait_peak_tilt = 0.0
            fell = False
            for direction, speed in (
                ("forward", args.speed_mm_s),
                ("backward", -args.speed_mm_s),
            ):
                response = session.cmd(f"J {speed:.1f} 0 0 {gait}")
                if not response.get("ok"):
                    raise RuntimeError(response)
                advance(
                    args.direction_s,
                    f"gait_{gait}_{direction}", gait, direction,
                )
                response = session.cmd("J 0 0 0")
                if not response.get("ok"):
                    raise RuntimeError(response)
                advance(
                    args.settle_s,
                    f"gait_{gait}_{direction}_settle", gait, direction,
                )
                fell = fell or session.downed
                if session.downed:
                    break

            end = np.asarray(session._live()["chassis_xyz_m"], dtype=float)
            # Read the just-written rows later for aggregate peaks; keeping the
            # primary output tick-complete is more useful than a second schema.
            summaries.append({
                "gait": gait,
                "name": GAITS[gait],
                "start_xyz_m": start.tolist(),
                "end_xyz_m": end.tolist(),
                "net_xy_m": (end[:2] - start[:2]).tolist(),
                "fell": fell,
                "peak_current_a": gait_peak_current,
                "peak_tilt_deg": gait_peak_tilt,
            })
            if session.downed:
                # Keep later gait coverage independent instead of allowing one
                # failed controller to erase the rest of the requested suite.
                session.sim_reset("plant")
                session.armed = True

    # Fill peak aggregates from the canonical tick CSV.
    by_gait: dict[int, dict[str, float]] = {
        gait: {"peak_current_a": 0.0, "peak_tilt_deg": 0.0}
        for gait in args.gaits
    }
    with csv_path.open(newline="") as stream:
        for row in csv.DictReader(stream):
            gait = int(row["gait"])
            stats = by_gait[gait]
            stats["peak_current_a"] = max(
                stats["peak_current_a"], float(row["max_joint_current_a"])
            )
            stats["peak_tilt_deg"] = max(
                stats["peak_tilt_deg"], abs(float(row["roll_deg"])),
                abs(float(row["pitch_deg"])),
            )
    for summary in summaries:
        summary.update(by_gait[summary["gait"]])
    payload = {
        "protocol": {
            "joint_frame": FRAME_ROBOT_ABS,
            "joint_contract": JOINT_CONTRACT,
            "speed_mm_s": args.speed_mm_s,
            "direction_s": args.direction_s,
            "settle_s": args.settle_s,
            "gaits": args.gaits,
            "cpg": args.cpg,
            "plant_robot_absolute_deg": plant_robot_abs_deg.tolist(),
            "plant_mujoco_relative_deg": np.degrees(
                plant_model_rel_rad
            ).tolist(),
            "joint_frame_roundtrip_verified": True,
        },
        "dt_s": session.env.dt,
        "gaits": summaries,
        "unavailable": unavailable,
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(payload, indent=2) + "\n"
    )
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
