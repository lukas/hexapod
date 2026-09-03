#!/usr/bin/env python3
"""Generate an unloaded leg radial-shear control from the L5 timing template."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "protocols" / "l5_ground_radial_shear_hysteresis_v1.json"
FEMUR_MM = 90.0
TIBIA_MM = 150.0
AIR_Y_MM = 60.0
CAMERA_CLEARANCE_YAW_DEG = 35.0


def fk(hip_deg: float, knee_absolute_deg: float) -> tuple[float, float]:
    hip = math.radians(hip_deg)
    knee = math.radians(knee_absolute_deg)
    return (
        FEMUR_MM * math.cos(hip) + TIBIA_MM * math.cos(knee),
        FEMUR_MM * math.sin(hip) + TIBIA_MM * math.sin(knee),
    )


def ik(x_mm: float, y_mm: float) -> tuple[float, float]:
    cosine = (
        x_mm * x_mm + y_mm * y_mm - FEMUR_MM * FEMUR_MM - TIBIA_MM * TIBIA_MM
    ) / (2.0 * FEMUR_MM * TIBIA_MM)
    relative_knee = math.acos(max(-1.0, min(1.0, cosine)))
    hip = math.atan2(y_mm, x_mm) - math.atan2(
        TIBIA_MM * math.sin(relative_knee),
        FEMUR_MM + TIBIA_MM * math.cos(relative_knee),
    )
    knee_absolute = hip + relative_knee
    return math.degrees(hip), math.degrees(knee_absolute)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--leg", type=int, choices=range(6), default=5)
    parser.add_argument("--clear-adjacent", action="store_true")
    args = parser.parse_args()
    leg = args.leg
    hip_joint = leg * 3 + 1
    knee_joint = leg * 3 + 2

    protocol = json.loads(SOURCE.read_text(encoding="utf-8"))
    segment = protocol["segments"][0]
    air_base = ik(180.0, AIR_Y_MM)
    transformed: list[list[float]] = []

    def smoothstep(value: float) -> float:
        value = max(0.0, min(1.0, value))
        return value * value * (3.0 - 2.0 * value)

    for t_s, source_q in zip(segment["t_s"], segment["q_deg"]):
        q = list(source_q)
        # The checked-in L5 protocol supplies the proven timing and radial
        # path. Clear its active joints before assigning that path to a
        # different leg.
        if leg != 5:
            q[16] = 0.0
            q[17] = 0.0
        if 6.0 <= t_s < 14.0 or 62.0 <= t_s < 70.0:
            hip, knee = air_base
        elif 14.0 <= t_s < 62.0:
            x_mm, _ = fk(float(source_q[16]), float(source_q[17]))
            hip, knee = ik(x_mm, AIR_Y_MM)
        else:
            # Preserve the template's eased home↔air transitions.
            hip, knee = float(source_q[16]), float(source_q[17])
        q[hip_joint] = round(hip, 3)
        q[knee_joint] = round(knee, 3)
        if args.clear_adjacent:
            if t_s < 1.0 or t_s >= 75.0:
                clearance = 0.0
            elif t_s < 6.0:
                clearance = smoothstep((t_s - 1.0) / 5.0)
            elif t_s < 70.0:
                clearance = 1.0
            else:
                clearance = 1.0 - smoothstep((t_s - 70.0) / 5.0)
            q[((leg - 1) % 6) * 3] = round(
                -CAMERA_CLEARANCE_YAW_DEG * clearance, 3
            )
            q[((leg + 1) % 6) * 3] = round(
                CAMERA_CLEARANCE_YAW_DEG * clearance, 3
            )
        transformed.append(q)

    protocol["name"] = f"l{leg}_air_radial_shear_hysteresis_control_v1"
    protocol["created"] = "2026-09-02T18:02:00-07:00"
    protocol["description"] = (
        f"Supported-chassis unloaded control for the L{leg} planted radial-shear test. "
        f"Keep L{leg} retracted at y=60 mm and replay the same x=180 to 187.5 to 195 mm "
        "three-cycle timing and 3 s midpoint dwells. This distinguishes unloaded "
        "servo/geartrain hysteresis from ground-load-dependent compliance. Soft torque "
        "700; trip after three consecutive readings above 0.75 A; immediate ceiling 3.0 A."
        + (
            f" Adjacent legs L{(leg - 1) % 6}/L{(leg + 1) % 6} ease to "
            f"{-CAMERA_CLEARANCE_YAW_DEG:+.0f}/{CAMERA_CLEARANCE_YAW_DEG:+.0f} deg yaw "
            "to clear the camera view, then return to zero."
            if args.clear_adjacent else ""
        )
    )
    segment["label"] = f"L{leg}_three_quasistatic_air_shear_control_cycles"
    segment["q_deg"] = transformed

    assert len(segment["t_s"]) == len(transformed) == 780
    for t_s, q in zip(segment["t_s"], transformed):
        if 14.0 <= t_s < 62.0:
            _, y_mm = fk(q[hip_joint], q[knee_joint])
            assert abs(y_mm - AIR_Y_MM) < 0.01
    if args.clear_adjacent:
        assert transformed[0][((leg - 1) % 6) * 3] == 0.0
        assert transformed[60][((leg - 1) % 6) * 3] == -CAMERA_CLEARANCE_YAW_DEG
        assert transformed[-1][((leg - 1) % 6) * 3] == 0.0

    output = ROOT / "protocols" / f"{protocol['name']}.json"
    output.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
