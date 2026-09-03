#!/usr/bin/env python3
"""Create and validate joint-flex run manifests without controlling hardware."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import re
from typing import Any

import yaml


HERE = Path(__file__).resolve().parent
PROTOTYPE_ROOT = HERE.parents[2]
DEFAULT_OUTPUT_ROOT = PROTOTYPE_ROOT / "artifacts" / "joint_flex" / "hexapod-1"
TEMPLATE = HERE / "run-manifest-template.yaml"
RUN_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}-static-(hip|knee)-L[0-5]$")
REQUIRED_CONFIRMATIONS = (
    "chassis_rigidly_supported",
    "tested_leg_off_ground",
    "tested_joints_limp_or_power_off",
    "no_visible_crack_requires_stop",
    "safe_force_ceiling_selected",
    "no_fasteners_changed_since_baseline",
)


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def create_run(
    *,
    leg: str,
    joint: str,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    now: datetime | None = None,
) -> Path:
    """Create a new run directory and populated manifest, refusing overwrite."""
    if leg not in {f"L{i}" for i in range(6)}:
        raise ValueError("leg must be L0 through L5")
    if joint not in {"hip", "knee"}:
        raise ValueError("joint must be hip or knee")

    timestamp = now or datetime.now().astimezone()
    run_id = f"{timestamp.strftime('%Y%m%dT%H%M%S')}-static-{joint}-{leg}"
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    manifest = deepcopy(load_yaml(TEMPLATE))
    manifest["run_id"] = run_id
    manifest["started_at"] = timestamp.isoformat(timespec="seconds")
    manifest["target"]["leg"] = leg
    manifest["target"]["joint"] = joint
    (run_dir / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )
    return run_dir


def readiness_issues(manifest: dict[str, Any]) -> list[str]:
    """Return capture blockers; an empty result means Phase 0 may begin."""
    issues: list[str] = []

    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
        issues.append("run_id must match YYYYMMDDTHHMMSS-static-(hip|knee)-L0..L5")
    if not manifest.get("started_at"):
        issues.append("started_at is required")

    target = manifest.get("target", {})
    if target.get("leg") not in {f"L{i}" for i in range(6)}:
        issues.append("target.leg must be L0 through L5")
    if target.get("joint") not in {"hip", "knee"}:
        issues.append("target.joint must be hip or knee")

    confirmations = manifest.get("operator_confirmations") or {}
    for name in REQUIRED_CONFIRMATIONS:
        if confirmations.get(name) is not True:
            issues.append(f"operator_confirmations.{name} must be true")

    servo = manifest.get("servo_state") or {}
    power, torque = servo.get("power"), servo.get("torque")
    if power != "off" and torque not in {"off", "disabled", "limp"}:
        issues.append("servo must be power=off or torque=off/disabled/limp")

    cameras = manifest.get("cameras") or {}
    for view in ("face", "edge"):
        camera = cameras.get(view) or {}
        for field in ("device_model", "device_index", "resolution_px", "frame_rate_hz"):
            if camera.get(field) in (None, "", "unknown"):
                issues.append(f"cameras.{view}.{field} is required")

    markers = manifest.get("markers") or {}
    for field in (
        "world_reference", "R_fixed_reference", "S_perimeter_screw",
        "Y_adjacent_yoke", "F1_proximal_femur", "F2_distal_femur",
    ):
        if not markers.get(field):
            issues.append(f"markers.{field} is required")

    load = manifest.get("load") or {}
    for field in (
        "application_point_description", "lever_arm_mm",
        "force_measurement_device", "operator_max_force_N",
    ):
        if load.get(field) in (None, ""):
            issues.append(f"load.{field} is required")
    if not load.get("sweep_steps_N"):
        issues.append(
            "load.sweep_steps_N must contain at least one operator-selected step"
        )

    return issues


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    init = subparsers.add_parser("init", help="create a unique run manifest")
    init.add_argument("--leg", required=True, choices=[f"L{i}" for i in range(6)])
    init.add_argument("--joint", required=True, choices=("hip", "knee"))
    init.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    check = subparsers.add_parser(
        "check", help="check whether a manifest is capture-ready"
    )
    check.add_argument("manifest", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "init":
        print(create_run(leg=args.leg, joint=args.joint, output_root=args.output_root))
        return 0

    issues = readiness_issues(load_yaml(args.manifest))
    if issues:
        print("NOT READY")
        for issue in issues:
            print(f"- {issue}")
        return 2
    print("READY: manifest satisfies the Phase 0 capture prerequisites")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
