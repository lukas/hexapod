#!/usr/bin/env python3
"""Sample the chassis tag's world pose to characterise its at-rest noise.

Bus-free: /api/pose-state is served by the local camera server from its own
AprilTag pass; it never touches the robot's servo bus.
"""
import json, sys, time, urllib.request
CAM = "http://127.0.0.1:8766"
BODY_TAG = "0"
n = int(sys.argv[1]); out = sys.argv[2]
rows = []
for i in range(n):
    try:
        with urllib.request.urlopen(CAM + "/api/pose-state", timeout=8) as r:
            d = json.loads(r.read().decode())
        m = (d["camera_pose"].get("markers") or {}).get(BODY_TAG)
        if m and m.get("status") == "tracked":
            rows.append({"t": time.time(),
                         "x": m["position_mm"]["x"], "y": m["position_mm"]["y"],
                         "yaw": (m.get("rotation_degrees") or {}).get("yaw"),
                         "err95_mm": (m.get("error_95_estimate") or {}).get("position_mm"),
                         "cams": m.get("camera_indices")})
        else:
            rows.append({"t": time.time(), "missing": True})
    except Exception as e:
        rows.append({"t": time.time(), "error": str(e)})
    time.sleep(1.0)
json.dump(rows, open(out, "w"), indent=1)
ok = [r for r in rows if "x" in r]
print(f"samples={len(rows)} tracked={len(ok)}")
if len(ok) >= 2:
    xs = [r["x"] for r in ok]; ys = [r["y"] for r in ok]
    yaws = [r["yaw"] for r in ok if r["yaw"] is not None]
    import statistics as st
    print(f"x  mean {st.mean(xs):8.2f} sd {st.pstdev(xs):6.2f} ptp {max(xs)-min(xs):7.2f} mm")
    print(f"y  mean {st.mean(ys):8.2f} sd {st.pstdev(ys):6.2f} ptp {max(ys)-min(ys):7.2f} mm")
    if yaws:
        print(f"yaw mean {st.mean(yaws):7.2f} sd {st.pstdev(yaws):6.2f} ptp {max(yaws)-min(yaws):7.2f} deg")
    d = [((r["x"]-st.mean(xs))**2 + (r["y"]-st.mean(ys))**2)**0.5 for r in ok]
    print(f"radial offset from mean: max {max(d):.2f} mm")
