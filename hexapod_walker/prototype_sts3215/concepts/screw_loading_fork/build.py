"""Generate a two-screw loading fork and explanatory BuildViz scene.

Run: uv run --with build123d --with trimesh python build.py
"""
from pathlib import Path
import json
import math

from build123d import Box, Cylinder, Pos, Align, export_stl, export_step
import trimesh

HERE = Path(__file__).resolve().parent
OUT = HERE / "stl"
OUT.mkdir(exist_ok=True)
PITCH = 14.0  # opposite holes, DISC_HORN_BOLT_PCD in hexapod_prototype.py
THICKNESS = 0.8
SEAT = 3.3


def box(x, y, z, dx, dy, dz):
    return Pos(x, y, z) * Box(dx, dy, dz, align=(Align.CENTER, Align.CENTER, Align.MIN))


def cyl(x, y, z, radius, height):
    return Pos(x, y, z) * Cylinder(radius, height, align=(Align.CENTER, Align.CENTER, Align.MIN))


def fork(throat):
    # Flat underside prints on bed; thin spring fingers terminate at y=8.
    p = box(0, -2, 0, 23, 20, THICKNESS)
    p += box(0, -22, 0, 16, 24, 3.2)
    for x in (-PITCH / 2, PITCH / 2):
        p -= cyl(x, 0, -1, SEAT / 2, 5)
        p -= box(x, 5, -1, throat, 10, 5)
        # Wider last millimetre gives an entry lead-in.
        p -= box(x, 8, -1, 3.8, 2, 5)
    # Open centre channel clears the central fastener during withdrawal.
    p -= cyl(0, 0, -1, 3.5, 5)
    p -= box(0, 5, -1, 7, 10, 5)
    p -= cyl(0, -28, -1, 2, 6)
    return p


parts = {"fork_snug": fork(2.9), "fork_loose": fork(3.3)}
# Explicitly schematic interface, not replacement robot hardware.
plate = cyl(0, 0, -2.1, 11, 2.1)
for x, y in [(7, 0), (-7, 0), (0, 7), (0, -7), (0, 0)]:
    plate -= cyl(x, y, -3, 1.7, 4)
parts["reference_plate_DO_NOT_PRINT"] = plate
parts["reference_screw_DO_NOT_PRINT"] = cyl(0, 0, -5.2, 1.5, 6) + cyl(0, 0, 0.8, 2.75, 3)
report = {}
for name, solid in parts.items():
    assert solid.is_valid and len(solid.solids()) == 1, name
    export_stl(solid, OUT / f"{name}.stl", tolerance=0.03, angular_tolerance=0.1)
    if name.startswith("fork_"):
        export_step(solid, HERE / f"{name}.step")
    mesh = trimesh.load(OUT / f"{name}.stl", force="mesh")
    assert mesh.is_watertight and mesh.is_volume, name
    report[name] = {"watertight": True, "volume_mm3": float(mesh.volume), "bounds_mm": mesh.bounds.tolist()}

# Nominal loose fork releases without requiring elastic deformation.
loose = parts["fork_loose"]
screw = parts["reference_screw_DO_NOT_PRINT"]
for travel in (0, 0.5, 1, 2, 4, 6, 8, 10, 16):
    for x in (-7, 7):
        intersection = (Pos(0, -travel, 0) * loose) & (Pos(x, 0, 0) * screw)
        assert intersection.volume < 1e-6, (travel, intersection.volume)
report["release_check"] = "Loose fork clears both nominal M3 screw envelopes at 9 withdrawal positions; snug fork requires flex and is untested."

scene = {"name": "Two-screw loading fork — M3 / 14 mm — prototype v1", "units": "mm", "center": [0, -8, 0], "meshes": [], "instances": []}
for name in parts:
    scene["meshes"].append({"id": name, "name": name, "url": f"stl/{name}.stl"})


def instance(mesh, label, x=0, y=0, color="#36bad1", reference=False):
    scene["instances"].append({"id": label, "name": label, "meshId": mesh, "partType": mesh, "color": color, "cots": reference, "role": "reference" if reference else "printed", "transform": [1,0,0,0,0,1,0,0,0,0,1,0,x,y,0,1]})

instance("fork_snug", "1 — PRINT THIS: snug retaining fork", -40)
instance("fork_loose", "2 — Start both screws through fork", 0)
instance("fork_loose", "3 — Pull handle toward you, then tighten", 40, -16)
for station in (0, 40):
    instance("reference_plate_DO_NOT_PRINT", f"Schematic bracket face {station}", station, color="#9aa6b2", reference=True)
    for x in (-7, 7):
        instance("reference_screw_DO_NOT_PRINT", f"M3 screw {station} {x}", station+x, color="#e8ad49", reference=True)
(HERE / "scene.json").write_text(json.dumps(scene, indent=2) + "\n")
(HERE / "checks.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
