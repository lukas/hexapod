"""Two-piece printable coxa with a full support plate and four self-tappers.

This revives the repository's retired Part A / Part B coxa split without
bringing back the dovetail quick-release.  Part A carries the yaw hub and a
full rectangular support plate; Part B carries the hip cradle and 688 housing.
Four self-tapping screws enter upward from the underside of Part A into
reinforced corner pads in Part B.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
PROTO_DIR = HERE.parents[1]
STL_DIR = HERE / "stl"
sys.path.insert(0, str(PROTO_DIR))
import hexapod_prototype as hp  # noqa: E402
sys.path.insert(0, str(HERE.parent / "horn_compression_limiters"))
import make_horn_compression_limiter_concept as limiter  # noqa: E402


BUILD_ID = "prototype_sts3215/two-piece-coxa-screws"
SPLIT_Z = hp.YAW_HUB_PLATFORM_Z1

# Existing Part A/B bolt pattern.
JOIN_PCD = hp.COXA_JOIN_BOLT_PCD
JOIN_ANGLES = hp.COXA_JOIN_BOLT_ANGLES_RAD
SELF_TAP_PILOT_OD = hp.COXA_JOIN_PILOT_OD
SELF_TAP_HEAD_OD = 5.7
SELF_TAP_HEAD_DEPTH = 3.0
SELF_TAP_LENGTH = 10.0

# Four actual material locations in the hip bracket, reinforced by printed
# corner pads below.  They are deliberately outside the five yaw-drive holes.
SELF_TAP_CENTRES = ((-27.0, -16.0), (27.0, -16.0),
                    (-27.0, 16.0), (27.0, 16.0))
PLATE_MARGIN = 1.0
CORNER_PAD_R = 3.5
CORNER_PAD_H = 8.0

# Ordinary M3 hex nuts captured in Part A.  The small radial clearance is
# deliberately printable; tune it with one pocket coupon before six robots.
HEX_NUT_AF = 5.8
HEX_POCKET_AF = 6.2
HEX_POCKET_DEPTH = 3.2

REGISTER_H = 2.0


def _cyl(radius: float, height: float, z0: float) -> trimesh.Trimesh:
    mesh = trimesh.creation.cylinder(radius=radius, height=height, sections=96)
    mesh.apply_translation([0.0, 0.0, z0 + height / 2.0])
    return mesh


def _hex_prism(across_flats: float, height: float, z0: float,
               x: float, y: float) -> trimesh.Trimesh:
    # trimesh's regular polygon radius is the circumradius.  Rotate a flat
    # onto the X axis so the pocket is predictable in the printed part.
    radius = across_flats / math.sqrt(3.0)
    mesh = trimesh.creation.cylinder(
        radius=radius, height=height, sections=6, start_angle=math.pi / 6.0
    )
    mesh.apply_translation([x, y, z0 + height / 2.0])
    return mesh


def _difference(source: trimesh.Trimesh,
                cuts: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    result = trimesh.boolean.difference([source, *cuts], engine="manifold")
    result.remove_unreferenced_vertices()
    if not result.is_volume:
        raise RuntimeError("two-piece coxa boolean did not produce a volume")
    return result


def _union(source: trimesh.Trimesh,
           additions: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    result = trimesh.boolean.union([source, *additions], engine="manifold")
    result.remove_unreferenced_vertices()
    if not result.is_volume:
        raise RuntimeError("two-piece coxa register union did not produce a volume")
    return result


def _join_centres() -> list[tuple[float, float]]:
    radius = JOIN_PCD / 2.0
    return [(radius * math.cos(angle), radius * math.sin(angle))
            for angle in JOIN_ANGLES]


def _make_screw_reference() -> trimesh.Trimesh:
    """Local-space self-tapper entering upward from the hub underside."""
    shaft = _cyl(1.45, SELF_TAP_LENGTH, 0.0)
    head = _hex_prism(SELF_TAP_HEAD_OD, SELF_TAP_HEAD_DEPTH,
                      -SELF_TAP_HEAD_DEPTH, 0.0, 0.0)
    screw = trimesh.boolean.union([shaft, head], engine="manifold")
    screw.remove_unreferenced_vertices()
    return screw


def build_parts() -> tuple[trimesh.Trimesh, trimesh.Trimesh]:
    hub = hp.make_coxa_yaw_hub(one_piece=False)
    raw_leg = hp.make_coxa_hip_bracket(one_piece=False)

    # Trim the upper part first; derive the lower plate from its real face.

    below_seam = trimesh.creation.box(extents=[120.0, 120.0, 40.0])
    below_seam.apply_translation([0.0, 0.0, SPLIT_Z - 20.0])
    leg = _difference(raw_leg, [below_seam])

    # Add four reinforced corner pads above the seam for upward self-tapping
    # screws.  The pads make the attachment locations real bracket material,
    # rather than relying on the retired lower foot geometry.
    corner_pads = []
    for x, y in SELF_TAP_CENTRES:
        pad = _cyl(CORNER_PAD_R, CORNER_PAD_H, SPLIT_Z)
        pad.apply_translation([x, y, 0.0])
        corner_pads.append(pad)
    leg = _union(leg, corner_pads)

    face = leg.section(plane_origin=[0,0,SPLIT_Z+.001], plane_normal=[0,0,1])
    assert face is not None
    planar, _ = face.to_2D(to_2D=np.eye(4))
    plates = []
    for polygon in planar.polygons_full:
        plate = trimesh.creation.extrude_polygon(
            polygon, SPLIT_Z-hp.YAW_HUB_BOSS_TOP_Z, engine="earcut")
        plate.apply_translation([0,0,hp.YAW_HUB_BOSS_TOP_Z])
        plates.append(plate)
    hub = _union(hub, plates)

    hub_cuts = []
    leg_cuts = []
    for x, y in SELF_TAP_CENTRES:
        # Underside counterbore for the self-tapper head and a pilot through
        # the full support plate.
        head = _cyl(SELF_TAP_HEAD_OD / 2.0, SELF_TAP_HEAD_DEPTH + 0.3,
                    hp.YAW_HUB_BOSS_TOP_Z - SELF_TAP_HEAD_DEPTH)
        head.apply_translation([x, y, 0.0])
        hub_cuts.append(head)
        bore = _cyl(SELF_TAP_PILOT_OD / 2.0,
                    SPLIT_Z - hp.YAW_HUB_BOSS_TOP_Z + 0.5,
                    hp.YAW_HUB_BOSS_TOP_Z - 0.25)
        bore.apply_translation([x, y, 0.0])
        hub_cuts.append(bore)
        # Pilot into the printed corner pad above the mating plane.
        up = _cyl(SELF_TAP_PILOT_OD / 2.0, CORNER_PAD_H + 0.5,
                   SPLIT_Z - 0.25)
        up.apply_translation([x, y, 0.0])
        leg_cuts.append(up)
    hub = _difference(hub, hub_cuts)
    # Separate from the four bracket-to-hub join screws: five open access
    # shafts for the yaw-horn drive hardware already modeled in Part A
    # (center plus four stations on the disc-horn PCD).  These must remain
    # open through Part B so a driver can reach the yaw hub below it.
    yaw_access_shafts = []
    yaw_access_r = hp.YAW_HUB_HORN_HEAD_CB_OD / 2.0
    yaw_stations = [(0.0, 0.0)]
    yaw_r = hp.DISC_HORN_BOLT_PCD / 2.0
    yaw_stations.extend(
        (yaw_r * math.cos(angle), yaw_r * math.sin(angle))
        for angle in hp.DISC_HORN_BOLT_ANGLES_RAD
    )
    for x, y in yaw_stations:
        access = _cyl(yaw_access_r, 80.0 - hp.YAW_HUB_HORN_CENTRE_SEAT_Z,
                      hp.YAW_HUB_HORN_CENTRE_SEAT_Z)
        access.apply_translation([x, y, 0.0])
        yaw_access_shafts.append(access)
    leg = _difference(leg, [*leg_cuts, *yaw_access_shafts])

    # Apply access cuts AFTER the support-plate union, to both halves. The
    # plate previously closed the hub's holes while only Part B was re-drilled.
    centre_access = yaw_access_shafts[0]
    if limiter.SPACER_ENABLED:
        hub = limiter._add_yaw_limiter_nub(hub)
        # The added neck must not fill the original centre/spline clearance.
        centre = limiter._cyl_z(hp.HORN_CENTRE_OD / 2,
                               hp.YAW_HUB_BOSS_BOT_Z - .2, 80, 0, 0)
        collar = limiter._cyl_z(hp.DISC_HORN_COLLAR_OD / 2 + .25,
                               hp.YAW_HUB_BOSS_BOT_Z - .2,
                               hp.YAW_HUB_BOSS_BOT_Z + hp.DISC_HORN_COLLAR_DEPTH + 1,
                               0, 0)
        access_cuts = [centre_access, *limiter._yaw_head_access_cuts()]
        hub = _difference(hub, [centre, collar, *limiter._yaw_limiter_cuts(), *access_cuts])
        leg = _difference(leg, access_cuts)
    else:
        hub = _difference(hub, yaw_access_shafts)
    verify_yaw_paths(hub, leg)

    for name, mesh in (("coxa_hub_screw.stl", hub),
                       ("coxa_leg_screw.stl", leg)):
        mesh.export(STL_DIR / name)
        if not mesh.is_watertight:
            raise RuntimeError(f"{name} is not watertight")

    _make_screw_reference().export(STL_DIR / "m3_screw_reference.stl")

    # Four upward self-tapper hardware instances are visual references only.
    fasteners = []
    for index, (x, y) in enumerate(SELF_TAP_CENTRES):
        fasteners.append({
            "id": f"self-tap-{index}",
            "meshId": "stl:m3_screw",
            "name": f"M3 self-tapper {index + 1}",
            "partType": "m3_self_tapper",
            "role": "hardware",
            "joint": None,
            "leg": None,
            "cots": True,
            "color": "#505050",
            "transform": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0,
                           x, y, hp.YAW_HUB_BOSS_TOP_Z, 1],
        })

    scene = {
        "name": "STS3215 two-piece coxa — full support plate + four self-tappers",
        "source": "make_two_piece_coxa_screws.py",
        "buildId": BUILD_ID,
        "designSpecUrl": "design_spec.yaml",
        "units": "mm",
        "center": [0, 0, 12],
        "meshes": [
            {"id": "stl:hub", "name": "coxa_hub_screw.stl",
             "url": "stl/coxa_hub_screw.stl"},
            {"id": "stl:leg", "name": "coxa_leg_screw.stl",
             "url": "stl/coxa_leg_screw.stl"},
            {"id": "stl:m3_screw", "name": "m3_screw_reference.stl",
             "url": "stl/m3_screw_reference.stl"},
        ],
        "instances": [
            {"id": "hub", "meshId": "stl:hub",
             "name": "Part A — yaw hub with compression-spacer pockets",
             "partType": "coxa_hub_screw", "role": "concept",
             "joint": None, "leg": None, "cots": False,
             "color": "#4878b0",
             "transform": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0,
                            0, 0, 0, 1]},
            {"id": "leg", "meshId": "stl:leg",
             "name": "Part B — hip bracket with flat print face",
             "partType": "coxa_leg_screw", "role": "concept",
             "joint": None, "leg": None, "cots": False,
             "color": "#c44e52",
             "transform": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0,
                            0, 0, 0, 1]},
            *fasteners,
        ],
    }
    if limiter.SPACER_ENABLED:
        limiter._annular_spacer(limiter.SPACER_LENGTH).export(STL_DIR / "yaw_spacer_DO_NOT_PRINT.stl")
        scene["meshes"].append({"id": "stl:yaw_spacer", "name": "yaw_spacer_DO_NOT_PRINT.stl",
                                "url": "stl/yaw_spacer_DO_NOT_PRINT.stl"})
        for index, angle in enumerate(hp.DISC_HORN_BOLT_ANGLES_RAD):
            x, y = 7*math.cos(angle), 7*math.sin(angle)
            scene["instances"].append({
                "id": f"yaw-spacer-{index}", "meshId": "stl:yaw_spacer",
                "name": f"Yaw compression spacer {index+1}: {limiter.SPACER_OD:g} OD x {limiter.SPACER_LENGTH:g} mm",
                "partType": "yaw_compression_spacer", "role": "hardware", "cots": True,
                "color": "#d6a84a", "joint": None, "leg": None,
                "transform": [1,0,0,0,0,1,0,0,0,0,1,0,x,y,hp.YAW_HUB_BOSS_BOT_Z,1],
            })
    (HERE / "scene.json").write_text(json.dumps(scene, indent=2) + "\n")
    return hub, leg


def verify_yaw_paths(hub: trimesh.Trimesh, leg: trimesh.Trimesh) -> None:
    """Volume probes on final solids catch filled holes in either half."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    def outline(mesh, z):
        section = mesh.section(plane_origin=[0,0,z], plane_normal=[0,0,1])
        planar, _ = section.to_2D(to_2D=np.eye(4))
        return unary_union([Polygon(p.exterior) for p in planar.polygons_full])
    bottom = outline(hub, SPLIT_Z-.001)
    top = outline(leg, SPLIT_Z+.001)
    round_hub = outline(hp.make_coxa_yaw_hub(one_piece=False), SPLIT_Z-.001)
    mismatch = bottom.symmetric_difference(top).difference(round_hub.buffer(.002)).area
    assert mismatch < .05, f"mating outlines differ outside round hub: {mismatch} mm2"
    print(f"Mating-outline mismatch outside round hub: {mismatch:.6f} mm2")
    probes = [limiter._cyl_z(hp.YAW_HUB_HORN_HEAD_CB_OD / 2 - .05,
                            hp.YAW_HUB_HORN_CENTRE_SEAT_Z + .01, 80, 0, 0)]
    probes.append(limiter._cyl_z(hp.HORN_CENTRE_OD / 2 - .05,
                                hp.YAW_HUB_BOSS_BOT_Z-.1, 80, 0, 0))
    if limiter.SPACER_ENABLED:
        probes += limiter._yaw_head_access_cuts()
        probes += limiter._yaw_limiter_cuts(limiter.SPACER_OD + .05)
    else:
        probes += [limiter._cyl_z(hp.YAW_HUB_HORN_HEAD_CB_OD / 2 - .05,
                                 hp.YAW_HUB_HORN_HEAD_SEAT_Z + .01, 80,
                                 7*math.cos(a), 7*math.sin(a))
                   for a in hp.DISC_HORN_BOLT_ANGLES_RAD]
    for name, mesh in (("hub", hub), ("bracket", leg)):
        assert mesh.is_volume and mesh.body_count == 1, f"{name} is not one closed solid"
        for i, probe in enumerate(probes):
            intersection = trimesh.boolean.intersection([mesh, probe], engine="manifold")
            assert abs(intersection.volume) < .001, f"{name} yaw path {i} is obstructed"
    if limiter.SPACER_ENABLED:
        assert abs(limiter.YAW_PERIMETER_HEAD_SEAT_Z - hp.YAW_HUB_BOSS_BOT_Z
                   - limiter.SPACER_LENGTH - limiter.SEAT_PRELOAD) < 1e-6
        for angle in hp.DISC_HORN_BOLT_ANGLES_RAD:
            x, y = 7*math.cos(angle), 7*math.sin(angle)
            # Washer bears on solid plastic just outside the enlarged bore.
            ring = [[x+3.2*math.cos(a), y+3.2*math.sin(a),
                     limiter.YAW_PERIMETER_HEAD_SEAT_Z-.1]
                    for a in np.linspace(0,2*math.pi,16,endpoint=False)]
            assert hub.contains(ring).all(), "yaw washer seat lacks material"
    print("Verified five open yaw-driver paths through both halves and configured spacer clearance")


if __name__ == "__main__":
    STL_DIR.mkdir(parents=True, exist_ok=True)
    hub, leg = build_parts()
    print(f"split plane z={SPLIT_Z:.2f} mm")
    print(f"hub volume={hub.volume / 1000:.1f} cm^3")
    print(f"leg volume={leg.volume / 1000:.1f} cm^3")
    print("wrote scene.json and two printable STL parts")
