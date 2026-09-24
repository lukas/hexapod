import * as THREE from 'three'
import type { BuildInstance, BuildMesh, BuildSceneManifest, Vec3 } from '../core/buildScene'
import { loadMeshGeometry, type MeshGeometry } from '../core/geometryEngine'

// ---------------------------------------------------------------------------
// FDM plate layout: per-part print-orientation optimization + plate packing.
//
// This is intentionally a fast GEOMETRIC HEURISTIC, not a slicer. It reuses the
// shared STL loader / BVH from buildvizGeometry (loadMeshGeometry) and works
// purely from scene.json + its mesh assets, so it runs offline alongside the
// rest of the BuildViz CLI gates.
//
// Two stages:
//   1. orientMesh()  — score a set of candidate "rest" orientations per UNIQUE
//      mesh (the 6 axis-aligned rests + the largest natural facets) by a
//      printability heuristic (support need, bed contact/stability, height) and
//      pick the best one that still fits the bed.
//   2. packParts()   — a shelf/skyline bin-packer that lays the oriented part
//      footprints onto the bed with spacing, spilling onto extra plates when
//      they don't all fit, and rejects any single part too big for the bed.
//
// Caveats (documented on purpose): the support metric counts steep
// downward-facing triangle area and does NOT detect self-supporting bridges or
// model support volume; orientation ignores part-to-part dependencies; packing
// uses axis-aligned footprint AABBs (optionally rotated 90°), not true nesting.
// ---------------------------------------------------------------------------

export type PrinterBed = { x: number; y: number; z: number }
export type PrinterSpec = { id: string; name: string; bed: PrinterBed }

// Small named table so adding a printer later is a one-line change. Bed volumes
// are the usable X(width) × Y(depth) × Z(height) in mm.
export const PRINTERS: Record<string, PrinterSpec> = {
  x1c: { id: 'x1c', name: 'Bambu Lab X1C', bed: { x: 256, y: 256, z: 256 } },
  h2d: { id: 'h2d', name: 'Bambu Lab H2D', bed: { x: 350, y: 320, z: 325 } },
}

export const DEFAULT_PRINTER = 'x1c'
// Default self-support angle, measured from vertical: surfaces tilted MORE than
// this from vertical (i.e. more horizontal) are treated as overhangs needing
// support. 45° is the common FDM default.
export const DEFAULT_SUPPORT_ANGLE_DEG = 45
// Part-to-part gap on the plate (mm) and a margin/brim allowance kept clear
// around the bed edge (mm).
export const DEFAULT_SPACING_MM = 6
export const DEFAULT_MARGIN_MM = 5

export const resolvePrinter = (name: string | undefined): PrinterSpec => {
  const key = (name ?? DEFAULT_PRINTER).toLowerCase()
  const printer = PRINTERS[key]
  if (!printer) {
    throw new Error(
      `Unknown printer "${name}". Known: ${Object.keys(PRINTERS).join(', ')} (or pass --bed WxDxH).`,
    )
  }
  return printer
}

// Parse a custom "--bed WxDxH" string (mm), e.g. "300x300x340".
export const parseBed = (value: string): PrinterBed => {
  const match = value.trim().match(/^(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)$/i)
  if (!match) throw new Error(`Invalid --bed "${value}". Expected WxDxH in mm, e.g. 256x256x256.`)
  const [x, y, z] = [Number(match[1]), Number(match[2]), Number(match[3])]
  if (x <= 0 || y <= 0 || z <= 0) throw new Error(`Invalid --bed "${value}": dimensions must be positive.`)
  return { x, y, z }
}

const DOWN = new THREE.Vector3(0, 0, -1)
// Two faces whose down-normals are within this angle are treated as the same
// candidate orientation (dedupe axis rests against natural facets).
const DEDUPE_DOT = Math.cos((8 * Math.PI) / 180)
// A downward triangle this flat (|n·-Z| ≥) sitting at the bed counts as contact.
const FLAT_DOWN_DOT = 0.985

export type Orientation = {
  /** Column-major 16 rotation-only matrix mapping local → printed rest pose. */
  rotation: number[]
  rotationEulerDeg: [number, number, number]
  /** Footprint AABB (mm) on the bed after orienting (before any pack rotation). */
  footprint: { x: number; y: number }
  heightMm: number
  /** Steep downward-facing area (mm²) that would need support. HEURISTIC. */
  supportAreaMm2: number
  /** Area (mm²) resting flat on the bed (adhesion / stability). */
  contactAreaMm2: number
  surfaceAreaMm2: number
  /** Lower is better. */
  score: number
  /** 'axis' = axis-aligned rest; 'facet' = rests on a large natural face. */
  kind: 'axis' | 'facet'
  fitsBed: boolean
  /** Axis-aligned bounds of the oriented (rotated, not yet dropped) geometry. */
  box: { min: Vec3; max: Vec3 }
}

const round = (value: number, places = 3) => {
  const factor = 10 ** places
  return Math.round(value * factor) / factor
}

// Evaluate one candidate orientation (given as a quaternion) against the mesh:
// transform vertices, measure the footprint/height, and accumulate the steep
// downward (support) area and the flat-on-bed (contact) area.
const evaluateOrientation = (
  mesh: MeshGeometry,
  quat: THREE.Quaternion,
  supportSin: number,
  contactEps: number,
) => {
  const position = mesh.geometry.attributes.position
  const index = mesh.geometry.index
  const vCount = position.count
  const rot = new THREE.Matrix4().makeRotationFromQuaternion(quat)
  const tx = new Float32Array(vCount * 3)
  const v = new THREE.Vector3()
  let minX = Infinity
  let minY = Infinity
  let minZ = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  let maxZ = -Infinity
  for (let i = 0; i < vCount; i += 1) {
    v.set(position.getX(i), position.getY(i), position.getZ(i)).applyMatrix4(rot)
    tx[i * 3] = v.x
    tx[i * 3 + 1] = v.y
    tx[i * 3 + 2] = v.z
    if (v.x < minX) minX = v.x
    if (v.y < minY) minY = v.y
    if (v.z < minZ) minZ = v.z
    if (v.x > maxX) maxX = v.x
    if (v.y > maxY) maxY = v.y
    if (v.z > maxZ) maxZ = v.z
  }

  const triCount = (index ? index.count : vCount) / 3
  const a = new THREE.Vector3()
  const b = new THREE.Vector3()
  const c = new THREE.Vector3()
  const ab = new THREE.Vector3()
  const ac = new THREE.Vector3()
  const n = new THREE.Vector3()
  let support = 0
  let contact = 0
  let surface = 0
  const readVertex = (corner: number, out: THREE.Vector3, triangle: number) => {
    const vertex = index ? index.getX(triangle * 3 + corner) : triangle * 3 + corner
    out.set(tx[vertex * 3], tx[vertex * 3 + 1], tx[vertex * 3 + 2])
  }
  for (let t = 0; t < triCount; t += 1) {
    readVertex(0, a, t)
    readVertex(1, b, t)
    readVertex(2, c, t)
    ab.subVectors(b, a)
    ac.subVectors(c, a)
    n.crossVectors(ab, ac)
    const area = n.length() * 0.5
    if (area <= 1e-9) continue
    surface += area
    const nz = n.z / (area * 2) // normalized z-component of the face normal
    const triMinZ = Math.min(a.z, b.z, c.z) - minZ
    if (nz < -FLAT_DOWN_DOT && triMinZ <= contactEps) {
      contact += area
      continue
    }
    // Downward and tilted more than the support angle from vertical → overhang.
    if (nz < -supportSin) support += area
  }

  return {
    footprint: { x: maxX - minX, y: maxY - minY },
    heightMm: maxZ - minZ,
    supportAreaMm2: support,
    contactAreaMm2: contact,
    surfaceAreaMm2: surface,
    box: { min: [minX, minY, minZ] as Vec3, max: [maxX, maxY, maxZ] as Vec3 },
  }
}

// Heuristic score (lower is better): support need dominates, a larger bed
// contact fraction is rewarded, height is a mild secondary penalty, and a small
// footprint relative to height is penalized as a tipping risk.
const scoreOrientation = (e: ReturnType<typeof evaluateOrientation>) => {
  const footprintArea = Math.max(e.footprint.x * e.footprint.y, 1e-6)
  const supportFrac = e.surfaceAreaMm2 > 0 ? e.supportAreaMm2 / e.surfaceAreaMm2 : 0
  const heightTerm = e.heightMm / (e.heightMm + Math.max(e.footprint.x, e.footprint.y, 1e-3))
  const contactFrac = Math.min(1, e.contactAreaMm2 / footprintArea)
  const minFp = Math.max(Math.min(e.footprint.x, e.footprint.y), 1e-3)
  const tipRisk = e.heightMm / minFp
  let tipPenalty = 0
  if (contactFrac < 0.02) tipPenalty += 0.5
  if (tipRisk > 4) tipPenalty += 0.3 * Math.min(1, (tipRisk - 4) / 6)
  return 1.0 * supportFrac + 0.15 * heightTerm - 0.25 * contactFrac + tipPenalty
}

// Candidate down-normals (in the mesh's local frame): the 6 axis-aligned faces
// plus the largest natural facets (area-weighted normal clusters).
const candidateNormals = (mesh: MeshGeometry) => {
  const axes: Array<{ dir: THREE.Vector3; kind: 'axis' | 'facet' }> = [
    { dir: new THREE.Vector3(1, 0, 0), kind: 'axis' },
    { dir: new THREE.Vector3(-1, 0, 0), kind: 'axis' },
    { dir: new THREE.Vector3(0, 1, 0), kind: 'axis' },
    { dir: new THREE.Vector3(0, -1, 0), kind: 'axis' },
    { dir: new THREE.Vector3(0, 0, 1), kind: 'axis' },
    { dir: new THREE.Vector3(0, 0, -1), kind: 'axis' },
  ]

  // Cluster triangle normals (quantized) and keep the largest-area directions —
  // these are the flat faces a part can naturally rest on (hull-like facets).
  const position = mesh.geometry.attributes.position
  const index = mesh.geometry.index
  const triCount = (index ? index.count : position.count) / 3
  const a = new THREE.Vector3()
  const b = new THREE.Vector3()
  const c = new THREE.Vector3()
  const ab = new THREE.Vector3()
  const ac = new THREE.Vector3()
  const n = new THREE.Vector3()
  const bins = new Map<string, { dir: THREE.Vector3; area: number }>()
  let totalArea = 0
  const readVertex = (corner: number, out: THREE.Vector3, triangle: number) => {
    const vertex = index ? index.getX(triangle * 3 + corner) : triangle * 3 + corner
    out.set(position.getX(vertex), position.getY(vertex), position.getZ(vertex))
  }
  for (let t = 0; t < triCount; t += 1) {
    readVertex(0, a, t)
    readVertex(1, b, t)
    readVertex(2, c, t)
    ab.subVectors(b, a)
    ac.subVectors(c, a)
    n.crossVectors(ab, ac)
    const area = n.length() * 0.5
    if (area <= 1e-9) continue
    n.multiplyScalar(1 / (area * 2))
    totalArea += area
    const key = `${Math.round(n.x * 12)},${Math.round(n.y * 12)},${Math.round(n.z * 12)}`
    const bin = bins.get(key)
    if (bin) {
      bin.dir.addScaledVector(n, area)
      bin.area += area
    } else {
      bins.set(key, { dir: n.clone().multiplyScalar(area), area })
    }
  }

  const facets = [...bins.values()]
    .filter((bin) => bin.area >= totalArea * 0.03)
    .sort((x, y) => y.area - x.area)
    .slice(0, 8)
    .map((bin) => ({ dir: bin.dir.normalize(), kind: 'facet' as const }))

  // Axis rests first so a facet coincident with an axis dedupes to the axis.
  const out: Array<{ dir: THREE.Vector3; kind: 'axis' | 'facet' }> = []
  for (const candidate of [...axes, ...facets]) {
    if (out.some((existing) => existing.dir.dot(candidate.dir) >= DEDUPE_DOT)) continue
    out.push(candidate)
  }
  return out
}

export type OrientOptions = {
  /** Self-support angle from vertical (deg); steeper downward area needs support. */
  supportAngleDeg?: number
  /** Bed used to mark each orientation's fitsBed (defaults to no limit). */
  bed?: PrinterBed
}

// Pick the best printing orientation for one mesh. Returns the chosen
// orientation plus every scored candidate (for transparency / JSON output).
export const orientMesh = (
  mesh: MeshGeometry,
  options: OrientOptions = {},
): { chosen: Orientation; candidates: Orientation[] } => {
  const supportAngleDeg = options.supportAngleDeg ?? DEFAULT_SUPPORT_ANGLE_DEG
  const supportSin = Math.sin((supportAngleDeg * Math.PI) / 180)
  const size = new THREE.Vector3()
  mesh.localBox.getSize(size)
  const contactEps = Math.max(0.5, size.length() * 0.002)
  const bed = options.bed

  const candidates: Orientation[] = candidateNormals(mesh).map(({ dir, kind }) => {
    const quat = new THREE.Quaternion().setFromUnitVectors(dir, DOWN)
    const e = evaluateOrientation(mesh, quat, supportSin, contactEps)
    const rotMatrix = new THREE.Matrix4().makeRotationFromQuaternion(quat)
    const euler = new THREE.Euler().setFromQuaternion(quat)
    const innerX = bed ? bed.x : Infinity
    const innerY = bed ? bed.y : Infinity
    const fitsXY =
      (e.footprint.x <= innerX && e.footprint.y <= innerY) ||
      (e.footprint.y <= innerX && e.footprint.x <= innerY)
    const fitsBed = fitsXY && (!bed || e.heightMm <= bed.z)
    return {
      rotation: rotMatrix.toArray(),
      rotationEulerDeg: [
        round((euler.x * 180) / Math.PI, 2),
        round((euler.y * 180) / Math.PI, 2),
        round((euler.z * 180) / Math.PI, 2),
      ],
      footprint: { x: round(e.footprint.x), y: round(e.footprint.y) },
      heightMm: round(e.heightMm),
      supportAreaMm2: round(e.supportAreaMm2, 1),
      contactAreaMm2: round(e.contactAreaMm2, 1),
      surfaceAreaMm2: round(e.surfaceAreaMm2, 1),
      score: round(scoreOrientation(e), 4),
      kind,
      fitsBed,
      box: {
        min: e.box.min.map((value) => round(value)) as Vec3,
        max: e.box.max.map((value) => round(value)) as Vec3,
      },
    }
  })

  // Prefer orientations that fit the bed, then the lowest (best) score.
  const ranked = [...candidates].sort((x, y) => {
    if (x.fitsBed !== y.fitsBed) return x.fitsBed ? -1 : 1
    return x.score - y.score
  })
  return { chosen: ranked[0], candidates }
}

// --- Packing -------------------------------------------------------------

export type PackInputPart = {
  instanceId: string
  partType: string
  name: string
  meshId: string
  color: string
  orientation: Orientation
}

export type PackedPart = PackInputPart & {
  plate: number
  /** Footprint min-corner position within the bed (mm), inside the margin. */
  position: { x: number; y: number }
  /** Footprint placed on the bed (mm), after any 90° pack rotation. */
  footprint: { x: number; y: number }
  heightMm: number
  supportAreaMm2: number
  /** Whether the footprint was rotated 90° about Z to fit/pack better. */
  rotated90: boolean
  /** Column-major 16 world transform placing the oriented part on its plate. */
  transform: number[]
}

export type PlateSummary = {
  plate: number
  partCount: number
  /** Footprint area used / bed area, 0..1. */
  utilization: number
  usedAreaMm2: number
}

export type PackResult = {
  printer: string | null
  bed: PrinterBed
  marginMm: number
  spacingMm: number
  supportAngleDeg: number
  plates: PlateSummary[]
  parts: PackedPart[]
  totals: {
    partCount: number
    plateCount: number
    partsRotated: number
    partsNeedingSupport: number
    totalSupportAreaMm2: number
    avgSupportAreaMm2: number
  }
}

export type PackOptions = {
  bed: PrinterBed
  marginMm?: number
  spacingMm?: number
  supportAngleDeg?: number
  printer?: string | null
}

// Rotate the orientation's (pre-drop) AABB by an optional 90° Z spin and return
// the resulting footprint + the world transform that drops it to z=0 with its
// min-corner at (originX+px, py).
const placeTransform = (
  orientation: Orientation,
  rotated90: boolean,
  originX: number,
  px: number,
  py: number,
) => {
  const rot = new THREE.Matrix4().fromArray(orientation.rotation)
  const spin = new THREE.Matrix4().makeRotationZ(rotated90 ? Math.PI / 2 : 0)
  const combined = new THREE.Matrix4().multiplyMatrices(spin, rot)
  // AABB of the spun box: transform the 8 corners of the oriented box by `spin`.
  const min = orientation.box.min
  const max = orientation.box.max
  const corner = new THREE.Vector3()
  let nMinX = Infinity
  let nMinY = Infinity
  let nMinZ = Infinity
  let nMaxX = -Infinity
  let nMaxY = -Infinity
  for (let i = 0; i < 8; i += 1) {
    corner
      .set(i & 1 ? max[0] : min[0], i & 2 ? max[1] : min[1], i & 4 ? max[2] : min[2])
      .applyMatrix4(spin)
    if (corner.x < nMinX) nMinX = corner.x
    if (corner.y < nMinY) nMinY = corner.y
    if (corner.z < nMinZ) nMinZ = corner.z
    if (corner.x > nMaxX) nMaxX = corner.x
    if (corner.y > nMaxY) nMaxY = corner.y
  }
  const tx = originX + px - nMinX
  const ty = py - nMinY
  const tz = -nMinZ
  const translate = new THREE.Matrix4().makeTranslation(tx, ty, tz)
  const world = translate.multiply(combined)
  return {
    footprint: { x: round(nMaxX - nMinX), y: round(nMaxY - nMinY) },
    transform: world.toArray(),
  }
}

// Shelf/skyline bin-packer. Parts are sorted by footprint depth (tallest shelf
// first), placed left→right on a shelf; a part that overruns the bed width wraps
// to a new shelf, and one that overruns the bed depth starts a new plate. Any
// single part too big for the bed (even rotated 90°) is rejected with a clear
// error. Plates are laid out along world +X with a gap for the emitted scene.
export const packParts = (parts: PackInputPart[], options: PackOptions): PackResult => {
  const { bed } = options
  const marginMm = options.marginMm ?? DEFAULT_MARGIN_MM
  const spacingMm = options.spacingMm ?? DEFAULT_SPACING_MM
  const supportAngleDeg = options.supportAngleDeg ?? DEFAULT_SUPPORT_ANGLE_DEG
  const innerX = bed.x - 2 * marginMm
  const innerY = bed.y - 2 * marginMm
  if (innerX <= 0 || innerY <= 0) {
    throw new Error(`Margin ${marginMm}mm leaves no usable area on a ${bed.x}×${bed.y}mm bed.`)
  }
  const plateGap = Math.max(bed.x, bed.y) * 0.15

  // Resolve each part's plate footprint (with optional 90° rotation to fit) and
  // reject anything too large up front so packing never silently drops a part.
  type Prepared = PackInputPart & { w: number; h: number; rotated90: boolean }
  const prepared: Prepared[] = parts.map((part) => {
    const fp = part.orientation.footprint
    if (part.orientation.heightMm > bed.z) {
      throw new Error(
        `Part "${part.name}" (${part.partType}) is ${round(part.orientation.heightMm, 1)}mm tall in its ` +
          `best orientation, exceeding the ${bed.z}mm build height. Split the part or use a taller printer.`,
      )
    }
    const fitsAsIs = fp.x <= innerX && fp.y <= innerY
    const fitsRot = fp.y <= innerX && fp.x <= innerY
    if (!fitsAsIs && !fitsRot) {
      throw new Error(
        `Part "${part.name}" (${part.partType}) footprint ${round(fp.x, 1)}×${round(fp.y, 1)}mm does not fit ` +
          `the usable ${round(innerX, 1)}×${round(innerY, 1)}mm bed (${bed.x}×${bed.y}mm minus ${marginMm}mm margin), ` +
          `even rotated. Split the part or use a larger bed (--bed WxDxH / --printer).`,
      )
    }
    // Prefer the part's own orientation; only rotate 90° when it must to fit.
    const rotated90 = !fitsAsIs && fitsRot
    return {
      ...part,
      w: rotated90 ? fp.y : fp.x,
      h: rotated90 ? fp.x : fp.y,
      rotated90,
    }
  })

  // Tallest-shelf-first reduces wasted vertical gaps in shelf packing.
  prepared.sort((x, y) => y.h - x.h)

  const packed: PackedPart[] = []
  let plate = 0
  let cursorX = marginMm
  let cursorY = marginMm
  let shelfDepth = 0
  for (const part of prepared) {
    if (cursorX + part.w > marginMm + innerX + 1e-6) {
      cursorY += shelfDepth + spacingMm
      cursorX = marginMm
      shelfDepth = 0
    }
    if (cursorY + part.h > marginMm + innerY + 1e-6) {
      plate += 1
      cursorX = marginMm
      cursorY = marginMm
      shelfDepth = 0
    }
    const originX = plate * (bed.x + plateGap)
    const placed = placeTransform(part.orientation, part.rotated90, originX, cursorX, cursorY)
    packed.push({
      instanceId: part.instanceId,
      partType: part.partType,
      name: part.name,
      meshId: part.meshId,
      color: part.color,
      orientation: part.orientation,
      plate,
      position: { x: round(cursorX), y: round(cursorY) },
      footprint: placed.footprint,
      heightMm: part.orientation.heightMm,
      supportAreaMm2: part.orientation.supportAreaMm2,
      rotated90: part.rotated90,
      transform: placed.transform,
    })
    cursorX += part.w + spacingMm
    shelfDepth = Math.max(shelfDepth, part.h)
  }

  const plateCount = packed.length === 0 ? 0 : Math.max(...packed.map((part) => part.plate)) + 1
  const bedArea = bed.x * bed.y
  const plates: PlateSummary[] = []
  for (let index = 0; index < plateCount; index += 1) {
    const onPlate = packed.filter((part) => part.plate === index)
    const usedArea = onPlate.reduce((sum, part) => sum + part.footprint.x * part.footprint.y, 0)
    plates.push({
      plate: index,
      partCount: onPlate.length,
      usedAreaMm2: round(usedArea, 1),
      utilization: round(usedArea / bedArea, 4),
    })
  }

  const partsNeedingSupport = packed.filter((part) => part.supportAreaMm2 > 0).length
  const totalSupport = packed.reduce((sum, part) => sum + part.supportAreaMm2, 0)
  return {
    printer: options.printer ?? null,
    bed,
    marginMm,
    spacingMm,
    supportAngleDeg,
    plates,
    parts: packed,
    totals: {
      partCount: packed.length,
      plateCount,
      partsRotated: packed.filter((part) => part.rotated90).length,
      partsNeedingSupport,
      totalSupportAreaMm2: round(totalSupport, 1),
      avgSupportAreaMm2: packed.length > 0 ? round(totalSupport / packed.length, 1) : 0,
    },
  }
}

// Build a BuildViz scene that visualizes the packed plates: every part is
// instanced at its on-plate world transform, and a thin slab box is drawn under
// each plate as its boundary. Mesh URLs are reused verbatim from the source
// build so the same server that serves the original assets serves these too.
export const buildPackedScene = (
  result: PackResult,
  sourceName: string,
  sourceMeshes: BuildMesh[],
): BuildSceneManifest => {
  const meshById = new Map(sourceMeshes.map((mesh) => [mesh.id, mesh]))
  const usedMeshIds = new Set(result.parts.map((part) => part.meshId))
  const plateGap = Math.max(result.bed.x, result.bed.y) * 0.15
  const slabHeight = 2

  const meshes: BuildMesh[] = [
    ...sourceMeshes.filter((mesh) => usedMeshIds.has(mesh.id)),
    {
      id: 'pack:plate',
      name: 'Print plate',
      primitive: { kind: 'box', size: [result.bed.x, result.bed.y, slabHeight] },
    },
  ]

  const instances: BuildInstance[] = []
  for (let plate = 0; plate < result.totals.plateCount; plate += 1) {
    const originX = plate * (result.bed.x + plateGap)
    instances.push({
      id: `pack:plate-${plate}`,
      meshId: 'pack:plate',
      name: `Plate ${plate + 1}`,
      partType: 'print_plate',
      role: `print plate ${plate + 1} (${result.bed.x}×${result.bed.y}mm)`,
      color: '#1f2937',
      // Slab centered under the plate, top at z=0 so parts rest on it.
      transform: [
        1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, 0,
        originX + result.bed.x / 2, result.bed.y / 2, -slabHeight / 2, 1,
      ],
      focusGroup: `plate-${plate}`,
    })
  }

  for (const part of result.parts) {
    const source = meshById.get(part.meshId)
    if (!source) continue
    instances.push({
      id: part.instanceId,
      meshId: part.meshId,
      name: part.name,
      partType: part.partType,
      role: `${part.partType} oriented for printing on plate ${part.plate + 1}`,
      color: part.color,
      transform: part.transform,
      focusGroup: `plate-${part.plate}`,
    })
  }

  const totalWidth =
    result.totals.plateCount > 0
      ? result.totals.plateCount * result.bed.x + (result.totals.plateCount - 1) * plateGap
      : result.bed.x
  return {
    name: `${sourceName} — packed for ${result.printer ? PRINTERS[result.printer]?.name ?? result.printer : 'custom bed'}`,
    units: 'mm',
    center: [totalWidth / 2, result.bed.y / 2, 0],
    meshes,
    instances,
  }
}

// Load + orient every UNIQUE non-fastener mesh once (orientations are reused by
// all instances of that mesh). `loadBytes` returns the STL ArrayBuffer for a
// mesh, or null when the asset is missing/inapplicable.
export const orientMeshes = async (
  meshes: BuildMesh[],
  loadBytes: (mesh: BuildMesh) => Promise<ArrayBuffer | null>,
  options: OrientOptions,
): Promise<Map<string, { chosen: Orientation; candidates: Orientation[] }>> => {
  const out = new Map<string, { chosen: Orientation; candidates: Orientation[] }>()
  await Promise.all(
    meshes.map(async (mesh) => {
      const data = await loadBytes(mesh)
      if (!data) return
      try {
        const geometry = loadMeshGeometry(data)
        if (geometry.triangleCount === 0) return
        out.set(mesh.id, orientMesh(geometry, options))
      } catch {
        // Skip meshes that fail to parse; the caller reports missing meshes.
      }
    }),
  )
  return out
}
