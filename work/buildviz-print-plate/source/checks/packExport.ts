// ---------------------------------------------------------------------------
// Plate export orchestration shared by the CLI (`buildviz pack --export`) and
// the hub endpoint (POST /__buildviz/pack-export).
//
//   runPack()          — orient + pack the printable parts of a build (reusing
//                        buildvizPacking) AND retain each unique mesh's raw
//                        vertex/triangle data so the SAME geometry the layout
//                        was computed from can be baked into the export.
//   exportPlateFiles() — turn the pack result + retained geometry into one file
//                        per plate (3MF default, merged STL fallback), written
//                        to disk, returning the absolute paths.
//
// Keeping this here (rather than inside cli/buildviz.ts) lets the hub run
// the exact same export server-side without importing the CLI dispatcher.
// ---------------------------------------------------------------------------
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import type { BuildMesh, BuildSceneManifest } from '../core/buildScene'
import { isFastenerMesh, loadMeshGeometry } from '../core/geometryEngine'
import {
  DEFAULT_MARGIN_MM,
  DEFAULT_SPACING_MM,
  DEFAULT_SUPPORT_ANGLE_DEG,
  orientMesh,
  packParts,
  type PackInputPart,
  type PackResult,
  type PrinterBed,
} from './buildvizPacking'
import {
  create3mf,
  createBinaryStl,
  type Build3mfItem,
  type Mesh3mfObject,
  type StlTriangle,
} from './buildviz3mf'

export type ExportFormat = '3mf' | 'stl'

// Raw geometry retained per unique mesh so the exporter bakes EXACTLY what the
// packer oriented/placed (no second, divergent orientation pass).
export type MeshTriData = { vertices: number[]; triangles: number[] }

export type RunPackOptions = {
  /** Reads the raw STL bytes for a mesh, or null when the asset is missing. */
  loadMesh: (mesh: BuildMesh) => Promise<ArrayBuffer | null>
  bed: PrinterBed
  printerId: string | null
  assembly?: string
  supportAngleDeg?: number
  spacingMm?: number
  marginMm?: number
}

export type RunPackResult = {
  result: PackResult
  /** meshId -> retained raw geometry (only for meshes that packed). */
  meshData: Map<string, MeshTriData>
  /** Instance ids skipped because their mesh had no loadable geometry. */
  skipped: string[]
  assembly: string | null
}

// Coerce a focusGroup/leg tag to a comparable lowercase string. `leg` is typed
// string|null but some exporters emit a number (e.g. 0), so coerce defensively.
const tagString = (value: unknown): string =>
  value === null || value === undefined ? '' : String(value).toLowerCase()

// Match an instance against an --assembly selector. Supports focusGroup/leg tags
// (string or number), the conventional "L<n>" leg form against a numeric leg
// (so --assembly L0 selects leg 0), and an instance-name prefix (names here read
// like "L0 coxa_yaw_hub").
const matchesAssembly = (
  instance: BuildSceneManifest['instances'][number],
  assembly: string | undefined,
) => {
  if (!assembly) return true
  const target = assembly.toLowerCase()
  const leg = tagString(instance.leg)
  if (tagString(instance.focusGroup) === target || leg === target) return true
  if (leg.length > 0 && `l${leg}` === target) return true
  const name = (instance.name ?? '').toLowerCase()
  return name === target || name.startsWith(`${target} `) || name.startsWith(`${target}_`)
}

// Human-readable list of the assembly selectors a build offers (for error help):
// focusGroup values, "L<n>" leg forms, and raw leg tags.
const assemblyOptions = (manifest: BuildSceneManifest): string[] => {
  const out = new Set<string>()
  for (const instance of manifest.instances) {
    if (instance.focusGroup) out.add(String(instance.focusGroup))
    if (instance.leg !== null && instance.leg !== undefined) {
      const leg = String(instance.leg)
      out.add(/^\d+$/.test(leg) ? `L${leg}` : leg)
    }
  }
  return [...out].sort()
}

const extractTriData = (geometry: ReturnType<typeof loadMeshGeometry>): MeshTriData => {
  const position = geometry.geometry.attributes.position
  const index = geometry.geometry.index
  const vertices = new Array<number>(position.count * 3)
  for (let i = 0; i < position.count; i += 1) {
    vertices[i * 3] = position.getX(i)
    vertices[i * 3 + 1] = position.getY(i)
    vertices[i * 3 + 2] = position.getZ(i)
  }
  let triangles: number[]
  if (index) {
    triangles = new Array<number>(index.count)
    for (let i = 0; i < index.count; i += 1) triangles[i] = index.getX(i)
  } else {
    triangles = new Array<number>(position.count)
    for (let i = 0; i < position.count; i += 1) triangles[i] = i
  }
  return { vertices, triangles }
}

// Orient + pack the printable (non-fastener) parts of a build, keeping the raw
// geometry of every unique mesh so the export bakes the same meshes/orientations
// the layout shows. Mirrors the selection/orientation/packing the `pack` command
// already performs; throws clear errors for an empty selection.
export const runPack = async (
  manifest: BuildSceneManifest,
  options: RunPackOptions,
): Promise<RunPackResult> => {
  const supportAngleDeg = options.supportAngleDeg ?? DEFAULT_SUPPORT_ANGLE_DEG
  const spacingMm = options.spacingMm ?? DEFAULT_SPACING_MM
  const marginMm = options.marginMm ?? DEFAULT_MARGIN_MM
  const assembly = options.assembly
  const { bed, printerId } = options

  // Hardware (screws/nuts/inserts) is not printed, so it is excluded. An
  // optional assembly narrows to one focusGroup / leg within the build.
  const fastenerMeshIds = new Set(manifest.meshes.filter(isFastenerMesh).map((mesh) => mesh.id))
  const printableInstances = manifest.instances.filter(
    (instance) => !fastenerMeshIds.has(instance.meshId) && matchesAssembly(instance, assembly),
  )
  if (printableInstances.length === 0) {
    if (assembly) {
      const groups = assemblyOptions(manifest)
      throw new Error(
        `No printable parts in assembly "${assembly}". ` +
          `Available focusGroup/leg values: ${groups.join(', ') || '(none)'}.`,
      )
    }
    throw new Error('No printable (non-fastener) parts to pack.')
  }

  // Orient every unique mesh referenced by the selection once, retaining its raw
  // geometry. Instances of the same mesh share an orientation AND the geometry.
  const meshesNeeded = manifest.meshes.filter((mesh) =>
    printableInstances.some((instance) => instance.meshId === mesh.id),
  )
  const orientations = new Map<string, ReturnType<typeof orientMesh>>()
  const meshData = new Map<string, MeshTriData>()
  await Promise.all(
    meshesNeeded.map(async (mesh) => {
      const data = await options.loadMesh(mesh)
      if (!data) return
      try {
        const geometry = loadMeshGeometry(data)
        if (geometry.triangleCount === 0) return
        orientations.set(mesh.id, orientMesh(geometry, { supportAngleDeg, bed }))
        meshData.set(mesh.id, extractTriData(geometry))
      } catch {
        // Skip meshes that fail to parse; their instances are reported skipped.
      }
    }),
  )

  const inputs: PackInputPart[] = []
  const skipped: string[] = []
  for (const instance of printableInstances) {
    const oriented = orientations.get(instance.meshId)
    if (!oriented) {
      skipped.push(instance.id)
      continue
    }
    inputs.push({
      instanceId: instance.id,
      partType: instance.partType,
      name: instance.name,
      meshId: instance.meshId,
      color: instance.color,
      orientation: oriented.chosen,
    })
  }
  if (inputs.length === 0) {
    throw new Error('No selected parts had loadable mesh geometry to pack.')
  }

  const result = packParts(inputs, { bed, marginMm, spacingMm, supportAngleDeg, printer: printerId })
  // Keep only the geometry that actually packed (drop unused meshes).
  const usedMeshIds = new Set(result.parts.map((part) => part.meshId))
  for (const meshId of [...meshData.keys()]) {
    if (!usedMeshIds.has(meshId)) meshData.delete(meshId)
  }

  return { result, meshData, skipped, assembly: assembly ?? null }
}

export type PlateExportFile = {
  plate: number
  fileName: string
  path: string
  partCount: number
}

export type PlateExportResult = {
  outDir: string
  format: ExportFormat
  plateCount: number
  files: PlateExportFile[]
}

// Plates are laid out along world +X with this gap (matching buildPackedScene);
// each part's transform encodes that per-plate origin, which we subtract so a
// single-plate file lands the parts at the plate's own bed corner.
const plateOriginX = (plate: number, bed: PrinterBed) =>
  plate * (bed.x + Math.max(bed.x, bed.y) * 0.15)

const applyMatrixPoint = (
  te: number[],
  x: number,
  y: number,
  z: number,
): [number, number, number] => [
  te[0] * x + te[4] * y + te[8] * z + te[12],
  te[1] * x + te[5] * y + te[9] * z + te[13],
  te[2] * x + te[6] * y + te[10] * z + te[14],
]

export const buildPlate3mf = (
  parts: PackResult['parts'],
  meshData: Map<string, MeshTriData>,
  originX: number,
): Buffer => {
  const objectIdByMesh = new Map<string, number>()
  const objects: Mesh3mfObject[] = []
  let nextId = 1
  for (const part of parts) {
    if (objectIdByMesh.has(part.meshId)) continue
    const data = meshData.get(part.meshId)
    if (!data) continue
    const id = nextId
    nextId += 1
    objectIdByMesh.set(part.meshId, id)
    objects.push({ id, name: part.name, vertices: data.vertices, triangles: data.triangles })
  }
  const items: Build3mfItem[] = []
  for (const part of parts) {
    const objectId = objectIdByMesh.get(part.meshId)
    if (objectId === undefined) continue
    const te = part.transform.slice()
    te[12] -= originX
    items.push({ objectId, transform: te, name: part.name, partType: part.partType })
  }
  return create3mf(objects, items)
}

const buildPlateStl = (
  parts: PackResult['parts'],
  meshData: Map<string, MeshTriData>,
  originX: number,
): Buffer => {
  const triangles: StlTriangle[] = []
  for (const part of parts) {
    const data = meshData.get(part.meshId)
    if (!data) continue
    const te = part.transform.slice()
    te[12] -= originX
    const { vertices, triangles: tri } = data
    for (let i = 0; i < tri.length; i += 3) {
      const a = tri[i] * 3
      const b = tri[i + 1] * 3
      const c = tri[i + 2] * 3
      triangles.push({
        v1: applyMatrixPoint(te, vertices[a], vertices[a + 1], vertices[a + 2]),
        v2: applyMatrixPoint(te, vertices[b], vertices[b + 1], vertices[b + 2]),
        v3: applyMatrixPoint(te, vertices[c], vertices[c + 1], vertices[c + 2]),
      })
    }
  }
  return createBinaryStl(triangles)
}

// Write one file per plate (plate-1.3mf … plate-N.3mf, or .stl) into outDir,
// baking the packed XY position + print orientation into each part's placement.
// Returns the absolute output dir + per-plate file paths.
export const exportPlateFiles = async (params: {
  result: PackResult
  meshData: Map<string, MeshTriData>
  bed: PrinterBed
  format: ExportFormat
  outDir: string
}): Promise<PlateExportResult> => {
  const { result, meshData, bed, format } = params
  const outDir = path.resolve(params.outDir)
  await mkdir(outDir, { recursive: true })

  const files: PlateExportFile[] = []
  for (let plate = 0; plate < result.totals.plateCount; plate += 1) {
    const parts = result.parts.filter((part) => part.plate === plate)
    if (parts.length === 0) continue
    const originX = plateOriginX(plate, bed)
    const ext = format === 'stl' ? 'stl' : '3mf'
    const fileName = `plate-${plate + 1}.${ext}`
    const buffer = format === 'stl'
      ? buildPlateStl(parts, meshData, originX)
      : buildPlate3mf(parts, meshData, originX)
    const filePath = path.join(outDir, fileName)
    await writeFile(filePath, buffer)
    files.push({ plate: plate + 1, fileName, path: filePath, partCount: parts.length })
  }

  return { outDir, format, plateCount: files.length, files }
}
