// STEP (ISO 10303 / .step/.stp) ingest for BuildViz, node-side only.
//
// BuildViz stays mesh-based internally (the checks/drawings/sections/viewer
// engines are all BVH-over-triangles), so STEP is accepted AT INGEST and
// tessellated once via OpenCascade (occt-import-js, WASM) into the same
// binary STLs a plain push would carry. What STEP adds over loose STLs:
// exact BREP source geometry (tessellation quality is ours to choose, not
// the exporter's), plus assembly structure — part names, colors, and
// repeated-part instances — that STL files simply do not have.
import path from 'node:path'
import occtimportjs from 'occt-import-js'

export const STEP_EXTENSIONS = ['.step', '.stp']

export const isStepFile = (file: string) =>
  STEP_EXTENSIONS.includes(path.extname(file).toLowerCase())

export type StepTessellationOptions = {
  /** Max chord deviation (mm) between the BREP surface and the mesh. */
  linearDeflectionMm?: number
  /** Max angle (radians) between adjacent facet normals. */
  angularDeflectionRad?: number
}

export type StepPart = {
  /** Human name from the STEP assembly tree (deepest node naming this solid). */
  name: string
  /** #rrggbb from the STEP color attributes, when present. */
  color?: string
  /** Binary STL bytes of the tessellated solid (mm, world/assembly frame). */
  stl: Buffer
  triangleCount: number
  bboxMm: { min: [number, number, number]; max: [number, number, number] }
}

type OcctMesh = {
  name: string
  color?: [number, number, number]
  attributes: { position: { array: number[] } }
  index?: { array: number[] }
}

type OcctNode = {
  name: string
  meshes: number[]
  children?: OcctNode[]
}

type OcctResult = { success: boolean; root: OcctNode; meshes: OcctMesh[] }

const hexColor = (rgb: [number, number, number]) =>
  '#' + rgb.map((c) => Math.max(0, Math.min(255, Math.round(c * 255))).toString(16).padStart(2, '0')).join('')

// Deepest assembly-tree node that references each mesh index: STEP meshes are
// usually named just "SOLID"; the tree node (PLATE, ROD_ASM, …) carries the
// meaningful name.
const namesByMeshIndex = (root: OcctNode): Map<number, string> => {
  const names = new Map<number, string>()
  const walk = (node: OcctNode) => {
    for (const meshIndex of node.meshes ?? []) {
      if (node.name) names.set(meshIndex, node.name)
    }
    for (const child of node.children ?? []) walk(child)
  }
  walk(root)
  return names
}

// Binary STL: 80-byte header, uint32 triangle count, 50 bytes per triangle.
const toBinaryStl = (position: number[], index: number[] | undefined, sourceName: string): Buffer => {
  const triangleCount = (index ? index.length : position.length / 3) / 3
  const buffer = Buffer.alloc(84 + triangleCount * 50)
  buffer.write(`BuildViz STEP tessellation: ${sourceName}`.slice(0, 79), 0, 'ascii')
  buffer.writeUInt32LE(triangleCount, 80)
  let offset = 84
  const vertex = (triangle: number, corner: number) => {
    const vi = index ? index[triangle * 3 + corner] : triangle * 3 + corner
    return [position[vi * 3], position[vi * 3 + 1], position[vi * 3 + 2]]
  }
  for (let t = 0; t < triangleCount; t += 1) {
    const [ax, ay, az] = vertex(t, 0)
    const [bx, by, bz] = vertex(t, 1)
    const [cx, cy, cz] = vertex(t, 2)
    const ux = bx - ax, uy = by - ay, uz = bz - az
    const vx = cx - ax, vy = cy - ay, vz = cz - az
    let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx
    const len = Math.hypot(nx, ny, nz)
    if (len > 0) { nx /= len; ny /= len; nz /= len }
    for (const value of [nx, ny, nz, ax, ay, az, bx, by, bz, cx, cy, cz]) {
      buffer.writeFloatLE(value, offset)
      offset += 4
    }
    buffer.writeUInt16LE(0, offset)
    offset += 2
  }
  return buffer
}

/** Tessellate one STEP file into per-solid binary STLs (mm, assembly frame). */
export const tessellateStepFile = async (
  bytes: Uint8Array,
  sourceName: string,
  options: StepTessellationOptions = {},
): Promise<StepPart[]> => {
  const occt = await occtimportjs()
  const params =
    options.linearDeflectionMm !== undefined || options.angularDeflectionRad !== undefined
      ? {
          linearUnit: 'millimeter',
          linearDeflectionType: 'absolute_value',
          linearDeflection: options.linearDeflectionMm ?? 0.1,
          angularDeflection: options.angularDeflectionRad ?? 0.5,
        }
      : null
  const result = (await occt.ReadStepFile(bytes, params)) as OcctResult
  if (!result.success || result.meshes.length === 0) {
    throw new Error(`Could not read STEP file ${sourceName} (no solids found).`)
  }

  const names = namesByMeshIndex(result.root)
  return result.meshes.map((mesh, meshIndex) => {
    const position = mesh.attributes.position.array
    const index = mesh.index?.array
    const min: [number, number, number] = [Infinity, Infinity, Infinity]
    const max: [number, number, number] = [-Infinity, -Infinity, -Infinity]
    for (let i = 0; i < position.length; i += 3) {
      for (let axis = 0; axis < 3; axis += 1) {
        const value = position[i + axis]
        if (value < min[axis]) min[axis] = value
        if (value > max[axis]) max[axis] = value
      }
    }
    return {
      name: names.get(meshIndex) ?? mesh.name ?? `part_${meshIndex + 1}`,
      color: mesh.color ? hexColor(mesh.color) : undefined,
      stl: toBinaryStl(position, index, sourceName),
      triangleCount: (index ? index.length : position.length / 3) / 3,
      bboxMm: { min, max },
    }
  })
}
