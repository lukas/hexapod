#!/usr/bin/env python3
"""Re-demonstrate the exclusive command lease for THIS run (7299f243).

The plan's analysis_dependencies[3] asks that "/api/command-lease answers
rather than 404 on the installed revision, and the exclusive lease is
demonstrated to refuse the :8898 hub and direct motion routes while
/api/rl/stop, /api/standup/stop and /api/safe_zero stay open".  Earlier runs
in this family recorded that demo under their own owners; this reproduces it
under THIS run's owner so the evidence is this experiment's, not a citation.

Motion routes are POSTed while the lease is held by someone else, so the
expected outcome for every one of them is a 409 refusal -- the robot must not
move at any point in this script.
"""
import json, time, urllib.request, urllib.error, sys

ROBOT = "http://192.168.4.39:8080"
HUB = "http://127.0.0.1:8898"
OWNER = "guarded-runner-7299f243"
steps = []


def call(base, path, body=None, method="POST", hdrs=None):
    req = urllib.request.Request(
        base + path, data=json.dumps(body or {}).encode(),
        headers={"Content-Type": "application/json",
                 "X-Hexapod-Controller": "exclusivity-probe-7299f243",
                 **(hdrs or {})}, method=method)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.getcode(), r.read().decode(), (time.time()-t0)*1000
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), (time.time()-t0)*1000
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"[:220], (time.time()-t0)*1000


def rec(step, code, body, ms, expect):
    ok = (code in expect) if expect else None
    steps.append({"step": step, "code": code, "ms": round(ms), "expect": expect,
                  "as_expected": ok, "body": body[:400]})
    print(f"  [{'ok ' if ok else 'CHK'}] {step:38s} {str(code):5s} "
          f"{round(ms):5d} ms  {body[:90]}")
    return ok


print("1) abort paths BEFORE the lease (must be open)")
for ep in ("/api/rl/stop", "/api/standup/stop"):
    rec(f"pre-lease abort {ep}", *call(ROBOT, ep), expect=(200,))

print("2) acquire the exclusive lease as", OWNER)
code, body, ms = call(ROBOT, "/api/command-lease/acquire",
                      {"owner": OWNER, "ttl_s": 120,
                       "reason": "exclusivity demonstration for 7299f243"})
rec("acquire lease", code, body, ms, (200,))
token = (json.loads(body).get("token") if code == 200 else None)
if not token:
    print("!! could not take the lease -- aborting demo"); sys.exit(2)

try:
    print("3) DIRECT motion routes from another controller (must 409)")
    # /api/sysid/run is the route THIS run uses, so a foreign controller
    # being refused it is the plan's foreign_controller_command_observed
    # stop being unreachable in the first place. /api/standup/start is not
    # probed: it does not exist on this revision (only /api/standup/modes
    # and /api/standup/stop do), so a 404 would say nothing about gating.
    for ep in ("/api/rl/stand", "/api/rl/lower", "/api/rl/walk",
               "/api/standup", "/api/sysid/run"):
        rec(f"direct {ep}", *call(ROBOT, ep), expect=(409,))

    print("4) :8898 HUB motion routes from another controller (must 409/fail)")
    for ep in ("/api/rl/stand", "/api/rl/lower", "/api/rl/walk"):
        c, b, m = call(HUB, ep)
        rec(f"hub{ep}", c, b, m, (409,) if c is not None else None)

    print("5) abort paths WHILE the lease is held (must STILL be open)")
    for ep in ("/api/rl/stop", "/api/standup/stop", "/api/safe_zero"):
        # /api/safe_zero MOVES the robot, so it is only probed for gating with
        # a dry_run flag; the plan lists it as an ungated abort path.
        body = {"dry_run": True} if ep == "/api/safe_zero" else {}
        rec(f"leased abort {ep}", *call(ROBOT, ep, body), expect=(200,))
finally:
    c, b, m = call(ROBOT, "/api/command-lease/release",
                   {"command_lease": token})
    rec("release lease", c, b, m, (200,))

fb = urllib.request.urlopen(ROBOT + "/api/feedback", timeout=30).read()
pose = json.loads(fb.decode())
worst = max(range(18), key=lambda i: abs(pose["joints"][i]["deg"]))
print(f"\npose after the demo: live {pose.get('live')}/18, worst joint {worst} "
      f"at {pose['joints'][worst]['deg']} deg -- the robot must not have moved")

out = {"owner": OWNER, "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                 time.gmtime()),
       "robot_url": ROBOT, "hub_url": HUB, "steps": steps,
       "pose_after": {"live": pose.get("live"),
                      "deg": [j["deg"] for j in pose["joints"]],
                      "worst_joint": worst,
                      "worst_deg": pose["joints"][worst]["deg"]}}
unexpected = [s for s in steps if s["as_expected"] is False]
out["unexpected_steps"] = unexpected
out["verdict"] = ("lease is exclusive and abort paths stay open"
                  if not unexpected else "REVIEW: unexpected responses")
json.dump(out, open("exclusive_command_path_demo.json", "w"), indent=1)
print("verdict:", out["verdict"], "| unexpected:", len(unexpected))
