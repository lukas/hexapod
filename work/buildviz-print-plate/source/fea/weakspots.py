#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["gmsh", "numpy", "trimesh", "scipy", "scikit-image", "fast-simplification"]
# ///
"""Find weak spots in a robot part: Gmsh tet mesh -> CalculiX linear static FEA
-> von Mises hotspots -> BuildViz visualization.

Pipeline position (see fea/loadcases_mujoco.py for the load-case side):
    MuJoCo (or static estimate)  ->  loadcase JSON  ->  THIS SCRIPT
    THIS SCRIPT: Gmsh meshes the STL/STEP part, CalculiX (ccx) solves linear
    static elasticity, and the results come back as
      1. a summary + top-K hotspot list (JSON + console),
      2. a BuildViz highlight URL that pins hotspot markers on the real build,
      3. optionally a stress-colored derived build (surface triangles binned
         by von Mises into colored sub-meshes) pushed to the hub.

Usage:
    uv run fea/weakspots.py part.stl --loadcase case.json [options]
    uv run fea/weakspots.py part.stl --inspect          # bbox + selector help

Loadcase JSON schema (coordinates in the part file's own frame, mm / N):
    {
      "name": "single-foot landing 3x bodyweight",
      "material": {"name": "PLA", "youngMPa": 3500, "poisson": 0.36, "yieldMPa": 50},
      "fixtures": [
        {"type": "sphere", "center": [x, y, z], "radiusMm": 6},
        {"type": "plane", "axis": "z", "side": "max", "depthMm": 2.5}
      ],
      "loads": [
        {"type": "force", "at": [x, y, z], "radiusMm": 5, "forceN": [0, 0, -90]}
      ]
    }
Fixtures clamp (all DOF) every mesh node inside the region; each load's force
is split evenly over the nodes inside its region. Units: mm + N -> MPa.

Requires the CalculiX solver on PATH (`brew install costerwi/calculix/calculix-ccx`
installs `ccx_2.23`; any `ccx*` on PATH is found automatically).
"""

from __future__ import annotations

import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

import numpy as np

DEFAULT_MATERIAL = {"name": "PLA", "youngMPa": 3500.0, "poisson": 0.36, "yieldMPa": 50.0}

# Blue -> cyan -> green -> yellow -> red stress ramp for the derived build.
STRESS_RAMP = ["#3b4cc0", "#5d8bd8", "#8fc3dd", "#d5d8c1", "#f2b669", "#ec7f42", "#d94a35", "#b40426"]


# ---------------------------------------------------------------------------
# Gmsh: STL/STEP -> quadratic tet mesh
# ---------------------------------------------------------------------------

def voxel_remesh(part_file: Path) -> Path:
    """Last-resort surface reconstruction: voxelize + marching cubes (+ light
    decimation). Loses ~1 voxel of sharpness but survives any triangle soup."""
    import trimesh

    mesh = trimesh.load(str(part_file), force="mesh")
    pitch = float(mesh.extents.max()) / 150
    voxels = mesh.voxelized(pitch).fill()
    remeshed = voxels.marching_cubes
    remeshed.apply_scale(pitch)
    remeshed.apply_translation(voxels.translation)
    if len(remeshed.faces) > 24000:
        try:
            decimated = remeshed.simplify_quadric_decimation(face_count=24000)
            decimated.fill_holes()
            # Only keep the decimation if it stayed watertight — gmsh's
            # boundary recovery chokes on cracked surfaces.
            if decimated.is_watertight:
                remeshed = decimated
        except Exception:
            pass
    out = Path(tempfile.mkstemp(suffix=".remeshed.stl")[1])
    remeshed.export(str(out))
    return out


def mesh_part(part_file: Path, element_mm: float | None, order: int, verbose: bool,
              strategy: str = "auto"):
    """strategy: "auto" tries feature classification (40deg then 60deg) and the
    raw STL triangulation; "remesh" forces the voxel-remesh fallback.

    Each geometry attempt runs in a FRESH gmsh session (a failed 3D generate
    leaves gmsh in a state where later meshes silently come out empty) and is
    tried with the target element size then unconstrained (a coarse size
    target can break boundary recovery on thin features)."""
    import gmsh

    ext = part_file.suffix.lower()
    if ext not in (".step", ".stp", ".stl"):
        raise SystemExit(f"Unsupported part file {part_file.name}; use .stl or .step/.stp")

    def load_geometry(attempt):
        if ext in (".step", ".stp"):
            gmsh.model.occ.importShapes(str(part_file))
            gmsh.model.occ.synchronize()
            return
        if attempt == "remesh":
            gmsh.merge(str(voxel_remesh(part_file)))
            gmsh.model.mesh.createTopology()
        elif attempt == "topology":
            # Mesh the volume directly on the existing STL triangulation
            # (survives non-manifold-ish topology, keeps sliver triangles).
            gmsh.merge(str(part_file))
            gmsh.model.mesh.createTopology()
        else:
            # Reconstruct a clean geometry from the triangle soup: classify
            # by feature angle, then reparametrize (best mesh quality).
            gmsh.merge(str(part_file))
            gmsh.model.mesh.classifySurfaces(math.radians(attempt), True, True, math.radians(180))
            gmsh.model.mesh.createGeometry()
        surfaces = [s[1] for s in gmsh.model.getEntities(2)]
        loop = gmsh.model.geo.addSurfaceLoop(surfaces)
        gmsh.model.geo.addVolume([loop])
        gmsh.model.geo.synchronize()

    attempts = ["remesh"] if strategy == "remesh" else [40, 60, "topology"]
    plan = [("step", True)] if ext in (".step", ".stp") else [(a, s) for a in attempts for s in (True, False)]
    last_error: Exception | None = None
    for attempt, use_size in plan:
        gmsh.initialize()
        gmsh.option.setNumber("General.Terminal", 1 if verbose else 0)
        gmsh.option.setNumber("Mesh.ElementOrder", order)
        # Straight mid-edge nodes + optimization passes: curved second-order
        # tets on STL-classified geometry otherwise produce the occasional
        # negative-Jacobian element that CalculiX refuses to solve.
        gmsh.option.setNumber("Mesh.SecondOrderLinear", 1)
        gmsh.option.setNumber("Mesh.Optimize", 1)
        gmsh.option.setNumber("Mesh.OptimizeNetgen", 1)
        try:
            load_geometry(attempt)
            bounds = gmsh.model.getBoundingBox(-1, -1)
            diag = math.dist(bounds[:3], bounds[3:])
            if use_size:
                size = element_mm if element_mm else max(diag / 40, 0.8)
                gmsh.option.setNumber("Mesh.MeshSizeMax", size)
                gmsh.option.setNumber("Mesh.MeshSizeMin", size / 4)
            gmsh.model.mesh.generate(3)

            node_ids, node_xyz, _ = gmsh.model.mesh.getNodes()
            coords = np.asarray(node_xyz, dtype=float).reshape(-1, 3)
            ids = np.asarray(node_ids, dtype=np.int64)

            elem_types, elem_tags, elem_nodes = gmsh.model.mesh.getElements(3)
            tets = None
            tet_type = None
            for etype, tags, nodes in zip(elem_types, elem_tags, elem_nodes):
                name, _, _, nodes_per, *_ = gmsh.model.mesh.getElementProperties(etype)
                if nodes_per in (4, 10):
                    tets = np.asarray(nodes, dtype=np.int64).reshape(-1, nodes_per)
                    tet_type = "C3D10" if nodes_per == 10 else "C3D4"
            if tets is None or len(tets) == 0:
                raise Exception("no tetrahedra generated")

            # Boundary triangles (corner nodes only) for the stress-colored view.
            tri_types, tri_tags, tri_nodes = gmsh.model.mesh.getElements(2)
            tris = np.zeros((0, 3), dtype=np.int64)
            for etype, tags, nodes in zip(tri_types, tri_tags, tri_nodes):
                name, _, _, nodes_per, *_ = gmsh.model.mesh.getElementProperties(etype)
                if nodes_per in (3, 6):
                    tris = np.asarray(nodes, dtype=np.int64).reshape(-1, nodes_per)[:, :3]
            return ids, coords, tets, tet_type, tris
        except Exception as error:  # gmsh raises bare Exception
            last_error = error
        finally:
            gmsh.finalize()
    raise SystemExit(
        f"Gmsh could not mesh {part_file.name}: {last_error} "
        "(is the mesh watertight? try --elem-mm)"
    )


# ---------------------------------------------------------------------------
# CalculiX job: compose .inp, run ccx, parse .frd
# ---------------------------------------------------------------------------

# Gmsh and Abaqus/CalculiX agree on tet10 ordering except the last two
# mid-edge nodes, which are swapped.
GMSH_TO_ABAQUS_TET10 = [0, 1, 2, 3, 4, 5, 6, 7, 9, 8]


def select_nodes(ids: np.ndarray, coords: np.ndarray, region: dict, bounds) -> np.ndarray:
    kind = region.get("type")
    if kind == "sphere":
        center = np.asarray(region["center"], dtype=float)
        radius = float(region["radiusMm"])
        mask = np.linalg.norm(coords - center, axis=1) <= radius
    elif kind == "plane":
        axis = {"x": 0, "y": 1, "z": 2}[region.get("axis", "z")]
        depth = float(region.get("depthMm", 2.0))
        if region.get("side", "min") == "max":
            mask = coords[:, axis] >= bounds[1][axis] - depth
        else:
            mask = coords[:, axis] <= bounds[0][axis] + depth
    elif kind == "box":
        lo = np.asarray(region["min"], dtype=float)
        hi = np.asarray(region["max"], dtype=float)
        mask = np.all((coords >= lo) & (coords <= hi), axis=1)
    else:
        raise SystemExit(f"Unknown region type {kind!r}; use sphere, plane, or box")
    picked = ids[mask]
    if picked.size == 0:
        raise SystemExit(f"Region selected no nodes: {json.dumps(region)} — check coordinates with --inspect")
    return picked


def write_inp(job: Path, ids, coords, tets, tet_type, fix_nodes, loads, material):
    lines: list[str] = ["*HEADING", "BuildViz weakspots linear static", "*NODE"]
    for node_id, (x, y, z) in zip(ids, coords):
        lines.append(f"{node_id}, {x:.6f}, {y:.6f}, {z:.6f}")
    lines.append(f"*ELEMENT, TYPE={tet_type}, ELSET=EALL")
    for index, tet in enumerate(tets, start=1):
        ordered = tet[GMSH_TO_ABAQUS_TET10] if tet_type == "C3D10" else tet
        lines.append(f"{index}, " + ", ".join(str(n) for n in ordered))
    lines.append("*NSET, NSET=FIX")
    for start in range(0, len(fix_nodes), 12):
        lines.append(", ".join(str(n) for n in fix_nodes[start:start + 12]))
    lines += [
        "*MATERIAL, NAME=MAT",
        "*ELASTIC",
        f"{material['youngMPa']}, {material['poisson']}",
        "*SOLID SECTION, ELSET=EALL, MATERIAL=MAT",
        "*STEP",
        "*STATIC",
        "*BOUNDARY",
        "FIX, 1, 3, 0.",
        "*CLOAD",
    ]
    for load_nodes, force in loads:
        per_node = np.asarray(force, dtype=float) / len(load_nodes)
        for node in load_nodes:
            for dof, component in enumerate(per_node, start=1):
                if component != 0:
                    lines.append(f"{node}, {dof}, {component:.6e}")
    lines += ["*NODE FILE", "U", "*EL FILE", "S", "*END STEP", ""]
    job.with_suffix(".inp").write_text("\n".join(lines))


def find_ccx() -> str:
    for name in ("ccx", "ccx_2.23", "ccx_2.22", "ccx_2.21"):
        found = shutil.which(name)
        if found:
            return found
    raise SystemExit(
        "CalculiX solver not found on PATH. Install it with:\n"
        "  brew install costerwi/calculix/calculix-ccx"
    )


def run_ccx(job: Path, verbose: bool):
    # Single-threaded by default: multithreaded ccx 2.23 showed run-to-run
    # result variation on identical inputs (likely an OMP race). Solves here
    # are seconds; override with BUILDVIZ_FEA_THREADS if you need speed.
    threads = os.environ.get("BUILDVIZ_FEA_THREADS", "1")
    env = dict(os.environ, OMP_NUM_THREADS=threads, CCX_NPROC_STIFFNESS=threads)
    result = subprocess.run(
        [find_ccx(), "-i", job.name],
        cwd=job.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if verbose:
        sys.stderr.write(result.stdout[-2000:] + result.stderr[-2000:])
    frd = job.with_suffix(".frd")
    if result.returncode != 0 or not frd.exists():
        tail = (result.stdout + result.stderr)[-1500:]
        raise SystemExit(f"CalculiX failed (exit {result.returncode}):\n{tail}")
    return frd


def parse_frd(frd: Path):
    """Return {node_id: (disp[3], stress[6])} from the CalculiX .frd output."""
    disp: dict[int, list[float]] = {}
    stress: dict[int, list[float]] = {}
    target = None
    values_per = 0
    for line in frd.read_text().splitlines():
        code = line[:5].strip()
        if code == "-4":
            parts = line.split()
            name = parts[1] if len(parts) > 1 else ""
            target = {"DISP": disp, "STRESS": stress}.get(name)
            values_per = 3 if name == "DISP" else 6
        elif code == "-3":
            target = None
        elif code == "-1" and target is not None:
            node = int(line[3:13])
            values = [float(line[13 + i * 12: 25 + i * 12]) for i in range(values_per)]
            target[node] = values
    return disp, stress


def von_mises(s: np.ndarray) -> np.ndarray:
    sxx, syy, szz, sxy, syz, szx = s.T
    return np.sqrt(
        0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
        + 3.0 * (sxy**2 + syz**2 + szx**2)
    )


# ---------------------------------------------------------------------------
# Results -> hotspots, highlight URL, stress-colored build
# ---------------------------------------------------------------------------

def hotspot_clusters(node_ids, coords_by_id, vm_by_id, top_k: int, radius: float):
    order = sorted(node_ids, key=lambda n: -vm_by_id[n])
    spots = []
    for node in order:
        pos = coords_by_id[node]
        if any(math.dist(pos, s["positionMm"]) < radius for s in spots):
            continue
        spots.append({"node": int(node), "positionMm": [round(v, 2) for v in pos], "vonMisesMPa": round(vm_by_id[node], 2)})
        if len(spots) >= top_k:
            break
    return spots


def highlight_url(hub: str, build_id: str, spots, yield_mpa: float) -> str:
    ramp = lambda sf: "#d94a35" if sf < 1.5 else ("#ec9b3b" if sf < 3 else "#3fb27f")  # noqa: E731
    points = [
        {
            "point": s["positionMm"],
            "color": ramp(yield_mpa / max(s["vonMisesMPa"], 1e-6)),
            "label": f"{s['vonMisesMPa']} MPa",
            "annotation": f"hotspot {i + 1}: {s['vonMisesMPa']} MPa · SF {round(yield_mpa / max(s['vonMisesMPa'], 1e-6), 1)}",
            "radiusMm": 3,
        }
        for i, s in enumerate(spots)
    ]
    project, _, build = build_id.partition("/")
    query = f"project={project}&build={build}" if build else f"build={build_id}"
    payload = urllib.parse.quote(json.dumps({"points": points}, separators=(",", ":")))
    return f"{hub}/?{query}&highlight={payload}"


def binary_stl(triangles: np.ndarray) -> bytes:
    """triangles: (n, 3, 3) float array -> binary STL bytes."""
    header = b"BuildViz FEA stress bin" + b" " * 57
    out = [header, struct.pack("<I", len(triangles))]
    for tri in triangles:
        u, v = tri[1] - tri[0], tri[2] - tri[0]
        n = np.cross(u, v)
        length = np.linalg.norm(n)
        if length > 0:
            n = n / length
        out.append(struct.pack("<3f", *n))
        for vertex in tri:
            out.append(struct.pack("<3f", *vertex))
        out.append(struct.pack("<H", 0))
    return b"".join(out)


def push_stress_build(build_id: str, part_name: str, case_name: str, tris, coords_by_id, vm_by_id,
                      yield_mpa, message, analysis_name: str | None = None):
    """Bin surface triangles by von Mises and push as a colored derived build,
    or (with analysis_name) as a named analysis page attached to build_id."""
    vm_max = max(vm_by_id.values())
    bins = len(STRESS_RAMP)
    tri_bins: list[list[np.ndarray]] = [[] for _ in range(bins)]
    for tri in tris:
        try:
            values = [vm_by_id[int(n)] for n in tri]
            pts = np.array([coords_by_id[int(n)] for n in tri])
        except KeyError:
            continue
        level = min(bins - 1, int(max(values) / vm_max * bins)) if vm_max > 0 else 0
        tri_bins[level].append(pts)

    with tempfile.TemporaryDirectory(prefix="buildviz-fea-") as tmp:
        tmp_path = Path(tmp)
        meshes, instances = [], []
        for level, bucket in enumerate(tri_bins):
            if not bucket:
                continue
            lo = vm_max * level / bins
            hi = vm_max * (level + 1) / bins
            slug = f"vm_{level:02d}"
            (tmp_path / f"{slug}.stl").write_bytes(binary_stl(np.array(bucket)))
            meshes.append({"id": f"stl:{slug}", "name": f"{lo:.1f}–{hi:.1f} MPa", "url": f"{slug}.stl"})
            center = np.array(bucket).reshape(-1, 3).mean(axis=0)
            instances.append({
                "id": slug,
                "meshId": f"stl:{slug}",
                "name": f"von Mises {lo:.1f}–{hi:.1f} MPa",
                "partType": slug,
                "role": f"stress bin {level + 1}/{bins}" + (" (above yield!)" if lo >= yield_mpa else ""),
                "color": STRESS_RAMP[level],
                "transform": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
                "centroid": [round(float(v), 2) for v in center],
            })
        all_pts = np.concatenate([np.array(b).reshape(-1, 3) for b in tri_bins if b])
        scene = {
            "name": f"{part_name} stress · {case_name}",
            "source": "buildviz fea/weakspots.py",
            "schemaVersion": 3,
            "units": "mm",
            "center": [round(float(v), 2) for v in (all_pts.min(axis=0) + all_pts.max(axis=0)) / 2],
            "meshes": meshes,
            "instances": instances,
        }
        scene_path = tmp_path / "scene.json"
        scene_path.write_text(json.dumps(scene))
        if analysis_name:
            # Attach as a named analysis PAGE on the real build instead of
            # creating a separate build (keeps the builds index clean).
            command = ["npx", "buildviz", "push-analysis", build_id, "--name", analysis_name,
                       "--scene", str(scene_path), "--assets-dir", str(tmp_path),
                       "--display-name", scene["name"], "-m", message]
        else:
            command = ["npx", "buildviz", "push", "--scene", str(scene_path), "--assets-dir", str(tmp_path),
                       "--upload-assets", "--build-id", build_id, "--name", scene["name"], "--bump", "-m", message]
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        sys.stdout.write(result.stdout)
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            print("(stress-view push failed; FEA results above are still valid)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Gmsh + CalculiX weak-spot finder for BuildViz parts")
    parser.add_argument("part", help="part mesh (.stl) or CAD (.step/.stp), mm units")
    parser.add_argument("--loadcase", help="loadcase JSON (see module docstring)")
    parser.add_argument("--inspect", action="store_true", help="print bbox + selector hints and exit")
    parser.add_argument("--elem-mm", type=float, help="target element size (default: bbox diag / 40)")
    parser.add_argument("--first-order", action="store_true", help="C3D4 instead of C3D10 (faster, less accurate)")
    parser.add_argument("--top-k", type=int, default=8, help="hotspot count (default 8)")
    parser.add_argument("--out", help="write full results JSON here")
    parser.add_argument("--build", help="BuildViz build id for the hotspot highlight URL (e.g. prototype_sts3215)")
    parser.add_argument("--hub", default="http://127.0.0.1:5183", help="hub base URL for links")
    parser.add_argument("--push-stress", metavar="BUILD_ID", help="push stress-colored derived build (e.g. fea/femur-stress)")
    parser.add_argument("--push-analysis", metavar="NAME",
                        help="attach the stress view as a named analysis page on --build instead of a separate build")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    part_file = Path(args.part).resolve()
    if not part_file.exists():
        raise SystemExit(f"No such file: {part_file}")

    ids, coords, tets, tet_type, tris = mesh_part(part_file, args.elem_mm, 1 if args.first_order else 2, args.verbose)
    bounds = (coords.min(axis=0), coords.max(axis=0))
    print(f"Meshed {part_file.name}: {len(ids)} nodes, {len(tets)} {tet_type} tets")
    print(f"bbox min {np.round(bounds[0], 1).tolist()} max {np.round(bounds[1], 1).tolist()} mm")

    if args.inspect or not args.loadcase:
        if not args.inspect:
            print("\nNo --loadcase given; stopping after mesh. Example loadcase JSON:")
        center = np.round((bounds[0] + bounds[1]) / 2, 1).tolist()
        example = {
            "name": "example: press down on top, part bolted at bottom",
            "fixtures": [{"type": "plane", "axis": "z", "side": "min", "depthMm": 2.0}],
            "loads": [{"type": "sphere-note: use sphere/plane/box", "at": [center[0], center[1], round(float(bounds[1][2]), 1)], "radiusMm": 5, "forceN": [0, 0, -50]}],
        }
        example["loads"][0]["type"] = "force"
        print(json.dumps(example, indent=2))
        return

    case = json.loads(Path(args.loadcase).read_text())
    material = {**DEFAULT_MATERIAL, **case.get("material", {})}
    fix_nodes = np.unique(np.concatenate([select_nodes(ids, coords, f, bounds) for f in case["fixtures"]]))
    loads = []
    for load in case["loads"]:
        region = {"type": "sphere", "center": load["at"], "radiusMm": load.get("radiusMm", 5)} if "at" in load else load["region"]
        load_nodes = select_nodes(ids, coords, region, bounds)
        loads.append((load_nodes, load["forceN"]))
        print(f"load {load['forceN']} N over {len(load_nodes)} node(s)")
    print(f"fixed {len(fix_nodes)} node(s) · material {material['name']} (E={material['youngMPa']} MPa, yield={material['yieldMPa']} MPa)")

    with tempfile.TemporaryDirectory(prefix="buildviz-ccx-") as tmp:
        job = Path(tmp) / "weakspot"
        write_inp(job, ids, coords, tets, tet_type, fix_nodes, loads, material)
        print("Running CalculiX ...")
        frd = run_ccx(job, args.verbose)
        disp, stress = parse_frd(frd)

    stress_ids = np.array(sorted(stress.keys()))
    vm = von_mises(np.array([stress[n] for n in stress_ids]))
    vm_by_id = dict(zip(stress_ids.tolist(), vm.tolist()))
    coords_by_id = {int(n): coords[i].tolist() for i, n in enumerate(ids)}
    disp_mag = {n: math.dist(d, [0, 0, 0]) for n, d in disp.items()}

    max_node = int(stress_ids[int(np.argmax(vm))])
    max_vm = float(vm.max())
    max_disp = max(disp_mag.values()) if disp_mag else 0.0
    safety = material["yieldMPa"] / max_vm if max_vm > 0 else float("inf")
    diag = math.dist(bounds[0], bounds[1])
    spots = hotspot_clusters(stress_ids.tolist(), coords_by_id, vm_by_id, args.top_k, radius=max(diag / 12, 4.0))

    print(f"\n=== {case.get('name', 'loadcase')} ===")
    print(f"max von Mises: {max_vm:.2f} MPa at {np.round(coords_by_id[max_node], 1).tolist()} mm")
    print(f"max deflection: {max_disp:.3f} mm")
    verdict = "FAILS (yield exceeded)" if safety < 1 else ("MARGINAL" if safety < 2 else "OK")
    print(f"safety factor vs yield ({material['yieldMPa']} MPa): {safety:.2f} -> {verdict}")
    print("\nhotspots:")
    for i, spot in enumerate(spots):
        sf = material["yieldMPa"] / max(spot["vonMisesMPa"], 1e-6)
        print(f"  {i + 1}. {spot['vonMisesMPa']:8.2f} MPa  SF {sf:5.1f}  at {spot['positionMm']}")

    if args.build:
        print("\nhotspot overlay (open in BuildViz):")
        print(highlight_url(args.hub.rstrip("/"), args.build, spots, material["yieldMPa"]))

    if args.push_analysis and not args.build:
        raise SystemExit("--push-analysis requires --build (the build to attach the page to)")
    if args.push_stress or args.push_analysis:
        print("\npushing stress view ...")
        push_stress_build(
            args.push_stress or args.build, part_file.stem, case.get("name", "loadcase"),
            tris, coords_by_id, vm_by_id, material["yieldMPa"],
            f"FEA {case.get('name', 'loadcase')}: max {max_vm:.1f} MPa, SF {safety:.2f}",
            analysis_name=args.push_analysis,
        )

    if args.out:
        Path(args.out).write_text(json.dumps({
            "part": part_file.name,
            "loadcase": case,
            "material": material,
            "mesh": {"nodes": len(ids), "tets": len(tets), "type": tet_type},
            "maxVonMisesMPa": round(max_vm, 3),
            "maxDeflectionMm": round(max_disp, 4),
            "safetyFactor": round(safety, 3),
            "verdict": verdict,
            "hotspots": spots,
        }, indent=2))
        print(f"\nresults JSON -> {args.out}")


if __name__ == "__main__":
    main()
