#!/usr/bin/env python3
"""Flatten this run's evidence into Robot Lab artifact names and write both
artifact-list.json and artifact_manifest.json.

Robot Lab artifact names must be flat and unique, so directory separators are
encoded as "__" (run1/result.json -> run1__result.json).  Camera frames are far
too many to list individually, so each run's frames/ directory is bundled as
<run>__frames.tar.gz; every frame's sha256 is already in the matching
frame_index.jsonl, so the imagery stays verifiable file-by-file.
"""
import hashlib, json, os, shutil, tarfile

D = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.join(D, "_staged")
SKIP_DIRS = {"_staged", "preflight_frames"}
SERVER_OWNED = {"experiment.json", "manifest.json", "summary.md"}

os.path.isdir(STAGE) and shutil.rmtree(STAGE)
os.makedirs(STAGE)

entries = []


def stage(src, flat):
    dst = os.path.join(STAGE, flat)
    shutil.copy2(src, dst)
    blob = open(dst, "rb").read()
    entries.append({"artifact": flat,
                    "original_path": os.path.relpath(src, D),
                    "bytes": len(blob),
                    "sha256": hashlib.sha256(blob).hexdigest()})


# 1) bundle each run's frames
for run in ("run1", "run2", "run3", "run4", "dryrun"):
    fdir = os.path.join(D, run, "frames")
    if not os.path.isdir(fdir):
        continue
    tgz = os.path.join(STAGE, f"{run}__frames.tar.gz")
    with tarfile.open(tgz, "w:gz") as tf:
        for cam in sorted(os.listdir(fdir)):
            cdir = os.path.join(fdir, cam)
            if not os.path.isdir(cdir):
                continue
            for fn in sorted(os.listdir(cdir)):
                tf.add(os.path.join(cdir, fn), arcname=f"{cam}/{fn}")
    blob = open(tgz, "rb").read()
    entries.append({"artifact": f"{run}__frames.tar.gz",
                    "original_path": f"{run}/frames/  (bundled, internal paths robot-N/NNNNN.jpg)",
                    "bytes": len(blob),
                    "sha256": hashlib.sha256(blob).hexdigest()})

# 2) every other regular file, flattened
for root, dirs, files in os.walk(D):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS and d != "frames"]
    for fn in sorted(files):
        if fn.startswith(".") or fn in SERVER_OWNED:
            continue
        if fn in ("artifact-list.json", "artifact_manifest.json", "result_for_lab.json"):
            continue
        src = os.path.join(root, fn)
        rel = os.path.relpath(src, D)
        stage(src, rel.replace(os.sep, "__"))

# 3) preflight frames (few) go in individually so the swept-area evidence is
#    directly readable rather than buried in a bundle
pf = os.path.join(D, "preflight_frames")
for fn in sorted(os.listdir(pf)):
    stage(os.path.join(pf, fn), f"preflight_frames__{fn}")

entries.sort(key=lambda e: e["artifact"])
names = [e["artifact"] for e in entries]
assert len(names) == len(set(names)), "duplicate flat artifact name"

json.dump([os.path.join("_staged", n) for n in names],
          open(os.path.join(D, "artifact-list.json"), "w"), indent=1)
json.dump({
    "experiment_id": "881677a009404afda40c6c0d84e8b7d6",
    "note": ('Robot Lab artifact names must be flat, so directory separators are '
             'encoded as "__" (run1/result.json -> run1__result.json). Camera '
             'frames exceed the per-experiment artifact limit, so each run\'s '
             'frames directory is bundled as <run>__frames.tar.gz with internal '
             'paths robot-N/NNNNN.jpg; every frame sha256 is listed in the '
             'matching <run>__frame_index.jsonl.'),
    "artifact_count": len(entries),
    "total_bytes": sum(e["bytes"] for e in entries),
    "artifacts": entries,
}, open(os.path.join(D, "artifact_manifest.json"), "w"), indent=1)
print(f"{len(entries)} artifacts, {sum(e['bytes'] for e in entries)} bytes")
for e in entries:
    print(f"  {e['artifact']}  {e['bytes']}")
