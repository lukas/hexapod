import * as THREE from 'three'
import { checkFastenings } from './fastenings'
import { MeshBVH } from 'three-mesh-bvh'
import type {
  AllowedInterference,
  BuildMesh,
  BuildSceneManifest,
  OverlapAllowance,
  Route,
  Vec3,
} from '../core/buildScene'
import { jointMotionGroups, resolveOverlapAllowance } from '../core/buildScene'
import {
  DEFAULT_MAX_UNSUPPORTED_MM,
  DEFAULT_WIRE_CLEARANCE_MM,
  effectiveMinBendRadiusMm,
  minBendRadius,
  polylineLength,
  resolveRoute,
  sampleRoute,
  unsupportedSpans,
} from '../core/buildWiring'
import {
  INTERSECTION_EPSILON,
  UnionFind,
  aabbDistance,
  analyzeTopology,
  axisSamples,
  broadPhasePairs,
  buildInstanceGeometries,
  detectSelfIntersections,
  estimateMinWall,
  isFastenerMesh,
  parseStl,
  pointAabbDistance,
  pointInAabb,
  pointInside,
  penetrationDepth,
  readTriVertex,
  round3,
  roundVec,
  surfaceDistance,
  tmpHit,
  worldAabb,
  type GeometryLoadOptions,
  type InstanceGeometry,
  type MeshGeometry,
  type PenetrationResult,
} from '../core/geometryEngine'

// Geometry-based design sanity checker.
//
// The checker works purely from scene.json + its STL assets so it runs without
// a design_spec.yaml. It answers two questions an LLM-generated assembly often
// gets wrong:
//   1. Interference  - do any two parts actually overlap in space?
//   2. Connectivity  - is every part attached to the main assembly, or are
//                      some parts floating in space / left with a gap?
//
// Performance is a hard requirement (the largest build has ~674 instances), so
// the pipeline is:
//   - load each UNIQUE mesh once and build a BVH per geometry (reused by every
//     instance that references it)
//   - broad phase: world-space AABB + sweep-and-prune to enumerate only the
//     candidate instance pairs whose bounds are within tolerance
//   - narrow phase: BVH-accelerated exact triangle distance on candidates only,
//     plus an interior volume-sampling penetration depth for intersecting pairs.
//
// Fasteners (screws, nuts, washers, heat-set inserts, dowel pins, ...) are
// MODELLED as solids that deliberately occupy their host's tapped/clearance
// holes, so they interfere by design. Like every CAD interference checker we
// suppress the fastener library by default (pass includeFasteners to analyze
// them too). This both removes thousands of "screw vs hole" false positives and
// keeps large builds fast, since fasteners are usually the bulk of the instances.

export type CheckCollision = {
  a: { instanceId: string; partType: string; name: string }
  b: { instanceId: string; partType: string; name: string }
  /**
   * Estimated penetration depth in mm: the deepest interior point shared by both
   * solids, measured as its distance to the nearest surface of either part. This
   * is robust for shallow flat-face / edge clipping (where vertex-only sampling
   * underestimates) while reading ~0 for intended touching mates (coincident
   * faces enclose no shared volume), so touching mates are not flagged.
   */
  penetrationMm: number
  /** World-space anchor at the deepest shared interior point (overlap centre). */
  point: [number, number, number] | null
  /** World-space AABB enclosing the sampled overlap interior — a localized box
   *  around the contact/interpenetration region, NOT the full part bounds. Used
   *  by the viewer to shade just the overlapping volume. */
  region: { min: [number, number, number]; max: [number, number, number] } | null
  /** True when this pair is an allowed interference — a typed instance-level
   *  checksConfig.allowedInterferences entry, or the legacy partType-level
   *  ignoreOverlapPairs blanket (static parts only). Still reported for audit,
   *  but does NOT count toward problemCount / results.passed. */
  allowed?: boolean
  /** How the allowance was decided (source / kind / reason), including refusals:
   *  a matching entry that was rejected because the penetration exceeds its
   *  declared cap, or a legacy partType ignore rejected because the two parts
   *  move relative to each other (joints[]). Absent when nothing matched. */
  allowance?: OverlapAllowance
}

export type CheckFloating = {
  instanceId: string
  partType: string
  name: string
  componentId: number
  componentSize: number
  /** Closest surface distance from this part to the main assembly, in mm. */
  nearestGapMm: number | null
  nearestInstanceId: string | null
}

export type CheckGap = {
  instanceId: string
  partType: string
  name: string
  gapMm: number
  nearestInstanceId: string
}

// ---------------------------------------------------------------------------
// Printability / assembleability result shapes (CLI gate). These are computed
// per-UNIQUE-mesh (printability) or per-instance (assembleability) and reuse the
// BVHs already built for interference. They are plain-data so the THREE-free
// buildvizChecks module can turn them into generic SceneCheck records.
// ---------------------------------------------------------------------------

/**
 * Per-unique-mesh printability findings. `watertight`/`manifold`/`degenerate`
 * are ROBUST (exact triangle-edge adjacency); `minWallMm` is a HEURISTIC
 * estimate from inward ray casts, not an exact medial-axis thickness.
 */
export type MeshPrintability = {
  meshId: string
  meshName: string
  /** Every instance referencing this mesh (so a per-mesh issue can highlight). */
  instanceIds: string[]
  triangleCount: number
  /** Boundary edges shared by exactly one triangle (mesh has holes). Null when
   *  the topology check was not run. */
  openEdges: number | null
  /** Edges shared by more than two triangles (non-manifold). Null when not run. */
  nonManifoldEdges: number | null
  /** Two triangles traverse a shared edge the same way (flipped normal). */
  inconsistentWinding: boolean
  /** Triangles with ~zero area (collinear/coincident vertices). Null when not run. */
  degenerateTriangles: number | null
  /** Count of non-adjacent triangle PAIRS within this mesh that intersect each
   *  other (a slicer-breaking self-intersection). ROBUST: a separating-axis
   *  triangle-triangle test, skipping topologically-adjacent (shared-vertex)
   *  pairs and contacts shorter than an epsilon (coplanar edge touches). Null
   *  when the self-intersection pass was not run. */
  selfIntersections: number | null
  /** World-space anchor at a representative self-intersection contact. */
  selfIntersectionPoint: [number, number, number] | null
  /** Number of disjoint connected-components (welded-vertex bodies) in the mesh.
   *  >1 means the single part mesh contains a detached island / floating ring (an
   *  INTRA-mesh fault, distinct from inter-part connectivity). ROBUST: union-find
   *  over the same welded vertex ids used for watertightness. Null when not run. */
  componentCount: number | null
  /** The smallest disjoint body (the likely stray island) for triage/shading.
   *  Null when there is one component or the pass was not run. */
  smallestComponent: { triangleCount: number; volumeMm3: number; point: [number, number, number] | null } | null
  /** Enclosed volume in mm³; ~0 means a flat shell / open surface. */
  volumeMm3: number | null
  /** Estimated min wall thickness (mm), or null when not computed. HEURISTIC. */
  minWallMm: number | null
  /** World-space anchor of the thinnest sample on a representative instance. */
  thinPoint: [number, number, number] | null
}

/**
 * Per-fastener thread-engagement / grip estimate. HEURISTIC: measures the axial
 * length over which the fastener shaft is surrounded by host (non-fastener)
 * material, by probing a ring just outside the shaft at stations along the axis.
 */
export type FastenerEngagement = {
  instanceId: string
  partType: string
  name: string
  /** Axial length of the fastener along its principal axis, in mm. */
  shaftLengthMm: number
  /** Estimated engaged length (shaft surrounded by host material), in mm. */
  engagementMm: number
  /** Host (non-fastener) instances the fastener engages. */
  hostInstanceIds: string[]
  /** World-space anchor near the fastener's engaged region. */
  point: [number, number, number] | null
}

/**
 * Per-part assembly-access feasibility. COARSE HEURISTIC: tests a small set of
 * straight-line extraction directions (±X/±Y/±Z and radial-out) with an AABB
 * "shadow" sweep against already-present parts; a part with no clear direction
 * may not be installable/removable in place. Not a motion planner.
 */
export type AssemblyAccess = {
  instanceId: string
  partType: string
  name: string
  /** Candidate extraction directions tested. */
  directionsTried: number
  /** Directions with a collision-free straight-line sweep out of the assembly. */
  clearDirections: number
  point: [number, number, number] | null
}

/**
 * Audit of one checksConfig.allowedInterferences entry against the actual
 * geometry. Every declared allowance is verified so the allowlist cannot rot:
 *  - 'overlapping': the declared interference exists (within its cap) — pass.
 *  - 'in_contact': no deep overlap, but the parts touch — pass (e.g. a
 *    press fit modeled at exact size).
 *  - 'exceeds_max_penetration': present but DEEPER than the entry's declared
 *    maxPenetrationMm — fail.
 *  - 'not_in_contact': the parts are apart — a stale entry (or a drifted
 *    part); fail so dead allowances get cleaned up.
 *  - 'unknown_instance': an instance id in the entry is not in the scene (or
 *    its mesh failed to load) — fail.
 */
export type DeclaredInterferenceResult = {
  kind: string
  instances: [string, string]
  reason: string
  feature: string | null
  maxPenetrationMm: number | null
  outcome:
    | 'overlapping'
    | 'in_contact'
    | 'not_in_contact'
    | 'exceeds_max_penetration'
    | 'unknown_instance'
  /** Measured interior penetration (mm) when overlapping; null otherwise. */
  penetrationMm: number | null
  /** Surface gap (mm) when not overlapping; null when overlapping/unknown or
   *  beyond the mating search window. */
  gapMm: number | null
  point: [number, number, number] | null
  region: { min: [number, number, number]; max: [number, number, number] } | null
  /** True when the same pair is also in collisions[] (so an over-cap entry is
   *  not double-counted in problemCount). */
  reportedAsCollision: boolean
}

/** Declared-interference outcomes that count as problems (fail the gate). */
export const isDeclaredInterferenceIssue = (result: DeclaredInterferenceResult) =>
  result.outcome === 'not_in_contact' ||
  result.outcome === 'unknown_instance' ||
  result.outcome === 'exceeds_max_penetration'

/**
 * Per-instance-pair mating-face contact result (assembleability gate). A
 * "mating pair" is either DECLARED (its partTypes are listed in the project's
 * `ignoreOverlapPairs`, i.e. an intended interface) or LIKELY (two non-fastener
 * parts whose surfaces are near-touching). The check verifies the contact is
 * within a tight tolerance: in contact (gap ~0) rather than floating apart or
 * interpenetrating deeply. ROBUST surface metric (exact BVH surface distance +
 * interior-grid penetration depth), reusing the interference engine.
 */
export type MatingContact = {
  a: { instanceId: string; partType: string; name: string }
  b: { instanceId: string; partType: string; name: string }
  /** True when the pair's partTypes are an intended mating (ignoreOverlapPairs). */
  declared: boolean
  /** Surface gap (mm) when the parts are separated; 0 when touching/intersecting. */
  gapMm: number
  /** Interior penetration depth (mm) when interpenetrating; 0 otherwise. */
  penetrationMm: number
  /** World-space anchor near the contact (overlap centre or nearest point). */
  point: [number, number, number] | null
  region: { min: [number, number, number]; max: [number, number, number] } | null
}

/**
 * Per-route cable/harness wiring result (assembleability gate, schema-first).
 * Measured on the SAMPLED Catmull-Rom curve through the resolved waypoints
 * (the same curve the viewer draws): total length vs an optional budget,
 * pass-through-solid obstruction, tightest bend radius vs the allowed minimum
 * (explicit or 6 × OD), longest span between anchors vs the support-spacing
 * budget, and closest approach to a non-termination solid (chafing).
 * HEURISTIC where noted — it does not model slack or connector seating.
 * Automatic harness inference (without route data) is intentionally NOT
 * attempted; see plans/validation.md (non-goals) and plans/wiring.md.
 */
export type RoutingReach = {
  routeId: string
  label: string
  /** Total routed curve length (mm). */
  lengthMm: number
  /** Budget the route must stay within (mm), or null when none was supplied. */
  maxLengthMm: number | null
  /** Instances whose solids a routed segment passes through (obstructions). */
  blockingInstanceIds: string[]
  /** World-space anchor at the first obstruction (or the route midpoint). */
  point: [number, number, number] | null
  /** Bundle outer diameter (mm), or null when unspecified. */
  diameterMm: number | null
  /** Number of anchored (physically secured) waypoints, endpoints included. */
  anchorCount: number
  /** Tightest measured bend radius (mm), or null for straight/short paths. */
  minBendRadiusMm: number | null
  /** Allowed minimum bend radius (mm): explicit or 6 × OD; null = unchecked. */
  minBendRadiusAllowedMm: number | null
  /** Where the tightest bend occurs. */
  bendPoint: [number, number, number] | null
  /** Longest measured span between consecutive anchors (mm). */
  maxUnsupportedMm: number | null
  /** Allowed span between anchors (mm) before wire_support asks for a clip. */
  maxUnsupportedAllowedMm: number
  /** Midpoint of the longest span — where a clip/tie would help. */
  spanPoint: [number, number, number] | null
  /** Closest wire-surface-to-solid air gap seen below the clearance threshold
   *  (mm), or null when the route stays clear. */
  clearanceMm: number | null
  /** The solid the wire passes closest to (when clearanceMm is set). */
  clearanceInstanceId: string | null
  clearancePoint: [number, number, number] | null
  /** Waypoint instance ids that were not found in the scene. */
  missingInstances: string[]
}

export type CheckTimings = {
  loadMs: number
  bvhMs: number
  broadMs: number
  narrowMs: number
  connectivityMs: number
  printabilityMs: number
  threadMs: number
  accessMs: number
  matingMs: number
  routingMs: number
  totalMs: number
}

export type CheckReport = {
  passed: boolean
  problemCount: number
  toleranceMm: number
  minPenetrationMm: number
  instanceCount: number
  meshCount: number
  missingMeshes: string[]
  fastenersExcluded: number
  fastenersIncluded: boolean
  broadPhasePairs: number
  narrowPhasePairs: number
  capped: boolean
  collisions: CheckCollision[]
  floating: CheckFloating[]
  gaps: CheckGap[]
  /** Audit of every checksConfig.allowedInterferences entry (empty when none). */
  declaredInterferences: DeclaredInterferenceResult[]
  /** Per-unique-mesh printability findings (empty unless enabled). */
  printability: MeshPrintability[]
  /** Per-fastener engagement findings (empty unless enabled). */
  fasteners: FastenerEngagement[]
  fasteningChecks?: import('../core/buildScene').SceneCheck[]
  /** Per-part assembly-access findings (empty unless enabled). */
  access: AssemblyAccess[]
  /** Per-pair mating-face contact findings (empty unless enabled). */
  mating: MatingContact[]
  /** Per-route cable/harness routing-reach findings (empty unless enabled). */
  routing: RoutingReach[]
  /** Thresholds the printability/assembleability checks were run with. */
  minWallMm: number
  minThreadEngagementMm: number
  matingToleranceMm: number
  components: {
    count: number
    mainComponentSize: number
    floatingComponentCount: number
  }
  timings: CheckTimings
}

export type CheckOptions = {
  /** Surface separation (mm) treated as "in contact" for connectivity: two
   *  parts whose surfaces are within this distance are considered joined. */
  toleranceMm?: number
  /** Penetration depth (mm) at or above which an overlap is reported as a
   *  collision. Intended touching mates read ~0 penetration with the interior
   *  volume metric, so this stays small. Defaults to DEFAULT_MIN_PENETRATION_MM. */
  minPenetrationMm?: number
  /** Cap on candidate pairs processed in the narrow phase (keeps large builds
   *  bounded). When exceeded the report is flagged `capped`. */
  maxPairs?: number
  /** Floating parts whose closest approach to the main assembly is within this
   *  window (mm) are also surfaced as "suspicious gaps". */
  gapWindowMm?: number
  /** Include fastener parts (screws, nuts, inserts, ...) in the interference and
   *  connectivity analysis. Off by default: fasteners are expected to overlap
   *  the holes they sit in, so analyzing them floods the report and is slow. */
  includeFasteners?: boolean
  /** Run robust watertight/manifold + degenerate-geometry topology checks per
   *  unique (non-fastener) mesh. Cheap. Off unless set (the live viewer stays
   *  on the fast spatial overlays; the CLI gate turns these on). */
  checkWatertight?: boolean
  /** Estimate min wall thickness per unique (non-fastener) mesh via inward ray
   *  casts. HEURISTIC, bounded by wallSamples. Off unless set. */
  checkWallThickness?: boolean
  /** Detect triangle self-intersections per unique (non-fastener) mesh (a
   *  slicer-breaking printability fault). ROBUST triangle-triangle test, bounded
   *  by selfIntersectionMaxTriangles. Off unless set. */
  checkSelfIntersection?: boolean
  /** Count disjoint welded-vertex bodies per unique (non-fastener) mesh and gate
   *  on meshes with more than their expected count (a floating island / detached
   *  ring). ROBUST, O(triangles) on the weld pass. Off unless set. */
  checkComponents?: boolean
  /** Per-mesh expected disjoint body count (mesh.id → count) for checkComponents. */
  expectedMeshComponents?: Record<string, number>
  /** Global default expected disjoint body count (defaults to 1). */
  maxMeshComponents?: number
  /** Estimate per-fastener thread engagement / grip. HEURISTIC. Off unless set. */
  checkThreadEngagement?: boolean
  /** Test per-part straight-line extraction feasibility. COARSE HEURISTIC and
   *  the most expensive group; off unless set. */
  checkAssemblyAccess?: boolean
  /** Verify declared / near-touching mating pairs are in contact within tolerance
   *  (not floating apart or interpenetrating deeply). ROBUST. Off unless set. */
  checkMatingContact?: boolean
  /** Min acceptable wall thickness (mm); thinner meshes are flagged. */
  minWallMm?: number
  /** Min acceptable fastener engagement (mm); shorter grips are flagged. */
  minThreadEngagementMm?: number
  /** Allowed mating gap/overlap (mm). A mating pair is "in contact" when its gap
   *  AND its penetration are within this; otherwise it floats / crashes. */
  matingToleranceMm?: number
  /** Intended mating pairs, by partType (the project's ignoreOverlapPairs). Used
   *  to decide which pairs are DECLARED matings for the mating-contact gate. */
  matingPairs?: Array<[string, string]>
  /** Producer-supplied cable/harness routes for the routing-reach gate. */
  routes?: Route[]
  /** Min wire-surface-to-solid air gap (mm) before wire_clearance warns. */
  wireClearanceMm?: number
  /** Default longest allowed span between wire anchors (mm) for wire_support;
   *  a route's own maxUnsupportedMm overrides. */
  maxUnsupportedMm?: number
  /** Upper bound on surface samples per mesh for wall-thickness (speed knob). */
  wallSamples?: number
  /** Reads the raw STL bytes for a mesh, or null when the asset is missing. */
  loadMesh: (mesh: BuildMesh) => Promise<ArrayBuffer | null>
}

const DEFAULT_TOLERANCE_MM = 0.5
// Penetration at/above which an overlap is reported as a collision. Real
// interferences here (the oracle clips, electronics overlapping trays, ...) run
// well over 1mm, while intended touching mates read ~0 and slightly-modelled
// press-fit mates (servo horns, joint pads) sit a few tenths of a mm; 1.0mm
// keeps the former and suppresses the latter.
const DEFAULT_MIN_PENETRATION_MM = 1.0
const DEFAULT_MAX_PAIRS = 400_000
const DEFAULT_GAP_WINDOW_MM = 8
// Only compute per-part gap distances when the floating set is small enough to
// stay fast; very large floating sets skip the (optional) gap enrichment.
const MAX_GAP_INSTANCES = 400

// --- Printability / assembleability defaults ---
// Min wall thickness (mm) below which a mesh is flagged. 0.8mm is a permissive
// FDM-ish floor: thinner than two 0.4mm perimeters. Heuristic, so it WARNs.
const DEFAULT_MIN_WALL_MM = 0.8
// Min fastener thread engagement / grip (mm) below which a fastener is flagged.
// ~1x an M3 diameter; conservative so well-seated hardware is not flagged.
const DEFAULT_MIN_THREAD_ENGAGEMENT_MM = 2.0
// Surface samples per unique mesh for the wall-thickness estimate (bounded).
const DEFAULT_WALL_SAMPLES = 1500
// Axial stations sampled along a fastener for the engagement estimate, and the
// number of ring probes per station just outside the shaft surface.
const THREAD_STATIONS = 24
const THREAD_RING_PROBES = 6
// Ring probe radius as a fraction beyond the shaft radius (just into the host).
const THREAD_RING_SCALE = 1.08
// --- Mating-face contact defaults ---
// Allowed gap/overlap (mm) for a mating pair to count as "in contact". Tight by
// design: a real seated mate reads a few hundredths of a mm; beyond this it is
// floating apart or crashing in.
const DEFAULT_MATING_TOLERANCE_MM = 0.2
// How far apart (mm) two surfaces may be and still be considered a candidate
// mating pair to evaluate. Bounds the broad phase and the exact distance search,
// so a declared mate separated by more than this reads "floating (> window)".
const MATING_SEARCH_MM = 5.0

// ---------------------------------------------------------------------------
// Assembleability helpers (per-instance, HEURISTIC)
// ---------------------------------------------------------------------------

// Principal (long) axis of an instance in WORLD space, plus the shaft radius
// (max half-extent perpendicular to that axis) and the world end-points of the
// axis through the local AABB centre. Used to model a fastener as a shaft.
const principalAxisWorld = (instance: InstanceGeometry) => {
  const box = instance.mesh.localBox
  const size = new THREE.Vector3()
  box.getSize(size)
  const center = new THREE.Vector3()
  box.getCenter(center)
  const dims = [size.x, size.y, size.z]
  let axis = 0
  if (dims[1] > dims[axis]) axis = 1
  if (dims[2] > dims[axis]) axis = 2
  const half = dims[axis] / 2
  const radius = Math.max(...dims.filter((_, i) => i !== axis)) / 2

  const localDir = new THREE.Vector3(axis === 0 ? 1 : 0, axis === 1 ? 1 : 0, axis === 2 ? 1 : 0)
  const localLo = center.clone().addScaledVector(localDir, -half)
  const localHi = center.clone().addScaledVector(localDir, half)
  const worldLo = localLo.applyMatrix4(instance.matrix)
  const worldHi = localHi.applyMatrix4(instance.matrix)
  // Scale radius by the instance transform (assume ~uniform scale).
  const scale = new THREE.Vector3()
  instance.matrix.decompose(new THREE.Vector3(), new THREE.Quaternion(), scale)
  const worldRadius = radius * Math.max(scale.x, scale.y, scale.z)
  const lengthMm = worldLo.distanceTo(worldHi)
  const dir = worldHi.clone().sub(worldLo).normalize()
  return { worldLo, worldHi, dir, lengthMm, worldRadius }
}

// HEURISTIC fastener engagement: walk axial stations along the shaft; at each,
// probe a ring just OUTSIDE the shaft surface and mark the station "engaged" if
// any probe point lies inside a host (non-fastener) part. Engaged length =
// engaged-station fraction × shaft length. Captures "shaft surrounded by host
// material" (i.e. threaded/gripped) and reads ~0 for a screw poking into air.
const estimateEngagement = (
  fastener: InstanceGeometry,
  hosts: InstanceGeometry[],
): {
  axial: boolean
  engagementMm: number
  shaftLengthMm: number
  hostInstanceIds: string[]
  point: THREE.Vector3 | null
} => {
  const { worldLo, dir, lengthMm, worldRadius } = principalAxisWorld(fastener)
  // Only elongated parts (screws/bolts/inserts/standoffs) have a meaningful
  // "thread engagement"; thin disks (washers) / squat nuts are not axial, so we
  // skip them to avoid flooding the report with nonsense grip estimates.
  const axial = lengthMm > Math.max(worldRadius * 2.4, 1.5)
  if (!axial || lengthMm <= 1e-3)
    return { axial: false, engagementMm: 0, shaftLengthMm: lengthMm, hostInstanceIds: [], point: null }

  // Two perpendicular vectors spanning the ring plane.
  const up = Math.abs(dir.z) < 0.9 ? new THREE.Vector3(0, 0, 1) : new THREE.Vector3(1, 0, 0)
  const u = new THREE.Vector3().crossVectors(dir, up).normalize()
  const v = new THREE.Vector3().crossVectors(dir, u).normalize()
  const ringR = Math.max(worldRadius * THREAD_RING_SCALE, 0.5)

  // Candidate hosts: AABBs (expanded by ring radius) that overlap the fastener.
  const pad = ringR + 0.5
  const candidates = hosts.filter(
    (host) =>
      host.worldMin[0] - pad <= fastener.worldMax[0] &&
      host.worldMax[0] + pad >= fastener.worldMin[0] &&
      host.worldMin[1] - pad <= fastener.worldMax[1] &&
      host.worldMax[1] + pad >= fastener.worldMin[1] &&
      host.worldMin[2] - pad <= fastener.worldMax[2] &&
      host.worldMax[2] + pad >= fastener.worldMin[2],
  )
  if (candidates.length === 0)
    return { axial: true, engagementMm: 0, shaftLengthMm: lengthMm, hostInstanceIds: [], point: null }

  const station = new THREE.Vector3()
  const ringPoint = new THREE.Vector3()
  const local = new THREE.Vector3()
  const engagedHosts = new Set<string>()
  let engagedStations = 0
  let firstEngagedPoint: THREE.Vector3 | null = null

  for (let s = 0; s < THREAD_STATIONS; s += 1) {
    const tAxial = (lengthMm * s) / (THREAD_STATIONS - 1)
    station.copy(worldLo).addScaledVector(dir, tAxial)
    let stationEngaged = false
    for (let p = 0; p < THREAD_RING_PROBES && !stationEngaged; p += 1) {
      const angle = (Math.PI * 2 * p) / THREAD_RING_PROBES
      ringPoint
        .copy(station)
        .addScaledVector(u, Math.cos(angle) * ringR)
        .addScaledVector(v, Math.sin(angle) * ringR)
      for (const host of candidates) {
        local.copy(ringPoint).applyMatrix4(host.inverse)
        if (pointInside(host.mesh.bvh, local)) {
          stationEngaged = true
          engagedHosts.add(host.instanceId)
          if (!firstEngagedPoint) firstEngagedPoint = station.clone()
          break
        }
      }
    }
    if (stationEngaged) engagedStations += 1
  }

  const engagementMm = (lengthMm * engagedStations) / THREAD_STATIONS
  return {
    axial: true,
    engagementMm,
    shaftLengthMm: lengthMm,
    hostInstanceIds: [...engagedHosts],
    point: firstEngagedPoint,
  }
}

// COARSE assembly-access feasibility. For each candidate direction, AABB-shadow
// sweep the part to "infinity": any OTHER present part whose AABB overlaps the
// moving part's cross-section (the two axes perpendicular to the sweep) AND lies
// ahead of it along the sweep axis blocks that direction. A part is flagged when
// EVERY candidate direction is blocked (no straight-line install/removal). This
// overestimates blockage (it ignores shape), so it is a WARN-level heuristic.
const ACCESS_AXES: Array<[number, number]> = [
  [0, 1],
  [0, -1],
  [1, 1],
  [1, -1],
  [2, 1],
  [2, -1],
]

// Perpendicular overlap (mm) a blocker must exceed on BOTH cross-section axes to
// count: filters mere touching mates / coincident faces (which share a face but
// don't actually obstruct a straight pull) from flagging every neighbour.
const ACCESS_TOUCH_MM = 0.5

const corridorOverlaps = (part: InstanceGeometry, other: InstanceGeometry, perp: number[]) => {
  for (const a of perp) {
    const overlap =
      Math.min(part.worldMax[a], other.worldMax[a]) - Math.max(part.worldMin[a], other.worldMin[a])
    if (overlap <= ACCESS_TOUCH_MM) return false
  }
  return true
}

const accessClearDirections = (part: InstanceGeometry, others: InstanceGeometry[], center: Vec3Tuple) => {
  let clear = 0
  // ±X/±Y/±Z axis sweeps.
  for (const [axis, sign] of ACCESS_AXES) {
    const perp = [0, 1, 2].filter((a) => a !== axis)
    const blocked = others.some((other) => {
      // Must substantially overlap the shadow corridor's cross-section.
      if (!corridorOverlaps(part, other, perp)) return false
      // Must lie ahead of the part along the sweep direction.
      return sign > 0 ? other.worldMax[axis] > part.worldMax[axis] : other.worldMin[axis] < part.worldMin[axis]
    })
    if (!blocked) clear += 1
  }
  // Radial-out from the scene centre (often the natural extraction direction).
  const cx = (part.worldMin[0] + part.worldMax[0]) / 2 - center[0]
  const cy = (part.worldMin[1] + part.worldMax[1]) / 2 - center[1]
  const cz = (part.worldMin[2] + part.worldMax[2]) / 2 - center[2]
  const rlen = Math.hypot(cx, cy, cz)
  let radialTried = 0
  if (rlen > 1e-3) {
    radialTried = 1
    const rdir = [cx / rlen, cy / rlen, cz / rlen]
    const blocked = others.some((other) => {
      // Project both AABB centres along rdir; "ahead" if the other is farther out.
      const po = (part.worldMin[0] + part.worldMax[0]) / 2 * rdir[0] +
        (part.worldMin[1] + part.worldMax[1]) / 2 * rdir[1] +
        (part.worldMin[2] + part.worldMax[2]) / 2 * rdir[2]
      const oo = (other.worldMin[0] + other.worldMax[0]) / 2 * rdir[0] +
        (other.worldMin[1] + other.worldMax[1]) / 2 * rdir[1] +
        (other.worldMin[2] + other.worldMax[2]) / 2 * rdir[2]
      if (oo <= po) return false
      // Crude corridor test: AABBs overlap on the two axes least aligned with rdir.
      const absdir = rdir.map(Math.abs)
      const sweepAxis = absdir.indexOf(Math.max(...absdir))
      const perp = [0, 1, 2].filter((a) => a !== sweepAxis)
      return corridorOverlaps(part, other, perp)
    })
    if (!blocked) clear += 1
  }
  return { clear, tried: ACCESS_AXES.length + radialTried }
}

type Vec3Tuple = [number, number, number]

// ---------------------------------------------------------------------------
// Mating-face contact helpers (per instance pair, ROBUST surface metric)
// ---------------------------------------------------------------------------

const partTypePairKey = (a: string, b: string) => (a <= b ? `${a}\u0000${b}` : `${b}\u0000${a}`)

// Exact contact metric for a candidate mating pair: if the surfaces intersect,
// report the interior penetration depth (and localized overlap anchors); else
// report the surface gap. Bounded by MATING_SEARCH_MM so a far-apart pair reads
// gap = MATING_SEARCH_MM rather than paying for an unbounded distance search.
const matingMetric = (
  a: InstanceGeometry,
  b: InstanceGeometry,
  searchMm: number,
): { gapMm: number; penetrationMm: number; point: Vec3Tuple | null; region: PenetrationResult['region'] } => {
  const dist = surfaceDistance(a, b, searchMm)
  if (dist <= INTERSECTION_EPSILON) {
    const pen = penetrationDepth(a, b)
    return { gapMm: 0, penetrationMm: pen.depthMm, point: pen.point, region: pen.region }
  }
  // Separated: anchor a marker at the midpoint between the two AABB centres so
  // a floating mate still points somewhere sensible in the viewer.
  const mid: Vec3Tuple = [
    (a.worldMin[0] + a.worldMax[0] + b.worldMin[0] + b.worldMax[0]) / 4,
    (a.worldMin[1] + a.worldMax[1] + b.worldMin[1] + b.worldMax[1]) / 4,
    (a.worldMin[2] + a.worldMax[2] + b.worldMin[2] + b.worldMax[2]) / 4,
  ]
  return { gapMm: Number.isFinite(dist) ? dist : searchMm, penetrationMm: 0, point: mid, region: null }
}

// ---------------------------------------------------------------------------
// Cable/harness wiring helper (per route). The path is resolved (world +
// instance-anchored waypoints) and sampled with the shared Catmull-Rom from
// core/buildWiring, then measured for: length, pass-through obstruction (ray
// per sampled segment), tightest bend radius, longest span between anchors,
// and closest approach to non-termination solids. Rigid transforms are
// assumed (local distances == world mm), matching the rest of the engine.
// ---------------------------------------------------------------------------

const evaluateRoute = (
  manifest: BuildSceneManifest,
  route: Route,
  instances: InstanceGeometry[],
  opts: { wireClearanceMm: number; maxUnsupportedMm: number },
): RoutingReach => {
  const resolved = resolveRoute(manifest, route)
  const sampled = sampleRoute(resolved.points)
  const points = sampled.samples.map((p) => new THREE.Vector3(p[0], p[1], p[2]))
  const ownInstances = new Set(resolved.instances)
  const candidates = instances.filter((instance) => !ownInstances.has(instance.instanceId))
  const wireRadius = (route.diameterMm ?? 0) / 2

  const lengthMm = polylineLength(sampled.samples)
  const blocking = new Set<string>()
  let firstBlock: Vec3Tuple | null = null
  const localOrigin = new THREE.Vector3()
  const localDir = new THREE.Vector3()
  const dirWorld = new THREE.Vector3()
  const worldHit = new THREE.Vector3()

  // Obstruction: cast each sampled segment against every candidate BVH.
  for (let i = 0; i < points.length - 1; i += 1) {
    const p0 = points[i]
    const p1 = points[i + 1]
    dirWorld.copy(p1).sub(p0)
    const segLen = dirWorld.length()
    if (segLen <= 1e-6) continue
    dirWorld.multiplyScalar(1 / segLen)
    for (const instance of candidates) {
      localOrigin.copy(p0).applyMatrix4(instance.inverse)
      localDir.copy(dirWorld).transformDirection(instance.inverse)
      const ray = new THREE.Ray(localOrigin, localDir)
      const hit = instance.mesh.bvh.raycastFirst(ray, THREE.DoubleSide)
      if (hit && hit.distance > 1e-3 && hit.distance <= segLen) {
        blocking.add(instance.instanceId)
        if (!firstBlock) {
          worldHit.copy(hit.point).applyMatrix4(instance.matrix)
          firstBlock = [worldHit.x, worldHit.y, worldHit.z]
        }
      }
    }
  }

  // Clearance: closest wire-SURFACE approach (sample distance minus the wire
  // radius) to any candidate solid, tracked only below the warn threshold.
  // World-AABB prefilter keeps this cheap for the common all-clear case.
  const clearanceThreshold = opts.wireClearanceMm
  let clearance: { gapMm: number; instanceId: string; point: Vec3Tuple } | null = null
  const samplePoint = new THREE.Vector3()
  for (const instance of candidates) {
    if (blocking.has(instance.instanceId)) continue
    for (let i = 0; i < points.length; i += 1) {
      const aabbGap = pointAabbDistance(instance, points[i])
      if (aabbGap - wireRadius > clearanceThreshold) continue
      samplePoint.copy(points[i]).applyMatrix4(instance.inverse)
      const hit = instance.mesh.bvh.closestPointToPoint(
        samplePoint,
        tmpHit,
        0,
        clearanceThreshold + wireRadius + 1e-3,
      )
      if (!hit) continue
      const gap = hit.distance - wireRadius
      if (gap <= clearanceThreshold && (!clearance || gap < clearance.gapMm)) {
        clearance = {
          gapMm: Math.max(gap, 0),
          instanceId: instance.instanceId,
          point: [points[i].x, points[i].y, points[i].z],
        }
      }
    }
  }

  // Bend radius + support spans on the shared sampled curve.
  const bend = minBendRadius(sampled.samples)
  const spans = unsupportedSpans(resolved.anchors, sampled)
  const worstSpan = spans.reduce<(typeof spans)[number] | null>(
    (worst, span) => (worst === null || span.lengthMm > worst.lengthMm ? span : worst),
    null,
  )
  const anchorCount = resolved.anchors.filter(Boolean).length

  let anchor = firstBlock
  if (!anchor && points.length > 0) {
    const mid = points[Math.floor(points.length / 2)]
    anchor = [mid.x, mid.y, mid.z]
  }
  return {
    routeId: route.id,
    label: route.label ?? route.id,
    lengthMm: round3(lengthMm),
    maxLengthMm: route.maxLengthMm ?? null,
    blockingInstanceIds: [...blocking],
    point: anchor ? (anchor.map(round3) as Vec3Tuple) : null,
    diameterMm: route.diameterMm ?? null,
    anchorCount,
    minBendRadiusMm: bend ? round3(bend.radiusMm) : null,
    minBendRadiusAllowedMm: effectiveMinBendRadiusMm(route),
    bendPoint: bend ? (bend.point.map(round3) as Vec3Tuple) : null,
    maxUnsupportedMm: worstSpan ? round3(worstSpan.lengthMm) : null,
    maxUnsupportedAllowedMm: route.maxUnsupportedMm ?? opts.maxUnsupportedMm,
    spanPoint: worstSpan ? (worstSpan.midpoint.map(round3) as Vec3Tuple) : null,
    clearanceMm: clearance ? round3(clearance.gapMm) : null,
    clearanceInstanceId: clearance?.instanceId ?? null,
    clearancePoint: clearance ? (clearance.point.map(round3) as Vec3Tuple) : null,
    missingInstances: resolved.missingInstances,
  }
}

// ---------------------------------------------------------------------------
// Swept-pose / motion validation (Phase 3). Re-evaluates interference across a
// set of posed configurations and reports the WORST-CASE envelope per instance
// pair. Geometry is loaded + BVH'd ONCE; each pose only changes the rigid query
// transforms (matrix/inverse/world AABB) — BVHs are never rebuilt — so the cost
// is (Phase-2 overlap cost) × (#samples). The caller (buildvizKinematics) bakes
// the forward kinematics into per-sample instance transform overrides, keeping
// this engine kinematics-agnostic. See plans/validation.md (motion).
// ---------------------------------------------------------------------------

export type SweepSampleInput = {
  id: string
  label: string
  /** instanceId → column-major 16 world override; missing = use base transform. */
  overrides: Record<string, number[]>
}

export type SweptPair = {
  a: { instanceId: string; partType: string; name: string }
  b: { instanceId: string; partType: string; name: string }
  /** 'overlap' when the pair interpenetrates at some sample; otherwise 'clearance'. */
  kind: 'overlap' | 'clearance'
  /** Worst (max) interior penetration over the whole sweep, mm. 0 for clearance. */
  maxPenetrationMm: number
  /** Closest surface approach over the whole sweep, mm (null when never tracked). */
  minClearanceMm: number | null
  /** Sample id/label at which the worst case occurred. */
  worstSampleId: string
  worstLabel: string
  /** Localized overlap anchors at the worst sample (for in-place shading). */
  point: [number, number, number] | null
  region: { min: [number, number, number]; max: [number, number, number] } | null
  /** True when the worst-case overlap is an allowed interference (typed
   *  allowedInterferences entry within its cap, or the legacy blanket between
   *  parts with no relative motion). Same semantics as CheckCollision.allowed. */
  allowed?: boolean
  /** Allowance decision detail (source / kind / reason / refusal). */
  allowance?: OverlapAllowance
}

export type SweepReport = {
  sampleCount: number
  instanceCount: number
  meshCount: number
  missingMeshes: string[]
  fastenersExcluded: number
  worstPenetrationMm: number
  capped: boolean
  pairs: SweptPair[]
  timings: { loadMs: number; bvhMs: number; sweepMs: number; totalMs: number }
}

export type SweepOptions = {
  toleranceMm?: number
  minPenetrationMm?: number
  /** Track closest approach below this air-gap (mm) as a swept clearance. 0 = off. */
  clearanceMm?: number
  maxPairs?: number
  includeFasteners?: boolean
  loadMesh: (mesh: BuildMesh) => Promise<ArrayBuffer | null>
}

const sweptPairKey = (a: string, b: string) => (a <= b ? `${a}\u0000${b}` : `${b}\u0000${a}`)

export const sweepOverlaps = async (
  manifest: BuildSceneManifest,
  samples: SweepSampleInput[],
  options: SweepOptions,
): Promise<SweepReport> => {
  const toleranceMm = options.toleranceMm ?? DEFAULT_TOLERANCE_MM
  const minPenetrationMm = options.minPenetrationMm ?? DEFAULT_MIN_PENETRATION_MM
  const clearanceMm = options.clearanceMm ?? 0
  const maxPairs = options.maxPairs ?? DEFAULT_MAX_PAIRS
  const includeFasteners = options.includeFasteners ?? false
  const startedAt = performance.now()

  const fastenerMeshIds = new Set(
    manifest.meshes.filter((mesh) => isFastenerMesh(mesh)).map((mesh) => mesh.id),
  )

  // Load + BVH every unique mesh once, reused across all instances AND poses.
  const loadStart = performance.now()
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
  const loadMs = performance.now() - loadStart

  const bvhStart = performance.now()
  for (const mesh of meshById.values()) {
    mesh.geometry.boundsTree = mesh.bvh
  }

  // Fasteners overlap their holes by design, so they are excluded by default
  // (they would also dominate the sweep cost). Base matrices are kept so each
  // pose can re-derive the world AABB from a pose override or the static base.
  let fastenersExcluded = 0
  const instances: InstanceGeometry[] = []
  const baseMatrices: THREE.Matrix4[] = []
  manifest.instances.forEach((instance, index) => {
    const mesh = meshById.get(instance.meshId)
    if (!mesh) return
    if (!includeFasteners && fastenerMeshIds.has(instance.meshId)) {
      fastenersExcluded += 1
      return
    }
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
      isFastener: false,
    })
    baseMatrices.push(matrix.clone())
  })
  const bvhMs = performance.now() - bvhStart

  const instanceBySlot = instances.map((instance) => instance.instanceId)
  const surfaceThreshold = Math.max(toleranceMm, clearanceMm)

  // World-AABB intersection depth (min overlap extent across axes), 0 when the
  // boxes are disjoint. A near-free proxy used to RANK poses during the sweep so
  // the expensive interior-grid penetration runs only once per pair, at its
  // worst pose (recomputed precisely in the final pass below). The proxy upper-
  // bounds the true penetration, so it never misses an interference.
  const aabbOverlapDepth = (a: InstanceGeometry, b: InstanceGeometry) => {
    let minOverlap = Infinity
    for (let axis = 0; axis < 3; axis += 1) {
      const overlap =
        Math.min(a.worldMax[axis], b.worldMax[axis]) - Math.max(a.worldMin[axis], b.worldMin[axis])
      if (overlap <= 0) return 0
      if (overlap < minOverlap) minOverlap = overlap
    }
    return minOverlap === Infinity ? 0 : minOverlap
  }

  const reposeInstances = (sample: SweepSampleInput) => {
    instances.forEach((instance, slot) => {
      const override = sample.overrides[instanceBySlot[slot]]
      if (override && override.length === 16) {
        instance.matrix.fromArray(override)
      } else {
        instance.matrix.copy(baseMatrices[slot])
      }
      instance.inverse.copy(instance.matrix).invert()
      const { min, max } = worldAabb(instance.mesh.localBox, instance.matrix)
      instance.worldMin = min
      instance.worldMax = max
    })
  }

  type Acc = {
    a: InstanceGeometry
    b: InstanceGeometry
    /** Max world-AABB overlap depth seen (overlap candidate ranking). */
    maxOverlapProxy: number
    overlapSample: SweepSampleInput | null
    /** Min world-AABB gap seen (clearance candidate ranking). */
    minGapProxy: number
    gapSample: SweepSampleInput | null
  }
  const accByPair = new Map<string, Acc>()
  let capped = false

  // The sweep loop does NO BVH work: it only updates rigid transforms + world
  // AABBs and tracks, per pair, the pose with the deepest AABB overlap (an upper
  // bound on true penetration) and the pose with the smallest AABB gap. All
  // exact distance/penetration queries are deferred to ONE precise pass per
  // candidate pair below, so cost ≈ #candidate pairs rather than #samples ×
  // BVH-vs-BVH queries — the difference between sub-second and a minute here.
  const sweepStart = performance.now()
  for (const sample of samples) {
    reposeInstances(sample)
    const moved = new Set(Object.keys(sample.overrides))
    const isHome = moved.size === 0

    const { pairs, capped: sampleCapped } = broadPhasePairs(instances, surfaceThreshold, maxPairs)
    if (sampleCapped) capped = true

    for (const [a, b] of pairs) {
      if (!isHome && !moved.has(a.instanceId) && !moved.has(b.instanceId)) continue
      const key = sweptPairKey(a.instanceId, b.instanceId)
      let acc = accByPair.get(key)
      if (!acc) {
        acc = {
          a,
          b,
          maxOverlapProxy: -Infinity,
          overlapSample: null,
          minGapProxy: Infinity,
          gapSample: null,
        }
        accByPair.set(key, acc)
      }
      const overlap = aabbOverlapDepth(a, b)
      if (overlap > 0) {
        if (overlap > acc.maxOverlapProxy) {
          acc.maxOverlapProxy = overlap
          acc.overlapSample = sample
        }
      } else {
        const gap = aabbDistance(a, b)
        if (gap < acc.minGapProxy) {
          acc.minGapProxy = gap
          acc.gapSample = sample
        }
      }
    }
  }
  const sweepMs = performance.now() - sweepStart

  // Precise pass: confirm each candidate ONCE at its worst pose. Overlap
  // candidates (AABBs overlapped) get the exact interior-grid penetration +
  // localized region; remaining candidates whose AABB gap fell within the
  // clearance window get an exact surface-distance closest approach.
  const allowanceConfig = manifest.checksConfig
  const motionGroups = jointMotionGroups(manifest.joints)
  const round3 = (v: number) => Math.round(v * 1000) / 1000
  const pairsOut: SweptPair[] = []
  let worstPenetrationMm = 0
  for (const acc of accByPair.values()) {
    let recordedOverlap = false
    if (acc.overlapSample) {
      reposeInstances(acc.overlapSample)
      const distance = surfaceDistance(acc.a, acc.b, surfaceThreshold)
      if (distance <= INTERSECTION_EPSILON) {
        const penetration = penetrationDepth(acc.a, acc.b)
        if (penetration.depthMm >= minPenetrationMm) {
          if (penetration.depthMm > worstPenetrationMm) worstPenetrationMm = penetration.depthMm
          // Same allowance semantics as the static check, evaluated at the
          // worst pose. A pair swept through its motion range is by definition
          // in relative motion, so a legacy partType ignore only survives here
          // for pairs the joints do not move against each other.
          const allowance = resolveOverlapAllowance(
            allowanceConfig,
            acc.a,
            acc.b,
            penetration.depthMm,
            motionGroups,
          )
          pairsOut.push({
            a: { instanceId: acc.a.instanceId, partType: acc.a.partType, name: acc.a.name },
            b: { instanceId: acc.b.instanceId, partType: acc.b.partType, name: acc.b.name },
            kind: 'overlap',
            maxPenetrationMm: round3(penetration.depthMm),
            minClearanceMm: null,
            worstSampleId: acc.overlapSample.id,
            worstLabel: acc.overlapSample.label,
            point: penetration.point ? (penetration.point.map(round3) as [number, number, number]) : null,
            region: penetration.region
              ? {
                  min: penetration.region.min.map(round3) as [number, number, number],
                  max: penetration.region.max.map(round3) as [number, number, number],
                }
              : null,
            ...(allowance.allowed ? { allowed: true } : {}),
            ...(allowance.source !== null ? { allowance } : {}),
          })
          recordedOverlap = true
        }
      }
    }
    if (recordedOverlap) continue
    // Clearance: only when a window is configured and the AABB gap implies the
    // surfaces could be within it (AABB gap ≤ true surface gap).
    if (clearanceMm > 0 && acc.gapSample && acc.minGapProxy <= clearanceMm) {
      reposeInstances(acc.gapSample)
      const distance = surfaceDistance(acc.a, acc.b, clearanceMm)
      if (distance > INTERSECTION_EPSILON && distance <= clearanceMm) {
        pairsOut.push({
          a: { instanceId: acc.a.instanceId, partType: acc.a.partType, name: acc.a.name },
          b: { instanceId: acc.b.instanceId, partType: acc.b.partType, name: acc.b.name },
          kind: 'clearance',
          maxPenetrationMm: 0,
          minClearanceMm: round3(distance),
          worstSampleId: acc.gapSample.id,
          worstLabel: acc.gapSample.label,
          point: null,
          region: null,
        })
      }
    }
  }
  pairsOut.sort((a, b) => b.maxPenetrationMm - a.maxPenetrationMm)

  return {
    sampleCount: samples.length,
    instanceCount: instances.length,
    meshCount: meshById.size,
    missingMeshes,
    fastenersExcluded,
    worstPenetrationMm: round3(worstPenetrationMm),
    capped,
    pairs: pairsOut,
    timings: {
      loadMs: Math.round(loadMs),
      bvhMs: Math.round(bvhMs),
      sweepMs: Math.round(sweepMs),
      totalMs: Math.round(performance.now() - startedAt),
    },
  }
}

export const checkAssembly = async (
  manifest: BuildSceneManifest,
  options: CheckOptions,
): Promise<CheckReport> => {
  const toleranceMm = options.toleranceMm ?? DEFAULT_TOLERANCE_MM
  const minPenetrationMm = options.minPenetrationMm ?? DEFAULT_MIN_PENETRATION_MM
  const maxPairs = options.maxPairs ?? DEFAULT_MAX_PAIRS
  const gapWindowMm = options.gapWindowMm ?? DEFAULT_GAP_WINDOW_MM
  const includeFasteners = options.includeFasteners ?? false
  const checkWatertight = options.checkWatertight ?? false
  const checkWallThickness = options.checkWallThickness ?? false
  const checkSelfIntersection = options.checkSelfIntersection ?? false
  const checkComponents = options.checkComponents ?? false
  const expectedMeshComponents = options.expectedMeshComponents ?? {}
  const maxMeshComponents = options.maxMeshComponents ?? 1
  const checkThreadEngagement = options.checkThreadEngagement ?? false
  const checkAssemblyAccess = options.checkAssemblyAccess ?? false
  const checkMatingContact = options.checkMatingContact ?? false
  const minWallMm = options.minWallMm ?? DEFAULT_MIN_WALL_MM
  const minThreadEngagementMm = options.minThreadEngagementMm ?? DEFAULT_MIN_THREAD_ENGAGEMENT_MM
  const matingToleranceMm = options.matingToleranceMm ?? DEFAULT_MATING_TOLERANCE_MM
  const matingPairs = options.matingPairs ?? []
  const routes = options.routes ?? []
  const wallSamples = options.wallSamples ?? DEFAULT_WALL_SAMPLES
  const startedAt = performance.now()

  // Classify fastener meshes up front so their instances can be suppressed.
  const fastenerMeshIds = new Set(
    manifest.meshes.filter((mesh) => isFastenerMesh(mesh)).map((mesh) => mesh.id),
  )

  // Load + BVH every unique mesh once, reused across all instances. Fastener
  // meshes are still loaded (cheaply) so suppressed fasteners can act as
  // connectivity bridges between the parts they join.
  const loadStart = performance.now()
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
  const loadMs = performance.now() - loadStart

  const bvhStart = performance.now()
  for (const mesh of meshById.values()) {
    // closestPointToGeometry uses the other geometry's boundsTree for speed.
    mesh.geometry.boundsTree = mesh.bvh
  }
  let fastenersExcluded = 0
  const instances: InstanceGeometry[] = []
  manifest.instances.forEach((instance, index) => {
    const mesh = meshById.get(instance.meshId)
    if (!mesh) return
    const isFastener = !includeFasteners && fastenerMeshIds.has(instance.meshId)
    if (isFastener) fastenersExcluded += 1
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
  const bvhMs = performance.now() - bvhStart

  const broadStart = performance.now()
  const { pairs, capped } = broadPhasePairs(instances, toleranceMm, maxPairs)
  const broadMs = performance.now() - broadStart

  // Allowance intent (typed allowedInterferences + legacy ignoreOverlapPairs)
  // and the joints-derived motion groups the legacy blanket is gated on.
  const allowanceConfig = manifest.checksConfig
  const motionGroups = jointMotionGroups(manifest.joints)

  const narrowStart = performance.now()
  const unionFind = new UnionFind(instances.length)
  const collisions: CheckCollision[] = []
  for (const [a, b] of pairs) {
    // Suppressed fasteners are never checked for interference (they overlap
    // their holes by design); instead a fastener spanning two parts bridges
    // them for connectivity, so the parts it joins are not flagged as floating.
    if (a.isFastener || b.isFastener) {
      unionFind.union(a.index, b.index)
      continue
    }
    const distance = surfaceDistance(a, b, toleranceMm)
    if (distance > toleranceMm) continue
    if (distance > INTERSECTION_EPSILON) {
      // Within tolerance => the two parts are in contact: connect them.
      unionFind.union(a.index, b.index)
      continue
    }
    // They actually intersect: measure interior penetration and localize the
    // overlap region so the viewer can shade just the interpenetrating volume.
    const penetration = penetrationDepth(a, b)
    if (penetration.depthMm < minPenetrationMm) {
      // Shallow (mate-grade) contact: connected, not a reportable collision.
      unionFind.union(a.index, b.index)
      continue
    }
    const allowance = resolveOverlapAllowance(allowanceConfig, a, b, penetration.depthMm, motionGroups)
    // Only an ALLOWED interference joins parts. An unexpected deep overlap is a
    // modeling error, not an attachment — two links do not "connect" by crashing
    // into each other — so it must not bridge connectivity (a real joint needs a
    // fastener/pin/bearing or a declared interference). This also means a bad
    // overlap can no longer mask a floating part.
    if (allowance.allowed) unionFind.union(a.index, b.index)
    const round3 = (v: number) => Math.round(v * 1000) / 1000
    collisions.push({
      a: { instanceId: a.instanceId, partType: a.partType, name: a.name },
      b: { instanceId: b.instanceId, partType: b.partType, name: b.name },
      penetrationMm: round3(penetration.depthMm),
      point: penetration.point
        ? [round3(penetration.point[0]), round3(penetration.point[1]), round3(penetration.point[2])]
        : null,
      region: penetration.region
        ? {
            min: penetration.region.min.map(round3) as [number, number, number],
            max: penetration.region.max.map(round3) as [number, number, number],
          }
        : null,
      ...(allowance.allowed ? { allowed: true } : {}),
      ...(allowance.source !== null ? { allowance } : {}),
    })
  }
  const narrowMs = performance.now() - narrowStart

  const connectivityStart = performance.now()
  const componentRoots = new Map<number, number[]>()
  instances.forEach((instance) => {
    const root = unionFind.find(instance.index)
    const members = componentRoots.get(root) ?? []
    members.push(instance.index)
    componentRoots.set(root, members)
  })
  const components = [...componentRoots.values()]
  const indexToInstance = new Map(instances.map((instance) => [instance.index, instance]))

  let mainRoot = -1
  let mainSize = -1
  componentRoots.forEach((members, root) => {
    if (members.length > mainSize) {
      mainSize = members.length
      mainRoot = root
    }
  })
  const mainInstances = (componentRoots.get(mainRoot) ?? [])
    .map((index) => indexToInstance.get(index))
    .filter((value): value is InstanceGeometry => value !== undefined)

  // Suppressed fasteners are bridges, not reportable parts, so they never count
  // as floating themselves.
  const floatingInstances = instances.filter(
    (instance) => !instance.isFastener && unionFind.find(instance.index) !== mainRoot,
  )

  // Optional gap enrichment: for each floating part, find its closest approach
  // to the main assembly. Cheap broad AABB pre-filter, then exact distance only
  // on the nearest main-assembly candidates. Skipped if the floating set is huge.
  const floating: CheckFloating[] = []
  const gaps: CheckGap[] = []
  const computeGaps = floatingInstances.length > 0 && floatingInstances.length <= MAX_GAP_INSTANCES
  for (const instance of floatingInstances) {
    let nearestGapMm: number | null = null
    let nearestInstanceId: string | null = null
    if (computeGaps && mainInstances.length > 0) {
      const ranked = mainInstances
        .map((main) => ({ main, aabb: aabbDistance(instance, main) }))
        .sort((x, y) => x.aabb - y.aabb)
        .slice(0, 6)
      let best = Infinity
      let bestId: string | null = null
      for (const { main, aabb } of ranked) {
        if (aabb > best) break
        const distance = surfaceDistance(instance, main, Math.min(best, gapWindowMm * 4))
        if (distance < best) {
          best = distance
          bestId = main.instanceId
        }
      }
      if (Number.isFinite(best)) {
        nearestGapMm = Math.round(best * 1000) / 1000
        nearestInstanceId = bestId
      }
    }
    floating.push({
      instanceId: instance.instanceId,
      partType: instance.partType,
      name: instance.name,
      componentId: unionFind.find(instance.index),
      componentSize: (componentRoots.get(unionFind.find(instance.index)) ?? []).length,
      nearestGapMm,
      nearestInstanceId,
    })
    if (nearestGapMm !== null && nearestInstanceId && nearestGapMm <= gapWindowMm) {
      gaps.push({
        instanceId: instance.instanceId,
        partType: instance.partType,
        name: instance.name,
        gapMm: nearestGapMm,
        nearestInstanceId,
      })
    }
  }
  const connectivityMs = performance.now() - connectivityStart

  // --- Printability: per UNIQUE non-fastener mesh, reusing its cached BVH. ---
  const printabilityStart = performance.now()
  const printability: MeshPrintability[] = []
  if (checkWatertight || checkWallThickness || checkSelfIntersection || checkComponents) {
    for (const mesh of manifest.meshes) {
      if (fastenerMeshIds.has(mesh.id)) continue // hardware is not printed
      const geom = meshById.get(mesh.id)
      if (!geom) continue
      const refs = manifest.instances.filter((instance) => instance.meshId === mesh.id)
      if (refs.length === 0) continue
      const repr = instances.find((instance) => instance.instanceId === refs[0].id)

      // analyzeTopology powers both watertight and components; run it when either
      // is requested, but only surface the fields the caller asked for.
      const needTopo = checkWatertight || checkComponents
      const topo = needTopo
        ? analyzeTopology(geom, checkComponents)
        : {
            openEdges: null,
            nonManifoldEdges: null,
            inconsistentWinding: false,
            degenerateTriangles: null,
            volumeMm3: null,
            componentCount: null,
            smallestComponent: null,
          }
      let minWall: number | null = null
      let thinPoint: [number, number, number] | null = null
      if (checkWallThickness) {
        const wall = estimateMinWall(geom, wallSamples)
        minWall = wall.minWallMm === null ? null : Math.round(wall.minWallMm * 1000) / 1000
        if (wall.localPoint && repr) {
          const world = wall.localPoint.clone().applyMatrix4(repr.matrix)
          thinPoint = [world.x, world.y, world.z]
        }
      }
      let selfIntersections: number | null = null
      let selfIntersectionPoint: [number, number, number] | null = null
      if (checkSelfIntersection) {
        const selfHit = detectSelfIntersections(geom)
        selfIntersections = selfHit.count
        if (selfHit.localPoint && repr) {
          const world = selfHit.localPoint.clone().applyMatrix4(repr.matrix)
          selfIntersectionPoint = [world.x, world.y, world.z]
        }
      }
      let smallestComponent: MeshPrintability['smallestComponent'] = null
      if (checkComponents && topo.smallestComponent) {
        let point: [number, number, number] | null = null
        if (topo.smallestComponent.localPoint && repr) {
          const world = topo.smallestComponent.localPoint.clone().applyMatrix4(repr.matrix)
          point = [
            Math.round(world.x * 1000) / 1000,
            Math.round(world.y * 1000) / 1000,
            Math.round(world.z * 1000) / 1000,
          ]
        }
        smallestComponent = {
          triangleCount: topo.smallestComponent.triangleCount,
          volumeMm3: Math.round(topo.smallestComponent.volumeMm3 * 1000) / 1000,
          point,
        }
      }
      printability.push({
        meshId: mesh.id,
        meshName: mesh.name,
        instanceIds: refs.map((ref) => ref.id),
        triangleCount: geom.triangleCount,
        openEdges: checkWatertight ? topo.openEdges : null,
        nonManifoldEdges: checkWatertight ? topo.nonManifoldEdges : null,
        inconsistentWinding: checkWatertight ? topo.inconsistentWinding : false,
        degenerateTriangles: checkWatertight ? topo.degenerateTriangles : null,
        selfIntersections,
        selfIntersectionPoint,
        componentCount: checkComponents ? topo.componentCount : null,
        smallestComponent,
        volumeMm3: topo.volumeMm3 === null ? null : Math.round(topo.volumeMm3 * 1000) / 1000,
        minWallMm: minWall,
        thinPoint,
      })
    }
  }
  const printabilityMs = performance.now() - printabilityStart

  // --- Thread engagement: per fastener instance vs host (non-fastener) parts. ---
  const threadStart = performance.now()
  const fasteners: FastenerEngagement[] = []
  if (checkThreadEngagement) {
    const fastenerInstances = instances.filter((instance) => fastenerMeshIds.has(instance.meshId))
    for (const fastener of fastenerInstances) {
      // Hosts are ALL other instances: a screw legitimately grips into a
      // heat-set insert or nut (themselves classified as fasteners), so the
      // engaging material must not be restricted to non-fastener parts.
      const hostInstances = instances.filter((instance) => instance !== fastener)
      const engagement = estimateEngagement(fastener, hostInstances)
      if (!engagement.axial) continue
      fasteners.push({
        instanceId: fastener.instanceId,
        partType: fastener.partType,
        name: fastener.name,
        shaftLengthMm: Math.round(engagement.shaftLengthMm * 1000) / 1000,
        engagementMm: Math.round(engagement.engagementMm * 1000) / 1000,
        hostInstanceIds: engagement.hostInstanceIds,
        point: engagement.point ? [engagement.point.x, engagement.point.y, engagement.point.z] : null,
      })
    }
  }
  const threadMs = performance.now() - threadStart

  // --- Assembly access: per non-fastener part, coarse AABB-shadow extraction. ---
  const accessStart = performance.now()
  const access: AssemblyAccess[] = []
  if (checkAssemblyAccess) {
    const parts = instances.filter((instance) => !fastenerMeshIds.has(instance.meshId))
    const center = manifest.center ?? [0, 0, 0]
    for (const part of parts) {
      const others = parts.filter((other) => other !== part)
      const { clear, tried } = accessClearDirections(part, others, center as Vec3Tuple)
      const cx = (part.worldMin[0] + part.worldMax[0]) / 2
      const cy = (part.worldMin[1] + part.worldMax[1]) / 2
      const cz = (part.worldMin[2] + part.worldMax[2]) / 2
      access.push({
        instanceId: part.instanceId,
        partType: part.partType,
        name: part.name,
        directionsTried: tried,
        clearDirections: clear,
        point: [cx, cy, cz],
      })
    }
  }
  const accessMs = performance.now() - accessStart

  // --- Mating-face contact: verify declared / near-touching mating pairs are in
  // contact within tolerance (not floating apart, not crashing in). ---
  const matingStart = performance.now()
  const mating: MatingContact[] = []
  if (checkMatingContact) {
    const round3 = (value: number) => Math.round(value * 1000) / 1000
    const declaredSet = new Set(matingPairs.map(([x, y]) => partTypePairKey(x, y)))
    const partTypesInPairs = new Set(matingPairs.flat())
    const seen = new Set<string>()
    type Candidate = { a: InstanceGeometry; b: InstanceGeometry; declared: boolean }
    const candidates: Candidate[] = []
    const addCandidate = (a: InstanceGeometry, b: InstanceGeometry, declared: boolean) => {
      if (a.isFastener || b.isFastener) return // hardware overlaps by design
      const key = sweptPairKey(a.instanceId, b.instanceId)
      if (seen.has(key)) return
      seen.add(key)
      candidates.push({ a, b, declared })
    }

    // DECLARED matings: a wider, targeted broad phase over only the instances
    // whose partType participates in an ignoreOverlapPairs entry, so a declared
    // mate that floated apart (up to MATING_SEARCH_MM) is still caught.
    if (declaredSet.size > 0) {
      const relevant = instances.filter(
        (instance) => !instance.isFastener && partTypesInPairs.has(instance.partType),
      )
      const { pairs: declaredPairs } = broadPhasePairs(relevant, MATING_SEARCH_MM * 2, maxPairs)
      for (const [a, b] of declaredPairs) {
        if (declaredSet.has(partTypePairKey(a.partType, b.partType))) addCandidate(a, b, true)
      }
    }
    // LIKELY matings: the standard near-touching candidate pairs (the same broad
    // phase used for interference). These are only KEPT below when they are
    // actually in contact, so undeclared deep overlaps stay with mesh_overlap.
    for (const [a, b] of pairs) addCandidate(a, b, false)

    for (const candidate of candidates) {
      // Declared pairs search the wide window (to detect floating). Likely pairs
      // only matter when near-touching, so a tolerance-sized window lets the BVH
      // prune distant neighbours cheaply (the bulk of the candidates on big builds).
      const searchMm = candidate.declared ? MATING_SEARCH_MM : matingToleranceMm + INTERSECTION_EPSILON
      const metric = matingMetric(candidate.a, candidate.b, searchMm)
      // An undeclared pair is only a "mating" when it is genuinely in contact
      // (gap within tolerance and not deeply interpenetrating); otherwise it is
      // either a far neighbour or a clash already reported by mesh_overlap.
      if (!candidate.declared && (metric.gapMm > matingToleranceMm || metric.penetrationMm > matingToleranceMm)) {
        continue
      }
      // Split "intended mate" from "intended interference": a declared mate that
      // interpenetrates is NOT a crash when that same overlap is an allowed
      // interference (typed allowedInterferences entry, or the legacy blanket on
      // static parts) — it is already audited as an allowed mesh_overlap /
      // declared_interference record. The mating gate's remaining job for
      // declared pairs is catching mates that drift APART.
      if (
        candidate.declared &&
        metric.penetrationMm > matingToleranceMm &&
        resolveOverlapAllowance(
          allowanceConfig,
          candidate.a,
          candidate.b,
          metric.penetrationMm,
          motionGroups,
        ).allowed
      ) {
        continue
      }
      mating.push({
        a: { instanceId: candidate.a.instanceId, partType: candidate.a.partType, name: candidate.a.name },
        b: { instanceId: candidate.b.instanceId, partType: candidate.b.partType, name: candidate.b.name },
        declared: candidate.declared,
        gapMm: round3(metric.gapMm),
        penetrationMm: round3(metric.penetrationMm),
        point: metric.point ? (metric.point.map(round3) as Vec3Tuple) : null,
        region: metric.region
          ? {
              min: metric.region.min.map(round3) as Vec3Tuple,
              max: metric.region.max.map(round3) as Vec3Tuple,
            }
          : null,
      })
    }
  }
  const matingMs = performance.now() - matingStart

  // --- Wiring: producer-supplied routes vs solids, budget, bend, support, clearance. ---
  const routingStart = performance.now()
  const routing: RoutingReach[] = []
  if (routes.length > 0) {
    const solids = instances.filter((instance) => !instance.isFastener)
    const wireOpts = {
      wireClearanceMm: options.wireClearanceMm ?? DEFAULT_WIRE_CLEARANCE_MM,
      maxUnsupportedMm: options.maxUnsupportedMm ?? DEFAULT_MAX_UNSUPPORTED_MM,
    }
    for (const route of routes) routing.push(evaluateRoute(manifest, route, solids, wireOpts))
  }
  const routingMs = performance.now() - routingStart

  collisions.sort((a, b) => b.penetrationMm - a.penetrationMm)
  gaps.sort((a, b) => a.gapMm - b.gapMm)

  // --- Declared-interference audit: verify every allowedInterferences entry
  // against the actual geometry so the allowlist cannot rot. An entry must name
  // instances that exist and a pair that genuinely interferes (or at least
  // touches), within its declared maxPenetrationMm cap. Runs even for fastener
  // instances (suppressed from the interference pass) via direct measurement.
  const declaredInterferences: DeclaredInterferenceResult[] = []
  const declaredEntries: AllowedInterference[] = manifest.checksConfig?.allowedInterferences ?? []
  if (declaredEntries.length > 0) {
    const byInstanceId = new Map(instances.map((instance) => [instance.instanceId, instance]))
    const collisionByPair = new Map(
      collisions.map((collision) => [
        sweptPairKey(collision.a.instanceId, collision.b.instanceId),
        collision,
      ]),
    )
    const roundD = (v: number) => Math.round(v * 1000) / 1000
    for (const entry of declaredEntries) {
      const base = {
        kind: entry.kind as string,
        instances: entry.instances,
        reason: entry.reason,
        feature: entry.feature ?? null,
        maxPenetrationMm: entry.maxPenetrationMm ?? null,
      }
      const a = byInstanceId.get(entry.instances[0])
      const b = byInstanceId.get(entry.instances[1])
      if (!a || !b) {
        declaredInterferences.push({
          ...base,
          outcome: 'unknown_instance',
          penetrationMm: null,
          gapMm: null,
          point: null,
          region: null,
          reportedAsCollision: false,
        })
        continue
      }
      const collision = collisionByPair.get(sweptPairKey(a.instanceId, b.instanceId))
      if (collision) {
        const overCap =
          entry.maxPenetrationMm !== undefined && collision.penetrationMm > entry.maxPenetrationMm
        declaredInterferences.push({
          ...base,
          outcome: overCap ? 'exceeds_max_penetration' : 'overlapping',
          penetrationMm: collision.penetrationMm,
          gapMm: null,
          point: collision.point,
          region: collision.region,
          reportedAsCollision: true,
        })
        continue
      }
      // Not in the collision list (fastener pair, shallow overlap, or apart):
      // measure the pair directly. Only a handful of entries, so this is cheap.
      const distance = surfaceDistance(a, b, MATING_SEARCH_MM)
      if (distance <= INTERSECTION_EPSILON) {
        const penetration = penetrationDepth(a, b)
        const overCap =
          entry.maxPenetrationMm !== undefined && penetration.depthMm > entry.maxPenetrationMm
        declaredInterferences.push({
          ...base,
          outcome: overCap ? 'exceeds_max_penetration' : 'overlapping',
          penetrationMm: roundD(penetration.depthMm),
          gapMm: null,
          point: penetration.point
            ? (penetration.point.map(roundD) as [number, number, number])
            : null,
          region: penetration.region
            ? {
                min: penetration.region.min.map(roundD) as [number, number, number],
                max: penetration.region.max.map(roundD) as [number, number, number],
              }
            : null,
          reportedAsCollision: false,
        })
        continue
      }
      const inContact = distance <= Math.max(toleranceMm, matingToleranceMm)
      declaredInterferences.push({
        ...base,
        outcome: inContact ? 'in_contact' : 'not_in_contact',
        penetrationMm: null,
        gapMm: distance <= MATING_SEARCH_MM ? roundD(distance) : null,
        point: null,
        region: null,
        reportedAsCollision: false,
      })
    }
  }

  // A printed mesh that is >1 disjoint body is unmanufacturable: fold those fails
  // into problemCount so `passed` flips, the same way collisions/floating do.
  const disconnectedFails = checkComponents
    ? printability.filter(
        (mesh) =>
          mesh.componentCount !== null &&
          mesh.componentCount > (expectedMeshComponents[mesh.meshId] ?? maxMeshComponents),
      ).length
    : 0

  // Intentional overlaps (typed allowedInterferences entries, or the legacy
  // ignoreOverlapPairs blanket on static parts) do not count as problems. A
  // broken allowlist DOES: stale/dangling/over-cap declared entries fail (over-
  // cap pairs already counted through collisions[] are not double-counted).
  const unexpectedCollisions = collisions.filter((collision) => !collision.allowed).length
  const declaredIssues = declaredInterferences.filter(
    (result) =>
      isDeclaredInterferenceIssue(result) &&
      !(result.outcome === 'exceeds_max_penetration' && result.reportedAsCollision),
  ).length
  const fasteningChecks = checkFastenings(manifest, instances)
  const problemCount = unexpectedCollisions + floating.length + disconnectedFails + declaredIssues + fasteningChecks.filter(c => c.status === 'fail').length
  const totalMs = performance.now() - startedAt

  return {
    passed: problemCount === 0,
    problemCount,
    toleranceMm,
    minPenetrationMm,
    instanceCount: instances.length,
    meshCount: meshById.size,
    missingMeshes,
    fastenersExcluded,
    fastenersIncluded: includeFasteners,
    broadPhasePairs: pairs.length,
    narrowPhasePairs: pairs.length,
    capped,
    collisions,
    floating,
    gaps,
    declaredInterferences,
    printability,
    fasteners,
    fasteningChecks,
    access,
    mating,
    routing,
    minWallMm,
    minThreadEngagementMm,
    matingToleranceMm,
    components: {
      count: components.length,
      mainComponentSize: Math.max(mainSize, 0),
      floatingComponentCount: components.length - (mainSize > 0 ? 1 : 0),
    },
    timings: {
      loadMs: Math.round(loadMs),
      bvhMs: Math.round(bvhMs),
      broadMs: Math.round(broadMs),
      narrowMs: Math.round(narrowMs),
      connectivityMs: Math.round(connectivityMs),
      printabilityMs: Math.round(printabilityMs),
      threadMs: Math.round(threadMs),
      accessMs: Math.round(accessMs),
      matingMs: Math.round(matingMs),
      routingMs: Math.round(routingMs),
      totalMs: Math.round(totalMs),
    },
  }
}

// ---------------------------------------------------------------------------
// Geometry query API (LLM/agent): probe / slice / thickness / mesh stats.
//
// These commands answer "is this point/box solid?", "how thick is this member
// here?", and "what are this mesh's bounds/volume/topology?" directly from
// scene.json + STL assets, reusing the same load-once BVH machinery as the
// interference checker. They are plain-data (THREE-free) outputs so the CLI can
// JSON-serialize them and the viewer can paint them through the highlight
// channel. Rigid instance transforms are assumed throughout (local distances
// equal world millimetres), matching the rest of the engine.
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// probe points / probe region
// ---------------------------------------------------------------------------

export type ProbePointResult = {
  point: Vec3
  /** True when the point lies strictly inside at least one solid instance. */
  insideSolid: boolean
  /** Instance ids whose solid encloses the point. */
  insideInstanceIds: string[]
  /** Distance (mm) to the nearest mesh surface (the wall depth when inside). */
  nearestSurfaceDistanceMm: number | null
  nearestFeature: { instanceId: string; partType: string; name: string } | null
  /**
   * `solid` = inside material; `hole` = empty but within a part's bounding
   * envelope (a bore/pocket — HEURISTIC); `void` = empty and outside every
   * part's bounds.
   */
  classification: 'solid' | 'hole' | 'void'
}

export type ProbePointsReport = {
  instanceCount: number
  meshCount: number
  missingMeshes: string[]
  fastenersExcluded: number
  insideCount: number
  points: ProbePointResult[]
  timings: { loadMs: number; queryMs: number; totalMs: number }
}

// Classify each query point against the build's solids: inside/outside, nearest
// surface distance + feature, and a solid/hole/void label. Built on the same
// ray-parity point-in-mesh test the penetration sampler uses.
export const probePoints = async (
  manifest: BuildSceneManifest,
  points: Vec3[],
  options: GeometryLoadOptions,
): Promise<ProbePointsReport> => {
  const startedAt = performance.now()
  const loadStart = performance.now()
  const { instances, meshById, missingMeshes, fastenersExcluded } = await buildInstanceGeometries(manifest, options)
  const loadMs = performance.now() - loadStart

  const queryStart = performance.now()
  const world = new THREE.Vector3()
  const local = new THREE.Vector3()
  const results: ProbePointResult[] = []
  let insideCount = 0

  for (const point of points) {
    world.set(point[0], point[1], point[2])
    const insideInstanceIds: string[] = []
    let insideAabb = false
    for (const instance of instances) {
      if (!pointInAabb(instance, world, INTERSECTION_EPSILON)) continue
      insideAabb = true
      local.copy(world).applyMatrix4(instance.inverse)
      if (pointInside(instance.mesh.bvh, local)) insideInstanceIds.push(instance.instanceId)
    }

    // Nearest surface: rank instances by AABB distance, then take the exact
    // closest-point distance on the nearest few BVHs.
    const ranked = instances
      .map((instance) => ({ instance, aabb: pointAabbDistance(instance, world) }))
      .sort((a, b) => a.aabb - b.aabb)
      .slice(0, 8)
    let nearest = Infinity
    let nearestInstance: InstanceGeometry | null = null
    for (const { instance, aabb } of ranked) {
      if (aabb > nearest) break
      local.copy(world).applyMatrix4(instance.inverse)
      const hit = instance.mesh.bvh.closestPointToPoint(local, tmpHit)
      if (hit && hit.distance < nearest) {
        nearest = hit.distance
        nearestInstance = instance
      }
    }

    const insideSolid = insideInstanceIds.length > 0
    if (insideSolid) insideCount += 1
    const classification: ProbePointResult['classification'] = insideSolid
      ? 'solid'
      : insideAabb
        ? 'hole'
        : 'void'
    results.push({
      point: roundVec(point),
      insideSolid,
      insideInstanceIds,
      nearestSurfaceDistanceMm: Number.isFinite(nearest) ? round3(nearest) : null,
      nearestFeature: nearestInstance
        ? { instanceId: nearestInstance.instanceId, partType: nearestInstance.partType, name: nearestInstance.name }
        : null,
      classification,
    })
  }
  const queryMs = performance.now() - queryStart

  return {
    instanceCount: instances.length,
    meshCount: meshById.size,
    missingMeshes,
    fastenersExcluded,
    insideCount,
    points: results,
    timings: { loadMs: Math.round(loadMs), queryMs: Math.round(queryMs), totalMs: Math.round(performance.now() - startedAt) },
  }
}

export type ProbeRegionReport = {
  box: { min: Vec3; max: Vec3 }
  instanceCount: number
  meshCount: number
  missingMeshes: string[]
  fastenersExcluded: number
  /** Grid samples per axis [nx, ny, nz] and the total tested. */
  grid: [number, number, number]
  sampleCount: number
  occupiedSamples: number
  occupiedFraction: number
  boxVolumeMm3: number
  occupiedVolumeEstimateMm3: number
  /** World AABB enclosing the occupied (solid) samples, or null when empty. */
  occupiedBounds: { min: Vec3; max: Vec3 } | null
  /** Instance ids that contributed at least one occupied sample. */
  occupantInstanceIds: string[]
  timings: { loadMs: number; queryMs: number; totalMs: number }
}

const REGION_TARGET_SAMPLES = 8000
const REGION_MAX_AXIS = 48

// Sample a 3D grid spanning the query box and report the solid-occupied
// fraction, an occupied-volume estimate, the occupied bounds, and which
// instances contribute. The spacing scales with the box so the sample budget
// stays bounded for any box size.
export const probeRegion = async (
  manifest: BuildSceneManifest,
  box: { min: Vec3; max: Vec3 },
  options: GeometryLoadOptions & { samples?: number },
): Promise<ProbeRegionReport> => {
  const startedAt = performance.now()
  const loadStart = performance.now()
  const { instances, meshById, missingMeshes, fastenersExcluded } = await buildInstanceGeometries(manifest, options)
  const loadMs = performance.now() - loadStart

  const dims: [number, number, number] = [
    Math.max(0, box.max[0] - box.min[0]),
    Math.max(0, box.max[1] - box.min[1]),
    Math.max(0, box.max[2] - box.min[2]),
  ]
  const boxVolumeMm3 = dims[0] * dims[1] * dims[2]
  const budget = Math.max(8, Math.round(options.samples ?? REGION_TARGET_SAMPLES))
  const volume = Math.max(dims[0], 1e-3) * Math.max(dims[1], 1e-3) * Math.max(dims[2], 1e-3)
  const spacing = Math.cbrt(volume / budget)
  const counts: [number, number, number] = dims.map((dim) =>
    Math.min(REGION_MAX_AXIS, Math.max(1, Math.floor(dim / Math.max(spacing, 1e-6)) + 1)),
  ) as [number, number, number]

  const queryStart = performance.now()
  const xs = axisSamples(box.min[0], box.max[0], counts[0])
  const ys = axisSamples(box.min[1], box.max[1], counts[1])
  const zs = axisSamples(box.min[2], box.max[2], counts[2])
  const world = new THREE.Vector3()
  const local = new THREE.Vector3()
  const occMin: [number, number, number] = [Infinity, Infinity, Infinity]
  const occMax: [number, number, number] = [-Infinity, -Infinity, -Infinity]
  const occupants = new Set<string>()
  let occupied = 0
  let sampleCount = 0

  // Pre-cull to instances whose AABB intersects the query box.
  const candidates = instances.filter(
    (instance) =>
      instance.worldMin[0] <= box.max[0] &&
      instance.worldMax[0] >= box.min[0] &&
      instance.worldMin[1] <= box.max[1] &&
      instance.worldMax[1] >= box.min[1] &&
      instance.worldMin[2] <= box.max[2] &&
      instance.worldMax[2] >= box.min[2],
  )

  for (const x of xs) {
    for (const y of ys) {
      for (const z of zs) {
        sampleCount += 1
        world.set(x, y, z)
        let isOccupied = false
        for (const instance of candidates) {
          if (!pointInAabb(instance, world, INTERSECTION_EPSILON)) continue
          local.copy(world).applyMatrix4(instance.inverse)
          if (pointInside(instance.mesh.bvh, local)) {
            isOccupied = true
            occupants.add(instance.instanceId)
          }
        }
        if (isOccupied) {
          occupied += 1
          if (x < occMin[0]) occMin[0] = x
          if (y < occMin[1]) occMin[1] = y
          if (z < occMin[2]) occMin[2] = z
          if (x > occMax[0]) occMax[0] = x
          if (y > occMax[1]) occMax[1] = y
          if (z > occMax[2]) occMax[2] = z
        }
      }
    }
  }
  const queryMs = performance.now() - queryStart
  const occupiedFraction = sampleCount > 0 ? occupied / sampleCount : 0

  return {
    box: { min: roundVec(box.min), max: roundVec(box.max) },
    instanceCount: instances.length,
    meshCount: meshById.size,
    missingMeshes,
    fastenersExcluded,
    grid: counts,
    sampleCount,
    occupiedSamples: occupied,
    occupiedFraction: round3(occupiedFraction),
    boxVolumeMm3: round3(boxVolumeMm3),
    occupiedVolumeEstimateMm3: round3(occupiedFraction * boxVolumeMm3),
    occupiedBounds: occupied > 0 ? { min: roundVec(occMin), max: roundVec(occMax) } : null,
    occupantInstanceIds: [...occupants],
    timings: { loadMs: Math.round(loadMs), queryMs: Math.round(queryMs), totalMs: Math.round(performance.now() - startedAt) },
  }
}

// ---------------------------------------------------------------------------
// slice / thickness
// ---------------------------------------------------------------------------

export type SlicePlane = 'xy' | 'yz' | 'xz'

// plane → the world axis index of its NORMAL and the two in-plane (u,v) axes.
const PLANE_AXES: Record<SlicePlane, { normal: number; u: number; v: number; normalName: 'x' | 'y' | 'z' }> = {
  yz: { normal: 0, u: 1, v: 2, normalName: 'x' },
  xz: { normal: 1, u: 0, v: 2, normalName: 'y' },
  xy: { normal: 2, u: 0, v: 1, normalName: 'z' },
}

export type SliceRegion = {
  areaMm2: number
  cellCount: number
  /** 2D bbox of the region in plane (u,v) coords. */
  bbox: { uMin: number; uMax: number; vMin: number; vMax: number }
  /** Local min thickness (mm) ≈ inscribed-disk diameter (2× distance transform).
   *  HEURISTIC; null when the metric was not requested. */
  thicknessMm: number | null
  /** World point at the thickest inscribed location (the disk centre). */
  point: Vec3 | null
}

export type SliceSection = {
  /** Position (mm) along the plane normal axis. */
  coord: number
  areaMm2: number
  regionCount: number
  /** Min region thickness over significant regions (mm), or null. */
  minThicknessMm: number | null
  maxThicknessMm: number | null
  /** World point where the section's min thickness occurs. */
  minThicknessPoint: Vec3 | null
  regions: SliceRegion[]
}

export type SliceReport = {
  plane: SlicePlane
  normalAxis: 'x' | 'y' | 'z'
  resolutionMm: number
  metric: 'area' | 'min-thickness'
  instanceCount: number
  meshCount: number
  missingMeshes: string[]
  fastenersExcluded: number
  sectionCount: number
  sections: SliceSection[]
  /** The narrowest point across all sections (min-thickness metric). */
  overall: {
    minThicknessMm: number | null
    atCoord: number | null
    atPoint: Vec3 | null
    /** Pass/fail vs an optional threshold (null when none supplied). */
    threshold: number | null
    passed: boolean | null
  }
  timings: { loadMs: number; sliceMs: number; totalMs: number }
}

const SLICE_MAX_AXIS = 200
const SLICE_MIN_REGION_AREA_FRACTION = 0.02

// 2D distance transform (in cells) of an occupancy grid: the distance from each
// occupied cell to the nearest empty cell, via a two-pass chamfer (orthogonal 1,
// diagonal √2). Out-of-bounds counts as empty so the part's outer boundary is a
// background edge. Returns the per-cell distances and the (col,row) of the max.
const distanceTransform = (occ: Uint8Array, w: number, h: number) => {
  const INF = 1e9
  const dt = new Float64Array(w * h)
  for (let i = 0; i < dt.length; i += 1) dt[i] = occ[i] ? INF : 0
  const D1 = 1
  const D2 = Math.SQRT2
  const at = (x: number, y: number) => (x < 0 || y < 0 || x >= w || y >= h ? 0 : dt[y * w + x])
  // Forward pass.
  for (let y = 0; y < h; y += 1) {
    for (let x = 0; x < w; x += 1) {
      const i = y * w + x
      if (!occ[i]) continue
      let best = dt[i]
      best = Math.min(best, at(x - 1, y) + D1, at(x, y - 1) + D1, at(x - 1, y - 1) + D2, at(x + 1, y - 1) + D2)
      dt[i] = best
    }
  }
  // Backward pass.
  for (let y = h - 1; y >= 0; y -= 1) {
    for (let x = w - 1; x >= 0; x -= 1) {
      const i = y * w + x
      if (!occ[i]) continue
      let best = dt[i]
      best = Math.min(best, at(x + 1, y) + D1, at(x, y + 1) + D1, at(x + 1, y + 1) + D2, at(x - 1, y + 1) + D2)
      dt[i] = best
    }
  }
  return dt
}

// Connected components (4-connectivity) over the occupancy grid, returning a
// label per cell (0 = background) and the component count.
const labelComponents = (occ: Uint8Array, w: number, h: number) => {
  const labels = new Int32Array(w * h)
  let next = 0
  const stack: number[] = []
  for (let start = 0; start < occ.length; start += 1) {
    if (!occ[start] || labels[start] !== 0) continue
    next += 1
    labels[start] = next
    stack.length = 0
    stack.push(start)
    while (stack.length > 0) {
      const i = stack.pop() as number
      const x = i % w
      const y = (i - x) / w
      const neighbors = [
        x > 0 ? i - 1 : -1,
        x < w - 1 ? i + 1 : -1,
        y > 0 ? i - w : -1,
        y < h - 1 ? i + w : -1,
      ]
      for (const n of neighbors) {
        if (n >= 0 && occ[n] && labels[n] === 0) {
          labels[n] = next
          stack.push(n)
        }
      }
    }
  }
  return { labels, count: next }
}

const computeSections = (
  instances: InstanceGeometry[],
  plane: SlicePlane,
  coords: number[],
  resMm: number,
  computeThickness: boolean,
): SliceSection[] => {
  const { normal, u, v } = PLANE_AXES[plane]
  const world = new THREE.Vector3()
  const local = new THREE.Vector3()
  const sections: SliceSection[] = []

  for (const coord of coords) {
    // Instances straddling this section coordinate along the normal axis.
    const straddling = instances.filter(
      (instance) => instance.worldMin[normal] - INTERSECTION_EPSILON <= coord && instance.worldMax[normal] + INTERSECTION_EPSILON >= coord,
    )
    if (straddling.length === 0) {
      sections.push({ coord: round3(coord), areaMm2: 0, regionCount: 0, minThicknessMm: null, maxThicknessMm: null, minThicknessPoint: null, regions: [] })
      continue
    }
    // In-plane bounds (with a margin) over the straddling instances.
    let uMin = Infinity
    let uMax = -Infinity
    let vMin = Infinity
    let vMax = -Infinity
    for (const instance of straddling) {
      uMin = Math.min(uMin, instance.worldMin[u])
      uMax = Math.max(uMax, instance.worldMax[u])
      vMin = Math.min(vMin, instance.worldMin[v])
      vMax = Math.max(vMax, instance.worldMax[v])
    }
    const uSpan = Math.max(uMax - uMin, 1e-3)
    const vSpan = Math.max(vMax - vMin, 1e-3)
    const w = Math.min(SLICE_MAX_AXIS, Math.max(1, Math.ceil(uSpan / resMm)))
    const h = Math.min(SLICE_MAX_AXIS, Math.max(1, Math.ceil(vSpan / resMm)))
    const cellU = uSpan / w
    const cellV = vSpan / h
    const cellArea = cellU * cellV
    const occ = new Uint8Array(w * h)

    for (let yi = 0; yi < h; yi += 1) {
      const vc = vMin + (yi + 0.5) * cellV
      for (let xi = 0; xi < w; xi += 1) {
        const uc = uMin + (xi + 0.5) * cellU
        world.setComponent(normal, coord)
        world.setComponent(u, uc)
        world.setComponent(v, vc)
        for (const instance of straddling) {
          if (!pointInAabb(instance, world, INTERSECTION_EPSILON)) continue
          local.copy(world).applyMatrix4(instance.inverse)
          if (pointInside(instance.mesh.bvh, local)) {
            occ[yi * w + xi] = 1
            break
          }
        }
      }
    }

    const occupiedCells = occ.reduce((sum, value) => sum + value, 0)
    const { labels, count } = labelComponents(occ, w, h)
    const dt = computeThickness ? distanceTransform(occ, w, h) : null
    const cellDiag = Math.min(cellU, cellV)

    type RegionAcc = { cells: number; uMin: number; uMax: number; vMin: number; vMax: number; maxDt: number; maxDtX: number; maxDtY: number }
    const accs = new Map<number, RegionAcc>()
    for (let yi = 0; yi < h; yi += 1) {
      for (let xi = 0; xi < w; xi += 1) {
        const i = yi * w + xi
        const label = labels[i]
        if (label === 0) continue
        const uc = uMin + (xi + 0.5) * cellU
        const vc = vMin + (yi + 0.5) * cellV
        let acc = accs.get(label)
        if (!acc) {
          acc = { cells: 0, uMin: Infinity, uMax: -Infinity, vMin: Infinity, vMax: -Infinity, maxDt: -1, maxDtX: xi, maxDtY: yi }
          accs.set(label, acc)
        }
        acc.cells += 1
        acc.uMin = Math.min(acc.uMin, uc - cellU / 2)
        acc.uMax = Math.max(acc.uMax, uc + cellU / 2)
        acc.vMin = Math.min(acc.vMin, vc - cellV / 2)
        acc.vMax = Math.max(acc.vMax, vc + cellV / 2)
        if (dt) {
          const d = dt[i]
          if (d > acc.maxDt) {
            acc.maxDt = d
            acc.maxDtX = xi
            acc.maxDtY = yi
          }
        }
      }
    }

    const regions: SliceRegion[] = []
    for (const acc of accs.values()) {
      let thicknessMm: number | null = null
      let point: Vec3 | null = null
      if (dt) {
        // Inscribed-disk diameter ≈ 2 × (distance-transform peak in mm).
        thicknessMm = round3(Math.max(acc.maxDt * cellDiag * 2, cellDiag))
        const pu = uMin + (acc.maxDtX + 0.5) * cellU
        const pv = vMin + (acc.maxDtY + 0.5) * cellV
        const p: [number, number, number] = [0, 0, 0]
        p[normal] = coord
        p[u] = pu
        p[v] = pv
        point = roundVec(p)
      }
      regions.push({
        areaMm2: round3(acc.cells * cellArea),
        cellCount: acc.cells,
        bbox: { uMin: round3(acc.uMin), uMax: round3(acc.uMax), vMin: round3(acc.vMin), vMax: round3(acc.vMax) },
        thicknessMm,
        point,
      })
    }
    regions.sort((a, b) => b.areaMm2 - a.areaMm2)

    // Section thickness = min over SIGNIFICANT regions (filters speck regions
    // from tessellation noise that would report an artificially small width).
    let minThicknessMm: number | null = null
    let maxThicknessMm: number | null = null
    let minThicknessPoint: Vec3 | null = null
    if (computeThickness) {
      const totalArea = occupiedCells * cellArea
      const significant = regions.filter((region) => region.areaMm2 >= totalArea * SLICE_MIN_REGION_AREA_FRACTION)
      for (const region of significant.length > 0 ? significant : regions) {
        if (region.thicknessMm === null) continue
        if (minThicknessMm === null || region.thicknessMm < minThicknessMm) {
          minThicknessMm = region.thicknessMm
          minThicknessPoint = region.point
        }
        if (maxThicknessMm === null || region.thicknessMm > maxThicknessMm) maxThicknessMm = region.thicknessMm
      }
    }

    sections.push({
      coord: round3(coord),
      areaMm2: round3(occupiedCells * cellArea),
      regionCount: count,
      minThicknessMm,
      maxThicknessMm,
      minThicknessPoint,
      regions,
    })
  }
  return sections
}

export type SliceOptions = GeometryLoadOptions & {
  plane: SlicePlane
  /** Section coordinates (mm) along the plane normal axis. */
  coords?: number[]
  /** Range sweep [lo, hi, step] along the normal axis (overrides coords). */
  range?: { lo: number; hi: number; step: number }
  /** Grid cell size (mm) for the section rasterization. Default 1mm. */
  resolutionMm?: number
  /** Compute the per-region min-thickness metric (distance transform). */
  metric?: 'area' | 'min-thickness'
  /** Optional pass/fail threshold (mm) for the overall min thickness. */
  minThicknessMm?: number
}

const DEFAULT_SLICE_RES_MM = 1.0

export const sliceBuild = async (
  manifest: BuildSceneManifest,
  options: SliceOptions,
): Promise<SliceReport> => {
  const startedAt = performance.now()
  const loadStart = performance.now()
  const { instances, meshById, missingMeshes, fastenersExcluded } = await buildInstanceGeometries(manifest, options)
  const loadMs = performance.now() - loadStart

  const { normal, normalName } = PLANE_AXES[options.plane]
  const resMm = Math.max(options.resolutionMm ?? DEFAULT_SLICE_RES_MM, 1e-3)
  const computeThickness = (options.metric ?? 'area') === 'min-thickness'

  // Resolve the section coordinates: explicit coords, a range sweep, or a single
  // section at the midpoint of the build's extent along the normal axis.
  let coords: number[] = []
  if (options.coords && options.coords.length > 0) {
    coords = options.coords
  } else if (options.range) {
    const { lo, hi, step } = options.range
    const realStep = step > 0 ? step : Math.max((hi - lo) / 32, 1e-3)
    for (let c = lo; c <= hi + 1e-6; c += realStep) coords.push(c)
  } else if (instances.length > 0) {
    let lo = Infinity
    let hi = -Infinity
    for (const instance of instances) {
      lo = Math.min(lo, instance.worldMin[normal])
      hi = Math.max(hi, instance.worldMax[normal])
    }
    coords = [(lo + hi) / 2]
  }

  const sliceStart = performance.now()
  const sections = computeSections(instances, options.plane, coords, resMm, computeThickness)
  const sliceMs = performance.now() - sliceStart

  let overallMin: number | null = null
  let atCoord: number | null = null
  let atPoint: Vec3 | null = null
  if (computeThickness) {
    for (const section of sections) {
      if (section.minThicknessMm === null) continue
      if (overallMin === null || section.minThicknessMm < overallMin) {
        overallMin = section.minThicknessMm
        atCoord = section.coord
        atPoint = section.minThicknessPoint
      }
    }
  }
  const threshold = options.minThicknessMm ?? null
  const passed = threshold === null || overallMin === null ? null : overallMin >= threshold

  return {
    plane: options.plane,
    normalAxis: normalName,
    resolutionMm: round3(resMm),
    metric: computeThickness ? 'min-thickness' : 'area',
    instanceCount: instances.length,
    meshCount: meshById.size,
    missingMeshes,
    fastenersExcluded,
    sectionCount: sections.length,
    sections,
    overall: { minThicknessMm: overallMin, atCoord, atPoint, threshold, passed },
    timings: { loadMs: Math.round(loadMs), sliceMs: Math.round(sliceMs), totalMs: Math.round(performance.now() - startedAt) },
  }
}

export type ThicknessReport = {
  plane: SlicePlane
  normalAxis: 'x' | 'y' | 'z'
  resolutionMm: number
  sectionCount: number
  instanceCount: number
  meshCount: number
  missingMeshes: string[]
  fastenersExcluded: number
  minThicknessMm: number | null
  atCoord: number | null
  atPoint: Vec3 | null
  /** In-plane axis (u/v world axis names) along which the member is narrowest. */
  weakestAxis: 'x' | 'y' | 'z' | null
  threshold: number | null
  passed: boolean | null
  timings: { loadMs: number; sliceMs: number; totalMs: number }
}

const AXIS_NAME: Array<'x' | 'y' | 'z'> = ['x', 'y', 'z']

// Prove a member's min thickness along its length: auto-pick the section plane
// perpendicular to the filtered geometry's LONGEST axis (so sections cut across
// the member), sweep along it, and report the narrowest section. A thin wrapper
// over sliceBuild's min-thickness metric.
export const thicknessBuild = async (
  manifest: BuildSceneManifest,
  options: GeometryLoadOptions & { plane?: SlicePlane | 'auto'; resolutionMm?: number; sections?: number; minThicknessMm?: number },
): Promise<ThicknessReport> => {
  const startedAt = performance.now()
  const loadStart = performance.now()
  const { instances, meshById, missingMeshes, fastenersExcluded } = await buildInstanceGeometries(manifest, options)
  const loadMs = performance.now() - loadStart

  // World extent across the selected instances.
  const min: [number, number, number] = [Infinity, Infinity, Infinity]
  const max: [number, number, number] = [-Infinity, -Infinity, -Infinity]
  for (const instance of instances) {
    for (let axis = 0; axis < 3; axis += 1) {
      min[axis] = Math.min(min[axis], instance.worldMin[axis])
      max[axis] = Math.max(max[axis], instance.worldMax[axis])
    }
  }
  const extents = [max[0] - min[0], max[1] - min[1], max[2] - min[2]]

  // Pick the plane whose NORMAL is the longest axis (cut across the member).
  let normalAxis = 0
  if (extents[1] > extents[normalAxis]) normalAxis = 1
  if (extents[2] > extents[normalAxis]) normalAxis = 2
  let plane: SlicePlane = normalAxis === 0 ? 'yz' : normalAxis === 1 ? 'xz' : 'xy'
  if (options.plane && options.plane !== 'auto') {
    plane = options.plane
    normalAxis = PLANE_AXES[plane].normal
  }

  const resMm = Math.max(options.resolutionMm ?? DEFAULT_SLICE_RES_MM, 1e-3)
  const sectionCount = Math.max(2, Math.round(options.sections ?? 24))
  const lo = min[normalAxis]
  const hi = max[normalAxis]
  // Avoid the exact extremes (degenerate end-cap sections).
  const span = hi - lo
  const inset = span * 0.02
  const coords: number[] = []
  for (let i = 0; i < sectionCount; i += 1) {
    coords.push(lo + inset + ((span - 2 * inset) * i) / (sectionCount - 1))
  }

  const sliceStart = performance.now()
  const sections = instances.length > 0 ? computeSections(instances, plane, coords, resMm, true) : []
  const sliceMs = performance.now() - sliceStart

  let minThicknessMm: number | null = null
  let atCoord: number | null = null
  let atPoint: Vec3 | null = null
  let weakRegionBbox: SliceRegion['bbox'] | null = null
  for (const section of sections) {
    if (section.minThicknessMm === null) continue
    if (minThicknessMm === null || section.minThicknessMm < minThicknessMm) {
      minThicknessMm = section.minThicknessMm
      atCoord = section.coord
      atPoint = section.minThicknessPoint
      // The region carrying the section min (largest significant region first).
      weakRegionBbox = section.regions.find((region) => region.thicknessMm === section.minThicknessMm)?.bbox ?? null
    }
  }

  // Weakest in-plane axis: the narrower bbox dimension of the governing region.
  let weakestAxis: 'x' | 'y' | 'z' | null = null
  if (weakRegionBbox) {
    const { u, v } = PLANE_AXES[plane]
    const uExtent = weakRegionBbox.uMax - weakRegionBbox.uMin
    const vExtent = weakRegionBbox.vMax - weakRegionBbox.vMin
    weakestAxis = uExtent <= vExtent ? AXIS_NAME[u] : AXIS_NAME[v]
  }

  const threshold = options.minThicknessMm ?? null
  const passed = threshold === null || minThicknessMm === null ? null : minThicknessMm >= threshold

  return {
    plane,
    normalAxis: AXIS_NAME[normalAxis],
    resolutionMm: round3(resMm),
    sectionCount: sections.length,
    instanceCount: instances.length,
    meshCount: meshById.size,
    missingMeshes,
    fastenersExcluded,
    minThicknessMm,
    atCoord,
    atPoint,
    weakestAxis,
    threshold,
    passed,
    timings: { loadMs: Math.round(loadMs), sliceMs: Math.round(sliceMs), totalMs: Math.round(performance.now() - startedAt) },
  }
}

// ---------------------------------------------------------------------------
// mesh stats
// ---------------------------------------------------------------------------

export type MeshStat = {
  meshId: string
  meshName: string
  isFastener: boolean
  instanceIds: string[]
  partTypes: string[]
  triangleCount: number
  vertexCount: number
  bounds: { min: Vec3; max: Vec3 }
  sizeMm: Vec3
  volumeMm3: number
  surfaceAreaMm2: number
  watertight: boolean
  openEdges: number
  nonManifoldEdges: number
  inconsistentWinding: boolean
  degenerateTriangles: number
  componentCount: number
}

export type MeshStatsReport = {
  meshCount: number
  instanceCount: number
  missingMeshes: string[]
  meshes: MeshStat[]
  totals: { triangleCount: number; volumeMm3: number; surfaceAreaMm2: number; nonWatertight: number }
  timings: { loadMs: number; statsMs: number; totalMs: number }
}

const meshSurfaceArea = (mesh: MeshGeometry) => {
  const geometry = mesh.geometry
  const position = geometry.attributes.position as THREE.BufferAttribute
  const index = geometry.index
  const a = new THREE.Vector3()
  const b = new THREE.Vector3()
  const c = new THREE.Vector3()
  const ab = new THREE.Vector3()
  const ac = new THREE.Vector3()
  let area = 0
  for (let t = 0; t < mesh.triangleCount; t += 1) {
    readTriVertex(position, index, t, 0, a)
    readTriVertex(position, index, t, 1, b)
    readTriVertex(position, index, t, 2, c)
    ab.subVectors(b, a)
    ac.subVectors(c, a)
    area += ab.cross(ac).length() * 0.5
  }
  return area
}

// Per-unique-mesh bounds / volume / surface area / triangle + vertex count /
// watertightness / connected components. Reuses analyzeTopology (the same robust
// edge-adjacency + welded-vertex union-find the printability checks use).
export const meshStats = async (
  manifest: BuildSceneManifest,
  options: GeometryLoadOptions,
): Promise<MeshStatsReport> => {
  const startedAt = performance.now()
  const loadStart = performance.now()
  // Load with fasteners included by default for stats (they are real meshes),
  // unless the caller filtered them out; the instance set below uses the same
  // filter so counts line up.
  const { instances, meshById, missingMeshes } = await buildInstanceGeometries(manifest, {
    ...options,
    includeFasteners: options.includeFasteners ?? true,
  })
  const loadMs = performance.now() - loadStart

  const fastenerMeshIds = new Set(manifest.meshes.filter((mesh) => isFastenerMesh(mesh)).map((mesh) => mesh.id))
  const refsByMesh = new Map<string, InstanceGeometry[]>()
  for (const instance of instances) {
    const list = refsByMesh.get(instance.meshId) ?? []
    list.push(instance)
    refsByMesh.set(instance.meshId, list)
  }

  const statsStart = performance.now()
  const meshes: MeshStat[] = []
  let totalTris = 0
  let totalVolume = 0
  let totalArea = 0
  let nonWatertight = 0
  for (const mesh of manifest.meshes) {
    const geom = meshById.get(mesh.id)
    if (!geom) continue
    const refs = refsByMesh.get(mesh.id) ?? []
    // Honor the part/instance filter: skip meshes with no surviving instance.
    if ((options.partTypes || options.instanceIds) && refs.length === 0) continue
    const topo = analyzeTopology(geom, true)
    const area = meshSurfaceArea(geom)
    const size = new THREE.Vector3()
    geom.localBox.getSize(size)
    const watertight = topo.openEdges === 0 && topo.nonManifoldEdges === 0
    if (!watertight) nonWatertight += 1
    totalTris += geom.triangleCount
    totalVolume += topo.volumeMm3
    totalArea += area
    meshes.push({
      meshId: mesh.id,
      meshName: mesh.name,
      isFastener: fastenerMeshIds.has(mesh.id),
      instanceIds: refs.map((ref) => ref.instanceId),
      partTypes: [...new Set(refs.map((ref) => ref.partType))],
      triangleCount: geom.triangleCount,
      vertexCount: (geom.geometry.index ? geom.geometry.attributes.position.count : geom.triangleCount * 3),
      bounds: { min: roundVec([geom.localBox.min.x, geom.localBox.min.y, geom.localBox.min.z]), max: roundVec([geom.localBox.max.x, geom.localBox.max.y, geom.localBox.max.z]) },
      sizeMm: roundVec([size.x, size.y, size.z]),
      volumeMm3: round3(topo.volumeMm3),
      surfaceAreaMm2: round3(area),
      watertight,
      openEdges: topo.openEdges,
      nonManifoldEdges: topo.nonManifoldEdges,
      inconsistentWinding: topo.inconsistentWinding,
      degenerateTriangles: topo.degenerateTriangles,
      componentCount: topo.componentCount ?? 1,
    })
  }
  const statsMs = performance.now() - statsStart

  return {
    meshCount: meshes.length,
    instanceCount: instances.length,
    missingMeshes,
    meshes,
    totals: { triangleCount: totalTris, volumeMm3: round3(totalVolume), surfaceAreaMm2: round3(totalArea), nonWatertight },
    timings: { loadMs: Math.round(loadMs), statsMs: Math.round(statsMs), totalMs: Math.round(performance.now() - startedAt) },
  }
}

// ---------------------------------------------------------------------------
// bom — bill of materials (per part type)
// ---------------------------------------------------------------------------

export type BomPartType = {
  partType: string
  /** Number of instances of this part type. */
  count: number
  /** Printed parts vs fasteners (fastener meshes are name/path heuristics). */
  isFastener: boolean
  /** Unique mesh ids used by this part type. */
  meshIds: string[]
  /** Enclosed solid volume of ONE unit (mm³), from the topology engine. */
  unitVolumeMm3: number
  /** unitVolumeMm3 × count (mm³). */
  totalVolumeMm3: number
  /** Mass of one unit (g) when a density is supplied, else null. */
  unitMassG: number | null
  /** unitMassG × count (g), or null. */
  totalMassG: number | null
  /** Local bounding-box size of one unit [x,y,z] mm (the printed/physical size). */
  sizeMm: Vec3
  /** False when the volume estimate is unreliable (open / non-watertight mesh). */
  watertight: boolean
}

export type BomReport = {
  partTypeCount: number
  instanceCount: number
  /** Density used for the mass estimate (g/cm³), or null when none was given. */
  densityGCm3: number | null
  missingMeshes: string[]
  /** Part types sorted by total volume descending. */
  parts: BomPartType[]
  totals: {
    volumeMm3: number
    massG: number | null
    printedParts: number
    fastenerParts: number
    printedPartTypes: number
    fastenerPartTypes: number
  }
  timings: { loadMs: number; totalMs: number }
}

// Determinant of a Matrix4's upper-left 3×3 (the linear part); its absolute
// value is the per-instance volume scale factor, so a scaled placement reports
// the right physical volume. Rigid placements (rotation + translation) give 1.
const linearDeterminant = (matrix: THREE.Matrix4) => {
  const e = matrix.elements
  return (
    e[0] * (e[5] * e[10] - e[6] * e[9]) -
    e[4] * (e[1] * e[10] - e[2] * e[9]) +
    e[8] * (e[1] * e[6] - e[2] * e[5])
  )
}

// Per-part-type bill of materials: instance count, total solid volume (from the
// robust topology engine, scaled by each placement's determinant), an optional
// density-based mass estimate, the unit bounding size, and a printed-vs-fastener
// split. Fasteners are INCLUDED by default (they are real BOM line items).
export const billOfMaterials = async (
  manifest: BuildSceneManifest,
  options: GeometryLoadOptions & { densityGCm3?: number },
): Promise<BomReport> => {
  const startedAt = performance.now()
  const loadStart = performance.now()
  const { instances, meshById, missingMeshes } = await buildInstanceGeometries(manifest, {
    ...options,
    includeFasteners: options.includeFasteners ?? true,
  })
  const loadMs = performance.now() - loadStart

  const fastenerMeshIds = new Set(manifest.meshes.filter((mesh) => isFastenerMesh(mesh)).map((mesh) => mesh.id))
  const density = options.densityGCm3 !== undefined && Number.isFinite(options.densityGCm3) && options.densityGCm3 > 0
    ? options.densityGCm3
    : null

  // Cache per-mesh topology (volume + watertightness) so each unique mesh is
  // analyzed once even when referenced by many instances.
  const topoByMesh = new Map<string, { volumeMm3: number; watertight: boolean; size: Vec3 }>()
  const topoFor = (meshId: string) => {
    const cached = topoByMesh.get(meshId)
    if (cached) return cached
    const geom = meshById.get(meshId)
    if (!geom) return null
    const topo = analyzeTopology(geom, false)
    const size = new THREE.Vector3()
    geom.localBox.getSize(size)
    const entry = {
      volumeMm3: topo.volumeMm3,
      watertight: topo.openEdges === 0 && topo.nonManifoldEdges === 0,
      size: [size.x, size.y, size.z] as Vec3,
    }
    topoByMesh.set(meshId, entry)
    return entry
  }

  type Group = {
    partType: string
    isFastener: boolean
    count: number
    meshIds: Set<string>
    totalVolumeMm3: number
    watertight: boolean
    size: Vec3
  }
  const groups = new Map<string, Group>()

  for (const instance of instances) {
    const topo = topoFor(instance.meshId)
    if (!topo) continue
    const scale = Math.abs(linearDeterminant(instance.matrix))
    const unitVolume = topo.volumeMm3 * (Number.isFinite(scale) && scale > 0 ? scale : 1)
    const isFastener = fastenerMeshIds.has(instance.meshId)
    let group = groups.get(instance.partType)
    if (!group) {
      group = {
        partType: instance.partType,
        isFastener,
        count: 0,
        meshIds: new Set<string>(),
        totalVolumeMm3: 0,
        watertight: true,
        size: [0, 0, 0],
      }
      groups.set(instance.partType, group)
    }
    group.count += 1
    group.meshIds.add(instance.meshId)
    group.totalVolumeMm3 += unitVolume
    if (!topo.watertight) group.watertight = false
    // Representative unit size: the largest mesh bounding box for the type.
    const volMag = topo.size[0] * topo.size[1] * topo.size[2]
    const curMag = group.size[0] * group.size[1] * group.size[2]
    if (volMag > curMag) group.size = topo.size
    // A part type seen with both fastener and non-fastener meshes is treated as
    // a fastener line if ANY of its meshes is a fastener.
    group.isFastener = group.isFastener || isFastener
  }

  const parts: BomPartType[] = [...groups.values()]
    .map((group) => {
      const unitVolume = group.count > 0 ? group.totalVolumeMm3 / group.count : 0
      const unitMassG = density !== null ? (unitVolume / 1000) * density : null
      return {
        partType: group.partType,
        count: group.count,
        isFastener: group.isFastener,
        meshIds: [...group.meshIds],
        unitVolumeMm3: round3(unitVolume),
        totalVolumeMm3: round3(group.totalVolumeMm3),
        unitMassG: unitMassG !== null ? round3(unitMassG) : null,
        totalMassG: unitMassG !== null ? round3(unitMassG * group.count) : null,
        sizeMm: roundVec(group.size),
        watertight: group.watertight,
      }
    })
    .sort((a, b) => b.totalVolumeMm3 - a.totalVolumeMm3)

  const totalVolume = parts.reduce((sum, part) => sum + part.totalVolumeMm3, 0)
  const printedParts = parts.filter((part) => !part.isFastener)
  const fastenerParts = parts.filter((part) => part.isFastener)

  return {
    partTypeCount: parts.length,
    instanceCount: instances.length,
    densityGCm3: density,
    missingMeshes,
    parts,
    totals: {
      volumeMm3: round3(totalVolume),
      massG: density !== null ? round3((totalVolume / 1000) * density) : null,
      printedParts: printedParts.reduce((sum, part) => sum + part.count, 0),
      fastenerParts: fastenerParts.reduce((sum, part) => sum + part.count, 0),
      printedPartTypes: printedParts.length,
      fastenerPartTypes: fastenerParts.length,
    },
    timings: { loadMs: Math.round(loadMs), totalMs: Math.round(performance.now() - startedAt) },
  }
}

// ---------------------------------------------------------------------------
// identify — dual world / part-local frame
// ---------------------------------------------------------------------------

export type IdentifyFrame = {
  instanceId: string
  partType: string
  name: string
  meshId: string
  /** The world point expressed in THIS instance's local (part) frame [x,y,z] mm. */
  localPoint: Vec3
  /** True when the world point lies strictly inside this instance's solid. */
  insideSolid: boolean
  /** Distance (mm) from the world point to this instance's surface (0 ⇒ on it). */
  surfaceDistanceMm: number
  /** This instance's mesh bounding box, in the part-local frame. */
  localBounds: { min: Vec3; max: Vec3 }
  /** The instance's local origin (0,0,0) in world coords — i.e. its placement. */
  worldOrigin: Vec3
}

export type IdentifyQuery = {
  /** Identify a world-frame point. */
  worldPoint?: Vec3
  /** Identify a specific instance (its placement, or a point relative to it). */
  instanceId?: string
  /** A part-local point to translate INTO world (requires instanceId). */
  localPoint?: Vec3
}

export type IdentifyReport = {
  mode: 'point' | 'instance' | 'local-point'
  /** The world-frame point that was identified. */
  worldPoint: Vec3
  /** Instances whose local frame the point was expressed in. For a point query:
   *  enclosing instances first, else the single nearest. For an instance query:
   *  just that instance. */
  frames: IdentifyFrame[]
  instanceCount: number
  missingMeshes: string[]
  timings: { loadMs: number; totalMs: number }
}

// Translate between the viewer's world frame and a part's local frame — the
// constant coordinate-translation tax when comparing a viewer pick against
// design_spec / CAD part-local coordinates. Given a world point, report its
// part-local coordinates in every enclosing (or the nearest) instance; given an
// instance (optionally with a part-local point), report the world placement.
export const identify = async (
  manifest: BuildSceneManifest,
  query: IdentifyQuery,
  options: GeometryLoadOptions,
): Promise<IdentifyReport> => {
  const startedAt = performance.now()
  const loadStart = performance.now()
  const { instances, missingMeshes } = await buildInstanceGeometries(manifest, {
    ...options,
    includeFasteners: options.includeFasteners ?? true,
  })
  const loadMs = performance.now() - loadStart

  const local = new THREE.Vector3()
  const frameFor = (instance: InstanceGeometry, world: THREE.Vector3): IdentifyFrame => {
    local.copy(world).applyMatrix4(instance.inverse)
    const localPoint: Vec3 = [local.x, local.y, local.z]
    const insideSolid = pointInside(instance.mesh.bvh, local)
    const hit = instance.mesh.bvh.closestPointToPoint(local, tmpHit)
    const origin = new THREE.Vector3(0, 0, 0).applyMatrix4(instance.matrix)
    const box = instance.mesh.localBox
    return {
      instanceId: instance.instanceId,
      partType: instance.partType,
      name: instance.name,
      meshId: instance.meshId,
      localPoint: roundVec(localPoint),
      insideSolid,
      surfaceDistanceMm: hit ? round3(hit.distance) : 0,
      localBounds: {
        min: roundVec([box.min.x, box.min.y, box.min.z]),
        max: roundVec([box.max.x, box.max.y, box.max.z]),
      },
      worldOrigin: roundVec([origin.x, origin.y, origin.z]),
    }
  }

  // --instance + --local: translate a part-local point into world.
  if (query.instanceId && query.localPoint) {
    const instance = instances.find((entry) => entry.instanceId === query.instanceId)
    if (!instance) throw new Error(`No instance "${query.instanceId}" in this build.`)
    const world = new THREE.Vector3(...query.localPoint).applyMatrix4(instance.matrix)
    return {
      mode: 'local-point',
      worldPoint: roundVec([world.x, world.y, world.z]),
      frames: [frameFor(instance, world)],
      instanceCount: instances.length,
      missingMeshes,
      timings: { loadMs: Math.round(loadMs), totalMs: Math.round(performance.now() - startedAt) },
    }
  }

  // --instance (optionally + a world --point): describe that instance's frame.
  if (query.instanceId) {
    const instance = instances.find((entry) => entry.instanceId === query.instanceId)
    if (!instance) throw new Error(`No instance "${query.instanceId}" in this build.`)
    const world = query.worldPoint
      ? new THREE.Vector3(...query.worldPoint)
      : new THREE.Vector3(0, 0, 0).applyMatrix4(instance.matrix)
    return {
      mode: 'instance',
      worldPoint: roundVec([world.x, world.y, world.z]),
      frames: [frameFor(instance, world)],
      instanceCount: instances.length,
      missingMeshes,
      timings: { loadMs: Math.round(loadMs), totalMs: Math.round(performance.now() - startedAt) },
    }
  }

  // --point: a world point. Express it in every enclosing instance's frame, or
  // (when it is in free space) the single nearest instance's frame.
  if (!query.worldPoint) {
    throw new Error('identify requires --instance <id> or --point x,y,z.')
  }
  const world = new THREE.Vector3(...query.worldPoint)
  const enclosing: InstanceGeometry[] = []
  for (const instance of instances) {
    if (!pointInAabb(instance, world, INTERSECTION_EPSILON)) continue
    local.copy(world).applyMatrix4(instance.inverse)
    if (pointInside(instance.mesh.bvh, local)) enclosing.push(instance)
  }

  let targets = enclosing
  if (targets.length === 0) {
    // Free space: rank by AABB distance, then exact closest-point on the best few.
    const ranked = instances
      .map((instance) => ({ instance, aabb: pointAabbDistance(instance, world) }))
      .sort((a, b) => a.aabb - b.aabb)
      .slice(0, 8)
    let nearest = Infinity
    let nearestInstance: InstanceGeometry | null = null
    for (const { instance, aabb } of ranked) {
      if (aabb > nearest) break
      local.copy(world).applyMatrix4(instance.inverse)
      const hit = instance.mesh.bvh.closestPointToPoint(local, tmpHit)
      if (hit && hit.distance < nearest) {
        nearest = hit.distance
        nearestInstance = instance
      }
    }
    targets = nearestInstance ? [nearestInstance] : []
  }

  return {
    mode: 'point',
    worldPoint: roundVec([world.x, world.y, world.z]),
    frames: targets.map((instance) => frameFor(instance, world)),
    instanceCount: instances.length,
    missingMeshes,
    timings: { loadMs: Math.round(loadMs), totalMs: Math.round(performance.now() - startedAt) },
  }
}
