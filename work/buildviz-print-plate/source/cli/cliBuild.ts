import { createHash } from 'node:crypto'
import { existsSync } from 'node:fs'
import { readFile, readdir, stat } from 'node:fs/promises'
import path from 'node:path'
import { CURRENT_SCENE_SCHEMA_VERSION } from '../core/buildScene'
import type { BuildSceneManifest, Vec3 } from '../core/buildScene'
import {
  type SlicePlane,
} from '../checks/buildvizGeometry'
import {
  listBuildVersions,
} from '../hub/buildsIndex'
import {
  optionString,
  projectRoot,
  type CliOptions,
} from '../hub/cliShared'
import {
  ASSET_STORE_ID,
  hubBaseUrl,
  readServerInfo,
  SERVE_DEFAULT_PORT,
} from '../hub/hub'
import { apiEnvelope, loadBuild, resolveAssetPath } from '../hub/buildLoad'

// Shared CLI plumbing: validation, scene-from-STL synthesis, option/vector
// parsing, and highlight URL construction. Used by every command module.
//
// Build loading + the JSON envelope + viewer-URL construction live at the hub
// layer (hub/buildLoad.ts) because the hub's MCP server needs them too and
// hub -> cli is not a legal dependency edge (plans/repo-split.md); they are
// re-exported here so command modules are unchanged.
export {
  resolveBuildDir,
  loadBuild,
  resolveAssetPath,
  apiEnvelope,
  parseNumberOption,
  makeLoadMesh,
  viewerDesignSpecUrl,
  buildViewerUrl,
} from '../hub/buildLoad'

export const fileInfo = async (filePath: string) => {
  if (!existsSync(filePath)) {
    return { path: filePath, exists: false, sizeBytes: null, modifiedAt: null }
  }
  const info = await stat(filePath)
  return {
    path: filePath,
    exists: true,
    sizeBytes: info.size,
    modifiedAt: info.mtime.toISOString(),
  }
}

export const identityTransformAt = (x: number, y: number, z = 0) =>
  [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, x, y, z, 1]

export const toPosixPath = (filePath: string) => filePath.split(path.sep).join('/')

export const slugFromFile = (filePath: string) =>
  path.basename(filePath, path.extname(filePath)).replace(/\.cache$/, '').replaceAll(/[^A-Za-z0-9_ -]+/g, '_')

export const colorForIndex = (index: number) => {
  const palette = [
    '#38bdf8',
    '#f97316',
    '#22c55e',
    '#a78bfa',
    '#f43f5e',
    '#eab308',
    '#14b8a6',
    '#fb7185',
  ]
  return palette[index % palette.length]
}

export const shouldSkipScanDir = (name: string) =>
  name.startsWith('.') ||
  ['__pycache__', 'dist', 'node_modules', 'renders', 'target', 'venv'].includes(name)

export const findStlFiles = async (root: string): Promise<string[]> => {
  const out: string[] = []

  const visit = async (dir: string) => {
    const entries = await readdir(dir, { withFileTypes: true })
    await Promise.all(entries.map(async (entry) => {
      const entryPath = path.join(dir, entry.name)
      if (entry.isDirectory()) {
        if (!shouldSkipScanDir(entry.name)) await visit(entryPath)
        return
      }
      if (entry.isFile() && entry.name.toLowerCase().endsWith('.stl')) {
        out.push(entryPath)
      }
    }))
  }

  await visit(root)
  return out.sort((a, b) => a.localeCompare(b))
}

export const preferredStlDirs = async (buildDir: string) => {
  const names = ['stl', 'stls', 'stl_prototype', 'meshes', 'assets', 'fasteners']
  const dirs: string[] = []
  await Promise.all(names.map(async (name) => {
    const candidate = path.join(buildDir, name)
    try {
      const info = await stat(candidate)
      if (info.isDirectory()) dirs.push(candidate)
    } catch {
      // Missing preferred directories are fine; init can fall back to recursive scanning.
    }
  }))
  return dirs.sort((a, b) => a.localeCompare(b))
}

export const findInitStlFiles = async (buildDir: string, stlDirOption: string | undefined) => {
  if (stlDirOption) {
    const stlDir = path.resolve(buildDir, stlDirOption)
    return findStlFiles(stlDir)
  }

  const dirs = await preferredStlDirs(buildDir)
  if (dirs.length > 0) {
    const nested = await Promise.all(dirs.map((dir) => findStlFiles(dir)))
    return nested.flat().sort((a, b) => a.localeCompare(b))
  }

  return findStlFiles(buildDir)
}

export const sceneFromStls = (
  buildDir: string,
  stlFiles: string[],
  name: string,
): BuildSceneManifest => {
  const spacing = 90
  const columns = Math.max(1, Math.ceil(Math.sqrt(stlFiles.length)))
  const centerOffset = ((columns - 1) * spacing) / 2
  const seenIds = new Map<string, number>()
  const assetIds = stlFiles.map((filePath) => {
    const baseId = slugFromFile(filePath)
    const count = seenIds.get(baseId) ?? 0
    seenIds.set(baseId, count + 1)
    return count === 0 ? baseId : `${baseId}_${count + 1}`
  })

  return {
    name,
    source: buildDir,
    designSpecUrl: 'design_spec.yaml',
    units: 'mm',
    center: [0, 0, 0],
    meshes: stlFiles.map((filePath, index) => {
      const relative = toPosixPath(path.relative(buildDir, filePath))
      return {
        id: assetIds[index],
        name: path.basename(filePath),
        url: relative,
      }
    }),
    instances: stlFiles.map((filePath, index) => {
      const relative = toPosixPath(path.relative(buildDir, filePath))
      const partType = assetIds[index]
      const row = Math.floor(index / columns)
      const column = index % columns
      const x = column * spacing - centerOffset
      const y = row * spacing - centerOffset
      return {
        id: partType,
        meshId: partType,
        name: partType,
        partType,
        role: `STL asset from ${relative}`,
        color: colorForIndex(index),
        transform: identityTransformAt(x, y, 0),
        centroid: [x, y, 0],
        focusGroup: path.dirname(relative) === '.' ? 'root' : toPosixPath(path.dirname(relative)),
      }
    }),
  }
}

export const meshContentHashes = async (build: Awaited<ReturnType<typeof loadBuild>>) => {
  const hashes: Record<string, string> = {}
  await Promise.all(
    build.index.manifest.meshes.map(async (mesh) => {
      if (!mesh.url) return
      const assetPath = resolveAssetPath(build, mesh.url)
      if (!existsSync(assetPath)) return
      hashes[mesh.id] = createHash('sha1').update(await readFile(assetPath)).digest('hex')
    }),
  )
  return hashes
}

export const validateBuild = async (build: Awaited<ReturnType<typeof loadBuild>>) => {
  const warnings: Array<{ code: string; message: string; partType?: string; meshId?: string }> = []
  const errors: Array<{ code: string; message: string; instanceId?: string; meshId?: string }> = []
  const meshIds = new Set<string>()
  const instanceIds = new Set<string>()

  build.index.manifest.meshes.forEach((mesh) => {
    if (meshIds.has(mesh.id)) {
      errors.push({ code: 'duplicate_mesh_id', meshId: mesh.id, message: `Duplicate mesh id: ${mesh.id}` })
    }
    meshIds.add(mesh.id)
    if (mesh.url && !existsSync(resolveAssetPath(build, mesh.url))) {
      errors.push({ code: 'missing_mesh_file', meshId: mesh.id, message: `Missing mesh file: ${mesh.url}` })
    }
    // A relative mesh URL resolves on the local filesystem (so missing_mesh_file
    // passes) but 404s under static hosting unless the scene sets assetsBaseUrl
    // for the viewer to resolve against. Surface that as an actionable warning.
    if (
      mesh.url &&
      !/^[a-z][a-z0-9+.-]*:/i.test(mesh.url) &&
      !mesh.url.startsWith('/') &&
      !build.index.manifest.assetsBaseUrl
    ) {
      warnings.push({
        code: 'relative_mesh_url_static_risk',
        meshId: mesh.id,
        message: `Mesh URL "${mesh.url}" is relative and the scene sets no assetsBaseUrl; it will 404 under static hosting. Use an absolute /builds/... URL or set assetsBaseUrl.`,
      })
    }
  })

  // Explicit scene schemaVersion (optional, additive). Absent → no warning
  // (back-compat). Newer than this BuildViz → forward-incompatible risk; older
  // → may predate fields a check expects. Non-integers are a producer bug.
  const schemaVersion = build.index.manifest.schemaVersion
  if (schemaVersion !== undefined) {
    if (typeof schemaVersion !== 'number' || !Number.isInteger(schemaVersion)) {
      warnings.push({
        code: 'invalid_schema_version',
        message: `scene.schemaVersion must be an integer; got ${JSON.stringify(schemaVersion)}.`,
      })
    } else if (schemaVersion > CURRENT_SCENE_SCHEMA_VERSION) {
      warnings.push({
        code: 'unknown_schema_version',
        message:
          `scene.schemaVersion ${schemaVersion} is newer than this BuildViz supports ` +
          `(${CURRENT_SCENE_SCHEMA_VERSION}); some fields may not render. Update BuildViz.`,
      })
    } else if (schemaVersion < CURRENT_SCENE_SCHEMA_VERSION) {
      warnings.push({
        code: 'old_schema_version',
        message:
          `scene.schemaVersion ${schemaVersion} is older than the current schema ` +
          `(${CURRENT_SCENE_SCHEMA_VERSION}); re-export to pick up the latest scene fields.`,
      })
    }
  }

  build.index.manifest.instances.forEach((instance) => {
    if (instanceIds.has(instance.id)) {
      errors.push({
        code: 'duplicate_instance_id',
        instanceId: instance.id,
        message: `Duplicate instance id: ${instance.id}`,
      })
    }
    instanceIds.add(instance.id)
    if (!meshIds.has(instance.meshId)) {
      errors.push({
        code: 'missing_mesh_reference',
        instanceId: instance.id,
        meshId: instance.meshId,
        message: `${instance.id} references missing mesh ${instance.meshId}`,
      })
    }
    if (instance.transform.length !== 16) {
      errors.push({
        code: 'invalid_transform',
        instanceId: instance.id,
        message: `${instance.id} transform must contain 16 numbers`,
      })
    }
    if (!build.index.designSpec?.parts?.[instance.partType]) {
      warnings.push({
        code: 'missing_design_spec_part',
        partType: instance.partType,
        message: `No design_spec.yaml entry for partType ${instance.partType}`,
      })
    }
  })

  return apiEnvelope(errors.length === 0, build, `Build has ${warnings.length} warnings and ${errors.length} errors.`, {
    meshCount: build.index.manifest.meshes.length,
    instanceCount: build.index.manifest.instances.length,
    partTypeCount: new Set(build.index.manifest.instances.map((instance) => instance.partType)).size,
  }, warnings, errors)
}

// Read a project-authored markdown doc and classify it: present + non-empty
// (pass) vs empty (fail) vs missing (fail). Used for ASSEMBLY.md / BOM.md.
export const parseVec3 = (source: string): Vec3 => {
  const parsed = JSON.parse(source) as unknown
  if (
    Array.isArray(parsed) &&
    parsed.length === 3 &&
    parsed.every((value) => typeof value === 'number' && Number.isFinite(value))
  ) {
    return parsed as Vec3
  }
  throw new Error(`Expected [x,y,z], got: ${source}`)
}

// Accept either bare "x,y,z" (the `identify --point` ergonomic form) or a JSON
// "[x,y,z]" array. Used by commands that take a single coordinate on the CLI.
export const parseLooseVec3 = (source: string): Vec3 => {
  const trimmed = source.trim()
  if (trimmed.startsWith('[')) return parseVec3(trimmed)
  const parts = trimmed.split(',').map((value) => Number(value.trim()))
  if (parts.length === 3 && parts.every((value) => Number.isFinite(value))) {
    return parts as Vec3
  }
  throw new Error(`Expected x,y,z or [x,y,z], got: ${source}`)
}

export const parseLine = (source: string): { from: Vec3; to: Vec3 } => {
  const parsed = JSON.parse(source) as unknown
  if (Array.isArray(parsed) && parsed.length === 2) {
    return { from: parseVec3(JSON.stringify(parsed[0])), to: parseVec3(JSON.stringify(parsed[1])) }
  }
  throw new Error(`Expected [[x,y,z],[x,y,z]], got: ${source}`)
}

export const parseRegion = (source: string): { min: Vec3; max: Vec3 } => {
  if (source.trim().startsWith('{')) {
    const parsed = JSON.parse(source) as { min?: Vec3; max?: Vec3 }
    if (parsed.min && parsed.max) return { min: parsed.min, max: parsed.max }
  }

  const axes = new Map<string, [number, number]>()
  source.split(',').forEach((segment) => {
    const match = segment.trim().match(/^([xyz])=(-?\d+(?:\.\d+)?):(-?\d+(?:\.\d+)?)$/)
    if (!match) throw new Error(`Invalid region segment: ${segment}`)
    axes.set(match[1], [Number(match[2]), Number(match[3])])
  })

  const x = axes.get('x')
  const y = axes.get('y')
  const z = axes.get('z')
  if (!x || !y || !z) throw new Error(`Region must include x, y, and z ranges: ${source}`)
  return { min: [x[0], y[0], z[0]], max: [x[1], y[1], z[1]] }
}

// Parse `--points '[[x,y,z],...]'` (or a single `[x,y,z]`) for `probe points`.
export const parsePoints = (source: string): Vec3[] => {
  const parsed = JSON.parse(source) as unknown
  if (!Array.isArray(parsed)) throw new Error(`Expected an array of [x,y,z] points: ${source}`)
  if (parsed.length === 3 && parsed.every((value) => typeof value === 'number')) {
    return [parseVec3(source)]
  }
  return parsed.map((entry) => parseVec3(JSON.stringify(entry)))
}

export const parsePlane = (value: string | undefined): SlicePlane => {
  const normalized = (value ?? 'xy').toLowerCase()
  if (normalized === 'xy' || normalized === 'yz' || normalized === 'xz') return normalized
  throw new Error(`Unknown --plane "${value}". Use xy, yz, or xz.`)
}

// Parse `--range axis=lo:hi[:step]` (e.g. "x=0:75:2") for the slice sweep.
export const parseRange = (source: string): { axis: 'x' | 'y' | 'z'; lo: number; hi: number; step: number } => {
  const match = source.trim().match(/^([xyz])=(-?\d+(?:\.\d+)?):(-?\d+(?:\.\d+)?)(?::(-?\d+(?:\.\d+)?))?$/)
  if (!match) throw new Error(`Invalid --range "${source}". Use axis=lo:hi[:step], e.g. x=0:75:2.`)
  const lo = Number(match[2])
  const hi = Number(match[3])
  const step = match[4] ? Number(match[4]) : Math.max((hi - lo) / 32, 1e-3)
  return { axis: match[1] as 'x' | 'y' | 'z', lo, hi, step }
}

// Shared `--part` / `--instance` / `--include-fasteners` filters for the
// geometry-query commands (probe / slice / thickness / mesh stats).
export const geometryFilters = (options: CliOptions) => {
  const part = optionString(options, 'part')
  const instance = optionString(options, 'instance')
  const toSet = (value: string | undefined) =>
    value ? new Set(value.split(',').map((entry) => entry.trim()).filter(Boolean)) : undefined
  return {
    includeFasteners: Boolean(options['include-fasteners'] ?? options.includeFasteners),
    partTypes: toSet(part),
    instanceIds: toSet(instance),
  }
}

// Color a probe point by its classification for the viewer overlay.
export const probeColor = (classification: 'solid' | 'hole' | 'void') =>
  classification === 'solid' ? '#22c55e' : classification === 'hole' ? '#f59e0b' : '#94a3b8'

export const highlightSpecFromOptions = (options: CliOptions) => {
  const color = typeof options.color === 'string' ? options.color : undefined
  const partType = typeof options.part === 'string' ? options.part : undefined
  const instanceId = typeof options.instance === 'string' ? options.instance : undefined
  const group = typeof options.group === 'string' ? options.group : undefined
  const label = typeof options.label === 'string' ? options.label : undefined
  const annotation = typeof options.annotation === 'string' ? options.annotation : undefined
  const hasGeometryTarget =
    typeof options.point === 'string' ||
    typeof options.line === 'string' ||
    typeof options.region === 'string'
  const highlights: {
    parts?: unknown[]
    points?: unknown[]
    lines?: unknown[]
    regions?: unknown[]
    annotations?: unknown[]
  } = {}

  if (partType || instanceId || group) {
    highlights.parts = [{ partType, instanceId, group, color, label, annotation: hasGeometryTarget ? undefined : annotation }]
  }
  if (typeof options.point === 'string') {
    highlights.points = [{ point: parseVec3(options.point), partType, instanceId, color, label, annotation }]
  }
  if (typeof options.line === 'string') {
    highlights.lines = [{ ...parseLine(options.line), partType, instanceId, color, label, annotation }]
  }
  if (typeof options.region === 'string') {
    highlights.regions = [{ ...parseRegion(options.region), partType, instanceId, color, label, annotation }]
  }
  if (annotation && !partType && !instanceId && !group && typeof options.point !== 'string') {
    highlights.annotations = [{ text: annotation, color }]
  }

  return highlights
}

// Resolve the base URL for printed/opened viewer links. An explicit --url wins;
// otherwise we ALWAYS resolve the canonical hub from ~/.buildviz/server.json
// (never hardcode a port), falling back to the local serve port only when no
// hub discovery file exists.
export const resolveViewerBaseUrl = async (options: CliOptions) => {
  const explicit = optionString(options, 'url')
  if (explicit) return explicit
  const info = await readServerInfo()
  return info?.baseUrl ?? hubBaseUrl('127.0.0.1', SERVE_DEFAULT_PORT)
}

// Walk a builds root (cache or public/builds) and return every build's id +
// directory. A directory is a build when it has a scene.json or a versions/<name>
// snapshot; never descends into versions/. Used by `versions` (browse) and
// `migrate`.
export const walkBuildDirs = async (root: string): Promise<Array<{ id: string; dir: string }>> => {
  if (!existsSync(root)) return []
  const out: Array<{ id: string; dir: string }> = []

  const visit = async (dir: string, idPrefix: string) => {
    if (idPrefix) {
      const hasScene = existsSync(path.join(dir, 'scene.json'))
      const versions = await listBuildVersions(dir)
      if (hasScene || versions.length > 0) out.push({ id: idPrefix, dir })
    }
    const entries = await readdir(dir, { withFileTypes: true })
    await Promise.all(
      entries
        .filter(
          (entry) =>
            entry.isDirectory() &&
            entry.name !== 'versions' &&
            // The shared content-addressed asset store is not a build.
            !(idPrefix === '' && entry.name === ASSET_STORE_ID),
        )
        .map((entry) =>
          visit(path.join(dir, entry.name), idPrefix ? `${idPrefix}/${entry.name}` : entry.name),
        ),
    )
  }

  await visit(root, '')
  return out
}

export const onDiskBuildsRoot = path.join(projectRoot, 'public', 'builds')

// `buildviz versions [project | project/build | dir]`: browse the project ->
// build -> named-version hierarchy. With no argument, list every project and
// build the hub cache (and on-disk public/builds) know about; with a project,
// filter to it; with a concrete build id/dir, list that build's versions and
// mark the default.
