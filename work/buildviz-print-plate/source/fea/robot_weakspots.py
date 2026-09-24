#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["gmsh", "numpy", "trimesh", "scipy", "scikit-image", "fast-simplification"]
# ///
"""Whole-robot weak-spot FEA: run fea/weakspots.py's pipeline over EVERY
printed structural part of a BuildViz build, with load cases derived
automatically from the assembly.

    uv run fea/robot_weakspots.py prototype_sts3215 [--impact-g 3] \
        [--push-analysis walking-stress] [--out robot_fea.json]

Per unique printed partType (bought parts — anything in
checksConfig.partMassesGrams — and fasteners are skipped):
  1. Gmsh meshes the part's STL, nodes transformed into WORLD frame.
  2. Contact interfaces with neighboring instances are detected by proximity
     (surface nodes within --contact-tol of a sampled neighbor surface),
     grouped per neighbor.
  3. Interfaces nearest the robot center are CLAMPED (inboard mount); the
     farthest interface carries a SUITE of load cases: single-foot landing
     (mass x g x impact-g vertical), walking traction (--walk-g vertical plus
     --friction horizontal, radial and lateral), and servo-stall bending
     (--servo-torque-nm over the part's lever arm, in the lift plane and the
     yaw-scrub plane). The report keeps the worst case per part; the stress
     view uses the per-node envelope over all cases. Linear analysis: the von
     Mises field is identical for a reversed load, so one direction per axis
     covers both signs.
  4. CalculiX solves; per-part safety factors and hotspots aggregate into a
     robot-wide report, one combined hotspot highlight URL, and (with
     --push-analysis <name>) a NAMED ANALYSIS PAGE attached to the analyzed
     build — printed parts stress-colored in place (replicated to all sibling
     instances), everything else gray context — instead of a separate build.

Assembly-derived load cases are heuristic: symmetric siblings share one
analysis, and every part sees the full single-foot force (conservative for
chassis parts). For a part-specific scenario write a loadcase JSON and use
fea/weakspots.py directly.

With --mujoco-report <json> (a probe_walk_loads.py report from the rl_move
sim; committed copies live in fea/reports/), the heuristic suite is replaced
by MEASURED walking/rising loads for every joint-classified part: per
joint-axis bending moment and servo torque over the part's lever arm, and
the transmitted joint / foot ground force. Walking impact events (stumble
catches) are already in the measured maxima; the 3g drop-landing screen only
runs in heuristic mode. --mujoco-stat picks max (worst tick) or p95. Note
the probe samples the control tick, so sub-tick impact spikes are
underreported — max is a lower bound on the true peak.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import weakspots as ws  # noqa: E402

FASTENER_RE = re.compile(r"screw|bolt|nut|washer|fastener|standoff|magnet", re.IGNORECASE)
CONTEXT_GRAY = "#8a8f96"

# Stress-bin edges as fractions of yield. NONLINEAR on purpose: printed parts
# under nominal loads mostly live below 20% of yield, so linear bins collapse
# the whole robot into one flat blue (looks like "no stress"). These edges give
# color resolution where the material actually lives while red still means
# at/over yield — unlike CAD tools that auto-scale the legend to the study max
# (which makes every plot a rainbow regardless of margin).
STRESS_BIN_FRACTIONS = [0.02, 0.05, 0.10, 0.20, 0.35, 0.60, 1.00]


# ---------------------------------------------------------------------------
# Scene + mesh loading
# ---------------------------------------------------------------------------

def fetch(hub: str, path: str) -> bytes:
    with urllib.request.urlopen(f"{hub}{path}", timeout=60) as response:
        return response.read()


def parse_stl(data: bytes) -> np.ndarray:
    """Return triangle soup (n, 3, 3) from binary or ASCII STL bytes."""
    if len(data) >= 84:
        (count,) = np.frombuffer(data[80:84], dtype="<u4")
        if len(data) == 84 + 50 * int(count):
            record = np.frombuffer(data[84:], dtype=np.uint8).reshape(-1, 50)
            floats = record[:, :48].copy().view("<f4").reshape(-1, 12)
            return floats[:, 3:].reshape(-1, 3, 3).astype(float)
    vertices = re.findall(rb"vertex\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)", data)
    return np.array(vertices, dtype=float).reshape(-1, 3, 3)


def sample_surface(tris: np.ndarray, spacing: float, cap: int = 30000) -> np.ndarray:
    """Roughly uniform points on a triangle soup (for contact detection)."""
    edge1 = tris[:, 1] - tris[:, 0]
    edge2 = tris[:, 2] - tris[:, 0]
    areas = 0.5 * np.linalg.norm(np.cross(edge1, edge2), axis=1)
    counts = np.maximum(1, np.ceil(areas / (spacing * spacing)).astype(int))
    total = int(counts.sum())
    if total > cap:
        counts = np.maximum(1, (counts * (cap / total)).astype(int))
    tri_idx = np.repeat(np.arange(len(tris)), counts)
    rng = np.random.default_rng(0)
    u = rng.random(len(tri_idx))
    v = rng.random(len(tri_idx))
    flip = u + v > 1
    u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
    return (
        tris[tri_idx, 0]
        + edge1[tri_idx] * u[:, None]
        + edge2[tri_idx] * v[:, None]
    )


def to_matrix(transform: list[float]) -> np.ndarray:
    """BuildViz stores column-major 4x4 (THREE.Matrix4.fromArray convention)."""
    return np.asarray(transform, dtype=float).reshape(4, 4).T


def apply(matrix: np.ndarray, points: np.ndarray) -> np.ndarray:
    return points @ matrix[:3, :3].T + matrix[:3, 3]


# ---------------------------------------------------------------------------
# Per-part automatic load case
# ---------------------------------------------------------------------------

def contact_clusters(boundary_ids, coords_by_id, instances, self_index, mesh_tris, tol, spacing):
    """Group this part's surface nodes by which neighbor instance they touch."""
    boundary_pts = np.array([coords_by_id[n] for n in boundary_ids])
    lo, hi = boundary_pts.min(axis=0) - tol * 2, boundary_pts.max(axis=0) + tol * 2
    clusters = []
    for j, other in enumerate(instances):
        if j == self_index:
            continue
        if np.any(other["bboxMax"] < lo) or np.any(other["bboxMin"] > hi):
            continue
        tris = mesh_tris.get(other["meshId"])
        if tris is None or len(tris) == 0:
            continue
        samples = apply(other["matrix"], sample_surface(tris, spacing))
        hits = cKDTree(samples).query_ball_point(boundary_pts, tol)
        touching = np.array([i for i, h in enumerate(hits) if h])
        if touching.size < 3:
            continue
        nodes = [boundary_ids[i] for i in touching]
        clusters.append({
            "neighbor": other.get("name") or other["partType"],
            "neighborPartType": other["partType"],
            "neighborCenterZ": float((other["bboxMin"][2] + other["bboxMax"][2]) / 2),
            "nodes": nodes,
            "centroid": boundary_pts[touching].mean(axis=0),
        })
    return clusters


def spread_load(seed_nodes, exclude, coords_by_id, boundary_ids, radius):
    """Grow a load patch from seed nodes to every boundary node within radius:
    concentrating the full force on a screw-sized contact patch produces fake
    point-load stress peaks, whereas real loads arrive through a bearing area."""
    seeds = np.array([coords_by_id[n] for n in seed_nodes])
    candidates = [n for n in boundary_ids if n not in exclude]
    points = np.array([coords_by_id[n] for n in candidates])
    hits = cKDTree(seeds).query_ball_point(points, radius)
    return [n for n, h in zip(candidates, hits) if h]


def pick_fix_and_load(clusters, coords_by_id, boundary_ids, center, diag, bought):
    """Clamp inboard interface(s), load the outboard interface BAND (all
    interfaces near the far end share the force, like a real joint). Parts
    with one interface ring get a handling load on the far free end."""
    if not clusters:
        return None
    # A bought part RESTING on this one (electronics on a deck: contact patch
    # below the neighbor's center) cannot hold it down — it is not a fixture.
    # Treating it as one plants fake clamps mid-plate and fabricates stress at
    # their edges. Fasteners and printed neighbors still count as mounts.
    def is_resting(cluster):
        return (
            cluster["neighborPartType"] in bought
            and not FASTENER_RE.search(cluster["neighborPartType"])
            and cluster["neighborCenterZ"] > cluster["centroid"][2]
        )
    # Only mounts may CLAMP; every interface (horns, servos...) may carry load.
    mounts = [c for c in clusters if not is_resting(c)] or clusters
    distances = np.array([np.linalg.norm(c["centroid"] - center) for c in clusters])
    mount_distances = np.array([np.linalg.norm(c["centroid"] - center) for c in mounts])
    dmin, dmax = mount_distances.min(), distances.max()
    radius = max(diag * 0.1, 5.0)
    if dmax - dmin > max(diag * 0.2, 8.0):
        band = 0.25 * (dmax - dmin)
        fix_nodes = sorted({n for c, d in zip(mounts, mount_distances) if d <= dmin + band for n in c["nodes"]})
        fix_set = set(fix_nodes)
        outboard = [c for c, d in zip(clusters, distances) if d >= dmax - band]
        # Interfaces can share nodes (a screw and the part it clamps touch the
        # same face), so subtract clamped nodes rather than dropping clusters.
        seed = sorted({n for c in outboard for n in c["nodes"]} - fix_set)
        if seed:
            load_nodes = spread_load(seed, fix_set, coords_by_id, boundary_ids, radius)
            label = ", ".join(sorted({c["neighbor"] for c in outboard}))
            return fix_nodes, load_nodes, f"{label} joint", False
    # All mounts at similar radius (or inboard/outboard fully overlap):
    # clamp the mounts, push on the free point farthest from the clamps.
    fix_nodes = sorted({n for c in mounts for n in c["nodes"]})
    fix_set = set(fix_nodes)
    free = [n for n in boundary_ids if n not in fix_set]
    if not free:
        return None
    fix_centroid = np.array([coords_by_id[n] for n in fix_nodes]).mean(axis=0)
    free_pts = np.array([coords_by_id[n] for n in free])
    far_node = free[int(np.argmax(np.linalg.norm(free_pts - fix_centroid, axis=1)))]
    load_nodes = spread_load([far_node], fix_set, coords_by_id, boundary_ids, radius)
    return fix_nodes, load_nodes, "free end", True


def normalized(vector, fallback):
    length = float(np.linalg.norm(vector))
    return vector / length if length > 1e-6 else np.asarray(fallback, dtype=float)


# Joint-axis keywords as they appear in hexapod part/neighbor names. "hip" and
# "pitch" are the same physical joint (the femur lift servo).
MUJOCO_AXIS_WORDS = {
    "yaw": ("yaw",),
    "pitch": ("hip", "pitch", "femur"),
    "knee": ("knee", "tibia", "foot"),
}


def load_mujoco_report(paths: list[str], stat: str) -> dict:
    """Distill measured MuJoCo load reports into the numbers the load-case
    builder needs: per joint-axis bending moment, servo torque, and transmitted
    joint force, plus the worst foot ground force. Two formats are accepted and
    MERGED conservatively (element-wise max) when several files are given:

    * probe_walk_loads.py reports (weird_objects rl_move sim probe): per-axis
      bend/tau/force stats + per-foot ground force — the walking envelope.
    * Onshape-study load summaries (weird_objects strength/, e.g.
      fea/reports/onshape_study_loads.json): curated stand/walk/RISE/LOWER
      scenario peaks — single-foot normal envelope + servo torque envelope.
      These carry no bending moments, but the belly-to-plant rise event peaks
      ~2x the walking foot force, so merging one in lifts the foot and
      transmitted-force cases to the standup worst case."""
    merged: dict = {"axes": {}, "foot_n": 0.0, "stat": stat, "meta": {}}
    for path in paths:
        payload = json.loads(Path(path).read_text())
        if "per_axis" in payload:  # probe_walk_loads.py format
            for axis, entry in payload["per_axis"].items():
                prev = merged["axes"].setdefault(axis, {"bend_nm": 0.0, "tau_nm": 0.0, "force_n": 0.0})
                for key, src in (("bend_nm", "bend_nm"), ("tau_nm", "tau_nm"), ("force_n", "force_n")):
                    prev[key] = max(prev[key], float(payload["per_axis"][axis][src][stat]))
            merged["foot_n"] = max(merged["foot_n"],
                                   max(float(row[f"{stat}_n"]) for row in payload["per_foot"].values()))
            merged["meta"].update({key: payload.get(key) for key in
                                   ("ckpt", "vx_cmd", "mass_kg", "dr_scale", "variant", "seeds")})
        elif "top_scenarios" in payload or "walking_peak_single_foot_normal_N" in payload:
            # Onshape-study summary: scenario foot-normal peaks + torque envelope.
            foot = max([float(s["max_single_foot_normal_N"]) for s in payload.get("top_scenarios", [])]
                       + [float(payload.get("walking_peak_single_foot_normal_N") or 0.0),
                          float(payload.get("standing_peak_single_foot_normal_N") or 0.0)])
            merged["foot_n"] = max(merged["foot_n"], foot)
            tau_env = float(payload.get("servo_torque_envelope_Nm") or 0.0)
            for entry in merged["axes"].values():
                entry["tau_nm"] = max(entry["tau_nm"], tau_env)
            merged.setdefault("meta", {})["study"] = payload.get("source")
        else:
            raise SystemExit(f"unrecognized mujoco report format: {path}")
    # The rise/lower foot force transmits up the whole leg chain, so no joint
    # in the chain can see less than the foot envelope.
    for entry in merged["axes"].values():
        entry["force_n"] = max(entry["force_n"], merged["foot_n"])
    if not merged["axes"]:
        raise SystemExit("--mujoco-report needs at least one probe_walk_loads.py report (per-axis moments)")
    return merged


def classify_mujoco_axis(mujoco: dict, text: str) -> str | None:
    """Pick the joint axis a part serves from its own name and its interface
    neighbors. If several match (a link spans two joints), take the one with
    the larger measured bending moment — conservative for screening."""
    lowered = text.lower()
    matched = [axis for axis, words in MUJOCO_AXIS_WORDS.items()
               if axis in mujoco["axes"] and any(w in lowered for w in words)]
    if not matched:
        return None
    return max(matched, key=lambda axis: mujoco["axes"][axis]["bend_nm"])


# Caps / retainers / covers CLAMP a bearing or horn in place — they are
# parallel, secondary members. The joint bending moment resolves as a force
# couple through the horn and bearing seats into the servo body, not through
# the cap's own lever arm, and the ground reaction pushes the bearing INTO its
# pocket (compression), so the cap only ever sees retention/pry loads. A
# one-part-at-a-time cantilever model can't see that parallel load path;
# feeding a cap the full joint moment overstates its load by ~10x (which is
# exactly what "all the stress sits on top of the servos" looks like). Screen
# them with the handling press instead; their true share needs assembly FEA.
RETENTION_RE = re.compile(r"cap|retainer|cover|lid", re.IGNORECASE)


def build_load_cases(fix_nodes, load_nodes, coords_by_id, center, is_free_end, args, weight_n, force_n,
                     mujoco=None, part_text="", part_type=""):
    """The screening suite for one part: landing, walking traction (two
    horizontal directions), and servo-stall bending (lift plane + yaw-scrub
    plane). With --mujoco-report, the suite is replaced by MEASURED sim
    loads: joint bending moment over the part's lever arm, peak servo
    torque, and the transmitted joint force. Load signs don't matter in linear
    analysis (von Mises is invariant under load reversal), so one direction
    per axis covers both."""
    if is_free_end:
        return [("handling press", np.array([0.0, 0.0, -args.handling_n]))]
    if RETENTION_RE.search(part_type):
        return [("retention/handling press", np.array([0.0, 0.0, -args.handling_n]))]

    z = np.array([0.0, 0.0, 1.0])
    fix_centroid = np.array([coords_by_id[n] for n in fix_nodes]).mean(axis=0)
    load_centroid = np.array([coords_by_id[n] for n in load_nodes]).mean(axis=0)
    lever = load_centroid - fix_centroid
    lever_mm = float(np.linalg.norm(lever))
    axis = normalized(lever, [1, 0, 0])
    radial = normalized((load_centroid - center) * [1, 1, 0], [1, 0, 0])
    tangent = normalized(np.cross(z, radial), [0, 1, 0])
    # Perpendiculars to the leg axis: the lift plane (how a servo raises the
    # link against ground) and the horizontal scrub plane (turning drag).
    lift = normalized(z - axis * float(axis @ z), radial)
    scrub = normalized(np.cross(axis, z), tangent)

    axis_name = classify_mujoco_axis(mujoco, part_text) if mujoco else None
    if axis_name is not None:
        measured = mujoco["axes"][axis_name]
        stat = mujoco["stat"]
        arm_mm = max(lever_mm, 5.0)
        bend_force = measured["bend_nm"] * 1000.0 / arm_mm
        tau_force = measured["tau_nm"] * 1000.0 / arm_mm
        # Tibia-chain parts carry the raw ground reaction; other joints see
        # the (larger of) transmitted interaction force.
        transmitted = measured["force_n"]
        if any(word in part_text.lower() for word in ("tibia", "foot")):
            transmitted = max(transmitted, mujoco["foot_n"])
        return [
            (f"mj walk bend lift [{axis_name} {measured['bend_nm']:.2f} N*m {stat}]", bend_force * lift),
            (f"mj walk bend scrub [{axis_name} {measured['bend_nm']:.2f} N*m {stat}]", bend_force * scrub),
            (f"mj rise/lower tau [{axis_name} {measured['tau_nm']:.2f} N*m {stat}]", tau_force * lift),
            (f"mj walk/rise joint force [{transmitted:.0f} N {stat}]", np.array([0.0, 0.0, -transmitted])),
        ]

    walk_v = args.walk_g * weight_n
    walk_h = args.friction * walk_v
    stall = args.servo_torque_nm * 1000.0 / max(lever_mm, 5.0)
    return [
        (f"landing {args.impact_g:g}g", np.array([0.0, 0.0, -force_n])),
        (f"walk traction radial ({args.walk_g:g}g+mu)", -walk_v * z + walk_h * radial),
        (f"walk traction lateral ({args.walk_g:g}g+mu)", -walk_v * z + walk_h * tangent),
        (f"rise/lower servo stall ({stall:.0f} N)", stall * lift),
        (f"turn scrub servo stall ({stall:.0f} N)", stall * scrub),
    ]


# ---------------------------------------------------------------------------
# Robot-wide report + stress build
# ---------------------------------------------------------------------------

def combined_highlight_url(hub, build_id, part_results, yield_mpa):
    points = []
    for result in sorted(part_results, key=lambda r: r["safetyFactor"]):
        spot = result["hotspots"][0]
        sf = result["safetyFactor"]
        color = "#d94a35" if sf < 1.5 else ("#ec9b3b" if sf < 3 else "#3fb27f")
        points.append({
            "point": spot["positionMm"],
            "color": color,
            "label": f"{result['partType']} SF {sf:.1f}",
            "annotation": f"{result['partType']}: {spot['vonMisesMPa']} MPa max · SF {sf:.1f} ({result['loadDescription']})",
            "radiusMm": 3,
        })
    project, _, build = build_id.partition("/")
    query = f"project={project}&build={build}" if build else f"build={build_id}"
    payload = urllib.parse.quote(json.dumps({"points": points[:14]}, separators=(",", ":")))
    return f"{hub}/?{query}&highlight={payload}"


def push_robot_stress_build(build_id, analysis_name, scene, analyzed, instances, mesh_bytes, hub,
                            message, yield_mpa, source_version=None):
    """Attach the stress view as a NAMED ANALYSIS PAGE on the analyzed build
    (not a separate build): printed parts as stress bins (all siblings),
    everything else as gray context. One GLOBAL color scale for the whole
    robot, anchored at the material yield: red means at/over yield everywhere,
    so a mildly loaded plate can't glow like a failing bracket."""
    bins = len(ws.STRESS_RAMP)
    with tempfile.TemporaryDirectory(prefix="buildviz-fea-robot-") as tmp:
        tmp_path = Path(tmp)
        meshes, out_instances = [], []
        analyzed_types = {r["partType"] for r in analyzed}

        edges_mpa = [yield_mpa * fraction for fraction in STRESS_BIN_FRACTIONS]
        for result in analyzed:
            inv0 = np.linalg.inv(result["matrix"])
            tri_bins: list[list[np.ndarray]] = [[] for _ in range(bins)]
            for tri, value in zip(result["surfaceTris"], result["surfaceTriVm"]):
                level = int(np.searchsorted(edges_mpa, value))
                tri_bins[level].append(apply(inv0, tri))
            for level, bucket in enumerate(tri_bins):
                if not bucket:
                    continue
                slug = f"{result['partType']}_vm{level:02d}"
                (tmp_path / f"{slug}.stl").write_bytes(ws.binary_stl(np.array(bucket)))
                lo = edges_mpa[level - 1] if level > 0 else 0.0
                hi = edges_mpa[level] if level < len(edges_mpa) else float("inf")
                label = f"{lo:g}-{hi:g} MPa" if level < bins - 1 else f">{lo:g} MPa (YIELD)"
                meshes.append({"id": f"stl:{slug}", "name": f"{result['partType']} {label}", "url": f"{slug}.stl"})
                result.setdefault("binSlugs", []).append((level, slug, lo, hi))

        for index, inst in enumerate(instances):
            source = inst["raw"]
            if inst["partType"] in analyzed_types:
                result = next(r for r in analyzed if r["partType"] == inst["partType"])
                for level, slug, lo, hi in result.get("binSlugs", []):
                    out_instances.append({
                        "id": f"{source.get('id', inst['partType'])}_{index}_vm{level:02d}",
                        "meshId": f"stl:{slug}",
                        "name": f"{source.get('name', inst['partType'])} · "
                                + (f"{lo:g}-{hi:g} MPa" if np.isfinite(hi) else f">{lo:g} MPa (YIELD)"),
                        "partType": f"{inst['partType']}_vm{level:02d}",
                        "role": f"von Mises bin {level + 1}/{bins}",
                        "color": ws.STRESS_RAMP[level],
                        "transform": source["transform"],
                    })
            else:
                mesh_id = inst["meshId"]
                if not any(m["id"] == mesh_id for m in meshes):
                    slug = re.sub(r"[^A-Za-z0-9_.-]", "_", mesh_id)
                    (tmp_path / f"{slug}.stl").write_bytes(mesh_bytes[mesh_id])
                    original = next(m for m in scene["meshes"] if m["id"] == mesh_id)
                    meshes.append({"id": mesh_id, "name": original.get("name", mesh_id), "url": f"{slug}.stl"})
                # Context parts go uniform gray: only the stress ramp should
                # carry color in this build.
                out_instances.append({**source, "color": CONTEXT_GRAY})

        derived = {
            "name": f"{scene.get('name', 'robot')} — FEA stress",
            "source": "buildviz fea/robot_weakspots.py",
            "schemaVersion": scene.get("schemaVersion", 3),
            "units": scene.get("units", "mm"),
            "center": scene.get("center", [0, 0, 0]),
            "meshes": meshes,
            "instances": out_instances,
        }
        scene_path = tmp_path / "scene.json"
        scene_path.write_text(json.dumps(derived))
        command = ["npx", "buildviz", "push-analysis", build_id, "--name", analysis_name,
                   "--scene", str(scene_path), "--assets-dir", str(tmp_path),
                   "--display-name", analysis_name.replace("-", " "), "-m", message]
        if source_version:
            command += ["--source-version", source_version]
        result = subprocess.run(command, capture_output=True, text=True, timeout=600)
        sys.stdout.write(result.stdout)
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            print("(analysis push failed; the FEA report above is still valid)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Whole-robot weak-spot FEA for a BuildViz build")
    parser.add_argument("build", help="build id on the hub (e.g. prototype_sts3215)")
    parser.add_argument("--hub", default="http://127.0.0.1:5183")
    parser.add_argument("--impact-g", type=float, default=3.0, help="landing impact factor (default 3)")
    parser.add_argument("--force-n", type=float, help="override the per-part force (default: mass x g x impact-g)")
    parser.add_argument("--handling-n", type=float, default=30.0,
                        help="load for parts OUTSIDE the leg load path (free-end case, default 30 N)")
    parser.add_argument("--walk-g", type=float, default=1.5,
                        help="dynamic factor for the walking-traction cases (default 1.5)")
    parser.add_argument("--friction", type=float, default=0.8,
                        help="foot friction coefficient for horizontal traction (default 0.8)")
    parser.add_argument("--servo-torque-nm", type=float, default=1.9,
                        help="servo stall torque for rise/turn cases, N*m (default 1.9 ~ STS3215)")
    parser.add_argument("--mujoco-report", metavar="JSON", action="append",
                        help="measured load report (repeatable, merged by max): probe_walk_loads.py "
                             "walking report and/or an Onshape-study load summary with the "
                             "rise/lower foot-force envelope (see fea/reports/)")
    parser.add_argument("--mujoco-stat", choices=("max", "p95"), default="max",
                        help="which statistic of the measured loads to apply (default max)")
    parser.add_argument("--parts", help="only analyze partTypes matching this regex")
    parser.add_argument("--skip", help="additionally skip partTypes matching this regex")
    parser.add_argument("--elem-mm", type=float, help="target element size for all parts")
    parser.add_argument("--contact-tol", type=float, default=1.2, help="interface detection distance, mm")
    parser.add_argument("--top-k", type=int, default=5, help="hotspots kept per part")
    parser.add_argument("--out", help="write the aggregated results JSON here")
    parser.add_argument("--material", help="material name label (default PLA)")
    parser.add_argument("--young-mpa", type=float, help="Young's modulus override, MPa")
    parser.add_argument("--yield-mpa", type=float,
                        help="yield strength override, MPa — sets the failure threshold AND the red "
                             "end of the analysis color scale (e.g. 22.7 for PETG at 25%% infill)")
    parser.add_argument("--push-analysis", metavar="NAME",
                        help="attach the stress view as a named analysis PAGE on the analyzed build "
                             "(shows in the viewer's Analyses picker; re-push overwrites)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    hub = args.hub.rstrip("/")
    mujoco = None
    if args.mujoco_report:
        mujoco = load_mujoco_report(args.mujoco_report, args.mujoco_stat)
        meta = mujoco["meta"]
        print(f"MuJoCo loads ({', '.join(args.mujoco_report)}, {args.mujoco_stat}): "
              + " · ".join(f"{axis} bend {v['bend_nm']:.2f} N*m / tau {v['tau_nm']:.2f} N*m / F {v['force_n']:.0f} N"
                           for axis, v in mujoco["axes"].items())
              + f" · foot {mujoco['foot_n']:.0f} N"
              + (f" · vx {meta['vx_cmd']} m/s dr {meta['dr_scale']}" if meta.get("vx_cmd") is not None else ""))

    scene = json.loads(fetch(hub, f"/builds/{args.build}/scene.json"))
    material = dict(ws.DEFAULT_MATERIAL)
    if args.material:
        material["name"] = args.material
    if args.young_mpa:
        material["youngMPa"] = args.young_mpa
    if args.yield_mpa:
        material["yieldMPa"] = args.yield_mpa
    bought = set((scene.get("checksConfig") or {}).get("partMassesGrams", {}))
    center = np.asarray(scene.get("center", [0, 0, 0]), dtype=float)

    mesh_urls = {m["id"]: m["url"] for m in scene["meshes"]}
    mesh_bytes, mesh_tris = {}, {}
    for mesh_id, url in mesh_urls.items():
        path = url if url.startswith("/") else f"/builds/{args.build}/{url}"
        try:
            mesh_bytes[mesh_id] = fetch(hub, path)
            mesh_tris[mesh_id] = parse_stl(mesh_bytes[mesh_id])
        except Exception as error:  # noqa: BLE001 - missing context mesh is survivable
            print(f"warning: could not load mesh {mesh_id}: {error}")

    instances = []
    for raw in scene["instances"]:
        matrix = to_matrix(raw["transform"])
        tris = mesh_tris.get(raw["meshId"])
        if tris is None or len(tris) == 0:
            continue
        corners = apply(matrix, tris.reshape(-1, 3))
        instances.append({
            "raw": raw, "partType": raw["partType"], "meshId": raw["meshId"],
            "name": raw.get("name"), "matrix": matrix,
            "bboxMin": corners.min(axis=0), "bboxMax": corners.max(axis=0),
        })

    printed = {}
    for index, inst in enumerate(instances):
        part_type = inst["partType"]
        if part_type in printed or part_type in bought or FASTENER_RE.search(part_type):
            continue
        if args.parts and not re.search(args.parts, part_type):
            continue
        if args.skip and re.search(args.skip, part_type):
            continue
        printed[part_type] = index
    skipped = sorted({i["partType"] for i in instances} - set(printed))
    print(f"{len(instances)} instances · analyzing {len(printed)} printed partTypes: {', '.join(printed)}")
    print(f"skipped (bought/fastener/filtered): {', '.join(skipped)}")

    if args.force_n:
        force_n = args.force_n
        weight_n = force_n / args.impact_g
    else:
        mass = subprocess.run(["npx", "buildviz", "mass", args.build, "--json"], capture_output=True, text=True, timeout=300)
        grams = json.loads(mass.stdout)["results"]["totalGrams"] if mass.returncode == 0 else None
        if grams is None:
            sys.exit("Could not estimate mass; pass --force-n")
        weight_n = grams / 1000 * 9.81
        force_n = weight_n * args.impact_g
        print(f"robot mass ~{grams / 1000:.2f} kg -> worst single-foot force {force_n:.1f} N (impact {args.impact_g}g)")

    results, failures = [], []
    for part_type, index in printed.items():
        inst = instances[index]
        siblings = sum(1 for i in instances if i["partType"] == part_type)
        print(f"\n--- {part_type} ({siblings} instance(s), analyzing one) ---")
        try:
            with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as handle:
                handle.write(mesh_bytes[inst["meshId"]])
                stl_path = Path(handle.name)

            solved_cases = None
            # Escalate on failure: distorted STL tets can break the solve, the
            # voxel remesh survives anything (at ~1 voxel geometric cost).
            for order, strategy in ((2, "auto"), (2, "remesh"), (1, "remesh")):
                ids, local_coords, tets, tet_type, tris = ws.mesh_part(
                    stl_path, args.elem_mm, order, args.verbose, strategy=strategy)
                coords = apply(inst["matrix"], local_coords)
                coords_by_id = {int(n): coords[i] for i, n in enumerate(ids)}
                boundary_ids = sorted({int(n) for n in np.unique(tris)})
                diag = float(np.linalg.norm(coords.max(axis=0) - coords.min(axis=0)))

                # A remeshed surface sits up to ~1 voxel off the true one, so
                # widen the interface search accordingly.
                tol = args.contact_tol if strategy == "auto" else max(args.contact_tol, diag / 150 * 1.6)
                clusters = contact_clusters(boundary_ids, coords_by_id, instances, index, mesh_tris,
                                            tol, spacing=1.0)
                picked = pick_fix_and_load(clusters, coords_by_id, boundary_ids, center, diag, bought)
                if picked is None:
                    break
                fix_nodes, load_nodes, load_at, is_free_end = picked
                part_text = " ".join(
                    [part_type, load_at]
                    + [f"{c['neighbor']} {c['neighborPartType']}" for c in clusters])
                cases = build_load_cases(fix_nodes, load_nodes, coords_by_id, center,
                                         is_free_end, args, weight_n, force_n,
                                         mujoco=mujoco, part_text=part_text, part_type=part_type)
                print(f"  {len(clusters)} interface(s): {', '.join(sorted({c['neighbor'] for c in clusters}))}")
                print(f"  clamped {len(fix_nodes)} nodes · load over {len(load_nodes)} nodes at {load_at}"
                      + (f" [{tet_type}/{strategy}]" if strategy != "auto" or order != 2 else ""))

                solved_cases = []
                for case_index, (case_name, force_vec) in enumerate(cases):
                    try:
                        with tempfile.TemporaryDirectory(prefix="buildviz-ccx-") as tmp:
                            job = Path(tmp) / "part"
                            ws.write_inp(job, ids, coords, tets, tet_type, fix_nodes,
                                         [(load_nodes, force_vec.tolist())], material)
                            frd = ws.run_ccx(job, args.verbose)
                            disp, stress = ws.parse_frd(frd)
                    except SystemExit:
                        # First case failing means the mesh is bad -> escalate;
                        # later failures are case-specific, skip just the case.
                        if case_index == 0:
                            solved_cases = None
                            break
                        print(f"    {case_name}: solve failed, skipped")
                        continue
                    stress_ids = np.array(sorted(stress))
                    vm = ws.von_mises(np.array([stress[n] for n in stress_ids]))
                    vm_by_id = dict(zip(stress_ids.tolist(), vm.tolist()))
                    max_vm = float(vm.max())
                    safety = material["yieldMPa"] / max_vm if max_vm > 0 else float("inf")
                    max_disp = max(float(np.linalg.norm(d)) for d in disp.values()) if disp else 0.0
                    force_mag = float(np.linalg.norm(force_vec))
                    print(f"    {case_name:34s} {force_mag:6.0f} N -> max {max_vm:7.1f} MPa · SF {safety:5.2f}")
                    solved_cases.append({
                        "name": case_name, "forceN": round(force_mag, 1),
                        "maxVonMisesMPa": round(max_vm, 2), "maxDeflectionMm": round(max_disp, 3),
                        "safetyFactor": round(safety, 2), "vmById": vm_by_id,
                    })
                if solved_cases:
                    break
            stl_path.unlink()
            if picked is None:
                failures.append((part_type, "no contact interfaces found"))
                print("  no interfaces found — skipping (try --contact-tol)")
                continue
            if not solved_cases:
                failures.append((part_type, "all load cases failed to solve"))
                continue

            worst = min(solved_cases, key=lambda c: c["safetyFactor"])
            # Stress view + hotspots use the ENVELOPE: worst von Mises any
            # case produced at each node.
            envelope: dict[int, float] = {}
            for case in solved_cases:
                for node, value in case["vmById"].items():
                    if value > envelope.get(node, 0.0):
                        envelope[node] = value
            safety = worst["safetyFactor"]
            verdict = "FAILS" if safety < 1 else ("MARGINAL" if safety < 2 else "OK")
            spots = ws.hotspot_clusters(sorted(envelope), {n: coords_by_id[n].tolist() for n in coords_by_id},
                                        envelope, args.top_k, radius=max(diag / 12, 4.0))
            print(f"  worst: {worst['name']} · max {worst['maxVonMisesMPa']:.1f} MPa · SF {safety:.2f} -> {verdict}")

            surface_tris, surface_vm = [], []
            for tri in tris:
                corner_ids = [int(n) for n in tri[:3]]
                if all(n in envelope for n in corner_ids):
                    surface_tris.append(np.array([coords_by_id[n] for n in corner_ids]))
                    surface_vm.append(max(envelope[n] for n in corner_ids))
            results.append({
                "partType": part_type, "instances": siblings,
                "measured": any(c["name"].startswith("mj ") for c in solved_cases),
                "maxVonMisesMPa": worst["maxVonMisesMPa"], "maxDeflectionMm": worst["maxDeflectionMm"],
                "safetyFactor": safety, "verdict": verdict,
                "loadDescription": f"{worst['forceN']:.0f} N {worst['name']} at {load_at}",
                "cases": [{k: v for k, v in c.items() if k != "vmById"} for c in solved_cases],
                "hotspots": spots, "matrix": inst["matrix"],
                "surfaceTris": surface_tris, "surfaceTriVm": surface_vm,
            })
        except (SystemExit, Exception) as error:  # noqa: BLE001 - keep batch going
            failures.append((part_type, str(error)))
            print(f"  FAILED: {error}")

    if not results:
        sys.exit("No parts analyzed successfully.")

    loads_label = (f"MuJoCo walk loads {args.mujoco_stat}, heuristic for off-path parts"
                   if mujoco else f"{force_n:.0f} N single-foot case")
    print(f"\n=== robot weak-spot report ({args.build}, {loads_label}) ===")
    print(f"{'part':26s} {'max MPa':>8s} {'SF':>6s}  verdict")
    for result in sorted(results, key=lambda r: r["safetyFactor"]):
        print(f"{result['partType']:26s} {result['maxVonMisesMPa']:8.1f} {result['safetyFactor']:6.2f}  {result['verdict']}"
              + (f"  <- {result['loadDescription']}" if result["safetyFactor"] < 2 else ""))
    for part_type, reason in failures:
        print(f"{part_type:26s} {'—':>8s} {'—':>6s}  SKIPPED ({reason.splitlines()[0][:60]})")

    print("\ncombined hotspot overlay (open in BuildViz):")
    print(combined_highlight_url(hub, args.build, results, material["yieldMPa"]))

    if args.push_analysis:
        weakest = min(results, key=lambda r: r["safetyFactor"])
        print("\nattaching stress analysis page ...")
        source = f"MuJoCo walk loads ({args.mujoco_stat})" if mujoco else f"{force_n:.0f} N heuristic"
        # In measured mode, off-load-path parts only saw the handling press —
        # coloring them would put heuristic stress on a "walking loads" page.
        colored = [r for r in results if r["measured"]] if mujoco else results
        # Label the page with the build version it was computed from.
        source_version = None
        try:
            index = json.loads(fetch(hub, "/builds/index.json"))
            entry = next((b for b in index.get("builds", []) if b.get("id") == args.build), None)
            source_version = (entry or {}).get("defaultVersion")
        except Exception:  # noqa: BLE001 - label only
            pass
        push_robot_stress_build(
            args.build, args.push_analysis, scene, colored, instances, mesh_bytes, hub,
            f"robot FEA, {source}: weakest {weakest['partType']} SF {weakest['safetyFactor']}",
            yield_mpa=material["yieldMPa"], source_version=source_version,
        )

    if args.out:
        Path(args.out).write_text(json.dumps({
            "build": args.build, "forceN": round(force_n, 1), "impactG": args.impact_g,
            "material": material,
            "mujocoReport": ({"path": args.mujoco_report, "stat": args.mujoco_stat,
                              "axes": mujoco["axes"], "footN": mujoco["foot_n"],
                              "meta": mujoco["meta"]} if mujoco else None),
            "parts": [{k: v for k, v in r.items() if k not in ("matrix", "surfaceTris", "surfaceTriVm", "binSlugs")}
                      for r in sorted(results, key=lambda r: r["safetyFactor"])],
            "failures": [{"partType": p, "reason": r} for p, r in failures],
        }, indent=2))
        print(f"results JSON -> {args.out}")


if __name__ == "__main__":
    main()
