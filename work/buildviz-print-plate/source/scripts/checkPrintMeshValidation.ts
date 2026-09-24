import assert from 'node:assert/strict'
import { preparePrintMesh } from '../checks/printMeshValidation'
import { build3mfModelXml } from '../checks/buildviz3mf'
const mesh = { id: 1, name: 'Test tetrahedron', vertices: [0,0,0,1,0,0,0,1,0,0,0,1], triangles: [0,2,1,0,1,3,0,3,2,1,2,3] }
const matrix = [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
const soup = { ...mesh, vertices: mesh.triangles.flatMap(i => mesh.vertices.slice(i*3,i*3+3)), triangles: mesh.triangles.map((_,i) => i) }
assert.equal(preparePrintMesh(soup).vertices.length,12)
assert.equal((build3mfModelXml([soup],[{objectId:1,transform:matrix}]).match(/<vertex /g)||[]).length,4)
assert.throws(() => preparePrintMesh({...mesh,triangles:mesh.triangles.slice(3)}),/open edges/)
assert.throws(() => preparePrintMesh({...mesh,triangles:[...mesh.triangles,0,2,1]}),/duplicate faces.*non-manifold/)
assert.throws(() => preparePrintMesh({...mesh,triangles:[0,1,2,...mesh.triangles.slice(3)]}),/inconsistently oriented/)
assert.throws(() => preparePrintMesh({...mesh,triangles:[0,0,1,...mesh.triangles.slice(3)]}),/zero-area/)
assert.throws(() => preparePrintMesh({...mesh,vertices:[NaN,...mesh.vertices.slice(1)]}),/non-finite/)
assert.throws(() => preparePrintMesh({...mesh,triangles:[99,...mesh.triangles.slice(1)]}),/invalid triangle/)
assert.throws(() => build3mfModelXml([mesh],[{objectId:2,transform:matrix}]),/invalid object placement/)
assert.throws(() => build3mfModelXml([mesh],[{objectId:1,transform:[NaN,...matrix.slice(1)]}]),/object placement/)
assert.throws(() => build3mfModelXml([mesh],[{objectId:1,transform:[0,...matrix.slice(1)]}]),/collapsed object placement/)
// Two independently closed shells are legitimate; do not reject multi-solid STLs.
const double = { ...mesh, vertices: [...mesh.vertices,...mesh.vertices.map((x,i)=>i%3===0?x+3:x)], triangles: [...mesh.triangles,...mesh.triangles.map(i=>i+4)] }
assert.equal(preparePrintMesh(double).vertices.length,24)
console.log('Print mesh validation: 12 checks passed')
