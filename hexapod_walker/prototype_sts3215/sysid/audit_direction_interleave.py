"""Audit whether whole trajectory streams can be interleaved by semantic cycle.

This is an offline admission tool.  It deliberately does not guess that equal
row slices are cycles: radial-shear protocols may share approach, base-dwell,
and return rows across several measurement cycles.  A composition is admitted
only when the source carries explicit, non-overlapping ``semantic_cycles`` row
boundaries.  Without those boundaries the report still identifies the
matched-dwell cycles and quantifies the unsafe equal-slice alternative.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from linux_control.sysid_protocol import materialize, protocol_hash, validate

FEMUR_MM = 90.0
TIBIA_MM = 150.0
MIN_PLATEAU_SAMPLES = 5
COMMAND_MATCH_ATOL_DEG = 0.002


@dataclass(frozen=True)
class Plateau:
    start: int
    stop: int
    command: tuple[float, float]


def _near(left: tuple[float, float], right: tuple[float, float]) -> bool:
    return all(
        math.isclose(a, b, abs_tol=COMMAND_MATCH_ATOL_DEG, rel_tol=0.0)
        for a, b in zip(left, right)
    )


def _foot_x(command: tuple[float, float]) -> float:
    hip, knee = map(math.radians, command)
    return FEMUR_MM * math.cos(hip) + TIBIA_MM * math.cos(knee)


def _active_leg(rows: list[list[float]]) -> int:
    moving = []
    for leg in range(6):
        joints = (3 * leg + 1, 3 * leg + 2)
        span = sum(
            max(row[j] for row in rows) - min(row[j] for row in rows) for j in joints
        )
        if span > 0.1:
            moving.append(leg)
    if len(moving) != 1:
        raise ValueError(f"expected exactly one active hip/knee leg, found {moving}")
    return moving[0]


def _plateaus(rows: list[list[float]], leg: int) -> list[Plateau]:
    joints = (3 * leg + 1, 3 * leg + 2)
    commands = [tuple(float(row[j]) for j in joints) for row in rows]
    result: list[Plateau] = []
    start = 0
    for stop in range(1, len(commands) + 1):
        if stop == len(commands) or commands[stop] != commands[start]:
            if stop - start >= MIN_PLATEAU_SAMPLES:
                result.append(Plateau(start, stop, commands[start]))
            start = stop
    return result


def semantic_cycle_boundaries(rows: list[list[float]]) -> list[dict[str, Any]]:
    """Locate analyzer-equivalent base/midpoint/peak/midpoint/base windows."""

    plateaus = _plateaus(rows, _active_leg(rows))
    cycles = []
    for index in range(len(plateaus) - 4):
        base, outbound, peak, inbound, returned = plateaus[index : index + 5]
        if not (
            _near(base.command, returned.command)
            and _near(outbound.command, inbound.command)
        ):
            continue
        if not (
            _foot_x(base.command) + 0.05
            < _foot_x(outbound.command)
            < _foot_x(peak.command) - 0.05
        ):
            continue
        cycles.append(
            {
                "cycle_index": len(cycles),
                "command_rows": [base.start, returned.stop],
                "outbound_midpoint_rows": [outbound.start + 1, outbound.stop],
                "inbound_midpoint_rows": [inbound.start + 1, inbound.stop],
                "dwell_samples_per_side": outbound.stop - outbound.start - 1,
            }
        )
    return cycles


def _max_step(rows: list[list[float]]) -> float:
    return max(
        abs(value - rows[index - 1][joint])
        for index, row in enumerate(rows[1:], start=1)
        for joint, value in enumerate(row)
    )


def _stream_sha256(rows: list[list[float]]) -> str:
    encoded = json.dumps(rows, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def audit_direction_interleave(
    source: dict[str, Any],
    *,
    direction_order: list[str],
    expected_rows: int,
    max_allowed_adjacent_step_deg: float,
    expected_source_hash: str | None = None,
    expected_reversed_hash: str | None = None,
) -> dict[str, Any]:
    """Return a deterministic admission report without producing commands."""

    errors = validate(source)
    if errors:
        raise ValueError("invalid source protocol: " + "; ".join(errors))
    if set(direction_order) - {"normal", "reversed"}:
        raise ValueError("direction_order entries must be normal or reversed")
    if not direction_order or expected_rows % len(direction_order):
        raise ValueError("expected_rows must divide evenly across direction_order")

    materialized = materialize(source)
    rows = [tick["cmd"] for tick in materialized["ticks"]]
    source_hash = protocol_hash(source)
    if expected_source_hash and source_hash != expected_source_hash:
        raise ValueError(
            f"source protocol hash {source_hash} != expected {expected_source_hash}"
        )

    cycles = semantic_cycle_boundaries(rows)
    overlaps = [
        {
            "left_cycle": left["cycle_index"],
            "right_cycle": right["cycle_index"],
            "shared_rows": [right["command_rows"][0], left["command_rows"][1]],
        }
        for left, right in itertools.pairwise(cycles)
        if right["command_rows"][0] < left["command_rows"][1]
    ]
    explicit = source.get("semantic_cycles")
    explicit_ok = (
        isinstance(explicit, list)
        and len(explicit) == len(direction_order)
        and all(
            isinstance(boundary, list)
            and len(boundary) == 2
            and all(isinstance(value, int) for value in boundary)
            and 0 <= boundary[0] < boundary[1] <= len(rows)
            for boundary in explicit
        )
        and all(left[1] <= right[0] for left, right in itertools.pairwise(explicit))
    )

    chunk_rows = expected_rows // len(direction_order)
    naive = []
    reversed_rows = list(reversed(rows))
    for index, direction in enumerate(direction_order):
        selected = rows if direction == "normal" else reversed_rows
        start = (index % (len(rows) // chunk_rows)) * chunk_rows
        naive.extend(selected[start : start + chunk_rows])
    candidate = naive
    if explicit_ok:
        candidate = []
        for direction, (start, stop) in zip(direction_order, explicit):
            selected = rows if direction == "normal" else reversed_rows
            selected_start, selected_stop = (
                (start, stop)
                if direction == "normal"
                else (len(rows) - stop, len(rows) - start)
            )
            candidate.extend(selected[selected_start:selected_stop])
    source_max_step = _max_step(rows)
    naive_max_step = _max_step(naive)
    candidate_max_step = _max_step(candidate)

    # Explicit boundaries are intentionally required.  Analyzer windows alone
    # overlap at shared base dwells and therefore cannot define row ownership.
    materializable = bool(
        explicit_ok
        and len(candidate) == expected_rows
        and candidate_max_step <= max_allowed_adjacent_step_deg
    )
    reasons = []
    if not explicit_ok:
        reasons.append(
            "source lacks explicit non-overlapping semantic_cycles row boundaries"
        )
    if overlaps and not explicit_ok:
        reasons.append(
            "analyzer-equivalent cycle windows overlap at shared base dwells"
        )
    if not explicit_ok and naive_max_step > max_allowed_adjacent_step_deg:
        reasons.append("equal-row slicing exceeds the adjacent-step limit")
    if explicit_ok and len(candidate) != expected_rows:
        reasons.append("explicit semantic cycle rows do not total requested_rows")
    if explicit_ok and candidate_max_step > max_allowed_adjacent_step_deg:
        reasons.append(
            "explicit semantic cycle composition exceeds the adjacent-step limit"
        )

    return {
        "schema_version": 1,
        "admitted": materializable and not reasons,
        "source_protocol_hash": source_hash,
        "reversed_protocol_hash_claim": expected_reversed_hash,
        "source_rows": len(rows),
        "requested_rows": expected_rows,
        "direction_order": direction_order,
        "materialized_trajectory_hash": (
            _stream_sha256(candidate) if materializable and not reasons else None
        ),
        "semantic_cycle_boundaries": cycles,
        "cycle_boundary_overlaps": overlaps,
        "adjacent_step_report": {
            "source_max_deg": round(source_max_step, 9),
            "equal_slice_candidate_max_deg": round(naive_max_step, 9),
            "explicit_candidate_max_deg": (
                round(candidate_max_step, 9) if explicit_ok else None
            ),
            "allowed_max_deg": max_allowed_adjacent_step_deg,
            "passed": candidate_max_step <= max_allowed_adjacent_step_deg,
        },
        "dwell_equivalence_report": {
            "detected_cycle_count": len(cycles),
            "samples_per_side": sorted(
                {cycle["dwell_samples_per_side"] for cycle in cycles}
            ),
            "preservable_by_unambiguous_composition": explicit_ok,
        },
        "deterministic_replay_report": {
            "execution": "offline_no_io_admission_audit",
            "robot_contacted": False,
            "robot_motion": False,
            "candidate_command_stream_sha256": _stream_sha256(candidate),
            "passed": materializable and not reasons,
            "reasons": reasons,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--direction-order", required=True)
    parser.add_argument("--expected-rows", type=int, required=True)
    parser.add_argument("--max-adjacent-step-deg", type=float, required=True)
    parser.add_argument("--source-hash")
    parser.add_argument("--reversed-hash")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = audit_direction_interleave(
        json.loads(args.source.read_text(encoding="utf-8")),
        direction_order=args.direction_order.split(","),
        expected_rows=args.expected_rows,
        max_allowed_adjacent_step_deg=args.max_adjacent_step_deg,
        expected_source_hash=args.source_hash,
        expected_reversed_hash=args.reversed_hash,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["admitted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
