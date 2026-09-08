"""Derive a deterministic time-reversed trajectory protocol.

The transform reverses only the command rows of every trajectory segment.
Timestamps, cadence, safety limits, torque settings, and every command value
are preserved.  The source protocol hash is embedded for review and replay.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


from sysid_protocol import protocol_hash, validate


def reverse_protocol_time(
    source: dict,
    *,
    name: str,
    description: str,
) -> dict:
    """Return a validated protocol with each trajectory command stream reversed."""
    errors = validate(source)
    if errors:
        raise ValueError("invalid source protocol: " + "; ".join(errors))
    if not source.get("segments") or any(
        segment.get("kind") != "traj" for segment in source["segments"]
    ):
        raise ValueError("temporal reversal requires trajectory-only segments")

    result = copy.deepcopy(source)
    result["name"] = name
    result["description"] = description
    result["trajectory_transform"] = {
        "method": "reverse_outbound_inbound_temporal_order",
        "preserve_command_values": True,
        "preserve_dwells": True,
        "source_protocol_hash": protocol_hash(source),
    }
    for segment in result["segments"]:
        segment["q_deg"] = list(reversed(segment["q_deg"]))

    errors = validate(result)
    if errors:
        raise ValueError("reversed protocol is invalid: " + "; ".join(errors))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--description", required=True)
    args = parser.parse_args()

    source = json.loads(args.source.read_text(encoding="utf-8"))
    result = reverse_protocol_time(
        source,
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
