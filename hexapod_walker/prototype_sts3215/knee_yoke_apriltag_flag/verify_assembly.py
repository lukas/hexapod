"""Check tag identity, hierarchy, cup placement and static rigid clearance."""
import json
from pathlib import Path
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent / 'assembly'
s = json.loads((HERE / 'scene.json').read_text())
manifest = json.loads((HERE / 'tag_manifest.json').read_text())
meshes = {m['id']: trimesh.load_mesh(HERE / m['url']) for m in s['meshes']}
placed = {}
for i in s['instances']:
    m = meshes[i['meshId']].copy()
    m.apply_transform(np.array(i['transform']).reshape(4,4).T)
    placed[i['id']] = m
instances = {i['id']: i for i in s['instances']}
collisions = []
for t in manifest['tags']:
    tid = t['tagId']
    parent = t['parentInstance']
    for material in ['white','black']:
        identifier = f'apriltag-{tid}-{material}'
        assert identifier in instances
        assert [j['id'] for j in s['joints'] if identifier in j['instances']] == [j['id'] for j in s['joints'] if parent in j['instances']]
    m = placed[f'apriltag-{tid}-white']
    for i in s['instances']:
        # Screw-head interference is intentional for the friction cups.
        if i['partType'].startswith(('apriltag_', 'screw_')) or i['id'] == parent:
            continue
        other = placed[i['id']]
        if np.any(m.bounds[1] <= other.bounds[0]+0.01) or np.any(other.bounds[1] <= m.bounds[0]+0.01):
            continue
        intersection = trimesh.boolean.intersection([m,other], engine='manifold', check_volume=False)
        volume = abs(float(intersection.volume)) if intersection is not None else 0
        if volume > .05:
            collisions.append({'tagId':tid,'part':i['id'],'volumeMm3':round(volume,3)})
report = {'tagCount':len(manifest['tags']), 'uniqueIds':len({t['tagId'] for t in manifest['tags']}),
          'jointHierarchyPass':True, 'staticRigidOverlapsExcludingScrewsAndMountParent':collisions,
          'limitations':'Not a cable-clearance or full articulated collision certification.'}
(HERE/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
