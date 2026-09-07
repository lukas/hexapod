"""Matched-dwell hysteresis metrics for radial-shear sysid traces.

The radial-shear protocols visit the same midpoint once while moving
outward and once while returning::

    base -> midpoint -> peak -> midpoint -> base

For each cycle, this module compares the mean encoder position over the two
midpoint dwells.  The first row of each command plateau is the endpoint of
the preceding move, so it is excluded exactly as it was in the accepted L5
analysis.  The reported condition metric is the mean absolute loop magnitude
over its cycles.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .trace import load


FEMUR_MM = 90.0
TIBIA_MM = 150.0
MIN_PLATEAU_SAMPLES = 5
COMMAND_MATCH_ATOL_DEG = 0.002


@dataclass(frozen=True)
class _Plateau:
    start: int
    stop: int
    command: np.ndarray


def _parse_leg(value: int | str) -> int:
    if isinstance(value, str):
        value = value.strip().lower()
        if value.startswith("l"):
            value = value[1:]
        try:
            value = int(value)
        except ValueError as exc:
            raise ValueError("leg must be L0..L5 or 0..5") from exc
    if value not in range(6):
        raise ValueError("leg must be L0..L5 or 0..5")
    return int(value)


def _infer_leg(cmd: np.ndarray) -> int:
    scores = []
    for leg in range(6):
        hip, knee = 3 * leg + 1, 3 * leg + 2
        score = float(np.ptp(cmd[:, hip]) + np.ptp(cmd[:, knee]))
        scores.append(score)
    moving = [leg for leg, score in enumerate(scores) if score > 0.1]
    if len(moving) != 1:
        detail = ", ".join(f"L{leg}={scores[leg]:.3f}" for leg in range(6))
        raise ValueError(
            "could not infer one active leg from hip/knee commands "
            f"({detail}); pass --leg L0..L5"
        )
    return moving[0]


def _fk(command: np.ndarray) -> tuple[float, float]:
    hip, knee = np.radians(command)
    return (
        float(FEMUR_MM * math.cos(hip) + TIBIA_MM * math.cos(knee)),
        float(FEMUR_MM * math.sin(hip) + TIBIA_MM * math.sin(knee)),
    )


def _near(a: np.ndarray, b: np.ndarray) -> bool:
    return bool(np.allclose(a, b, atol=COMMAND_MATCH_ATOL_DEG, rtol=0.0))


def _plateaus(command: np.ndarray) -> list[_Plateau]:
    """Return command plateaus, ignoring short rounded transition repeats."""
    out: list[_Plateau] = []
    start = 0
    for stop in range(1, len(command) + 1):
        if stop == len(command) or not np.array_equal(
            command[stop], command[start]
        ):
            if stop - start >= MIN_PLATEAU_SAMPLES:
                out.append(_Plateau(start, stop, command[start].copy()))
            start = stop
    return out


def _extract_cycles(cmd: np.ndarray, q: np.ndarray, leg: int) -> list[dict]:
    hip_joint, knee_joint = 3 * leg + 1, 3 * leg + 2
    plateaus = _plateaus(cmd[:, [hip_joint, knee_joint]])
    cycles: list[dict] = []

    # Five successive dwells form a complete cycle.  The outward-x check
    # rejects the equally symmetric peak->midpoint->base->midpoint->peak
    # window spanning two neighboring cycles.
    for index in range(len(plateaus) - 4):
        base, outbound, peak, inbound, returned = plateaus[index:index + 5]
        if not (_near(base.command, returned.command)
                and _near(outbound.command, inbound.command)):
            continue
        base_x, base_y = _fk(base.command)
        midpoint_x, midpoint_y = _fk(outbound.command)
        peak_x, peak_y = _fk(peak.command)
        if not (base_x + 0.05 < midpoint_x < peak_x - 0.05):
            continue

        # The arrival endpoint and the following hold share one command run.
        # Drop that endpoint, leaving exactly the requested dwell samples.
        outbound_slice = slice(outbound.start + 1, outbound.stop)
        inbound_slice = slice(inbound.start + 1, inbound.stop)
        outbound_count = outbound.stop - outbound.start - 1
        inbound_count = inbound.stop - inbound.start - 1
        if outbound_count != inbound_count:
            raise ValueError(
                "outbound/inbound midpoint dwell lengths do not match: "
                f"{outbound_count} versus {inbound_count} samples"
            )
        selected = q[
            np.r_[outbound.start + 1:outbound.stop,
                  inbound.start + 1:inbound.stop],
        ][:, [hip_joint, knee_joint]]
        if not np.isfinite(selected).all():
            raise ValueError("non-finite encoder value in a matched dwell")

        outbound_mean = np.mean(
            q[outbound_slice][:, [hip_joint, knee_joint]], axis=0
        )
        inbound_mean = np.mean(
            q[inbound_slice][:, [hip_joint, knee_joint]], axis=0
        )
        loop = np.abs(outbound_mean - inbound_mean)
        cycles.append({
            "amplitude_mm": round(peak_x - base_x, 2),
            "base_y_mm": round((base_y + midpoint_y + peak_y) / 3.0, 2),
            "dwell_samples_per_side": outbound_count,
            "outbound_rows": [outbound.start + 1, outbound.stop],
            "inbound_rows": [inbound.start + 1, inbound.stop],
            "outbound_mean_deg": {
                "hip": round(float(outbound_mean[0]), 6),
                "knee": round(float(outbound_mean[1]), 6),
            },
            "inbound_mean_deg": {
                "hip": round(float(inbound_mean[0]), 6),
                "knee": round(float(inbound_mean[1]), 6),
            },
            "hip_loop_deg": round(float(loop[0]), 6),
            "knee_loop_deg": round(float(loop[1]), 6),
        })
    if not cycles:
        raise ValueError(
            "no complete outward radial-shear cycles found; expected repeated "
            "base -> midpoint -> peak -> midpoint -> base command dwells"
        )
    return cycles


def _resolve_profile(requested: str, source_text: str, cycles: list[dict]) -> str:
    requested = requested.lower()
    if requested == "ground":
        requested = "planted"
    if requested not in {"auto", "air", "planted"}:
        raise ValueError("profile must be auto, air, planted, or ground")
    if requested != "auto":
        return requested

    source_text = source_text.lower()
    if "air_radial_shear" in source_text:
        return "air"
    if "ground_radial_shear" in source_text or "planted" in source_text:
        return "planted"
    return "air" if float(np.median(
        [cycle["base_y_mm"] for cycle in cycles]
    )) < 90.0 else "planted"


def analyze_hysteresis(
    csv_path: Path | str,
    *,
    leg: int | str | None = None,
    profile: str = "auto",
) -> dict:
    """Analyze one radial-shear dataset CSV.

    ``leg`` is inferred from the commanded hip/knee motion when omitted.
    ``profile`` is inferred from embedded protocol metadata (or commanded
    foot height) and may be forced to ``air`` or ``planted``.
    """
    trace = load(csv_path)
    cmd = np.asarray(trace["cmd"], dtype=float)
    q = np.asarray(trace["q"], dtype=float)
    if cmd.ndim != 2 or q.shape != cmd.shape or cmd.shape[1] < 18:
        raise ValueError("expected matching N x 18 command and encoder arrays")
    if not np.isfinite(cmd).all():
        raise ValueError("command stream contains non-finite values")

    resolved_leg = _infer_leg(cmd) if leg is None else _parse_leg(leg)
    cycles = _extract_cycles(cmd, q, resolved_leg)
    protocol = trace.get("protocol") or {}
    protocol_name = str(protocol.get("name", ""))
    resolved_profile = _resolve_profile(
        profile, f"{trace['name']} {protocol_name}", cycles
    )

    grouped: dict[tuple[float, float], list[dict]] = {}
    for cycle in cycles:
        key = (cycle["amplitude_mm"], cycle["base_y_mm"])
        grouped.setdefault(key, []).append(cycle)

    conditions = []
    for (amplitude_mm, base_y_mm), condition_cycles in grouped.items():
        conditions.append({
            "amplitude_mm": amplitude_mm,
            "base_y_mm": base_y_mm,
            "cycle_count": len(condition_cycles),
            "dwell_samples_per_side": sorted({
                cycle["dwell_samples_per_side"] for cycle in condition_cycles
            }),
            # Accepted convention: absolute loop per cycle, then mean cycles.
            "hip_loop_deg": round(float(np.mean([
                cycle["hip_loop_deg"] for cycle in condition_cycles
            ])), 3),
            "knee_loop_deg": round(float(np.mean([
                cycle["knee_loop_deg"] for cycle in condition_cycles
            ])), 3),
            "cycles": condition_cycles,
        })

    return {
        "source_csv": str(Path(csv_path)),
        "protocol": protocol_name or None,
        "profile": resolved_profile,
        "leg": resolved_leg,
        "leg_name": f"L{resolved_leg}",
        "hip_joint": 3 * resolved_leg + 1,
        "knee_joint": 3 * resolved_leg + 2,
        "method": "matched_midpoint_dwells_excluding_arrival_endpoint_v1",
        "cycle_count": len(cycles),
        "conditions": conditions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute matched-dwell radial-shear hysteresis metrics."
    )
    parser.add_argument("csv", type=Path, help="sysid dataset CSV")
    parser.add_argument("--leg", help="active leg (L0..L5 or 0..5); default: infer")
    parser.add_argument(
        "--profile",
        choices=("auto", "air", "planted", "ground"),
        default="auto",
    )
    args = parser.parse_args()
    try:
        result = analyze_hysteresis(args.csv, leg=args.leg, profile=args.profile)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
