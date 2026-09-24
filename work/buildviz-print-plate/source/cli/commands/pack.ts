import { existsSync } from 'node:fs'
import { readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import {
  DEFAULT_MARGIN_MM,
  DEFAULT_SPACING_MM,
  DEFAULT_SUPPORT_ANGLE_DEG,
  buildPackedScene,
  parseBed,
  resolvePrinter,
} from '../../checks/buildvizPacking'
import { exportPlateFiles, runPack, type ExportFormat } from '../../checks/packExport'
import {
  optionString,
  type CliOptions,
} from '../../hub/cliShared'
import {
  loadBuild,
  resolveAssetPath,
  apiEnvelope,
  parseNumberOption,
  buildViewerUrl,
} from '../cliBuild'

// `buildviz pack`: plate packing + slicer export orchestration.

export const packBuild = async (
  build: Awaited<ReturnType<typeof loadBuild>>,
  options: CliOptions,
  viewerBaseUrl: string,
) => {
  const manifest = build.index.manifest
  const printerOpt = optionString(options, 'printer')
  const bedOpt = optionString(options, 'bed')
  // A custom --bed wins; otherwise resolve a named printer (default X1C).
  const bed = bedOpt ? parseBed(bedOpt) : resolvePrinter(printerOpt).bed
  const printerId = bedOpt ? null : resolvePrinter(printerOpt).id
  const supportAngleDeg =
    parseNumberOption(optionString(options, 'angle'), 'angle') ?? DEFAULT_SUPPORT_ANGLE_DEG
  const spacingMm =
    parseNumberOption(optionString(options, 'spacing'), 'spacing') ?? DEFAULT_SPACING_MM
  const marginMm = parseNumberOption(optionString(options, 'margin'), 'margin') ?? DEFAULT_MARGIN_MM
  const assembly = optionString(options, 'assembly')

  // Export options: --export writes one Bambu-ingestible file per plate (3MF
  // default, merged STL fallback) into --out (default <build>/plates/).
  const doExport = Boolean(options.export)
  const formatOpt = (optionString(options, 'format') ?? '3mf').toLowerCase()
  if (formatOpt !== '3mf' && formatOpt !== 'stl') {
    throw new Error(`Unknown --format "${formatOpt}". Use 3mf or stl.`)
  }
  const format = formatOpt as ExportFormat

  // Orient + pack the printable (non-fastener) parts, retaining each unique
  // mesh's geometry so an export bakes exactly what the layout shows.
  const { result, meshData, skipped } = await runPack(manifest, {
    loadMesh: async (mesh) => {
      const assetPath = resolveAssetPath(build, mesh.url)
      if (!mesh.url || !existsSync(assetPath)) return null
      const buffer = await readFile(assetPath)
      return buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength) as ArrayBuffer
    },
    bed,
    printerId,
    assembly,
    supportAngleDeg,
    spacingMm,
    marginMm,
  })

  let exportInfo: Awaited<ReturnType<typeof exportPlateFiles>> | null = null
  if (doExport) {
    const outOpt = optionString(options, 'out')
    const outDir = outOpt
      ? path.resolve(process.cwd(), outOpt)
      : path.join(build.buildDir, 'plates')
    exportInfo = await exportPlateFiles({ result, meshData, bed, format, outDir })
  }

  let scenePath: string | null = null
  let viewerUrl: string | null = null
  if (options.emit) {
    const scene = buildPackedScene(result, manifest.name, manifest.meshes)
    scenePath = path.join(build.buildDir, 'buildviz_pack.json')
    await writeFile(scenePath, `${JSON.stringify(scene, null, 2)}\n`, 'utf8')
    // The viewer ?scene= override loads this packed manifest directly; its mesh
    // URLs are reused verbatim from the source build, so the same server serves
    // both. Path mirrors how the build's scene.json is served per version.
    const sceneUrl = build.isDefaultVersion
      ? `/builds/${build.buildId}/buildviz_pack.json`
      : `/builds/${build.buildId}/versions/${build.version}/buildviz_pack.json`
    viewerUrl = buildViewerUrl(build, viewerBaseUrl, { scene: sceneUrl })
  }

  const summary =
    `Packed ${result.totals.partCount} part(s) onto ${result.totals.plateCount} plate(s) on the ` +
    `${printerId ?? 'custom'} bed (${bed.x}×${bed.y}×${bed.z}mm); ${result.totals.partsNeedingSupport} ` +
    `need support, ${result.totals.partsRotated} rotated.` +
    (exportInfo
      ? ` Exported ${exportInfo.files.length} ${exportInfo.format.toUpperCase()} plate file(s) to ${exportInfo.outDir}.`
      : '') +
    (skipped.length > 0 ? ` Skipped ${skipped.length} part(s) with no loadable geometry.` : '')

  const warnings = skipped.length > 0 ? [{ code: 'skipped_parts', instanceIds: skipped }] : []
  return apiEnvelope(
    true,
    build,
    summary,
    { ...result, assembly: assembly ?? null, skipped, scenePath, viewerUrl, export: exportInfo },
    warnings,
  )
}

