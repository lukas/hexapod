"""One immutable v38 metal-clamp femur and matching cap, for an X1C.

Run with uv run python <this file> [--material PETG|PLA]. No printer connection.
Uses the installed Bambu Studio profiles and CLI, not account/device settings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.request
import uuid
import zipfile
from xml.etree import ElementTree as ET

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
BAMBU = Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")
PROFILES = BAMBU.parents[1] / "Resources/profiles/BBL"
CACHE = Path.home() / ".buildviz/cache/_assets"
HOST = "https://buildviz.cwd1f0-new-cluster.coreweave.app"
SOURCES = (
    ("femur_ovh_body", "8c43f3d8a2daa5fc43c9c1b25b19b31632e3fd235784817b74f0da2ea2e5efed", 90),
    ("knee_clamp_cap_ovh", "38eeb58892996beb5bae3d80f1e486d3634e38c820efdaa954062b4020ab07fe", -90),
)
FRONT_HOLES = [(7, 17.15), (0, 24.15), (-7, 17.15), (0, 10.15),
               (0, -1.35), (0, 35.65)]


def resolve_profile(path: Path, stack=()) -> dict:
    """Resolve both inheritance AND included machine G-code templates."""
    assert path not in stack, f"Cyclic profile: {path}"
    data = json.loads(path.read_text())
    merged = {}
    if data.get("inherits"):
        merged.update(resolve_profile(path.parent / (data["inherits"] + ".json"), (*stack, path)))
    for name in data.get("include", []):
        merged.update(resolve_profile(path.parent / (name + ".json"), (*stack, path)))
    merged.update(data)
    merged.pop("inherits", None)
    merged.pop("include", None)
    return merged


def set_values(profile, updates):
    for key, value in updates.items():
        old = profile.get(key)
        profile[key] = [value] * len(old) if isinstance(old, list) else value


def source_mesh(name, sha, temp):
    path = CACHE / (sha + ".stl")
    if not path.is_file():
        path = temp / (sha + ".stl")
        urllib.request.urlretrieve(f"{HOST}/builds/_assets/{sha}.stl", path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == sha, name
    mesh = trimesh.load_mesh(path)
    assert mesh.is_volume and len(mesh.split()) == 1, name
    return mesh


def make_geometry(temp):
    meshes, records = [], []
    cursor = 0.0
    for name, sha, angle in SOURCES:
        raw = source_mesh(name, sha, temp)
        mesh = raw.copy()
        rotation = trimesh.transformations.rotation_matrix(math.radians(angle), [1, 0, 0])
        mesh.apply_transform(rotation)
        offset = -mesh.bounds[0]
        offset[0] += cursor
        offset[1] -= mesh.extents[1] / 2
        mesh.apply_translation(offset)
        cursor = mesh.bounds[1, 0] + 12
        assert np.isclose(mesh.volume, raw.volume)
        ground = np.all(np.abs(mesh.triangles[:, :, 2]) < 1e-4, axis=1)
        records.append({"part": name, "quantity": 1, "source_sha256": sha,
                        "source_url": f"{HOST}/builds/_assets/{sha}.stl",
                        "rotation_x_deg": angle, "volume_mm3": float(mesh.volume),
                        "bed_contact_mm2": float(mesh.area_faces[ground].sum()),
                        "source_to_plate": rotation.tolist()})
        meshes.append(mesh)
        records[-1]["source_to_plate"][0][3] = float(offset[0])
        records[-1]["source_to_plate"][1][3] = float(offset[1])
        records[-1]["source_to_plate"][2][3] = float(offset[2])
    bounds = trimesh.util.concatenate(meshes).bounds
    center = np.r_[128 - bounds.mean(axis=0)[:2], 0.0]
    scene = trimesh.Scene()
    for mesh, record in zip(meshes, records):
        mesh.apply_translation(center)
        transform = np.array(record["source_to_plate"])
        transform[:3, 3] += center
        record["source_to_plate"] = transform.tolist()
        record["bounds_mm"] = mesh.bounds.tolist()
        assert np.isclose(mesh.bounds[0, 2], 0)
        assert (mesh.bounds[0, :2] > 30).all() and (mesh.bounds[1, :2] < 240).all()
        assert record["bed_contact_mm2"] > 2000
        scene.add_geometry(mesh, geom_name=record["part"], node_name=record["part"])
    path = HERE / "metal_femur_and_cap_v38_geometry.3mf"
    scene.export(path)
    loaded = trimesh.load(path, force="scene")
    assert len(loaded.geometry) == 2 and np.allclose(loaded.bounds, scene.bounds)
    return path, records


def profiles(material):
    machine = resolve_profile(PROFILES / "machine/Bambu Lab X1 Carbon 0.4 nozzle.json")
    process = resolve_profile(PROFILES / "process/0.20mm Standard @BBL X1C.json")
    filament = resolve_profile(PROFILES / f"filament/Generic {material}.json")
    assert "G28" in machine["machine_start_gcode"]
    assert machine["printer_model"] == "Bambu Lab X1 Carbon"
    process.update(name=f"Metal femur + cap - X1C {material} 0.20mm",
                   print_settings_id=f"Metal femur + cap - X1C {material} 0.20mm")
    set_values(process, {
        "curr_bed_type": "Textured PEI Plate", "layer_height": "0.2",
        "initial_layer_print_height": "0.2", "wall_loops": "6",
        "sparse_infill_density": "40%", "sparse_infill_pattern": "gyroid",
        "top_shell_layers": "6", "bottom_shell_layers": "6",
        "top_shell_thickness": "1.2", "bottom_shell_thickness": "1.2",
        "initial_layer_speed": "25", "initial_layer_infill_speed": "40",
        "outer_wall_speed": "60", "inner_wall_speed": "120",
        "top_surface_speed": "50", "sparse_infill_speed": "120",
        "internal_solid_infill_speed": "100", "bridge_speed": "25",
        "default_acceleration": "4000", "outer_wall_acceleration": "1500",
        "enable_support": "1", "support_type": "normal(auto)",
        "support_style": "snug", "support_on_build_plate_only": "0",
        "support_critical_regions_only": "1", "support_remove_small_overhang": "1",
        "support_base_pattern_spacing": "4", "support_interface_top_layers": "2",
        "support_interface_spacing": "0.5", "support_object_xy_distance": "0.5",
        "support_top_z_distance": "0.24", "support_bottom_z_distance": "0.24",
        "bridge_no_support": "1", "brim_type": "no_brim", "skirt_loops": "0",
        "enable_prime_tower": "0", "print_sequence": "by layer",
        "enable_arc_fitting": "0",
    })
    set_values(filament, {"additional_cooling_fan_speed": "0"})
    return machine, process, filament


def run_cli(args, log):
    result = subprocess.run([str(BAMBU), "--debug", "2", *args],
                            capture_output=True, text=True, timeout=300)
    log.write_text(result.stdout + "\n" + result.stderr)
    assert result.returncode == 0, f"Bambu failed: see {log}"


def complete_plate_metadata(path, parts):
    """Add plate membership and keep small fastener bores free of supports."""
    with zipfile.ZipFile(path) as archive:
        entries = {n: archive.read(n) for n in archive.namelist()}
    model = ET.fromstring(entries["3D/3dmodel.model"])
    core = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    production = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"
    ET.register_namespace("", core)
    ET.register_namespace("p", production)
    tag = lambda name: "{" + core + "}" + name
    ns = {"m": core}
    items = model.findall("m:build/m:item", ns)
    config = ET.fromstring(entries["Metadata/model_settings.config"])
    plate = config.find("plate")
    assert plate is not None and len(items) == 2
    assert not plate.findall("model_instance")
    for index, item in enumerate(items):
        instance = ET.SubElement(plate, "model_instance")
        for key, value in (("object_id", item.get("objectid")),
                           ("instance_id", "0"), ("identify_id", str(2 * (index + 1)))):
            ET.SubElement(instance, "metadata", key=key, value=value)
    plate.find("metadata[@key='plater_name']").set("value", "v38 - one femur + cap")
    named = {obj.find("metadata[@key='name']").get("value"): obj
             for obj in config.findall("object")}
    # The cap prints face down. Its small counterbore ledges bridge without
    # packing support into the two vertical screw passages.
    ET.SubElement(named["knee_clamp_cap_ovh"], "metadata", key="enable_support", value="0")
    body_config = named["femur_ovh_body"]
    body_id = body_config.get("id")
    body_item = next(item for item in items if item.get("objectid") == body_id)
    values = np.array([float(v) for v in body_item.get("transform").split()])
    instance = np.eye(4)
    instance[:3, :3] = values[:9].reshape(3, 3).T
    instance[:3, 3] = values[9:]
    body_transform = np.array(parts[0]["source_to_plate"])
    source_to_component = np.linalg.inv(instance) @ body_transform
    components = model.find(f"m:resources/m:object[@id='{body_id}']/m:components", ns)
    blocker_model = ET.Element(tag("model"), unit="millimeter")
    resources = ET.SubElement(blocker_model, tag("resources"))
    for ident, (y, z) in enumerate(FRONT_HOLES, 100):
        # Bores are 2.5 mm diameter and 7 mm deep. Add 0.55 mm radial room
        # for the support extrusion envelope; no printable material changes.
        mesh = trimesh.creation.cylinder(radius=1.8, height=9, sections=32)
        mesh.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
        mesh.apply_translation([67, y, z])
        mesh.apply_transform(source_to_component)
        obj = ET.SubElement(resources, tag("object"), id=str(ident), type="model")
        xml_mesh = ET.SubElement(obj, tag("mesh"))
        vertices = ET.SubElement(xml_mesh, tag("vertices"))
        faces = ET.SubElement(xml_mesh, tag("triangles"))
        for vertex in mesh.vertices:
            ET.SubElement(vertices, tag("vertex"), **dict(zip("xyz", map(str, vertex))))
        for face in mesh.faces:
            ET.SubElement(faces, tag("triangle"), **dict(zip(("v1", "v2", "v3"), map(str, face))))
        ET.SubElement(components, tag("component"), {
            "{" + production + "}path": "/3D/Objects/blockers.model",
            "objectid": str(ident), "{" + production + "}UUID": str(uuid.uuid4()),
            "transform": "1 0 0 0 1 0 0 0 1 0 0 0"})
        part = ET.SubElement(body_config, "part", id=str(ident), subtype="support_blocker", uuid=str(uuid.uuid4()))
        ET.SubElement(part, "metadata", key="name", value="Keep self-tapping pilot clear")
        ET.SubElement(part, "metadata", key="matrix", value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1")
    entries["3D/Objects/blockers.model"] = ET.tostring(blocker_model, encoding="utf-8", xml_declaration=True)
    entries["3D/3dmodel.model"] = ET.tostring(model, encoding="utf-8", xml_declaration=True)
    rels = ET.fromstring(entries["3D/_rels/3dmodel.model.rels"])
    ET.SubElement(rels, "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship",
                  Id="support_blockers", Target="/3D/Objects/blockers.model",
                  Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel")
    # Bambu's relationship reader expects unprefixed Relationship tags.
    ET.register_namespace("", "http://schemas.openxmlformats.org/package/2006/relationships")
    entries["3D/_rels/3dmodel.model.rels"] = ET.tostring(rels, encoding="utf-8", xml_declaration=True)
    ET.register_namespace("", core)
    entries["Metadata/model_settings.config"] = ET.tostring(config, encoding="utf-8", xml_declaration=True)
    settings = json.loads(entries["Metadata/project_settings.config"])
    settings["extruder_nozzle_stats"] = ["Standard#1"]
    entries["Metadata/project_settings.config"] = json.dumps(settings, indent=2).encode()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)


def verify_project(path, parts, material):
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        settings = json.loads(archive.read("Metadata/project_settings.config"))
        model = ET.fromstring(archive.read("Metadata/model_settings.config"))
        objects = model.findall("object")
        plates = model.findall("plate")
        assert len(objects) == 2 and len(plates) == 1
        assert len(plates[0].findall("model_instance")) == 2
        assert len(model.findall("object/part[@subtype='normal_part']")) == 2
        assert len(model.findall("object/part[@subtype='support_blocker']")) == 6
        assert settings["printer_model"] == "Bambu Lab X1 Carbon"
        assert settings["nozzle_diameter"] == ["0.4"]
        assert settings["filament_type"] == [material]
        assert settings["wall_loops"] == "6"
        assert settings["sparse_infill_density"] == "40%"
        assert settings["enable_prime_tower"] == "0"
        assert "Metadata/plate_1.gcode" in archive.namelist()
        gcode = archive.read("Metadata/plate_1.gcode").decode()
        stats = [line for line in gcode.splitlines()
                 if line.startswith(("; total estimated", "; total filament", "; model printing"))]
        info = ET.fromstring(archive.read("Metadata/slice_info.config"))
        warnings = [ET.tostring(n, encoding="unicode") for n in info.iter()
                    if n.tag in {"warning", "warnings"}]
        # Read individual mesh objects explicitly. Trimesh's generic importer
        # merges all objects in a referenced .model file and would mistake the
        # six nonprinting support blockers for copies of the whole femur.
        meshes = printable_meshes(archive, model)
    assert len(meshes) == 2
    for expected in parts:
        matches = [m for m in meshes if np.isclose(m.volume, expected["volume_mm3"], rtol=1e-5)]
        assert len(matches) == 1
        assert np.allclose(matches[0].bounds, expected["bounds_mm"], atol=0.002)
        assert matches[0].is_watertight
    paths = verify_toolpaths(gcode, parts)
    result = json.loads((HERE / "result.json").read_text())
    assert result["return_code"] == 0 and len(result["sliced_plates"]) == 1
    assert not result["sliced_plates"][0]["warning_message"]
    return {"printer": settings["printer_model"], "nozzle_mm": 0.4,
            "material": material, "bed": settings["curr_bed_type"],
            "slice_success": True, "slicer_warnings": warnings, "stats": stats,
            "toolpath_checks": paths}


def printable_meshes(archive, config):
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    prod = "{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}"
    root = ET.fromstring(archive.read("3D/3dmodel.model"))
    meshes = []

    def matrix(value):
        result = np.eye(4)
        values = np.array([float(v) for v in value.split()])
        result[:3, :3] = values[:9].reshape(3, 3).T
        result[:3, 3] = values[9:]
        return result

    for item in root.findall("m:build/m:item", ns):
        ident = item.get("objectid")
        object_config = config.find(f"object[@id='{ident}']")
        normal_ids = {part.get("id") for part in object_config.findall("part[@subtype='normal_part']")}
        obj = root.find(f"m:resources/m:object[@id='{ident}']", ns)
        for component in obj.findall("m:components/m:component", ns):
            cid = component.get("objectid")
            if cid not in normal_ids:
                continue
            sub = ET.fromstring(archive.read(component.get(prod + "path").lstrip("/")))
            mesh = sub.find(f"m:resources/m:object[@id='{cid}']/m:mesh", ns)
            vertices = [[float(v.get(k)) for k in "xyz"] for v in mesh.findall("m:vertices/m:vertex", ns)]
            faces = [[int(f.get(k)) for k in ("v1", "v2", "v3")] for f in mesh.findall("m:triangles/m:triangle", ns)]
            result = trimesh.Trimesh(vertices=vertices, faces=faces)
            result.apply_transform(matrix(item.get("transform")) @ matrix(component.get("transform")))
            meshes.append(result)
    return meshes


def verify_toolpaths(gcode, parts):
    """Check the support extrusion envelope against ten functional bores."""
    pos = np.zeros(3)
    feature, segments = "", []
    for line in gcode.splitlines():
        if line.startswith("; FEATURE:"):
            feature = line.split(":", 1)[1].strip()
        if not re.match(r"^G[0123] ", line):
            continue
        values = {k: float(v) for k, v in re.findall(r"([XYZE])(-?\d*\.?\d+)", line.split(";")[0])}
        old = pos.copy()
        for i, key in enumerate("XYZ"):
            if key in values:
                pos[i] = values[key]
        if feature.startswith("Support") and values.get("E", 0) > 0 and ("X" in values or "Y" in values):
            assert line.startswith("G1 "), "Arc support requires arc-aware checking"
            segments.append((old, pos.copy()))
    a = np.array([segment[0] for segment in segments])
    b = np.array([segment[1] for segment in segments])
    assert len(a) > 0  # selective supports remain on the femur's larger overhangs
    checked = 0
    for record in parts:
        transform = np.array(record["source_to_plate"])
        if record["part"] == "femur_ovh_body":
            holes = [("insert", [x, 10.2, 17.15], [x, 16.9, 17.15], 2.0) for x in (68.8, 123.2)]
            holes += [("pilot", [63.5, y, z], [70.5, y, z], 1.25) for y, z in FRONT_HOLES]
        else:
            holes = [("cap", [x, 5, 17.15], [x, 21.9, 17.15], 1.7) for x in (-27.2, 27.2)]
        for name, start, end, radius in holes:
            start = (transform @ np.r_[start, 1])[:3]
            end = (transform @ np.r_[end, 1])[:3]
            axis = np.argmax(np.abs(end - start))
            radial_axes = [i for i in range(3) if i != axis]
            lower, upper = sorted((start[axis], end[axis]))
            da = b[:, axis] - a[:, axis]
            parallel = np.abs(da) < 1e-10
            valid = (~parallel) | ((a[:, axis] >= lower) & (a[:, axis] <= upper))
            t0 = (lower - a[:, axis]) / np.where(parallel, 1, da)
            t1 = (upper - a[:, axis]) / np.where(parallel, 1, da)
            lo = np.where(parallel, 0, np.maximum(0, np.minimum(t0, t1)))
            hi = np.where(parallel, 1, np.minimum(1, np.maximum(t0, t1)))
            valid &= lo <= hi
            d = b[:, radial_axes] - a[:, radial_axes]
            denominator = (d * d).sum(axis=1)
            t = ((start[radial_axes] - a[:, radial_axes]) * d).sum(axis=1) / np.where(denominator > 1e-10, denominator, 1)
            t = np.maximum(lo, np.minimum(hi, t))
            near = a + t[:, None] * (b - a)
            distance = np.linalg.norm(near[:, radial_axes] - start[radial_axes], axis=1)
            assert not np.any(valid & (distance < radius + 0.21)), f"Support in {name} at {start}"
            checked += 1
    return {"support_segments": len(segments), "bores_checked": checked,
            "support_in_functional_bores": 0, "cap_support_disabled": True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--material", choices=["PETG", "PLA"], default="PETG")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="hexapod-x1c-femur-") as temp_name:
        temp = Path(temp_name)
        geometry, parts = make_geometry(temp)
        paths = []
        for name, data in zip(("machine", "process", "filament"), profiles(args.material)):
            path = HERE / f"{name}_{args.material}.json"
            path.write_text(json.dumps(data, indent=2) + "\n")
            paths.append(path)
        output = HERE / f"metal_femur_and_cap_v38_X1C_{args.material}.3mf"
        configured = temp / "configured.3mf"
        run_cli(["--outputdir", str(temp), "--arrange", "0", "--orient", "0",
                 "--load-settings", f"{paths[0]};{paths[1]}",
                 "--load-filaments", str(paths[2]),
                 "--export-3mf", configured.name, str(geometry)], HERE / "configure.log")
        complete_plate_metadata(configured, parts)
        run_cli(["--outputdir", str(HERE), "--arrange", "0", "--orient", "0",
                 "--slice", "0", "--export-3mf", output.name, str(configured)], HERE / "slice.log")
        report = verify_project(output, parts, args.material)
        shutil.copyfile(HERE / "result.json", HERE / "slice_result.json")
        run_cli(["--outputdir", str(temp), "--export-png", "1", "--camera-view", "0",
                 str(output)], HERE / "render.log")
        shutil.copyfile(temp / "plate_1_0.png", HERE / "plate_preview.png")
        report.update(source_build="prototype_sts3215/premade-chorn-56", source_version="v38",
                      geometry_changed=False, parts=parts, printer_contacted=False,
                      physical_fit_tested=False, output=output.name)
        (HERE / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
