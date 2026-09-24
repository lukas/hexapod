import { writeFile } from 'node:fs/promises'
import path from 'node:path'
import {
  meshStats,
  probePoints,
  probeRegion,
  sliceBuild,
  thicknessBuild,
  type SlicePlane,
} from '../../checks/buildvizGeometry'
import { buildInstanceGeometries, loadMeshGeometry } from '../../core/geometryEngine'
import { generatePartDrawing, parseDrawingViews, resolvePartMesh } from '../../core/schematicDrawing'
import {
  generateSectionFigure,
  parseSectionPlanes,
  parseSectionWindow,
  translateInstances,
  type SectionSource,
} from '../../core/sectionFigure'
import type { BuildSceneManifest } from '../../core/buildScene'
import { massProperties } from '../../checks/buildvizMass'
import {
  printJson,
  printMeshStats,
  printProbePoints,
  printProbeRegion,
  printSlice,
  printThickness,
} from '../cliFormat'
import {
  optionString,
  type CliOptions,
} from '../../hub/cliShared'
import {
  loadBuild,
  apiEnvelope,
  parseNumberOption,
  parseRegion,
  parsePoints,
  parsePlane,
  parseRange,
  makeLoadMesh,
  geometryFilters,
  probeColor,
  resolveViewerBaseUrl,
  buildViewerUrl,
} from '../cliBuild'

// Geometry query commands: `probe`, `slice`, `thickness`, `mesh stats`.

// --- Geometry query commands (probe / slice / thickness / mesh stats) --------

export const probeCommand = async (positional: string[], options: CliOptions) => {
  const sub = positional[0]
  if (sub !== 'points' && sub !== 'region') {
    throw new Error("Usage: buildviz probe points|region <build> ...")
  }
  const buildArg = positional[1]
  if (!buildArg) throw new Error('Missing build directory.')
  const build = await loadBuild(buildArg, optionString(options, 'version'), optionString(options, 'branch'))
  const filters = geometryFilters(options)
  const loadMesh = makeLoadMesh(build)
  const viewerBaseUrl = await resolveViewerBaseUrl(options)

  if (sub === 'points') {
    const pointsArg = optionString(options, 'points', 'point')
    if (!pointsArg) throw new Error("Missing --points '[[x,y,z],...]'.")
    const points = parsePoints(pointsArg)
    const report = await probePoints(build.index.manifest, points, { loadMesh, ...filters })
    const highlights = {
      points: report.points.map((entry) => ({
        point: entry.point,
        color: probeColor(entry.classification),
        annotation:
          `${entry.classification}` +
          (entry.nearestSurfaceDistanceMm !== null ? ` · ${entry.nearestSurfaceDistanceMm}mm to surface` : ''),
      })),
    }
    const highlightUrl =
      highlights.points.length > 0
        ? buildViewerUrl(build, viewerBaseUrl, { highlight: JSON.stringify(highlights) })
        : null
    if (options.json) {
      printJson(
        apiEnvelope(
          true,
          build,
          `Probed ${points.length} point(s); ${report.insideCount} inside solid.`,
          { ...report, highlights, highlightUrl },
        ),
      )
    } else {
      printProbePoints({ ...report, highlightUrl })
    }
    return
  }

  const boxArg = optionString(options, 'box', 'region')
  if (!boxArg) throw new Error('Missing --box "x=a:b,y=c:d,z=e:f".')
  const box = parseRegion(boxArg)
  const samples = parseNumberOption(optionString(options, 'samples'), 'samples')
  const report = await probeRegion(build.index.manifest, box, { loadMesh, samples, ...filters })
  const overlayBox = report.occupiedBounds ?? report.box
  const highlights = {
    regions: [
      {
        min: overlayBox.min,
        max: overlayBox.max,
        color: report.occupiedFraction > 0 ? '#22c55e' : '#94a3b8',
        annotation: `${(report.occupiedFraction * 100).toFixed(1)}% occupied (~${report.occupiedVolumeEstimateMm3}mm³)`,
      },
    ],
  }
  const highlightUrl = buildViewerUrl(build, viewerBaseUrl, { highlight: JSON.stringify(highlights) })
  if (options.json) {
    printJson(
      apiEnvelope(
        true,
        build,
        `Region ${(report.occupiedFraction * 100).toFixed(1)}% occupied.`,
        { ...report, highlights, highlightUrl },
      ),
    )
  } else {
    printProbeRegion({ ...report, highlightUrl })
  }
}

const PLANE_NORMAL_NAME: Record<SlicePlane, 'x' | 'y' | 'z'> = { yz: 'x', xz: 'y', xy: 'z' }

export const sliceCommand = async (positional: string[], options: CliOptions) => {
  const buildArg = positional[0]
  if (!buildArg) throw new Error('Missing build directory.')
  const build = await loadBuild(buildArg, optionString(options, 'version'), optionString(options, 'branch'))
  const filters = geometryFilters(options)
  const plane = parsePlane(optionString(options, 'plane'))
  const metricOpt = (optionString(options, 'metric') ?? '').toLowerCase()
  const metric = metricOpt === 'min-thickness' || metricOpt === 'thickness' ? 'min-thickness' : 'area'
  const resolutionMm = parseNumberOption(optionString(options, 'res', 'resolution'), 'res')
  const minThicknessMm = parseNumberOption(optionString(options, 'min', 'min-thickness'), 'min')

  const rangeArg = optionString(options, 'range')
  const atArg = optionString(options, 'at')
  let range: { lo: number; hi: number; step: number } | undefined
  let coords: number[] | undefined
  if (rangeArg) {
    const parsed = parseRange(rangeArg)
    if (parsed.axis !== PLANE_NORMAL_NAME[plane]) {
      throw new Error(
        `--range axis "${parsed.axis}" must match the plane "${plane}" normal axis "${PLANE_NORMAL_NAME[plane]}".`,
      )
    }
    range = { lo: parsed.lo, hi: parsed.hi, step: parsed.step }
  } else if (atArg) {
    coords = atArg
      .split(',')
      .map((value) => Number(value.trim()))
      .filter((value) => Number.isFinite(value))
  }

  const report = await sliceBuild(build.index.manifest, {
    loadMesh: makeLoadMesh(build),
    plane,
    metric,
    resolutionMm,
    minThicknessMm,
    range,
    coords,
    ...filters,
  })
  let highlightUrl: string | null = null
  if (report.overall.atPoint) {
    const highlights = {
      points: [
        {
          point: report.overall.atPoint,
          color: '#f59e0b',
          annotation: `min thickness ≈ ${report.overall.minThicknessMm}mm`,
        },
      ],
    }
    highlightUrl = buildViewerUrl(build, await resolveViewerBaseUrl(options), {
      highlight: JSON.stringify(highlights),
    })
  }
  if (options.json) {
    printJson(apiEnvelope(true, build, `Sliced ${report.sectionCount} section(s) on ${plane}.`, { ...report, highlightUrl }))
  } else {
    printSlice({ ...report, highlightUrl })
  }
}

export const thicknessCommand = async (positional: string[], options: CliOptions) => {
  const buildArg = positional[0]
  if (!buildArg) throw new Error('Missing build directory.')
  const build = await loadBuild(buildArg, optionString(options, 'version'), optionString(options, 'branch'))
  const planeOpt = optionString(options, 'plane')
  const plane: SlicePlane | 'auto' = planeOpt
    ? planeOpt.toLowerCase() === 'auto'
      ? 'auto'
      : parsePlane(planeOpt)
    : 'auto'
  const resolutionMm = parseNumberOption(optionString(options, 'res', 'resolution'), 'res')
  const sections = parseNumberOption(optionString(options, 'sections'), 'sections')
  const minThicknessMm = parseNumberOption(optionString(options, 'min', 'min-thickness'), 'min')

  const report = await thicknessBuild(build.index.manifest, {
    loadMesh: makeLoadMesh(build),
    plane,
    resolutionMm,
    sections,
    minThicknessMm,
    ...geometryFilters(options),
  })
  let highlightUrl: string | null = null
  if (report.atPoint) {
    const highlights = {
      points: [
        {
          point: report.atPoint,
          color: report.passed === false ? '#ff3b30' : '#f59e0b',
          annotation: `min thickness ≈ ${report.minThicknessMm}mm`,
        },
      ],
    }
    highlightUrl = buildViewerUrl(build, await resolveViewerBaseUrl(options), {
      highlight: JSON.stringify(highlights),
    })
  }
  const summary =
    report.minThicknessMm !== null ? `Min thickness ≈ ${report.minThicknessMm}mm.` : 'No thickness measured.'
  if (options.json) {
    printJson(apiEnvelope(true, build, summary, { ...report, highlightUrl }))
  } else {
    printThickness({ ...report, highlightUrl })
  }
}

// `buildviz drawing <build> --part <type>`: schematic orthographic drawing of
// one part as a dimensioned SVG sheet (same generator as the hub MCP tool and
// the viewer's Drawings panel).
export const drawingCommand = async (positional: string[], options: CliOptions) => {
  const buildArg = positional[0]
  if (!buildArg) throw new Error('Missing build directory.')
  const build = await loadBuild(buildArg, optionString(options, 'version'), optionString(options, 'branch'))
  const partRef = optionString(options, 'part')
  if (!partRef) throw new Error('Missing --part <partType|meshId|instanceId>.')

  const { mesh, partType, instanceCount } = resolvePartMesh(build.index.manifest, partRef)
  const bytes = await makeLoadMesh(build)(mesh)
  if (!bytes) throw new Error(`Mesh asset for "${mesh.id}" (${mesh.url ?? 'no url'}) not found.`)

  const drawing = generatePartDrawing(loadMeshGeometry(bytes).geometry, {
    views: parseDrawingViews(optionString(options, 'views')),
    includeHidden: !(options['no-hidden'] ?? options.noHidden),
    title: partType,
    subtitle: `${build.buildId}@${build.branch}@${build.version}`,
  })

  const outArg = optionString(options, 'out')
  const outPath = outArg ? path.resolve(outArg) : null
  if (outPath) await writeFile(outPath, drawing.svg, 'utf8')

  const viewNames = drawing.views.map((view) => view.view).join(', ')
  const summary = `Drew ${partType} (${viewNames}); bbox ${drawing.bboxMm.size.join(' × ')} mm.`
  if (options.json) {
    printJson(
      apiEnvelope(true, build, summary, {
        part: partType,
        meshId: mesh.id,
        instanceCount,
        triangleCount: drawing.triangleCount,
        bboxMm: drawing.bboxMm,
        views: drawing.views,
        ...(outPath ? { outPath } : { svg: drawing.svg }),
      }),
    )
  } else if (outPath) {
    console.log(summary)
    console.log(`Wrote ${outPath}`)
  } else {
    // No --out: the SVG itself is the output (pipe it to a file or a viewer).
    console.log(drawing.svg)
  }
}

// `buildviz section <build> --plane z=0[,z=-4] [--compare <build@ver>]`:
// true cross-section outlines on axis-aligned world planes, rendered as a
// labeled, to-scale SVG figure (grid, legend, filled parts or per-plane
// outlines, dashed compare overlay). Same generator as the hub MCP tool
// get_section_figure. `--out x.png` rasterizes via @resvg/resvg-js.
export const sectionCommand = async (positional: string[], options: CliOptions) => {
  const buildArg = positional[0]
  if (!buildArg) throw new Error('Missing build directory.')
  const build = await loadBuild(buildArg, optionString(options, 'version'), optionString(options, 'branch'))
  const planes = parseSectionPlanes(optionString(options, 'plane'))
  const window = parseSectionWindow(optionString(options, 'window'), planes[0].axis)
  const filters = geometryFilters(options)

  const loadSource = async (
    sourceBuild: Awaited<ReturnType<typeof loadBuild>>,
    label: string,
  ): Promise<{ source: SectionSource; missingMeshes: string[] }> => {
    const manifest: BuildSceneManifest = sourceBuild.index.manifest
    const { instances, missingMeshes } = await buildInstanceGeometries(manifest, {
      loadMesh: makeLoadMesh(sourceBuild),
      ...filters,
    })
    const colors = new Map(manifest.instances.map((instance) => [instance.id, instance.color]))
    return { source: { instances, colors, label }, missingMeshes }
  }

  const { source: baseSource, missingMeshes } = await loadSource(
    build,
    `${build.buildId}@${build.version}`,
  )
  if (baseSource.instances.length === 0) {
    throw new Error('No instances to section (check --part/--instance filters and mesh assets).')
  }

  const compareArg = optionString(options, 'compare')
  let compareSource: SectionSource | undefined
  let compareBuildInfo: { buildId: string; branch: string; version: string } | null = null
  const compareMissing: string[] = []
  if (compareArg) {
    const compareBuild = await loadBuild(compareArg)
    const loaded = await loadSource(compareBuild, `${compareBuild.buildId}@${compareBuild.version}`)
    compareSource = loaded.source
    compareMissing.push(...loaded.missingMeshes)
    // Builds can use different world frames (e.g. a robot-standing scene vs a
    // part-frame concept scene); --compare-offset shifts the compare build into
    // the base build's frame before cutting.
    const offsetArg = optionString(options, 'compare-offset', 'compareOffset')
    if (offsetArg) {
      const parts = offsetArg.split(',').map((value) => Number(value.trim()))
      if (parts.length !== 3 || parts.some((value) => !Number.isFinite(value))) {
        throw new Error(`Invalid --compare-offset "${offsetArg}". Use x,y,z in mm, e.g. 0,0,-40.5.`)
      }
      compareSource = {
        ...compareSource,
        instances: translateInstances(compareSource.instances, parts as [number, number, number]),
      }
    }
    if (compareSource.instances.length === 0) {
      throw new Error(
        `Compare build "${compareArg}" has no sectionable instances` +
          (loaded.missingMeshes.length > 0
            ? ` — ${loaded.missingMeshes.length} mesh asset(s) missing (was it pushed without --upload-assets? point --compare at its on-disk build directory instead).`
            : ' (check the --part/--instance filters).'),
      )
    }
    compareBuildInfo = {
      buildId: compareBuild.buildId,
      branch: compareBuild.branch,
      version: compareBuild.version,
    }
  }

  const figure = generateSectionFigure(
    baseSource,
    {
      planes,
      window,
      title: optionString(options, 'title') ?? `${build.buildId} — section`,
      subtitle:
        `${build.buildId}@${build.branch}@${build.version}` +
        (compareBuildInfo
          ? `  ·  dashed = ${compareBuildInfo.buildId}@${compareBuildInfo.branch}@${compareBuildInfo.version}`
          : ''),
    },
    compareSource,
  )

  const outArg = optionString(options, 'out')
  const outPath = outArg ? path.resolve(outArg) : null
  if (outPath && outPath.toLowerCase().endsWith('.png')) {
    const widthPx = parseNumberOption(optionString(options, 'width'), 'width') ?? 1600
    let resvg: typeof import('@resvg/resvg-js')
    try {
      resvg = await import('@resvg/resvg-js')
    } catch {
      throw new Error(
        'PNG output needs @resvg/resvg-js. Run `npm install @resvg/resvg-js` in the BuildViz repo, or use an .svg --out.',
      )
    }
    const png = new resvg.Resvg(figure.svg, { fitTo: { mode: 'width', value: widthPx } }).render().asPng()
    await writeFile(outPath, png)
  } else if (outPath) {
    await writeFile(outPath, figure.svg, 'utf8')
  }

  const planeSummary = figure.planes
    .map((plane) => `${plane.axis}=${plane.value} (${plane.loopCount} loops, ${plane.areaMm2}mm²)`)
    .join('; ')
  const summary = `Sectioned ${baseSource.instances.length} instance(s): ${planeSummary}.`
  const warnings: Array<{ code: string; meshIds: string[] }> = []
  if (missingMeshes.length > 0) warnings.push({ code: 'missing_meshes', meshIds: missingMeshes })
  if (compareMissing.length > 0) warnings.push({ code: 'missing_compare_meshes', meshIds: compareMissing })
  if (options.json) {
    printJson(
      apiEnvelope(
        true,
        build,
        summary,
        {
          axes: figure.axes,
          window: figure.window,
          planes: figure.planes,
          compare: compareBuildInfo,
          ...(outPath ? { outPath } : { svg: figure.svg }),
        },
        warnings,
      ),
    )
  } else if (outPath) {
    console.log(summary)
    console.log(`Wrote ${outPath}`)
  } else {
    // No --out: the SVG itself is the output (pipe it to a file or a viewer).
    console.log(figure.svg)
  }
}

// `buildviz mass <build>`: estimate weight + weight distribution from the
// meshes (volume × density, with checksConfig.partMassesGrams overrides for
// bought parts). Same engine as the hub MCP tool get_mass_properties.
export const massCommand = async (positional: string[], options: CliOptions) => {
  const buildArg = positional[0]
  if (!buildArg) throw new Error('Missing build directory.')
  const build = await loadBuild(buildArg, optionString(options, 'version'), optionString(options, 'branch'))
  const density = parseNumberOption(optionString(options, 'density'), 'density')
  const report = await massProperties(build.index.manifest, {
    loadMesh: makeLoadMesh(build),
    defaultDensityGCm3: density,
    ...geometryFilters(options),
    includeFasteners: !(options['no-fasteners'] ?? options.noFasteners),
  })
  const kg = report.totalGrams / 1000
  const summary =
    `Estimated ${kg >= 1 ? `${round1(kg)}kg` : `${Math.round(report.totalGrams)}g`} over ` +
    `${report.instanceCount} instance(s); CoM at [${report.centerOfMassMm.join(', ')}]mm.`
  if (options.json) {
    printJson(apiEnvelope(true, build, summary, report))
    return
  }
  console.log(summary)
  console.log(
    `CoM position in bounds (x,y,z fraction): ${report.centerOfMassFraction.join(', ')} · default density ${report.defaultDensityGCm3}g/cm³`,
  )
  if (report.configuredMassPartTypes.length === 0) {
    console.log(
      'Note: no checksConfig.partMassesGrams configured — bought parts (servos, batteries, PCBs) are weighed as solid plastic, which underestimates them.',
    )
  }
  console.log('\nHeaviest part types:')
  for (const entry of report.byPartType.slice(0, 12)) {
    console.log(
      `  ${entry.partType.padEnd(24)} ${String(entry.count).padStart(3)}× ${String(entry.unitGrams).padStart(8)}g = ${String(entry.totalGrams).padStart(9)}g  (${(entry.share * 100).toFixed(1)}%, ${entry.source})`,
    )
  }
  if (report.byGroup.length > 1) {
    console.log('\nBy group:')
    for (const group of report.byGroup) {
      console.log(
        `  ${group.group.padEnd(24)} ${String(group.totalGrams).padStart(9)}g  (${(group.share * 100).toFixed(1)}%)  CoM [${group.centerOfMassMm.join(', ')}]`,
      )
    }
  }
  if (report.missingMeshes.length > 0) {
    console.log(`\nMissing meshes (not weighed): ${report.missingMeshes.join(', ')}`)
  }
}

const round1 = (value: number) => Math.round(value * 10) / 10

export const meshCommand = async (positional: string[], options: CliOptions) => {
  const sub = positional[0]
  if (sub !== 'stats') throw new Error('Usage: buildviz mesh stats <build> [--part <type>] [--no-fasteners] [--json]')
  const buildArg = positional[1]
  if (!buildArg) throw new Error('Missing build directory.')
  const build = await loadBuild(buildArg, optionString(options, 'version'), optionString(options, 'branch'))
  const filters = geometryFilters(options)
  const report = await meshStats(build.index.manifest, {
    loadMesh: makeLoadMesh(build),
    partTypes: filters.partTypes,
    instanceIds: filters.instanceIds,
    // Fasteners are real meshes worth stat-ing, so they are INCLUDED by default
    // here (unlike the interference/probe commands); --no-fasteners drops them.
    includeFasteners: !(options['no-fasteners'] ?? options.noFasteners),
  })
  if (options.json) {
    printJson(
      apiEnvelope(true, build, `${report.meshCount} mesh(es), ${report.totals.nonWatertight} non-watertight.`, report),
    )
  } else {
    printMeshStats(report)
  }
}

