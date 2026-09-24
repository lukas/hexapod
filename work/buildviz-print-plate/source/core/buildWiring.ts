// Wire/cable route math (plans/wiring.md). Pure, three-free functions shared
// by the checks engine, the `buildviz wires` CLI command, and the viewer, so
// every consumer measures the SAME curve: control points are resolved from the
// route's waypoints (world or instance-anchored), then densified with a
// centripetal Catmull-Rom spline — the same family of curve the viewer draws.

import type { BuildSceneManifest, Route, RoutePoint, Vec3 } from './buildScene'

/** Default minimum bend radius multiplier: 6 × bundle OD (IPC/WHMA-A-620 static). */
export const DEFAULT_BEND_RADIUS_MULTIPLIER = 6
/** Default longest allowed unsupported span between anchors (mm). */
export const DEFAULT_MAX_UNSUPPORTED_MM = 150
/** Default wire-to-solid clearance (mm) below which `wire_clearance` warns. */
export const DEFAULT_WIRE_CLEARANCE_MM = 1

export type ResolvedRoute = {
  /** World-frame control points, in path order. */
  points: Vec3[]
  /** Whether each control point is a physical attachment (endpoints always are). */
  anchors: boolean[]
  /** Termination instance ids (route.instances + instance-anchored waypoints). */
  instances: string[]
  /** Waypoints that referenced an instance id missing from the scene. */
  missingInstances: string[]
}

// Apply a column-major 4x4 transform (the scene's instance format) to a point.
const applyTransform = (m: number[], p: Vec3): Vec3 => [
  m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12],
  m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13],
  m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14],
]

/**
 * Resolve a route's path to world-frame control points. `waypoints` wins over
 * the legacy `points` polyline; instance-anchored waypoints are transformed by
 * the instance's base transform (or a posed override from forward kinematics,
 * passed as column-major 16-float arrays keyed by instance id). Legacy world
 * `points` are treated as endpoints-anchored only.
 */
export const resolveRoute = (
  manifest: BuildSceneManifest,
  route: Route,
  poseOverrides?: Record<string, number[]>,
): ResolvedRoute => {
  const instanceById = new Map(manifest.instances.map((instance) => [instance.id, instance]))
  const terminations = new Set(route.instances ?? [])
  const missingInstances: string[] = []

  const waypoints = route.waypoints ?? []
  if (waypoints.length === 0) {
    const points = (route.points ?? []).map((p): Vec3 => [p[0], p[1], p[2]])
    return {
      points,
      anchors: points.map((_, index) => index === 0 || index === points.length - 1),
      instances: [...terminations],
      missingInstances,
    }
  }

  const points: Vec3[] = []
  const anchors: boolean[] = []
  waypoints.forEach((waypoint: RoutePoint, index) => {
    let world: Vec3 | null = null
    if (waypoint.instanceId) {
      const instance = instanceById.get(waypoint.instanceId)
      if (!instance) {
        missingInstances.push(waypoint.instanceId)
        world = waypoint.position ? [...waypoint.position] : null
      } else {
        terminations.add(waypoint.instanceId)
        const matrix = poseOverrides?.[waypoint.instanceId] ?? instance.transform
        world = applyTransform(matrix, waypoint.local ?? [0, 0, 0])
      }
    } else if (waypoint.position) {
      world = [...waypoint.position]
    }
    if (!world) return
    points.push(world)
    anchors.push(
      waypoint.anchor === true ||
        waypoint.instanceId !== undefined ||
        index === 0 ||
        index === waypoints.length - 1,
    )
  })

  return { points, anchors, instances: [...terminations], missingInstances }
}

export type SampledRoute = {
  /** Dense polyline through the control points. */
  samples: Vec3[]
  /** Index into `samples` of each control point (control i = samples[controlIndex[i]]). */
  controlIndex: number[]
}

const distance = (a: Vec3, b: Vec3) =>
  Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2])

// Centripetal Catmull-Rom interpolation of one span (p1 → p2 with p0/p3 as
// neighbors). Centripetal parameterization avoids the loops/overshoot the
// uniform variant produces on unevenly spaced control points.
const catmullRomSpan = (p0: Vec3, p1: Vec3, p2: Vec3, p3: Vec3, segments: number): Vec3[] => {
  const alpha = 0.5
  const knot = (ti: number, a: Vec3, b: Vec3) => ti + Math.max(distance(a, b), 1e-9) ** alpha
  const t0 = 0
  const t1 = knot(t0, p0, p1)
  const t2 = knot(t1, p1, p2)
  const t3 = knot(t2, p2, p3)

  const lerp = (a: Vec3, b: Vec3, ta: number, tb: number, t: number): Vec3 => {
    const w = tb - ta <= 1e-12 ? 0 : (t - ta) / (tb - ta)
    return [
      a[0] + (b[0] - a[0]) * w,
      a[1] + (b[1] - a[1]) * w,
      a[2] + (b[2] - a[2]) * w,
    ]
  }

  const out: Vec3[] = []
  for (let i = 1; i <= segments; i += 1) {
    const t = t1 + ((t2 - t1) * i) / segments
    const a1 = lerp(p0, p1, t0, t1, t)
    const a2 = lerp(p1, p2, t1, t2, t)
    const a3 = lerp(p2, p3, t2, t3, t)
    const b1 = lerp(a1, a2, t0, t2, t)
    const b2 = lerp(a2, a3, t1, t3, t)
    out.push(lerp(b1, b2, t1, t2, t))
  }
  return out
}

/**
 * Densify the control polyline with a centripetal Catmull-Rom spline
 * (`segmentsPerSpan` samples per control span; endpoints use mirrored phantom
 * neighbors). Returns the dense samples plus each control point's index into
 * them, so span measurements (anchor-to-anchor arc length) stay exact.
 */
export const sampleRoute = (points: Vec3[], segmentsPerSpan = 8): SampledRoute => {
  if (points.length < 2) {
    return { samples: [...points], controlIndex: points.map((_, i) => i) }
  }
  if (points.length === 2) {
    const samples: Vec3[] = [points[0]]
    for (let i = 1; i <= segmentsPerSpan; i += 1) {
      const t = i / segmentsPerSpan
      samples.push([
        points[0][0] + (points[1][0] - points[0][0]) * t,
        points[0][1] + (points[1][1] - points[0][1]) * t,
        points[0][2] + (points[1][2] - points[0][2]) * t,
      ])
    }
    return { samples, controlIndex: [0, samples.length - 1] }
  }

  const mirror = (a: Vec3, b: Vec3): Vec3 => [2 * a[0] - b[0], 2 * a[1] - b[1], 2 * a[2] - b[2]]
  const samples: Vec3[] = [points[0]]
  const controlIndex: number[] = [0]
  for (let i = 0; i < points.length - 1; i += 1) {
    const p0 = i === 0 ? mirror(points[0], points[1]) : points[i - 1]
    const p3 = i === points.length - 2 ? mirror(points[i + 1], points[i]) : points[i + 2]
    samples.push(...catmullRomSpan(p0, points[i], points[i + 1], p3, segmentsPerSpan))
    controlIndex.push(samples.length - 1)
  }
  return { samples, controlIndex }
}

export const polylineLength = (points: Vec3[]): number => {
  let length = 0
  for (let i = 0; i < points.length - 1; i += 1) length += distance(points[i], points[i + 1])
  return length
}

export type BendRadiusResult = { radiusMm: number; point: Vec3 }

/**
 * Tightest bend along the sampled curve: the minimum circumradius over
 * consecutive sample triples. Near-collinear triples (radius beyond 10m) are
 * treated as straight and skipped. Null for paths with fewer than 3 samples
 * or fully straight runs.
 */
export const minBendRadius = (samples: Vec3[]): BendRadiusResult | null => {
  let best: BendRadiusResult | null = null
  for (let i = 1; i < samples.length - 1; i += 1) {
    const a = distance(samples[i - 1], samples[i])
    const b = distance(samples[i], samples[i + 1])
    const c = distance(samples[i - 1], samples[i + 1])
    if (a < 1e-9 || b < 1e-9 || c < 1e-9) continue
    // Circumradius R = abc / (4 * area), via Heron's formula.
    const s = (a + b + c) / 2
    const areaSq = s * (s - a) * (s - b) * (s - c)
    if (areaSq <= 1e-12) continue
    const radius = (a * b * c) / (4 * Math.sqrt(areaSq))
    if (radius > 10_000) continue
    if (!best || radius < best.radiusMm) best = { radiusMm: radius, point: samples[i] }
  }
  return best
}

export type UnsupportedSpan = {
  /** Arc length (mm) along the curve between two consecutive anchors. */
  lengthMm: number
  /** Curve midpoint of the span — where a clip/tie would help. */
  midpoint: Vec3
}

/**
 * Arc length between consecutive ANCHORED control points, measured along the
 * sampled curve. The longest span is what `wire_support` compares against the
 * allowed maximum; its midpoint is the natural "add a clip here" suggestion.
 */
export const unsupportedSpans = (
  anchors: boolean[],
  sampled: SampledRoute,
): UnsupportedSpan[] => {
  const anchorSampleIndices = anchors
    .map((isAnchor, control) => (isAnchor ? sampled.controlIndex[control] : -1))
    .filter((index) => index >= 0)
  const spans: UnsupportedSpan[] = []
  for (let i = 0; i < anchorSampleIndices.length - 1; i += 1) {
    const from = anchorSampleIndices[i]
    const to = anchorSampleIndices[i + 1]
    let lengthMm = 0
    for (let j = from; j < to; j += 1) lengthMm += distance(sampled.samples[j], sampled.samples[j + 1])
    // Walk back to the arc-length midpoint for the suggestion anchor.
    let walked = 0
    let midpoint = sampled.samples[from]
    for (let j = from; j < to; j += 1) {
      walked += distance(sampled.samples[j], sampled.samples[j + 1])
      if (walked >= lengthMm / 2) {
        midpoint = sampled.samples[j + 1]
        break
      }
    }
    spans.push({ lengthMm, midpoint })
  }
  return spans
}

/** Allowed minimum bend radius: explicit, else 6 × OD, else null (unchecked). */
export const effectiveMinBendRadiusMm = (route: Route): number | null => {
  if (typeof route.minBendRadiusMm === 'number') return route.minBendRadiusMm
  if (typeof route.diameterMm === 'number' && route.diameterMm > 0) {
    return DEFAULT_BEND_RADIUS_MULTIPLIER * route.diameterMm
  }
  return null
}

/** Display color for a route: explicit `color`, else a per-kind default. */
export const routeDisplayColor = (route: Route): string => {
  if (route.color) return route.color
  switch (route.kind) {
    case 'power':
      return '#dc2626'
    case 'ground':
      return '#1f2937'
    case 'signal':
      return '#2563eb'
    case 'data':
      return '#16a34a'
    default:
      return '#d97706'
  }
}
