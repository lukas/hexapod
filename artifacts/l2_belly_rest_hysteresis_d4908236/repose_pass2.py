#!/usr/bin/env python3
"""Second safe_zero pass: L2 hip settled 2.11 deg off zero after pass 1.

Same collision-aware planner, same guards, held lease, and this time the
script WAITS for the demo to stop running before sampling and releasing.
"""
import json, os, time, urllib.request, urllib.error
ROBOT = os.environ.get("ROBOT_URL", "http://192.168.4.39:8080")
OWNER = "repose-d4908236-p2"
token = ""

def get(p, t=30.0):
    with urllib.request.urlopen(ROBOT + p, timeout=t) as r:
        return json.loads(r.read().decode())

def post(p, body=None, t=60.0, lease=True):
    h = {"Content-Type": "application/json", "X-Hexapod-Controller": OWNER}
    if lease and token: h["X-Hexapod-Command-Lease"] = token
    req = urllib.request.Request(ROBOT + p, data=json.dumps(body or {}).encode(),
                                 headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=t) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try: return {"_http": e.code, **json.loads(raw or "{}")}
        except ValueError: return {"_http": e.code, "raw": raw[:400]}

def sample(tries=8):
    for _ in range(tries):
        try:
            d = get("/api/status")
            ms = sorted(d["motors"], key=lambda m: m["joint"])
            if len(ms) == 18:
                return {"t": time.time(), "armed": d.get("armed"),
                        "mode": d.get("mode"),
                        "n_ok": sum(1 for m in ms if m.get("ok")),
                        "deg": [m["deg"] for m in ms],
                        "current_a": [m["current_a"] for m in ms],
                        "load_pct": [m["load_pct"] for m in ms],
                        "temp_c": [m["temp_c"] for m in ms]}
        except Exception:
            pass
        time.sleep(1.5)
    return None

rec = {"owner": OWNER, "note": "second pass; pass 1 left j7 at 2.11 deg"}
r = post("/api/command-lease/acquire",
         {"owner": OWNER, "ttl_s": 600.0,
          "reason": "tighten belly_rest_logical_zero before d4908236"}, lease=False)
assert r.get("ok"), r
token = r["token"]
print("lease held")
try:
    b = sample(); rec["before"] = b
    print("before worst:", max((abs(v), j) for j, v in enumerate(b["deg"])))
    run = post("/api/safe_zero", {})
    rec["run_ack"] = {"ok": run.get("ok"), "started": run.get("started"),
                      "plan": run.get("plan")}
    print("started:", run.get("ok"), run.get("started"))
    # wait for the demo to actually stop running
    t0 = time.time()
    while time.time() - t0 < 60:
        time.sleep(1.0)
        try:
            st = get("/api/calibrate", timeout=15.0)
        except Exception:
            continue
        running = bool((st.get("demo") or {}).get("running"))
        if not running:
            break
    rec["wait_s"] = round(time.time() - t0, 1)
    print(f"demo stopped after {rec['wait_s']}s")
    time.sleep(2.0)
    after = [s for s in (sample(), (time.sleep(1.5) or sample()),
                         (time.sleep(1.5) or sample())) if s]
    rec["after"] = after
    w = max((abs(v), j) for j, v in enumerate(after[-1]["deg"]))
    rec["worst_after"] = {"joint": w[1], "abs_deg": round(w[0], 3)}
    rec["max_current_a"] = max(max(s["current_a"]) for s in after)
    rec["max_temp_c"] = max(max(s["temp_c"]) for s in after)
    rec["all_18"] = all(s["n_ok"] == 18 for s in after)
    print(f"after worst j{w[1]} {w[0]:.2f} deg  maxA={rec['max_current_a']} "
          f"maxT={rec['max_temp_c']} 18/18={rec['all_18']}")
    print("deg:", [round(v, 2) for v in after[-1]["deg"]])
finally:
    print("release:", post("/api/command-lease/release", {"owner": OWNER}))
    json.dump(rec, open("repose_pass2.json", "w"), indent=1)
