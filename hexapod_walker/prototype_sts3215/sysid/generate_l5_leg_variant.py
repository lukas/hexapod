#!/usr/bin/env python3
"""Remap a checked L5 trajectory protocol to another leg."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CAMERA_CLEARANCE_YAW_DEG = 35.0


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--leg", type=int, choices=range(6), required=True)
    parser.add_argument("--clear-adjacent", action="store_true")
    args = parser.parse_args()

    protocol = json.loads(args.source.read_text(encoding="utf-8"))
    source_name = str(protocol["name"])
    if not source_name.startswith("l5_"):
        raise SystemExit("source protocol name must start with l5_")
    if len(protocol.get("segments", [])) != 1:
        raise SystemExit("expected one trajectory segment")
    segment = protocol["segments"][0]
    if segment.get("kind") != "traj":
        raise SystemExit("expected a traj segment")

    leg = args.leg
    duration_s = float(segment["t_s"][-1]) + 1.0 / float(protocol["hz"])
    transformed: list[list[float]] = []
    for t_s, source_q in zip(segment["t_s"], segment["q_deg"]):
        if len(source_q) != 18:
            raise SystemExit("expected 18-joint trajectory rows")
        q = list(source_q)
        source_leg = q[15:18]
        q[15:18] = [0.0, 0.0, 0.0]
        q[leg * 3:leg * 3 + 3] = source_leg
        if args.clear_adjacent:
            if t_s < 1.0 or t_s >= duration_s - 1.0:
                clearance = 0.0
            elif t_s < 6.0:
                clearance = smoothstep((t_s - 1.0) / 5.0)
            elif t_s < duration_s - 6.0:
                clearance = 1.0
            else:
                clearance = 1.0 - smoothstep(
                    (t_s - (duration_s - 6.0)) / 5.0
                )
            q[((leg - 1) % 6) * 3] = round(
                -CAMERA_CLEARANCE_YAW_DEG * clearance, 3
            )
            q[((leg + 1) % 6) * 3] = round(
                CAMERA_CLEARANCE_YAW_DEG * clearance, 3
            )
        transformed.append(q)

    name = "l" + str(leg) + source_name[2:]
    protocol["name"] = name
    protocol["created"] = "2026-09-02T18:40:00-07:00"
    protocol["description"] = str(protocol.get("description", "")).replace(
        "L5", f"L{leg}"
    ) + (
        f" Adjacent legs L{(leg - 1) % 6}/L{(leg + 1) % 6} ease to "
        f"{-CAMERA_CLEARANCE_YAW_DEG:+.0f}/{CAMERA_CLEARANCE_YAW_DEG:+.0f} deg yaw "
        "to clear the camera view, then return to zero."
        if args.clear_adjacent else ""
    )
    segment["label"] = str(segment.get("label", "")).replace("L5", f"L{leg}")
    segment["q_deg"] = transformed

    assert transformed[0] == [0.0] * 18
    assert transformed[-1] == [0.0] * 18
    output = ROOT / "protocols" / f"{name}.json"
    output.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
