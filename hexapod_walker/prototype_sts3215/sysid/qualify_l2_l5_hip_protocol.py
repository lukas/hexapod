"""Generate and qualify the exact reduced-amplitude L2/L5 hip protocol.

This is a pure offline tool: it imports the deterministic materializer but no
HTTP client or robot dependency.  The emitted protocol is relative to the
freshly measured segment-admission pose, so it does not assert an absolute
logical zero or bypass the separate mechanical-inspection clearance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from itertools import pairwise
from pathlib import Path
from typing import Any

from sysid_protocol import N_JOINTS, materialize, protocol_hash, validate

from . import PROTO_DIR

NAME = "l2_l5_hip_matched_midpoint_2deg_10hz_90s_v1"
SOURCE_EXPERIMENT_ID = "f809758314414667bd1591266f45f36a"
ENGINEERING_JOB_ID = "0f3135023d6f429b98edfb6123496822"
SOURCE_ANALYSIS_JOB_ID = "cedfbcaf4a4a416e90be531eab6131c0"
HZ = 10
L2_HIP = 7
L5_HIP = 16
AMPLITUDE_DEG = 2.0
SLEW_DEG_PER_TICK = 0.05


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json(document: Any) -> bytes:
    return json.dumps(
        document, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _ramp(start: float, stop: float, ticks: int) -> list[float]:
    return [start + (stop - start) * (index + 1) / ticks for index in range(ticks)]


def offsets() -> list[float]:
    """The exact 900-sample matched-midpoint trajectory."""

    cycle = (
        _ramp(0.0, AMPLITUDE_DEG, 40)
        + [AMPLITUDE_DEG] * 20
        + _ramp(AMPLITUDE_DEG, -AMPLITUDE_DEG, 80)
        + [-AMPLITUDE_DEG] * 20
        + _ramp(-AMPLITUDE_DEG, 0.0, 40)
    )
    return [0.0] * 50 + cycle * 4 + [0.0] * 50


def build_protocol() -> dict[str, Any]:
    rows = []
    for offset in offsets():
        row = [0.0] * N_JOINTS
        row[L2_HIP] = offset
        row[L5_HIP] = offset
        rows.append(row)
    return {
        "sysid_protocol": 1,
        "name": NAME,
        "created": "2026-09-05",
        "description": (
            "Simultaneous L2/L5 hip matched-midpoint reversal, relative to "
            "the measured segment-admission pose; four cycles at ±2 deg."
        ),
        "hz": HZ,
        "segments": [{
            "kind": "rel_traj",
            "label": "L2_L5_hip_matched_midpoint_reversal",
            "active": [L2_HIP, L5_HIP],
            "t_s": [index / HZ for index in range(900)],
            "q_deg": rows,
        }],
    }


def qualify(project_root: Path = PROTO_DIR) -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = build_protocol()
    errors = validate(protocol)
    materialized = materialize(protocol) if not errors else {"ticks": [], "hz": HZ}
    ticks = materialized["ticks"]
    stream = [
        {
            "tick": index,
            "t_s": index / HZ,
            "active": tick["active"],
            "offset_deg": [tick["cmd"][L2_HIP], tick["cmd"][L5_HIP]],
        }
        for index, tick in enumerate(ticks)
    ]
    values = [tick["cmd"][L2_HIP] for tick in ticks]
    max_step = max(
        (abs(right - left) for left, right in pairwise(values)),
        default=0.0,
    )
    source = project_root / "linux_control" / "sysid_runner.py"
    report = {
        "schema_version": 1,
        "engineering_job_id": ENGINEERING_JOB_ID,
        "source_analysis_job_id": SOURCE_ANALYSIS_JOB_ID,
        "source_experiment_id": SOURCE_EXPERIMENT_ID,
        "qualified": bool(
            not errors
            and len(ticks) == 900
            and materialized["hz"] == HZ
            and values[:50] == [0.0] * 50
            and values[-50:] == [0.0] * 50
            and max_step <= SLEW_DEG_PER_TICK + 1e-12
            and min(values, default=0.0) == -AMPLITUDE_DEG
            and max(values, default=0.0) == AMPLITUDE_DEG
        ),
        "protocol_name": NAME,
        "protocol_version": 1,
        "protocol_hash": protocol_hash(protocol),
        "canonical_protocol_sha256": _sha256_bytes(_canonical_json(protocol)),
        "canonical_command_stream_sha256": _sha256_bytes(_canonical_json(stream)),
        "trusted_deterministic_executor": "linux_control.sysid_runner.run_sysid_protocol",
        "trusted_executor_source_sha256": _sha256_bytes(source.read_bytes()),
        "runner_compatibility": {
            "passed": not errors and all(tick["mode"] == "rel" for tick in ticks),
            "validation_errors": errors,
            "relative_to_measured_segment_pose": True,
            "force_guard_required": True,
        },
        "timing_validation": {
            "passed": len(ticks) == 900 and materialized["hz"] == HZ,
            "sample_rate_hz": materialized["hz"],
            "sample_count": len(ticks),
            "duration_seconds": len(ticks) / HZ,
            "pre_baseline_seconds": 5,
            "post_baseline_seconds": 5,
            "cycles": 4,
        },
        "joint_limit_validation": {
            "passed": not errors and max_step <= SLEW_DEG_PER_TICK + 1e-12,
            "active_joints": {"L2_hip": L2_HIP, "L5_hip": L5_HIP},
            "minimum_offset_deg": min(values, default=0.0),
            "maximum_offset_deg": max(values, default=0.0),
            "maximum_slew_deg_per_s": round(max_step * HZ, 12),
        },
        "robot_contacted": False,
        "robot_motion": False,
        "inspection_clearance_granted": False,
    }
    return protocol, {**report, "command_stream": stream}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    protocol, report = qualify()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    protocol_path = args.out_dir / f"{NAME}.json"
    stream_path = args.out_dir / f"{NAME}.command_stream.json"
    report_path = args.out_dir / f"{NAME}.qualification.json"
    # Keep the saved bytes identical to the canonical bytes hashed above, so
    # the hardware lane can verify the file unchanged with an ordinary SHA-256.
    protocol_path.write_bytes(_canonical_json(protocol))
    stream_path.write_bytes(_canonical_json(report.pop("command_stream")))
    report["artifacts"] = {
        "protocol": protocol_path.name,
        "command_stream": stream_path.name,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(report_path), **report}, indent=2))
    return 0 if report["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
