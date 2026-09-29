"""Package flat yaw key and both screw carriers; uv run python make_plate.py."""
from pathlib import Path
import json, zipfile, xml.etree.ElementTree as E
import trimesh
HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
ns='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
E.register_namespace('',ns)
def el(n,attr=None,parent=None):
    attr=attr or {}
    return E.SubElement(parent,'{'+ns+'}'+n,attr) if parent is not None else E.Element('{'+ns+'}'+n,attr)
model=el('model',{'unit':'millimeter'});res=el('resources',parent=model);build=el('build',parent=model)
layout=[]
parts=[('Yaw key v2 FLAT',BASE/'yaw_alignment_key/stl/yaw_alignment_key_PRINT.stl',(135,150)),('Carrier snug',BASE/'screw_loading_fork/stl/fork_snug.stl',(195,130)),('Carrier loose',BASE/'screw_loading_fork/stl/fork_loose.stl',(195,190))]
for idx,(name,path,xy) in enumerate(parts,1):
    m=trimesh.load(path,force='mesh');m.apply_translation([xy[0]-m.bounds[:,0].mean(),xy[1]-m.bounds[:,1].mean(),-m.bounds[0,2]])
    assert m.is_watertight and m.is_volume
    assert m.bounds[0,0]>30 and m.bounds[1,0]<300 and m.bounds[0,1]>30 and m.bounds[1,1]<300
    assert m.bounds[1,2]<5.31
    for other in layout:
        b=other['bounds_mm'];a=m.bounds
        assert a[1,0]+10<b[0][0] or a[0,0]-10>b[1][0] or a[1,1]+10<b[0][1] or a[0,1]-10>b[1][1]
    layout.append({'name':name,'bounds_mm':m.bounds.tolist()})
    obj=el('object',{'id':str(idx),'type':'model','name':name},res);mesh=el('mesh',parent=obj);verts=el('vertices',parent=mesh);tris=el('triangles',parent=mesh)
    for x,y,z in m.vertices:el('vertex',{'x':str(x),'y':str(y),'z':str(z)},verts)
    for a,b,c in m.faces:el('triangle',{'v1':str(a),'v2':str(b),'v3':str(c)},tris)
    el('item',{'objectid':str(idx)},build)
with zipfile.ZipFile(HERE/'alignment-tools-flat-v2-layout.3mf','w',zipfile.ZIP_DEFLATED) as z:
    z.writestr('3D/3dmodel.model',E.tostring(model,encoding='utf-8',xml_declaration=True))
    z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
(HERE/'flat-v2-layout.json').write_text(json.dumps(layout,indent=2))
print(layout)
