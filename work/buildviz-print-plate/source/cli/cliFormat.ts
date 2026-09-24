// Human-readable CLI output. These are the pure presentation functions for the
// default (non-`--json`) terminal mode: they take an already-computed result
// and print it. The command handlers in buildviz.ts own the `--json` path
// (machine-readable, the LLM surface) and call these only for human output, so
// "compute the answer" and "present the answer" stay cleanly separated.
import type { inspectBuild, queryBuild, summarizePart } from '../core/buildvizCore'
import { summarizeDiff, type diffManifests } from '../core/buildDiff'
import type {
  BomReport,
  CheckReport,
  IdentifyReport,
  MeshStatsReport,
  ProbePointsReport,
  ProbeRegionReport,
  SliceReport,
  SweepReport,
  ThicknessReport,
} from '../checks/buildvizGeometry'
import type { PackResult } from '../checks/buildvizPacking'
import type { BuildsIndexProject } from '../core/buildModel'
import type { UsageSummary } from '../hub/usageLog'

// printJson lives in cliShared (the hub needs it too, and the hub must not
// depend on this CLI presentation module); re-exported here for CLI consumers.
export { printJson } from '../hub/cliShared'

export const printInspect = (value: ReturnType<typeof inspectBuild>) => {
  console.log(`${value.name} (${value.units})`)
  console.log(`${value.instanceCount} instances, ${value.meshCount} meshes, ${value.partTypeCount} part types`)
  if (value.missingDesignSpec.length > 0) {
    console.log(`Missing design_spec entries: ${value.missingDesignSpec.join(', ')}`)
  }
  console.log('')
  value.parts.forEach((part) => {
    if (!part) return
    const detail = [
      `${part.instanceCount}x`,
      part.hasDesignSpec ? 'spec' : 'no spec',
      `${part.featureCount} features`,
      `${part.holeCount} holes`,
    ].join(', ')
    console.log(`- ${part.partType}: ${detail}`)
    if (part.description) console.log(`  ${part.description}`)
  })
}

export const printPart = (part: NonNullable<ReturnType<typeof summarizePart>>) => {
  console.log(`${part.partType} (${part.instanceCount} instances)`)
  if (part.description) console.log(part.description)
  console.log(`Meshes: ${part.meshIds.join(', ')}`)
  console.log(`Design spec: ${part.hasDesignSpec ? 'yes' : 'missing'}`)
  console.log(`Features: ${part.featureCount}, holes: ${part.holeCount}`)
  if (part.dimensions.length > 0) {
    console.log('Dimensions:')
    part.dimensions.forEach((dimension) => console.log(`- ${dimension}`))
  }
  console.log('Instances:')
  part.instances.forEach((instance) => {
    console.log(`- ${instance.id}: ${instance.name} (${instance.role})`)
  })
}

export const printQuery = (value: ReturnType<typeof queryBuild>) => {
  console.log(value.answer)
  value.results.forEach(({ score, part }) => {
    console.log(`\n${part.partType} (score ${score})`)
    if (part.description) console.log(part.description)
    if (part.dimensions.length > 0) {
      console.log(`Dimensions: ${part.dimensions.join('; ')}`)
    }
    if (part.holeCount > 0) console.log(`Holes: ${part.holeCount}`)
  })
}

export const printDiff = (
  buildId: string,
  fromVersion: string,
  toVersion: string,
  diff: ReturnType<typeof diffManifests>,
) => {
  console.log(`${buildId}: ${fromVersion} -> ${toVersion}`)
  console.log(summarizeDiff(diff))
  diff.instances.added.forEach((item) => console.log(`+ added ${item.instanceId} (${item.partType})`))
  diff.instances.removed.forEach((item) => console.log(`- removed ${item.instanceId} (${item.partType})`))
  diff.instances.moved.forEach((item) =>
    console.log(`~ moved ${item.instanceId} (${item.partType}) by [${item.translationMm.join(', ')}] mm`),
  )
  diff.instances.changed.forEach((item) =>
    console.log(`~ changed ${item.instanceId} (${item.partType}): ${item.changes.join(', ')}`),
  )
  diff.meshes.added.forEach((meshId) => console.log(`+ mesh added ${meshId}`))
  diff.meshes.removed.forEach((meshId) => console.log(`- mesh removed ${meshId}`))
  diff.meshes.changed.forEach((mesh) =>
    console.log(`~ mesh changed ${mesh.meshId}: ${mesh.changes.join(', ')}`),
  )
}

export const printVersionTree = (projects: BuildsIndexProject[]) => {
  projects.forEach((project) => {
    console.log(`▸ ${project.id}`)
    project.builds.forEach((build) => {
      const versions = build.versions
        .map((entry) => (entry.isDefault ? `${entry.name} (default)` : entry.name))
        .join(', ')
      console.log(`  - ${build.build}: ${build.name ?? build.build}${versions ? ` — ${versions}` : ''}`)
    })
  })
}

export const printCheck = (
  report: CheckReport & {
    highlightUrl: string | null
    sidecarPath?: string | null
    checkSummary?: { fail: number; warn: number; pass: number; total: number }
  },
) => {
  const allowedCollisions = report.collisions.filter((collision) => collision.allowed === true)
  const unexpectedCollisions = report.collisions.length - allowedCollisions.length
  const declaredIssues = (report.declaredInterferences ?? []).filter(
    (declared) =>
      declared.outcome === 'not_in_contact' ||
      declared.outcome === 'unknown_instance' ||
      declared.outcome === 'exceeds_max_penetration',
  )
  console.log(
    report.passed
      ? `PASS: no unexpected interference or floating parts` +
          (allowedCollisions.length > 0
            ? ` (${allowedCollisions.length} allowed interference(s))`
            : '') +
          ` (${report.instanceCount} instances).`
      : `PROBLEMS: ${unexpectedCollisions} unexpected colliding pair(s)` +
          (allowedCollisions.length > 0 ? ` (+ ${allowedCollisions.length} allowed)` : '') +
          `, ${report.floating.length} floating part(s)` +
          (declaredIssues.length > 0
            ? `, ${declaredIssues.length} broken allowedInterferences declaration(s).`
            : '.'),
  )
  if (report.checkSummary) {
    console.log(
      `Checks: ${report.checkSummary.fail} fail · ${report.checkSummary.warn} warn · ` +
        `${report.checkSummary.pass} pass (${report.checkSummary.total} total).`,
    )
  }
  console.log(
    `tolerance ${report.toleranceMm}mm · min penetration ${report.minPenetrationMm}mm · ` +
      `${report.broadPhasePairs} candidate pairs · ${report.instanceCount} parts · ${report.timings.totalMs}ms` +
      (report.capped ? ' · CAPPED (raise --max-pairs)' : ''),
  )
  if (report.fastenersExcluded > 0 && !report.fastenersIncluded) {
    console.log(
      `Excluded ${report.fastenersExcluded} fastener instance(s) (use --include-fasteners to analyze them).`,
    )
  }
  if (report.missingMeshes.length > 0) {
    console.log(`Skipped ${report.missingMeshes.length} missing mesh(es): ${report.missingMeshes.join(', ')}`)
  }
  if (report.collisions.length > 0) {
    console.log('\nCollisions (penetration mm):')
    report.collisions.forEach((collision) => {
      const tag =
        collision.allowed === true
          ? collision.allowance?.source === 'declared'
            ? ` — allowed (${collision.allowance.kind})`
            : ' — allowed (legacy ignoreOverlapPairs)'
          : collision.allowance?.refusal === 'relative_motion'
            ? ' — ignoreOverlapPairs REFUSED: parts move relative to each other'
            : collision.allowance?.refusal === 'max_penetration_exceeded'
              ? ` — exceeds declared ${collision.allowance.maxPenetrationMm}mm cap`
              : ''
      console.log(
        `- ${collision.a.partType} (${collision.a.instanceId}) ↔ ${collision.b.partType} (${collision.b.instanceId}): ${collision.penetrationMm}mm${tag}`,
      )
    })
  }
  if (declaredIssues.length > 0) {
    console.log(`\nBroken allowedInterferences declarations (${declaredIssues.length}):`)
    declaredIssues.forEach((declared) => {
      const detail =
        declared.outcome === 'unknown_instance'
          ? 'references instance id(s) not in the scene'
          : declared.outcome === 'not_in_contact'
            ? `not present — parts are ${declared.gapMm !== null ? `${declared.gapMm}mm` : 'far'} apart (stale?)`
            : `${declared.penetrationMm}mm exceeds the declared ${declared.maxPenetrationMm}mm cap`
      console.log(`- ${declared.instances[0]} ↔ ${declared.instances[1]} (${declared.kind}): ${detail}`)
    })
  }
  if (report.floating.length > 0) {
    console.log(`\nFloating / disconnected (${report.floating.length}):`)
    report.floating.forEach((floating) => {
      const gap =
        floating.nearestGapMm !== null
          ? ` (nearest ${floating.nearestInstanceId} at ${floating.nearestGapMm}mm)`
          : ''
      console.log(`- ${floating.partType} (${floating.instanceId})${gap}`)
    })
  }
  if (report.gaps.length > 0) {
    console.log(`\nSuspicious gaps (${report.gaps.length}):`)
    report.gaps.forEach((gap) => {
      console.log(`- ${gap.partType} (${gap.instanceId}) is ${gap.gapMm}mm from ${gap.nearestInstanceId}`)
    })
  }

  // Printability (per unique mesh): robust watertight/manifold + heuristic wall.
  if (report.printability.length > 0) {
    const topo = report.printability.filter((mesh) => mesh.openEdges !== null)
    const broken = topo.filter((mesh) => (mesh.openEdges ?? 0) > 0 || (mesh.nonManifoldEdges ?? 0) > 0)
    const wound = topo.filter(
      (mesh) => mesh.inconsistentWinding && (mesh.openEdges ?? 0) === 0 && (mesh.nonManifoldEdges ?? 0) === 0,
    )
    const degen = report.printability.filter((mesh) => (mesh.degenerateTriangles ?? 0) > 0)
    const selfChecked = report.printability.filter((mesh) => mesh.selfIntersections !== null)
    const selfHit = selfChecked.filter((mesh) => (mesh.selfIntersections ?? 0) > 0)
    const walled = report.printability.filter((mesh) => mesh.minWallMm !== null)
    const thin = walled.filter((mesh) => (mesh.minWallMm ?? Infinity) < report.minWallMm)
    if (topo.length > 0) {
      console.log(
        `\nPrintability — watertight/manifold (robust): ${broken.length} non-watertight/non-manifold` +
          ` of ${topo.length} mesh(es).`,
      )
      broken.forEach((mesh) => {
        console.log(`- ${mesh.meshName}: ${mesh.openEdges} open · ${mesh.nonManifoldEdges} non-manifold edge(s)`)
      })
      wound.forEach((mesh) => console.log(`- ${mesh.meshName}: inconsistent winding (flipped normal)`))
      degen.forEach((mesh) =>
        console.log(`- ${mesh.meshName}: ${mesh.degenerateTriangles} degenerate (zero-area) triangle(s)`),
      )
    }
    if (selfChecked.length > 0) {
      console.log(
        `Printability — self-intersection (robust): ${selfHit.length} self-intersecting` +
          ` of ${selfChecked.length} mesh(es).`,
      )
      selfHit
        .sort((a, b) => (b.selfIntersections ?? 0) - (a.selfIntersections ?? 0))
        .forEach((mesh) =>
          console.log(`- ${mesh.meshName}: ${mesh.selfIntersections} self-intersecting triangle pair(s)`),
        )
    }
    if (walled.length > 0) {
      console.log(
        `Printability — wall thickness (heuristic est.): ${thin.length} below ${report.minWallMm}mm` +
          ` of ${walled.length} mesh(es).`,
      )
      thin
        .sort((a, b) => (a.minWallMm ?? 0) - (b.minWallMm ?? 0))
        .forEach((mesh) => console.log(`- ${mesh.meshName}: min wall ≈ ${mesh.minWallMm}mm`))
    }
  }

  // Assembleability (heuristic): fastener engagement + straight-line access.
  if (report.fasteners.length > 0) {
    const under = report.fasteners.filter((fastener) => fastener.engagementMm < report.minThreadEngagementMm)
    console.log(
      `\nAssembleability — thread engagement (heuristic est.): ${under.length} under-engaged` +
        ` of ${report.fasteners.length} axial fastener(s) (< ${report.minThreadEngagementMm}mm).`,
    )
    under
      .sort((a, b) => a.engagementMm - b.engagementMm)
      .slice(0, 20)
      .forEach((fastener) =>
        console.log(
          `- ${fastener.partType} (${fastener.instanceId}): ≈ ${fastener.engagementMm}mm of ${fastener.shaftLengthMm}mm`,
        ),
      )
  }
  if (report.access.length > 0) {
    const blocked = report.access.filter((part) => part.clearDirections === 0)
    console.log(
      `\nAssembleability — assembly access (coarse heuristic): ${blocked.length} part(s) with no clear` +
        ` straight-line extraction of ${report.access.length} checked.`,
    )
    blocked
      .slice(0, 20)
      .forEach((part) => console.log(`- ${part.partType} (${part.instanceId})`))
  }

  // Mating-face contact (robust): floating / crashing declared or likely mates.
  if (report.mating.length > 0) {
    const tol = report.matingToleranceMm
    const bad = report.mating.filter(
      (mate) => mate.penetrationMm > tol || (mate.penetrationMm === 0 && mate.gapMm > tol),
    )
    const declared = report.mating.filter((mate) => mate.declared).length
    console.log(
      `\nAssembleability — mating contact (robust, ${tol}mm tol): ${bad.length} out-of-tolerance` +
        ` of ${report.mating.length} mating pair(s) checked (${declared} declared).`,
    )
    bad
      .sort((a, b) => b.penetrationMm + b.gapMm - (a.penetrationMm + a.gapMm))
      .slice(0, 20)
      .forEach((mate) => {
        const detail =
          mate.penetrationMm > tol
            ? `interpenetrating ${mate.penetrationMm}mm (crash)`
            : `floating, gap ${mate.gapMm}mm`
        console.log(`- ${mate.a.partType} (${mate.a.instanceId}) ⟷ ${mate.b.partType} (${mate.b.instanceId}): ${detail}`)
      })
  }

  // Routing reach (heuristic): cable/harness routes over budget or obstructed.
  if (report.routing.length > 0) {
    const bad = report.routing.filter(
      (route) => route.blockingInstanceIds.length > 0 || (route.maxLengthMm !== null && route.lengthMm > route.maxLengthMm),
    )
    console.log(
      `\nAssembleability — routing reach (heuristic): ${bad.length} unroutable` +
        ` of ${report.routing.length} route(s) checked.`,
    )
    bad.slice(0, 20).forEach((route) => {
      const reasons: string[] = []
      if (route.maxLengthMm !== null && route.lengthMm > route.maxLengthMm)
        reasons.push(`length ${route.lengthMm}mm > ${route.maxLengthMm}mm`)
      if (route.blockingInstanceIds.length > 0)
        reasons.push(`through ${route.blockingInstanceIds.length} solid(s)`)
      console.log(`- ${route.label}: ${reasons.join('; ')}`)
    })
  }

  if (report.sidecarPath) {
    console.log(`\nWrote check records to ${report.sidecarPath} (the viewer reads it automatically).`)
  }
  if (report.highlightUrl) {
    console.log(`\nView issues: ${report.highlightUrl}`)
  }
}

export const printSweep = (
  report: SweepReport & {
    checkSummary?: { fail: number; warn: number; pass: number; total: number }
    highlightUrl?: string | null
    sidecarPath?: string | null
  },
) => {
  const overlaps = report.pairs.filter((pair) => pair.kind === 'overlap')
  const clearances = report.pairs.filter((pair) => pair.kind === 'clearance')
  console.log(
    overlaps.length === 0
      ? `PASS: no swept interference across ${report.sampleCount} pose(s).`
      : `SWEPT INTERFERENCE: ${overlaps.length} pair(s) overlap somewhere in the motion range.`,
  )
  console.log(
    `${report.sampleCount} pose samples · ${report.instanceCount} parts · worst penetration ` +
      `${report.worstPenetrationMm}mm · ${report.timings.totalMs}ms ` +
      `(load ${report.timings.loadMs}ms · sweep ${report.timings.sweepMs}ms)` +
      (report.capped ? ' · CAPPED' : ''),
  )
  if (report.fastenersExcluded > 0) {
    console.log(`Excluded ${report.fastenersExcluded} fastener instance(s) (use --include-fasteners).`)
  }
  if (overlaps.length > 0) {
    console.log('\nWorst-case overlap envelope (max penetration over sweep):')
    overlaps.forEach((pair) => {
      console.log(
        `- ${pair.a.partType} (${pair.a.instanceId}) ↔ ${pair.b.partType} (${pair.b.instanceId}): ` +
          `${pair.maxPenetrationMm}mm @ ${pair.worstLabel}`,
      )
    })
  }
  if (clearances.length > 0) {
    console.log(`\nClosest approaches (within clearance window):`)
    clearances.forEach((pair) => {
      console.log(
        `- ${pair.a.partType} (${pair.a.instanceId}) ↔ ${pair.b.partType} (${pair.b.instanceId}): ` +
          `${pair.minClearanceMm}mm @ ${pair.worstLabel}`,
      )
    })
  }
  if (report.sidecarPath) {
    console.log(`\nWrote swept check records to ${report.sidecarPath} (the viewer reads it automatically).`)
  }
  if (report.highlightUrl) {
    console.log(`\nView worst-case poses: ${report.highlightUrl}`)
  }
}

// Geometry probe: per-point solid/hole/void classification + nearest surface.
export const printProbePoints = (
  report: ProbePointsReport & { highlightUrl?: string | null },
) => {
  console.log(
    `Probed ${report.points.length} point(s): ${report.insideCount} inside solid · ` +
      `${report.instanceCount} parts · ${report.timings.totalMs}ms` +
      (report.fastenersExcluded > 0 ? ` · ${report.fastenersExcluded} fastener(s) excluded` : ''),
  )
  report.points.forEach((point) => {
    const where = point.nearestFeature
      ? ` · nearest ${point.nearestFeature.partType} (${point.nearestFeature.instanceId}) at ${point.nearestSurfaceDistanceMm}mm`
      : ''
    const inside =
      point.insideInstanceIds.length > 0 ? ` in ${point.insideInstanceIds.join(', ')}` : ''
    console.log(`- [${point.point.join(', ')}]: ${point.classification.toUpperCase()}${inside}${where}`)
  })
  if (report.missingMeshes.length > 0) {
    console.log(`Skipped ${report.missingMeshes.length} missing mesh(es).`)
  }
  if (report.highlightUrl) console.log(`\nView: ${report.highlightUrl}`)
}

// Geometry probe: box occupancy fraction + occupied volume estimate.
export const printProbeRegion = (
  report: ProbeRegionReport & { highlightUrl?: string | null },
) => {
  const pct = (report.occupiedFraction * 100).toFixed(1)
  console.log(
    `Region [${report.box.min.join(', ')}]→[${report.box.max.join(', ')}]: ${pct}% occupied ` +
      `(${report.occupiedSamples}/${report.sampleCount} samples, grid ${report.grid.join('×')}).`,
  )
  console.log(
    `Box volume ${report.boxVolumeMm3}mm³ · occupied ≈ ${report.occupiedVolumeEstimateMm3}mm³ · ` +
      `${report.timings.totalMs}ms`,
  )
  if (report.occupiedBounds) {
    console.log(`Occupied bounds: [${report.occupiedBounds.min.join(', ')}] → [${report.occupiedBounds.max.join(', ')}]`)
  }
  if (report.occupantInstanceIds.length > 0) {
    console.log(`Occupants: ${report.occupantInstanceIds.join(', ')}`)
  } else {
    console.log('Occupants: none (empty / void)')
  }
  if (report.highlightUrl) console.log(`\nView: ${report.highlightUrl}`)
}

// Cross-section sweep: per-section area + region count, plus the min-thickness
// metric (heuristic, inscribed-disk diameter via distance transform).
export const printSlice = (report: SliceReport & { highlightUrl?: string | null }) => {
  console.log(
    `Slice ${report.plane} (normal ${report.normalAxis}) · ${report.sectionCount} section(s) · ` +
      `res ${report.resolutionMm}mm · ${report.instanceCount} parts · ${report.timings.totalMs}ms`,
  )
  report.sections.forEach((section) => {
    const thickness =
      section.minThicknessMm !== null
        ? ` · min thickness ≈ ${section.minThicknessMm}mm (est.)`
        : ''
    console.log(
      `- ${report.normalAxis}=${section.coord}: area ${section.areaMm2}mm² · ` +
        `${section.regionCount} region(s)${thickness}`,
    )
  })
  if (report.metric === 'min-thickness' && report.overall.minThicknessMm !== null) {
    const pass =
      report.overall.passed === null
        ? ''
        : report.overall.passed
          ? ` · PASS (≥ ${report.overall.threshold}mm)`
          : ` · FAIL (< ${report.overall.threshold}mm)`
    console.log(
      `\nNarrowest: ≈ ${report.overall.minThicknessMm}mm at ${report.normalAxis}=${report.overall.atCoord}` +
        (report.overall.atPoint ? ` [${report.overall.atPoint.join(', ')}]` : '') +
        pass,
    )
  }
  if (report.highlightUrl) console.log(`\nView: ${report.highlightUrl}`)
}

export const printThickness = (report: ThicknessReport & { highlightUrl?: string | null }) => {
  if (report.minThicknessMm === null) {
    console.log('No thickness measured (no geometry matched the filter).')
    return
  }
  const pass =
    report.passed === null ? '' : report.passed ? ` · PASS (≥ ${report.threshold}mm)` : ` · FAIL (< ${report.threshold}mm)`
  console.log(
    `Min thickness ≈ ${report.minThicknessMm}mm (HEURISTIC) at ${report.normalAxis}=${report.atCoord}` +
      (report.atPoint ? ` [${report.atPoint.join(', ')}]` : '') +
      pass,
  )
  console.log(
    `Swept ${report.sectionCount} section(s) on plane ${report.plane} · ` +
      (report.weakestAxis ? `weakest along ${report.weakestAxis} · ` : '') +
      `${report.instanceCount} parts · ${report.timings.totalMs}ms`,
  )
  if (report.highlightUrl) console.log(`\nView: ${report.highlightUrl}`)
}

export const printMeshStats = (report: MeshStatsReport) => {
  console.log(
    `${report.meshCount} mesh(es) · ${report.instanceCount} instance(s) · ` +
      `${report.totals.triangleCount} triangles · ${report.totals.nonWatertight} non-watertight · ` +
      `${report.timings.totalMs}ms`,
  )
  report.meshes.forEach((mesh) => {
    console.log(
      `\n${mesh.meshName} (${mesh.meshId})${mesh.isFastener ? ' [fastener]' : ''} ×${mesh.instanceIds.length}`,
    )
    console.log(
      `  size ${mesh.sizeMm.join('×')}mm · ${mesh.triangleCount} tris · vol ${mesh.volumeMm3}mm³ · ` +
        `area ${mesh.surfaceAreaMm2}mm²`,
    )
    const topo = mesh.watertight
      ? 'watertight & manifold'
      : `${mesh.openEdges} open + ${mesh.nonManifoldEdges} non-manifold edge(s)`
    const extra = [
      mesh.componentCount > 1 ? `${mesh.componentCount} bodies` : null,
      mesh.degenerateTriangles > 0 ? `${mesh.degenerateTriangles} degenerate` : null,
      mesh.inconsistentWinding ? 'inconsistent winding' : null,
    ].filter(Boolean)
    console.log(`  ${topo}${extra.length > 0 ? ` · ${extra.join(' · ')}` : ''}`)
  })
}

// Bill of materials: per-part-type count + volume/mass + size, split into
// printed parts and fasteners. Volume comes from the topology engine; mass is
// volume × an optional density.
export const printBom = (report: BomReport) => {
  const massTotal = report.totals.massG !== null ? ` · ${report.totals.massG}g` : ''
  console.log(
    `Bill of materials: ${report.partTypeCount} part type(s) · ${report.instanceCount} part(s) · ` +
      `${report.totals.volumeMm3}mm³${massTotal} · ${report.timings.totalMs}ms`,
  )
  if (report.densityGCm3 !== null) {
    console.log(`Density: ${report.densityGCm3} g/cm³ (mass = volume × density).`)
  } else {
    console.log('No density given (pass --density <g/cm³> for a mass estimate).')
  }
  if (report.missingMeshes.length > 0) {
    console.log(`Skipped ${report.missingMeshes.length} missing mesh(es): ${report.missingMeshes.join(', ')}`)
  }

  const printLine = (part: BomReport['parts'][number]) => {
    const mass = part.totalMassG !== null ? ` · ${part.totalMassG}g` : ''
    const flag = part.watertight ? '' : ' · ⚠ open mesh (volume approx.)'
    console.log(
      `- ${part.partType} ×${part.count}: ${part.totalVolumeMm3}mm³${mass} · ` +
        `unit ${part.sizeMm.join('×')}mm${flag}`,
    )
  }

  const printed = report.parts.filter((part) => !part.isFastener)
  const fasteners = report.parts.filter((part) => part.isFastener)
  if (printed.length > 0) {
    console.log(`\nPrinted parts (${report.totals.printedParts} part(s), ${report.totals.printedPartTypes} type(s)):`)
    printed.forEach(printLine)
  }
  if (fasteners.length > 0) {
    console.log(`\nFasteners (${report.totals.fastenerParts} part(s), ${report.totals.fastenerPartTypes} type(s)):`)
    fasteners.forEach(printLine)
  }
}

// identify: a world point expressed in each relevant part's local frame (or an
// instance's placement), removing the viewer↔part-local translation tax.
export const printIdentify = (report: IdentifyReport & { highlightUrl?: string | null }) => {
  console.log(
    `Identify (${report.mode}) · world [${report.worldPoint.join(', ')}] · ` +
      `${report.frames.length} frame(s) · ${report.instanceCount} part(s) · ${report.timings.totalMs}ms`,
  )
  if (report.frames.length === 0) {
    console.log('No part encloses or is near this point.')
  }
  report.frames.forEach((frame) => {
    const where = frame.insideSolid ? 'inside' : `${frame.surfaceDistanceMm}mm from surface`
    console.log(
      `- ${frame.partType} (${frame.instanceId}) [${frame.name}]: local [${frame.localPoint.join(', ')}] (${where})`,
    )
    console.log(
      `    placement origin (world) [${frame.worldOrigin.join(', ')}] · ` +
        `local bounds [${frame.localBounds.min.join(', ')}] → [${frame.localBounds.max.join(', ')}]`,
    )
  })
  if (report.highlightUrl) console.log(`\nView: ${report.highlightUrl}`)
}

// Cached version listing (hub retention / inspection).
export const printCacheList = (result: {
  cacheRoot: string
  builds: Array<{
    id: string
    name: string | null
    defaultVersion: string
    versionCount: number
    versions: Array<{ name: string; isDefault: boolean; sizeBytes: number; pushedAt: string | null }>
    sizeBytes: number
  }>
  totalBytes: number
}) => {
  const mb = (bytes: number) => `${(bytes / (1024 * 1024)).toFixed(1)}MB`
  console.log(`Cache: ${result.cacheRoot}`)
  console.log(`${result.builds.length} build(s) · ${mb(result.totalBytes)} total`)
  result.builds.forEach((build) => {
    console.log(`\n▸ ${build.id}${build.name ? ` (${build.name})` : ''} — ${mb(build.sizeBytes)}`)
    build.versions.forEach((version) => {
      console.log(
        `  - ${version.name}${version.isDefault ? ' (default)' : ''} · ${mb(version.sizeBytes)}` +
          (version.pushedAt ? ` · ${version.pushedAt}` : ''),
      )
    })
  })
}

// Plate-packing report. Per-plate summary table + per-part orientation lines
// (rotation, footprint, height, support estimate). Heuristic — labeled as such.
export const printPack = (
  result: PackResult & {
    scenePath?: string | null
    viewerUrl?: string | null
    export?: {
      outDir: string
      format: string
      plateCount: number
      files: Array<{ plate: number; fileName: string; path: string; partCount: number }>
    } | null
  },
) => {
  const bedLabel =
    `${result.bed.x}×${result.bed.y}×${result.bed.z}mm` +
    (result.printer ? ` (${result.printer})` : ' (custom bed)')
  console.log(
    `Packed ${result.totals.partCount} part(s) onto ${result.totals.plateCount} plate(s) — ${bedLabel}.`,
  )
  console.log(
    `support angle ${result.supportAngleDeg}° · spacing ${result.spacingMm}mm · margin ${result.marginMm}mm · ` +
      `${result.totals.partsRotated} rotated 90° · ${result.totals.partsNeedingSupport} need support ` +
      `(avg ${result.totals.avgSupportAreaMm2}mm²/part). Orientation + packing are HEURISTICS.`,
  )

  console.log('\nPlates:')
  result.plates.forEach((plate) => {
    console.log(
      `- Plate ${plate.plate + 1}: ${plate.partCount} part(s), ` +
        `${(plate.utilization * 100).toFixed(1)}% bed utilization`,
    )
  })

  // Group parts by plate for the per-part detail.
  for (const plate of result.plates) {
    const parts = result.parts.filter((part) => part.plate === plate.plate)
    console.log(`\nPlate ${plate.plate + 1} parts:`)
    parts.forEach((part) => {
      const rot = part.orientation.rotationEulerDeg
      const rotated = part.rotated90 ? ' +90°Z' : ''
      const support = part.supportAreaMm2 > 0 ? `${part.supportAreaMm2}mm² support` : 'no support'
      console.log(
        `- ${part.partType} (${part.instanceId}): rest ${part.orientation.kind} ` +
          `[${rot[0]},${rot[1]},${rot[2]}]°${rotated} · ` +
          `footprint ${part.footprint.x}×${part.footprint.y}mm · h ${part.heightMm}mm · ${support} · ` +
          `@(${part.position.x},${part.position.y})mm`,
      )
    })
  }

  if (result.export) {
    console.log(
      `\nExported ${result.export.files.length} ${result.export.format.toUpperCase()} plate file(s) to:`,
    )
    console.log(result.export.outDir)
    result.export.files.forEach((file) => {
      console.log(`- Plate ${file.plate} (${file.partCount} part(s)): ${file.path}`)
    })
  }

  if (result.scenePath) {
    console.log(`\nWrote packed layout scene to ${result.scenePath}.`)
  }
  if (result.viewerUrl) {
    console.log(`\nOpen in viewer: ${result.viewerUrl}`)
  }
}

// Project-compatibility report (`buildviz compat`). A project is
// BuildViz-compatible when every requirement is a pass or warn (no fail).
export type CompatStatus = 'pass' | 'warn' | 'fail'

export type CompatRequirement = {
  id: string
  label: string
  status: CompatStatus
  summary: string
  details: string[]
  remediation: string | null
}

export type CompatReport = {
  ok: true
  compatible: boolean
  projectDir: string
  buildId: string
  summary: string
  requirements: CompatRequirement[]
  remediation: string[]
}

const compatMark = (status: CompatStatus) =>
  status === 'pass' ? 'PASS' : status === 'warn' ? 'WARN' : 'FAIL'

// Usage summary (`buildviz usage`). A readable roll-up of ~/.buildviz/usage.jsonl
// that makes a re-audit trivial: per-command and per-endpoint counts with
// first-/last-seen timestamps. Handles a missing/empty log gracefully.
export const printUsage = (summary: UsageSummary) => {
  if (!summary.exists || summary.totalEvents === 0) {
    console.log('No usage recorded yet.')
    console.log(`Log: ${summary.logPath}`)
    return
  }

  console.log(`Usage log: ${summary.logPath}`)
  console.log(
    `${summary.totalEvents} event(s) · ${summary.cliInvocations} CLI invocation(s) · ` +
      `${summary.hubRequests} hub request(s)`,
  )
  if (summary.firstSeen && summary.lastSeen) {
    console.log(`Recorded ${summary.firstSeen} → ${summary.lastSeen}`)
  }
  if (summary.malformedLines > 0) {
    console.log(`(${summary.malformedLines} malformed line(s) skipped)`)
  }

  if (summary.commands.length > 0) {
    console.log('\nCLI commands:')
    summary.commands.forEach((entry) => {
      console.log(`- ${entry.key}: ${entry.count}× · first ${entry.firstSeen} · last ${entry.lastSeen}`)
    })
  }

  if (summary.endpoints.length > 0) {
    console.log('\nHub endpoints:')
    summary.endpoints.forEach((entry) => {
      console.log(`- ${entry.key}: ${entry.count}× · first ${entry.firstSeen} · last ${entry.lastSeen}`)
    })
  }
}

export const printCompat = (report: CompatReport) => {
  console.log(
    `${report.compatible ? 'COMPATIBLE' : 'NOT COMPATIBLE'} — ${report.buildId}`,
  )
  console.log(report.summary)
  console.log(`Project: ${report.projectDir}`)
  console.log('')
  report.requirements.forEach((requirement) => {
    console.log(`[${compatMark(requirement.status)}] ${requirement.label}: ${requirement.summary}`)
    requirement.details.forEach((detail) => console.log(`    - ${detail}`))
  })
  if (report.remediation.length > 0) {
    console.log('\nTo become compatible:')
    report.remediation.forEach((item) => console.log(`- ${item}`))
  }
}
