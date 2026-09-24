"""Lengthen the knee servo box 6 mm and restore two mid-height self-tappers.

No offset fastening lug, nuts, or nut-loading slots. Frozen v35 scene is the
revision baseline; v34's pre-lug meshes supply the unmodified cradle features.
Run with uv run python <this file> from the repository root.
"""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import trimesh
import yaml

HERE=Path(__file__).resolve().parent
OUT=HERE/"output"
_previous_spec=importlib.util.spec_from_file_location("knee_cap_v35_source",HERE.parent/"knee_cap_two_point/make_variant.py")
previous=importlib.util.module_from_spec(_previous_spec)
_previous_spec.loader.exec_module(previous)
g,v7=previous.g,previous.v7
BODY,CAP=previous.BODY_KEY,previous.CAP_KEY
EXTEND=6.0
OLD_KNEE_X=90.0
KNEE_X=OLD_KNEE_X+EXTEND
FACE,SEAT,OUTER=16.9,18.9,21.9
CENTRES=[(-27.2,17.15),(27.2,17.15)]
PILOT_D,PILOT_DEPTH=2.5,8.0
SCREW_D,SCREW_LENGTH,TIP=3.0,8.0,1.0
MESSAGE="Simplify knee servo box: 6 mm longer receiver end, two mid-height 3x8 self-tapping cap screws, no offset lug or captive nuts. Move knee and downstream assembly/pivot 6 mm outward."
REASON=("User rejected v35's offset upper-corner lug and end-loaded nuts. Lengthen the box at its hip-bracket end so the original paired mid-height cap screws fit in solid walls beyond the metal web. "
        "Use self-tapping screws directly in 2.5 mm pilot holes. This intentionally increases hip-to-knee length from 90 to 96 mm; all knee/downstream transforms and knee joint origins are updated together. "
        "Cap and femur must be reprinted as a matching pair. Self-tapped plastic trades away metal-thread cycle life; physical fit and screw torque/strength remain untested. Front bracket insert pockets are unchanged.")


def trans(xyz):
    T=np.eye(4);T[:3,3]=xyz;return T


def placed(m,T):return previous.transformed(m,T)


def inputs():
    source=json.loads((HERE/"baseline/v35-scene.json").read_text())
    baseline,old=previous.inputs()
    # No unrelated v35 geometry may differ from v34.
    for m in baseline["meshes"]:
        if m["id"] not in ("stl:"+CAP,"stl:"+BODY):
            assert m["url"]==next(n for n in source["meshes"] if n["id"]==m["id"])["url"]
    return source,baseline,old


def make_parts(old):
    shifted=placed(old[BODY],trans([EXTEND,0,0]))
    # Straight receiver and full-height inboard wall, instead of the old
    # overhead wedge and broken cap mount. Keep the metal web datum x=63.5.
    cavity_x0=KNEE_X-(g.hp.SERVO_BODY_W/2+g.hp.WELL_BODY_CL-g.hp.WELL_INSIDE_X_TIGHTEN/2)
    wall_x0=KNEE_X-g.hp.WELL_W/2
    receiver=g._box((cavity_x0-g.RECEIVER_X0,25,56),
                   ((cavity_x0+g.RECEIVER_X0)/2,0,17.15))
    wall=g._box((cavity_x0-wall_x0,g.hp.WELL_D,g.hp.WELL_H),
               ((cavity_x0+wall_x0)/2,0,g.hp.WELL_H/2))
    # Refill the outboard v34 nut/clearance pocket before drilling its pilot.
    plugs=[g._cyl_y(3.6,4.5,FACE,x=KNEE_X+x,z=z) for x,z in CENTRES]
    body=g._union(shifted,receiver,wall,*plugs)
    cuts=g._femur_receiver_cuts()
    cuts.append(g._cyl_x(g.RECEIVER_CENTER_D/2,g.RECEIVER_X0-.5,cavity_x0+.1,z=17.15))
    cuts.extend(g._cyl_y(PILOT_D/2,FACE-PILOT_DEPTH,FACE+.2,x=KNEE_X+x,z=z) for x,z in CENTRES)
    body=g._diff(body,*cuts)
    # Use the ordinary symmetric servo cap, with its original locating
    # tongue/hooks and both flush counterbores, not the offset v35 lug.
    cap=g.hp.make_servo_clamp_cap()
    assert np.allclose([g.hp.CLAMP_BOLT_X,g.hp.CLAMP_BOLT_Z],[27.2,17.15])
    screw=g._union(g._cyl_z(2.75,-3,0),g._cyl_z(SCREW_D/2,-.01,SCREW_LENGTH-TIP),
        placed(trimesh.creation.cone(radius=SCREW_D/2,height=TIP,sections=64),trans([0,0,SCREW_LENGTH-TIP])))
    # A generic cross-drive envelope; head is bounded by Ø5.5 x 3 mm.
    screw=g._diff(screw,g._box((3.2,.9,1.6),(0,0,-2.35)),g._box((.9,3.2,1.6),(0,0,-2.35)))
    return {BODY:v7.clean(body,"longer plain servo box"),CAP:v7.clean(cap,"standard middle-screw cap"),
            "knee_cap_selftap":v7.clean(screw,"3x8 self-tapper reference")}


def compose(source,parts):
    scene=copy.deepcopy(source)
    scene["name"]="Premade C-horns — longer knee box with simple middle screws"
    scene["source"]=REASON;scene["designSpecUrl"]="design_spec.yaml"
    removed={i["id"] for i in scene["instances"] if i.get("partType") in ("knee_cap_nut","knee_cap_screw")}
    scene["instances"]=[i for i in scene["instances"] if i["id"] not in removed]
    scene["meshes"]=[m for m in scene["meshes"] if m["id"] not in ("stl:knee_cap_nut","stl:knee_cap_screw")]
    for m in scene["meshes"]:
        key=m["id"].removeprefix("stl:")
        if key in parts:m.update(url=key+".stl",name=key+".stl")
    scene["meshes"].append({"id":"stl:knee_cap_selftap","name":"3x8_self_tapping_screw_DO_NOT_PRINT.stl","url":"knee_cap_selftap.stl"})
    scene["fastenings"]=[f for f in scene["fastenings"] if "-knee-cap-" not in f["id"]]
    cfg=scene["checksConfig"]
    cfg["allowedInterferences"]=[a for a in cfg["allowedInterferences"] if not set(a["instances"])&removed]
    for k in ("stl:knee_cap_nut","stl:knee_cap_screw"):cfg["expectedMeshComponents"].pop(k,None)
    cfg["expectedMeshComponents"]["stl:knee_cap_selftap"]=1
    for j in scene["joints"]:j["instances"]=[i for i in j["instances"] if i not in removed]
    for leg in range(6):
        body=next(i for i in scene["instances"] if i.get("leg")==leg and i["partType"]==BODY)
        cap=next(i for i in scene["instances"] if i.get("leg")==leg and i["partType"]==CAP)
        knee_servo=next(i for i in scene["instances"] if i.get("leg")==leg and "knee servo" in i["name"])
        Tbody=np.array(body["transform"]).reshape(4,4).T
        delta=Tbody[:3,:3]@np.array([EXTEND,0,0])
        knee_joint=next(j for j in scene["joints"] if j["id"]==f"L{leg}-knee")
        move_ids=set(knee_joint["instances"])|{cap["id"],knee_servo["id"]}
        for i in scene["instances"]:
            if i["id"] in move_ids:
                T=np.array(i["transform"]).reshape(4,4).T;T[:3,3]+=delta;i["transform"]=g._mat16(T)
        knee_joint["origin"]=(np.array(knee_joint["origin"])+delta).tolist()
        body["name"]=f"L{leg} 6mm longer servo box — self-tapping cap pilots"
        cap["name"]=f"L{leg} plain knee cap — two middle screws"
        Tcap=np.array(cap["transform"]).reshape(4,4).T
        hip_joint=next(j for j in scene["joints"] if cap["id"] in j["instances"])
        for n,(x,z) in enumerate(CENTRES):
            iid=f"L{leg}-knee-middle-selftap-{n}"
            scene["instances"].append({"id":iid,"name":f"L{leg} 3x8 knee cap self-tapper {n+1}",
                "meshId":"stl:knee_cap_selftap","partType":"knee_cap_selftap","role":"fastener","leg":leg,
                "cots":True,"color":"#b7bdc5","transform":v7.placement(Tcap,[x,SEAT,z],[0,-1,0])})
            hip_joint["instances"].append(iid)
            scene["fastenings"].append({"id":iid,"clampedInstanceId":cap["id"],"receiverInstanceId":body["id"],
                "headSeat":[x,SEAT,z],"axis":[0,-1,0],"lengthMm":SCREW_LENGTH,"shaftDiameterMm":SCREW_D,
                "minEngagementMm":4.5,"minWallMm":1.5,"tipLengthMm":TIP})
            cfg["allowedInterferences"].append({"kind":"thread_engagement","instances":[iid,body["id"]],
                "maxPenetrationMm":.3,"reason":"3 mm thread envelope intentionally engages a 2.5 mm plastic self-tapping pilot"})
    return scene


def ring(x,y,z,r):return previous.ring(x,y,z,r)


def verify(old,parts,scene,source):
    body,cap=parts[BODY],parts[CAP]
    capT=trans([KNEE_X,0,0])
    cb=placed(cap,capT);servo=placed(old["servo_body"],capT);bracket=old["chorn_clamp_cnc"]
    report={"extension_mm":EXTEND,"hip_to_knee_before_after_mm":[90,96],"cap_fasteners_per_leg":2,
        "nut_pockets":0,"pilots_mm":{"diameter":PILOT_D,"depth":PILOT_DEPTH},"screw_envelope_mm":{"diameter":3,"length":8,"head_diameter":5.5,"head_height":3,"point_length":1},
        "nominal_plastic_engagement_mm":6,"full_diameter_engagement_excluding_tip_mm":5,"tip_clearance_mm":2,
        "hip_c_front_insert_pockets":"unchanged: six diameter4.6 x depth3.1 mm; NOT for 5.7 mm inserts"}
    for label,a,b in (("cap_box",cb,body),("servo_box",servo,body),("cap_hip_C",cb,bracket),("box_hip_C",body,bracket)):
        volume=g._inter_vol(a,b);report[label+"_overlap_mm3"]=volume;assert volume<.03,(label,volume)
    report["intentional_cap_servo_press_mm3"]=g._inter_vol(cb,servo)
    assert 650<report["intentional_cap_servo_press_mm3"]<900
    for x,z in CENTRES:
        assert cap.contains(ring(x,SEAT-.1,z,2.3)).all(),"unsupported screw head seat"
        for y in np.arange(11.95,16.81,.35):
            assert body.contains(ring(KNEE_X+x,y,z,1.45)).all(),"missing self-tap bite"
            assert body.contains(ring(KNEE_X+x,y,z,3.0)).all(),"insufficient pilot wall"
        assert not body.contains([[KNEE_X+x,FACE-PILOT_DEPTH+.1,z]])[0]
        assert body.contains([[KNEE_X+x,FACE-PILOT_DEPTH-.15,z]])[0],"pilot missing blind floor"
    for dy in (.1,1,2,5,15,35):
        moved=placed(cb,trans([0,dy,0]))
        assert g._inter_vol(moved,body)<.03 and g._inter_vol(moved,bracket)<.03,("cap removal",dy)
    # Receiver front, all six insert pockets, and metal datum are untouched.
    zone=g._box((3.6,25,56),(65.3,0,17.15))
    a=g._intersect(old[BODY],zone);b=g._intersect(body,zone)
    assert abs(a.volume-b.volume)<.01 and g._inter_vol(a,b)>a.volume-.01
    meshes={**old,**parts}
    world={i["id"]:placed(meshes[i["partType"]],np.array(i["transform"]).reshape(4,4).T) for i in scene["instances"]}
    for ci in [i for i in scene["instances"] if i["partType"]==CAP]:
        T=np.array(ci["transform"]).reshape(4,4).T
        for x,z in CENTRES:
            probe=placed(g._cyl_y(2.75,OUTER+.1,OUTER+50,x=x,z=z),T)
            for iid,other in world.items():assert g._inter_vol(probe,other)<.03,("driver blocked",ci["id"],iid)
    report["driver_access"]="12/12 clear with diameter5.5 x 50 mm shaft at authored pose"
    report["cap_removal"]="+Y clear at 0.1,1,2,5,15,35 mm"
    report["motion"]=check_motion(meshes)
    return report


def shifted_frames(**kwargs):
    T=g.base.leg_transforms(0,**kwargs)
    delta=(T["femur"]@g.base.MH)[:3,:3]@np.array([EXTEND,0,0])
    for key in ("knee_cap","tibia"):T[key][:3,3]+=delta
    return T


def check_motion(meshes):
    t0=shifted_frames()
    cap_parts=[meshes[CAP]]
    for x,z in CENTRES:
        cap_parts.append(placed(meshes["knee_cap_selftap"],np.array(v7.placement(np.eye(4),[x,SEAT,z],[0,-1,0])).reshape(4,4).T))
    cap_hw=trimesh.util.concatenate(cap_parts)
    fixed=[placed(meshes[k],t0[f]) for k,f in (("hip_clamp_cap_ovh","hip_cap"),("hip_bearing_carrier_ovh","hip_cap"),("servo_body","hip_cap"),("coxa_link_ovh","coxa"),("coxa_yaw_hub_carrier_ovh","coxa"),("bearing_6805","yaw_top"))]
    for angle in np.arange(30,-110.1,-2.5):
        T=shifted_frames(femur_deg=float(angle))
        moving=[placed(meshes[BODY],T["femur"]@g.base.MH),placed(cap_hw,T["knee_cap"])]
        for m in moving:
            for f in fixed:assert g._inter_vol(m,f)<.03,("hip clearance",angle)
    for yaw in (-35,-20,0,20,35):
        for hip in np.arange(30,-110.1,-2.5):
            T=shifted_frames(yaw_deg=float(yaw),femur_deg=float(hip))
            for m in (placed(meshes[BODY],T["femur"]@g.base.MH),placed(cap_hw,T["knee_cap"])):
                for k in ("chassis_bottom","chassis_top_rigid","top_hatch_rigid"):
                    if k in meshes:assert g._inter_vol(m,meshes[k])<.03,("chassis clearance",yaw,hip,k)
    knee_fixed=[placed(meshes[BODY],t0["femur"]@g.base.MH),placed(cap_hw,t0["knee_cap"]),placed(meshes["servo_body"],t0["knee_cap"])]
    for knee in np.arange(-30,20.1,2.5):
        T=shifted_frames(tibia_deg=float(knee))
        for key in ("chorn_clamp_cnc","driven_spacer","passive_spacer","tibia_ovh_socket"):
            for f in knee_fixed:assert g._inter_vol(placed(meshes[key],T["tibia"]@g.base.MH),f)<.03,("knee clearance",knee,key)
    # Continuous swept horn extraction envelope on the relocated cradle.
    r=g.hp.DISC_HORN_OD/2+1.5;z0=g.hp.WELL_RIM_Z+.6;z1=g.hp.WELL_H-.6;travel=g.hp.WELL_D+g.hp.SERVO_BODY_D
    sweep=g._union(g._cyl_z(r,z0,z1,x=g.hp.SERVO_OUTPUT_X),g._box((2*r,travel+r,z1-z0),(g.hp.SERVO_OUTPUT_X,(travel+r)/2,(z0+z1)/2)))
    assert g._inter_vol(placed(sweep,trans([KNEE_X,0,0])),meshes[BODY])<.03
    return {"hip_deg":[-110,30],"knee_deg":[-30,20],"step_deg":2.5,"yaw_samples_deg":[-35,-20,0,20,35],"horn_on_extraction":"clear with 1.5mm radial margin"}


def spec(report):
    s=yaml.safe_load((previous.BASELINE/"v34-design_spec.yaml").read_text())
    s["revision_note"]=MESSAGE+" "+REASON
    s["simple_knee_box"]={"baseline":"v35","source_geometry":"v34 pre-lug core plus ordinary symmetric servo cap", "reason":REASON,"checks":report,"hardware":"2x 3mm-diameter x8mm self-tapping screws per knee. Head must fit diameter6 x depth3 mm recess. 2.5mm printed pilot is an initial fit value; verify for the actual screw/thread form and printer.","physical_validation":"Not performed; first print one matched pair and dry-fit. Do not overtighten plastic threads."}
    s["servo_clamp_cap_captive_nuts"]["knee"]="REMOVED: knee uses two direct self-tapping screws at the original mid-height centers; no captive nuts or slots"
    s["servo_clamp_cap_captive_nuts"]["scope"]="Existing hip clamp nuts only; the knee cap now self-taps directly into the longer femur box"
    s["servo_clamp_cap_captive_nuts"]["quantity_per_robot"]="Hip only:12 M3 nuts +12 M3x8 screws. Knee:12 separate 3x8 self-tapping screws, zero nuts."
    s["front_receiver"]["femur_thickness_mm"]=9.6
    s["front_receiver"]["femur_servo_side_skin_mm"]=6.5
    for key in ("first_contact_deg","first_contact_part"):
        s["workspace"].pop(key,None)
    s["workspace"]["hip_to_knee_length_mm"]=KNEE_X
    s["workspace"]["validation_scope"]="Exact new cap/box and hardware sampled through hip -110..30 and knee -30..20; do not reuse source-version first-contact estimates. Kinematic pivot and all downstream placements move 6mm outward."
    s["parts"][BODY].update(description="6mm longer hip-end receiver and plain servo box with two 2.5mm self-tapping pilots at mid-height. No nut pockets, loading slots or offset lug. Six front insert pockets unchanged.",printable=True)
    s["parts"][CAP].update(description="Ordinary symmetric knee servo cap with two recessed mid-height self-tapping screws, locating tongue and hooks.",printable=True)
    s["parts"]["knee_cap_selftap"]={"description":"3x8 self-tapping screw for plastic, head envelope diameter5.5 x height3mm", "material":"steel","printable":False,"cots":True,"qty_per_robot":12}
    return yaml.safe_dump(s,sort_keys=False,allow_unicode=True)


def main():
    source,baseline,old=inputs();parts=make_parts(old);scene=compose(source,parts)
    OUT.mkdir(exist_ok=True)
    for k,m in parts.items():m.export(OUT/(k+".stl"));print(k,round(m.volume,2),m.bounds.tolist(),flush=True)
    report=verify(old,parts,scene,source)
    (OUT/"print").mkdir(exist_ok=True)
    for k in (BODY,CAP):
        m=placed(parts[k],trimesh.transformations.rotation_matrix(-math.pi/2,[1,0,0]))
        m.apply_translation([-m.bounds.mean(axis=0)[0],-m.bounds.mean(axis=0)[1],-m.bounds[0,2]])
        assert m.is_volume and m.body_count==1
        area=float(m.area_faces[np.all(m.triangles[:,:,2]<.0001,axis=1)].sum());assert area>100
        report[k+"_bed_contact_mm2"]=area;m.export(OUT/"print"/(k+"_flat_face_down.stl"))
    (OUT/"scene.json").write_text(json.dumps(scene,indent=2)+"\n")
    (OUT/"checks.json").write_text(json.dumps(report,indent=2)+"\n")
    (OUT/"design_spec.yaml").write_text(spec(report))
    print(json.dumps(report,indent=2),flush=True)


if __name__=="__main__":main()
