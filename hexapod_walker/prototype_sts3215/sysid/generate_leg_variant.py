#!/usr/bin/env python3
"""Remap a checked single-leg trajectory protocol to another leg.

This tool has always taken --leg and done the whole remapping. Until
2026-09-10 it also insisted its source be named ``l5_`` and read the source
columns from leg 5's slice, because it was written for the L5 ladder. The
belly-rest hysteresis family's reviewed source is ``l2_``, so the tool
rejected it, and six per-leg protocols were instead hand-authored one at a
time -- roughly 45 minutes and $50 of agent work each, for a remap this
function does exactly. The source leg is now read from the protocol name.

The transform stays deliberately narrow: it moves one leg's three columns to
another leg, leaves every other joint at home, and asserts the trajectory
still starts and ends at all-zero. ``--strict-independent`` additionally
asserts nothing but the target leg's hip and knee ever moves.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


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
    parser.add_argument("--version", type=int, default=1)
    parser.add_argument("--strict-independent", action="store_true")
    parser.add_argument("--created")
    args = parser.parse_args()
    if args.version < 1:
        parser.error("--version must be at least 1")
    if args.clear_adjacent and args.strict_independent:
        parser.error("--clear-adjacent conflicts with --strict-independent")

    protocol = json.loads(args.source.read_text(encoding="utf-8"))
    try:
        remap_protocol_to_leg(
            protocol, args.leg,
            clear_adjacent=args.clear_adjacent,
            strict_independent=args.strict_independent,
            version=args.version,
            created=args.created,
        )
    except ValueError as error:
        raise SystemExit(str(error)) from error
    output = ROOT / "protocols" / f"{protocol['name']}.json"
    output.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
    print(output)


def source_leg_of(name: str) -> int:
    """The leg a protocol was authored for, from its own name."""
    match = re.match(r"^l([0-5])_", str(name))
    if match is None:
        raise ValueError(
            f"source protocol name must start with l<0-5>_, got {name!r}"
        )
    return int(match.group(1))


def remap_protocol_to_leg(
    protocol: dict, leg: int, *, clear_adjacent: bool = False,
    strict_independent: bool = False, version: int = 1,
    created: str | None = None,
) -> dict:
    """Move the source leg's three columns onto ``leg``, in place."""
    if leg not in range(6):
        raise ValueError("leg must be 0-5")
    if version < 1:
        raise ValueError("version must be at least 1")
    if clear_adjacent and strict_independent:
        raise ValueError("clear_adjacent conflicts with strict_independent")
    source_name = str(protocol["name"])
    source = source_leg_of(source_name)
    if source == leg:
        raise ValueError(
            f"source protocol is already leg {leg}; nothing to remap"
        )
    if len(protocol.get("segments", [])) != 1:
        raise ValueError("expected one trajectory segment")
    segment = protocol["segments"][0]
    if segment.get("kind") != "traj":
        raise ValueError("expected a traj segment")
    args = argparse.Namespace(
        clear_adjacent=clear_adjacent, strict_independent=strict_independent,
        version=version, created=created,
    )
    duration_s = float(segment["t_s"][-1]) + 1.0 / float(protocol["hz"])
    transformed: list[list[float]] = []
    for t_s, source_q in zip(segment["t_s"], segment["q_deg"]):
        if len(source_q) != 18:
            raise SystemExit("expected 18-joint trajectory rows")
        q = list(source_q)
        moved = q[source * 3:source * 3 + 3]
        q[source * 3:source * 3 + 3] = [0.0, 0.0, 0.0]
        q[leg * 3:leg * 3 + 3] = moved
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
    name = re.sub(r"_v\d+$", f"_v{args.version}", name)
    protocol["name"] = name
    protocol["created"] = args.created or "2026-09-02T18:40:00-07:00"
    protocol["description"] = str(protocol.get("description", "")).replace(
        f"L{source}", f"L{leg}"
    ) + (
        f" Adjacent legs L{(leg - 1) % 6}/L{(leg + 1) % 6} ease to "
        f"{-CAMERA_CLEARANCE_YAW_DEG:+.0f}/{CAMERA_CLEARANCE_YAW_DEG:+.0f} deg yaw "
        "to clear the camera view, then return to zero."
        if args.clear_adjacent else (
            f" Strict independent-leg variant: only L{leg} hip and knee "
            "change; every other joint target stays at home."
            if args.strict_independent else ""
        )
    )
    segment["label"] = str(segment.get("label", "")).replace(
        f"L{source}", f"L{leg}")
    segment["q_deg"] = transformed

    assert transformed[0] == [0.0] * 18
    assert transformed[-1] == [0.0] * 18
    if args.strict_independent:
        moving = {leg * 3 + 1, leg * 3 + 2}
        assert all(
            value == 0.0
            for row in transformed
            for joint, value in enumerate(row)
            if joint not in moving
        )
    return protocol


if __name__ == "__main__":
    main()
