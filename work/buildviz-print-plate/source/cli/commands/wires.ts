import {
  effectiveMinBendRadiusMm,
  minBendRadius,
  polylineLength,
  resolveRoute,
  routeDisplayColor,
  sampleRoute,
  unsupportedSpans,
  DEFAULT_MAX_UNSUPPORTED_MM,
} from '../../core/buildWiring'
import { loadBuild, apiEnvelope } from '../cliBuild'

// `buildviz wires` — fast, geometry-free wiring summary (plans/wiring.md).
// Resolves and samples each routes[] entry with the SAME curve the viewer
// draws and the checks measure, and reports per wire: kind, diameter, routed
// length (vs budget), tightest bend radius (vs allowed), anchors, longest
// unsupported span (vs allowed), and endpoints. Obstruction/clearance need
// mesh geometry and stay in `buildviz check` (wire_* kinds).

export type WireSummary = {
  id: string
  label: string
  kind: string | null
  color: string
  diameterMm: number | null
  lengthMm: number
  maxLengthMm: number | null
  minBendRadiusMm: number | null
  minBendRadiusAllowedMm: number | null
  anchorCount: number
  waypointCount: number
  maxUnsupportedMm: number | null
  maxUnsupportedAllowedMm: number
  instances: string[]
  missingInstances: string[]
  issues: string[]
}

const round1 = (value: number) => Math.round(value * 10) / 10

export const summarizeWires = (build: Awaited<ReturnType<typeof loadBuild>>) => {
  const manifest = build.index.manifest
  const routes = manifest.routes ?? []
  const wires: WireSummary[] = routes.map((route) => {
    const resolved = resolveRoute(manifest, route)
    const sampled = sampleRoute(resolved.points)
    const lengthMm = round1(polylineLength(sampled.samples))
    const bend = minBendRadius(sampled.samples)
    const bendAllowed = effectiveMinBendRadiusMm(route)
    const spans = unsupportedSpans(resolved.anchors, sampled)
    const worstSpan = spans.reduce((worst, span) => Math.max(worst, span.lengthMm), 0)
    const spanAllowed = route.maxUnsupportedMm ?? DEFAULT_MAX_UNSUPPORTED_MM

    const issues: string[] = []
    if (resolved.points.length < 2) issues.push('fewer than 2 resolvable waypoints')
    if (route.maxLengthMm !== undefined && lengthMm > route.maxLengthMm) {
      issues.push(`length ${lengthMm}mm exceeds the ${route.maxLengthMm}mm budget`)
    }
    if (bend && bendAllowed !== null && bend.radiusMm < bendAllowed) {
      issues.push(`bend radius ${round1(bend.radiusMm)}mm < ${bendAllowed}mm minimum`)
    }
    if (spans.length > 0 && worstSpan > spanAllowed) {
      issues.push(`${round1(worstSpan)}mm unsupported span > ${spanAllowed}mm — add a clip/tie (anchor: true)`)
    }
    if (resolved.missingInstances.length > 0) {
      issues.push(`waypoint instance(s) not in the scene: ${resolved.missingInstances.join(', ')}`)
    }

    return {
      id: route.id,
      label: route.label ?? route.id,
      kind: route.kind ?? null,
      color: routeDisplayColor(route),
      diameterMm: route.diameterMm ?? null,
      lengthMm,
      maxLengthMm: route.maxLengthMm ?? null,
      minBendRadiusMm: bend ? round1(bend.radiusMm) : null,
      minBendRadiusAllowedMm: bendAllowed,
      anchorCount: resolved.anchors.filter(Boolean).length,
      waypointCount: resolved.points.length,
      maxUnsupportedMm: spans.length > 0 ? round1(worstSpan) : null,
      maxUnsupportedAllowedMm: spanAllowed,
      instances: resolved.instances,
      missingInstances: resolved.missingInstances,
      issues,
    }
  })

  const issueCount = wires.reduce((count, wire) => count + wire.issues.length, 0)
  const summary =
    wires.length === 0
      ? 'No wires: the scene has no routes[]. Publish them in scene.json (see plans/wiring.md).'
      : `${wires.length} wire(s), total ${round1(wires.reduce((sum, wire) => sum + wire.lengthMm, 0))}mm` +
        (issueCount > 0 ? ` — ${issueCount} issue(s); run \`buildviz check\` for geometry-aware wiring checks.` : ', no issues.')

  return apiEnvelope(true, build, summary, { wireCount: wires.length, wires })
}

export const printWiresHuman = (result: ReturnType<typeof summarizeWires>) => {
  console.log(result.summary)
  const { wires } = result.results as { wires: WireSummary[] }
  for (const wire of wires) {
    const kind = wire.kind ? ` [${wire.kind}]` : ''
    const od = wire.diameterMm !== null ? `, OD ${wire.diameterMm}mm` : ''
    const budget = wire.maxLengthMm !== null ? ` (budget ${wire.maxLengthMm}mm)` : ''
    console.log(`- ${wire.label}${kind}: ${wire.lengthMm}mm${budget}${od}`)
    const bend =
      wire.minBendRadiusMm === null
        ? 'straight'
        : `${wire.minBendRadiusMm}mm` +
          (wire.minBendRadiusAllowedMm !== null ? ` (min ${wire.minBendRadiusAllowedMm}mm)` : '')
    const span =
      wire.maxUnsupportedMm === null
        ? 'n/a'
        : `${wire.maxUnsupportedMm}mm (max ${wire.maxUnsupportedAllowedMm}mm)`
    console.log(
      `    bend radius: ${bend} · anchors: ${wire.anchorCount}/${wire.waypointCount} · longest span: ${span}`,
    )
    if (wire.instances.length > 0) console.log(`    connects: ${wire.instances.join(' ↔ ')}`)
    for (const issue of wire.issues) console.log(`    ⚠ ${issue}`)
  }
}
