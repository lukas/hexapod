#!/usr/bin/env python3
"""Verify the knee-yoke flag geometry against the production yoke."""

from __future__ import annotations

import json
import math
import sys
import zipfile
from pathlib import Path

import cv2
import numpy as np
import trimesh


HERE = Path(__file__).resolve().parent
PROTO_DIR = HERE.parent
for import_dir in (PROTO_DIR, HERE):
    if str(import_dir) not in sys.path:
        sys.path.insert(0, str(import_dir))

import hexapod_prototype as hp  # noqa: E402
import make_knee_yoke_apriltag_flag as flag  # noqa: E402


def rotate_about_output(mesh: trimesh.Trimesh, angle_deg: float) -> trimesh.Trimesh:
    result = mesh.copy()
    output = np.array([hp.SERVO_OUTPUT_X, 0.0, 0.0])
    result.apply_translation(-output)
    result.apply_transform(
        trimesh.transformations.rotation_matrix(math.radians(angle_deg), [0, 0, 1])
    )
    result.apply_translation(output)
    return result


def overlap_volume(first: trimesh.Trimesh, second: trimesh.Trimesh) -> float:
    if not np.all(first.bounds[1] >= second.bounds[0]) or not np.all(
        second.bounds[1] >= first.bounds[0]
    ):
        return 0.0
    intersection = trimesh.boolean.intersection(
        [first, second], engine="manifold", check_volume=False
    )
    if intersection is None or not len(intersection.faces):
        return 0.0
    return abs(float(intersection.volume))


def main() -> None:
    holder, dimensions = flag.build_holder(
        tag_id=flag.DEFAULT_TAG_ID,
        head_diameter=flag.DEFAULT_HEAD_D,
        head_height=flag.DEFAULT_HEAD_H,
        throat_clearance=flag.DEFAULT_THROAT_CLEARANCE,
    )
    installed = flag.installed_mesh(holder, dimensions["total_height_mm"])
    yoke = hp.make_tibia_knee_yoke()
    fixed = hp._femur_knee_fixed_solid()

    # The installed holder intentionally touches only the four modeled screw
    # heads.  It must remain entirely outboard of the yoke's driven face.
    yoke_overlap = overlap_volume(installed, yoke)
    outboard_gap = float(installed.bounds[0][2] - yoke.bounds[1][2])

    sweep: list[dict[str, float]] = []
    max_fixed_overlap = 0.0
    for angle in np.linspace(-25.0, 85.0, 111):
        posed = rotate_about_output(installed, float(angle))
        overlap = overlap_volume(posed, fixed)
        max_fixed_overlap = max(max_fixed_overlap, overlap)
        sweep.append({"knee_deg": round(float(angle), 3), "fixed_overlap_mm3": overlap})

    centres = np.asarray(flag.bolt_centres_about_output())
    radii = np.linalg.norm(centres, axis=1)

    preview_path = HERE / "out" / "preview.png"
    decoded_ids: list[int] = []
    if preview_path.is_file():
        preview = cv2.imread(str(preview_path), cv2.IMREAD_GRAYSCALE)
        detector = cv2.aruco.ArucoDetector(
            cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11),
            cv2.aruco.DetectorParameters(),
        )
        _corners, ids, _rejected = detector.detectMarkers(preview)
        if ids is not None:
            decoded_ids = [int(value) for value in ids.flatten()]

    bambu_path = HERE / "out" / "tag36h11_16_knee_yoke_snap_flag_BambuStudio.3mf"
    bambu_extruders: list[str] = []
    if bambu_path.is_file():
        with zipfile.ZipFile(bambu_path) as project:
            settings = project.read("Metadata/model_settings.config").decode("utf-8")
        bambu_extruders = sorted(
            {
                part.split('value="', 1)[1].split('"', 1)[0]
                for part in settings.split('key="extruder"')[1:]
            }
        )

    report = {
        "pass": bool(
            holder.is_watertight
            and len(holder.split(only_watertight=False)) == 1
            and yoke_overlap < 0.01
            and outboard_gap >= -0.01
            and max_fixed_overlap < 0.01
            and np.max(np.abs(radii - hp.DISC_HORN_BOLT_PCD / 2.0)) < 1e-9
            and flag.DEFAULT_TAG_ID in decoded_ids
            and (not bambu_path.is_file() or bambu_extruders == ["1", "2"])
        ),
        "holder_watertight": bool(holder.is_watertight),
        "holder_components": len(holder.split(only_watertight=False)),
        "yoke_overlap_mm3": yoke_overlap,
        "outboard_gap_mm": outboard_gap,
        "max_fixed_side_overlap_mm3": max_fixed_overlap,
        "sweep_knee_deg": [-25.0, 85.0],
        "bolt_radii_mm": radii.tolist(),
        "expected_bolt_radius_mm": hp.DISC_HORN_BOLT_PCD / 2.0,
        "opencv_decoded_tag_ids": decoded_ids,
        "bambu_assigned_extruders": bambu_extruders,
        "dimensions": dimensions,
        "samples": sweep,
    }
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    (out / "fit_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "samples"}, indent=2))
    if not report["pass"]:
        raise SystemExit("knee-yoke AprilTag flag fit verification failed")


if __name__ == "__main__":
    main()
