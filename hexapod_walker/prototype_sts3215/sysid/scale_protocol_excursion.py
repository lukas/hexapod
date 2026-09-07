"""Derive a deterministic scaled-excursion sysid protocol.

Trajectory samples are scaled about ``home_deg`` while timestamps, safety
limits, and every non-trajectory field remain unchanged.  The output embeds
the source protocol's canonical hash so a guarded runner can prove which
reviewed command stream was transformed.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

LINUX_CONTROL = Path(__file__).resolve().parents[1] / "linux_control"
if str(LINUX_CONTROL) not in sys.path:
    sys.path.insert(0, str(LINUX_CONTROL))

from sysid_protocol import N_JOINTS, protocol_hash, validate  # noqa: E402


def scale_protocol(
    source: dict,
    *,
    scale: float,
    name: str,
    description: str,
) -> dict:
    """Return ``source`` with command deviations from home scaled by ``scale``."""
    errors = validate(source)
    if errors:
        raise ValueError("invalid source protocol: " + "; ".join(errors))
    if not 0.0 < scale <= 1.0:
        raise ValueError("scale must be in (0, 1]")

    home = source.get("home_deg")
    if not isinstance(home, list) or len(home) != N_JOINTS:
        raise ValueError("scaled trajectory protocol requires 18-value home_deg")

    result = copy.deepcopy(source)
    result["name"] = name
    result["description"] = description
    result["trajectory_transform"] = {
        "method": "scale_joint_deviation_from_home",
        "scale": scale,
        "source_protocol_hash": protocol_hash(source),
    }
    for segment in result["segments"]:
        kind = segment.get("kind")
        if kind == "traj":
            segment["q_deg"] = [
                [float(h) + scale * (float(q) - float(h))
                 for h, q in zip(home, row)]
                for row in segment["q_deg"]
            ]
        elif kind in {"step", "sine"}:
            segment["amp_deg"] = float(segment["amp_deg"]) * scale

    errors = validate(result)
    if errors:
        raise ValueError("scaled protocol is invalid: " + "; ".join(errors))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--scale", type=float, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--description", required=True)
    args = parser.parse_args()

    source = json.loads(args.source.read_text(encoding="utf-8"))
    result = scale_protocol(
        source,
        scale=args.scale,
        name=args.name,
        description=args.description,
    )
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    print(f"{args.output}: {protocol_hash(result)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
