// Export-time checks on the exact indexed mesh written into the 3MF.
// No tolerance welding: nearby, intentionally separate surfaces stay separate.
export function preparePrintMesh(mesh: { name?: string; id: number; vertices: number[]; triangles: number[] }) {
  const fail = (why: string): never => { throw new Error(`Print check failed for "${mesh.name || `mesh ${mesh.id}`}": ${why}. Repair the source mesh before printing.`) }
  if (!mesh.vertices.length || mesh.vertices.length % 3 || !mesh.triangles.length || mesh.triangles.length % 3) fail('empty or incomplete mesh data')
  if (!mesh.vertices.every(Number.isFinite)) fail('non-finite vertex coordinates')
  const vertices: number[] = [], remap: number[] = []
  const byPosition = new Map<string, number>()
  for (let i = 0; i < mesh.vertices.length; i += 3) {
    const xyz = mesh.vertices.slice(i, i + 3), key = xyz.join(',')
    let index = byPosition.get(key)
    if (index === undefined) { index = vertices.length / 3; vertices.push(...xyz); byPosition.set(key, index) }
    remap.push(index)
  }
  if (!mesh.triangles.every(i => Number.isInteger(i) && i >= 0 && i < remap.length)) fail('invalid triangle vertex index')
  const triangles = mesh.triangles.map(i => remap[i])
  const edges = new Map<string, { count: number; direction: number }>(), faces = new Set<string>()
  let degenerate = 0, duplicate = 0
  for (let i = 0; i < triangles.length; i += 3) {
    const [a,b,c] = triangles.slice(i, i+3)
    const u = [0,1,2].map(k => vertices[3*b+k] - vertices[3*a+k])
    const v = [0,1,2].map(k => vertices[3*c+k] - vertices[3*a+k])
    if (a === b || b === c || c === a || Math.hypot(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]) === 0) degenerate++
    const key = [a,b,c].sort((x,y) => x-y).join(',')
    if (faces.has(key)) duplicate++
    faces.add(key)
    for (const [x,y] of [[a,b],[b,c],[c,a]]) {
      const key = x < y ? `${x},${y}` : `${y},${x}`
      const edge = edges.get(key) ?? { count: 0, direction: 0 }
      edge.count++; edge.direction += x < y ? 1 : -1; edges.set(key, edge)
    }
  }
  let open = 0, nonmanifold = 0, winding = 0
  for (const edge of edges.values()) {
    if (edge.count === 1) open++
    else if (edge.count !== 2) nonmanifold++
    else if (edge.direction !== 0) winding++
  }
  const problems = [degenerate && `${degenerate} zero-area triangles`, duplicate && `${duplicate} duplicate faces`, open && `${open} open edges`, nonmanifold && `${nonmanifold} non-manifold edges`, winding && `${winding} inconsistently oriented edges`].filter(Boolean)
  if (problems.length) fail(problems.join(', '))
  return { vertices, triangles }
}
