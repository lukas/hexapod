#!/usr/bin/env python3
"""Live demonstration that a guarded lease excludes the :8898 hub.

Zero motion by construction: the point is that the stand/lower commands are
REFUSED before they reach the bus. Pose is read before and after to prove it.
"""
import json, time, urllib.request, urllib.error

ROBOT = "http://192.168.4.39:8080"
HUB = "http://127.0.0.1:8898"
out = {"steps": []}


def call(base, path, body=None, method="POST", headers=None, timeout=25.0):
    data = None
    hdr = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode()
        hdr["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=data, headers=hdr,
                                 method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw or "{}")
        except ValueError:
            return e.code, {"raw": raw[:300]}
    except Exception as e:
        return None, {"transport_error": str(e)}


def step(name, **kw):
    kw["step"] = name
    kw["t"] = time.time()
    out["steps"].append(kw)
    print(f"-- {name}: {json.dumps({k: v for k, v in kw.items() if k not in ('t',)})[:400]}",
          flush=True)
    return kw


def pose():
    _, s = call(ROBOT, "/api/status", method="GET")
    return {"activity": s.get("mode"), "armed": s.get("armed"),
            "status": s.get("status"), "live": len(s.get("live_ids") or []),
            "deg": [m.get("deg") for m in (s.get("motors") or [])]}


def last_error_ts():
    _, e = call(ROBOT, "/api/errors", method="GET")
    rows = e.get("errors") or []
    return max((str(r.get("ts") or "") for r in rows), default="")


before = pose(); step("pose_before", pose=before)
err_before = last_error_ts(); step("errors_before", last_ts=err_before)

code, free = call(ROBOT, "/api/command-lease", method="GET")
step("lease_before", code=code, body=free)

code, got = call(ROBOT, "/api/command-lease/acquire",
                 {"owner": "guarded-runner-413d5402", "ttl_s": 120,
                  "reason": "exclusivity demonstration (no motion)"})
step("acquire", code=code, owner=got.get("lease", {}).get("owner"),
     ok=got.get("ok"))
token = got.get("token")
assert token, got

# THE RECORDED GAP: the :8898 hub commanding stand/lower mid-window.
for path in ("/api/rl/stand", "/api/rl/lower", "/api/rl/walk"):
    code, body = call(HUB, path, {})
    step(f"hub{path}", code=code, error_code=body.get("code"),
         error=str(body.get("error"))[:160])

# Same, straight at the robot, and a raw joint line.
for path in ("/api/rl/stand", "/api/standup", "/api/sysid/run", "/api/pose"):
    code, body = call(ROBOT, path, {})
    step(f"direct{path}", code=code, error_code=body.get("code"),
         error=str(body.get("error"))[:160])
code, body = call(ROBOT, "/cmd", None, headers={"Content-Type": "text/plain"})
req = urllib.request.Request(ROBOT + "/cmd", data=b"J 0 5 0", method="POST")
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        code, raw = r.status, r.read().decode()
except urllib.error.HTTPError as e:
    code, raw = e.code, e.read().decode()
step("direct/cmd J 0 5 0", code=code, body=raw[:200])

# The lease holder itself is NOT blocked (validator rejects the empty body).
code, body = call(ROBOT, "/api/sysid/run", {},
                  headers={"X-Hexapod-Command-Lease": token})
step("holder/api/sysid/run", code=code, error=str(body.get("error"))[:160],
     lease_blocked=body.get("code") == "command_lease_held")

# The abort path must answer ANY controller while the lease is held.
code, body = call(ROBOT, "/api/rl/stop", {})
step("abort/api/rl/stop", code=code, ok=body.get("ok"),
     lease_blocked=body.get("code") == "command_lease_held")
req = urllib.request.Request(ROBOT + "/cmd", data=b"X", method="POST")
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        code, raw = r.status, r.read().decode()
except urllib.error.HTTPError as e:
    code, raw = e.code, e.read().decode()
step("abort/cmd X", code=code, body=raw[:120])

code, held = call(ROBOT, "/api/command-lease", method="GET")
step("lease_during", code=code, body=held)

code, rel = call(ROBOT, "/api/command-lease/release", {"command_lease": token})
step("release", code=code, body=rel)
code, after_free = call(ROBOT, "/api/command-lease", method="GET")
step("lease_after", code=code, held=after_free.get("held"))

after = pose(); step("pose_after", pose=after)
err_after = last_error_ts(); step("errors_after", last_ts=err_after)

_, cmds = call(ROBOT, "/api/commands?limit=40", method="GET")
out["journal_tail"] = [
    {k: e.get(k) for k in ("ts", "path", "controller", "peer", "code")}
    for e in (cmds.get("entries") or cmds.get("commands") or [])][-20:]

moved = [i for i, (a, b) in enumerate(zip(before["deg"], after["deg"]))
         if a is not None and b is not None and abs(a - b) > 0.5]
out["verdict"] = {
    "joints_moved_gt_0p5deg": moved,
    "no_motion": not moved,
    "no_new_error_row": err_after == err_before,
    "activity_before": before["activity"], "activity_after": after["activity"],
}
json.dump(out, open("exclusive_command_path_demo.json", "w"), indent=1)
print(json.dumps(out["verdict"], indent=1))
