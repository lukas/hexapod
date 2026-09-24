import { existsSync } from 'node:fs'
import { readFile, stat } from 'node:fs/promises'
import path from 'node:path'
import type { BuildSceneManifest } from '../../core/buildScene'
import {
  createBuildIndex,
  parseDesignSpec,
} from '../../core/buildvizCore'
import {
  DEFAULT_VERSION_NAME,
} from '../../hub/buildsIndex'
import {
  printCompat,
  printJson,
  type CompatReport,
  type CompatRequirement,
} from '../cliFormat'
import {
  readJson,
  type CliOptions,
} from '../../hub/cliShared'
import {
  buildIdForDir,
} from '../../hub/hub'
import {
  loadBuild,
  toPosixPath,
  resolveAssetPath,
  validateBuild,
} from '../cliBuild'

// `buildviz compat`: the project-compatibility contract report.

export const checkProjectDoc = async (
  projectDir: string,
  fileName: string,
  label: string,
  purpose: string,
): Promise<CompatRequirement> => {
  const filePath = path.join(projectDir, fileName)
  if (!existsSync(filePath)) {
    return {
      id: fileName,
      label,
      status: 'fail',
      summary: `Missing ${fileName}.`,
      details: [],
      remediation: `Add ${fileName} with ${purpose}.`,
    }
  }
  const text = (await readFile(filePath, 'utf8')).trim()
  if (text.length === 0) {
    return {
      id: fileName,
      label,
      status: 'fail',
      summary: `${fileName} is empty.`,
      details: [],
      remediation: `Fill in ${fileName} with ${purpose}.`,
    }
  }
  return {
    id: fileName,
    label,
    status: 'pass',
    summary: `${fileName} present (${text.length} chars).`,
    details: [],
    remediation: null,
  }
}

// Read a file's mtime in ms, returning null instead of throwing when the file is
// missing or unstatable. Used by the compat staleness heuristic so a missing
// scene/STL just drops out of the comparison rather than crashing the check.
export const safeMtimeMs = async (target: string): Promise<number | null> => {
  try {
    return (await stat(target)).mtimeMs
  } catch {
    return null
  }
}

// Inspect a project directory and report, per requirement, whether it is a
// BuildViz-compatible project (see BUILDVIZ_COMPATIBILITY.md). Purely additive
// and robust: a directory missing everything reports fails, never throws.
export const compatProject = async (
  projectDirArg: string | undefined,
): Promise<CompatReport> => {
  const projectDir = path.resolve(process.cwd(), projectDirArg ?? '.')
  const rel = (target: string) => path.relative(process.cwd(), target) || target
  const requirements: CompatRequirement[] = []

  // Load scene.json without throwing so a missing/broken manifest is reported,
  // not fatal.
  const scenePath = path.join(projectDir, 'scene.json')
  let manifest: BuildSceneManifest | null = null
  let sceneParseError: string | null = null
  if (existsSync(scenePath)) {
    try {
      manifest = await readJson<BuildSceneManifest>(scenePath)
    } catch (error) {
      sceneParseError = error instanceof Error ? error.message : String(error)
    }
  }

  const designSpecPath = path.join(projectDir, 'design_spec.yaml')
  const designSpecText = existsSync(designSpecPath) ? await readFile(designSpecPath, 'utf8') : null
  const buildId = buildIdForDir(projectDir)

  // A minimal build handle mirroring loadBuild's shape for a default-version
  // on-disk build, so we can reuse resolveAssetPath / validateBuild when the
  // manifest parsed.
  const build: Awaited<ReturnType<typeof loadBuild>> | null =
    manifest !== null
      ? {
          baseDir: projectDir,
          buildDir: projectDir,
          branchDir: projectDir,
          buildId,
          branch: DEFAULT_VERSION_NAME,
          defaultBranch: DEFAULT_VERSION_NAME,
          isDefaultBranch: true,
          version: DEFAULT_VERSION_NAME,
          defaultVersion: DEFAULT_VERSION_NAME,
          isDefaultVersion: true,
          designSpecPath: designSpecText !== null ? designSpecPath : null,
          index: createBuildIndex(manifest, designSpecText),
        }
      : null

  // Run the shared manifest validator once; split its findings across the scene
  // and STL requirements below (structural issues vs missing mesh files).
  const validation = build ? await validateBuild(build) : null
  const errors = (validation?.errors ?? []) as Array<{ code: string; message: string }>
  const warnings = (validation?.warnings ?? []) as Array<{ code: string; message: string }>

  // 1) scene.json — present, parses, passes basic manifest validation.
  {
    const structuralCodes = new Set([
      'duplicate_mesh_id',
      'duplicate_instance_id',
      'missing_mesh_reference',
      'invalid_transform',
    ])
    const structuralErrors = errors.filter((error) => structuralCodes.has(error.code))
    const sceneWarnings = warnings.filter((warning) =>
      [
        'relative_mesh_url_static_risk',
        'invalid_schema_version',
        'unknown_schema_version',
        'old_schema_version',
      ].includes(warning.code),
    )
    if (!existsSync(scenePath)) {
      requirements.push({
        id: 'scene.json',
        label: 'scene.json manifest',
        status: 'fail',
        summary: `Missing ${rel(scenePath)}.`,
        details: [],
        remediation:
          'Add a scene.json BuildViz manifest (meshes[] + instances[]); see BUILDVIZ_INTEGRATION.md "scene.json Contract".',
      })
    } else if (sceneParseError || !manifest) {
      requirements.push({
        id: 'scene.json',
        label: 'scene.json manifest',
        status: 'fail',
        summary: 'scene.json did not parse as JSON.',
        details: sceneParseError ? [sceneParseError] : [],
        remediation: 'Fix scene.json so it is valid JSON with meshes[] and instances[].',
      })
    } else if (structuralErrors.length > 0) {
      requirements.push({
        id: 'scene.json',
        label: 'scene.json manifest',
        status: 'fail',
        summary: `scene.json has ${structuralErrors.length} manifest error(s).`,
        details: structuralErrors.slice(0, 20).map((error) => error.message),
        remediation: 'Fix the manifest errors (run `buildviz validate <dir>` for detail).',
      })
    } else if (sceneWarnings.length > 0) {
      requirements.push({
        id: 'scene.json',
        label: 'scene.json manifest',
        status: 'warn',
        summary: `scene.json valid: ${manifest.meshes.length} mesh(es), ${manifest.instances.length} instance(s) (with warnings).`,
        details: sceneWarnings.slice(0, 20).map((warning) => warning.message),
        remediation: null,
      })
    } else {
      requirements.push({
        id: 'scene.json',
        label: 'scene.json manifest',
        status: 'pass',
        summary: `scene.json valid: ${manifest.meshes.length} mesh(es), ${manifest.instances.length} instance(s).`,
        details: [],
        remediation: null,
      })
    }
  }

  // 2) STL folder present + all scene-referenced meshes resolve on disk.
  if (!manifest || !build) {
    requirements.push({
      id: 'stl',
      label: 'STL / mesh assets',
      status: 'fail',
      summary: 'Cannot check meshes without a valid scene.json.',
      details: [],
      remediation: 'Add a valid scene.json first, then a folder of the STL files it references.',
    })
  } else {
    const meshesWithUrl = manifest.meshes.filter((mesh) => typeof mesh.url === 'string' && mesh.url.length > 0)
    const missing = meshesWithUrl.filter((mesh) => !existsSync(resolveAssetPath(build, mesh.url)))
    // Distinct on-disk directories the resolved meshes live in (e.g.
    // "stl_prototype", "fasteners"), for a readable "folder present" summary.
    const meshDirs = [
      ...new Set(
        meshesWithUrl
          .map((mesh) => {
            const resolved = resolveAssetPath(build, mesh.url)
            const relDir = path.dirname(path.relative(projectDir, resolved))
            return relDir === '.' || relDir.startsWith('..') ? '' : toPosixPath(relDir)
          })
          .filter((dir) => dir.length > 0),
      ),
    ]
    if (manifest.meshes.length === 0) {
      requirements.push({
        id: 'stl',
        label: 'STL / mesh assets',
        status: 'fail',
        summary: 'scene.json references no meshes.',
        details: [],
        remediation: 'Add meshes[] to scene.json pointing at STL files, and include those STLs.',
      })
    } else if (missing.length > 0) {
      requirements.push({
        id: 'stl',
        label: 'STL / mesh assets',
        status: 'fail',
        summary: `${missing.length} of ${meshesWithUrl.length} referenced mesh(es) do not resolve on disk.`,
        details: missing.slice(0, 20).map((mesh) => `${mesh.id}: ${mesh.url}`),
        remediation: 'Add the missing STL files (or fix their scene.json mesh urls).',
      })
    } else {
      const folderNote = meshDirs.length > 0 ? ` in ${meshDirs.join(', ')}/` : ''
      requirements.push({
        id: 'stl',
        label: 'STL / mesh assets',
        status: 'pass',
        summary: `All ${meshesWithUrl.length} referenced mesh(es) resolve${folderNote}.`,
        details: [],
        remediation: null,
      })
    }
  }

  // 3) design_spec.yaml present + up-to-date vs the scene's part types.
  {
    const spec = build?.index.designSpec ?? parseDesignSpec(designSpecText)
    if (!existsSync(designSpecPath)) {
      requirements.push({
        id: 'design_spec.yaml',
        label: 'design_spec.yaml',
        status: 'fail',
        summary: `Missing ${rel(designSpecPath)}.`,
        details: [],
        remediation: 'Add design_spec.yaml with a parts: entry for each part type in the scene (see DESIGN_YAML_SPEC.md).',
      })
    } else if (!spec) {
      requirements.push({
        id: 'design_spec.yaml',
        label: 'design_spec.yaml',
        status: 'fail',
        summary: 'design_spec.yaml did not parse as a YAML mapping.',
        details: [],
        remediation: 'Fix design_spec.yaml so it parses as a YAML mapping with a parts: section.',
      })
    } else if (!spec.parts || Object.keys(spec.parts).length === 0) {
      requirements.push({
        id: 'design_spec.yaml',
        label: 'design_spec.yaml',
        status: 'fail',
        summary: 'design_spec.yaml has no parts: section.',
        details: [],
        remediation: 'Add a parts: section with an entry per part type in the scene.',
      })
    } else if (!manifest) {
      requirements.push({
        id: 'design_spec.yaml',
        label: 'design_spec.yaml',
        status: 'warn',
        summary: 'design_spec.yaml present; coverage unverified (no valid scene.json).',
        details: [],
        remediation: null,
      })
    } else {
      const scenePartTypes = [...new Set(manifest.instances.map((instance) => instance.partType))]
      const specParts = Object.keys(spec.parts)
      const missingSpec = scenePartTypes.filter((partType) => !specParts.includes(partType))
      const extraSpec = specParts.filter((partType) => !scenePartTypes.includes(partType))

      // Staleness heuristic: the spec should be at least as new as the scene and
      // the geometry it describes. If scene.json or any referenced STL was
      // modified more recently than design_spec.yaml, the rationale/dimensions may
      // no longer match. mtimes are read defensively — a missing/unstatable file
      // simply drops out of the comparison and never crashes the check.
      const specMtime = await safeMtimeMs(designSpecPath)
      const newerSources: string[] = []
      if (specMtime !== null) {
        const sceneMtime = await safeMtimeMs(scenePath)
        if (sceneMtime !== null && sceneMtime > specMtime) {
          newerSources.push('scene.json')
        }
        let anyStlNewer = false
        if (build) {
          for (const mesh of manifest.meshes) {
            if (typeof mesh.url !== 'string' || mesh.url.length === 0) continue
            const stlMtime = await safeMtimeMs(resolveAssetPath(build, mesh.url))
            if (stlMtime !== null && stlMtime > specMtime) {
              anyStlNewer = true
              break
            }
          }
        }
        if (anyStlNewer) newerSources.push('referenced STL geometry')
      }
      const stale = newerSources.length > 0

      const details: string[] = []
      if (missingSpec.length > 0) {
        details.push(
          `${missingSpec.length} scene part(s) with NO design_spec entry (uncovered — this fails): ${missingSpec.slice(0, 20).join(', ')}`,
        )
      }
      if (extraSpec.length > 0) {
        details.push(
          `${extraSpec.length} spec entrie(s) with no matching scene part (stale drift): ${extraSpec.slice(0, 20).join(', ')}`,
        )
      }
      if (stale) {
        details.push(
          `design_spec.yaml may be out of date: ${newerSources.join(' and ')} changed more recently — confirm rationale/dimensions still match.`,
        )
      }

      if (missingSpec.length > 0) {
        // Uncovered scene parts are the core "the agent dropped it" case: an
        // incomplete spec means a part with no recorded intent. This blocks.
        requirements.push({
          id: 'design_spec.yaml',
          label: 'design_spec.yaml',
          status: 'fail',
          summary: `design_spec.yaml is incomplete: ${missingSpec.length} scene part(s) have no entry.`,
          details,
          remediation: `Add a design_spec entry (rationale, dimensions, features) for each uncovered scene part: ${missingSpec.slice(0, 20).join(', ')}. Keep design_spec.yaml updated in the same change that alters geometry.`,
        })
      } else if (extraSpec.length > 0 || stale) {
        const summaryParts: string[] = []
        if (stale) summaryParts.push('may be out of date vs the scene/geometry')
        if (extraSpec.length > 0) summaryParts.push('has stale entries with no matching scene part')
        const remediationParts: string[] = []
        if (stale) {
          remediationParts.push(
            're-check design_spec.yaml against the current scene/STLs and update any changed rationale/dimensions (edit it in the same change as the geometry)',
          )
        }
        if (extraSpec.length > 0) {
          remediationParts.push('remove or rename the stale spec entries so design_spec matches the scene')
        }
        requirements.push({
          id: 'design_spec.yaml',
          label: 'design_spec.yaml',
          status: 'warn',
          summary: `design_spec.yaml ${summaryParts.join(' and ')}.`,
          details,
          remediation: `${remediationParts.join('; ')}.`,
        })
      } else {
        requirements.push({
          id: 'design_spec.yaml',
          label: 'design_spec.yaml',
          status: 'pass',
          summary: `design_spec.yaml covers all ${scenePartTypes.length} scene part type(s).`,
          details: [],
          remediation: null,
        })
      }
    }
  }

  // 4) + 5) Project-authored ASSEMBLY.md + BOM.md (present + non-empty).
  requirements.push(
    await checkProjectDoc(projectDir, 'ASSEMBLY.md', 'ASSEMBLY.md', 'assembly directions'),
  )
  requirements.push(await checkProjectDoc(projectDir, 'BOM.md', 'BOM.md', 'the bill of materials'))

  const failCount = requirements.filter((requirement) => requirement.status === 'fail').length
  const warnCount = requirements.filter((requirement) => requirement.status === 'warn').length
  const passCount = requirements.filter((requirement) => requirement.status === 'pass').length
  const compatible = failCount === 0
  const remediation = requirements
    .filter((requirement) => requirement.status === 'fail' && requirement.remediation)
    .map((requirement) => requirement.remediation as string)

  return {
    ok: true,
    compatible,
    projectDir: rel(projectDir),
    buildId,
    summary:
      `${compatible ? 'COMPATIBLE' : 'NOT COMPATIBLE'}: ` +
      `${passCount} pass · ${warnCount} warn · ${failCount} fail of ${requirements.length} requirement(s).`,
    requirements,
    remediation,
  }
}

export const compatCommand = async (positional: string[], options: CliOptions) => {
  const report = await compatProject(positional[0])
  if (options.json) {
    printJson(report)
  } else {
    printCompat(report)
  }
}

