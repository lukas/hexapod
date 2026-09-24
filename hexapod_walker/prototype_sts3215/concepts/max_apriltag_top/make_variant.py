"""Flush, maximum practical square AprilTag in the removable hex hatch."""
from pathlib import Path
import json
import shutil
import sys
import math
import zipfile
import cv2
import numpy as np
import trimesh
from shapely.geometry import Polygon, box, Point
from shapely.ops import unary_union
from shapely.affinity import translate, rotate
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
PROTO = HERE.parents[1]
sys.path[:0] = [str(PROTO), str(PROTO/'apriltag_lids'), str(PROTO/'knee_yoke_apriltag_flag')]
import make_apriltag_lids as lids
import make_knee_yoke_apriltag_flag as flag
BASE = PROTO/'concepts/apriltag_top_hatch/baseline'
TAG_ID = 0
EDGE_MARGIN = 1.0
SKIN = .6


def main():
    out = HERE/'stl';out.mkdir(exist_ok=True)
    scene = json.loads((BASE/'scene.json').read_text())
    source = next(m for m in scene['meshes'] if m['id']=='stl:top_hatch_rigid')
    original = trimesh.load_mesh(BASE/source['url'])
    top = float(original.bounds[1,2])
    section, trans = original.section([0,0,1],[0,0,top-.05]).to_2D()
    outline = max(section.polygons_full,key=lambda p:p.area)
    outline = translate(outline,trans[0,3],trans[1,3])
    holes = [Polygon(r) for r in outline.interiors]
    mounting = [h for h in holes if h.centroid.distance(Point(0,0))>60]
    obsolete = [h for h in holes if h not in mounting]
    assert len(mounting)==6 and len(obsolete)==9
    # Close the centre opening and eight old electronics holes over the 4mm sheet only.
    plugs = [flag.extrude_2d(h.buffer(.10),4.0,top-4.0) for h in obsolete]
    solid = flag.boolean_union([original,*plugs])
    face = Polygon(outline.exterior, [h.exterior.coords for h in mounting])
    usable = Polygon(outline.exterior).buffer(-EDGE_MARGIN)
    # Central regular hex is symmetric: for any orientation, a translated
    # square cannot exceed the best centered square. Search the 30-degree
    # fundamental interval at .05-degree steps, with binary size refinement.
    best=(0.,0.)
    for angle in np.linspace(0,30,601):
        lo,hi=0.,140.
        for _ in range(24):
            side=(lo+hi)/2
            q=rotate(box(-side/2,-side/2,side/2,side/2),angle,origin=(0,0))
            if usable.covers(q):lo=side
            else:hi=side
        if lo>best[0]:best=(lo,float(angle))
    size=math.floor(best[0]) # whole millimetres, with the prescribed edge margin
    angle=best[1]
    grid=lids.tag_grid(TAG_ID);cell=size/10
    cells=[]
    for row in range(10):
        for col in range(10):
            if grid[row][col]==0:
                x=-size/2+col*cell;y=size/2-row*cell
                cells.append(rotate(box(x,y-cell,x+cell,y),angle,origin=(0,0)))
    black=trimesh.util.concatenate([flag.extrude_2d(poly,SKIN,top-SKIN) for poly in cells])
    white=flag.boolean_difference(solid,[black])
    print('geometry',white.is_watertight,len(white.split()),black.is_watertight,solid.is_watertight, flush=True)
    assert white.is_watertight and len(white.split())==1 and black.is_watertight
    partition_error=abs(white.volume+black.volume-solid.volume)
    assert partition_error<.01,partition_error
    square=rotate(box(-size/2,-size/2,size/2,size/2),angle,origin=(0,0))
    assert face.covers(square)
    for h in mounting:
        assert not solid.contains([[h.centroid.x,h.centroid.y,top-2]])[0]
        assert square.distance(h)>3.0
    added=trimesh.boolean.difference([solid,original],engine='manifold')
    overlaps=[]
    for inst in scene['instances']:
        if inst['meshId']=='stl:top_hatch_rigid':continue
        a=next(m for m in scene['meshes'] if m['id']==inst['meshId'])
        other=trimesh.load_mesh(BASE/a['url']);other.apply_transform(np.array(inst['transform']).reshape(4,4).T)
        if np.any(added.bounds[1]<=other.bounds[0]) or np.any(other.bounds[1]<=added.bounds[0]):continue
        volume=abs(trimesh.boolean.intersection([added,other],engine='manifold').volume)
        if volume>.01:overlaps.append({'instance':inst['id'],'volume_mm3':volume})
    assert not overlaps,overlaps
    printable=[]
    for name,mesh in [('white',white),('black',black)]:
        mesh.export(out/f'hatch_{name}_assembly.stl')
        m=mesh.copy();m.apply_transform(trimesh.transformations.rotation_matrix(np.pi,[1,0,0]));m.apply_translation([0,0,top])
        m.export(out/f'hatch_{name}_print.stl');printable.append(m)
    portable=HERE/'hex_top_apriltag_0_98mm.3mf'
    lids.write_3mf(portable,[(TAG_ID,*printable)],arrange=False)
    root=lids.BAMBU_MACHINE_PROFILE.parent.parent
    lids.BAMBU_MACHINE_PROFILE=root/'machine/Bambu Lab H2D 0.4 nozzle.json'
    lids.BAMBU_PROCESS_PROFILE=root/'process/0.20mm Standard @BBL H2D.json'
    lids.BAMBU_PLA_PROFILE=root/'filament/Generic PLA @BBL H2D.json'
    bambu=HERE/'hex_top_apriltag_0_98mm_H2D.3mf'
    assert lids.write_bambu_project(bambu,portable)
    # Camera-facing preview, not the mirrored build-plate face.
    fig,ax=plt.subplots(figsize=(8,7),dpi=160)
    ax.fill(*outline.exterior.xy,color='#f8f8f8',edgecolor='#777777',linewidth=1)
    for h in mounting:ax.fill(*h.exterior.xy,color='#d7dbe1')
    for poly in cells:ax.fill(*poly.exterior.xy,color='#101010',linewidth=0)
    ax.set_aspect('equal');ax.set_xlim(-90,90);ax.set_ylim(-80,80);ax.axis('off')
    ax.set_title(f'Tag36h11 ID 0 · {size} mm including white border\n{size*.8:g} mm black square · flush two-colour surface',fontsize=13)
    fig.tight_layout();fig.savefig(HERE/'preview.png',facecolor='white');plt.close(fig)
    detector=cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11),cv2.aruco.DetectorParameters())
    _,ids,_=detector.detectMarkers(cv2.imread(str(HERE/'preview.png'),cv2.IMREAD_GRAYSCALE));assert ids is not None and 0 in ids.flatten()
    # Self-contained full assembly with only the hatch changed.
    for a in scene['meshes']:
        path=BASE/a['url']; target=out/('base_'+path.name);shutil.copy2(path,target);a['url']='stl/'+target.name
    scene['meshes'] += [{'id':f'hatch-{c}','name':f'hatch_{c}.stl','url':f'stl/hatch_{c}_assembly.stl'} for c in ['white','black']]
    old=next(i for i in scene['instances'] if i['meshId']=='stl:top_hatch_rigid')
    scene['instances'].remove(old)
    for c in ['white','black']:
        i=dict(old);i.update(id=f'hatch-{c}',meshId=f'hatch-{c}',name=f'98 mm AprilTag hatch — {c}',partType=f'apriltag_hatch_{c}',color='#f8f8f8' if c=='white' else '#101010');scene['instances'].append(i)
    for j in scene.get('joints',[]):
        if old['id'] in j.get('instances',[]):j['instances']=[x for x in j['instances'] if x!=old['id']]+['hatch-white','hatch-black']
    scene.update(name='Hexagonal top — integrated 98 mm AprilTag',buildId='prototype_sts3215/max-apriltag-top',source='concepts/max_apriltag_top/make_variant.py')
    scene.pop('checksConfig',None);scene.pop('designSpecUrl',None)
    (HERE/'scene.json').write_text(json.dumps(scene,indent=2)+'\n')
    report={'pass':True,'tag_id':0,'outer_tag_mm':size,'black_square_mm':size*.8,'cell_mm':cell,'skin_mm':SKIN,'angle_deg':angle,
      'max_square_with_1mm_margin_mm':best[0],'actual_edge_margin_mm':square.distance(Polygon(outline.exterior).boundary),
      'six_mounting_holes_preserved':True,'registration_lip_preserved':True,'closed_internal_openings':len(obsolete),
      'external_bounds_unchanged':bool(np.allclose(original.bounds,solid.bounds)),'colour_partition_error_mm3':partition_error,
      'new_material_collisions':overlaps,'decoded_ids':ids.flatten().tolist(),'limitations':'CAD-derived hatch variant. No physical fit or overhead-leg motion test; update tracker black-square size to 0.0784 m.'}
    (HERE/'geometry_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
