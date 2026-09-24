"""Thicken the archived v16 spacer femur yoke without moving its interfaces."""
from pathlib import Path
import sys,json,shutil
import numpy as np
import trimesh
import yaml
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'horn_compression_limiters'))
import make_horn_compression_limiter_concept as lim
hp=lim.hp

def intersect(a,b):return trimesh.boolean.intersection([a,b],engine='manifold')
def main():
 s=json.loads((HERE/'baseline/scene.json').read_text())
 i=next(i for i in s['instances'] if i['id']=='femur-test')
 source=trimesh.load_mesh(HERE/'baseline'/next(m['url'] for m in s['meshes'] if m['id']==i['meshId']))
 source.apply_transform(np.array(i['transform']).reshape(4,4).T)
 assert source.is_volume
 assert hp._YOKE_ARM_T==4
 top=hp.JOINT_HORN_TOP_Z+4;bottom=hp.JOINT_HORN_BOT_Z-4
 additions=[]
 for face,direction in [(top,1),(bottom,-1)]:
  section=source.section([0,0,1],[0,0,face-direction*.05])
  planar,_=section.to_2D(to_2D=np.eye(4))
  from shapely.geometry import box
  for polygon in planar.polygons_full:
   polygon=polygon.intersection(box(-100,-100,52,100))
   if polygon.is_empty:continue
   slab=trimesh.creation.extrude_polygon(polygon,3.05,engine='earcut')
   slab.apply_translation([0,0,face-.05 if direction==1 else face-3])
   # Keep original central screw seating depth; perimeter washers already
   # sit 1.1 mm above the old arm surface on the spacer bosses.
   slab=trimesh.boolean.difference([slab,lim._cyl_z(4,face-4,face+4,hp.SERVO_OUTPUT_X,0)],engine='manifold')
   # Recess each 7 mm washer to the existing 10 mm spacer seat.
   for x,y in hp._disc_horn_bolt_centres():
    z0,z1=(face+1.1,face+4) if direction==1 else (face-4,face-1.1)
    slab=trimesh.boolean.difference([slab,lim._cyl_z(3.65,z0,z1,x,y)],engine='manifold')
   additions.append(slab)
 result=trimesh.boolean.union([source,*additions],engine='manifold')
 result.merge_vertices(digits_vertex=5)
 result.update_faces(result.nondegenerate_faces());result.update_faces(result.unique_faces());result.remove_unreferenced_vertices()
 print("mesh",source.is_volume,source.body_count,result.is_volume,result.body_count,flush=True)
 assert result.is_volume and result.body_count==1
 assert abs(trimesh.boolean.difference([source,result],engine='manifold').volume)<.01,'original geometry removed'
 delta=trimesh.boolean.difference([result,source],engine='manifold')
 # Material grows outward; counterbores preserve existing hardware seats.
 assert delta.volume>100
 assert np.allclose(result.bounds[:,:2],source.bounds[:,:2],atol=.001)
 assert abs(result.bounds[0,2]-(bottom-3))<.001
 assert abs(result.bounds[1,2]-max(source.bounds[1,2],top+3))<.001
 assert delta.bounds[1,0]<52.001
 for face,direction in [(top,1),(bottom,-1)]:
  z0,z1=(face+1.11,face+4) if direction==1 else (face-4,face-1.11)
  for x,y in hp._disc_horn_bolt_centres():
   assert abs(intersect(result,lim._cyl_z(3.6,z0,z1,x,y)).volume)<.001,'washer access blocked'
 gap=trimesh.creation.box([200,200,top-bottom-.1]);gap.apply_translation([0,0,(top+bottom)/2])
 assert abs(intersect(delta,gap).volume)<.01
 for probe in lim._yoke_limiter_cuts(4.55):assert abs(intersect(result,probe).volume)<.001
 for face,direction in [(top,1),(bottom,-1)]:
  probe=lim._cyl_z(3.9,face,face+3.2,hp.SERVO_OUTPUT_X,0) if direction==1 else lim._cyl_z(3.9,face-3.2,face,hp.SERVO_OUTPUT_X,0)
  assert abs(intersect(delta,probe).volume)<.001
 out=HERE/'stl';out.mkdir(exist_ok=True)
 for n,m in enumerate(s['meshes']):
  dst=out/f'{n}.stl';shutil.copy2(HERE/'baseline'/m['url'],dst);m['url']=str(dst.relative_to(HERE))
 # Choose the same broad-side printing convention as the source generator.
 choices=[]
 for axis in [None,[1,0,0],[0,1,0]]:
  T=np.eye(4) if axis is None else trimesh.transformations.rotation_matrix(np.pi/2,axis)
  p=result.copy();p.apply_transform(T);choices.append((p.extents[2],T,p))
 _,T,printed=min(choices,key=lambda a:a[0])
 shift=np.array([-printed.bounds[:,0].mean(),-printed.bounds[:,1].mean(),-printed.bounds[0,2]])
 printed.apply_translation(shift);T[:3,3]=shift
 import manifold3d as mf
 mm=mf.Mesh(np.array(printed.vertices,dtype=np.float32),np.array(printed.faces,dtype=np.uint32),tolerance=1e-4);mm.merge()
 solid=mf.Manifold(mm);assert solid.status()==mf.Error.NoError
 raw=solid.to_mesh();printed=trimesh.Trimesh(raw.vert_properties[:,:3],raw.tri_verts)
 printed.export(out/'femur_yoke_7mm_arms_spacers.stl')
 assert trimesh.load_mesh(out/'femur_yoke_7mm_arms_spacers.stl').is_volume
 s['meshes'].append({'id':'thicker-femur-print','url':'stl/femur_yoke_7mm_arms_spacers.stl','name':'Femur yoke — 7 mm arms, 4.5 × 10 mm spacers'})
 assembly=np.eye(4)
 i.update(meshId='thicker-femur-print',printMeshId='thicker-femur-print',transform=(assembly@np.linalg.inv(T)).T.flatten().tolist(),name='Femur yoke — thicker 7 mm arms with 4.70 mm spacer bores')
 restored=printed.copy();restored.apply_transform(np.linalg.inv(T));assert np.allclose(restored.bounds,result.bounds)
 plate=trimesh.Scene();p=printed.copy();p.apply_translation([128,128,0]);plate.add_geometry(p,geom_name='thicker_femur_yoke');plate.export(HERE/'femur_yoke_7mm_spacer_plate.3mf')
 assert np.allclose(trimesh.load(HERE/'femur_yoke_7mm_spacer_plate.3mf',force='scene').bounds,plate.bounds)
 s['source']='concepts/femur_yoke_7mm/make_variant.py';s['name']='Spacer build — femur yoke with 7 mm arms';s.pop('analysis',None)
 (HERE/'scene.json').write_text(json.dumps(s,indent=2)+'\n')
 d=yaml.safe_load((HERE/'baseline/design_spec.yaml').read_text())
 kind=i['partType'];d['parts'][kind].update(description=i['name'],manufacturing='fdm',arm_thickness_mm=7,output_stl='stl/femur_yoke_7mm_arms_spacers.stl')
 report={'pass':True,'sourceVersion':'v25','armThicknessBeforeMm':4,'armThicknessAfterMm':7,'addedVolumeMm3':round(float(delta.volume),2),'spacer':'4.5 OD x 10 mm','spacerBoreMm':4.7,'washerRecessDiameterMm':7.3,'armOutwardGrowthMm':3,'yokeExtensionMm':2,'checks':['single watertight solid','all original geometry retained','servo gap unchanged','outward growth limited to 3 mm per arm; knee holder unchanged', 'washer access clear','spacer paths clear','central screw seats unchanged','print transform and 3MF round trip']}
 d['thicker_femur_yoke']=report
 (HERE/'design_spec.yaml').write_text(yaml.safe_dump(d,sort_keys=False));(HERE/'geometry_report.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
if __name__=='__main__':main()
