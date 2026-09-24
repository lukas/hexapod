"""v37: cap heat-set inserts, six self-tappers through the metal hip C web.

Immutable v36 is the geometry/placement baseline. Only the femur's eight
receiving holes change; the cap, outside envelope, and all joint datums stay.
Run with uv run python <this file> from the repository root.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import trimesh
import yaml

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
BASELINE = HERE / "baseline"
_loader = importlib.util.spec_from_file_location(
    "knee_v36", HERE.parent / "knee_cap_simple_selftap/make_variant.py")
v36 = importlib.util.module_from_spec(_loader)
_loader.loader.exec_module(v36)
g, v7 = v36.g, v36.v7
BODY, CAP = v36.BODY, v36.CAP
CACHE = v36.previous.CACHE
FACE, SEAT = v36.FACE, v36.SEAT
INSERT_L, INSERT_OD = 5.7, 4.6
INSERT_BORE, INSERT_DEPTH = 4.0, 6.7
LEAD_D, LEAD_DEPTH = 4.4, .2
CAP_SCREW = "knee_cap_m3x8"
INSERT = "knee_cap_heatset_m3x5p7"
FRONT_SCREW = "hip_c_front_selftap_3x8"
FRONT_PILOT, FRONT_DEPTH = 2.5, 7.0
SCREW_L, POINT_L = 8.0, 1.0
MESSAGE = "Two M3x5.7 heat-set cap inserts and M3x8 machine screws; six 3x8 self-tappers through the metal hip C into the printed femur. Exterior, cap STL and 96mm knee datum unchanged."
REASON = ("User requests swapping v36's fastening types: reusable metal threads at the two removable cap screws, "
          "and self-tapping plastic pilots at the six metal-C-to-femur screws. This removes the incompatible 3.1mm "
          "front insert pockets. Retain the longer v36 box, cap, all transforms and motion datums. "
          "Assume M3 inserts are 5.7mm long with 4.6mm knurled OD, as in the prior roof; verify the actual stock. "
          "Front plastic threads need dry-fit/torque testing and will wear with repeated disassembly.")


def inputs():
    scene = json.loads((BASELINE / "v36-scene.json").read_text())
    meshes = {}
    for m in scene["meshes"]:
        path = CACHE / Path(m["url"]).name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == path.stem, path
        meshes[m["id"].removeprefix("stl:")] = trimesh.load_mesh(path)
    assert next(m for m in scene["meshes"] if m["id"] == "stl:" + BODY)["url"].endswith(
        "48470f366425b8831d068e8c66d227ce09404e517b9de27f8306f77b8b783dff.stl")
    return scene, meshes


def transform(mesh, matrix):
    return v36.placed(mesh, matrix)


def oriented(mesh, xyz, axis, parent=None):
    T = np.array(v7.placement(np.eye(4) if parent is None else parent, xyz, axis)).reshape(4, 4).T
    return transform(mesh, T)


def make_parts(old):
    # Refill the obsolete six front insert pockets without changing the face.
    plugs = [g._cyl_x(2.6, g.RECEIVER_X0, g.RECEIVER_X0 + 3.2, y=y, z=z)
             for y, z in g._front_m3_centres()]
    # Fill the last 1.3mm of the old 8mm cap pilots, so 6.7mm holes are blind.
    plugs += [g._cyl_y(1.35, FACE - 8.1, FACE - 6.6, x=v36.KNEE_X+x, z=z)
              for x, z in v36.CENTRES]
    body = g._union(old[BODY], *plugs)
    cuts = [g._cyl_x(FRONT_PILOT/2, g.RECEIVER_X0-.1,
                    g.RECEIVER_X0+FRONT_DEPTH, y=y, z=z)
            for y, z in g._front_m3_centres()]
    for x, z in v36.CENTRES:
        cuts += [g._cyl_y(INSERT_BORE/2, FACE-INSERT_DEPTH, FACE+.1,
                          x=v36.KNEE_X+x, z=z),
                 g._cyl_y(LEAD_D/2, FACE-LEAD_DEPTH, FACE+.1,
                          x=v36.KNEE_X+x, z=z)]
    # Nominal brass envelope: full-length core, two knurled bands, M3 minor bore.
    insert = g._union(g._cyl_z(1.95, 0, INSERT_L),
                      g._cyl_z(INSERT_OD/2, 0, 1.8),
                      g._cyl_z(INSERT_OD/2, 3.2, 4.9))
    insert = g._diff(insert, g._cyl_z(1.25, -.1, INSERT_L+.1))
    return {BODY: v7.clean(g._diff(body, *cuts), "cap inserts / front self-tapping box"),
            CAP_SCREW: v7.clean(v7.bolt(SCREW_L), "M3x8 machine screw"),
            INSERT: v7.clean(insert, "M3x5.7 heat-set reference"),
            FRONT_SCREW: old["knee_cap_selftap"].copy()}


def compose(source, parts):
    scene = copy.deepcopy(source)
    scene.update(name="Premade C-horns — cap heat-sets, front self-tappers", source=REASON)
    removed = {i["id"] for i in scene["instances"] if i["partType"] == "knee_cap_selftap"}
    scene["instances"] = [i for i in scene["instances"] if i["id"] not in removed]
    scene["meshes"] = [m for m in scene["meshes"] if m["id"] != "stl:knee_cap_selftap"]
    scene["fastenings"] = [f for f in scene["fastenings"] if f["id"] not in removed]
    cfg = scene["checksConfig"]
    cfg["allowedInterferences"] = [a for a in cfg["allowedInterferences"] if not set(a["instances"]) & removed]
    cfg["expectedMeshComponents"].pop("stl:knee_cap_selftap", None)
    for joint in scene["joints"]:
        joint["instances"] = [i for i in joint["instances"] if i not in removed]
    for key in parts:
        record = next((m for m in scene["meshes"] if m["id"] == "stl:"+key), None)
        if record:
            record.update(url=key+".stl", name=key+".stl")
        else:
            scene["meshes"].append({"id":"stl:"+key, "url":key+".stl", "name":key+"_DO_NOT_PRINT.stl"})
        cfg["expectedMeshComponents"]["stl:"+key] = 1
    for leg in range(6):
        body = next(i for i in scene["instances"] if i.get("leg") == leg and i["partType"] == BODY)
        cap = next(i for i in scene["instances"] if i.get("leg") == leg and i["partType"] == CAP)
        bracket = next(i for i in scene["instances"] if i.get("leg") == leg and "hip C-clamp" in i["id"])
        Tbody, Tcap = (np.array(i["transform"]).reshape(4, 4).T for i in (body, cap))
        assert np.allclose(Tbody, np.array(bracket["transform"]).reshape(4,4).T)
        joint = next(j for j in scene["joints"] if cap["id"] in j["instances"])
        body["name"] = f"L{leg} knee box — cap heat-set inserts / C-bracket self-tappers"
        cap["name"] = f"L{leg} plain knee cap — two M3 machine screws"
        def add(iid, key, label, parent, origin, axis, color):
            scene["instances"].append({"id":iid, "name":f"L{leg} {label}", "meshId":"stl:"+key,
                "partType":key, "role":"fastener", "leg":leg, "cots":True,
                "color":color, "transform":v7.placement(parent, origin, axis)})
            joint["instances"].append(iid)
        for n, (x, z) in enumerate(v36.CENTRES):
            sid, iid = f"L{leg}-knee-heatset-screw-{n}", f"L{leg}-knee-heatset-insert-{n}"
            add(sid, CAP_SCREW, f"M3x8 cap screw {n+1}", Tcap, [x,SEAT,z], [0,-1,0], "#b7bdc5")
            add(iid, INSERT, f"M3x5.7 cap insert {n+1}", Tcap, [x,FACE,z], [0,-1,0], "#cda34c")
            scene["fastenings"].append({"id":sid, "clampedInstanceId":cap["id"], "receiverInstanceId":iid,
                "headSeat":[x,SEAT,z], "axis":[0,-1,0], "lengthMm":SCREW_L,
                "shaftDiameterMm":3, "minEngagementMm":5.5, "minWallMm":.35})
            cfg["allowedInterferences"] += [
                {"kind":"thread_engagement", "instances":[sid,iid], "maxPenetrationMm":.3,
                 "reason":"M3 machine screw major diameter engages the modeled brass insert minor bore"},
                {"kind":"heat_set_insert", "instances":[iid,body["id"]], "maxPenetrationMm":.35,
                 "reason":"4.6mm knurled bands displace the 4mm pilot during heat setting; confirm actual insert and print fit"}]
        for n, (y, z) in enumerate(g._front_m3_centres()):
            sid = f"L{leg}-hip-C-front-selftap-{n}"
            add(sid, FRONT_SCREW, f"3x8 C-bracket-to-femur self-tapper {n+1}", Tbody,
                [g.FRONT_X0,y,z], [1,0,0], "#b7bdc5")
            scene["fastenings"].append({"id":sid, "clampedInstanceId":bracket["id"], "receiverInstanceId":body["id"],
                "headSeat":[g.FRONT_X0,y,z], "axis":[1,0,0], "lengthMm":SCREW_L,
                "shaftDiameterMm":3, "minEngagementMm":4.5, "minWallMm":1.0, "tipLengthMm":POINT_L})
            cfg["allowedInterferences"].append({"kind":"thread_engagement", "instances":[sid,body["id"]],
                "maxPenetrationMm":.3, "reason":"3mm self-tapping thread envelope engages Ø2.5 plastic pilot, not the metal web"})
    return scene


def ring_x(x, y, z, radius):
    return np.array([[x, y+radius*math.cos(a), z+radius*math.sin(a)]
                     for a in np.linspace(0,2*math.pi,64,endpoint=False)])


def verify(source, old, parts, scene):
    body, cap = parts[BODY], old[CAP]
    cap_t = v36.trans([v36.KNEE_X,0,0])
    cb, servo = transform(cap,cap_t), transform(old["servo_body"],cap_t)
    bracket = old["chorn_clamp_cnc"]
    assert np.allclose(body.bounds, old[BODY].bounds)
    report = {"baseline":"v36", "changed_printed_meshes":[BODY], "cap_mesh_unchanged":True,
        "hip_to_knee_mm":96, "insert_assumption":{"thread":"M3", "length_mm":INSERT_L,"knurled_od_mm":INSERT_OD},
        "cap_joint":{"per_knee":2,"screw":"M3x8 machine", "pilot_diameter_mm":INSERT_BORE,
            "pilot_depth_mm":INSERT_DEPTH,"nominal_thread_engagement_mm":5.7,"blind_tip_clearance_mm":.7},
        "front_joint":{"per_knee":6,"screw":"3x8 self-tapping for plastic", "metal_thickness_mm":2.1,
            "pilot_diameter_mm":FRONT_PILOT,"pilot_depth_mm":FRONT_DEPTH,"plastic_entry_mm":5.9,
            "full_diameter_engagement_excluding_tip_mm":4.9,"blind_tip_clearance_mm":1.1,
            "plastic_remaining_behind_pilot_mm":2.6}, "hardware_intersections":[]}
    for label, a, b in (("cap_box",cb,body),("servo_box",servo,body),("cap_metal",cb,bracket),("box_metal",body,bracket)):
        v = g._inter_vol(a,b); report[label+"_mm3"] = v; assert v < .03, (label,v)
    # Verify that all pre-existing instances, placements, joints and cap mesh persist.
    old_ids = {i["id"]:i for i in source["instances"] if i["partType"] != "knee_cap_selftap"}
    new_ids = {i["id"]:i for i in scene["instances"]}
    for iid, i in old_ids.items(): assert new_ids[iid]["transform"] == i["transform"]
    for j, oldj in zip(scene["joints"],source["joints"]):
        assert {k:v for k,v in j.items() if k != "instances"} == {k:v for k,v in oldj.items() if k != "instances"}
    assert next(m for m in scene["meshes"] if m["id"] == "stl:"+CAP) == next(m for m in source["meshes"] if m["id"] == "stl:"+CAP)
    for x,z in v36.CENTRES:
        x += v36.KNEE_X
        for y in np.linspace(FACE-INSERT_L+.1, FACE-.25, 15):
            assert body.contains(v36.ring(x,y,z,4.0)).all(), ("insert insufficient surrounding wall",x,y)
        assert g._inter_vol(body,g._cyl_y(1.99,FACE-INSERT_DEPTH+.02,FACE+.1,x=x,z=z)) < .03
        assert body.contains([[x,FACE-INSERT_DEPTH-.1,z]])[0], "insert bore not blind"
        tool = g._cyl_y(2.5,FACE+.01,FACE+35,x=x,z=z)
        assert g._inter_vol(body,tool) < .03, "heat-setting access blocked"
    for y,z in g._front_m3_centres():
        for x in np.linspace(g.RECEIVER_X0+.1,g.FRONT_X0+SCREW_L-POINT_L-.05,17):
            assert body.contains(ring_x(x,y,z,1.45)).all(), "missing front thread bite"
            assert body.contains(ring_x(x,y,z,2.6)).all(), "missing front pilot wall"
        assert g._inter_vol(body,g._cyl_x(1.24,g.RECEIVER_X0-.1,g.RECEIVER_X0+FRONT_DEPTH-.02,y=y,z=z)) < .03
        assert body.contains([[g.RECEIVER_X0+FRONT_DEPTH+.1,y,z]])[0], "front pilot not blind"
    # Every edit must stay inside the eight explicitly targeted hole envelopes.
    zones = [g._cyl_x(2.7,g.RECEIVER_X0-.01,g.RECEIVER_X0+FRONT_DEPTH+.01,y=y,z=z) for y,z in g._front_m3_centres()]
    zones += [g._cyl_y(2.3,FACE-8.2,FACE+.1,x=v36.KNEE_X+x,z=z) for x,z in v36.CENTRES]
    unchanged_new, unchanged_old = (g._diff(m,*zones) for m in (body,old[BODY]))
    assert abs(unchanged_new.volume-unchanged_old.volume) < .03
    assert g._inter_vol(unchanged_new,unchanged_old) > unchanged_old.volume-.03
    cap_bolts = [oriented(parts[CAP_SCREW],[v36.KNEE_X+x,SEAT,z],[0,-1,0]) for x,z in v36.CENTRES]
    inserts = [oriented(parts[INSERT],[v36.KNEE_X+x,FACE,z],[0,-1,0]) for x,z in v36.CENTRES]
    front_bolts = [oriented(parts[FRONT_SCREW],[g.FRONT_X0,y,z],[1,0,0]) for y,z in g._front_m3_centres()]
    for n,bolt in enumerate(cap_bolts):
        for label,other in (("body",body),("cap",cb),("servo",servo),("metal",bracket)):
            assert g._inter_vol(bolt,other) < .03,("cap screw clash",n,label)
    for n,bolt in enumerate(front_bolts):
        for label,other in (("cap",cb),("servo",servo),("metal",bracket)):
            assert g._inter_vol(bolt,other) < .03,("front screw clash",n,label)
        for other in cap_bolts+inserts: assert g._inter_vol(bolt,other) < .03, "crossing fasteners"
    # Both cap and front driver approaches are valid on the detached subassembly.
    for x,z in v36.CENTRES:
        driver = g._cyl_y(2.75,v36.OUTER+.1,v36.OUTER+50,x=v36.KNEE_X+x,z=z)
        for m in (body,cb,bracket): assert g._inter_vol(driver,m) < .03
    for y,z in g._front_m3_centres():
        driver = g._cyl_x(2.75,g.FRONT_X0-50,g.FRONT_X0-3.01,y=y,z=z)
        for m in (body,cb,bracket): assert g._inter_vol(driver,m) < .03
    for dy in (.1,1,2,5,15,35):
        trial = transform(cb,v36.trans([0,dy,0]))
        for m in (body,bracket,*inserts,*front_bolts): assert g._inter_vol(trial,m) < .03
    report["cap_removal"] = "clear at +Y 0.1,1,2,5,15,35mm with front screws and inserts installed"
    report["tool_access"] = "Ø5 heat-set tip and Ø5.5x50 screwdrivers clear on detached subassembly; fasten C web before mounting C to hip servo"
    # Reuse the prior deterministic sampled sweep, now including the new metal
    # front fasteners in the moving group and full-length machine cap screws.
    motion_meshes = {**old,**parts,"knee_cap_selftap":parts[CAP_SCREW]}
    motion_meshes[BODY] = trimesh.util.concatenate([body,*front_bolts,*inserts])
    report["motion"] = v36.check_motion(motion_meshes)
    return report


def spec(report):
    s = yaml.safe_load((BASELINE/"v36-design_spec.yaml").read_text())
    s["revision_note"] = MESSAGE + " " + REASON
    s.pop("simple_knee_box",None)
    s["knee_fastening_swap"] = {"baseline":"v36", "reason":REASON,"checks":report,
        "assembly":"Heat-set two inserts from the cap mating face of the empty detached femur box. Attach metal C web with six 3x8 plastic self-tappers before mounting C on servo. Install knee servo and unchanged cap with two M3x8 machine screws. No front heat-set inserts; no cap self-tappers.",
        "physical_validation":"Not performed. Confirm 4.6mm insert OD; dry-test actual screws/printed pilots. No strength or torque qualification.",
        "insert_reference":"https://www.ruthex.de/en/collections/gewindeeinsatze/products/ruthex-gewindeeinsatz-m3-100-stuck-rx-m3x5-7-messing-gewindebuchsen"}
    s["front_receiver"].update(femur_attachment="6x 3x8 self-tapping screws through metal web into Ø2.5x7mm plastic pilots",
        femur_pilot_depth_mm=7.0,femur_servo_side_skin_mm=2.6)
    s["front_receiver"].pop("femur_insert_depth_mm",None)
    s["hardware_guidance"]["front_receiver_screws"] = "Femur: six 3x8 self-tappers, 2.1mm metal web, 5.9mm plastic entry / 4.9mm excluding point; no inserts. Tibia attachment remains unchanged M3/nyloc and needs measured stack."
    s["servo_clamp_cap_captive_nuts"].update(scope="Existing hip clamp nuts only; knee uses heat-set inserts",
        knee="Two M3x8 machine screws into M3x5.7 cap-face heat-set inserts; no knee nuts or slots",
        quantity_per_robot="Hip unchanged. Knee:12 M3x8 screws+12 M3x5.7 heat-sets. Hip C-to-femur:36 3x8 self-tapping screws.")
    s["parts"][BODY].update(description="Unchanged 96mm v36 box envelope; two cap-facing Ø4x6.7mm heat-set pilots and six bracket-facing Ø2.5x7mm self-tapping pilots. No front insert pockets.")
    s["parts"][CAP].update(description="Unchanged v36 symmetric cap, two recessed M3x8 machine screws into box heat-set inserts.")
    s["parts"].pop("knee_cap_selftap",None)
    for key,description,material,qty in ((CAP_SCREW,"M3x8 cap machine screw","steel",12),
            (INSERT,"M3x5.7 heat-set insert, assumed 4.6mm knurled OD","brass",12),
            (FRONT_SCREW,"3x8 self-tapping plastic screw through metal C web into printed femur","steel",36)):
        s["parts"][key] = {"description":description,"material":material,"printable":False,"cots":True,"qty_per_robot":qty}
    return yaml.safe_dump(s,sort_keys=False,allow_unicode=True)


def main():
    source, old = inputs()
    parts = make_parts(old)
    scene = compose(source,parts)
    OUT.mkdir(exist_ok=True)
    for key,mesh in parts.items():
        mesh.export(OUT/(key+".stl")); print(key,round(mesh.volume,3),flush=True)
    print("Checking fits, fastener engagement and sampled motion...",flush=True)
    report = verify(source,old,parts,scene)
    (OUT/"print").mkdir(exist_ok=True)
    for key,mesh in ((BODY,parts[BODY]),(CAP,old[CAP])):
        printmesh = transform(mesh,trimesh.transformations.rotation_matrix(-math.pi/2,[1,0,0]))
        printmesh.apply_translation([-printmesh.bounds.mean(axis=0)[0],-printmesh.bounds.mean(axis=0)[1],-printmesh.bounds[0,2]])
        assert printmesh.is_volume and printmesh.body_count == 1
        printmesh.export(OUT/"print"/(key+"_flat_face_down.stl"))
    (OUT/"scene.json").write_text(json.dumps(scene,indent=2)+"\n")
    (OUT/"checks.json").write_text(json.dumps(report,indent=2)+"\n")
    (OUT/"design_spec.yaml").write_text(spec(report))
    print(json.dumps(report,indent=2),flush=True)


if __name__ == "__main__":
    main()
