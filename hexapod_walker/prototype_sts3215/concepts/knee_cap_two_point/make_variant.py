"""Repair the v34 knee-cap attachment without regenerating unrelated parts.

Run from the repository root with ``uv run python <this file>``.
Published v34 meshes are immutable inputs, checked against their SHA256 names.
The cap and its matching femur receive one compact upper-corner fastening lug.
Both cap screws use the same M3x8 / ordinary captive-M3-nut stack.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import trimesh
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "premade_chorn_56"))
import make_premade_chorn_56_variant as g
import make_serviceable_yaw as v7

BASELINE = HERE / "baseline"
OUT = HERE / "output"
CACHE = Path.home() / ".buildviz/cache/_assets"
CAP_KEY = "knee_clamp_cap_ovh"
BODY_KEY = "femur_ovh_body"
NEW_X, NEW_Z = -34.0, 35.5  # cap-local; femur-local X = 56 mm
R = 4.75
CENTRES = [(NEW_X, NEW_Z), (27.2, 17.15)]
FACE, SEAT, OUTER = 16.9, 18.9, 21.9
NUT_Y0, NUT_Y1 = 11.2, 13.9


def transformed(mesh, matrix):
    out = mesh.copy()
    out.apply_transform(matrix)
    return out


def inputs():
    scene = json.loads((BASELINE / "v34-scene.json").read_text())
    meshes = {}
    for record in scene["meshes"]:
        path = CACHE / Path(record["url"]).name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == path.stem, path
        meshes[record["id"].removeprefix("stl:")] = trimesh.load_mesh(path)
    assert next(m for m in scene["meshes"] if m["id"] == "stl:" + CAP_KEY)["url"].endswith(
        "ed04f07994b410a2ad109fcadfe42ae5b3bbb926445a6edd61c9a4cd7b572341.stl")
    assert next(m for m in scene["meshes"] if m["id"] == "stl:" + BODY_KEY)["url"].endswith(
        "3f79d14d5baad527a198f2e88a80bce25148233cfafe81c719ab294bd301a28a.stl")
    return scene, meshes


def make_parts(meshes):
    # The receiver bridges OVER (not through) the 25-mm-wide bought web.
    # X clearance to metal = 61.4 - (56 + 4.75) = 0.65 mm.
    # Bridge Y starts at 13, leaving 0.5 mm above the metal web edge.
    cradle_add = g._union(
        g._cyl_y(R, 9.0, FACE, x=NEW_X, z=NEW_Z),
        g._box((20.0, 3.9, 2 * R), (-24.0, 14.95, NEW_Z)),
    )
    # A face-open nut recess does NOT retain the nut against screw tension.
    # Refill the existing open outboard recess; replace it with a side slot
    # beneath a 3 mm solid load-bearing roof. Both nuts then pull on BODY,
    # not on the cap that closes their loading aperture.
    refill = g._cyl_y(3.6, 14.0, FACE, x=27.2, z=17.15)
    body = g._union(meshes[BODY_KEY], transformed(cradle_add, g.KNEE_CAP_TO_FEMUR),
                    transformed(refill, g.KNEE_CAP_TO_FEMUR))
    cuts = []
    for x, z in CENTRES:
        end = x - 12 if x < 0 else x + 12
        cuts.extend([
            g._hex_y(5.8, NUT_Y0, NUT_Y1, x=x, z=z, flat_normal_angle_rad=math.pi / 2),
            g._box((abs(end-x), NUT_Y1-NUT_Y0, 5.8),
                   ((x+end)/2, (NUT_Y0+NUT_Y1)/2, z)),
            g._cyl_y(1.7, 10.7, FACE+.1, x=x, z=z),
        ])
    body = g._diff(body, *(transformed(c, g.KNEE_CAP_TO_FEMUR) for c in cuts))
    # Subtract only a matching clearance around the added body. Do not re-cut
    # the horn-on service slot, hook, or six-insert front receiver.
    body_clear = g._union(
        g._cyl_y(R + .15, 0, FACE, x=NEW_X, z=NEW_Z),
        g._box((20.3, FACE, 2 * R + .3), (-24.0, FACE/2, NEW_Z)),
    )
    cap = g._union(
        g._diff(meshes[CAP_KEY], body_clear),
        g._cyl_y(R, FACE, OUTER, x=NEW_X, z=NEW_Z),
        g._box((20.0, 5.0, 2 * R), (-24.0, 19.4, NEW_Z)),
    )
    cap = g._diff(cap,
        g._cyl_y(1.7, FACE - .1, OUTER + .1, x=NEW_X, z=NEW_Z),
        g._cyl_y(g.hp.CLAMP_HEAD_CB_OD / 2, SEAT, OUTER + .1, x=NEW_X, z=NEW_Z))
    return {BODY_KEY: v7.clean(body, BODY_KEY), CAP_KEY: v7.clean(cap, CAP_KEY)}


def hardware():
    return {
        "knee_cap_screw": v7.clean(v7.bolt(8), "M3x8 cap screw"),
        "knee_cap_nut": v7.clean(g._diff(
            g._hex_y(5.5, -1.2, 1.2, x=0, z=0, flat_normal_angle_rad=math.pi/2),
            g._cyl_y(1.25, -1.3, 1.3, x=0, z=0)), "M3 nut"),
    }


def compose(scene, changed):
    scene = copy.deepcopy(scene)
    scene["name"] = "Premade 56 mm C-horns — supported two-screw knee caps"
    scene["source"] = "knee_cap_two_point; immutable v34 baseline; see design_spec.yaml"
    scene["designSpecUrl"] = "design_spec.yaml"
    for m in scene["meshes"]:
        key = m["id"].removeprefix("stl:")
        if key in changed:
            m.update(url=f"{key}.stl", name=f"{key}.stl")
    for key in hardware():
        scene["meshes"].append({"id": "stl:"+key, "url": key+".stl",
                                 "name": key+"_DO_NOT_PRINT.stl"})
        scene["checksConfig"]["expectedMeshComponents"]["stl:"+key] = 1
    for leg in range(6):
        cap = next(i for i in scene["instances"] if i.get("leg")==leg and i.get("partType")==CAP_KEY)
        body = next(i for i in scene["instances"] if i.get("leg")==leg and i.get("partType")==BODY_KEY)
        cap["name"] = f"L{leg} knee cap — two recessed M3x8 screws"
        body["name"] = f"L{leg} femur — two side-loaded captive cap nuts"
        T = np.array(cap["transform"]).reshape(4,4).T
        joint = next(j for j in scene["joints"] if cap["id"] in j["instances"])
        for station, (x,z) in enumerate(CENTRES):
            screw_id, nut_id = (f"L{leg}-knee-cap-{station}-{kind}" for kind in ("screw","nut"))
            nt = np.eye(4); nt[:3,3] = [x,12.55,z]
            for iid, key, color, tr in (
                (screw_id,"knee_cap_screw","#a8b2bd",v7.placement(T,[x,SEAT,z],[0,-1,0])),
                (nut_id,"knee_cap_nut","#bb995b",g._mat16(T @ nt)),
            ):
                scene["instances"].append({"id":iid,"name":iid,"meshId":"stl:"+key,
                    "partType":key,"role":"fastener","leg":leg,"cots":True,"color":color,"transform":tr})
                joint["instances"].append(iid)
            scene["fastenings"].append({"id":f"L{leg}-knee-cap-{station}",
                "clampedInstanceId":cap["id"],"receiverInstanceId":nut_id,
                "headSeat":[x,SEAT,z],"axis":[0,-1,0],"lengthMm":8,
                "shaftDiameterMm":3,"minEngagementMm":2.0,"minWallMm":.5})
            scene["checksConfig"]["allowedInterferences"].append({
                "kind":"thread_engagement","instances":[screw_id,nut_id],
                "reason":"M3 screw nominal-major-diameter envelope engages the modeled nut minor bore; not a clearance collision",
                "maxPenetrationMm":.3})
    return scene


def ring(x,y,z,r):
    return [[x+r*math.cos(a),y,z+r*math.sin(a)] for a in np.linspace(0,2*math.pi,48,endpoint=False)]


def motion_check(meshes):
    t0=g.base.leg_transforms(0)
    cap_parts=[meshes[CAP_KEY]]
    for x,z in CENTRES:
        nt=np.eye(4);nt[:3,3]=[x,12.55,z]
        cap_parts.extend([
            transformed(meshes["knee_cap_nut"],nt),
            transformed(meshes["knee_cap_screw"],np.array(v7.placement(np.eye(4),[x,SEAT,z],[0,-1,0])).reshape(4,4).T)])
    cap_assembly=trimesh.util.concatenate(cap_parts)
    fixed=[transformed(meshes[key],t0[fr]) for key,fr in (
        ("hip_clamp_cap_ovh","hip_cap"),("hip_bearing_carrier_ovh","hip_cap"),
        ("servo_body","hip_cap"),("coxa_link_ovh","coxa"),
        ("coxa_yaw_hub_carrier_ovh","coxa"),("bearing_6805","yaw_top"))]
    for angle in np.arange(30,-110.1,-2.5):
        T=g.base.leg_transforms(0,femur_deg=float(angle))
        moving=[transformed(meshes[BODY_KEY],T["femur"]@g.base.MH),transformed(cap_assembly,T["knee_cap"])]
        for m in moving:
            for f in fixed:
                assert g._inter_vol(m,f)<.05,("hip sweep obstruction",angle)
    # Chassis/hatch are yaw-dependent; test both modified parts at all limits
    # and two intermediate yaw stations, through the specified hip range.
    stationary=[meshes[k] for k in ("chassis_bottom","chassis_top_rigid","top_hatch_rigid") if k in meshes]
    for yaw in (-35,-20,0,20,35):
        for hip in np.arange(30,-110.1,-2.5):
            T=g.base.leg_transforms(0,yaw_deg=float(yaw),femur_deg=float(hip))
            moving=[transformed(meshes[BODY_KEY],T["femur"]@g.base.MH),transformed(cap_assembly,T["knee_cap"])]
            for m in moving:
                for f in stationary:
                    assert g._inter_vol(m,f)<.05,("chassis sweep obstruction",yaw,hip)
    knee_fixed=[transformed(meshes[BODY_KEY],t0["femur"]@g.base.MH),
                transformed(cap_assembly,t0["knee_cap"])]
    for knee in np.arange(-30,20.1,2.5):
        T=g.base.leg_transforms(0,tibia_deg=float(knee))
        for key in ("chorn_clamp_cnc","driven_spacer","passive_spacer","tibia_ovh_socket"):
            moving=transformed(meshes[key],T["tibia"]@g.base.MH)
            for fixed_part in knee_fixed:
                assert g._inter_vol(moving,fixed_part)<.05,("knee sweep obstruction",knee,key)
    return {"hip_deg":[-110,30],"knee_deg":[-30,20],"step_deg":2.5,
        "chassis_yaw_samples_deg":[-35,-20,0,20,35],"scope":"modified cap, femur and cap hardware against own hip stack, knee moving bracket/socket and chassis; unchanged adjacent legs not revalidated"}


def verify(original_scene, old, changed, hw):
    meshes = {**old, **changed, **hw}
    report = {"fit":g.check_femur_servo_fit(meshes),
              "horn_on_extraction":g.check_horn_on_servo_extraction(meshes)}
    cap = changed[CAP_KEY]
    body = transformed(changed[BODY_KEY], np.linalg.inv(g.KNEE_CAP_TO_FEMUR))
    report["fasteners"] = []
    for x,z in CENTRES:
        nut = hw["knee_cap_nut"].copy(); nut.apply_translation([x,12.55,z])
        assert g._inter_vol(nut,body)<.02, "nut does not fit"
        assert body.contains(ring(x,14.05,z,2.3)).all(), "nut has no axial retaining roof"
        assert body.contains(ring(x,16.7,z,2.3)).all(), "nut roof opens into mating face"
        assert cap.contains(ring(x,SEAT-.1,z,2.3)).all(), "head bearing seat unsupported"
        assert cap.contains(ring(x,20,z,3.5)).all(), "open-sided head counterbore"
        sign=-1 if x<0 else 1
        for dx in np.arange(0,14.01,.5):
            trial=nut.copy(); trial.apply_translation([sign*dx,0,0])
            assert g._inter_vol(trial,body)<.02, ("nut insertion blocked",x,dx)
        pull=nut.copy();pull.apply_translation([0,.6,0])
        assert g._inter_vol(pull,body)>1, "nut pulls out toward cap"
        rotate=nut.copy();rotate.apply_transform(trimesh.transformations.rotation_matrix(
            math.pi/6,[0,1,0],[x,12.55,z]))
        assert g._inter_vol(rotate,body)>.1, "nut not prevented from spinning"
        screw=transformed(hw["knee_cap_screw"],np.array(v7.placement(np.eye(4),[x,SEAT,z],[0,-1,0])).reshape(4,4).T)
        assert g._inter_vol(screw,cap)<.02 and g._inter_vol(screw,body)<.02, "screw hits printed parts"
        assert g._inter_vol(screw,nut)>1, "missing nut engagement"
        if x<0:
            assert body.contains([[x,10.5,z]])[0], "missing blind screw-tip floor in added lug"
        report["fasteners"].append({"cap_local_xz_mm":[x,z],"screw":"M3x8 socket head",
            "nut":"ordinary M3, 5.5 AF x 2.4 thick", "nut_pocket_mm":[5.8,2.7],
            "nut_retaining_roof_mm":3.0,"nominal_thread_engagement_mm":2.4,
            "tip_clearance_mm":.2 if x<0 else "inherited through clearance", "head_flush":True,"side_loading_and_anti_rotation":"pass",
            "nut_pullout_blocked_by_body":"pass"})
    report["release"]={}
    bracket=transformed(old["chorn_clamp_cnc"],np.linalg.inv(g.KNEE_CAP_TO_FEMUR))
    for dy in (.1,1,2,5,15,35):
        lifted=cap.copy();lifted.apply_translation([0,dy,0])
        for label,other in (("femur",body),("hip_C",bracket)):
            vol=g._inter_vol(lifted,other)
            assert vol<.02,("cap release",label,dy,vol)
    report["release"]["cap_positive_y"]="clear at 0.1, 1, 2, 5, 15, 35 mm"
    # Verify the inboard tab did not change any of the six short insert bores.
    front_window=g._box((3.6,25,56),(65.3,0,17.15))
    a=g._intersect(old[BODY_KEY],front_window);b=g._intersect(changed[BODY_KEY],front_window)
    assert abs(a.volume-b.volume)<.01 and g._inter_vol(a,b)>a.volume-.01
    report["front_receiver"]={"unchanged":True,"metal_web_thickness_mm":2.1,
        "six_insert_bores_mm":{"diameter":4.6,"depth":3.1},"user_5_7mm_inserts_fit":False}
    # Check both 5.5-mm-diameter driver shafts in the actual assembled scene,
    # not just against an isolated cradle.
    placed={i["id"]:transformed(meshes[i["meshId"].removeprefix("stl:")],
              np.array(i["transform"]).reshape(4,4).T) for i in original_scene["instances"]}
    for ci in [i for i in original_scene["instances"] if i.get("partType")==CAP_KEY]:
        T=np.array(ci["transform"]).reshape(4,4).T
        for x,z in CENTRES:
            driver=transformed(g._cyl_y(2.75,OUTER+.1,OUTER+50,x=x,z=z),T)
            for iid,other in placed.items():
                assert g._inter_vol(driver,other)<.02,("driver blocked",ci["id"],x,iid)
    report["driver_access"]="both stations on all 6 knees: 5.5 mm diameter x 50 mm shaft clear at authored pose"
    # Any newly added material must not create an interference at authored pose.
    increases=[]
    for ci in [i for i in original_scene["instances"] if i.get("partType") in changed]:
        key=ci["partType"];T=np.array(ci["transform"]).reshape(4,4).T
        newpart=placed[ci["id"]];oldpart=transformed(old[key],T)
        for oi in original_scene["instances"]:
            if oi["id"]==ci["id"]:continue
            other=placed[oi["id"]]
            v=g._inter_vol(newpart,other)
            if v>.02:
                delta=v-g._inter_vol(oldpart,other)
                if delta>.03:increases.append([ci["id"],oi["id"],delta])
    assert not increases,increases
    report["authored_pose_regressions"]=increases
    report["motion"]=motion_check(meshes)
    return report


def design_spec(report):
    spec=yaml.safe_load((BASELINE/"v34-design_spec.yaml").read_text())
    spec["revision_note"]="Repair v34's missing second knee-cap attachment using two same-face M3x8 screws and side-loaded M3 nuts under solid retaining roofs. The cap and femur must be replaced together. All other v34 parts and datums are unchanged."
    spec["servo_clamp_cap_captive_nuts"]["knee"]="two side-loaded ordinary M3 hex nuts per knee; each retained axially by 3 mm of femur material above its pocket, not by the removable cap"
    spec["servo_clamp_cap_captive_nuts"]["quantity_per_robot"]="24 ordinary M3 hex nuts and 24 M3x8 SHCS across hip and knee caps; this revision models the 12 knee screws and 12 knee nuts"
    spec["servo_clamp_cap_captive_nuts"]["knee_pocket"]="5.8 mm AF x 2.7 mm deep; opposing end-entry slots; 3 mm retaining roof; 2.4 mm nominal nut engagement"
    spec["parts"][BODY_KEY]["description"]="Matching two-point knee-cap cradle with compact upper-corner inboard lug, end-entry M3 nut slots and 3 mm retaining roofs. Six short front insert pockets unchanged."
    spec["parts"][CAP_KEY]["description"]="Two recessed, same-face M3x8 cap screws: original outboard and compact upper-inboard corner. No tall upper lug or inaccessible underside screw."
    for key in (BODY_KEY,CAP_KEY):spec["parts"][key]["printable"]=True
    for key in ("knee_cap_screw","knee_cap_nut"):
        spec["parts"][key]={"description":"M3x8 socket-head screw" if key.endswith("screw") else "ordinary M3 hex nut, 5.5 AF x 2.4 mm thick", "material":"steel", "qty_per_robot":12,"printable":False,"cots":True}
    spec["knee_cap_two_point"]={"source_version":"v34","changed_parts":[BODY_KEY,CAP_KEY],
        "assembly":["Slide one ordinary M3 hex nut into each end-entry femur slot before seating the cap.",
            "Seat the cap and install two M3x8 socket-head screws from the same outer face. The femur roofs, not the cap, retain the nuts against screw tension.",
            "To service the servo, remove both accessible cap screws and withdraw the cap/servo through the existing open face."],
        "important":"This revision does not change the six femur-to-hip-C insert pockets; their 3.1 mm depth is too short for 5.7 mm inserts.",
        "validation":report,"physical_status":"Geometric prototype. Print one mating pair and dry-fit hardware; printed tolerance, pullout strength and loaded fatigue have not been tested."}
    return yaml.safe_dump(spec,sort_keys=False,allow_unicode=True)


def main():
    scene, meshes = inputs()
    changed = make_parts(meshes)
    hw=hardware()
    OUT.mkdir(exist_ok=True)
    for key, mesh in {**changed,**hw}.items():
        mesh.export(OUT / f"{key}.stl")
        print(key, "volume", round(mesh.volume, 2), "bounds", mesh.bounds.tolist(), flush=True)
    (OUT/"print").mkdir(exist_ok=True)
    for key,mesh in changed.items():
        printable=transformed(mesh,trimesh.transformations.rotation_matrix(-math.pi/2,[1,0,0]))
        printable.apply_translation([-printable.bounds.mean(axis=0)[0],-printable.bounds.mean(axis=0)[1],-printable.bounds[0,2]])
        assert printable.is_volume and printable.body_count==1
        contact=np.all(printable.triangles[:,:,2]<.0001,axis=1)
        area=float(printable.area_faces[contact].sum())
        assert area>100,("insufficient flat print face",key,area)
        printable.export(OUT/"print"/f"{key}_flat_face_down.stl")
        print(key,"bed contact mm2",round(area,1),flush=True)
    report = verify(scene,meshes,changed,hw)
    (OUT / "checks.json").write_text(json.dumps(report, indent=2) + "\n")
    (OUT/"scene.json").write_text(json.dumps(compose(scene,changed),indent=2)+"\n")
    (OUT/"design_spec.yaml").write_text(design_spec(report))
    print(json.dumps(report,indent=2),flush=True)


if __name__ == "__main__":
    main()
