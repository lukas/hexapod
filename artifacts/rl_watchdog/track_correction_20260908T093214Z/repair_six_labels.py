import argparse, hashlib, json, os, sys
from pathlib import Path
from datetime import datetime, timezone
os.chdir("/workspace/hexapod/hexapod_walker/prototype_sts3215")
sys.path.insert(0, str(Path("rl_move/orchestrator").resolve()))
import launch_run as lr
import tracks
import wandb
base="cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-"
names=[base+arm+suffix for arm in ("c1","offctrl") for suffix in ("","-torqueretain","-narrowhead")]
api=wandb.Api()
receipt={"at_utc":datetime.now(timezone.utc).isoformat(),"reason":"Correct six known scratch-walking source/descendant labels to walkcurr; preserve training commands and results.","runs":[]}
for name in names:
    candidates=[e for e in lr.load_ledger() if e.get("run")==name and (e.get("wandb_id") or e.get("checks",{}).get("pid"))]
    if not candidates: raise RuntimeError("Missing executed record: "+name)
    e=candidates[-1]
    if e.get("track") not in ("joystick","walkcurr"): raise RuntimeError("Unexpected track")
    r=api.run(tracks.project_path()+"/"+e["wandb_id"])
    prior=list(r.tags or [])
    record={"run":name,"created":e["created"],"wandb_id":e["wandb_id"],"track_before":e.get("track"),"tags_before":prior,"command_sha256":hashlib.sha256(e.get("command","").encode()).hexdigest()}
    if e.get("track")!="walkcurr":
        correction={"from":e.get("track"),"to":"walkcurr","at_utc":receipt["at_utc"],"reason":"This teacher-free scratch recipe belongs to the walkcurr campaign; inherited source label was wrong. Original launch command/tags remain in historical command provenance."}
        rc=lr.cmd_update(argparse.Namespace(run=name,created=e["created"],create=False,set=["track=walkcurr","track_correction="+json.dumps(correction)]))
        if rc: raise RuntimeError("Sanctioned update failed")
    desired=[x for x in prior if not x.startswith("track:")]+["track:walkcurr"]
    if prior!=desired:
        r.tags=desired
        r.update()
    api.flush()
    after=api.run(tracks.project_path()+"/"+e["wandb_id"])
    record["tags_after"]=list(after.tags or [])
    entry=[x for x in lr.load_ledger() if x.get("run")==name and x.get("created")==e["created"]][-1]
    record["track_after"]=entry["track"]
    assert hashlib.sha256(entry.get("command","").encode()).hexdigest()==record["command_sha256"]
    assert record["track_after"]=="walkcurr" and "track:walkcurr" in record["tags_after"] and "track:joystick" not in record["tags_after"]
    receipt["runs"].append(record)
Path("/tmp/hexapod-track-correction-20260908T093214Z.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps(receipt))
