from pathlib import Path
import importlib.util,json
import numpy as np
import trimesh as tm
p=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('base',p/'make_foot.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
cyl,box,union,diff,overlap=b.cyl,b.box,b.union,b.diff,b.overlap
out=p/'metal_spring';out.mkdir(exist_ok=True)
centers=[(11,0),(-11,0),(0,-11)]
hemi=tm.boolean.intersection([tm.creation.uv_sphere(radius=14,count=[48,96]),box([30,30,15],[0,0,-7.5])],engine='manifold')
foot=diff([union([hemi,cyl(14,-.02,2)]),*[cyl(.85,-3.5,2.1,x,y) for x,y in centers]])
body=diff([cyl(8,2.6,22.6),cyl(4.1,5.4,22.7),cyl(5.3,2.5,3.4),box([7.1,16.2,2],[0,11.9,3])])
ears=[]
for x,y in centers:
 ear=union([cyl(2.8,7,9,x,y),box([abs(x)+.1 if x else 5.6,abs(y)+.1 if y else 5.6,2],[x/2,y/2,8])])
 ears.append(ear)
body=diff([union([body,*ears]),cyl(4.1,5.4,22.7),*[cyl(1.75,6.9,9.1,x,y) for x,y in centers]])
film=union([cyl(5,2,2.2),box([6.5,5,.2],[0,6,2.1])])
meshes={'petg_foot':foot,'petg_socket':body,'silicone_pad':cyl(3.25,2.4,3.4),'sensor_reference':film}
# Nominal spring envelope only: source/rate to be selected after bench trial.
def spring(x,y):
 t=np.linspace(0,10*np.pi,601);r=2.15;wire=.3
 pts=np.column_stack([x+r*np.cos(t),y+r*np.sin(t),2.15+4.7*t/t[-1]])
 tangent=np.gradient(pts,axis=0);tangent/=np.linalg.norm(tangent,axis=1)[:,None]
 normal=np.column_stack([np.cos(t),np.sin(t),np.zeros(len(t))]);binormal=np.cross(tangent,normal)
 a=np.linspace(0,2*np.pi,12,endpoint=False)
 verts=(pts[:,None,:]+wire/2*(np.cos(a)[None,:,None]*normal[:,None,:]+np.sin(a)[None,:,None]*binormal[:,None,:])).reshape(-1,3)
 faces=[]
 for i in range(len(t)-1):
  for j in range(12):
   k=i*12+j;n=i*12+(j+1)%12;faces.extend([[k,n,n+12],[k,n+12,k+12]])
 for j in range(1,11):faces.extend([[0,j+1,j],[(len(t)-1)*12,(len(t)-1)*12+j,(len(t)-1)*12+j+1]])
 m=tm.Trimesh(verts,faces);m.fix_normals();return m
for i,(x,y) in enumerate(centers,1):
 meshes[f'spring_{i}']=spring(x,y)
 meshes[f'sleeve_{i}']=diff([cyl(1.5,2,9,x,y),cyl(1.1,1.9,9.1,x,y)])
 meshes[f'washer_{i}']=diff([cyl(2.5,9,9.5,x,y),cyl(1.1,8.9,9.6,x,y)])
 meshes[f'screw_{i}']=union([cyl(1,-2.5,9.5,x,y),diff([cyl(1.8,9.5,11,x,y),box([.65,4,.6],[x,y,10.9])])])
for name,m in meshes.items():assert m.is_watertight and m.volume>0,name
for travel in np.linspace(0,.6,7):
 moved=b.moved(body,-travel)
 assert overlap(moved,foot)<1e-6
 assert overlap(moved,film)<1e-6
 for name,m in meshes.items():
  if name.startswith(('sleeve','washer','screw')):assert overlap(moved,m)<1e-4,(name,travel,overlap(moved,m))
assert overlap(b.moved(body,-.7),foot)>.1
assert overlap(cyl(3.25,3.41,3.49),body)>.99*np.pi*3.25**2*.08
scene=dict(name='PETG contact foot with metal springs and screw retention',buildId='prototype_sts3215/sensor-full-foot',units='mm',center=[0,0,5],meshes=[],instances=[])
parts={};plate=tm.Scene();xpos=10
for name,m in meshes.items():
 printed=name.startswith('petg');matrix=np.eye(4);url=f'{name}.stl'
 color='#e9a13d' if name=='petg_foot' else '#97aac3' if printed else '#249796' if name=='sensor_reference' else '#dd617c' if name=='silicone_pad' else '#d9dcdf'
 if printed:
  mm=m.copy();rot=tm.transformations.rotation_matrix(np.pi,[1,0,0]);mm.apply_transform(rot);shift=-mm.bounds[0,2];mm.apply_translation([0,0,shift]);rot[2,3]=shift;matrix=np.linalg.inv(rot)
  mm.export(out/url)
  single=tm.Scene(mm);single.units='mm';single.export(str(out/f'{name}.3mf'))
  pm=mm.copy();lo=pm.bounds[0];pm.apply_translation([xpos-lo[0],10-lo[1],0]);xpos=pm.bounds[1,0]+10;plate.add_geometry(pm,node_name=name,geom_name=name)
 else:m.export(out/url)
 scene['meshes'].append(dict(id=name,url=url));scene['instances'].append(dict(id=name,meshId=name,partType=name,name=name.replace('_',' '),color=color,cots=not printed,transform=matrix.T.flatten().tolist()))
 parts[name]=dict(kind='printed' if printed else 'purchased',label=name.replace('_',' '))
 if printed:parts[name]['material']='PETG'
plate.units='mm';plate.export(str(out/'petg_all_parts.3mf'))
(out/'scene.json').write_text(json.dumps(scene,indent=2))
(out/'workflow.json').write_text(json.dumps(dict(schema=1,parts=parts,instructions=[dict(id='assembly',title='Metal spring prototype',text='Print two PETG parts. Fit sensor and 6.5 x 1 mm silicone pad. Place three 7 mm metal spacer sleeves and compression springs on the foot, slide socket ears over sleeves, fit washers and M2 x 12 screws into foot pilots. Screws clamp sleeves, never moving ears. Spring geometry is illustrative: select low-rate springs and bench-test contact/release. See README for dimensions and limitations.')]),indent=2))
(out/'design_spec.yaml').write_text('build:\n  id: prototype_sts3215/sensor-full-foot\n  name: PETG foot with metal return springs\n  units: mm\n  status: geometric prototype; spring selection and physical validation pending\nintent: Ground-contact detection with two PETG prints, metal guides and springs, silicone pressure pad.\n')
print('All meshes watertight; seven rigid travel positions, retainer clearances, stop and pad backing passed.')
