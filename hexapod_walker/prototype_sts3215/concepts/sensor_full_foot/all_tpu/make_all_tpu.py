"""Two-part 95A TPU concept. Compliance, return force and retention unvalidated."""
from pathlib import Path
import importlib.util,json
import numpy as np
import trimesh as tm
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('base',HERE.parent/'make_foot.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
cyl,box,union,diff,overlap=b.cyl,b.box,b.union,b.diff,b.overlap

def main():
 hemi=tm.boolean.intersection([tm.creation.uv_sphere(radius=9.5,count=[64,128]),box([21,21,11],[0,0,-5.5])],engine='manifold')
 # No guide bores: a continuous backing supports the entire sensor.
 groove=diff([cyl(10,.3,1.3),cyl(8.85,.2,1.4)])
 foot=diff([union([hemi,cyl(9.5,-.02,2)]),groove])
 film=union([cyl(5,2,2.2),box([6.5,5,.2],[0,6,2.1])])
 # A small conical roof reduces the internal bridge when printed socket-rim down.
 cone=tm.creation.cone(radius=2.8,height=2.8,sections=128)
 cone.apply_transform(tm.transformations.rotation_matrix(np.pi,[1,0,0]));cone.apply_translation([0,0,8.1])
 bore=union([cyl(4.1,9.5,26.8),cyl(2.8,8.09,9.51),cone])
 body=diff([cyl(8,2.6,26.7),bore,cyl(5.3,2.5,3.4),box([7.1,16.2,2],[0,11.9,3])])
 pad=cyl(3.25,2.4,3.42)
 assert overlap(cyl(3.25,3.41,3.5),body)>.99*np.pi*3.25**2*.09
 # Bowed membrane is fused to the socket; only its lower cuff stretches over the cup.
 profile=np.array([[9.9,.4],[9.9,1.2],[10.4,1.6],[11.4,2.6],[10.4,3.6],[8.65,4.7],[8.65,5.5],[7.65,5.5],[7.65,4.8],[8.15,4.6],[9.8,3],[10.5,2.6],[9.8,2.2],[9.65,1.3],[8.95,1.1],[8.95,.4]])
 collar=tm.creation.revolve(np.vstack([profile,profile[0]]),sections=128)
 if collar.volume<0:collar.invert()
 collar=diff([collar,box([7.1,20,2.2],[0,10,2.6])])
 upper=union([body,pad,collar])
 rod=diff([cyl(4,9.5,35),cyl(3,9.4,35.1)])
 meshes={'tpu_sensor_cup':foot,'tpu_socket_and_return':upper,'sensor_reference':film,'carbon_tube_reference':rod}
 for n,m in meshes.items():
  assert m.is_watertight and m.volume>0 and len(m.split())==1,n
 for a,z in [(foot,upper),(film,upper),(rod,upper),(film,foot)]:assert overlap(a,z)<1e-6
 for dz in np.linspace(0,.6,7):
  assert overlap(b.moved(body,-dz),foot)<1e-6
  assert overlap(b.moved(body,-dz),film)<1e-6
 assert overlap(b.moved(body,-.7),foot)>.1,'missing bumper contact'
 assert overlap(b.moved(rod,-.1),body)>.01,'missing rod seat'
 tail=box([6.5,20,.2],[0,10,2.1])
 assert overlap(tail,upper)<1e-6
 assert overlap(tail,b.moved(body,-.6))<1e-6
 # Hook geometry captures cup at rest; this is NOT a TPU pull-off test.
 assert overlap(b.moved(foot,-.2),collar)>.01,'missing cuff retention'
 scene=dict(name='Two-part all-TPU contact foot — 95A prototype',buildId='prototype_sts3215/sensor-full-foot',units='mm',center=[0,0,8],meshes=[],instances=[])
 parts={};plate=tm.Scene();x=10
 colors={'tpu_sensor_cup':'#e9a13d','tpu_socket_and_return':'#945dc7','sensor_reference':'#249796','carbon_tube_reference':'#40454b'}
 for n,m in meshes.items():
  printed=n.startswith('tpu_');mat=np.eye(4);mm=m.copy()
  if printed:
   mat=tm.transformations.rotation_matrix(np.pi,[1,0,0]);mm.apply_transform(mat)
   shift=-mm.bounds[0,2];mm.apply_translation([0,0,shift]);mat[2,3]=shift;mat=np.linalg.inv(mat)
   check=mm.copy();check.apply_transform(mat);assert np.allclose(check.vertices,m.vertices)
   single=tm.Scene(mm);single.units='mm';single.export(str(HERE/(n+'.3mf')))
   q=mm.copy();q.apply_translation([x-q.bounds[0,0],10-q.bounds[0,1],0]);x=q.bounds[1,0]+10;plate.add_geometry(q,node_name=n,geom_name=n)
  mm.export(HERE/(n+'.stl'))
  scene['meshes'].append(dict(id=n,url=n+'.stl'));scene['instances'].append(dict(id=n,meshId=n,partType=n,name=n.replace('_',' '),color=colors[n],cots=not printed,transform=mat.T.flatten().tolist()))
  parts[n]=dict(kind='printed' if printed else 'purchased',label=n.replace('_',' '))
  if printed:parts[n]['material']='TPU 95A (user confirmed hardness; brand unspecified)'
 plate.units='mm';plate.export(str(HERE/'all_tpu_parts.3mf'))
 workflow=dict(schema=1,parts=parts,instructions=[dict(id='assembly',title='Two-part TPU prototype',text='Designed for user-confirmed TPU 95A. Print the cup sensor-face down and socket top-rim down using the provided orientations; inspect the internal rod-seat ledge and bellows overhangs in the slicer. The sensor backing, socket and pad need dense fill; compliance is in the thin modeled return wall. Seat the 8/6 mm carbon tube on the internal shoulder, 17.2 mm below the top; secure the tube-to-socket interface with a material-compatible adhesive after checking a sample bond. Attach the 10 mm sensor flat to the cup, preserving its vent/active surface. Align wire opening, place the socket over the sensor, and stretch the lower cuff over the cup rim into its circumferential groove. No screws or metal spring; do not glue the flexing joint. Verify cuff engagement all around. Nominal sensor plus adhesive is 0.2 mm and pad gap is 0.2 mm. Bench-test unloaded baseline, return after sustained compression, gentle straight/angled contacts, pull-off retention and bumper contact. TPU bumper contact is not a rigid force limit. Deformation and load capacity are unvalidated.')])
 report=dict(material='TPU 95A',printed_parts=2,metal_spring=False,screws=False,rod_od_mm=8,rod_id_mm=6,socket_bore_mm=8.2,socket_depth_mm=17.2,foot_od_mm=19,collar_max_od_mm=22.8,sensor_od_mm=10,sensor_plus_adhesive_assumed_mm=.2,pad_diameter_mm=6.5,pad_height_mm=1,initial_pad_gap_mm=.2,nominal_bumper_contact_travel_mm=.6,nominal_pad_compression_at_bumper_mm=.4,checks='watertight connected solids; unloaded clearances; seven body stroke positions; rod seating; wire routing; cuff geometric capture; print transforms',limitations='No TPU deformation simulation, stiffness, trigger force, creep, friction, pull-off or fatigue tests. TPU bumper keeps compressing under load; it is not a hard stop. Collar carries a parallel load path. Socket adhesion needs material-specific testing.')
 for name,data in [('scene.json',scene),('workflow.json',workflow),('dimensions.json',report),('design_spec.yaml',dict(build=dict(id=scene['buildId'],name=scene['name'],units='mm'),parts={n:dict(manufacturing=p['kind'],purpose=p['label'],**({'material':p['material']} if 'material' in p else {})) for n,p in parts.items()}))]:
  (HERE/name).write_text(json.dumps(data,indent=2))
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
