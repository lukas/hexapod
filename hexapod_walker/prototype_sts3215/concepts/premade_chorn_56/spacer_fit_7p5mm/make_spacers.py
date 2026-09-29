"""Export isolated 7.5 mm fit-test spacers; do not modify published assemblies.

Run from the repository root with uv run python <this file>.
Only the bracket-facing plane moves 0.5 mm. The horn-side head pocket is
not scaled, and all hole diameters/centers remain exactly as in v38.
"""
from pathlib import Path
import hashlib
import json
import math
import urllib.request

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
EXTRA = 0.5
SOURCES = {
    "driven": "b1eadb1649e57c0b5fa2dfa2196a71b2279a50791c568d6a2b0313765fa2654d",
    "passive": "1ac5ba9098b887e0136d0b2d3c47dee4da0f147b8cc13e8887c91851190d6efa",
}


def make_spacer(kind, sha):
    source = HERE.parent / "stl" / f"{kind}_spacer_7mm.stl"
    if not source.is_file():
        source = HERE / "source" / f"{sha}.stl"
        source.parent.mkdir(exist_ok=True)
        if not source.is_file():
            urllib.request.urlretrieve(
                f"https://buildviz.cwd1f0-new-cluster.coreweave.app/builds/_assets/{sha}.stl", source)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == sha
    old = trimesh.load_mesh(source)
    assert old.is_volume and old.body_count == 1
    assert np.isclose(old.extents[2], 7.0, atol=1e-5)
    edited = old.copy()
    # Driven horn seats at min-Z; passive horn seats at max-Z in source CAD.
    outer = old.bounds[1 if kind == "driven" else 0, 2]
    on_face = np.isclose(old.vertices[:, 2], outer, atol=1e-5, rtol=0)
    surface = np.all(np.abs(old.triangles[:, :, 2] - outer) < 1e-5, axis=1)
    expected_added_volume = float(old.area_faces[surface].sum()) * EXTRA
    edited.vertices[on_face, 2] += EXTRA if kind == "driven" else -EXTRA
    assert edited.is_volume and edited.body_count == 1
    assert np.allclose(edited.extents, [21, 21, 7.5], atol=1e-5)
    assert np.isclose(edited.volume - old.volume, expected_added_volume, rtol=1e-5)
    removed = trimesh.boolean.difference([old, edited], engine="manifold")
    assert removed.is_empty or abs(removed.volume) < 1e-4

    # Original four Ø3.4 bores on a 14 mm PCD stay open for the full length.
    z0, z1 = edited.bounds[:, 2]
    zs = np.linspace(z0 + .01, z1 - .01, 30)
    centers = [(19.5, 0), (12.5, 7), (5.5, 0), (12.5, -7)]
    points = [[x + dx, y + dy, z] for x, y in centers for z in zs
              for dx, dy in [(0, 0), (1.6, 0), (-1.6, 0), (0, 1.6), (0, -1.6)]]
    assert not edited.contains(np.array(points)).any()
    assert not edited.contains(np.array([[12.5, 0, z] for z in zs])).any()
    if kind == "driven":
        # Blind Ø8.8 recess remains 2.8 mm deep, with Ø4.2 tool access above it.
        assert not edited.contains(np.array([[16.8, 0, z0 + .1], [16.8, 0, z0 + 2.7]])).any()
        assert edited.contains(np.array([[16.8, 0, z0 + 2.9], [16.8, 0, z1 - .1]])).all()
        edited.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]))
    else:
        assert not edited.contains(np.array([[16.7, 0, z] for z in zs])).any()

    # Bed at Z=0; driven pocket opens UP, so it does not need internal support.
    edited.apply_translation([-edited.bounds.mean(axis=0)[0],
                              -edited.bounds.mean(axis=0)[1], -edited.bounds[0, 2]])
    output = HERE / f"{kind}_horn_spacer_7p5mm_fit_test.stl"
    edited.export(output)
    roundtrip = trimesh.load_mesh(output)
    assert roundtrip.is_volume and roundtrip.body_count == 1
    assert np.allclose(roundtrip.bounds, edited.bounds, atol=1e-5)
    assert np.isclose(roundtrip.volume, edited.volume, rtol=1e-5)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == sha
    return {"file": output.name, "source_v38_sha256": sha,
            "stl_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "bounds_mm": roundtrip.bounds.tolist(), "watertight_single_solid": True,
            "four_bores_clear": True, "head_clearance_preserved": True,
            "added_volume_mm3": expected_added_volume}


if __name__ == "__main__":
    results = [make_spacer(kind, sha) for kind, sha in SOURCES.items()]
    report = {"status": "physical_fit_test_only", "thickness_mm": 7.5,
              "reason": "User reports a real gap with 7 mm spacers and suspects deeper horn seating; trial +0.5 mm per spacer.",
              "physical_fit_verified": False, "published_assembly_unchanged": True,
              "parts": results}
    (HERE / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
