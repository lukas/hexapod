#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Copy every build/version from the local BuildViz hub state to a remote hub.

Reads ~/.buildviz/registry.json (registered + pushed builds) and the local
cache, then POSTs each build@version to the remote hub's /__buildviz/push with
mesh bytes attached (assets[]), so the remote copies are fully self-contained.

Usage:
    uv run deploy/coreweave/migrate_local_builds.py https://buildviz.example.com [--dry-run]
"""

import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

API_KEY = os.environ.get("BUILDVIZ_API_KEY", "")

BUILDVIZ_HOME = Path.home() / ".buildviz"
CACHE = BUILDVIZ_HOME / "cache"
ASSETS = CACHE / "_assets"
MAX_UPLOAD_BYTES = 256 * 1024 * 1024

# Bundled sample builds already served by the remote hub's own checkout.
SKIP_IDS = {
    "hexapod-2", "hexapod-collision-chassis", "hexapod-collision-femur",
    "hexapod-fresh", "hexapod-motion-demo", "hexapod-prototype",
}


def resolve_mesh_file(url: str, scene_dir: Path) -> Path | None:
    if url.startswith(("http://", "https://")):
        return None  # already reachable from anywhere
    if url.startswith("/builds/_assets/"):
        candidate = ASSETS / Path(url).name
        return candidate if candidate.exists() else None
    if url.startswith("/"):
        return None  # other hub-rooted URL; leave as-is (warn later)
    candidate = scene_dir / url.lstrip("./")
    return candidate if candidate.exists() else None


def collect_assets(scene: dict, scene_dir: Path) -> tuple[list[dict], list[str]]:
    assets, unresolved = [], []
    for mesh in scene.get("meshes", []):
        url = mesh.get("url", "")
        mesh_id = mesh.get("id", "")
        if not url or not mesh_id:
            continue
        file = resolve_mesh_file(url, scene_dir)
        if file is None:
            if not url.startswith(("http://", "https://")):
                unresolved.append(url)
            continue
        assets.append({
            "meshId": mesh_id,
            "data": base64.b64encode(file.read_bytes()).decode(),
            "ext": file.suffix.lstrip(".") or "stl",
        })
    return assets, unresolved


def push(base_url: str, payload: dict) -> dict:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    req = urllib.request.Request(
        f"{base_url}/__buildviz/push",
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as response:
        return json.load(response)


def push_version(base_url: str, build_id: str, name: str | None, version: str,
                 scene_dir: Path, set_default: bool, dry_run: bool) -> None:
    scene_path = scene_dir / "scene.json"
    scene = json.loads(scene_path.read_text())
    assets, unresolved = collect_assets(scene, scene_dir)
    spec_path = scene_dir / "design_spec.yaml"
    design_spec = spec_path.read_text() if spec_path.exists() else None

    label = f"{build_id}@{version}"
    total_kb = sum(len(a["data"]) for a in assets) * 3 // 4 // 1024
    print(f"  {label}: {len(assets)} mesh file(s), ~{total_kb} KB"
          + (" [default]" if set_default else "")
          + (f"  UNRESOLVED: {unresolved}" if unresolved else ""))
    if dry_run:
        return

    payload = {
        "buildId": build_id,
        "version": version,
        "scene": scene,
        "setDefault": set_default,
        "maxUploadBytes": MAX_UPLOAD_BYTES,
    }
    if name:
        payload["name"] = name
    if design_spec:
        payload["designSpec"] = design_spec
    if assets:
        payload["assets"] = assets
    result = push(base_url, payload)
    print(f"    -> {result.get('summary', 'ok')}")


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry_run = "--dry-run" in sys.argv
    only: str | None = None
    if "--only" in args:
        index = args.index("--only")
        try:
            only = args[index + 1]
        except IndexError:
            sys.exit("--only requires a build id (e.g. --only myproj/widget)")
        del args[index:index + 2]
    if not args:
        sys.exit("usage: migrate_local_builds.py <remote-hub-base-url> [--dry-run] [--only <buildId>]")
    base_url = args[0].rstrip("/")

    status = json.load(urllib.request.urlopen(f"{base_url}/__buildviz/status", timeout=30))
    assert status.get("service") == "buildviz-hub", f"not a BuildViz hub at {base_url}"
    print(f"Remote hub verified at {base_url}\n")

    registry = json.loads((BUILDVIZ_HOME / "registry.json").read_text())
    for entry in registry.get("builds", []):
        build_id = entry["id"]
        if only is not None and build_id != only:
            continue
        if build_id in SKIP_IDS:
            continue
        build_dir = Path(entry["buildDir"])
        if not (build_dir / "scene.json").exists():
            print(f"  {build_id}: SKIP (source dir vanished: {build_dir})")
            continue

        name = entry.get("name")
        meta_path = build_dir / "meta.json"
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        default_version = meta.get("defaultVersion", "main")
        version_names = [v["name"] for v in meta.get("versions", [])] or ["main"]
        if default_version not in version_names:
            version_names.append(default_version)

        print(f"{build_id} ({len(version_names)} version(s), default {default_version})")
        # Push the default version last so intermediate pushes never leave a
        # non-default version looking newest.
        ordered = [v for v in version_names if v != default_version] + [default_version]
        for version in ordered:
            scene_dir = build_dir if version == default_version else build_dir / "versions" / version
            if not (scene_dir / "scene.json").exists():
                # The default version lives at the build root; non-default under
                # versions/. A missing dir means a pruned/incomplete version.
                print(f"  {build_id}@{version}: SKIP (no scene.json at {scene_dir})")
                continue
            push_version(base_url, build_id, name, version, scene_dir,
                         set_default=(version == default_version), dry_run=dry_run)
    print("\nDone.")


if __name__ == "__main__":
    main()
