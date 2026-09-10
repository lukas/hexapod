#!/usr/bin/env python3
"""Fetch the sysid CSV + summary this run just wrote, by stamp.

The on-robot runner writes logs/sysid_<name>_<stamp>.csv and _summary.json.
`/api/calibrate`'s `result` field carries a stale checkup report, so the file
is located by listing /api/logs and taking the newest matching pair whose
stamp is at or after the run's own start (passed as an ISO-ish UTC stamp
YYYYmmdd_HHMMSS), never by trusting the poll response.
"""
import json, sys, urllib.request, hashlib, os

ROBOT = os.environ.get("ROBOT_URL", "http://192.168.4.39:8080")
NAME = "l3_belly_rest_radial_shear_hysteresis_repeat6_v1"
floor_stamp, outdir = sys.argv[1], sys.argv[2]

with urllib.request.urlopen(ROBOT + "/api/logs", timeout=30) as r:
    listing = json.loads(r.read().decode())
entries = listing.get("logs") or listing.get("files") or listing
names = [e if isinstance(e, str) else (e.get("name") or e.get("file"))
         for e in entries]
cands = sorted(n for n in names if n and n.startswith(f"sysid_{NAME}_")
               and n.endswith(".csv") and n[len(f"sysid_{NAME}_"):-4] >= floor_stamp)
if not cands:
    print(json.dumps({"ok": False, "error": "no csv at/after " + floor_stamp,
                      "seen": [n for n in names if n and n.startswith("sysid_")][-6:]}))
    sys.exit(1)
csv_name = cands[-1]
stamp = csv_name[len(f"sysid_{NAME}_"):-4]
out = {"ok": True, "stamp": stamp, "files": []}
for fn in (csv_name, f"sysid_{NAME}_{stamp}_summary.json"):
    try:
        with urllib.request.urlopen(ROBOT + "/api/logs/" + fn, timeout=120) as r:
            blob = r.read()
    except Exception as e:
        out["files"].append({"name": fn, "error": str(e)})
        continue
    p = os.path.join(outdir, fn)
    open(p, "wb").write(blob)
    out["files"].append({"name": fn, "path": p, "bytes": len(blob),
                         "sha256": hashlib.sha256(blob).hexdigest()})
print(json.dumps(out, indent=1))
