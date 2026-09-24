import * as THREE from 'three'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js'
import { ExtendedTriangle, MeshBVH } from 'three-mesh-bvh'
import type { BuildMesh, BuildSceneManifest, Vec3 } from './buildScene'

// Geometry ENGINE: load-once STL parsing, per-unique-mesh BVH indexing, world
// AABB broad phase, BVH narrow-phase primitives (surface distance, interior
// penetration depth), and robust per-mesh facts (topology/watertightness, wall
// thickness estimate, self-intersections), plus fastener-library detection.
//
// This module computes FACTS about meshes and instance pairs. It never judges
// an assembly: everything that produces a report/check record (checkAssembly,
// sweepOverlaps, probe/slice/thickness/bom/identify) lives in
// buildvizGeometry.ts and builds on the primitives exported here.
//
// Browser- and Node-safe: mesh bytes arrive through the injected loadMesh
// callback, never fs.

// Surface distance (mm) below which two parts are treated as intersecting.
export const INTERSECTION_EPSILON = 1e-3
// Interior penetration sampling: target grid point budget per intersecting pair
// and the finest spacing (mm) we ever sample at. The grid spans the world-space
// AABB overlap of the two parts; spacing scales with the overlap volume so the
// point count stays ~MAX_GRID_POINTS regardless of part size.
const MAX_GRID_POINTS = 4096
const MIN_GRID_SPACING_MM = 0.4
const MAX_GRID_AXIS = 64
// Ray hits closer than this (mm) are treated as self/adjacent-triangle noise
// and ignored by the wall-thickness estimate.
const WALL_MIN_HIT_MM = 0.05
// Minimum |normal·ray| for an inward-ray hit to count as an opposing wall face
// (cos~60°). Rejects grazing hits on adjacent facets at concave corners.
const WALL_OPPOSING_DOT = 0.5
// Report this percentile of per-sample thicknesses (not the raw min) so a lone
// outlier ray can't flag an otherwise-thick mesh.
const WALL_PERCENTILE = 0.01
// ...but never below this many samples, so small meshes still report their min.
const WALL_MIN_CORROBORATING = 2
// Triangle area (mm²) at/below which a triangle is considered degenerate.
const DEGENERATE_AREA_MM2 = 1e-6
// Self-intersection: a triangle-triangle contact whose intersection segment is
// shorter than this (mm) is treated as a coplanar edge graze / numerical touch,
// not a genuine self-intersection. Adjacent (shared-vertex) pairs are skipped
// outright by topological welding.
const SELF_INTERSECTION_MIN_SEGMENT_MM = 1e-3
// Meshes with more triangles than this skip the (n·log n) self-intersection
// pass to keep the gate bounded; they report selfIntersections = null.
const SELF_INTERSECTION_MAX_TRIANGLES = 250_000
// A mesh is treated as a fastener when its asset lives in a fasteners/ directory
// or its id is namespaced "fasteners:" (the BuildViz exporter convention), or as
// a fallback when its part name reads like hardware. Conservative on purpose:
// structural parts (coxa_link, chassis_top, ...) never match.
const FASTENER_PATH = /(^|[/:])fasteners?[/:]/i
const FASTENER_KEYWORD =
  /\b(fastener|screw|bolt|shcs|washer|nyloc|\bnut\b|heat-?set|insert|dowel|standoff|grub|pan-?head|spline screw|hex(?:\s|-)?(?:bolt|nut|screw))\b/i

export const isFastenerMesh = (mesh: BuildMesh) =>
  FASTENER_PATH.test(mesh.url ?? '') || FASTENER_PATH.test(mesh.id) || FASTENER_KEYWORD.test(mesh.name ?? '')

export type MeshGeometry = {
  geometry: THREE.BufferGeometry
  bvh: MeshBVH
  triangleCount: number
  localBox: THREE.Box3
}

export type InstanceGeometry = {
  index: number
  instanceId: string
  meshId: string
  partType: string
  name: string
  mesh: MeshGeometry
  matrix: THREE.Matrix4
  inverse: THREE.Matrix4
  worldMin: [number, number, number]
  worldMax: [number, number, number]
  isFastener: boolean
}

const stlLoader = new STLLoader()

export const parseStl = (data: ArrayBuffer): THREE.BufferGeometry => {
  const geometry = stlLoader.parse(data)
  geometry.computeBoundingBox()
  return geometry
}

// Shared STL → geometry + BVH + bounds loader, reused by the interference
// checker (above) and the plate-packing orientation heuristic
// (buildvizPacking). Centralizing it keeps mesh loading in ONE place so callers
// never reimplement STL parsing. The boundsTree assignment lets three-mesh-bvh
// accelerated raycasts/closest-point queries run against the returned geometry.
export const loadMeshGeometry = (data: ArrayBuffer): MeshGeometry => {
  const geometry = parseStl(data)
  const bvh = new MeshBVH(geometry)
  geometry.boundsTree = bvh
  return {
    geometry,
    bvh,
    triangleCount: (geometry.index ? geometry.index.count : geometry.attributes.position.count) / 3,
    localBox: geometry.boundingBox ?? new THREE.Box3(),
  }
}

export const worldAabb = (localBox: THREE.Box3, matrix: THREE.Matrix4) => {
  const min: [number, number, number] = [Infinity, Infinity, Infinity]
  const max: [number, number, number] = [-Infinity, -Infinity, -Infinity]
  const corner = new THREE.Vector3()
  for (let i = 0; i < 8; i += 1) {
    corner.set(
      i & 1 ? localBox.max.x : localBox.min.x,
      i & 2 ? localBox.max.y : localBox.min.y,
      i & 4 ? localBox.max.z : localBox.min.z,
    )
    corner.applyMatrix4(matrix)
    min[0] = Math.min(min[0], corner.x)
    min[1] = Math.min(min[1], corner.y)
    min[2] = Math.min(min[2], corner.z)
    max[0] = Math.max(max[0], corner.x)
    max[1] = Math.max(max[1], corner.y)
    max[2] = Math.max(max[2], corner.z)
  }
  return { min, max }
}

export const aabbDistance = (a: InstanceGeometry, b: InstanceGeometry) => {
  let sum = 0
  for (let axis = 0; axis < 3; axis += 1) {
    const gap = Math.max(0, a.worldMin[axis] - b.worldMax[axis], b.worldMin[axis] - a.worldMax[axis])
    sum += gap * gap
  }
  return Math.sqrt(sum)
}

// Sweep-and-prune over X with Y/Z interval tests. AABBs are expanded by half the
// tolerance each so any pair whose surfaces could be within tolerance becomes a
// candidate; the exact distance test in the narrow phase removes false hits.
export const broadPhasePairs = (instances: InstanceGeometry[], toleranceMm: number, maxPairs: number) => {
  const pad = toleranceMm / 2
  const boxes = instances.map((instance) => ({
    instance,
    minX: instance.worldMin[0] - pad,
    maxX: instance.worldMax[0] + pad,
    minY: instance.worldMin[1] - pad,
    maxY: instance.worldMax[1] + pad,
    minZ: instance.worldMin[2] - pad,
    maxZ: instance.worldMax[2] + pad,
  }))
  boxes.sort((a, b) => a.minX - b.minX)

  const pairs: Array<[InstanceGeometry, InstanceGeometry]> = []
  const active: typeof boxes = []
  let capped = false

  for (const box of boxes) {
    for (let i = active.length - 1; i >= 0; i -= 1) {
      if (active[i].maxX < box.minX) {
        active[i] = active[active.length - 1]
        active.pop()
      }
    }
    for (const other of active) {
      const overlap =
        box.minY <= other.maxY &&
        box.maxY >= other.minY &&
        box.minZ <= other.maxZ &&
        box.maxZ >= other.minZ
      if (!overlap) continue
      if (pairs.length >= maxPairs) {
        capped = true
        break
      }
      pairs.push([box.instance, other.instance])
    }
    if (capped) break
    active.push(box)
  }

  return { pairs, capped }
}

const tmpMatrix = new THREE.Matrix4()
export const tmpHit: { point: THREE.Vector3; distance: number; faceIndex: number } = {
  point: new THREE.Vector3(),
  distance: 0,
  faceIndex: 0,
}
const insideRayDir = new THREE.Vector3(0.5611, 0.6754, 0.4781).normalize()

// True when `localPoint` (already in the BVH geometry's local frame) is inside
// the mesh, using ray-crossing parity. Robust for the watertight STL solids
// CAD exporters emit regardless of triangle winding.
export const pointInside = (bvh: MeshBVH, localPoint: THREE.Vector3) => {
  const ray = new THREE.Ray(localPoint.clone(), insideRayDir)
  const hits = bvh.raycast(ray, THREE.DoubleSide)
  return hits.length % 2 === 1
}

const tmpHit2: { point: THREE.Vector3; distance: number; faceIndex: number } = {
  point: new THREE.Vector3(),
  distance: 0,
  faceIndex: 0,
}
const penWorld = new THREE.Vector3()
const penLocalA = new THREE.Vector3()
const penLocalB = new THREE.Vector3()

export const axisSamples = (lo: number, hi: number, count: number) => {
  const span = hi - lo
  if (count <= 1) return [lo + span / 2]
  const out: number[] = []
  for (let i = 0; i < count; i += 1) out.push(lo + (span * i) / (count - 1))
  return out
}

export type PenetrationResult = {
  depthMm: number
  /** Deepest shared-interior point, world coords (overlap anchor). */
  point: [number, number, number] | null
  /** World AABB of the sampled shared interior (localized overlap region). */
  region: { min: [number, number, number]; max: [number, number, number] } | null
}

// Penetration depth (mm) for an intersecting pair: probe a 3D grid spanning the
// world-space AABB overlap of the two parts, keep the points that lie strictly
// inside BOTH solids, and report the deepest such point's distance to the
// nearest surface of either part. Unlike vertex-only sampling this resolves
// shallow flat-face / edge clipping (the chassis oracle) yet reads ~0 for
// coincident touching mates (which enclose no shared interior volume). Assumes
// rigid instance transforms so local distances equal world millimetres.
//
// It ALSO localizes the overlap: every grid point confirmed inside BOTH solids
// expands a world-space AABB (`region`) and the deepest such point is kept as a
// contact anchor (`point`). The viewer shades that box so the overlapping volume
// is visible in place, instead of only outlining the two whole parts.
export const penetrationDepth = (a: InstanceGeometry, b: InstanceGeometry): PenetrationResult => {
  const empty: PenetrationResult = { depthMm: 0, point: null, region: null }
  const lo: [number, number, number] = [0, 0, 0]
  const dims: [number, number, number] = [0, 0, 0]
  for (let axis = 0; axis < 3; axis += 1) {
    const low = Math.max(a.worldMin[axis], b.worldMin[axis])
    const high = Math.min(a.worldMax[axis], b.worldMax[axis])
    if (high < low) return empty
    lo[axis] = low
    dims[axis] = high - low
  }

  // Spacing scales with the overlap volume so the point budget stays bounded
  // for both tiny clips and large intersections.
  const volume = Math.max(dims[0], 1e-3) * Math.max(dims[1], 1e-3) * Math.max(dims[2], 1e-3)
  const spacing = Math.max(MIN_GRID_SPACING_MM, Math.cbrt(volume / MAX_GRID_POINTS))
  const counts = dims.map((dim) =>
    Math.min(MAX_GRID_AXIS, Math.max(1, Math.floor(dim / spacing) + 1)),
  )
  const xs = axisSamples(lo[0], lo[0] + dims[0], counts[0])
  const ys = axisSamples(lo[1], lo[1] + dims[1], counts[1])
  const zs = axisSamples(lo[2], lo[2] + dims[2], counts[2])

  let maxDepth = 0
  let deepPoint: [number, number, number] | null = null
  const rMin: [number, number, number] = [Infinity, Infinity, Infinity]
  const rMax: [number, number, number] = [-Infinity, -Infinity, -Infinity]
  let insideCount = 0

  for (const x of xs) {
    for (const y of ys) {
      for (const z of zs) {
        penWorld.set(x, y, z)
        penLocalA.copy(penWorld).applyMatrix4(a.inverse)
        if (!pointInside(a.mesh.bvh, penLocalA)) continue
        penLocalB.copy(penWorld).applyMatrix4(b.inverse)
        if (!pointInside(b.mesh.bvh, penLocalB)) continue
        // Confirmed inside BOTH solids: grow the localized overlap region.
        insideCount += 1
        if (x < rMin[0]) rMin[0] = x
        if (y < rMin[1]) rMin[1] = y
        if (z < rMin[2]) rMin[2] = z
        if (x > rMax[0]) rMax[0] = x
        if (y > rMax[1]) rMax[1] = y
        if (z > rMax[2]) rMax[2] = z
        const hitA = a.mesh.bvh.closestPointToPoint(penLocalA, tmpHit)
        const dA = hitA ? hitA.distance : 0
        const hitB = b.mesh.bvh.closestPointToPoint(penLocalB, tmpHit2)
        const dB = hitB ? hitB.distance : 0
        const depth = Math.min(dA, dB)
        if (depth > maxDepth) {
          maxDepth = depth
          deepPoint = [x, y, z]
        }
      }
    }
  }

  if (insideCount === 0) return empty
  return {
    depthMm: maxDepth,
    point: deepPoint,
    region: { min: [...rMin], max: [...rMax] },
  }
}

// Exact min surface distance (mm) between two instances, querying on the larger
// mesh's BVH and transforming the smaller one into its frame. maxThreshold
// prunes the search; null means "farther than maxThreshold".
export const surfaceDistance = (a: InstanceGeometry, b: InstanceGeometry, maxThreshold: number) => {
  const [bvhInstance, otherInstance] =
    a.mesh.triangleCount >= b.mesh.triangleCount ? [a, b] : [b, a]
  const otherToBvh = tmpMatrix.copy(bvhInstance.inverse).multiply(otherInstance.matrix)
  const hit = bvhInstance.mesh.bvh.closestPointToGeometry(
    otherInstance.mesh.geometry,
    otherToBvh,
    tmpHit,
    tmpHit2,
    0,
    maxThreshold,
  )
  return hit ? hit.distance : Infinity
}

// ---------------------------------------------------------------------------
// Printability helpers (per unique mesh, geometry-only, ROBUST except thickness)
// ---------------------------------------------------------------------------

export type TopologyResult = {
  openEdges: number
  nonManifoldEdges: number
  inconsistentWinding: boolean
  degenerateTriangles: number
  volumeMm3: number
  /** Disjoint welded-vertex bodies (only computed when requested), else null. */
  componentCount: number | null
  /** Smallest body (likely stray island) for triage, in LOCAL mesh space. */
  smallestComponent: { triangleCount: number; volumeMm3: number; localPoint: THREE.Vector3 | null } | null
}

// Read the i-th vertex of triangle t (0..2) into `out`, honoring an index buffer.
export const readTriVertex = (
  position: THREE.BufferAttribute | THREE.InterleavedBufferAttribute,
  index: THREE.BufferAttribute | null,
  triangle: number,
  corner: number,
  out: THREE.Vector3,
) => {
  const vertex = index ? index.getX(triangle * 3 + corner) : triangle * 3 + corner
  out.set(position.getX(vertex), position.getY(vertex), position.getZ(vertex))
}

// Robust watertight / manifold / winding / degenerate analysis from triangle
// edge adjacency. STL solids store unshared vertices, so we weld by quantized
// position first. Edge keyed by sorted welded-vertex ids:
//   shared by 1 triangle  => open boundary edge (mesh has a hole)
//   shared by >2          => non-manifold edge
//   shared by 2 same dir  => inconsistent winding (a flipped normal)
// Enclosed volume via the signed-tetrahedron sum (~0 => flat shell, not a solid).
export class UnionFind {
  private parent: number[]
  private size: number[]
  constructor(count: number) {
    this.parent = Array.from({ length: count }, (_, i) => i)
    this.size = new Array(count).fill(1)
  }
  find(x: number): number {
    let root = x
    while (this.parent[root] !== root) root = this.parent[root]
    while (this.parent[x] !== root) {
      const next = this.parent[x]
      this.parent[x] = root
      x = next
    }
    return root
  }
  union(a: number, b: number) {
    const ra = this.find(a)
    const rb = this.find(b)
    if (ra === rb) return
    if (this.size[ra] < this.size[rb]) {
      this.parent[ra] = rb
      this.size[rb] += this.size[ra]
    } else {
      this.parent[rb] = ra
      this.size[ra] += this.size[rb]
    }
  }
}

export const analyzeTopology = (mesh: MeshGeometry, computeComponents = false): TopologyResult => {
  const geometry = mesh.geometry
  const position = geometry.attributes.position as THREE.BufferAttribute
  const index = geometry.index
  const triangleCount = mesh.triangleCount

  const size = new THREE.Vector3()
  mesh.localBox.getSize(size)
  const diag = Math.max(size.length(), 1e-6)
  // Weld tolerance: micron-scale, but never coarser than ~1e-6 of the diagonal.
  const weld = Math.max(1e-4, diag * 1e-6)
  const invWeld = 1 / weld

  const vertexIds = new Map<string, number>()
  const keyFor = (v: THREE.Vector3) =>
    `${Math.round(v.x * invWeld)},${Math.round(v.y * invWeld)},${Math.round(v.z * invWeld)}`
  const idFor = (v: THREE.Vector3) => {
    const key = keyFor(v)
    let id = vertexIds.get(key)
    if (id === undefined) {
      id = vertexIds.size
      vertexIds.set(key, id)
    }
    return id
  }

  // edge key (sorted) -> [totalCount, lowToHighCount]
  const edges = new Map<number, [number, number]>()
  const a = new THREE.Vector3()
  const b = new THREE.Vector3()
  const c = new THREE.Vector3()
  const ab = new THREE.Vector3()
  const ac = new THREE.Vector3()
  const cross = new THREE.Vector3()

  let degenerateTriangles = 0
  let volume6 = 0
  // Per non-degenerate triangle, packed [representativeVertexId, signedVol6,
  // cx, cy, cz] — only collected when computing connected components, so the
  // default topology pass keeps its existing cost/memory profile.
  const compTris: number[] = []

  const addEdge = (u: number, v: number) => {
    const lowToHigh = u < v ? 1 : 0
    const lo = u < v ? u : v
    const hi = u < v ? v : u
    const key = lo * 0x4000000 + hi // pack into one number (< 2^53 for < 67M verts)
    const entry = edges.get(key)
    if (entry) {
      entry[0] += 1
      entry[1] += lowToHigh
    } else {
      edges.set(key, [1, lowToHigh])
    }
  }

  for (let t = 0; t < triangleCount; t += 1) {
    readTriVertex(position, index, t, 0, a)
    readTriVertex(position, index, t, 1, b)
    readTriVertex(position, index, t, 2, c)

    ab.subVectors(b, a)
    ac.subVectors(c, a)
    cross.crossVectors(ab, ac)
    const area = cross.length() * 0.5
    // Signed volume of the tetrahedron (origin, a, b, c): a · (b × c) / 6.
    const triVol6 = a.dot(cross.copy(b).cross(c))
    volume6 += triVol6

    const ia = idFor(a)
    const ib = idFor(b)
    const ic = idFor(c)
    if (area <= DEGENERATE_AREA_MM2 || ia === ib || ib === ic || ia === ic) {
      degenerateTriangles += 1
      continue
    }
    addEdge(ia, ib)
    addEdge(ib, ic)
    addEdge(ic, ia)
    if (computeComponents) {
      compTris.push(
        ia,
        triVol6,
        (a.x + b.x + c.x) / 3,
        (a.y + b.y + c.y) / 3,
        (a.z + b.z + c.z) / 3,
      )
    }
  }

  let openEdges = 0
  let nonManifoldEdges = 0
  let inconsistentWinding = false
  for (const [count, lowToHigh] of edges.values()) {
    if (count === 1) openEdges += 1
    else if (count > 2) nonManifoldEdges += 1
    else if (count === 2 && lowToHigh !== 1) inconsistentWinding = true
  }

  // Connected-components: union welded vertices joined by any (non-degenerate)
  // triangle edge, then count distinct roots over the triangle set. >1 root means
  // the single mesh is actually multiple disjoint bodies (a floating island).
  let componentCount: number | null = null
  let smallestComponent: TopologyResult['smallestComponent'] = null
  if (computeComponents) {
    const uf = new UnionFind(vertexIds.size)
    for (const key of edges.keys()) {
      const hi = key % 0x4000000
      const lo = (key - hi) / 0x4000000
      uf.union(lo, hi)
    }
    const comps = new Map<number, { tri: number; vol6: number; cx: number; cy: number; cz: number }>()
    for (let i = 0; i < compTris.length; i += 5) {
      const root = uf.find(compTris[i])
      const entry = comps.get(root) ?? { tri: 0, vol6: 0, cx: 0, cy: 0, cz: 0 }
      entry.tri += 1
      entry.vol6 += compTris[i + 1]
      entry.cx += compTris[i + 2]
      entry.cy += compTris[i + 3]
      entry.cz += compTris[i + 4]
      comps.set(root, entry)
    }
    componentCount = comps.size
    if (comps.size > 1) {
      let best: { vol: number; tri: number; cx: number; cy: number; cz: number } | null = null
      for (const entry of comps.values()) {
        const vol = Math.abs(entry.vol6) / 6
        if (!best || vol < best.vol) {
          best = { vol, tri: entry.tri, cx: entry.cx / entry.tri, cy: entry.cy / entry.tri, cz: entry.cz / entry.tri }
        }
      }
      if (best) {
        smallestComponent = {
          triangleCount: best.tri,
          volumeMm3: best.vol,
          localPoint: new THREE.Vector3(best.cx, best.cy, best.cz),
        }
      }
    }
  }

  return {
    openEdges,
    nonManifoldEdges,
    inconsistentWinding,
    degenerateTriangles,
    volumeMm3: Math.abs(volume6) / 6,
    componentCount,
    smallestComponent,
  }
}

// HEURISTIC min wall thickness: sample triangle centroids (strided to a budget),
// determine the inward normal, then cast an inward ray and take the nearest
// forward surface hit as the local wall thickness. Returns the minimum and its
// local-space location. Not an exact medial-axis thickness — it underestimates
// at sharp interior corners (so we WARN, never FAIL) and is bounded for speed.
export const estimateMinWall = (
  mesh: MeshGeometry,
  maxSamples: number,
): { minWallMm: number | null; localPoint: THREE.Vector3 | null } => {
  const geometry = mesh.geometry
  const position = geometry.attributes.position as THREE.BufferAttribute
  const index = geometry.index
  const triangleCount = mesh.triangleCount
  if (triangleCount === 0) return { minWallMm: null, localPoint: null }

  const stride = Math.max(1, Math.floor(triangleCount / maxSamples))
  const a = new THREE.Vector3()
  const b = new THREE.Vector3()
  const c = new THREE.Vector3()
  const centroid = new THREE.Vector3()
  const normal = new THREE.Vector3()
  const ab = new THREE.Vector3()
  const ac = new THREE.Vector3()
  const probe = new THREE.Vector3()

  // Collect a per-sample thickness + its surface point, then report a low
  // PERCENTILE rather than the raw minimum: a genuine thin wall produces many
  // thin samples (its whole face), while a lone tessellation/grazing artifact is
  // a single outlier the percentile discards. This is what keeps valid builds
  // from being flooded with spurious sub-tenth-mm "thin wall" readings.
  const samples: Array<{ thickness: number; point: THREE.Vector3 }> = []

  for (let t = 0; t < triangleCount; t += stride) {
    readTriVertex(position, index, t, 0, a)
    readTriVertex(position, index, t, 1, b)
    readTriVertex(position, index, t, 2, c)
    ab.subVectors(b, a)
    ac.subVectors(c, a)
    normal.crossVectors(ab, ac)
    const len = normal.length()
    if (len <= 1e-9) continue
    normal.multiplyScalar(1 / len)
    centroid.copy(a).add(b).add(c).multiplyScalar(1 / 3)

    // Orient inward: step a hair off the face and keep the side that is inside.
    probe.copy(centroid).addScaledVector(normal, -WALL_MIN_HIT_MM)
    const inwardSign = pointInside(mesh.bvh, probe) ? -1 : 1

    const rayDir = normal.clone().multiplyScalar(inwardSign)
    const origin = probe.copy(centroid).addScaledVector(normal, inwardSign * WALL_MIN_HIT_MM)
    const ray = new THREE.Ray(origin.clone(), rayDir)
    const hits = mesh.bvh.raycast(ray, THREE.DoubleSide)
    let nearest = Infinity
    for (const hit of hits) {
      if (hit.distance <= WALL_MIN_HIT_MM || hit.distance >= nearest) continue
      // Only count a hit on a roughly-OPPOSING surface as a "wall": the opposite
      // face of a wall is ~parallel to this face, so its normal is ~parallel to
      // the ray axis. Grazing hits on adjacent facets at concave corners / hole
      // rims are ~perpendicular and are rejected — that is the main source of
      // spurious sub-tenth-mm "thin wall" readings. Winding-agnostic (|dot|).
      const hitNormal = hit.face?.normal
      if (hitNormal && Math.abs(hitNormal.dot(rayDir)) < WALL_OPPOSING_DOT) continue
      nearest = hit.distance
    }
    if (Number.isFinite(nearest)) {
      samples.push({ thickness: nearest + WALL_MIN_HIT_MM, point: centroid.clone() })
    }
  }

  if (samples.length === 0) return { minWallMm: null, localPoint: null }
  samples.sort((x, y) => x.thickness - y.thickness)
  // 1st-percentile (min index 0), but require a few corroborating samples below
  // it so a single artifact never sets the result on a well-sampled mesh.
  const idx = Math.min(samples.length - 1, Math.max(WALL_MIN_CORROBORATING, Math.floor(samples.length * WALL_PERCENTILE)))
  const chosen = samples[idx]
  return { minWallMm: chosen.thickness, localPoint: chosen.point.clone() }
}

// ROBUST self-intersection detection: count triangle PAIRS within one mesh that
// actually cross each other, the classic slicer-breaking fault that the open-
// edge / non-manifold tests miss (those check topology; this checks geometry).
//
// For each triangle we shapecast its AABB against the mesh's own BVH and run a
// separating-axis triangle-triangle test (three-mesh-bvh's ExtendedTriangle) on
// every candidate. Two sources of false positives are removed: (1) topologically
// ADJACENT triangles (sharing a welded vertex) always "touch" at that vertex/edge
// and are skipped; (2) contacts whose intersection segment is shorter than an
// epsilon are coplanar grazes, not crossings. What remains is genuine: a facet
// poking through another facet. Bounded by SELF_INTERSECTION_MAX_TRIANGLES.
export const detectSelfIntersections = (
  mesh: MeshGeometry,
): { count: number | null; localPoint: THREE.Vector3 | null } => {
  const geometry = mesh.geometry
  const triangleCount = mesh.triangleCount
  if (triangleCount === 0) return { count: 0, localPoint: null }
  if (triangleCount > SELF_INTERSECTION_MAX_TRIANGLES) return { count: null, localPoint: null }

  const position = geometry.attributes.position as THREE.BufferAttribute
  const index = geometry.index

  // Weld vertices by quantized position (STL stores unshared vertices) so we can
  // recognize adjacency. triWeld[t*3 + k] = welded id of triangle t's vertex k.
  const size = new THREE.Vector3()
  mesh.localBox.getSize(size)
  const diag = Math.max(size.length(), 1e-6)
  const weld = Math.max(1e-4, diag * 1e-6)
  const invWeld = 1 / weld
  const vertexIds = new Map<string, number>()
  const v = new THREE.Vector3()
  const triWeld = new Int32Array(triangleCount * 3)
  for (let t = 0; t < triangleCount; t += 1) {
    for (let k = 0; k < 3; k += 1) {
      readTriVertex(position, index, t, k, v)
      const key = `${Math.round(v.x * invWeld)},${Math.round(v.y * invWeld)},${Math.round(v.z * invWeld)}`
      let id = vertexIds.get(key)
      if (id === undefined) {
        id = vertexIds.size
        vertexIds.set(key, id)
      }
      triWeld[t * 3 + k] = id
    }
  }

  const adjacent = (t1: number, t2: number) => {
    const a0 = triWeld[t1 * 3]
    const a1 = triWeld[t1 * 3 + 1]
    const a2 = triWeld[t1 * 3 + 2]
    for (let k = 0; k < 3; k += 1) {
      const b = triWeld[t2 * 3 + k]
      if (b === a0 || b === a1 || b === a2) return true
    }
    return false
  }

  const triA = new ExtendedTriangle()
  // The runtime supports a third `suppressLog` arg (coplanar contacts log a
  // warning otherwise); the bundled types omit it, so call through a cast.
  const intersects = triA.intersectsTriangle.bind(triA) as (
    other: ExtendedTriangle,
    target?: THREE.Line3,
    suppressLog?: boolean,
  ) => boolean
  const a = new THREE.Vector3()
  const b = new THREE.Vector3()
  const c = new THREE.Vector3()
  const triBox = new THREE.Box3()
  const seg = new THREE.Line3()
  const mid = new THREE.Vector3()
  const onTri = new THREE.Vector3()
  let count = 0
  let firstPoint: THREE.Vector3 | null = null
  const bvh = mesh.bvh

  for (let t = 0; t < triangleCount; t += 1) {
    readTriVertex(position, index, t, 0, a)
    readTriVertex(position, index, t, 1, b)
    readTriVertex(position, index, t, 2, c)
    triA.a.copy(a)
    triA.b.copy(b)
    triA.c.copy(c)
    // intersectsTriangle lazily refreshes the cached separating axes when this
    // flag is set, so no explicit update() call is needed.
    triA.needsUpdate = true
    triBox.makeEmpty()
    triBox.expandByPoint(a).expandByPoint(b).expandByPoint(c)

    bvh.shapecast({
      intersectsBounds: (box: THREE.Box3) => box.intersectsBox(triBox),
      intersectsTriangle: (tri: ExtendedTriangle, triIndex: number) => {
        // Each unordered pair once (triIndex > t), and never an adjacent pair.
        if (triIndex <= t || adjacent(t, triIndex)) return false
        // suppressLog=true: coplanar contacts can't yield an output edge and
        // would otherwise spam a warning; they read seg.distance()==0 and are
        // rejected by the epsilon below as grazes anyway.
        if (intersects(tri, seg, true)) {
          if (seg.distance() > SELF_INTERSECTION_MIN_SEGMENT_MM) {
            // NEAR-coplanar false-positive guard: for two triangles in almost
            // the same plane (e.g. two disjoint remnants of one boolean-cut
            // face), the SAT plane-line clip is ill-conditioned and can emit a
            // long garbage segment even though the triangles are far apart
            // in-plane. A REAL crossing's segment lies ON both triangles, so
            // require the segment midpoint to be (near-)coincident with each.
            seg.getCenter(mid)
            triA.closestPointToPoint(mid, onTri)
            const dA = onTri.distanceTo(mid)
            tri.closestPointToPoint(mid, onTri)
            const dB = onTri.distanceTo(mid)
            if (dA < SELF_INTERSECTION_MIN_SEGMENT_MM && dB < SELF_INTERSECTION_MIN_SEGMENT_MM) {
              count += 1
              if (!firstPoint) firstPoint = mid.clone()
            }
          }
        }
        return false // keep traversing; we want the total count
      },
    })
  }

  return { count, localPoint: firstPoint }
}

export const round3 = (value: number) => Math.round(value * 1000) / 1000
export const roundVec = (v: [number, number, number]): Vec3 => [round3(v[0]), round3(v[1]), round3(v[2])]

export type GeometryLoadOptions = {
  loadMesh: (mesh: BuildMesh) => Promise<ArrayBuffer | null>
  /** Include fastener meshes (off by default, like the interference checker). */
  includeFasteners?: boolean
  /** Restrict to these partTypes (e.g. the CLI `--part` filter). */
  partTypes?: Set<string>
  /** Restrict to these instance ids (e.g. the CLI `--instance` filter). */
  instanceIds?: Set<string>
}

// Load + BVH every unique mesh once and build the world-placed instance set,
// honoring the fastener/part/instance filters. Shared by every query command.
export const buildInstanceGeometries = async (
  manifest: BuildSceneManifest,
  options: GeometryLoadOptions,
): Promise<{ instances: InstanceGeometry[]; meshById: Map<string, MeshGeometry>; missingMeshes: string[]; fastenersExcluded: number }> => {
  const includeFasteners = options.includeFasteners ?? false
  const fastenerMeshIds = new Set(manifest.meshes.filter((mesh) => isFastenerMesh(mesh)).map((mesh) => mesh.id))
  const meshById = new Map<string, MeshGeometry>()
  const missingMeshes: string[] = []
  await Promise.all(
    manifest.meshes.map(async (mesh) => {
      try {
        const data = await options.loadMesh(mesh)
        if (!data) {
          missingMeshes.push(mesh.id)
          return
        }
        const geometry = parseStl(data)
        meshById.set(mesh.id, {
          geometry,
          bvh: new MeshBVH(geometry),
          triangleCount: (geometry.index ? geometry.index.count : geometry.attributes.position.count) / 3,
          localBox: geometry.boundingBox ?? new THREE.Box3(),
        })
      } catch {
        missingMeshes.push(mesh.id)
      }
    }),
  )
  for (const mesh of meshById.values()) mesh.geometry.boundsTree = mesh.bvh

  let fastenersExcluded = 0
  const instances: InstanceGeometry[] = []
  manifest.instances.forEach((instance, index) => {
    const mesh = meshById.get(instance.meshId)
    if (!mesh) return
    const isFastener = fastenerMeshIds.has(instance.meshId)
    if (isFastener && !includeFasteners) {
      fastenersExcluded += 1
      return
    }
    if (options.partTypes && !options.partTypes.has(instance.partType)) return
    if (options.instanceIds && !options.instanceIds.has(instance.id)) return
    const matrix = new THREE.Matrix4().fromArray(instance.transform)
    const { min, max } = worldAabb(mesh.localBox, matrix)
    instances.push({
      index,
      instanceId: instance.id,
      meshId: instance.meshId,
      partType: instance.partType,
      name: instance.name,
      mesh,
      matrix,
      inverse: new THREE.Matrix4().copy(matrix).invert(),
      worldMin: min,
      worldMax: max,
      isFastener,
    })
  })
  return { instances, meshById, missingMeshes, fastenersExcluded }
}

export const pointInAabb = (instance: InstanceGeometry, p: THREE.Vector3, pad = 0) =>
  p.x >= instance.worldMin[0] - pad &&
  p.x <= instance.worldMax[0] + pad &&
  p.y >= instance.worldMin[1] - pad &&
  p.y <= instance.worldMax[1] + pad &&
  p.z >= instance.worldMin[2] - pad &&
  p.z <= instance.worldMax[2] + pad

// World-space AABB distance from a point to an instance's bounds (0 when inside).
export const pointAabbDistance = (instance: InstanceGeometry, p: THREE.Vector3) => {
  const dx = Math.max(0, instance.worldMin[0] - p.x, p.x - instance.worldMax[0])
  const dy = Math.max(0, instance.worldMin[1] - p.y, p.y - instance.worldMax[1])
  const dz = Math.max(0, instance.worldMin[2] - p.z, p.z - instance.worldMax[2])
  return Math.sqrt(dx * dx + dy * dy + dz * dz)
}