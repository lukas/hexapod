#!/usr/bin/env python3
"""Documented re-pose recovery before experiment 376bea38.

L1 was left at hip -50.54 / knee 34.45 (limp) when the plan's own
api_errors_row interlock halted attempt 1 at 04:30:29Z.  The
plan declares that start pose, and the guarded runner's own start-pose gate
(3 deg) correctly refuses until it is restored.  This does NOT widen that
gate: it restores the pose through the robot's own collision-aware
`/api/safe_zero` planner, which keeps feet clear of the belly-down ground
plane, refuses on a crossing or an untrustworthy zero frame, and limps the
moment a servo reports it is not turning or is fighting a force.

Zero frame is NOT touched (`zero_frame_change: false` in the plan): this is a
re-pose, never `/api/set_zero`.
"""
import json, os, sys, time, urllib.request, urllib.error

ROBOT = os.environ.get("ROBOT_URL", "http://192.168.4.39:8080")
OWNER = "repose-376bea38"
OUT = os.environ.get("OUT_DIR", ".")
TOL_DEG = 1.0
token = ""


def get(p, t=25.0):
    with urllib.request.urlopen(ROBOT + p, timeout=t) as r:
        return json.loads(r.read().decode())


def post(p, body=None, t=60.0, lease=True):
    h = {"Content-Type": "application/json", "X-Hexapod-Controller": OWNER}
    if lease and token:
        h["X-Hexapod-Command-Lease"] = token
    req = urllib.request.Request(ROBOT + p, data=json.dumps(body or {}).encode(),
                                 headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=t) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return {"_http": e.code, **json.loads(raw or "{}")}
        except ValueError:
            return {"_http": e.code, "raw": raw[:400]}


def sample():
    d = get("/api/status")
    ms = sorted(d["motors"], key=lambda m: m["joint"])
    return {"t": time.time(), "armed": d.get("armed"), "mode": d.get("mode"),
            "n_ok": sum(1 for m in ms if m.get("ok")),
            "deg": [m["deg"] for m in ms],
            "current_a": [m["current_a"] for m in ms],
            "load_pct": [m["load_pct"] for m in ms],
            "temp_c": [m["temp_c"] for m in ms]}


def worst(s):
    return max((abs(float(d)), i) for i, d in enumerate(s["deg"]))


def main():
    global token
    rec = {"owner": OWNER, "robot": ROBOT, "tol_deg": TOL_DEG}

    before = [sample() for _ in range(3) if not time.sleep(1.0)]
    rec["before"] = before
    w = worst(before[-1])
    print(f"before: worst joint {w[1]} at {w[0]:.2f} deg, "
          f"18/18={all(s['n_ok']==18 for s in before)}")
    if w[0] <= TOL_DEG:
        print("already at logical zero -- nothing to do")
        rec["action"] = "none"
        json.dump(rec, open(f"{OUT}/repose_to_zero.json", "w"), indent=1)
        return 0

    r = post("/api/command-lease/acquire",
             {"owner": OWNER, "ttl_s": 600.0,
              "reason": "restore belly_rest_logical_zero after the attempt-1 interlock stop"},
             lease=False)
    if not r.get("ok"):
        print(f"!! lease refused: {r}")
        rec["lease"] = r
        json.dump(rec, open(f"{OUT}/repose_to_zero.json", "w"), indent=1)
        return 2
    token = r["token"]
    rec["lease"] = {"ok": True, "owner": OWNER}
    print("   command lease held")

    try:
        dry = post("/api/safe_zero", {"dry_run": True})
        rec["dry_run"] = dry
        print("   dry_run ->", json.dumps(dry)[:1200])
        if dry.get("_http") or not dry.get("ok", True):
            print("!! planner refused -- not commanding")
            return 3
        if os.environ.get("PLAN_ONLY") == "1":
            rec["action"] = "plan_only"
            return 0

        t0 = time.time()
        run = post("/api/safe_zero", {}, t=180.0)
        rec["run"] = run
        rec["elapsed_s"] = round(time.time() - t0, 2)
        print(f"   safe_zero -> {json.dumps(run)[:900]} ({rec['elapsed_s']}s)")

        after = []
        for _ in range(3):
            time.sleep(1.5)
            after.append(sample())
        rec["after"] = after
        w2 = worst(after[-1])
        rec["worst_after"] = {"joint": w2[1], "abs_deg": round(w2[0], 3)}
        rec["max_current_a_after"] = max(max(s["current_a"]) for s in after)
        rec["max_temp_c_after"] = max(max(s["temp_c"]) for s in after)
        print(f"after: worst joint {w2[1]} at {w2[0]:.2f} deg "
              f"(tol {TOL_DEG}), maxA={rec['max_current_a_after']}, "
              f"maxT={rec['max_temp_c_after']}")
        rec["ok"] = w2[0] <= TOL_DEG and all(s["n_ok"] == 18 for s in after)
        return 0 if rec["ok"] else 4
    finally:
        try:
            rel = post("/api/command-lease/release", {"owner": OWNER})
            rec["lease_release"] = rel
            print("   lease released:", json.dumps(rel)[:200])
        except Exception as e:
            rec["lease_release"] = {"error": str(e)}
        json.dump(rec, open(f"{OUT}/repose_to_zero.json", "w"), indent=1)


if __name__ == "__main__":
    sys.exit(main())
