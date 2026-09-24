import type {
  BuildSceneManifest,
  ChecksConfig,
  CheckStatus,
  OverlapAllowance,
  SceneCheck,
  Vec3,
} from '../core/buildScene'
// Type-only import: erased at runtime, so this module does NOT pull in three.js.
import type { CheckReport, SweepReport } from './buildvizGeometry'

// Project-agnostic check generation + presentation helpers shared by the CLI and
// the viewer. Two families of checks live here:
//   - STATIC (manifest-only, no geometry): scene_meta + placement. Cheap enough
//     to run live the instant a scene loads.
//   - GEOMETRY (derived from a CheckReport produced by buildvizGeometry): mesh
//     overlap, clearance, and connectivity.
// See plans/validation.md.

export const CHECK_STATUS_COLOR: Record<CheckStatus, string> = {
  fail: '#ff3b30',
  warn: '#f59e0b',
  pass: '#22c55e',
}

// Human-friendly display names per check kind for the viewer panel. Unknown
// kinds fall back to their raw id, so new kinds still render without a change.
export const CHECK_KIND_LABEL: Record<string, string> = {
  mesh_overlap: 'overlap',
  clearance: 'clearance',
  placement: 'placement',
  scene_meta: 'manifest',
  connectivity: 'connectivity',
  declared_interference: 'declared interference',
  watertight: 'watertight',
  wall_thickness: 'wall thickness',
  degenerate_geometry: 'degenerate',
  self_intersection: 'self-intersection',
  disconnected_components: 'disconnected body',
  thread_engagement: 'thread engagement',
  assembly_access: 'assembly access',
  mating_contact: 'mating contact',
  routing_reach: 'routing reach',
  wire_bend_radius: 'wire bend radius',
  wire_support: 'wire support',
  wire_clearance: 'wire clearance',
  swept_overlap: 'swept overlap',
  swept_clearance: 'swept clearance',
}

export const checkKindLabel = (kind: string) => CHECK_KIND_LABEL[kind] ?? kind

const STATUS_SEVERITY: Record<CheckStatus, number> = { pass: 0, warn: 1, fail: 2 }

export type CheckHighlightPart = { instanceId: string; color: string; annotation: string }
export type CheckHighlightPoint = {
  point: Vec3
  instanceId?: string
  color: string
  annotation: string
}
export type CheckHighlightRegion = {
  min: Vec3
  max: Vec3
  color: string
  annotation: string
}
export type CheckHighlights = {
  parts: CheckHighlightPart[]
  points: CheckHighlightPoint[]
  regions: CheckHighlightRegion[]
}

export type CheckSummary = {
  total: number
  pass: number
  warn: number
  fail: number
  byKind: Record<string, { pass: number; warn: number; fail: number }>
}

const VALID_UNITS = new Set(['mm', 'cm', 'm'])

const finiteNumbers = (transform: number[]) =>
  Array.isArray(transform) &&
  transform.length === 16 &&
  transform.every((value) => typeof value === 'number' && Number.isFinite(value))

// Determinant of the 3x3 linear part of a column-major 4x4 transform. ~0 means a
// degenerate (collapsed/mirrored-to-zero) placement, a classic broken transform.
const linearDeterminant = (t: number[]) => {
  const a = t[0]
  const b = t[1]
  const c = t[2]
  const d = t[4]
  const e = t[5]
  const f = t[6]
  const g = t[8]
  const h = t[9]
  const i = t[10]
  return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
}

// Manifest hygiene: units present + valid, every instance resolves to a mesh, no
// duplicate instance ids. Each rule emits one pass/fail record.
export const sceneMetaChecks = (manifest: BuildSceneManifest): SceneCheck[] => {
  const checks: SceneCheck[] = []

  const unitsValid = VALID_UNITS.has(manifest.units as string)
  checks.push({
    id: 'scene_meta-units',
    kind: 'scene_meta',
    status: unitsValid ? 'pass' : 'fail',
    label: unitsValid ? `units = ${manifest.units}` : `invalid or missing units: ${String(manifest.units)}`,
  })

  const meshIds = new Set(manifest.meshes.map((mesh) => mesh.id))
  const dangling = manifest.instances.filter((instance) => !meshIds.has(instance.meshId))
  checks.push({
    id: 'scene_meta-mesh-refs',
    kind: 'scene_meta',
    status: dangling.length === 0 ? 'pass' : 'fail',
    label:
      dangling.length === 0
        ? `all ${manifest.instances.length} instances resolve to a mesh`
        : `${dangling.length} instance(s) reference a missing mesh`,
    instances: dangling.length > 0 ? dangling.map((instance) => instance.id) : undefined,
  })

  const seen = new Set<string>()
  const duplicates = new Set<string>()
  for (const instance of manifest.instances) {
    if (seen.has(instance.id)) duplicates.add(instance.id)
    seen.add(instance.id)
  }
  checks.push({
    id: 'scene_meta-unique-ids',
    kind: 'scene_meta',
    status: duplicates.size === 0 ? 'pass' : 'fail',
    label:
      duplicates.size === 0
        ? 'instance ids are unique'
        : `${duplicates.size} duplicate instance id(s)`,
    instances: duplicates.size > 0 ? [...duplicates] : undefined,
  })

  // Legacy escape hatch in use: ignoreOverlapPairs suppresses EVERY collision
  // between two partTypes — including physically impossible ones — so warn
  // loudly on every run until the pairs are migrated to typed instance-level
  // allowedInterferences entries.
  const legacyPairs = manifest.checksConfig?.ignoreOverlapPairs ?? []
  if (legacyPairs.length > 0) {
    const preview = legacyPairs
      .slice(0, 3)
      .map(([a, b]) => `${a}/${b}`)
      .join(', ')
    checks.push({
      id: 'scene_meta-legacy-ignore-overlap-pairs',
      kind: 'scene_meta',
      status: 'warn',
      label:
        `checksConfig.ignoreOverlapPairs blanket-ignores ${legacyPairs.length} partType pair(s) ` +
        `(${preview}${legacyPairs.length > 3 ? ', …' : ''}) — every overlap between those types is ` +
        `suppressed, even unintended ones. Migrate to typed instance-level ` +
        `checksConfig.allowedInterferences entries (kind + reason + maxPenetrationMm).`,
    })
  }

  return checks
}

// Per-instance placement sanity. Deliberately conservative: only genuinely broken
// placement is flagged (non-finite / degenerate transform, or an implausibly far
// translation), never the legitimately-distal extremities of a large assembly.
const FAR_TRANSLATION_MM = 100_000

export const placementChecks = (manifest: BuildSceneManifest): SceneCheck[] => {
  const broken: string[] = []
  const far: string[] = []

  for (const instance of manifest.instances) {
    if (!finiteNumbers(instance.transform) || Math.abs(linearDeterminant(instance.transform)) < 1e-9) {
      broken.push(instance.id)
      continue
    }
    const [x, y, z] = [instance.transform[12], instance.transform[13], instance.transform[14]]
    if (Math.hypot(x, y, z) > FAR_TRANSLATION_MM) far.push(instance.id)
  }

  const checks: SceneCheck[] = [
    {
      id: 'placement-transforms',
      kind: 'placement',
      status: broken.length === 0 ? 'pass' : 'fail',
      label:
        broken.length === 0
          ? 'all transforms are well-formed'
          : `${broken.length} broken/degenerate transform(s)`,
      instances: broken.length > 0 ? broken : undefined,
    },
  ]
  if (far.length > 0) {
    checks.push({
      id: 'placement-far',
      kind: 'placement',
      status: 'warn',
      label: `${far.length} instance(s) placed implausibly far (possible lost transform)`,
      instances: far,
    })
  }
  return checks
}

export const staticChecks = (manifest: BuildSceneManifest): SceneCheck[] => [
  ...sceneMetaChecks(manifest),
  ...placementChecks(manifest),
]

// Human-readable qualifier for an overlap's allowance decision: how it was
// allowed (typed entry vs legacy blanket), or why a matching allowance was
// refused. Empty for plain unexpected overlaps.
const allowanceSuffix = (allowed: boolean, allowance?: OverlapAllowance): string => {
  if (allowed) {
    if (allowance?.source === 'declared') {
      return ` (allowed: ${allowance.kind} — ${allowance.reason})`
    }
    return ' (intentional — legacy checksConfig.ignoreOverlapPairs; migrate to allowedInterferences)'
  }
  if (allowance?.refusal === 'relative_motion') {
    return (
      ' — listed in ignoreOverlapPairs, but these parts move relative to each other (joints[]);' +
      ' blanket partType ignores never apply to moving bodies. Join them with a real' +
      ' fastener/pin/bearing (a declared allowedInterferences entry) or fix the interference.'
    )
  }
  if (allowance?.refusal === 'max_penetration_exceeded') {
    return ` — exceeds the declared allowedInterferences cap (maxPenetrationMm ${allowance.maxPenetrationMm})`
  }
  return ''
}

// Convert a geometry CheckReport into generic check records. Allowance intent
// (typed checksConfig.allowedInterferences + the legacy ignoreOverlapPairs
// blanket) is resolved by the engine per instance pair; allowed interferences
// become pass records so they stay visible/auditable in the panel without
// counting as failures.
export const geometryChecks = (
  report: CheckReport,
  config?: ChecksConfig,
): SceneCheck[] => {
  const checks: SceneCheck[] = []

  report.collisions.forEach((collision, index) => {
    const allowed = collision.allowed === true
    checks.push({
      id: `mesh_overlap-${index}`,
      kind: 'mesh_overlap',
      status: allowed ? 'pass' : 'fail',
      label:
        `${collision.a.partType} \u2229 ${collision.b.partType} = ${collision.penetrationMm}mm penetration` +
        allowanceSuffix(allowed, collision.allowance),
      instances: [collision.a.instanceId, collision.b.instanceId],
      // Localized overlap anchors so the viewer shades just the interpenetrating
      // volume (a small region box + contact point), not the whole parts.
      point: collision.point ?? undefined,
      region: collision.region ?? undefined,
    })
  })

  // Audit of each declared allowedInterferences entry: present-and-within-cap
  // (or at least in contact) passes; stale, dangling, or over-cap entries fail
  // so the allowlist itself stays trustworthy.
  ;(report.declaredInterferences ?? []).forEach((declared, index) => {
    const pair = `${declared.instances[0]} \u2229 ${declared.instances[1]}`
    const feature = declared.feature ? ` [${declared.feature}]` : ''
    let status: CheckStatus = 'pass'
    let detail: string
    switch (declared.outcome) {
      case 'overlapping':
        detail =
          `interference present, ${declared.penetrationMm}mm` +
          (declared.maxPenetrationMm !== null ? ` (≤ ${declared.maxPenetrationMm}mm cap)` : '')
        break
      case 'in_contact':
        detail = `in contact (gap ${declared.gapMm}mm), no measurable interference`
        break
      case 'exceeds_max_penetration':
        status = 'fail'
        detail = `${declared.penetrationMm}mm penetration exceeds the declared ${declared.maxPenetrationMm}mm cap`
        break
      case 'not_in_contact':
        status = 'fail'
        detail =
          `declared interference NOT present — parts are ` +
          (declared.gapMm !== null ? `${declared.gapMm}mm apart` : 'far apart') +
          ' (stale allowlist entry, or a part drifted)'
        break
      case 'unknown_instance':
        status = 'fail'
        detail = 'references instance id(s) not in the scene (or with unloadable meshes)'
        break
    }
    checks.push({
      id: `declared_interference-${index}`,
      kind: 'declared_interference',
      status,
      label: `${pair} (${declared.kind}${feature}): ${detail} — ${declared.reason}`,
      instances: declared.instances.filter(Boolean),
      point: declared.point ?? undefined,
      region: status === 'fail' ? (declared.region ?? undefined) : undefined,
    })
  })

  report.gaps.forEach((gap, index) => {
    checks.push({
      id: `clearance-${index}`,
      kind: 'clearance',
      status: 'warn',
      label: `${gap.partType} \u2194 ${gap.nearestInstanceId} gap ${gap.gapMm}mm`,
      instances: [gap.instanceId, gap.nearestInstanceId],
    })
  })

  report.floating.forEach((floating, index) => {
    const gap = floating.nearestGapMm !== null ? `, nearest ${floating.nearestGapMm}mm` : ''
    checks.push({
      id: `connectivity-${index}`,
      kind: 'connectivity',
      status: 'warn',
      label: `${floating.partType} floating / not connected to main assembly${gap}`,
      instances: [floating.instanceId],
    })
  })

  // --- Printability (per unique mesh) ---
  // `watertight`/`degenerate_geometry` are ROBUST (exact edge adjacency);
  // `wall_thickness` is a HEURISTIC inward-ray estimate (warn, never fail).
  const minWallMm = config?.minWallMm ?? report.minWallMm
  report.printability.forEach((mesh, index) => {
    if (mesh.openEdges !== null && mesh.nonManifoldEdges !== null) {
      const broken = mesh.openEdges > 0 || mesh.nonManifoldEdges > 0
      const status: CheckStatus = broken ? 'fail' : mesh.inconsistentWinding ? 'warn' : 'pass'
      const detail = broken
        ? `${mesh.openEdges} open + ${mesh.nonManifoldEdges} non-manifold edge(s)`
        : mesh.inconsistentWinding
          ? 'inconsistent winding'
          : 'watertight & manifold'
      checks.push({
        id: `watertight-${index}`,
        kind: 'watertight',
        status,
        label: `${mesh.meshName}: ${detail}`,
        instances: mesh.instanceIds,
        point: mesh.thinPoint ?? undefined,
      })
      if (mesh.degenerateTriangles !== null && mesh.degenerateTriangles > 0) {
        checks.push({
          id: `degenerate_geometry-${index}`,
          kind: 'degenerate_geometry',
          status: 'warn',
          label: `${mesh.meshName}: ${mesh.degenerateTriangles} degenerate (zero-area) triangle(s)`,
          instances: mesh.instanceIds,
        })
      }
    }
    // Self-intersection (ROBUST triangle-triangle): a slicer-breaking fault.
    // Any genuine self-intersection fails; null = pass (not run / mesh too big).
    if (mesh.selfIntersections !== null && mesh.selfIntersections > 0) {
      checks.push({
        id: `self_intersection-${index}`,
        kind: 'self_intersection',
        status: 'fail',
        label: `${mesh.meshName}: ${mesh.selfIntersections} self-intersecting triangle pair(s)`,
        instances: mesh.instanceIds,
        point: mesh.selfIntersectionPoint ?? undefined,
      })
    }
    // Disconnected components (ROBUST): a single printed mesh that is actually
    // >1 disjoint welded-vertex body (a floating island / detached ring). An
    // INTRA-mesh fault, distinct from the inter-part `connectivity` check above.
    // Intent as DATA: a legitimately multi-body mesh declares its expected count.
    if (mesh.componentCount !== null) {
      const expected =
        config?.expectedMeshComponents?.[mesh.meshId] ?? config?.maxMeshComponents ?? 1
      const broken = mesh.componentCount > expected
      const island = mesh.smallestComponent
        ? ` (stray island ≈ ${mesh.smallestComponent.volumeMm3}mm³)`
        : ''
      checks.push({
        id: `disconnected_components-${index}`,
        kind: 'disconnected_components',
        status: broken ? 'fail' : 'pass',
        label: broken
          ? `${mesh.meshName}: ${mesh.componentCount} disconnected bodies${island}`
          : mesh.componentCount > 1
            ? `${mesh.meshName}: ${mesh.componentCount} bodies (expected ${expected})`
            : `${mesh.meshName}: single connected body`,
        instances: mesh.instanceIds,
        point: broken ? (mesh.smallestComponent?.point ?? undefined) : undefined,
      })
    }
    if (mesh.minWallMm !== null) {
      const thin = mesh.minWallMm < minWallMm
      checks.push({
        id: `wall_thickness-${index}`,
        kind: 'wall_thickness',
        status: thin ? 'warn' : 'pass',
        label:
          `${mesh.meshName}: min wall ≈ ${mesh.minWallMm}mm` +
          (thin ? ` (< ${minWallMm}mm, est.)` : ' (est.)'),
        instances: mesh.instanceIds,
        point: thin ? (mesh.thinPoint ?? undefined) : undefined,
      })
    }
  })

  // --- Assembleability ---
  // Both HEURISTIC. To avoid flooding, only the problems are emitted as records
  // (under-engaged fasteners / parts with no clear extraction direction); the
  // CLI prints how many were checked overall.
  const minThreadMm = config?.minThreadEngagementMm ?? report.minThreadEngagementMm
  checks.push(...(report.fasteningChecks ?? []))
  report.fasteners.forEach((fastener, index) => {
    if (fastener.engagementMm >= minThreadMm) return
    const into = fastener.hostInstanceIds.length > 0 ? '' : ' — not seated in any part'
    checks.push({
      id: `thread_engagement-${index}`,
      kind: 'thread_engagement',
      status: 'warn',
      label:
        `${fastener.partType}: engagement ≈ ${fastener.engagementMm}mm of ${fastener.shaftLengthMm}mm ` +
        `(< ${minThreadMm}mm, est.)${into}`,
      instances: [fastener.instanceId, ...fastener.hostInstanceIds],
      point: fastener.point ?? undefined,
    })
  })

  report.access.forEach((part, index) => {
    if (part.clearDirections > 0) return
    checks.push({
      id: `assembly_access-${index}`,
      kind: 'assembly_access',
      status: 'warn',
      label: `${part.partType}: no collision-free straight-line extraction (${part.directionsTried} dirs tried, est.)`,
      instances: [part.instanceId],
      point: part.point ?? undefined,
    })
  })

  // --- Mating-face contact (ROBUST surface metric) ---
  // A mating pair should touch (gap ~0) within the tolerance. Floating apart
  // (gap > tol) or interpenetrating beyond tol (crash) FAILS; in-contact PASSES.
  // Declared pairs (ignoreOverlapPairs) always emit a record; likely (near-
  // touching) pairs only ever reach here as in-tolerance contacts, so they pass.
  const matingTol = config?.matingToleranceMm ?? report.matingToleranceMm
  report.mating.forEach((mate, index) => {
    const crash = mate.penetrationMm > matingTol
    const floating = mate.penetrationMm === 0 && mate.gapMm > matingTol
    const status: CheckStatus = crash || floating ? 'fail' : 'pass'
    const tag = mate.declared ? 'declared' : 'likely'
    const detail = crash
      ? `interpenetrating ${mate.penetrationMm}mm (crash, > ${matingTol}mm)`
      : floating
        ? `floating, gap ${mate.gapMm}mm (> ${matingTol}mm)`
        : mate.penetrationMm > 0
          ? `seated, contact ${mate.penetrationMm}mm`
          : `in contact, gap ${mate.gapMm}mm`
    checks.push({
      id: `mating_contact-${index}`,
      kind: 'mating_contact',
      status,
      label: `${mate.a.partType} ⟷ ${mate.b.partType} (${tag} mate): ${detail}`,
      instances: [mate.a.instanceId, mate.b.instanceId],
      point: mate.point ?? undefined,
      region: status === 'fail' ? (mate.region ?? undefined) : undefined,
    })
  })

  // --- Routing reach ---
  // A route fails when it overruns its length budget or passes through a solid.
  report.routing.forEach((route, index) => {
    const overBudget = route.maxLengthMm !== null && route.lengthMm > route.maxLengthMm
    const blocked = route.blockingInstanceIds.length > 0
    const status: CheckStatus = overBudget || blocked ? 'fail' : 'pass'
    const reasons: string[] = []
    if (overBudget) reasons.push(`length ${route.lengthMm}mm > ${route.maxLengthMm}mm budget`)
    if (blocked) reasons.push(`passes through ${route.blockingInstanceIds.length} solid(s)`)
    if (route.missingInstances.length > 0) {
      reasons.push(`waypoint instance(s) missing from the scene: ${route.missingInstances.join(', ')}`)
    }
    if (reasons.length === 0) {
      reasons.push(
        `length ${route.lengthMm}mm` + (route.maxLengthMm !== null ? ` (≤ ${route.maxLengthMm}mm)` : '') + ', clear',
      )
    }
    checks.push({
      id: `routing_reach-${index}`,
      kind: 'routing_reach',
      status: route.missingInstances.length > 0 && status === 'pass' ? 'warn' : status,
      label: `${route.label}: ${reasons.join('; ')} (est.)`,
      instances: route.blockingInstanceIds,
      point: route.point ?? undefined,
    })
  })

  // --- Wire bend radius ---
  // Fails when the tightest sampled bend is below the allowed minimum
  // (explicit minBendRadiusMm, else 6 × bundle OD). Unchecked (no record) when
  // neither is known — there is no rule to enforce.
  report.routing.forEach((route, index) => {
    if (route.minBendRadiusAllowedMm === null) return
    const measured = route.minBendRadiusMm
    const tooTight = measured !== null && measured < route.minBendRadiusAllowedMm
    checks.push({
      id: `wire_bend_radius-${index}`,
      kind: 'wire_bend_radius',
      status: tooTight ? 'fail' : 'pass',
      label: tooTight
        ? `${route.label}: bend radius ${measured}mm < ${route.minBendRadiusAllowedMm}mm minimum — ` +
          'ease the bend (move/add a waypoint or reroute around the corner)'
        : `${route.label}: tightest bend ${measured === null ? 'straight' : `${measured}mm`} ` +
          `(≥ ${route.minBendRadiusAllowedMm}mm)`,
      point: tooTight ? (route.bendPoint ?? undefined) : undefined,
    })
  })

  // --- Wire support (attachment spacing) ---
  // Warns when the longest span between anchored points exceeds the allowed
  // maximum — the "add a clip/tie here" nudge, anchored at the span midpoint.
  report.routing.forEach((route, index) => {
    if (route.maxUnsupportedMm === null) return
    const over = route.maxUnsupportedMm > route.maxUnsupportedAllowedMm
    checks.push({
      id: `wire_support-${index}`,
      kind: 'wire_support',
      status: over ? 'warn' : 'pass',
      label: over
        ? `${route.label}: ${route.maxUnsupportedMm}mm unsupported span > ${route.maxUnsupportedAllowedMm}mm — ` +
          'add a clip/tie waypoint (anchor: true) near the highlighted midpoint ' +
          `(${route.anchorCount} anchor(s) now)`
        : `${route.label}: longest unsupported span ${route.maxUnsupportedMm}mm ` +
          `(≤ ${route.maxUnsupportedAllowedMm}mm, ${route.anchorCount} anchor(s))`,
      point: over ? (route.spanPoint ?? undefined) : undefined,
    })
  })

  // --- Wire clearance (chafing) ---
  // Warns when the wire surface passes closer than the clearance threshold to
  // a solid it does not terminate at (route through a grommet/standoff, or move
  // the path). Pass-throughs are already fails under routing_reach.
  report.routing.forEach((route, index) => {
    if (route.clearanceMm === null || route.clearanceInstanceId === null) return
    checks.push({
      id: `wire_clearance-${index}`,
      kind: 'wire_clearance',
      status: 'warn',
      label:
        `${route.label}: passes ${route.clearanceMm}mm from ${route.clearanceInstanceId} — ` +
        'chafing risk; reroute or protect (grommet/edge guard)',
      instances: [route.clearanceInstanceId],
      point: route.clearancePoint ?? undefined,
    })
  })

  return checks
}

// Convert a swept-pose SweepReport (Phase 3) into generic check records. Each
// reported instance pair becomes a `swept_overlap` (worst-case interpenetration
// over the motion range) or `swept_clearance` (closest approach), labeled with
// the pose at which the worst case occurred. The localized overlap anchors paint
// through the same region/point highlight channel as static overlaps, so the
// viewer shades the worst-case contact volume in place.
export const sweptChecks = (report: SweepReport): SceneCheck[] => {
  const checks: SceneCheck[] = []
  report.pairs.forEach((pair, index) => {
    if (pair.kind === 'overlap') {
      const allowed = pair.allowed === true
      checks.push({
        id: `swept_overlap-${index}`,
        kind: 'swept_overlap',
        status: allowed ? 'pass' : 'fail',
        label:
          `${pair.a.partType} \u2229 ${pair.b.partType} = ${pair.maxPenetrationMm}mm worst penetration ` +
          `@ ${pair.worstLabel}` +
          allowanceSuffix(allowed, pair.allowance),
        instances: [pair.a.instanceId, pair.b.instanceId],
        point: pair.point ?? undefined,
        region: pair.region ?? undefined,
      })
    } else {
      checks.push({
        id: `swept_clearance-${index}`,
        kind: 'swept_clearance',
        status: 'warn',
        label:
          `${pair.a.partType} \u2194 ${pair.b.partType} closest ${pair.minClearanceMm}mm ` +
          `@ ${pair.worstLabel}`,
        instances: [pair.a.instanceId, pair.b.instanceId],
      })
    }
  })
  return checks
}

// Build a highlight payload for the existing window.buildviz.setHighlights API.
// Only warn/fail records highlight; the most severe status per instance wins.
export const checksToHighlights = (checks: SceneCheck[]): CheckHighlights => {
  const parts = new Map<string, CheckHighlightPart>()
  const points: CheckHighlightPoint[] = []
  const regions: CheckHighlightRegion[] = []

  for (const check of checks) {
    if (check.status === 'pass') continue
    const color = CHECK_STATUS_COLOR[check.status]
    for (const instanceId of check.instances ?? []) {
      const existing = parts.get(instanceId)
      if (
        !existing ||
        STATUS_SEVERITY[check.status] >
          (existing.color === CHECK_STATUS_COLOR.fail ? STATUS_SEVERITY.fail : STATUS_SEVERITY.warn)
      ) {
        parts.set(instanceId, { instanceId, color, annotation: check.label })
      }
    }
    // A localized region (e.g. the interpenetrating volume of an overlap) is
    // shaded in place by the viewer. Anchor the contact point at the region
    // centre when a region is present so the marker sits inside the overlap.
    if (check.region) {
      regions.push({
        min: check.region.min,
        max: check.region.max,
        color,
        annotation: check.label,
      })
    }
    if (check.point) {
      points.push({
        point: check.point,
        // World-space anchors (overlap points) must not be re-transformed by an
        // instance matrix, so deliberately leave instanceId unset for them.
        instanceId: check.region ? undefined : check.instances?.[0],
        color,
        annotation: check.label,
      })
    }
  }

  return { parts: [...parts.values()], points, regions }
}

export const summarizeChecks = (checks: SceneCheck[]): CheckSummary => {
  const summary: CheckSummary = { total: checks.length, pass: 0, warn: 0, fail: 0, byKind: {} }
  for (const check of checks) {
    summary[check.status] += 1
    const kind = (summary.byKind[check.kind] ??= { pass: 0, warn: 0, fail: 0 })
    kind[check.status] += 1
  }
  return summary
}
