"""Publish a NEW immutable revision to both existing BuildViz hubs.

Usage: BUILDVIZ_API_KEY=... uv run python publish.py v35
No overwrite flags, pruning, default promotion, or server deployment.
"""
import base64
import json
import os
from pathlib import Path
import sys
import urllib.request

HERE=Path(__file__).resolve().parent
OUT=HERE/"output"
VERSION=sys.argv[1]
assert VERSION.startswith("v") and VERSION[1:].isdigit()
BUILD="prototype_sts3215/premade-chorn-56"
MESSAGE=("Repair v34 knee caps: two supported M3x8 face screws, compact upper-inboard mount, "
         "and side-loaded M3 nuts under solid retaining roofs. Matching cap/femur pair; all other v34 meshes unchanged.")
REASON=("v34 claimed to restore an underside insert attachment but its cap lacks the receiving boss, leaving only one functioning fastening. "
        "Replace that missing connection with an accessible face screw and matching femur lug. Both nuts load from the ends beneath 3mm retaining roofs "
        "so screw tension is carried by the femur, not merely the removable cap. A straight-across draft interfered with the chassis at -105deg hip; "
        "the compact upper-corner station preserves the sampled -110..30deg hip and -30..20deg knee ranges. "
        "Requires reprinting both mating pieces; physical fit, strength and fatigue remain untested. The six short hip-C receiver insert pockets are unchanged.")


def call(url,method="GET",data=None):
    req=urllib.request.Request(url,method=method,data=None if data is None else json.dumps(data).encode(),
        headers={"X-API-Key":os.environ["BUILDVIZ_API_KEY"],"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=55) as response:return json.load(response)


report=json.loads((OUT/"checks.json").read_text())
assert not report["authored_pose_regressions"] and report["motion"]["hip_deg"]==[-110,30]
scene=json.loads((OUT/"scene.json").read_text())
assets=[]
for mesh in scene["meshes"]:
    if not mesh["url"].startswith("/"):
        assets.append({"meshId":mesh["id"],"ext":"stl","data":base64.b64encode((OUT/mesh["url"]).read_bytes()).decode()})
assert len(assets)==4
payload={"buildId":BUILD,"branch":"main","version":VERSION,"setDefault":False,
    "scene":scene,"designSpec":(OUT/"design_spec.yaml").read_text(),"assets":assets,
    "message":MESSAGE,"reason":REASON}
results={}
for label,hub in (("local","http://127.0.0.1:5183"),("cloud","https://buildviz.cwd1f0-new-cluster.coreweave.app")):
    status=call(hub+"/__buildviz/status")
    assert status["service"]=="buildviz-hub"
    result=call(hub+"/__buildviz/push","POST",payload)
    results[label]=result
    (OUT/(VERSION+"-publish-receipt.json")).write_text(json.dumps(results,indent=2)+"\n")
    print(label,json.dumps(result),flush=True)
