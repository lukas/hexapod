#!/usr/bin/env python3
"""Confirm the L2 hip's 2.11 deg free-rest offset is not an obstruction.

After safe_zero the whole bus reads `torque: 0` -- the servos are limp, so
every joint sits where gravity and friction leave it.  This commands the very
pose safe_zero already reached (all 18 joints at logical zero, the protocol's
own `home_deg`) WITH torque held at the protocol's own `soft_torque` 700, and
reports where each joint actually lands and at what current.  If L2 hip
reaches ~0 at a small current there is no obstruction and the start pose is
established; if it stalls short at a real current, that is a physical
condition and the run does not start.

Bounded: the largest commanded change is L2 hip 2.11 -> 0 deg.  The chassis
stays belly-down and no foot leaves its resting footprint.
"""
import json, os, time, urllib.request, urllib.error
ROBOT = os.environ.get("ROBOT_URL", "http://192.168.4.39:8080")
OWNER = "zerohold-d4908236"
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
                        "n_ok": sum(1 for m in ms if m.get("ok")),
                        "torque": [m.get("torque") for m in ms],
                        "deg": [m["deg"] for m in ms],
                        "current_a": [m["current_a"] for m in ms],
                        "load_pct": [m["load_pct"] for m in ms],
                        "temp_c": [m["temp_c"] for m in ms]}
        except Exception:
            pass
        time.sleep(1.2)
    return None

rec = {"owner": OWNER,
       "why": "L2 hip free-rests at 2.11 deg with torque off; prove it is not blocked",
       "commanded": "18 joints at logical zero (protocol home_deg), soft_torque 700"}
r = post("/api/command-lease/acquire",
         {"owner": OWNER, "ttl_s": 600.0,
          "reason": "hold logical zero to establish d4908236 start pose"}, lease=False)
assert r.get("ok"), r
token = r["token"]
print("lease held")
try:
    rec["before"] = sample()
    print("before j7=%.2f torque=%s" % (rec["before"]["deg"][7],
                                        rec["before"]["torque"][7]))
    ack = post("/api/pose", {"q_deg": [0.0] * 18, "seconds": 3.0,
                             "torque": 700, "limp_after": False})
    rec["pose_ack"] = ack
    print("pose ack:", json.dumps(ack)[:400])
    held = []
    for _ in range(5):
        time.sleep(1.5)
        s = sample()
        if s: held.append(s)
    rec["held"] = held
    last = held[-1]
    w = max((abs(v), j) for j, v in enumerate(last["deg"]))
    rec["worst_held"] = {"joint": w[1], "abs_deg": round(w[0], 3)}
    rec["j7_held_deg"] = last["deg"][7]
    rec["j7_current_a"] = [s["current_a"][7] for s in held]
    rec["j7_load_pct"] = [s["load_pct"][7] for s in held]
    rec["max_current_a"] = max(max(s["current_a"]) for s in held)
    rec["max_temp_c"] = max(max(s["temp_c"]) for s in held)
    rec["torque_on"] = last["torque"]
    rec["all_18"] = all(s["n_ok"] == 18 for s in held)
    print("held j7=%.2f  worst j%d %.2f  j7 A=%s  maxA=%.3f maxT=%d 18/18=%s"
          % (rec["j7_held_deg"], w[1], w[0], rec["j7_current_a"],
             rec["max_current_a"], rec["max_temp_c"], rec["all_18"]))
    print("deg:", [round(v, 2) for v in last["deg"]])
    rec["ok"] = w[0] <= 1.0 and rec["all_18"]
finally:
    print("release:", post("/api/command-lease/release", {"owner": OWNER}))
    json.dump(rec, open("zero_hold_check.json", "w"), indent=1)
