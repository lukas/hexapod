"""One-piece H2D camera calibration AprilGrid, IDs 400-419."""
from pathlib import Path
import sys,json,zipfile,subprocess
import numpy as np
import cv2
import trimesh
from shapely.geometry import box
HERE=Path(__file__).resolve().parent
PROTO=HERE.parent
sys.path[:0]=[str(PROTO/'apriltag_lids'),str(PROTO/'knee_yoke_apriltag_flag')]
import make_apriltag_lids as lids
import make_knee_yoke_apriltag_flag as flag
W,H,T=258.,318.,3.
ROWS,COLS,FIRST=5,4,400
PITCH=63.0
CELL=PITCH/10
TAG=8*CELL
SKIN=.6


def rewrite(path, entries):
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in entries.items():z.writestr(n,b)


def main():
    dictionary=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
    polys=[];tags={};svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">',f'<rect width="{W}" height="{H}" fill="white"/>']
    raster=np.full((int(H*6),int(W*6)),255,np.uint8)
    for r in range(ROWS):
        for c in range(COLS):
            tid=FIRST+r*COLS+c
            marker=cv2.aruco.generateImageMarker(dictionary,tid,8,borderBits=1)
            cx=(c-(COLS-1)/2)*PITCH;cy=((ROWS-1)/2-r)*PITCH
            x0=cx-TAG/2;y1=cy+TAG/2
            for y in range(8):
                for x in range(8):
                    if marker[y,x]!=0:continue
                    px=x0+x*CELL;py=y1-y*CELL
                    polys.append(box(px,py-CELL,px+CELL,py))
                    sx=px+W/2;sy=H/2-py
                    svg.append(f'<rect x="{sx:.6f}" y="{sy:.6f}" width="{CELL}" height="{CELL}" fill="black"/>')
                    xa,ya=round(sx*6),round(sy*6);xb,yb=round((sx+CELL)*6),round((sy+CELL)*6)
                    raster[ya:yb,xa:xb]=0
            tags[str(tid)]={'label':f'AprilGrid row {r} column {c}', 'world_from_tag':{'translation_m':[cx/1000,cy/1000,0.],'euler_xyz_deg':[0.,0.,0.]},
              'corners_board_m_tl_tr_br_bl':[[a/1000,b/1000,0.] for a,b in [(x0,y1),(x0+TAG,y1),(x0+TAG,y1-TAG),(x0,y1-TAG)]]}
    svg.append('</svg>');(HERE/'aprilgrid_400-419.svg').write_text('\n'.join(svg)+'\n');cv2.imwrite(str(HERE/'preview.png'),raster)
    detector=cv2.aruco.ArucoDetector(dictionary,cv2.aruco.DetectorParameters())
    corners,ids,_=detector.detectMarkers(raster);assert ids is not None and sorted(ids.flatten())==list(range(FIRST,FIRST+ROWS*COLS))
    # Confirm decoded corner orientation against the exported metric geometry.
    for found,tid in zip(corners,ids.flatten()):
        expected=np.array(tags[str(tid)]['corners_board_m_tl_tr_br_bl'])[:,:2]*1000
        expected[:,0]=(expected[:,0]+W/2)*6;expected[:,1]=(H/2-expected[:,1])*6
        assert np.max(np.abs(found.reshape(4,2)-expected))<2.0
    black=trimesh.util.concatenate([flag.extrude_2d(p,SKIN,T-SKIN) for p in polys])
    board=flag.extrude_2d(box(-W/2,-H/2,W/2,H/2),T)
    white=flag.boolean_difference(board,[black]);assert white.is_watertight and len(white.split())==1 and black.is_watertight
    error=abs(board.volume-white.volume-black.volume);assert error<.1,error
    white.export(HERE/'board_WHITE.stl');black.export(HERE/'board_BLACK.stl')
    portable=HERE/'aprilgrid_400-419_258x318mm_tower_clearance.3mf';lids.write_3mf(portable,[(400,white,black)],arrange=False)
    # Position before Bambu import so its plate membership metadata is valid.
    import re
    with zipfile.ZipFile(portable) as z: portable_entries={n:z.read(n) for n in z.namelist()}
    xml=portable_entries['3D/3dmodel.model'].decode()
    xml=re.sub(r'(<item\b[^>]*\btransform=")[^"]*',r'\g<1>1 0 0 0 1 0 0 0 1 155 160 0',xml)
    portable_entries['3D/3dmodel.model']=xml.encode();rewrite(portable,portable_entries)
    root=lids.BAMBU_MACHINE_PROFILE.parent.parent
    lids.BAMBU_MACHINE_PROFILE=root/'machine/Bambu Lab H2D 0.4 nozzle.json'
    lids.BAMBU_PROCESS_PROFILE=root/'process/0.20mm Standard @BBL H2D.json'
    lids.BAMBU_PLA_PROFILE=root/'filament/Generic PLA @BBL H2D.json'
    # Export profiles explicitly: automatic arrangement would reserve a tower
    # and move this full-bed board off the plate. Preserve a centered placement.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp);profiles=[]
        for name,p in [('machine',lids.BAMBU_MACHINE_PROFILE),('process',lids.BAMBU_PROCESS_PROFILE),('filament',lids.BAMBU_PLA_PROFILE)]:
            data=lids.resolved_bambu_profile(p)
            if name=='process':data.update(enable_prime_tower='1',prime_tower_width='30',prime_tower_brim_width='2',prime_tower_extra_rib_length='0',brim_type='no_brim',skirt_loops='0')
            q=tmp/(name+'.json');q.write_text(json.dumps(data));profiles.append(q)
        path=HERE/'aprilgrid_400-419_H2D_tower_clearance.3mf'
        cmd=[str(lids.BAMBU_STUDIO),'--outputdir',str(HERE),'--arrange','0','--load-settings',str(profiles[0])+';'+str(profiles[1]),'--load-filaments',str(profiles[2])+';'+str(profiles[2]),'--export-3mf',path.name,str(portable)]
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
        assert result.returncode==0,result.stdout[-3000:]+result.stderr[-3000:]
    lids._patch_bambu_project(path)
    with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist()}
    s=json.loads(entries['Metadata/project_settings.config']);s.update(enable_prime_tower='1',prime_tower_width='30',prime_tower_brim_width='2',prime_tower_extra_rib_length='0',brim_type='no_brim',skirt_loops='0',filament_map=['1','2'],filament_map_mode='Manual',wipe_tower_x=['290'],wipe_tower_y=['20'])
    entries['Metadata/project_settings.config']=json.dumps(s,indent=2).encode()
    # Locate the one board on the shared X=25..325 dual-nozzle region.
    import xml.etree.ElementTree as ET
    key='3D/3dmodel.model';model=ET.fromstring(entries[key]);ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
    items=model.findall('m:build/m:item',ns);assert len(items)==1
    import re
    xml=entries[key].decode()
    xml=re.sub(r'(<item\b[^>]*\btransform=")[^"]*',r'\g<1>1 0 0 0 1 0 0 0 1 155 160 0',xml)
    entries[key]=xml.encode()
    config=ET.fromstring(entries['Metadata/model_settings.config']);plate=config.find('plate')
    for entry in list(plate.findall('model_instance')):plate.remove(entry)
    instance=ET.SubElement(plate,'model_instance')
    for key,value in [('object_id',items[0].get('objectid')),('instance_id','0'),('identify_id','1')]:
        ET.SubElement(instance,'metadata',{'key':key,'value':value})
    entries['Metadata/model_settings.config']=ET.tostring(config,encoding='utf-8',xml_declaration=True)
    rewrite(path,entries)
    with tempfile.TemporaryDirectory() as render_dir:
        result=subprocess.run([str(lids.BAMBU_STUDIO),'--export-png','1','--camera-view','1','--outputdir',render_dir,str(path)],capture_output=True,text=True,timeout=120)
        assert result.returncode==0,result.stderr
        pngs=sorted(Path(render_dir).glob('plate_*.png'));assert pngs
        thumbnail=pngs[0].read_bytes()
        for name in ['Metadata/plate_1.png','Metadata/plate_1_small.png','Metadata/plate_no_light_1.png']:entries[name]=thumbnail
        rewrite(path,entries);(HERE/'plate_preview.png').write_bytes(thumbnail)
    manifest={'schema_version':1,'tag_family':'tag36h11','marker_size_m':TAG/1000,'board_size_m':[W/1000,H/1000],
      'rows':ROWS,'columns':COLS,'first_id':FIRST,'last_id':419,'tag_spacing_ratio':.25,'pitch_m':PITCH/1000,'gap_m':(PITCH-TAG)/1000,
      'world_frame':'origin at board center on printed face; +x printed right; +y printed up; +z out of face',
      'floor_tags':tags,'print_instructions':'H2D dual nozzle 0.4 mm; white and black matte PLA; face up; 100% scale. Board has a dedicated right-side prime-tower lane; tower enabled, no board brim or skirt. Measure pitch and keep flat on a rigid backing for calibration.'}
    (HERE/'calibration_board.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (HERE/'verification.json').write_text(json.dumps({'pass':True,'decoded_ids':sorted(ids.flatten().tolist()),'decoded_corners_match_manifest':True,'white_watertight':True,'black_watertight':True,'material_partition_error_mm3':error},indent=2)+'\n')
    print('Created 258 x 318 mm board with prime-tower lane; 20 decoded tags; marker 50.4 mm, pitch 63 mm.',flush=True)

if __name__=='__main__':main()
