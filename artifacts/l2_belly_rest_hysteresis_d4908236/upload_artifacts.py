#!/usr/bin/env python3
"""Upload evidence files to the Robot Lab BEFORE sealing.

The Lab's PUT is create-only (409 on an existing name) and the seal freezes
the manifest, so every artifact has to land first.  The bearer token is read
from the environment and never appears in argv or in any output.
"""
import json, os, sys, mimetypes, urllib.request, urllib.error

BASE = os.environ.get("LAB_BASE", "https://robot-lab.cwd1f0-new-cluster.coreweave.app")
TOKEN = os.environ["HEXAPOD_LAB_TOKEN"]
EXP = sys.argv[1]


def put(name: str, path: str) -> dict:
    data = open(path, "rb").read()
    ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
    req = urllib.request.Request(
        f"{BASE}/api/experiments/{EXP}/artifacts/{name}",
        data=data, method="PUT",
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return {"name": name, "code": r.status, "bytes": len(data)}
    except urllib.error.HTTPError as e:
        return {"name": name, "code": e.code, "bytes": len(data),
                "error": e.read().decode()[:200]}


def main():
    plan = json.load(open(sys.argv[2]))   # [{"name":..., "path":...}, ...]
    out = []
    for item in plan:
        r = put(item["name"], item["path"])
        out.append(r)
        print(f"{r['code']:>3} {r['bytes']:>9} {r['name']}"
              + (f"  {r.get('error','')}" if r["code"] >= 300 else ""))
    ok = sum(1 for r in out if r["code"] in (200, 201))
    print(f"-- {ok}/{len(out)} uploaded")
    json.dump(out, open("upload_report.json", "w"), indent=1)
    return 0 if ok == len(out) else 1


if __name__ == "__main__":
    sys.exit(main())
