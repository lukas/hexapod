"""Close the inner end of the extended tibia tube socket with a 2mm wall."""
from pathlib import Path
import sys,json,shutil
import numpy as np
import trimesh
import yaml
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'horn_compression_limiters'))
import make_horn_compression_limiter_concept as lim
hp=lim.hp

def inter(a,b):return trimesh.boolean.intersection([a,b],engine='manifold')
def diff(a,b):return trimesh.boolean.difference([a,b],engine='manifold')
def cx(r,x0,x1):
 m=trimesh.creation.cylinder(radius=r,height=x1-x0,sections=96);m.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0]));m.apply_translation([(x0+x1)/2,0,hp.JOINT_SOCKET_Z]);return m

def main():
 s=json.loads((HERE/'baseline/scene.json').read_text());i=next(i for i in s['instances'] if i['id']=='tibia-test')
 src=trimesh.load_mesh(HERE/'baseline'/next(m['url'] for m in s['meshes'] if m['id']==i['meshId']))
 A=np.array(i['transform']).reshape(4,4).T;A[1,3]-=78;src.apply_transform(A)
 assert src.is_volume
 inner=hp._YOKE_SOCKET_X+2;end=inner+2
 wall=cx(4.8,inner,end)
 result=trimesh.boolean.union([src,wall],engine='manifold')
 result.merge_vertices(digits_vertex=5);result.update_faces(result.nondegenerate_faces());result.update_faces(result.unique_faces());result.remove_unreferenced_vertices()
 assert result.is_volume and result.body_count==1
 assert np.allclose(result.bounds,src.bounds)
 assert abs(diff(src,result).volume)<.01
 # Tube still enters freely from the outer end; the back is fully closed.
 assert abs(inter(result,cx(4.02,end+.01,src.bounds[1,0]+5)).volume)<.01
 probe=cx(4,inner+.01,end-.01);assert inter(result,probe).volume>probe.volume*.999
 delta=diff(result,src);assert abs(diff(delta,cx(4.06,inner-.01,end+.01)).volume)<.01
 out=HERE/'stl';out.mkdir(exist_ok=True)
 for n,m in enumerate(s['meshes']):
  dst=out/f'{n}.stl';shutil.copy2(HERE/'baseline'/m['url'],dst);m['url']=str(dst.relative_to(HERE))
 P=np.linalg.inv(A);p=result.copy();p.apply_transform(P);assert abs(p.bounds[0,2])<.001
 p.export(out/'tibia_yoke_tube_stop.stl');assert trimesh.load_mesh(out/'tibia_yoke_tube_stop.stl').is_volume
 s['meshes'].append({'id':'tibia-stop-print','url':'stl/tibia_yoke_tube_stop.stl','name':'Tibia yoke — 2mm internal tube stop'})
 i.update(meshId='tibia-stop-print',printMeshId='tibia-stop-print',name='Tibia yoke — closed-back carbon tube socket')
 plate=trimesh.Scene();p.apply_translation([128,128,0]);plate.add_geometry(p,geom_name='tibia_yoke');plate.export(HERE/'tibia_socket_stop_plate.3mf')
 assert np.allclose(trimesh.load(HERE/'tibia_socket_stop_plate.3mf',force='scene').bounds,plate.bounds)
 s['source']='concepts/tibia_socket_stop/make_variant.py';s['name']='Spacer build — tibia carbon tube stop';(HERE/'scene.json').write_text(json.dumps(s,indent=2)+'\n')
 d=yaml.safe_load((HERE/'baseline/design_spec.yaml').read_text());d['parts'][i['partType']].update(description=i['name'],manufacturing='fdm',output_stl='stl/tibia_yoke_tube_stop.stl')
 report={'pass':True,'sourceVersion':'v24','stopThicknessMm':2,'stopXRangeMm':[inner,end],'tubeODmm':8,'remainingInsertionDepthMm':round(float(src.bounds[1,0]-end),3),'checks':['closed single solid and exported STL','all original geometry retained','outer dimensions unchanged','socket entry clear','tube blocked by full wall','new material confined to socket bore','3MF round trip']}
 d['tibia_socket_stop']=report;(HERE/'design_spec.yaml').write_text(yaml.safe_dump(d,sort_keys=False));(HERE/'geometry_report.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
if __name__=='__main__':main()
