"""Four inner tibia receiver self-tappers; immutable v37 parent, v38 successor.

The socket in the user's v5 catalog view is SHA-identical to v37. Carry the
new edit forward without reverting the newer knee/femur design.
Run: uv run python <this file>
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
BASELINE, OUT = HERE/"baseline", HERE/"output"
_loader = importlib.util.spec_from_file_location("tibia_parent_v37", HERE.parent/"knee_cap_heatset_front_selftap/make_variant.py")
v37 = importlib.util.module_from_spec(_loader)
_loader.loader.exec_module(v37)
g, v7, v36 = v37.g, v37.v7, v37.v36
KEY, SCREW = "tibia_ovh_socket", "tibia_inner_selftap_3x8"
PILOT_D, PILOT_DEPTH = 2.5, 7.0
SCREW_D, SCREW_L, TIP_L = 3.0, 8.0, 1.0
MESSAGE = "Tibia socket: replace four inaccessible inner nuts with Ø2.5x7mm blind pilots for 3x8 self-tappers; close obsolete nut-access windows. Keep two outer nyloc connections, tube fit and all v37 knee improvements."
REASON = ("User reports the four inner tibia receiver nuts cannot be installed/accessed, then explicitly chooses self-tapping screws instead of inserts. "
          "Remove only these four nut connections and restore solid plastic behind their original 14mm-PCD holes. "
          "Screws pass through the metal C web and tap the plastic. The two outer accessible nuts remain. "
          "Use v37 as the full-robot parent: the viewed v5 socket is identical, so earlier knee changes are preserved. "
          "Plastic threads trade away nut-thread durability and need physical pilot/torque fit testing.")


def inputs():
    scene = json.loads((BASELINE/"v37-scene.json").read_text())
    meshes = {}
    for record in scene["meshes"]:
        path = v37.CACHE/Path(record["url"]).name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == path.stem, path
        meshes[record["id"][4:]] = trimesh.load_mesh(path)
    assert next(m for m in scene["meshes"] if m["id"] == "stl:"+KEY)["url"].endswith(
        "d4d00e4bb99e93eb89d5d31ece4c4a96a8c9ec02b2be5dd8c159ea447afa97e8.stl")
    return scene, meshes


def outer_cuts():
    cuts = []
    for y,z in g._front_extra_m3_centres():
        cuts += [g._cyl_x(g.FRONT_M3_D/2,g.RECEIVER_X0-.1,g.RECEIVER_X1+.2,y=y,z=z),
                 g._hex_x(g.NYLOC_AF,g.RECEIVER_X1-g.NYLOC_POCKET_DEPTH,g.RECEIVER_X1+.2,y=y,z=z)]
    return cuts


def make_socket(old):
    # Restore the original continuous plate/collar envelope to fill the four
    # inner hex cavities and radial loading windows. Recut the unchanged tube
    # bore and outer nut seats. Preserve the ancestor's center entrance/stop.
    plate = g._box((g.RECEIVER_T,g.CHORN_BLADE_WIDTH,g.CHORN_OUTSIDE_SPAN),
                   ((g.RECEIVER_X0+g.RECEIVER_X1)/2,0,g.BRACKET_MID_Z))
    plate = g._diff(plate,g._cyl_x(g.RECEIVER_CENTER_D/2,g.RECEIVER_X0-.1,g.RECEIVER_X1+.1,z=g.BRACKET_MID_Z))
    collar = g._cyl_x(g.TIB_SOCKET_OUTER_R,g.RECEIVER_X0+.05,g.TIB_MOUTH_X,z=g.BRACKET_MID_Z)
    body = g._union(old,plate,collar)
    cuts = [g._cyl_x(g.TIB_SOCKET_BORE_R,g.TIB_BORE_X0,g.TIB_MOUTH_X+.5,z=g.BRACKET_MID_Z),*outer_cuts()]
    cuts += [g._cyl_x(PILOT_D/2,g.RECEIVER_X0-.1,g.RECEIVER_X0+PILOT_DEPTH,y=y,z=z)
             for y,z in g._front_usual_m3_centres()]
    return v7.clean(g._diff(body,*cuts),"tibia four inner self-tapping pilots")


def compose(source):
    scene = copy.deepcopy(source)
    scene.update(name="Premade C-horns — self-tapping inner tibia receiver",source=REASON)
    next(m for m in scene["meshes"] if m["id"] == "stl:"+KEY).update(url=KEY+".stl",name=KEY+".stl")
    hardware = copy.deepcopy(next(m for m in scene["meshes"] if m["id"] == "stl:hip_c_front_selftap_3x8"))
    hardware.update(id="stl:"+SCREW,name=SCREW+"_DO_NOT_PRINT.stl")
    scene["meshes"].append(hardware)
    scene["checksConfig"]["expectedMeshComponents"]["stl:"+SCREW] = 1
    for leg in range(6):
        socket = next(i for i in scene["instances"] if i.get("leg") == leg and i["partType"] == KEY)
        bracket = next(i for i in scene["instances"] if i.get("leg") == leg and "knee C-clamp" in i["id"])
        T = np.array(socket["transform"]).reshape(4,4).T
        assert np.allclose(T,np.array(bracket["transform"]).reshape(4,4).T)
        socket["name"] = f"L{leg} tibia socket — four inner self-tappers / two outer nuts"
        joint = next(j for j in scene["joints"] if j["id"] == f"L{leg}-knee")
        for n,(y,z) in enumerate(g._front_usual_m3_centres()):
            iid = f"L{leg}-tibia-inner-selftap-{n}"
            scene["instances"].append({"id":iid,"name":f"L{leg} 3x8 tibia inner self-tapper {n+1}",
                "meshId":"stl:"+SCREW,"partType":SCREW,"leg":leg,"role":"fastener","cots":True,
                "color":"#b7bdc5","transform":v7.placement(T,[g.FRONT_X0,y,z],[1,0,0])})
            joint["instances"].append(iid)
            scene["fastenings"].append({"id":iid,"clampedInstanceId":bracket["id"],"receiverInstanceId":socket["id"],
                "headSeat":[g.FRONT_X0,y,z],"axis":[1,0,0],"lengthMm":SCREW_L,"shaftDiameterMm":SCREW_D,
                "tipLengthMm":TIP_L,"minEngagementMm":4.5,"minWallMm":1.25})
            scene["checksConfig"]["allowedInterferences"].append({"kind":"thread_engagement",
                "instances":[iid,socket["id"]],"maxPenetrationMm":.3,
                "reason":"3mm self-tapping thread envelope engages Ø2.5 plastic pilot; threads are not cut in the metal C web"})
    return scene


def verify(source,old,socket,scene):
    before = old[KEY]
    report = {"baseline":"v37","viewed_socket_identical_to_v5":True,"only_changed_printed_part":KEY,
        "inner_joint":{"count_per_socket":4,"screw":"3x8 self-tapping for plastic","head_envelope_mm":[5.5,3],
            "pilot_diameter_mm":PILOT_D,"pilot_depth_mm":PILOT_DEPTH,"metal_web_mm":2.1,
            "plastic_entry_mm":5.9,"full_diameter_engagement_excluding_tip_mm":4.9,"tip_clearance_mm":1.1,
            "pilot_to_tube_bore_ligament_mm":7-PILOT_D/2-g.TIB_SOCKET_BORE_R,
            "thread_envelope_to_tube_bore_mm":7-SCREW_D/2-g.TIB_SOCKET_BORE_R,
            "blind_pilot_back_skin_min_mm":g.RECEIVER_T-PILOT_DEPTH},
        "outer_pair":"Unchanged Ø3.4 through holes and5.7AF x4mm-deep M3 nyloc pockets on37mm span",
        "tube_engagement_mm":g.TIB_TUBE_ENGAGEMENT,"nut_windows_removed":4,
        "kinematic_changes":False,"physical_validation":"None; actual screw profile, printed fit, torque, pullout and wear need testing"}
    assert socket.is_volume and socket.body_count == 1
    assert np.allclose(before.bounds,socket.bounds)
    assert socket.volume > before.volume
    # No old material removed except smaller pilots (which are inside existing
    # holes); tube fit/central stop and both outer fastenings stay exact.
    assert g._inter_vol(before,socket) > before.volume-.03
    bore_zone = g._cyl_x(g.TIB_SOCKET_BORE_R-.01,g.RECEIVER_X0-.1,g.TIB_MOUTH_X+.1,z=g.BRACKET_MID_Z)
    stop_zone = g._cyl_x(4.25,g.RECEIVER_X0-.1,g.TIB_BORE_X0+.1,z=g.BRACKET_MID_Z)
    for zone in [bore_zone,stop_zone]+[g._cyl_x(5,g.RECEIVER_X0-.1,g.RECEIVER_X1+.1,y=y,z=z)
                           for y,z in g._front_extra_m3_centres()]:
        a,b = g._intersect(before,zone),g._intersect(socket,zone)
        assert abs(a.volume-b.volume) < .03,("protected region changed",zone.bounds.tolist(),a.volume,b.volume)
        assert g._inter_vol(a,b) > a.volume-.03
    assert g._inter_vol(socket,g._cyl_x(4.04,g.TIB_BORE_X0+.01,g.TIB_MOUTH_X+.2,z=g.BRACKET_MID_Z)) < .03
    for y,z in g._front_usual_m3_centres():
        for x in np.linspace(g.RECEIVER_X0+.1,g.FRONT_X0+SCREW_L-TIP_L-.05,17):
            for rad in (1.45,2.75):
                assert socket.contains(v37.ring_x(x,y,z,rad)).all(),("missing plastic",x,y,z,rad)
        assert g._inter_vol(socket,g._cyl_x(1.24,g.RECEIVER_X0-.1,g.RECEIVER_X0+PILOT_DEPTH-.02,y=y,z=z)) < .03
        assert socket.contains([[g.RECEIVER_X0+PILOT_DEPTH+.1,y,z]])[0],"pilot not blind"
    new_ids = {i["id"]:i for i in scene["instances"]}
    for i in source["instances"]: assert new_ids[i["id"]]["transform"] == i["transform"]
    for j,prev in zip(scene["joints"],source["joints"]):
        assert {k:v for k,v in j.items() if k != "instances"} == {k:v for k,v in prev.items() if k != "instances"}
    for m in source["meshes"]:
        if m["id"] != "stl:"+KEY: assert m == next(n for n in scene["meshes"] if n["id"] == m["id"])
    screws = [v37.oriented(old["hip_c_front_selftap_3x8"],[g.FRONT_X0,y,z],[1,0,0]) for y,z in g._front_usual_m3_centres()]
    bracket = old["chorn_clamp_cnc"]
    for n,screw in enumerate(screws):
        assert g._inter_vol(screw,bracket) < .03,("screw/metal",n)
        for other in screws[n+1:]: assert g._inter_vol(screw,other) < .03
    assert g._inter_vol(socket,bracket) < .03
    # Driver approach through the empty C bracket before mounting it on servo.
    for y,z in g._front_usual_m3_centres():
        tool = g._cyl_x(2.75,g.FRONT_X0-50,g.FRONT_X0-3.01,y=y,z=z)
        assert g._inter_vol(tool,socket) < .03 and g._inter_vol(tool,bracket) < .03
    # Actual full-scene tube meshes (rather than just the nominal bore) stay clear.
    for leg in range(6):
        sock_i = next(i for i in scene["instances"] if i.get("leg") == leg and i["partType"] == KEY)
        tube_i = next(i for i in scene["instances"] if i.get("leg") == leg and i["partType"] == "tibia_tube_ovh")
        ts,tt = (np.array(i["transform"]).reshape(4,4).T for i in (sock_i,tube_i))
        tube_local = v37.transform(old["tibia_tube_ovh"],np.linalg.inv(ts)@tt)
        for item in [socket,*screws]: assert g._inter_vol(item,tube_local) < .03,("tube clash",leg)
    moving = trimesh.util.concatenate([socket,*screws])
    meshes = {**old,KEY:moving,"knee_cap_selftap":old["knee_cap_m3x8"]}
    report["motion"] = v36.check_motion(meshes)
    # Added socket material and screws tested against full chassis at sampled
    # yaw/hip/knee positions. Avoid claiming untested adjacent-leg clearance.
    for yaw in (-35,0,35):
        for hip in (-110,-75,-40,0,30):
            for knee in (-30,-15,0,20):
                T = v36.shifted_frames(yaw_deg=yaw,femur_deg=hip,tibia_deg=knee)
                world = v37.transform(moving,T["tibia"]@g.base.MH)
                for k in ("chassis_bottom","chassis_top_rigid","top_hatch_rigid"):
                    assert g._inter_vol(world,old[k]) < .03,("tibia chassis",yaw,hip,knee,k)
    report["tibia_chassis_samples"] = {"yaw":[-35,0,35],"hip":[-110,-75,-40,0,30],"knee":[-30,-15,0,20]}
    report["driver_access"] = "Four Ø5.5x50mm approaches clear on detached bracket/socket; install before attaching C bracket to knee servo"
    report["old_volume_mm3"],report["new_volume_mm3"] = float(before.volume),float(socket.volume)
    return report


def design_spec(report):
    s = yaml.safe_load((BASELINE/"v37-design_spec.yaml").read_text())
    s["revision_note"] = MESSAGE+" "+REASON
    s["tibia_inner_selftap"] = {"baseline":"v37","reason":REASON,"checks":report,
        "assembly":"Four inner3x8 self-tappers enter through metal C web into printed socket. Two outer M3 machine screws and nylocs remain unchanged. Attach socket to detached C before mounting on knee servo; no inner nuts/inserts or nut access windows. Fit-test actual screws first."}
    s["front_receiver"]["tibia_attachment"] = "Four inner3x8 plastic self-tappers on14mm PCD; two outer M3 through-bolts into original captive nylocs on37mm span"
    s["hardware_guidance"]["front_receiver_screws"] = "Femur: unchanged six3x8 self-tappers. Tibia: four inner3x8 self-tappers, Ø2.5x7mm pilots; two outer M3 machine screws/nylocs retain original measured-length requirement."
    s["tibia"]["front_screw_access"] = {"inner_sites":4,"central_pattern":"Four blind self-tapping pilots; no nuts/inserts or radial access slots",
        "outer_pair":"Unchanged two rear-accessible nyloc pockets","assembly_order":"Attach socket to detached C bracket, then mount C on knee servo. Tube fit unchanged."}
    s["parts"][KEY].update(description="Tibia socket with four blind inner self-tapping pilots, two original outer captive-nyloc sites and continuous30mm tube support. Obsolete inner nut windows filled; tube stop/bore and outside envelope unchanged.")
    s["parts"][SCREW] = {"description":"3x8 self-tapping screw for plastic, through knee C web into tibia inner receiver","material":"steel","printable":False,"cots":True,"qty_per_robot":24}
    return yaml.safe_dump(s,sort_keys=False,allow_unicode=True)


def main():
    source,old = inputs()
    socket = make_socket(old[KEY]); scene = compose(source)
    OUT.mkdir(exist_ok=True)
    socket.export(OUT/(KEY+".stl"))
    print("Socket generated; checking receiving walls, tube fit and motion",flush=True)
    report = verify(source,old,socket,scene)
    # Broad metal-mating face down; horn and tube datums are unaffected.
    printmesh = v37.transform(socket,trimesh.geometry.align_vectors([1,0,0],[0,0,1]))
    printmesh.apply_translation([-printmesh.bounds.mean(axis=0)[0],-printmesh.bounds.mean(axis=0)[1],-printmesh.bounds[0,2]])
    assert printmesh.is_volume and printmesh.body_count == 1
    bed_area = float(printmesh.area_faces[np.all(np.abs(printmesh.triangles[:,:,2]) < 1e-5,axis=1)].sum())
    assert bed_area > 1000, bed_area
    report["bed_contact_mm2"] = bed_area
    (OUT/"print").mkdir(exist_ok=True)
    printmesh.export(OUT/"print/tibia_receiver_inner_selftap_flat_face_down.stl")
    (OUT/"scene.json").write_text(json.dumps(scene,indent=2)+"\n")
    (OUT/"checks.json").write_text(json.dumps(report,indent=2)+"\n")
    (OUT/"design_spec.yaml").write_text(design_spec(report))
    print(json.dumps(report,indent=2),flush=True)


if __name__ == "__main__": main()
