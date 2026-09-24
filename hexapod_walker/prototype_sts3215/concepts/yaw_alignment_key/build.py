"""Long-reach key fitted to co xa_6706_bottom_nuts source assembly.
Run with uv run --with build123d --with trimesh --with manifold3d python build.py.
"""
from pathlib import Path
import json, shutil
import numpy as np
import trimesh
from build123d import Box, Cylinder, Cone, Pos, Align, export_stl, export_step

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'coxa_6706_bottom_nuts'
OUT=HERE/'stl'; OUT.mkdir(exist_ok=True)
A=(Align.CENTER,Align.CENTER,Align.MIN)
HORN_Z=-9.0
SEAT_Z=1.1
BRIDGE_Z=60.3  # 5 mm above actual upper-part bounding box
def cyl(x,z,d,h): return Pos(x,0,z)*Cylinder(d/2,h,align=A)
key=Pos(0,0,BRIDGE_Z)*Box(22,6,5,align=A)
key+=Pos(-23,0,BRIDGE_Z)*Box(28,10,5,align=A)
key-=cyl(-30,BRIDGE_Z-1,4,7)
for x,tip_depth in [(-7,1.5),(7,1.0)]:
    key+=cyl(x,SEAT_Z,5.8,2.0)  # rests on existing 4.7 bore / 7.2 access seat
    key+=cyl(x,SEAT_Z+1.9,4.6,BRIDGE_Z-SEAT_Z-1.8)
    key+=cyl(x,HORN_Z+0.3,2.8,SEAT_Z-HORN_Z-0.3)
    key+=Pos(x,0,HORN_Z)*Cone(1.1,1.4,0.3,align=A)
    key+=cyl(x,HORN_Z-tip_depth+0.6,2.2,tip_depth-0.6)
    key+=Pos(x,0,HORN_Z-tip_depth)*Cone(0.4,1.1,0.6,align=A)
assert key.is_valid and len(key.solids())==1
export_step(key,HERE/'yaw_alignment_key.step')
export_stl(key,OUT/'key_installed.stl',tolerance=.025,angular_tolerance=.1)
tool=trimesh.load(OUT/'key_installed.stl',force='mesh')
assert tool.is_watertight and tool.is_volume
# Handle on the bed, pins up; no support under the small annular shoulders.
P=trimesh.transformations.rotation_matrix(np.pi,[1,0,0]);P[2,3]=BRIDGE_Z+5
printed=tool.copy();printed.apply_transform(P);printed.export(OUT/'yaw_alignment_key_PRINT.stl')
source=json.loads((SOURCE/'scene.json').read_text())
lookup={m['id']:m for m in source['meshes']}
scene={'name':'Long-reach yaw alignment key — fitted to 6706 coxa','units':'mm',
       'center':[25,0,26],'meshes':[],'instances':[]}
for m in source['meshes']:
    dest=f"reference_{m['id'].replace(':','_')}.stl"
    shutil.copy2(SOURCE/m['url'],OUT/dest)
    scene['meshes'].append({'id':m['id'],'name':m['name'] if 'name' in m else m['id'],'url':f'stl/{dest}'})
refs=[]
for i in source['instances']:
    inst=dict(i);inst['cots']=True;inst['role']='reference'
    inst['name']=inst.get('name',inst['id'])+' — existing assembly reference'
    inst.pop('printMeshId',None);scene['instances'].append(inst)
    mesh=trimesh.load(SOURCE/lookup[i['meshId']]['url'],force='mesh')
    mesh.apply_transform(np.array(i['transform']).reshape(4,4).T)
    refs.append((i['id'],mesh))

# Actual source assembly lacks a horn mesh; add an explicitly schematic horn.
horn=trimesh.creation.cylinder(radius=10,height=3,sections=96);horn.apply_translation([0,0,-10.5])
cuts=[]
for x,y in [(7,0),(-7,0),(0,7),(0,-7),(0,0)]:
    c=trimesh.creation.cylinder(radius=1.25 if (x or y) else 1.7,height=5,sections=64)
    c.apply_translation([x,y,-10.5]);cuts.append(c)
horn=trimesh.boolean.difference([horn,*cuts],engine='manifold')
horn.export(OUT/'reference_horn_schematic.stl');refs.append(('horn_schematic',horn))
scene['meshes'] += [{'id':'horn_schematic','url':'stl/reference_horn_schematic.stl'},
                    {'id':'key','url':'stl/yaw_alignment_key_PRINT.stl'}]
def instance(mid,name,T,color,cots=False):
    scene['instances'].append({'id':name,'name':name,'meshId':mid,'partType':mid,'cots':cots,
      'role':'reference' if cots else 'printed','color':color,'transform':T.T.flatten().tolist()})
instance('horn_schematic','Horn — schematic thread envelope',np.eye(4),'#d6ab52',True)
instance('key','Alignment key — installed through both spacers',np.linalg.inv(P),'#25cadb')
T=np.linalg.inv(P);T[0,3]+=90
instance('key','Same key alone — shoulders stop at recessed seats',T,'#25cadb')

collisions={}
for name,mesh in refs:
    v=abs(trimesh.boolean.intersection([tool,mesh],engine='manifold').volume)
    collisions[name]=float(v)
    assert v<.005,(name,v)
for dz in [0.5,2,5,10,20,40,75]:
    moved=tool.copy();moved.apply_translation([0,0,dz])
    for name,mesh in refs:
        v=abs(trimesh.boolean.intersection([moved,mesh],engine='manifold').volume)
        assert v<.005,(dz,name,v)
# The key leaves driver paths free at the other opposite pair.
for y in (-7,7):
    driver=trimesh.creation.cylinder(radius=3,height=80,sections=64)
    driver.apply_translation([0,y,41.1])
    assert abs(trimesh.boolean.intersection([driver,tool],engine='manifold').volume)<.005
# Stop is effective: an extra 0.2 mm down would contact the seat.
deeper=tool.copy();deeper.apply_translation([0,0,-.2])
hub=next(m for n,m in refs if n=='hub')
stop_v=abs(trimesh.boolean.intersection([deeper,hub],engine='manifold').volume)
assert stop_v>.1,stop_v
report={'source':'coxa_6706_bottom_nuts/scene.json','source_upper_z_mm':55.3,
 'horn_face_z_mm':HORN_Z,'stop_seat_z_mm':SEAT_Z,'bridge_underside_z_mm':BRIDGE_Z,
 'reach_from_bridge_to_horn_mm':BRIDGE_Z-HORN_Z,'max_pin_projection_mm':BRIDGE_Z-HORN_Z+1.5,
 'spacer_bore_mm':3.2,'spacer_shank_mm':2.8,'diametral_spacer_clearance_mm':.4,
 'stem_mm':4.6,'shoulder_mm':5.8,'horn_pilot_mm':2.2,
 'collisions_mm3':collisions,'withdrawal_samples_mm':[.5,2,5,10,20,40,75],
 'stop_contact_after_0p2mm_overtravel_mm3':float(stop_v),'driver_envelope_mm':6,
 'watertight':True,'physical_tested':False,
 'limitations':'Existing coxa meshes and sleeves checked. Horn schematic. Servo/chassis absent from source scene; full robot access not validated. Hold tool by hand.'}
(HERE/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
(HERE/'scene.json').write_text(json.dumps(scene,indent=2)+'\n')
print(json.dumps(report,indent=2))
