// Check / sweep orchestration, HUB layer (see plans/repo-split.md).
//
// Moved from cli/commands/check.ts: the option-driven wrapping of the checks
// engine is shared by the `check`/`sweep` CLI commands AND the hub's MCP
// `check_build` tool, so it lives at the hub layer (hub -> checks/core is a
// legal edge; hub -> cli is not). The CLI re-exports these unchanged.
import { existsSync } from 'node:fs'
import { readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import type { ChecksConfig } from '../core/buildScene'
import {
  checkAssembly,
  isDeclaredInterferenceIssue,
  sweepOverlaps,
} from '../checks/buildvizGeometry'
import {
  checksToHighlights,
  geometryChecks,
  staticChecks,
  summarizeChecks,
  sweptChecks,
} from '../checks/buildvizChecks'
import { buildSweepSamples } from '../core/buildvizKinematics'
import {
  optionString,
  type CliOptions,
} from './cliShared'
import {
  loadBuild,
  resolveAssetPath,
  apiEnvelope,
  parseNumberOption,
  buildViewerUrl,
} from './buildLoad'

// `buildviz check` + `buildviz sweep`: static/spatial checks and the
// swept-pose (kinematics) validation envelope.

export const checkBuild = async (
  build: Awaited<ReturnType<typeof loadBuild>>,
  options: CliOptions,
  viewerBaseUrl: string,
) => {
  // Project intent lives in the scene as data (roadmap §6); CLI flags override it.
  const sceneConfig: ChecksConfig = build.index.manifest.checksConfig ?? {}
  const toleranceMm =
    parseNumberOption(optionString(options, 'tolerance'), 'tolerance') ?? sceneConfig.toleranceMm
  const minPenetrationMm =
    parseNumberOption(optionString(options, 'min-penetration', 'minPenetration'), 'min-penetration') ??
    sceneConfig.minPenetrationMm
  const maxPairs = parseNumberOption(optionString(options, 'max-pairs', 'maxPairs'), 'max-pairs')
  const gapWindowMm =
    parseNumberOption(optionString(options, 'gap-window', 'gapWindow'), 'gap-window') ??
    sceneConfig.clearanceMm
  const includeFasteners = Boolean(options['include-fasteners'] ?? options.includeFasteners)
  const minWallMm =
    parseNumberOption(optionString(options, 'min-wall', 'minWall'), 'min-wall') ?? sceneConfig.minWallMm
  const minThreadEngagementMm =
    parseNumberOption(
      optionString(options, 'min-thread-engagement', 'minThreadEngagement'),
      'min-thread-engagement',
    ) ?? sceneConfig.minThreadEngagementMm
  const wallSamples = parseNumberOption(optionString(options, 'wall-samples', 'wallSamples'), 'wall-samples')
  const matingToleranceMm =
    parseNumberOption(optionString(options, 'mating-tolerance', 'matingTolerance'), 'mating-tolerance') ??
    sceneConfig.matingToleranceMm
  const wireClearanceMm =
    parseNumberOption(optionString(options, 'wire-clearance', 'wireClearance'), 'wire-clearance') ??
    sceneConfig.wireClearanceMm
  const maxUnsupportedMm =
    parseNumberOption(optionString(options, 'max-span', 'maxSpan', 'max-unsupported'), 'max-span') ??
    sceneConfig.maxUnsupportedMm

  // Which check kinds to run/report. Base spatial + hygiene kinds plus the
  // default-on printability/thread checks; assembly_access is coarse + the
  // slowest, so it is opt-in via --access. `--checks a,b,c` is a full allowlist
  // that overrides the group defaults; `--no-printability` / `--no-assembleability`
  // toggle whole groups off.
  const BASE_KINDS = [
    'scene_meta',
    'placement',
    'mesh_overlap',
    'declared_interference',
    'clearance',
    'connectivity',
  ]
  const PRINTABILITY_KINDS = [
    'watertight',
    'wall_thickness',
    'degenerate_geometry',
    'self_intersection',
    'disconnected_components',
  ]
  // mating_contact + routing_reach + the wiring kinds are default-on
  // assembleability gates (the wiring kinds are no-ops for scenes without
  // routes[]); assembly_access stays the only opt-in (coarse + slowest) kind.
  const WIRING_KINDS = ['routing_reach', 'wire_bend_radius', 'wire_support', 'wire_clearance']
  const ASSEMBLEABILITY_KINDS = ['thread_engagement', 'assembly_access', 'mating_contact', ...WIRING_KINDS]
  const explicitChecks = optionString(options, 'checks')
  let enabledKinds: Set<string>
  if (explicitChecks) {
    enabledKinds = new Set(
      explicitChecks
        .split(',')
        .map((kind) => kind.trim())
        .filter(Boolean),
    )
  } else {
    enabledKinds = new Set([...BASE_KINDS, ...PRINTABILITY_KINDS, 'thread_engagement', 'mating_contact', ...WIRING_KINDS])
    if (options['no-printability'] ?? options.noPrintability)
      PRINTABILITY_KINDS.forEach((kind) => enabledKinds.delete(kind))
    if (options['no-assembleability'] ?? options.noAssembleability)
      ASSEMBLEABILITY_KINDS.forEach((kind) => enabledKinds.delete(kind))
    if (options.access) enabledKinds.add('assembly_access')
  }

  const checkWatertight = enabledKinds.has('watertight') || enabledKinds.has('degenerate_geometry')
  const checkWallThickness = enabledKinds.has('wall_thickness')
  const checkSelfIntersection = enabledKinds.has('self_intersection')
  const checkComponents = enabledKinds.has('disconnected_components')
  const checkThreadEngagement = enabledKinds.has('thread_engagement')
  const checkAssemblyAccess = enabledKinds.has('assembly_access')
  const checkMatingContact = enabledKinds.has('mating_contact')

  const effectiveConfig: ChecksConfig = {
    ...sceneConfig,
    ...(toleranceMm !== undefined ? { toleranceMm } : {}),
    ...(minPenetrationMm !== undefined ? { minPenetrationMm } : {}),
    ...(gapWindowMm !== undefined ? { clearanceMm: gapWindowMm } : {}),
    ...(minWallMm !== undefined ? { minWallMm } : {}),
    ...(minThreadEngagementMm !== undefined ? { minThreadEngagementMm } : {}),
    ...(matingToleranceMm !== undefined ? { matingToleranceMm } : {}),
    ...(wireClearanceMm !== undefined ? { wireClearanceMm } : {}),
    ...(maxUnsupportedMm !== undefined ? { maxUnsupportedMm } : {}),
  }

  const report = await checkAssembly(build.index.manifest, {
    toleranceMm,
    minPenetrationMm,
    maxPairs,
    gapWindowMm,
    includeFasteners,
    checkWatertight,
    checkWallThickness,
    checkSelfIntersection,
    checkComponents,
    expectedMeshComponents: effectiveConfig.expectedMeshComponents,
    maxMeshComponents: effectiveConfig.maxMeshComponents,
    checkThreadEngagement,
    checkAssemblyAccess,
    checkMatingContact,
    minWallMm,
    minThreadEngagementMm,
    matingToleranceMm,
    matingPairs: effectiveConfig.ignoreOverlapPairs,
    routes: WIRING_KINDS.some((kind) => enabledKinds.has(kind))
      ? build.index.manifest.routes
      : undefined,
    wireClearanceMm,
    maxUnsupportedMm,
    wallSamples,
    loadMesh: async (mesh) => {
      const assetPath = resolveAssetPath(build, mesh.url)
      if (!mesh.url || !existsSync(assetPath)) return null
      const buffer = await readFile(assetPath)
      return buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength) as ArrayBuffer
    },
  })

  // Generic, paintable check records: manifest hygiene + placement (static) plus
  // the geometry findings, with the project's allowed-pair intent applied. Then
  // keep only the enabled kinds (an explicit --checks allowlist can drop base
  // kinds too).
  const checks = [...staticChecks(build.index.manifest), ...geometryChecks(report, effectiveConfig)].filter(
    (check) => enabledKinds.has(check.kind),
  )
  const checkSummary = summarizeChecks(checks)
  const highlights = checksToHighlights(checks)
  const highlightUrl =
    highlights.parts.length > 0
      ? buildViewerUrl(build, viewerBaseUrl, { highlight: JSON.stringify(highlights) })
      : null

  const intentionalOverlaps = report.collisions.filter((collision) => collision.allowed).length
  const unexpectedOverlaps = report.collisions.length - intentionalOverlaps
  const declaredIssues = (report.declaredInterferences ?? []).filter(isDeclaredInterferenceIssue).length
  const summary = report.passed
    ? `No unexpected interference or floating parts` +
      (intentionalOverlaps > 0 ? ` (${intentionalOverlaps} intentional overlap(s) allowed)` : '') +
      ` (${report.instanceCount} instances, ${report.timings.totalMs}ms).`
    : `Found ${unexpectedOverlaps} unexpected colliding pair(s)` +
      (intentionalOverlaps > 0 ? ` (+ ${intentionalOverlaps} intentional)` : '') +
      `, ${report.floating.length} floating part(s)` +
      (declaredIssues > 0
        ? `, and ${declaredIssues} broken allowedInterferences declaration(s).`
        : '.')

  // Non-destructive sidecar (roadmap §7): a buildviz_checks.json next to the
  // scene that the viewer reads to paint overlays without touching scene.json.
  let sidecarPath: string | null = null
  if (options.emit) {
    sidecarPath = path.join(build.buildDir, 'buildviz_checks.json')
    const sidecar = {
      generatedAt: new Date().toISOString(),
      build: { id: build.buildId, name: build.index.manifest.name },
      checksConfig: effectiveConfig,
      summary: checkSummary,
      checks,
      highlights,
      report,
    }
    await writeFile(sidecarPath, `${JSON.stringify(sidecar, null, 2)}\n`, 'utf8')
  }

  return apiEnvelope(true, build, summary, {
    ...report,
    checksConfig: effectiveConfig,
    checkSummary,
    checks,
    highlightUrl,
    highlights,
    sidecarPath,
  })
}

// Swept-pose / motion validation (Phase 3). Drives the scene's joints[] through
// their range (a per-DOF workspace sweep) plus any named poses[], re-evaluating
// interference at each sampled pose with the cached BVHs, and reports the
// worst-case overlap envelope per instance pair. Mirrors `check`'s envelope:
// generic checks[] (swept_overlap / swept_clearance) + an optional sidecar.
export const sweepBuild = async (
  build: Awaited<ReturnType<typeof loadBuild>>,
  options: CliOptions,
  viewerBaseUrl: string,
) => {
  const manifest = build.index.manifest
  if (!manifest.joints || manifest.joints.length === 0) {
    throw new Error(
      `Scene has no joints[] — nothing to sweep. Add an additive joints[] block ` +
        `(see BUILDVIZ_INTEGRATION.md / "buildviz docs") to enable swept-pose validation.`,
    )
  }

  const sceneConfig: ChecksConfig = manifest.checksConfig ?? {}
  const samplesPerJoint =
    parseNumberOption(optionString(options, 'samples', 'samplesPerJoint'), 'samples') ?? undefined
  const toleranceMm =
    parseNumberOption(optionString(options, 'tolerance'), 'tolerance') ?? sceneConfig.toleranceMm
  const minPenetrationMm =
    parseNumberOption(optionString(options, 'min-penetration', 'minPenetration'), 'min-penetration') ??
    sceneConfig.minPenetrationMm
  const clearanceMm =
    parseNumberOption(optionString(options, 'clearance', 'gap-window', 'gapWindow'), 'clearance') ??
    sceneConfig.clearanceMm
  const includeFasteners = Boolean(options['include-fasteners'] ?? options.includeFasteners)

  const samples = buildSweepSamples(manifest, {
    samplesPerJoint: samplesPerJoint === undefined ? undefined : Math.round(samplesPerJoint),
  })

  const report = await sweepOverlaps(manifest, samples, {
    toleranceMm,
    minPenetrationMm,
    clearanceMm,
    includeFasteners,
    loadMesh: async (mesh) => {
      const assetPath = resolveAssetPath(build, mesh.url)
      if (!mesh.url || !existsSync(assetPath)) return null
      const buffer = await readFile(assetPath)
      return buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength) as ArrayBuffer
    },
  })

  // Allowance intent (allowedInterferences / legacy ignoreOverlapPairs) is
  // resolved by the engine per instance pair; sweptChecks just formats records.
  const checks = sweptChecks(report)
  const checkSummary = summarizeChecks(checks)
  const highlights = checksToHighlights(checks)
  const highlightUrl =
    highlights.parts.length > 0 || highlights.regions.length > 0
      ? buildViewerUrl(build, viewerBaseUrl, { highlight: JSON.stringify(highlights) })
      : null

  const overlapPairs = report.pairs.filter((pair) => pair.kind === 'overlap')
  const unexpectedPairs = overlapPairs.filter((pair) => pair.allowed !== true)
  const summary =
    unexpectedPairs.length === 0
      ? `No unexpected swept interference over ${report.sampleCount} pose(s)` +
        (overlapPairs.length > 0 ? ` (${overlapPairs.length} allowed interference(s))` : '') +
        ` (${report.instanceCount} parts, ${report.timings.totalMs}ms).`
      : `Found ${unexpectedPairs.length} pair(s) that interfere somewhere in the motion range ` +
        (overlapPairs.length > unexpectedPairs.length
          ? `(+ ${overlapPairs.length - unexpectedPairs.length} allowed) `
          : '') +
        `(worst ${report.worstPenetrationMm}mm over ${report.sampleCount} poses).`

  let sidecarPath: string | null = null
  if (options.emit) {
    sidecarPath = path.join(build.buildDir, 'buildviz_checks.json')
    const sidecar = {
      generatedAt: new Date().toISOString(),
      build: { id: build.buildId, name: manifest.name },
      kind: 'swept',
      checksConfig: manifest.checksConfig ?? {},
      summary: checkSummary,
      checks,
      highlights,
      report,
    }
    await writeFile(sidecarPath, `${JSON.stringify(sidecar, null, 2)}\n`, 'utf8')
  }

  return apiEnvelope(true, build, summary, {
    ...report,
    checkSummary,
    checks,
    highlightUrl,
    highlights,
    sidecarPath,
  })
}
