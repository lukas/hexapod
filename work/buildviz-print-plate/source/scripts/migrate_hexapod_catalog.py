#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Audit and classify existing hexapod builds without changing their geometry.

Dry-run is the default. It snapshots the complete index (including branches),
proposes catalog entries, and derives missing revision notes from saved scenes.
Apply a reviewed plan with --apply --plan <report.json>. Credentials never enter
the report, command line, or generated files.
"""

import argparse
import base64
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_URL = "https://buildviz.cwd1f0-new-cluster.coreweave.app"
MAIN = "prototype_sts3215"
FIRST = "prototype_sts3215/hexapod-v1"
METAL = "prototype_sts3215/premade-chorn-56"
AS_BUILT_FIRST = "2026-08-07-f9c91cf"
PLAN_VERSION = 2
SECOND_ROBOT_NAME = "Hexapod 2 · three-bearing STS"
SECOND_ROBOT_DESCRIPTION = (
    "Second built STS hexapod with two lower bearings and one upper bearing, as identified by the owner. "
    "Conversion to spacer-equipped joint parts is in progress; the displayed main STS CAD is a reference, "
    "with the exact installed revision still unpinned.")

# These are classifications of existing sources, never renames or moves. Stable
# semantic IDs intentionally differ from source IDs and remain useful after a
# producer renames a branch or directory.
CLASSIFICATIONS = {
    "prototype_sts3215/two-piece-coxa-screws": (
        "sts-coxa-split-support", "Split coxa support", "assembly", "active", "hexapod-2",
        "Two-piece yaw hub and hip bracket with a full support plate and accessible joining screws. This component design is also used in the current full STS CAD."),
    "prototype_sts3215/horn-compression-limiters": (
        "sts-horn-compression-study", "Spacer-equipped joint parts", "assembly", "active", "hexapod-2",
        "Selected replacement parts for Hexapod 2's spacer retrofit: coxa/yaw support, femur, and knee yoke, plus the fit coupon. The owner is switching the robot to these parts; installation is in progress and the completed configuration is not yet recorded."),
    "prototype_sts3215/fsr-sensor-foot": (
        "sts-contact-sensor-foot", "Contact-sensing foot", "study", "active", "hexapod-2",
        "Guided RP-C10 sensor-foot assembly with a tread, carriage, force spreader, and travel stops. The scene is a component study; calibrated force performance is not established."),
    "prototype_sts3215/knee-yoke-apriltag-flag": (
        "sts-knee-measurement-flag", "Knee measurement flag", "assembly", "active", "hexapod-1",
        "Push-on AprilTag flag for measuring knee-yoke motion, with separate printable holder and tag inlay. Attaches over existing screw heads."),
    "prototype_sts3215/rigid-hip": (
        "sts-rigid-yaw-support", "Rigid yaw support", "study", "active", "hexapod-metal",
        "Full-robot design study supporting the yaw axis at the upper and lower chassis. It is an ancestor of the metal-clamp designs; the old third-bearing display name is historical."),
    "prototype_sts3215/cnc-chorn-overhead": (
        "sts-cnc-overhead-study", "Custom CNC overhead clamps", "study", "active", "hexapod-metal",
        "Full-robot alternative using custom CNC aluminum clamps and an outboard hip pivot for overhead leg motion. This is distinct from the purchased 56 mm bracket build."),
    "prototype_sts3215/cnc-chorn-two-piece": (
        "sts-cnc-split-clamp-study", "Split CNC clamp", "study", "active", "hexapod-metal",
        "Custom CNC clamp alternative with independent driven and passive plates to simplify assembly. The locating joint remains experimental."),
    "prototype_sts3215/chassis-reinforcement-test": (
        "sts-chassis-reinforcement-study", "Chassis reinforcement", "study", "active", "hexapod-2",
        "Chassis and yaw-pocket reinforcement study with separate load-path test pieces. These are design-test configurations, not another physical robot."),
    "prototype_sts3215/tibia-yoke-reinforcement-test": (
        "sts-tibia-reinforcement-study", "Knee and tibia reinforcement", "study", "active", "hexapod-2",
        "Reinforcement study for the printed knee yoke and carbon-tube connection. Saved versions explore the moving leg's load path."),
    "prototype_sts3215_aluminum": (
        "sts-aluminum-stiffness-study", "Aluminum stiffness comparison", "study", "active", "hexapod-metal",
        "Earlier aluminum-bracket stiffness concept. Kept as a comparison study rather than a second STS project."),
    "fea/robot-stress": (
        "sts-whole-robot-stress-study", "Whole-robot stress study", "study", "active", "hexapod-2",
        "Full STS assembly displayed with finite-element stress results. The scene represents an analysis setup, not an installed hardware revision."),
    "dovetail-coxa-concept/split-coxa": (
        "sts-dovetail-coxa-study", "Dovetail coxa joint", "study", "active", "hexapod-2",
        "Alternative quick-release coxa connection using a printed dovetail. Retained separately from the current robot assembly."),
    "dovetail-coxa-concept/coupons": (
        "sts-dovetail-fit-coupons", "Dovetail fit coupons", "assembly", "active", "sts-dovetail-coxa-study",
        "Small fit-test pieces for the dovetail coxa connection. These coupon revisions belong to the joint study."),
    "qr-femur-concept/split-femur": (
        "sts-quick-release-femur-study", "Quick-release femur", "study", "active", "hexapod-2",
        "Split femur concept using a printed tenon for assembly and removal. It is an alternative component design, not a robot revision."),
    "prototype_ak40": (
        "ak40-hexapod-study", "AK40 actuator concept", "study", "active", None,
        "Hexapod design using AK40 actuators and CAN control. Repository documentation describes a design awaiting hardware-fit verification; it is not identified as either built STS robot."),
    "rideable_v2": (
        "rideable-hexapod-study", "Rideable hexapod study", "study", "archived", None,
        "Archived rideable-walker design visualization from an earlier design generation."),
    "single-motor-hexapod/crank-walker": (
        "single-motor-hexapod-study", "Single-motor crank walker", "study", "active", None,
        "Separate six-legged mechanism driven by one motor and cranks. It does not share the STS robot's independently actuated leg design."),
    "buildviz/hexapod-prototype": (
        "hobby-servo-hexapod-history", "Earlier hobby-servo prototype", "study", "archived", None,
        "Historical prototype_v1 model using hobby-servo electronics and an animated gait. This source is not the owner-identified first STS robot."),
    "cnc_chorn_overhead": (
        "archived-cnc-overhead-source", "Old CNC overhead source", "study", "archived", "sts-cnc-overhead-study",
        "Retired standalone source preserved with its original versions. Current work is grouped under Custom CNC overhead clamps."),
    "sts3215-rigid-hip": (
        "archived-rigid-yaw-source", "Old rigid-yaw source", "study", "archived", "sts-rigid-yaw-support",
        "Retired standalone rigid-hip source with historical revisions. Its version history remains available here."),
    "sts3215-rigid-hip-step": (
        "archived-rigid-yaw-step-source", "Old rigid-yaw STEP source", "study", "archived", "sts-rigid-yaw-support",
        "Retired STEP-pipeline rigid-hip source. Preserved for provenance and comparison with later geometry."),
}

DEMO_IDS = {
    "buildviz/hexapod-2", "buildviz/hexapod-fresh", "buildviz/hexapod-motion-demo",
    "buildviz/hexapod-collision-chassis", "buildviz/hexapod-collision-femur",
    "buildviz/overlap-allowlist-demo", "branch-demo/widget", "step-demo/as1",
}

PART_NAMES = {
    "chorn_clamp_cnc": "C bracket", "femur_ovh_body": "femur body", "tibia_ovh_socket": "tibia socket",
    "coxa_link_ovh": "coxa support", "hip_clamp_cap_ovh": "hip clamp cap", "knee_clamp_cap_ovh": "knee clamp cap",
    "hip_bearing_carrier_ovh": "upper yaw-bearing carrier", "coxa_yaw_hub_carrier_ovh": "lower yaw-bearing carrier",
    "fsr_guided_carriage": "guided sensor carriage", "fsr_tpu_tread": "flexible tread", "fsr_tpu_sole": "flexible sole",
    "fsr_tpu_sensing_spring": "flexible sensing spring", "fsr_foot_housing": "sensor-foot housing",
    "fsr_force_spreader": "force spreader", "makerhawk_rpc10_fsr": "RP-C10 sensor reference",
    "knee_yoke_apriltag_holder_white": "measurement-flag holder", "knee_yoke_apriltag_inlay_black": "AprilTag inlay",
    "coxa_link_yaw_compression_limiter_test": "yaw coxa with compression sleeves",
    "femur_link_compression_limiter_test": "femur with compression sleeves",
    "tibia_knee_yoke_compression_limiter_test": "knee yoke with compression sleeves",
}

# These are selections of existing full-assembly snapshots. They do not mint
# independent CAD copies or histories merely to display an assembly in isolation.
ASSEMBLY_SELECTIONS = {
    "chassis": ("Chassis", {"chassis_bottom", "chassis_top", "chassis_top_rigid", "top_hatch_rigid", "chassis_standoff", "yaw_servo_retainer"}),
    "yaw-hip": ("Yaw and hip support", {"coxa_link", "coxa_hip_bracket", "coxa_yaw_hub", "coxa_link_ovh", "coxa_yaw_hub_carrier_ovh", "hip_bearing_carrier_ovh", "hip_clamp_cap", "hip_clamp_cap_ovh", "yaw_bearing_cap", "yaw_bearing_lower", "yaw_bearing_upper", "bearing_6805", "coxa_self_tapper", "coxa_join_hex_nut", "coxa_join_machine_screw"}),
    "knee-foot": ("Knee, tibia and foot", {"knee_clamp_cap", "knee_clamp_cap_ovh", "tibia_knee_yoke", "tibia_tube", "tibia_tube_ovh", "tibia_ovh_socket", "foot_boot", "foot_pad", "tibia_foot_fitting"}),
}

INITIAL_NOTES = {
    MAIN: "Full STS robot assembly from the main design history, showing the chassis, six articulated legs, and fitted hardware.",
    FIRST: "Original STS robot design source with its split coxa, chassis, six articulated legs, and fitted hardware.",
    "dovetail-coxa-concept/coupons": "Dovetail coxa fit coupons for checking the printed joint before making complete links.",
    "prototype_sts3215/chassis-reinforcement-test": "Chassis reinforcement comparison showing separate printed structures and loading fixtures.",
    "prototype_sts3215/cnc-chorn-overhead": "Full-robot layout with custom CNC C-clamps and an outboard hip pivot for overhead leg travel.",
    "prototype_sts3215/cnc-chorn-two-piece": "Full-robot layout with split CNC clamps, allowing the driven and passive horn plates to be installed independently.",
    "prototype_sts3215/fsr-sensor-foot": "Sensor-foot concept with an RP-C10 reference, printed housing, force spreader, and flexible contact parts.",
    "prototype_sts3215/horn-compression-limiters": "Coxa, femur, and knee-yoke parts with metal compression sleeves, shown alongside a fit coupon.",
    "prototype_sts3215/knee-yoke-apriltag-flag": "Knee-yoke measurement flag with a printable holder and separate AprilTag inlay, mounted over the reference screw heads.",
    "prototype_sts3215/premade-chorn-56": "Full-robot layout using purchased 56 mm C brackets, printed leg adapters, and rigid yaw supports.",
    "prototype_sts3215/rigid-hip": "Full-robot rigid-yaw-support concept with an upper chassis frame and removable central hatch.",
}


def encoded(value):
    return urllib.parse.quote(value, safe="/")


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Hub:
    def __init__(self, url, key):
        self.url = url.rstrip("/")
        self.key = key

    def request(self, path, body=None, method="GET"):
        headers = {"Accept": "application/json"}
        if self.key:
            headers["X-API-Key"] = self.key
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.url + path,
            data=None if body is None else json.dumps(body).encode(), headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)


def credential(args):
    key = os.environ.get("BUILDVIZ_API_KEY", "").strip()
    if key or not args.kubeconfig:
        return key
    raw = subprocess.check_output(["kubectl", "--kubeconfig=" + str(Path(args.kubeconfig).expanduser()),
        "get", "secret", "buildviz-api-key", "-o", "jsonpath={.data.key}"], stderr=subprocess.PIPE)
    return base64.b64decode(raw).decode().strip()


def branches(build):
    return build.get("branches") or [{"name": build.get("defaultBranch", "main"),
        "defaultVersion": build.get("defaultVersion", "main"), "versions": build.get("versions", [])}]


def source(build_id, branch="main", version=None):
    return {"buildId": build_id, "branch": branch, **({"version": version} if version else {})}


def entry(semantic_id, name, kind, status, description, src, parent=None, collection="hexapods", **extra):
    return {"id": semantic_id, "name": name, "kind": kind, "collection": collection,
        "description": description, "status": status, "source": src,
        **({"parentId": parent} if parent else {}), **extra}


def make_catalog(builds, second_confirmed=False):
    # Keep the old optional argument compatible; the owner's September 8
    # clarification now supplies the identity without identifying a CAD snapshot.
    by_id = {b["id"]: b for b in builds}
    required = {FIRST, MAIN, METAL}
    if required - by_id.keys():
        raise ValueError("Missing primary source builds: " + ", ".join(sorted(required - by_id.keys())))
    first_versions = {v["name"] for br in branches(by_id[FIRST]) for v in br.get("versions", []) if br["name"] == "main"}
    if AS_BUILT_FIRST not in first_versions:
        raise ValueError("Owner-identified first-robot snapshot is missing; refusing to invent an as-built pin")
    first = entry("hexapod-1", "Hexapod 1 · original STS", "robot", "built",
        "Original STS robot used in RobotLab, with the split coxa and legacy 6706 bearing stack. The as-built reference is pinned separately from later screw and horn-access design revisions.",
        source(FIRST), aliases=["hexapod-v1", "RobotLab first STS", FIRST],
        asBuilt={**source(FIRST, "main", AS_BUILT_FIRST), "evidence":
            "Owner identification recorded in this snapshot's original revision message; repository robots/hexapod-1.yaml confirms the legacy split coxa and thinner bearings."},
        milestones=[{"name": "Original RobotLab assembly", "description":
            "Owner-identified original assembly; subsequent screw and access revisions are separate proposals.",
            "source": source(FIRST, "main", AS_BUILT_FIRST)}])
    second = entry("hexapod-2", SECOND_ROBOT_NAME, "robot", "built", SECOND_ROBOT_DESCRIPTION,
        source(MAIN), aliases=["second built hexapod", "main STS", MAIN,
            "three-bearing STS", "two lower bearings one upper", "spacer retrofit"])
    metal = entry("hexapod-metal", "Next hexapod · metal C-clamps", "robot", "planned",
        "Upcoming build using the purchased 56 mm aluminum C brackets and rigid upper/lower yaw support. Design history includes holder, bearing-carrier, screw-access, and reinforcement revisions; no assembled configuration is recorded.",
        source(METAL), aliases=["metal C clamps", "premade 56 mm C horns", "next hexapod", METAL])
    items = [first, second, metal]
    classified = set(required)
    for build_id, values in CLASSIFICATIONS.items():
        if build_id not in by_id:
            continue
        semantic_id, name, kind, status, parent, description = values
        items.append(entry(semantic_id, name, kind, status, description,
            source(build_id, by_id[build_id].get("defaultBranch", "main")), parent,
            aliases=[build_id, by_id[build_id].get("name", name)]))
        classified.add(build_id)
    for build_id in sorted(DEMO_IDS & by_id.keys()):
        items.append(entry("archived-demo-" + re.sub(r"[^a-z0-9]+", "-", build_id.lower()).strip("-"),
            by_id[build_id].get("name", build_id), "study", "archived",
            "Bundled example or viewer test preserved under its original source ID. Its name does not identify a physical robot.",
            source(build_id, by_id[build_id].get("defaultBranch", "main")), collection="buildviz-examples",
            aliases=[build_id]))
        classified.add(build_id)
    # Branch classification is explicit: a full-robot scene on an experimental
    # branch remains a study. Walk ALL branches, not only build.versions.
    for build in builds:
        if build["id"] not in classified or build["id"] in DEMO_IDS:
            continue
        for br in branches(build):
            if br["name"] == build.get("defaultBranch", "main"):
                continue
            semantic_id = "sts-yoke-reinforced-study" if (build["id"], br["name"]) == (MAIN, "yoke-reinforced") else \
                "branch-study-" + re.sub(r"[^a-z0-9]+", "-", build["id"] + "-" + br["name"]).strip("-")
            items.append(entry(semantic_id, "Reinforced yoke" if semantic_id == "sts-yoke-reinforced-study" else br["name"].replace("-", " "),
                "study", "active", "Alternative design preserved on its original branch, with an independent revision history.",
                source(build["id"], br["name"]), "hexapod-2", aliases=[build["id"] + ":" + br["name"]]))
    ids = {i["id"] for i in items}
    used_aliases = set(ids)
    for item in items:
        if item.get("parentId") not in ids:
            item.pop("parentId", None)
        aliases = []
        for alias in item.get("aliases", []):
            if alias not in used_aliases:
                aliases.append(alias)
                used_aliases.add(alias)
        item["aliases"] = aliases
    return items, sorted(set(by_id) - classified)


def scene_path(ref, filename="scene.json"):
    path = "/builds/" + encoded(ref["buildId"])
    if ref.get("branch", "main") != "main":
        path += "/branches/" + encoded(ref["branch"])
    if ref.get("version"):
        path += "/versions/" + encoded(ref["version"])
    return path + "/" + filename


def summarize_scene(scene):
    return {"name": scene.get("name"), "source": scene.get("source"),
        "metadata": scene.get("metadata"), "instanceCount": len(scene.get("instances", [])),
        "partCounts": dict(sorted(Counter(i.get("partType", "untyped") for i in scene.get("instances", [])).items())),
        "sha256": fingerprint(scene)}


def scene_parts(scene):
    meshes = {m["id"]: m for m in scene.get("meshes", [])}
    parts = defaultdict(list)
    for i in scene.get("instances", []):
        mesh = meshes.get(i.get("meshId"), {})
        # Content-addressed assets make mesh identity comparable across snapshots.
        # No hash means a URL reference difference only, not proven geometry.
        url = str(mesh.get("url", ""))
        parts[i.get("partType", "untyped")].append({"mesh": url,
            "transform": i.get("transform"), "count": 1})
    return {k: sorted(v, key=lambda item: json.dumps(item, sort_keys=True)) for k, v in parts.items()}


def difference(before, after):
    a, b = scene_parts(before), scene_parts(after)
    common = set(a) & set(b)
    geometry = sorted(k for k in common if sorted(v["mesh"] for v in a[k]) != sorted(v["mesh"] for v in b[k]))
    moved = sorted(k for k in common if k not in geometry and a[k] != b[k])
    return {"added": sorted(set(b) - set(a)), "removed": sorted(set(a) - set(b)),
        "geometryReferencesChanged": geometry, "placementChanged": moved,
        "changed": sorted(k for k in common if a[k] != b[k]),
        "sameScene": fingerprint(before) == fingerprint(after)}


def friendly(parts):
    names = [PART_NAMES.get(p, p.replace("_", " ")) for p in parts]
    if len(names) > 4:
        remaining = len(names) - 4
        names = names[:4] + [f"{remaining} other component {'type' if remaining == 1 else 'types'}"]
    return ", ".join(names)


def needs_description(build_id, branch, revision, since):
    if revision.get("message", "").strip():
        return False
    return (build_id in {FIRST, MAIN, METAL} or
        revision.get("pushedAt", "")[:10] >= since or
        revision["name"] == branch.get("defaultVersion"))


def revision_note(scene, prior, prior_version, label, build_id=""):
    """Conservative, inspectable descriptions; never claim fit or strength."""
    if prior is None:
        description = INITIAL_NOTES.get(build_id, label + ": saved component arrangement.")
        return (description + " Earliest preserved scene in this source; earlier change details are unrecorded.",
            {"basis": "saved-scene-and-classification", "scene": summarize_scene(scene)})
    diff = difference(prior, scene)
    clauses = []
    if diff["added"]:
        clauses.append("Adds " + friendly(diff["added"]))
    if diff["removed"]:
        clauses.append("removes " + friendly(diff["removed"]))
    if diff["geometryReferencesChanged"]:
        clauses.append("updates the displayed " + friendly(diff["geometryReferencesChanged"]))
    if diff["placementChanged"]:
        clauses.append("repositions " + friendly(diff["placementChanged"]))
    if not clauses:
        text = ("Re-publishes the same saved scene as " + prior_version + "." if diff["sameScene"] else
            "Same component geometry references and placements as " + prior_version + "; scene metadata or presentation differs.")
    else:
        text = "; ".join(clauses) + ". Compared with " + prior_version + "."
    return text[0].upper() + text[1:], {"basis": "scene-comparison", "comparedWith": prior_version,
        "difference": diff, "beforeSha256": fingerprint(prior), "afterSha256": fingerprint(scene)}


def fetch_scene(hub, build, branch, version):
    ref = source(build["id"], branch["name"], version)
    try:
        return hub.request(scene_path(ref))
    except urllib.error.HTTPError as error:
        if error.code != 404 or version != branch.get("defaultVersion"):
            raise
        return hub.request(scene_path(source(build["id"], branch["name"])))


def assembly_entries(hub, builds):
    items, evidence = [], {}
    by_id = {b["id"]: b for b in builds}
    for parent, build_id in (("hexapod-1", FIRST), ("hexapod-2", MAIN), ("hexapod-metal", METAL)):
        build = by_id[build_id]
        branch = next(br for br in branches(build) if br["name"] == build.get("defaultBranch", "main"))
        ref = source(build_id, branch["name"], branch["defaultVersion"])
        # The view contract requires a materialized immutable snapshot. No root
        # mirror fallback here: absent snapshots are reported, not falsely pinned.
        scene = hub.request(scene_path(ref))
        actual = {i.get("partType") for i in scene.get("instances", [])}
        evidence[parent] = {**summarize_scene(scene), "reference": ref}
        for slug, (name, requested) in ASSEMBLY_SELECTIONS.items():
            selected = sorted(actual & requested)
            if not selected:
                continue
            items.append(entry(parent + "-" + slug, name, "assembly", "active",
                f"Selected components from CAD revision {ref['version']}. Shares the full robot's source history; this selection does not establish what is installed.",
                ref, parent, view={"partTypes": selected}))
    return items, evidence


def audit(hub, args):
    status = hub.request("/__buildviz/status")
    if status.get("service") != "buildviz-hub":
        raise ValueError("The target does not identify itself as the BuildViz hub")
    index = hub.request("/builds/index.json")
    builds = index.get("builds") or [b for p in index.get("projects", []) for b in p.get("builds", [])]
    warnings = []
    try:
        existing = hub.request("/__buildviz/catalog")
        if existing.get("schema") != 1:
            raise ValueError("Unexpected catalog schema")
    except (urllib.error.HTTPError, json.JSONDecodeError, ValueError) as error:
        existing = {"schema": 1, "items": []}
        warnings.append("Catalog read unavailable before deployment: " + type(error).__name__)
    items, unclassified = make_catalog(builds, args.second_robot_confirmed)
    selections, selection_evidence = assembly_entries(hub, builds)
    # Read the named original snapshot as well as the current CAD selections.
    as_built_scene = hub.request(scene_path(source(FIRST, "main", AS_BUILT_FIRST)))
    items.extend(selections)
    labels = {}
    for item in items:
        if item["status"] != "archived" and not item.get("view"):
            # A selected subassembly shares its source without renaming the
            # full robot's history; nondefault studies retain their own label.
            labels.setdefault((item["source"]["buildId"], item["source"].get("branch", "main")), item["name"])
    targets = [b for b in builds if b["id"].startswith("prototype_sts3215") or b["id"] in {"dovetail-coxa-concept/coupons", "dovetail-coxa-concept/split-coxa", "qr-femur-concept/split-femur"}]

    def metadata(build):
        try:
            return build["id"], hub.request("/builds/" + encoded(build["id"]) + "/meta.json")
        except (urllib.error.HTTPError, json.JSONDecodeError) as error:
            return build["id"], {"readError": type(error).__name__}

    with ThreadPoolExecutor(max_workers=6) as pool:
        meta = dict(pool.map(metadata, targets))
    tasks = []
    for build in targets:
        for br in branches(build):
            records = {v["name"]: dict(v) for v in br.get("versions", [])}
            # Metadata can carry original messages not surfaced by an older index.
            meta_branches = branches(meta.get(build["id"], {}))
            for mbr in meta_branches:
                if mbr["name"] == br["name"]:
                    for version in mbr.get("versions", []):
                        if version["name"] in records and version.get("message"):
                            records[version["name"]]["message"] = version["message"]
            ordered = sorted(records.values(), key=lambda v: (v.get("pushedAt", ""), v["name"]))
            for n, revision in enumerate(ordered):
                if not needs_description(build["id"], br, revision, args.since):
                    continue
                tasks.append((build, br, revision, ordered[n - 1] if n else None))

    def describe(task):
        build, br, revision, previous = task
        ref = source(build["id"], br["name"], revision["name"])
        try:
            scene = fetch_scene(hub, build, br, revision["name"])
            before = fetch_scene(hub, build, br, previous["name"]) if previous else None
            message, evidence = revision_note(scene, before, previous["name"] if previous else None, labels.get((build["id"], br["name"]), build.get("name", build["id"])), build["id"])
            return {**ref, "message": message, "ifMessageMissing": True,
                "pushedAt": revision.get("pushedAt"), "evidence": evidence}
        except (urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as error:
            return {**ref, "skipped": True, "reason": "Saved scene could not be read: " + type(error).__name__}

    with ThreadPoolExecutor(max_workers=6) as pool:
        descriptions = list(pool.map(describe, tasks))
    by_existing = {i["id"]: i for i in existing.get("items", [])}
    proposed = [i for i in items if i["id"] not in by_existing]
    preserved = sorted(i["id"] for i in items if i["id"] in by_existing)
    return {"schema": 1, "planVersion": PLAN_VERSION, "createdAt": datetime.now(timezone.utc).isoformat(), "url": hub.url,
        "mode": "dry-run", "since": args.since, "indexSnapshot": index,
        "catalogBefore": existing, "metadataSnapshots": meta,
        "assemblySelectionEvidence": selection_evidence,
        "firstRobotAsBuiltScene": summarize_scene(as_built_scene),
        "catalogItems": proposed, "preservedExistingCatalogIds": preserved,
        "revisionUpdates": [d for d in descriptions if not d.get("skipped")],
        "skippedRevisions": [d for d in descriptions if d.get("skipped")],
        "unclassifiedBuildIds": unclassified,
        "warnings": warnings,
        "identityEvidence": {
            "hexapod-1": "Original version message identifies RobotLab first STS; pinned to " + FIRST + "@" + AS_BUILT_FIRST,
            "hexapod-2": "Owner clarification 2026-09-08: two bearings at the bottom and one at the top; switching to all spacer-equipped parts. Retrofit in progress; exact installed CAD revision unrecorded, main STS retained only as a design reference.",
            "hexapod-metal": "User requests upcoming metal-clamp build; premade_chorn_56 README records 16 purchased brackets, 12 per robot",
            "ordering": "Versions ordered by pushedAt, never numerically: names were reused/reset after older high version numbers"},
        "counts": {"builds": len(builds), "branches": sum(len(branches(b)) for b in builds),
            "versions": sum(len(br.get("versions", [])) for b in builds for br in branches(b)),
            "catalogItems": len(proposed), "revisionUpdates": sum(not d.get("skipped", False) for d in descriptions)}}


def apply(hub, plan):
    if plan.get("planVersion") != PLAN_VERSION:
        raise ValueError("Outdated migration plan: run a new dry audit before applying; this report lacks validated source references")
    if plan.get("url", "").rstrip("/") != hub.url:
        raise ValueError("Reviewed plan belongs to a different hub")
    for recorded in plan.get("assemblySelectionEvidence", {}).values():
        ref = recorded.get("reference")
        if not isinstance(ref, dict) or not all(isinstance(ref.get(k), str) and ref[k] for k in ("buildId", "branch", "version")):
            raise ValueError("Invalid pinned assembly reference in migration plan: run a new dry audit")
    current = hub.request("/__buildviz/catalog")
    if current.get("schema") != 1:
        raise ValueError("Catalog API is not deployed")
    for recorded in plan.get("assemblySelectionEvidence", {}).values():
        if fingerprint(hub.request(scene_path(recorded["reference"]))) != recorded["sha256"]:
            raise ValueError("Pinned assembly scene changed since review: " + json.dumps(recorded["reference"]))
    if plan.get("firstRobotAsBuiltScene") and fingerprint(hub.request(scene_path(source(FIRST, "main", AS_BUILT_FIRST)))) != plan["firstRobotAsBuiltScene"]["sha256"]:
        raise ValueError("Original as-built snapshot changed since review")
    before_by_id = {i["id"]: i for i in plan.get("catalogBefore", {}).get("items", [])}
    current_by_id = {i["id"]: i for i in current.get("items", [])}
    desired = []
    for item in plan["catalogItems"]:
        present = current_by_id.get(item["id"])
        if present == item:
            continue
        if present is not None and present != before_by_id.get(item["id"]):
            raise ValueError("Catalog item changed since review: " + item["id"])
        desired.append(item)
    live_index = hub.request("/builds/index.json")
    live_builds = live_index.get("builds") or [b for p in live_index.get("projects", []) for b in p.get("builds", [])]
    by_build = {b["id"]: b for b in live_builds}

    def current_scene(ref):
        build = by_build.get(ref["buildId"])
        branch = next((b for b in branches(build) if b["name"] == ref["branch"]), None) if build else None
        if branch is None:
            raise ValueError("Reviewed revision's source build or branch is no longer present")
        # Root mirrors are valid only for this branch's current default. The
        # same rule is used during audit, including legacy root-only defaults.
        return fetch_scene(hub, build, branch, ref["version"])

    ready, skipped = [], []
    # Validate every source read before the first write. A stale or unavailable
    # revision can be skipped without preventing independent reviewed metadata.
    for update in plan["revisionUpdates"]:
        payload = {key: update[key] for key in ("buildId", "branch", "version", "message", "ifMessageMissing")}
        evidence = update.get("evidence", {})
        expected = evidence.get("afterSha256") or evidence.get("scene", {}).get("sha256")
        try:
            changed = not expected or fingerprint(current_scene(payload)) != expected
            if evidence.get("comparedWith"):
                previous = {**payload, "version": evidence["comparedWith"]}
                changed = changed or fingerprint(current_scene(previous)) != evidence["beforeSha256"]
            reason = "Scene changed after the reviewed audit" if changed else None
        except (urllib.error.HTTPError, json.JSONDecodeError, TimeoutError, ValueError) as error:
            reason = "Reviewed scene is unavailable: " + type(error).__name__
        if reason:
            skipped.append({"source": {k: payload[k] for k in ("buildId", "branch", "version")},
                "result": {"updated": False, "skipped": reason}})
            continue
        ready.append(payload)
    results = {"catalog": hub.request("/__buildviz/catalog", {"items": desired}, "POST") if desired else {"ok": True, "unchanged": True}, "revisions": skipped}
    # Updates are conditional and additive; an intervening producer note wins.
    for payload in ready:
        results["revisions"].append({"source": {k: payload[k] for k in ("buildId", "branch", "version")},
            "result": hub.request("/__buildviz/revisions/metadata", payload, "PATCH")})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Default; read only")
    mode.add_argument("--apply", action="store_true", help="Apply the reviewed --plan")
    parser.add_argument("--plan", type=Path, help="Previously reviewed report; required with --apply")
    parser.add_argument("--report", type=Path, default=Path("/tmp/buildviz-hexapod-catalog-audit.json"))
    parser.add_argument("--since", default="2026-09-01", help="Backfill all blank primary robot notes; for other sources use this date plus branch defaults")
    parser.add_argument("--kubeconfig", help="Read the existing buildviz-api-key secret; defaults to BUILDVIZ_API_KEY env instead")
    parser.add_argument("--second-robot-confirmed", action="store_true", help="Legacy compatibility flag; the owner's three-bearing configuration is now recorded, without inventing an installed CAD revision")
    args = parser.parse_args()
    if args.apply and not args.plan:
        parser.error("--apply requires a reviewed --plan; run a dry audit first")
    hub = Hub(args.url, credential(args))
    if args.apply:
        plan = json.loads(args.plan.read_text())
        plan["applyResults"] = apply(hub, plan)
        plan["mode"] = "applied"
        plan["appliedAt"] = datetime.now(timezone.utc).isoformat()
    else:
        plan = audit(hub, args)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(plan, indent=2) + "\n")
    print(json.dumps({"mode": plan["mode"], "report": str(args.report), "counts": plan["counts"],
        "warnings": plan.get("warnings", []), "skippedRevisions": len(plan.get("skippedRevisions", []))}, indent=2))


if __name__ == "__main__":
    main()
