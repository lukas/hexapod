#!/usr/bin/env python3
"""Compose the six checked per-leg protocols into one simultaneous protocol.

Each ``l<N>_`` source in a belly-rest shear ladder drives exactly its own
leg's hip and knee (columns ``3N+1``/``3N+2``) and leaves the other sixteen
joints at home, so the six trajectories occupy disjoint columns and their
column-wise union is the same motion run by all six legs at once.  Every
commanded value in the output is copied verbatim from a source; nothing is
interpolated, rescaled, or invented.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent

# Protocol-level settings that must agree before the sources can be merged:
# they describe one shared bus/servo contract for the composed run.
SHARED_KEYS = (
    "sysid_protocol",
    "hz",
    "write_speed",
    "write_acc",
    "soft_torque",
    "max_current_a",
    "current_trip_polls",
    "hard_current_a",
    "home_deg",
)


def leg_of(protocol: dict) -> int:
    """Return the leg index declared by an ``l<N>_`` protocol name."""
    match = re.match(r"^l([0-5])_", str(protocol["name"]))
    if match is None:
        raise SystemExit(
            f"source protocol name must start with l<0-5>_: {protocol['name']!r}"
        )
    return int(match.group(1))


def moving_columns(rows: list[list[float]]) -> set[int]:
    return {
        joint
        for row in rows
        for joint, value in enumerate(row)
        if float(value) != 0.0
    }


def load_source(path: Path) -> tuple[int, dict, list[list[float]]]:
    protocol = json.loads(path.read_text(encoding="utf-8"))
    if len(protocol.get("segments", [])) != 1:
        raise SystemExit(f"{path.name}: expected one trajectory segment")
    segment = protocol["segments"][0]
    if segment.get("kind") != "traj":
        raise SystemExit(f"{path.name}: expected a traj segment")
    rows = [list(row) for row in segment["q_deg"]]
    if any(len(row) != 18 for row in rows):
        raise SystemExit(f"{path.name}: expected 18-joint trajectory rows")

    leg = leg_of(protocol)
    allowed = {leg * 3 + 1, leg * 3 + 2}
    stray = moving_columns(rows) - allowed
    if stray:
        raise SystemExit(
            f"{path.name}: leg {leg} source moves non-{leg} joints "
            f"{sorted(stray)}; only hip/knee {sorted(allowed)} may move"
        )
    return leg, protocol, rows


def compose(sources: list[Path], name: str, created: str | None) -> dict:
    loaded = [load_source(path) for path in sources]

    legs = [leg for leg, _, _ in loaded]
    if sorted(legs) != list(range(6)):
        raise SystemExit(f"expected one source per leg 0-5, got legs {sorted(legs)}")

    base = loaded[0][1]
    for leg, protocol, _ in loaded[1:]:
        for key in SHARED_KEYS:
            if protocol.get(key) != base.get(key):
                raise SystemExit(
                    f"leg {leg} source disagrees on {key!r}: "
                    f"{protocol.get(key)!r} != {base.get(key)!r}"
                )

    base_t_s = list(base["segments"][0]["t_s"])
    for leg, protocol, rows in loaded:
        if list(protocol["segments"][0]["t_s"]) != base_t_s:
            raise SystemExit(f"leg {leg} source has a different t_s timebase")
        if len(rows) != len(base_t_s):
            raise SystemExit(f"leg {leg} source row count != its own t_s length")

    # Disjointness is what makes a column-wise union equal to the six motions
    # superposed; overlapping sources would silently drop one leg's command.
    for i, (leg_a, _, rows_a) in enumerate(loaded):
        for leg_b, _, rows_b in loaded[i + 1:]:
            shared = moving_columns(rows_a) & moving_columns(rows_b)
            if shared:
                raise SystemExit(
                    f"legs {leg_a} and {leg_b} both move joints {sorted(shared)}"
                )

    n_rows = len(base_t_s)
    merged = [[0.0] * 18 for _ in range(n_rows)]
    for leg, _, rows in loaded:
        for column in (leg * 3 + 1, leg * 3 + 2):
            for tick in range(n_rows):
                merged[tick][column] = rows[tick][column]

    if merged[0] != [0.0] * 18 or merged[-1] != [0.0] * 18:
        raise SystemExit("composed trajectory must start and end at home")
    if moving_columns(merged) != {
        leg * 3 + offset for leg in range(6) for offset in (1, 2)
    }:
        raise SystemExit("composed trajectory does not move all six hips and knees")

    protocol = {key: base[key] for key in base if key != "segments"}
    protocol["name"] = name
    if created is not None:
        protocol["created"] = created
    protocol["description"] = (
        "All six legs driven simultaneously through the belly-rest radial "
        "shear reversal that the per-leg ladder measured one leg at a time. "
        "The chassis rests on its belly; no stand is required. Each leg's "
        "hip and knee replay their own checked per-leg trajectory unchanged "
        "and all six yaw columns stay at zero, so any difference from the "
        "isolated ladder values is attributable to eighteen joints sharing "
        "the bus and supply rather than to a different commanded path."
    )
    protocol["segments"] = [
        {
            "kind": "traj",
            "label": "all6_six_cycle_belly_rest_foot_clear_radial_shear",
            "t_s": base_t_s,
            "q_deg": merged,
        }
    ]
    return protocol


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", type=Path, nargs=6)
    parser.add_argument("--name", required=True)
    parser.add_argument("--created")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "protocols")
    args = parser.parse_args()

    protocol = compose(args.sources, args.name, args.created)
    output = args.out_dir / f"{args.name}.json"
    output.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
