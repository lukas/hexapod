"""Six unchanged v38 yaw retainers on one Bambu X1C PETG plate.

Run with uv run python <this file>. Uses Bambu Studio locally, never a printer.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile
import zipfile
from xml.etree import ElementTree as ET

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
HELPER = HERE.parents[1] / "knee_cap_heatset_front_selftap/x1c_plate/make_plate.py"
spec = importlib.util.spec_from_file_location("x1c_plate_helpers", HELPER)
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
SHA = "8106497cf755929ebab489b1b264ceb62d155095871f86ca06026817d7001476"
COUNT = 6
CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"


def geometry(temp):
    raw = helpers.source_mesh("yaw_servo_retainer", SHA, temp)
    rotation = trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])
    oriented = raw.copy()
    oriented.apply_transform(rotation)
    # Three columns, two rows, with 12 mm between model bounding boxes.
    size = oriented.extents
    pitch = size[:2] + 12
    footprint = size[:2] * [3, 2] + [24, 12]
    origin = np.array([128, 128]) - footprint / 2
    records, scene = [], trimesh.Scene()
    for index in range(COUNT):
        mesh = oriented.copy()
        offset = -mesh.bounds[0]
        offset[:2] += origin + pitch * [index % 3, index // 3]
        mesh.apply_translation(offset)
        transform = rotation.copy()
        transform[:3, 3] = offset
        name = f"yaw_retainer_{index + 1}"
        ground = np.all(np.abs(mesh.triangles[:, :, 2]) < 1e-4, axis=1)
        contact = float(mesh.area_faces[ground].sum())
        assert mesh.is_volume and len(mesh.split()) == 1
        assert np.isclose(mesh.volume, raw.volume)
        assert contact > 990 and np.isclose(mesh.bounds[0, 2], 0)
        assert (mesh.bounds[0, :2] > 20).all()
        assert (mesh.bounds[1, :2] < 240).all()
        records.append({"name": name, "bounds_mm": mesh.bounds.tolist(),
                        "volume_mm3": float(mesh.volume), "bed_contact_mm2": contact,
                        "source_to_plate": transform.tolist()})
        scene.add_geometry(mesh, geom_name=name, node_name=name)
    path = HERE / "yaw_retainers_6x_geometry.3mf"
    scene.export(path)
    loaded = trimesh.load(path, force="scene")
    assert len(loaded.geometry) == COUNT and np.allclose(loaded.bounds, scene.bounds)
    return path, records


def plate_membership(path):
    """Bambu CLI's initial import omits membership; add all six objects."""
    with zipfile.ZipFile(path) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    root = ET.fromstring(entries["3D/3dmodel.model"])
    items = root.findall("m:build/m:item", {"m": CORE})
    config = ET.fromstring(entries["Metadata/model_settings.config"])
    plate = config.find("plate")
    assert plate is not None and len(items) == COUNT
    assert not plate.findall("model_instance")
    for index, item in enumerate(items):
        instance = ET.SubElement(plate, "model_instance")
        for key, value in (("object_id", item.get("objectid")), ("instance_id", "0"),
                           ("identify_id", str(2 * (index + 1)))):
            ET.SubElement(instance, "metadata", key=key, value=value)
    plate.find("metadata[@key='plater_name']").set("value", "Six yaw retainers - PETG")
    entries["Metadata/model_settings.config"] = ET.tostring(config, encoding="utf-8", xml_declaration=True)
    settings = json.loads(entries["Metadata/project_settings.config"])
    settings["extruder_nozzle_stats"] = ["Standard#1"]
    entries["Metadata/project_settings.config"] = json.dumps(settings, indent=2).encode()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)


def support_clearance(gcode, records):
    """Check actual support extrusion envelopes against all 48 screw bores."""
    pos = np.zeros(3)
    feature, segments = "", []
    for line in gcode.splitlines():
        if line.startswith("; FEATURE:"):
            feature = line.split(":", 1)[1].strip()
        if not re.match(r"^G[0123] ", line):
            continue
        values = {k: float(v) for k, v in re.findall(r"([XYZE])(-?\d*\.?\d+)", line.split(";")[0])}
        old = pos.copy()
        for index, key in enumerate("XYZ"):
            if key in values:
                pos[index] = values[key]
        if feature.startswith("Support") and values.get("E", 0) > 0 and ("X" in values or "Y" in values):
            assert line.startswith("G1 "), "Arc support needs arc-aware checking"
            segments.append((old, pos.copy()))
    a = np.array([segment[0] for segment in segments]).reshape(-1, 3)
    b = np.array([segment[1] for segment in segments]).reshape(-1, 3)
    # Exact source-mesh vertical bores: four chassis anchors with counterbores,
    # and four rear-case M2.5 clearance holes. Dimensions are not changed.
    bores = [(x, y, -9, -6, 1.7) for x in (-12.5, -29) for y in (-21, 21)]
    bores += [(x, y, -11, -9, 3) for x in (-12.5, -29) for y in (-21, 21)]
    bores += [(x, y, -30.55, -27.05, 1.35) for x in (-8.3, -32.8) for y in (-10.2, 10.2)]
    for record in records:
        transform = np.array(record["source_to_plate"])
        for x, y, z0, z1, radius in bores:
            start = (transform @ [x, y, z0, 1])[:3]
            end = (transform @ [x, y, z1, 1])[:3]
            lower, upper = sorted((start[2], end[2]))
            # Support extrusion segments are horizontal in this sliced plate.
            assert np.allclose(a[:, 2], b[:, 2])
            valid = (a[:, 2] >= lower) & (a[:, 2] <= upper)
            d = b[:, :2] - a[:, :2]
            denom = (d * d).sum(axis=1)
            t = ((start[:2] - a[:, :2]) * d).sum(axis=1) / np.where(denom > 1e-10, denom, 1)
            near = a[:, :2] + np.clip(t, 0, 1)[:, None] * d
            distance = np.linalg.norm(near - start[:2], axis=1)
            assert not np.any(valid & (distance < radius + .21)), f"Support in bore: {record['name']} {(x, y)}"
    return {"support_segments": len(segments), "screw_bores_checked": COUNT * 8,
            "bore_sections_checked": COUNT * len(bores), "support_in_screw_bores": 0}


def verify(path, records):
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        settings = json.loads(archive.read("Metadata/project_settings.config"))
        config = ET.fromstring(archive.read("Metadata/model_settings.config"))
        objects, plates = config.findall("object"), config.findall("plate")
        assert len(objects) == COUNT and len(plates) == 1
        instances = plates[0].findall("model_instance")
        assert len(instances) == COUNT
        assert {i.find("metadata[@key='object_id']").get("value") for i in instances} == {o.get("id") for o in objects}
        assert len(config.findall("object/part[@subtype='normal_part']")) == COUNT
        assert {o.find("metadata[@key='name']").get("value") for o in objects} == {r["name"] for r in records}
        assert settings["printer_model"] == "Bambu Lab X1 Carbon"
        assert settings["nozzle_diameter"] == ["0.4"]
        assert settings["filament_type"] == ["PETG"]
        assert settings["curr_bed_type"] == "Textured PEI Plate"
        assert settings["wall_loops"] == "6" and settings["sparse_infill_density"] == "40%"
        assert settings["print_sequence"] == "by layer"
        meshes = helpers.printable_meshes(archive, config)
        assert len(meshes) == COUNT
        for record in records:
            matches = [m for m in meshes if np.allclose(m.bounds, record["bounds_mm"], atol=.002)]
            assert len(matches) == 1
            assert matches[0].is_volume and len(matches[0].split()) == 1
            assert np.isclose(matches[0].volume, record["volume_mm3"], rtol=1e-5)
        gcode = archive.read("Metadata/plate_1.gcode").decode()
        stats = [line for line in gcode.splitlines()
                 if line.startswith(("; total estimated", "; total filament", "; model printing"))]
    result = json.loads((HERE / "result.json").read_text())
    assert result["return_code"] == 0 and len(result["sliced_plates"]) == 1
    assert not result["sliced_plates"][0]["warning_message"]
    return {"printer": settings["printer_model"], "nozzle_mm": .4, "material": "PETG",
            "bed": settings["curr_bed_type"], "plate_count": 1, "part_count": COUNT,
            "orientation": "Flange down; 180 degrees about source X", "spacing_mm": 12,
            "slice_success": True, "slicer_warnings": [], "stats": stats,
            "support_checks": support_clearance(gcode, records)}


def main():
    with tempfile.TemporaryDirectory(prefix="hexapod-six-yaw-retainers-") as temp_name:
        temp = Path(temp_name)
        source, records = geometry(temp)
        machine, process, filament = helpers.profiles("PETG")
        process.update(name="Six yaw retainers - X1C PETG 0.20mm",
                       print_settings_id="Six yaw retainers - X1C PETG 0.20mm")
        paths = []
        for name, data in zip(("machine", "process", "filament"), (machine, process, filament)):
            path = HERE / f"{name}_PETG.json"
            path.write_text(json.dumps(data, indent=2) + "\n")
            paths.append(path)
        configured = temp / "configured.3mf"
        output = HERE / "yaw_retainers_6x_X1C_PETG.3mf"
        helpers.run_cli(["--outputdir", str(temp), "--arrange", "0", "--orient", "0",
                         "--load-settings", f"{paths[0]};{paths[1]}", "--load-filaments", str(paths[2]),
                         "--export-3mf", configured.name, str(source)], HERE / "configure.log")
        plate_membership(configured)
        helpers.run_cli(["--outputdir", str(HERE), "--arrange", "0", "--orient", "0",
                         "--slice", "0", "--export-3mf", output.name, str(configured)], HERE / "slice.log")
        report = verify(output, records)
        shutil.copyfile(HERE / "result.json", HERE / "slice_result.json")
        helpers.run_cli(["--outputdir", str(temp), "--export-png", "1", "--camera-view", "0",
                         str(output)], HERE / "render.log")
        shutil.copyfile(temp / "plate_1_0.png", HERE / "plate_preview.png")
        report.update(source_build="prototype_sts3215/premade-chorn-56", source_version="v38",
                      source_sha256=SHA, source_url=f"{helpers.HOST}/builds/_assets/{SHA}.stl",
                      geometry_changed=False, parts=records, printer_contacted=False,
                      physical_fit_tested=False, output=output.name)
        (HERE / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({k: v for k, v in report.items() if k != "parts"}, indent=2), flush=True)


if __name__ == "__main__":
    main()
