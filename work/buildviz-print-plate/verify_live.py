import json,subprocess,base64,urllib.request,pathlib,zipfile,io,xml.etree.ElementTree as ET
key=base64.b64decode(subprocess.check_output(['kubectl','--kubeconfig='+str(pathlib.Path.home()/'.kube/coreweave.yaml'),'get','secret','buildviz-api-key','-o','jsonpath={.data.key}'])).decode()
base='https://buildviz.cwd1f0-new-cluster.coreweave.app'
query='build=prototype_sts3215%2Ftwo-piece-coxa-6805&version=v3'
def get(path): return urllib.request.urlopen(urllib.request.Request(base+path,headers={'X-API-Key':key}),timeout=60).read()
data=json.loads(get('/__buildviz/workflows?'+query))
print('Printed:',[(p['partType'],p['quantity'],p['errors']) for p in data['printed']])
plate=get('/__buildviz/workflows/plate?'+query+'&selection=all&printer=x1c')
p=pathlib.Path('work/buildviz-print-plate/coxa-6805-v3-all-parts.3mf');p.write_bytes(plate)
z=zipfile.ZipFile(io.BytesIO(plate));root=ET.fromstring(z.read('3D/3dmodel.model'));ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
items=root.findall('m:build/m:item',ns);assert len(items)==sum(p['quantity'] for p in data['printed']);print('3MF build items',len(items))
import trimesh,numpy as np
scene=trimesh.load(p,force='scene');print('Plate bounds',scene.bounds.tolist());assert np.all(scene.bounds[0]>=-.001) and np.all(scene.bounds[1]<=[256,256,256]);assert len(scene.graph.nodes_geometry)==len(items)
print('Verified cloud plate',p)
