#!/usr/bin/env python3
"""Generate a repeated planted radial-shear amplitude ladder for one leg."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "protocols" / "l5_ground_radial_shear_amplitude_ladder_v1.json"
HZ = 10
FEMUR_MM = 90.0
TIBIA_MM = 150.0
BASE_X_MM = 180.0
AIR_Y_MM = 60.0
GROUND_Y_MM = 120.0
AMPLITUDES_MM = (3.75, 7.5, 11.25, 15.0)
CYCLES_PER_AMPLITUDE = 3
MICRO_AMPLITUDES_MM = (0.5, 1.0, 2.0, 3.0)
MICRO_CYCLES_PER_AMPLITUDE = 5
CAMERA_CLEARANCE_YAW_DEG = 35.0


def ik(x_mm: float, y_mm: float) -> tuple[float, float]:
    cosine = (
        x_mm * x_mm + y_mm * y_mm - FEMUR_MM * FEMUR_MM - TIBIA_MM * TIBIA_MM
    ) / (2.0 * FEMUR_MM * TIBIA_MM)
    relative_knee = math.acos(max(-1.0, min(1.0, cosine)))
    hip = math.atan2(y_mm, x_mm) - math.atan2(
        TIBIA_MM * math.sin(relative_knee),
        FEMUR_MM + TIBIA_MM * math.cos(relative_knee),
    )
    return math.degrees(hip), math.degrees(hip + relative_knee)


def pose(
    leg: int,
    hip_knee: tuple[float, float] | None = None,
    *,
    clear_adjacent: bool = False,
) -> list[float]:
    q = [0.0] * 18
    if hip_knee is not None:
        q[leg * 3 + 1], q[leg * 3 + 2] = hip_knee
    if clear_adjacent:
        q[((leg - 1) % 6) * 3] = -CAMERA_CLEARANCE_YAW_DEG
        q[((leg + 1) % 6) * 3] = CAMERA_CLEARANCE_YAW_DEG
    return q


def smoothstep(value: float) -> float:
    return value * value * (3.0 - 2.0 * value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("amplitude", "micro"), default="amplitude")
    parser.add_argument("--leg", type=int, choices=range(6), default=5)
    parser.add_argument("--clear-adjacent", action="store_true")
    parser.add_argument("--version", type=int, default=1)
    parser.add_argument("--strict-independent", action="store_true")
    parser.add_argument("--created")
    args = parser.parse_args()
    if args.version < 1:
        parser.error("--version must be at least 1")
    if args.clear_adjacent and args.strict_independent:
        parser.error("--clear-adjacent conflicts with --strict-independent")
    leg = args.leg
    micro = args.profile == "micro"
    amplitudes_mm = MICRO_AMPLITUDES_MM if micro else AMPLITUDES_MM
    cycles_per_amplitude = MICRO_CYCLES_PER_AMPLITUDE if micro else CYCLES_PER_AMPLITUDE
    move_s = 0.5 if micro else 1.0
    dwell_s = 1.0 if micro else 2.0
    samples: list[list[float]] = []

    def hold(q: list[float], duration_s: float) -> None:
        samples.extend([q.copy() for _ in range(round(duration_s * HZ))])

    def move(start: list[float], end: list[float], duration_s: float) -> None:
        count = round(duration_s * HZ)
        for step in range(1, count + 1):
            blend = smoothstep(step / count)
            samples.append(
                [round(a + (b - a) * blend, 3) for a, b in zip(start, end)]
            )

    home = pose(leg)
    air = pose(
        leg, ik(BASE_X_MM, AIR_Y_MM), clear_adjacent=args.clear_adjacent
    )
    ground = pose(
        leg, ik(BASE_X_MM, GROUND_Y_MM), clear_adjacent=args.clear_adjacent
    )
    hold(home, 1.0)
    move(home, air, 5.0)
    move(air, ground, 6.0)
    hold(ground, 2.0)

    for amplitude_mm in amplitudes_mm:
        midpoint = pose(
            leg,
            ik(BASE_X_MM + amplitude_mm / 2.0, GROUND_Y_MM),
            clear_adjacent=args.clear_adjacent,
        )
        peak = pose(
            leg,
            ik(BASE_X_MM + amplitude_mm, GROUND_Y_MM),
            clear_adjacent=args.clear_adjacent,
        )
        for _ in range(cycles_per_amplitude):
            move(ground, midpoint, move_s)
            hold(midpoint, dwell_s)
            move(midpoint, peak, move_s)
            hold(peak, dwell_s)
            move(peak, midpoint, move_s)
            hold(midpoint, dwell_s)
            move(midpoint, ground, move_s)
            hold(ground, dwell_s)

    move(ground, air, 6.0)
    hold(air, 2.0)
    move(air, home, 5.0)
    hold(home, 3.0)

    t_s = [round(index / HZ, 1) for index in range(len(samples))]
    if micro:
        name = f"l{leg}_ground_radial_shear_micro_ladder_v{args.version}"
        output = ROOT / "protocols" / f"{name}.json"
        description = (
            f"Supported-chassis planted L{leg} micro radial-shear ladder at y=120 mm. "
            "Run five cycles each at 0.5, 1, 2, and 3 mm outward excursion, with "
            "1 s midpoint, peak, and base dwells. This maps the reversal deadband "
            "below the prior 3.75 mm minimum. Soft torque 700; trip after three "
            "consecutive readings above 0.75 A; immediate ceiling 3.0 A."
            + (
                f" Adjacent legs L{(leg - 1) % 6}/L{(leg + 1) % 6} ease to "
                f"{-CAMERA_CLEARANCE_YAW_DEG:+.0f}/{CAMERA_CLEARANCE_YAW_DEG:+.0f} deg yaw "
                "to clear the camera view, then return to zero."
                if args.clear_adjacent else ""
            )
        )
        label = f"L{leg}_five_cycles_at_four_micro_ground_shear_amplitudes"
    else:
        name = f"l{leg}_ground_radial_shear_amplitude_ladder_v{args.version}"
        output = ROOT / "protocols" / f"{name}.json"
        description = (
            f"Supported-chassis planted L{leg} radial-shear amplitude ladder at y=120 mm. "
            "Run three quasi-static cycles each at 3.75, 7.5, 11.25, and 15 mm "
            "outward excursion, with 2 s midpoint, peak, and base dwells. The maximum "
            "excursion matches the already completed shear test. Soft torque 700; trip "
            "after three consecutive readings above 0.75 A; immediate ceiling 3.0 A."
            + (
                f" Adjacent legs L{(leg - 1) % 6}/L{(leg + 1) % 6} ease to "
                f"{-CAMERA_CLEARANCE_YAW_DEG:+.0f}/{CAMERA_CLEARANCE_YAW_DEG:+.0f} deg yaw "
                "to clear the camera view, then return to zero."
                if args.clear_adjacent else ""
            )
        )
        label = f"L{leg}_three_cycles_at_four_ground_shear_amplitudes"

    if args.strict_independent:
        description += (
            f" Strict independent-leg variant: only L{leg} hip and knee "
            "change; every other joint target stays at home."
        )
        moving = {leg * 3 + 1, leg * 3 + 2}
        assert all(
            value == 0.0
            for row in samples
            for joint, value in enumerate(row)
            if joint not in moving
        )

    protocol = {
        "sysid_protocol": 1,
        "name": name,
        "created": args.created or "2026-09-02T17:32:00-07:00",
        "description": description,
        "hz": HZ,
        "write_speed": 180,
        "write_acc": 10,
        "soft_torque": 700,
        "max_current_a": 0.75,
        "current_trip_polls": 3,
        "hard_current_a": 3,
        "home_deg": home,
        "segments": [
            {
                "kind": "traj",
                "label": label,
                "t_s": t_s,
                "q_deg": samples,
            }
        ],
    }
    expected = 1500 if micro else 1740
    assert len(samples) == expected
    output.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
