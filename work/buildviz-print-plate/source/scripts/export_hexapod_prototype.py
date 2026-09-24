#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy"]
# ///
"""Export the weird_objects prototype hexapod into a BuildViz scene.

Run with uv (dependencies resolve from the inline metadata above):
    uv run scripts/export_hexapod_prototype.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np


BUILDVIZ_ROOT = Path(__file__).resolve().parents[1]
WEIRD_OBJECTS_ROOT = Path(
    os.environ.get("WEIRD_OBJECTS_ROOT", BUILDVIZ_ROOT.parent / "weird_objects"),
).resolve()
PROTOTYPE_DIR = WEIRD_OBJECTS_ROOT / "hexapod_walker" / "prototype"
PUBLIC_BUILD_DIR = BUILDVIZ_ROOT / "public" / "builds" / "hexapod-prototype"


def _hex_color(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(channel * 255))):02x}" for channel in rgb)


def _three_matrix(matrix: np.ndarray) -> list[float]:
    """Convert a row-major NumPy transform into Three.js column-major order."""
    return [float(value) for value in matrix.T.reshape(-1)]


def _copy_asset(source: Path, destination_name: str) -> str:
    destination = PUBLIC_BUILD_DIR / destination_name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return f"/builds/hexapod-prototype/{destination_name}"


def main() -> None:
    if not PROTOTYPE_DIR.exists():
        raise SystemExit(f"Could not find prototype directory: {PROTOTYPE_DIR}")

    sys.path.insert(0, str(PROTOTYPE_DIR))

    import inspect_build  # type: ignore
    import part_palette as palette  # type: ignore

    PUBLIC_BUILD_DIR.mkdir(parents=True, exist_ok=True)

    instances = inspect_build._build_assembly_instances()
    instances.extend(inspect_build._build_fastener_instances())

    stl_keys = {inspect_build._instance_stl_key(instance) for instance in instances}
    stl_cache = inspect_build._load_stl_cache(stl_keys)
    chassis_lift = inspect_build._compute_chassis_lift(instances, stl_cache)
    lift = inspect_build._trans(0, 0, chassis_lift)

    meshes: dict[tuple[str, str], dict[str, Any]] = {}
    manifest_instances: list[dict[str, Any]] = []
    chassis_centroids: list[np.ndarray] = []
    fastener_index = 0

    for index, instance in enumerate(instances):
        stl_dir, stl_name = inspect_build._instance_stl_key(instance)
        stl_path = Path(stl_dir) / stl_name
        mesh_key = (stl_dir, stl_name)
        mesh_id = f"{Path(stl_dir).name}:{Path(stl_name).stem}"

        if mesh_key not in meshes:
            asset_name = (
                f"fasteners/{stl_name}"
                if Path(stl_dir).name == "fasteners"
                else f"stl_prototype/{stl_name}"
            )
            meshes[mesh_key] = {
                "id": mesh_id,
                "name": stl_name,
                "url": _copy_asset(stl_path, asset_name),
            }

        world_transform = lift @ instance.transform
        mesh = inspect_build._apply_transform(stl_cache[mesh_key], world_transform)
        centroid = np.array(mesh.center, dtype=float)

        if instance.part_type in ("chassis_top", "chassis_bottom"):
            chassis_centroids.append(centroid)

        leg = None if instance.leg_index is None else f"L{instance.leg_index}"
        label = palette.instance_label(
            instance.part_type,
            instance.leg_index,
            instance.joint,
            fastener_role=instance.fastener_role,
        )
        role = palette.instance_role(
            instance.part_type,
            instance.leg_index,
            instance.joint,
            fastener_role=instance.fastener_role,
        )

        if palette.is_fastener(instance.part_type):
            fastener_index += 1
            instance_id = f"fastener-{fastener_index:03d}"
        else:
            suffix = "" if leg is None else f"-{leg}"
            joint = "" if instance.joint is None else f"-{instance.joint}"
            instance_id = f"{instance.part_type}{suffix}{joint}"

        manifest_instances.append(
            {
                "id": f"{index:03d}-{instance_id}",
                "meshId": mesh_id,
                "name": label,
                "partType": instance.part_type,
                "role": role,
                "leg": leg,
                "joint": instance.joint,
                "color": _hex_color(palette.PART_COLORS.get(instance.part_type, (0.8, 0.8, 0.8))),
                "transform": _three_matrix(world_transform),
                "centroid": [float(value) for value in centroid],
                "focusGroup": "chassis" if leg is None else leg,
            },
        )

    center = (
        np.mean(np.vstack(chassis_centroids), axis=0)
        if chassis_centroids
        else np.array([0.0, 0.0, 0.0])
    )

    manifest = {
        "name": "Prototype hexapod",
        "source": str(PROTOTYPE_DIR),
        "units": "mm",
        "center": [float(value) for value in center],
        "meshes": list(meshes.values()),
        "instances": manifest_instances,
    }

    manifest_path = PUBLIC_BUILD_DIR / "scene.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    design_spec_path = PROTOTYPE_DIR / "design_spec.yaml"
    if design_spec_path.exists():
        shutil.copy2(design_spec_path, PUBLIC_BUILD_DIR / "design_spec.yaml")
    print(
        f"Exported {len(manifest_instances)} instances, {len(meshes)} meshes -> "
        f"{manifest_path.relative_to(BUILDVIZ_ROOT)}",
    )


if __name__ == "__main__":
    main()
