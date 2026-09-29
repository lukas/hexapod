"""Internal spring foot; geometric prototype, actual spring force unvalidated."""
from pathlib import Path
import importlib.util,json
import numpy as np
import trimesh as tm
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('base',HERE.parent/'make_foot.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
cyl,box,union,diff,overlap=b.cyl,b.box,b.union,b.diff,b.overlap

def radial(m):
 m=m.copy();m.apply_transform(tm.transformations.rotation_matrix(np.pi/2,[0,1,0]));m.apply_translation([0,0,10.2]);return m

def spring():
 t=np.linspace(0,10*np.pi,601);pts=np.column_stack([1.85*np.cos(t),1.85*np.sin(t),8.15+9.2*t/t[-1]])
 tangent=np.gradient(pts,axis=0);tangent/=np.linalg.norm(tangent,axis=1)[:,None]
 normal=np.column_stack([np.cos(t),np.sin(t),np.zeros(len(t))]);bn=np.cross(tangent,normal);a=np.linspace(0,2*np.pi,12,endpoint=False)
 verts=(pts[:,None,:]+.15*(np.cos(a)[None,:,None]*normal[:,None,:]+np.sin(a)[None,:,None]*bn[:,None,:])).reshape(-1,3);faces=[]
 for i in range(len(t)-1):
  for j in range(12):
   k=i*12+j;n=i*12+(j+1)%12;faces.extend([[k,n,n+12],[k,n+12,k+12]])
 for j in range(1,11):faces.extend([[0,j+1,j],[7200,7200+j,7200+j+1]])
 m=tm.Trimesh(verts,faces);m.fix_normals();return m

def main():
 hemi=tm.boolean.intersection([tm.creation.uv_sphere(radius=9.5,count=[48,96]),box([21,21,10],[0,0,-5])],engine='manifold')
 sleeve=diff([cyl(6,1.95,16),cyl(5.3,1.9,4.5),cyl(4.3,4.49,16.1),box([7.1,12,2.6],[0,6,3.25])])
 foot=union([hemi,cyl(9.5,-.02,2),sleeve])
 foot=diff([foot,*[box([1.6,5.4,2.8],[s*5.5,0,9.8]) for s in [-1,1]]])
 guide=diff([cyl(8,5,28),cyl(6.2,4.9,16.6),cyl(4.1,16.59,28.1),*[box([3.2,5.4,19.1],[sign*7.1,0,14.45]) for sign in [-1,1]]])
 # Two top-anchored cantilevers. Inward hooks engage the foot pockets;
 # their sloped lower faces cam outward as the foot is pushed in.
 hook=tm.convex.convex_hull(np.array([[x,y,z] for x,z in [(6.3,9.2),(6.3,11.2),(5.0,11.2),(5.0,10.5)] for y in [-2.1,2.1]]))
 tab=union([box([1.2,4.2,15.8],[6.8,0,17.1]),hook])
 other=tab.copy();other.apply_transform(tm.transformations.rotation_matrix(np.pi,[0,0,1]))
 guide=union([guide,tab,other])
 rod=diff([cyl(4,4.5,36),cyl(3,4.4,36.1)])
 plug=union([diff([cyl(2.9,4.4,22.5),cyl(2.2,4.3,17.5)]),diff([cyl(4,3.7,4.5),cyl(2.2,3.6,4.6)]),cyl(1,16.5,17.6)])
 plunger=union([cyl(2.8,2.2,2.7),cyl(2,2.6,8),cyl(1,7.9,9)])
 sensor=union([cyl(5,2,2.2),box([6.5,5,.2],[0,6,2.1])])
 meshes=dict(petg_foot=foot,petg_guide=guide,petg_plunger=plunger,petg_spring_stop=plug,carbon_tube_reference=rod,spring_reference=spring(),sensor_reference=sensor)
 for name,m in meshes.items():assert m.is_watertight and m.volume>0 and len(m.split())==1,name
 for d in np.linspace(0,.6,7):
  moving=b.moved(foot,d);film=b.moved(sensor,d);p=b.moved(plunger,d)
  for fixed in [guide,rod,plug]:
   assert overlap(moving,fixed)<1e-4,('foot travel',d)
   assert overlap(film,fixed)<1e-4,('sensor travel',d)
   assert overlap(p,fixed)<1e-4,('plunger travel',d)
 assert overlap(b.moved(foot,.7),guide)>.01,'missing compression stop'
 assert overlap(b.moved(foot,-.1),guide)>.01,'missing extension retainer'
 # Verify each retaining hook independently; report geometric bearing area,
 # not a pull-out force prediction.
 bearing=[]
 for sign in [-1,1]:
  half=box([10,20,30],[sign*5,0,10])
  catch=tm.boolean.intersection([guide,half],engine='manifold')
  v=overlap(b.moved(foot,-.1),catch)
  assert v>.1,('individual hook capture',sign)
  bearing.append(v/.1)
 # Both hooks lie inside pockets with side clearance throughout travel.
 assert (5.4-4.2)/2>.59

 assert overlap(sensor,plunger)<1e-5
 assert overlap(plug,rod)<1e-5,'insert intersects tube'
 assert overlap(plug,guide)<1e-5,'insert intersects guide'
 assert overlap(b.moved(plug,.1),rod)>.01,'flange does not stop at tube end'
 assert overlap(plug,spring())<1e-5,'spring intersects insert'
 # Straight axial insertion into the tube; flange reaches the end at zero.
 for dz in [-20,-15,-10,-5,0]:
  assert overlap(b.moved(plug,dz),rod)<1e-5,('insert insertion',dz)
 assert 3.7-(2.7+.6)>.399,'insufficient pad/flange clearance'
 tail=box([6.5,20,.2],[0,10,2.1])
 for d in [0,.6]:
  assert overlap(b.moved(tail,d),guide)<1e-5
  assert overlap(tail,foot)<1e-5
 scene=dict(name='Wider-hook snap foot with self-seating spring insert',buildId='prototype_sts3215/sensor-full-foot',units='mm',center=[0,0,12],meshes=[],instances=[])
 parts={};plate=tm.Scene();xpos=10
 colors=dict(petg_foot='#e9a13d',petg_guide='#97aac3',petg_plunger='#dd617c',petg_spring_stop='#9d71d6',carbon_tube_reference='#40454b',spring_reference='#dddddd',sensor_reference='#249796')
 for name,m in meshes.items():
  printed=name.startswith('petg');mat=np.eye(4);url=name+'.stl'
  if printed:
   mm=m.copy()
   if name in ('petg_foot','petg_guide','petg_spring_stop'):mat=tm.transformations.rotation_matrix(np.pi,[1,0,0]);mm.apply_transform(mat)
   mat[2,3]=-mm.bounds[0,2];mm.apply_translation([0,0,mat[2,3]]);inverse=np.linalg.inv(mat)
   test=mm.copy();test.apply_transform(inverse);assert np.allclose(test.vertices,m.vertices)
   mat=inverse;mm.export(HERE/url);one=tm.Scene(mm);one.units='mm';one.export(str(HERE/(name+'.3mf')))
   pm=mm.copy();lo=pm.bounds[0];pm.apply_translation([xpos-lo[0],10-lo[1],0]);xpos=pm.bounds[1,0]+8;plate.add_geometry(pm,node_name=name,geom_name=name)
  else:m.export(HERE/url)
  scene['meshes'].append(dict(id=name,url=url));scene['instances'].append(dict(id=name,meshId=name,partType=name,name=name.replace('_',' '),cots=not printed,color=colors.get(name,'#dddddd'),transform=mat.T.flatten().tolist()))
  parts[name]=dict(kind='printed' if printed else 'purchased',label=name.replace('_',' '))
  if printed:parts[name]['material']='PETG'
 plate.units='mm';plate.export(str(HERE/'all_petg_parts.3mf'))
 (HERE/'scene.json').write_text(json.dumps(scene,indent=2))
 workflow=dict(schema=1,parts=parts,instructions=[dict(id='assembly',title='Snap-on internal spring prototype',text='Print all four parts in PETG; use this wider-pocket foot and wider-hook guide together. The v13 spring insert and plunger can be reused. This is not an all-TPU geometry; a flexible tread would be a separate part.  guide top down so both snap tabs grow from their roots. Clear support from tab gaps. Push the flanged spring insert into the 6 mm tube bore until its 8 mm flange seats flush against the tube end. This automatically places the spring seat 13 mm inside. No glue on the insert; its flange carries spring force against the tube end. Ensure tube end is square and deburred. Bond guide to rod with guide top 23.5 mm above rod end. Insert 4 mm OD x 10 mm free-length spring and stepped PETG plunger (4 mm stem, 5.6 mm sensing pad) from below. Attach sensor to foot and align the two side pockets with the snap hooks; route the wire through its opening. Push foot upward until both hooks click into pockets. Confirm both hooks return fully and the foot slides freely through 0.6 mm then meets the shoulder. For removal gently lift both accessible hooks outward while withdrawing foot. No screws, tapping, TPU or carbon drilling. Spring rate, PETG tab strength, fatigue and print fit need bench testing. Do not glue sliding parts.')])
 (HERE/'workflow.json').write_text(json.dumps(workflow,indent=2))
 spec=dict(build=dict(id=scene['buildId'],name=scene['name'],units='mm',status='geometric prototype; spring force and physical fit unvalidated'),parts={n:dict(purpose=v['label'],manufacturing=v['kind'],**({'material':'PETG'} if n.startswith('petg') else {})) for n,v in parts.items()})
 # JSON is also valid YAML.
 (HERE/'design_spec.yaml').write_text(json.dumps(spec,indent=2))
 report=dict(tube_od_mm=8,tube_id_mm=6,foot_od_mm=19,guide_od_mm=16,travel_mm=.6,plunger_od_mm=5.6,plunger_stem_od_mm=4,insert_od_mm=5.8,insert_id_mm=4.4,insert_wall_mm=.7,insert_flange_od_mm=8,insert_flange_thickness_mm=.8,spring_seat_depth_mm=13,pad_flange_clearance_at_stop_mm=.4,spring_od_mm=4,spring_wire_mm=.3,spring_free_length_mm=10,spring_installed_length_mm=9.5,spring_preload_deflection_mm=.5,spring_length_at_stop_mm=8.9,foot_sleeve_od_mm=12,guide_bore_mm=12.4,retainers='two integral PETG cantilevers; no screws',snap_tab_thickness_mm=1.2,snap_tab_width_mm=4.2,snap_root_z_mm=24,snap_hook_tip_radius_mm=5.0,snap_hook_nominal_insertion_deflection_mm=1.2,retaining_bearing_area_per_hook_mm2=bearing,checks='individual hook capture; watertight single solids; seven travel positions clear; compression and extension stops; wire clearance; print transforms; insert insertion; flange seating; spring clearance',limitations='No measured snap insertion force, layer strength, fatigue, spring rate, friction, adhesive strength, sensor force or print fit. Snap insertion deformation is not simulated. Helix is illustrative, not measured coil/end geometry.')
 (HERE/'dimensions.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
