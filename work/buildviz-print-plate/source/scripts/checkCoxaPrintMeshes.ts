import { readFile } from 'node:fs/promises'
import { parseStl } from '../core/geometryEngine'
import { preparePrintMesh } from '../checks/printMeshValidation'
const base = '../../../hexapod_walker/prototype_sts3215/concepts/coxa_6805_spacer_hub/stl/'
for (const name of ['yaw_hub_6805_10mm_spacers.stl','hip_bracket_no_legacy_holes.stl','3.stl']) {
 const b=await readFile(base+name),g=parseStl(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength))
 const a=g.getAttribute('position'),mesh={id:1,name,vertices:Array.from(a.array),triangles:g.index?Array.from(g.index.array):Array.from({length:a.count},(_,i)=>i)}
 const result=preparePrintMesh(mesh); console.log(name,result.vertices.length/3,'vertices passed');g.dispose()
}
