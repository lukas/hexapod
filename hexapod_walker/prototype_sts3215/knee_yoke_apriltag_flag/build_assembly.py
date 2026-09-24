#!/usr/bin/env python3
"""Build the complete CAD assembly with the recorded 37 robot AprilTags.

CAD-derived placements are visualization geometry, not tracking calibration.
The base scene is copied, including joint hierarchy and animations.
"""
from pathlib import Path
import json
import shutil
import sys
import numpy as np
import trimesh
import yaml

HERE = Path(__file__).resolve().parent
PROTO = HERE.parent
sys.path[:0] = [str(HERE), str(PROTO), str(PROTO / 'apriltag_lids')]
import hexapod_prototype as hp
import make_knee_yoke_apriltag_flag as flag
import make_apriltag_lids as lids
from check_clearance import print_to_well_transform

OUT = HERE / 'assembly'
BASE = PROTO / 'full_robot_viz'
BUILD_ID = 'prototype_sts3215/apriltag-assembly'


def main():
    OUT.mkdir(exist_ok=True)
    shutil.copytree(BASE / 'stl', OUT / 'stl', dirs_exist_ok=True)
    spec = yaml.safe_load((BASE / 'design_spec.yaml').read_text())
    spec['name'] = 'Hexapod with all recorded AprilTags'
    for kind, purpose in [('chassis_tag', 'Servo-lid-style body pose marker centered over the display'),
                          ('servo_lid', 'Servo housing pose marker on the existing clamp cap'),
                          ('yoke_face', 'Moving link marker, four screw-head cups, 5.4 mm throat and 2 mm outward standoff')]:
        for material in ['white', 'black']:
            spec.setdefault('parts', {})[f'apriltag_{kind}_{material}'] = {
                'description': purpose + '; ' + material + ' material', 'material': 'PETG'}
    (OUT / 'design_spec.yaml').write_text(yaml.safe_dump(spec, sort_keys=False))
    scene = json.loads((BASE / 'scene.json').read_text())
    scene.pop('checksConfig', None)
    scene['name'] = 'Hexapod — all 37 AprilTags, tighter cups and 2 mm wire clearance'
    scene['buildId'] = BUILD_ID
    scene['source'] = 'knee_yoke_apriltag_flag/build_assembly.py'
    scene['metadata'] = {'tagFamily': 'tag36h11', 'placementBasis': 'CAD-derived; not a measured calibration',
                         'cupThroatDiameterMm': 5.4, 'plateOutwardOffsetMm': 2.0}
    layout = json.loads((PROTO / 'hexapod-tracker/configs/hexapod-1-apriltag-layout.json').read_text())
    base_instances = list(scene['instances'])
    report = []
    print_flags = []
    def find(typ, leg):
        return next(i for i in base_instances if i['partType'] == typ and i.get('leg') == leg)
    def matrix(i):
        return np.array(i['transform']).reshape(4, 4).T
    def add(mesh, tid, material, transform, parent, kind, leg, joint):
        name = f'apriltag-{tid}-{material}'
        mesh.export(OUT / 'stl' / f'{name}.stl')
        scene['meshes'].append({'id': name, 'name': f'{name}.stl', 'url': f'stl/{name}.stl'})
        scene['instances'].append({'id': name, 'meshId': name, 'name': f'Tag {tid} · {kind} · {material}',
            'partType': f'apriltag_{kind}_{material}', 'role': 'measurement_accessory',
            'leg': leg, 'joint': joint, 'cots': False,
            'color': '#f8f8f8' if material == 'white' else '#101010',
            'transform': transform.T.flatten().tolist()})
        for j in scene.get('joints', []):
            if parent['id'] in j['instances']:
                j['instances'].append(name)
    # Survey link coordinates x=distal,y=tangential,z=up -> CAD joint-local.
    link_to_local = np.array([[1., 0., 0.], [0., 0., 1.], [0., -1., 0.]])
    axes = {'+x': [1,0,0], '-x': [-1,0,0], '+y': [0,1,0], '-y': [0,-1,0], '+z': [0,0,1], '-z': [0,0,-1]}
    for tag in layout['robot_tags']:
        tid, kind, leg, joint = tag['id'], tag['kind'], tag.get('leg'), tag.get('joint')
        if kind == 'yoke_face':
            parent = find('femur_link' if joint == 'hip' else 'tibia_knee_yoke', leg)
            holder, dims = flag.build_holder(tag_id=tid, head_diameter=flag.DEFAULT_HEAD_D,
                head_height=flag.DEFAULT_HEAD_H, throat_clearance=flag.DEFAULT_THROAT_CLEARANCE)
            white, black = flag.build_colour_parts(holder, tid)
            print_flags.append((tid, white, black))
            assert flag.decoded_tag_id(tid) == tid
            tag_axes = tag['frame_from_tag']['tag_axes_in_frame']
            basis = link_to_local @ np.column_stack([axes[tag_axes[k]] for k in ('x','y','z')])
            normal = basis[:, 2]
            local = np.eye(4)
            local[:3, :3] = basis @ np.diag([-1., 1., -1.])
            face_z = hp._YOKE_TOP_Z1 if normal[2] > 0 else hp._YOKE_BOT_Z0
            local[:3, 3] = [hp.SERVO_OUTPUT_X, 0, face_z]
            local[:3, 3] += normal * dims['total_height_mm']
            transform = matrix(parent) @ local
            # The four cup mouths must land exactly on the CAD bolt circle.
            mouths = np.array([[x,y,dims['total_height_mm'],1] for x,y in flag.bolt_centres_about_output()])
            local_mouths = (local @ mouths.T).T[:, :3]
            assert np.allclose(local_mouths[:,2], face_z)
            assert np.allclose(np.linalg.norm(local_mouths[:,:2] - [hp.SERVO_OUTPUT_X,0], axis=1), 7)
            assert holder.is_watertight and len(holder.split()) == 1
        elif kind == 'servo_lid':
            parent = find(f'{joint}_clamp_cap', leg)
            white, black = lids.build_tag_meshes(tid)
            transform = matrix(parent) @ print_to_well_transform()
        elif kind == 'chassis_tag':
            parent = find('screen', None)
            # User reports a servo-lid-style tag installed over the screen.
            # Keep recorded chassis ID 0; mounting height is CAD-derived.
            white, black = lids.build_tag_meshes(tid)
            local = np.eye(4)
            local[2,3] = 4.0  # top of the screen reference mesh
            transform = matrix(parent) @ local
        else:
            raise ValueError(kind)
        for material, mesh in [('white', white), ('black', black)]:
            add(mesh, tid, material, transform, parent, kind, leg, joint)
        report.append({'tagId': tid, 'kind': kind, 'leg': leg, 'joint': joint,
                       'mountSide': tag.get('mount_side'), 'parentInstance': parent['id'],
                       'centerWorldMm': transform[:3,3].tolist()})
    assert len(report) == 37 and len({r['tagId'] for r in report}) == 37
    assert sum(r['kind'] == 'yoke_face' for r in report) == 24
    scene['metadata']['tagCount'] = len(report)
    (OUT / 'scene.json').write_text(json.dumps(scene, indent=2) + '\n')
    (OUT / 'tag_manifest.json').write_text(json.dumps({'tags': report,
        'limitations': ['Cable routing and printed fit require physical verification.',
                        'Servo-lid artwork uses the generator orientation; tag centers are CAD-derived.',
                        'Base robot is full_robot_viz; standalone mechanical concept variants are not merged.']}, indent=2) + '\n')
    flag.write_multimaterial_3mf(OUT / 'all_24_snap_flags.3mf', print_flags)
    lids.write_bambu_project(OUT / 'all_24_snap_flags_BambuStudio.3mf', OUT / 'all_24_snap_flags.3mf')
    print(f'Wrote {len(report)} tags, {len(scene["instances"])} instances: {OUT / "scene.json"}')


if __name__ == '__main__':
    main()
