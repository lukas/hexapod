"""Publish a NEW immutable version to both hubs, keeping the default unchanged.

BUILDVIZ_API_KEY=... uv run python <this file> v38
"""
import base64
import json
import os
import sys
import urllib.request

import make_variant as design

version = sys.argv[1]
assert version.startswith("v") and version[1:].isdigit()
out = design.OUT
checks = json.loads((out/"checks.json").read_text())
assert checks["inner_joint"]["count_per_socket"] == 4 and not checks["kinematic_changes"]
scene = json.loads((out/"scene.json").read_text())
assets = [{"meshId":m["id"],"ext":"stl","data":base64.b64encode((out/m["url"]).read_bytes()).decode()}
          for m in scene["meshes"] if not m["url"].startswith("/")]
assert len(assets) == 1 and assets[0]["meshId"] == "stl:tibia_ovh_socket"
payload = {"buildId":"prototype_sts3215/premade-chorn-56","branch":"main","version":version,
    "setDefault":False,"scene":scene,"assets":assets,"designSpec":(out/"design_spec.yaml").read_text(),
    "message":design.MESSAGE,"reason":design.REASON}


def call(url,data=None):
    req = urllib.request.Request(url,data=json.dumps(data).encode() if data is not None else None,
        headers={"Content-Type":"application/json","X-API-Key":os.environ["BUILDVIZ_API_KEY"]})
    with urllib.request.urlopen(req,timeout=55) as response: return json.load(response)


receipt = {}
for label,host in (("local","http://127.0.0.1:5183"),("cloud","https://buildviz.cwd1f0-new-cluster.coreweave.app")):
    assert call(host+"/__buildviz/status")["service"] == "buildviz-hub"
    result = call(host+"/__buildviz/push",payload)
    assert result.get("isNewVersion"), result
    receipt[label] = result
    (out/(version+"-publish-receipt.json")).write_text(json.dumps(receipt,indent=2)+"\n")
    print(label,json.dumps({k:result.get(k) for k in ("ok","version","isNewVersion","defaultVersion","uploads","warnings")}),flush=True)
