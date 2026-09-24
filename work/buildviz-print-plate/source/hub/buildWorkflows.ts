import { packParts, resolvePrinter, type PackInputPart } from '../checks/buildvizPacking'
import { buildPlate3mf, type MeshTriData } from '../checks/packExport'
import { createHash } from 'node:crypto'
import { readFile, realpath, stat } from 'node:fs/promises'
import path from 'node:path'
import yaml from 'js-yaml'
import { parseStl } from '../core/geometryEngine'
import type { BuildInstance, BuildSceneManifest } from '../core/buildScene'
import type { CatalogItem } from '../core/catalogModel'
import type {
  BuildWorkflows, WorkflowBomItem, WorkflowInstruction, WorkflowMetadata, WorkflowPart,
  WorkflowPartMetadata, WorkflowProvenance, WorkflowQuery, WorkflowRun,
} from '../core/buildWorkflows'
import { branchRootDir, describeBuildBranches, readBuildMeta, resolveDefaultBranch } from './buildsIndex'
import { readCatalog, type CatalogStoreDeps } from './catalogStore'

export type BuildWorkflowDeps = CatalogStoreDeps & { assetStoreDir: string }
const MAX_ASSET_BYTES = 128 * 1024 * 1024
const MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
const object = (raw: unknown, label: string): Record<string, unknown> => {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw new Error(`${label} must be an object`)
  return raw as Record<string, unknown>
}
const text = (raw: unknown, label: string): string => {
  if (typeof raw !== 'string' || !raw.trim() || raw.length > 30_000) throw new Error(`${label} must be nonempty text of at most 30000 characters`)
  return raw.trim()
}
const identifier = (raw: unknown, label: string, slash = false): string => {
  const value = text(raw, label)
  if (!(slash ? /^[\w][\w./-]*$/ : /^[\w][\w.-]*$/).test(value) || value.split('/').some((piece) => piece === '.' || piece === '..' || !piece)) {
    throw new Error(`${label} must be a safe identifier`)
  }
  return value
}
const link = (raw: unknown, label: string) => {
  const value = text(raw, label)
  if ([...value].some((character) => character === '\\' || character.charCodeAt(0) < 32) || /%5c|%0[0-9a-f]|%1[0-9a-f]/i.test(value)) throw new Error(`${label} contains unsafe URL characters`)
  if (value.startsWith('/') && !value.startsWith('//')) return value
  const url = new URL(value)
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) throw new Error(`${label} requires a root-relative or HTTP(S) URL without credentials`)
  return value
}
const optionalText = (raw: Record<string, unknown>, keys: string[]) => Object.fromEntries(
  keys.filter((key) => raw[key] !== undefined).map((key) => [key, text(raw[key], key)]),
)
const partTypes = (raw: unknown): string[] | undefined => {
  if (raw === undefined) return undefined
  if (!Array.isArray(raw) || !raw.length) throw new Error('partTypes must be a nonempty array')
  return [...new Set(raw.map((value) => text(value, 'partType')))]
}
const list = <T>(raw: unknown, label: string, parse: (value: unknown) => T & { id: string }): T[] => {
  if (!Array.isArray(raw) || raw.length > 10_000) throw new Error(`${label} must be an array of at most 10000 items`)
  const items = raw.map(parse)
  if (new Set(items.map((item) => item.id)).size !== items.length) throw new Error(`${label} has duplicate ids`)
  return items
}

/** Full replacement validation shared by the HTTP/MCP metadata writer. */
export const validateWorkflowMetadata = (raw: unknown): WorkflowMetadata => {
  const value = object(raw, 'Workflow metadata')
  if (value.schema !== 1) throw new Error('Workflow metadata schema must be 1')
  const parts = object(value.parts, 'parts')
  const result: WorkflowMetadata = { schema: 1, parts: Object.create(null) as WorkflowMetadata['parts'] }
  for (const [key, rawPart] of Object.entries(parts)) {
    text(key, 'partType')
    const part = object(rawPart, key)
    if (!['printed', 'purchased', 'other'].includes(String(part.kind))) throw new Error(`${key}.kind must be printed, purchased, or other`)
    result.parts[key] = {
      kind: part.kind as WorkflowPartMetadata['kind'],
      ...optionalText(part, ['label', 'material', 'notes', 'evidence']),
      ...(part.url === undefined ? {} : { url: link(part.url, `${key}.url`) }),
    }
  }
  if (value.bom !== undefined) {
    const bom = object(value.bom, 'bom')
    result.bom = { ...optionalText(bom, ['notes']) }
    if (bom.items !== undefined) result.bom.items = list<WorkflowBomItem>(bom.items, 'bom.items', (rawItem) => {
      const item = object(rawItem, 'BOM item')
      if (typeof item.quantity !== 'number' || !Number.isFinite(item.quantity) || item.quantity <= 0) throw new Error('BOM quantity must be positive')
      return { id: identifier(item.id, 'BOM id'), label: text(item.label, 'BOM label'), quantity: item.quantity,
        ...optionalText(item, ['unit', 'notes']), ...(item.url === undefined ? {} : { url: link(item.url, 'BOM url') }),
        ...(item.partTypes === undefined ? {} : { partTypes: partTypes(item.partTypes) }) }
    })
  }
  if (value.instructions !== undefined) result.instructions = list<WorkflowInstruction>(value.instructions, 'instructions', (rawItem) => {
    const item = object(rawItem, 'Instruction')
    if (item.url === undefined && item.text === undefined) throw new Error('An instruction requires text or a URL')
    return { id: identifier(item.id, 'Instruction id'), title: text(item.title, 'Instruction title'),
      ...optionalText(item, ['text']), ...(item.url === undefined ? {} : { url: link(item.url, 'Instruction url') }),
      ...(item.partTypes === undefined ? {} : { partTypes: partTypes(item.partTypes) }) }
  })
  if (value.runs !== undefined) result.runs = list<WorkflowRun>(value.runs, 'runs', (rawItem) => {
    const item = object(rawItem, 'Run')
    if (item.kind !== undefined && !['mujoco', 'training', 'evaluation', 'other'].includes(String(item.kind))) throw new Error('Invalid run kind')
    if (item.association !== undefined && !['exact-revision', 'robot-family', 'unverified'].includes(String(item.association))) throw new Error('Invalid run association')
    let source: WorkflowRun['source']
    if (item.source !== undefined) {
      const ref = object(item.source, 'Run source')
      source = { buildId: identifier(ref.buildId, 'Run buildId', true),
        ...(ref.branch === undefined ? {} : { branch: identifier(ref.branch, 'Run branch') }),
        ...(ref.version === undefined ? {} : { version: identifier(ref.version, 'Run version') }) }
    }
    if (item.association === 'exact-revision' && (!source?.branch || !source.version || source.version === 'latest')) {
      throw new Error('An exact-revision run requires a concrete source build, branch, and version')
    }
    return { id: identifier(item.id, 'Run id'), title: text(item.title, 'Run title'), url: link(item.url, 'Run url'),
      ...optionalText(item, ['status', 'summary', 'model']), ...(item.videoUrl === undefined ? {} : { videoUrl: link(item.videoUrl, 'Run videoUrl') }),
      ...(item.kind === undefined ? {} : { kind: item.kind as WorkflowRun['kind'] }),
      association: (item.association as WorkflowRun['association']) ?? 'unverified', ...(source ? { source } : {}),
      ...(item.partTypes === undefined ? {} : { partTypes: partTypes(item.partTypes) }) }
  })
  return result
}

const within = (root: string, file: string) => file === root || file.startsWith(`${root}${path.sep}`)
const safeFile = async (root: string, candidate: string) => {
  const rootReal = await realpath(root)
  if (!within(path.resolve(root), path.resolve(candidate))) throw new Error('Asset path escapes its allowed build root')
  const fileReal = await realpath(candidate)
  if (!within(rootReal, fileReal)) throw new Error('Asset symlink escapes its allowed build root')
  return fileReal
}
const maybeFile = async (root: string, candidate: string) => {
  try { return await safeFile(root, candidate) } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return null
    throw error
  }
}

const resolveSource = async (deps: BuildWorkflowDeps, query: WorkflowQuery) => {
  const buildId = identifier(query.build, 'build', true)
  const entry = deps.getBuilds().find((build) => build.id === buildId)
  if (!entry) throw new Error(`Build "${buildId}" is not on this hub`)
  const baseDir = await realpath(entry.buildDir)
  const metaFile = await maybeFile(baseDir, path.join(baseDir, 'meta.json'))
  const meta = metaFile ? await readBuildMeta(baseDir) : null
  const branches = await describeBuildBranches(baseDir, meta)
  const defaultBranch = identifier(resolveDefaultBranch(meta), 'default branch')
  const branch = query.branch ? identifier(query.branch, 'branch') : defaultBranch
  const branchEntry = branches.find((item) => item.name === branch)
  if (!branchEntry) throw new Error(`Unknown branch "${branch}"`)
  const version = identifier(query.version && query.version !== 'latest' ? query.version : branchEntry.defaultVersion, 'version')
  if (!branchEntry.versions.some((item) => item.name === version)) throw new Error(`Unknown revision "${version}"`)
  const branchDir = branchRootDir(baseDir, branch, defaultBranch)
  const snapshot = path.join(branchDir, 'versions', version)
  const snapshotFile = await maybeFile(baseDir, path.join(snapshot, 'scene.json'))
  // A raw current source uses the live root. Exact named sources prefer their snapshot.
  const snapshotSelected = !!query.version && query.version !== 'latest' && !!snapshotFile
  if (!snapshotFile && version !== branchEntry.defaultVersion) throw new Error(`Revision "${version}" has no scene snapshot`)
  const buildDir = snapshotSelected || version !== branchEntry.defaultVersion ? snapshot : branchDir
  const sceneFile = await safeFile(baseDir, path.join(buildDir, 'scene.json'))
  const manifest = JSON.parse(await readFile(sceneFile, 'utf8')) as BuildSceneManifest
  if (!Array.isArray(manifest.instances) || !Array.isArray(manifest.meshes)) throw new Error('Invalid scene manifest')
  return { baseDir, branchDir, buildDir, manifest, versions: branchEntry.versions,
    source: { buildId, branch, version, name: manifest.name || buildId, units: manifest.units,
      storage: (buildDir === branchDir ? 'working-copy' : 'snapshot') as BuildWorkflows['source']['storage'] } }
}
type ResolvedSource = Awaited<ReturnType<typeof resolveSource>>

const readSidecar = async (resolved: ResolvedSource, file: WorkflowProvenance['file']) => {
  const candidates = [resolved.buildDir, resolved.branchDir, resolved.baseDir].filter((dir, index, all) => all.indexOf(dir) === index)
  for (const dir of candidates) {
    const target = await maybeFile(resolved.baseDir, path.join(dir, file))
    if (!target) continue
    const level: WorkflowProvenance['level'] = dir === resolved.buildDir && resolved.source.storage === 'snapshot'
      ? 'exact-revision' : dir === resolved.baseDir && dir !== resolved.branchDir ? 'build-fallback' : 'branch-fallback'
    return { text: await readFile(target, 'utf8'), provenance: { level, file,
      note: level === 'exact-revision' ? `${file} is stored with this revision; this does not verify physical installation.`
        : `${file} comes from the current ${level === 'build-fallback' ? 'build' : 'branch'}, not a record of this revision's assembled hardware.` } satisfies WorkflowProvenance }
  }
  return { text: null, provenance: { level: 'missing', file, note: `No ${file} metadata is available.` } satisfies WorkflowProvenance }
}

/** Only explicit manufacturing evidence is usable; cots flags are known to be unreliable. */
const inferredPart = (raw: unknown): WorkflowPartMetadata | undefined => {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return undefined
  const part = raw as Record<string, unknown>
  const manufacturing = part.manufacturing && typeof part.manufacturing === 'object' ? part.manufacturing as Record<string, unknown> : {}
  const process = String(manufacturing.kind ?? manufacturing.process ?? part.manufacturing ?? '').trim().toLowerCase()
  const kind = ['printed', '3d printed', '3d-printed', 'fdm', 'fff', 'sla', 'sls'].includes(process) ? 'printed'
    : ['purchased', 'off-the-shelf', 'cots'].includes(process) ? 'purchased'
      : ['machined', 'cnc', 'laser-cut', 'other'].includes(process) ? 'other'
        : part.print_orientation !== undefined && part.print_orientation !== null ? 'printed' : undefined
  if (!kind) return undefined
  return { kind, ...(typeof part.label === 'string' ? { label: part.label } : {}),
    ...(typeof part.material === 'string' ? { material: part.material } : {}),
    evidence: process ? `design_spec manufacturing: ${process}` : 'design_spec declares print_orientation' }
}

const assetBytes = async (deps: BuildWorkflowDeps, resolved: ResolvedSource, rawUrl: string) => {
  if (resolved.manifest.assetsBaseUrl && !rawUrl.startsWith('/') && !/^[a-z][a-z\d+.-]*:/i.test(rawUrl)) {
    rawUrl = `${resolved.manifest.assetsBaseUrl.replace(/\/+$/, '')}/${rawUrl.replace(/^\.\//, '')}`
  }
  if (/[?#\0\\]/.test(rawUrl) || /^[a-z][a-z\d+.-]*:/i.test(rawUrl) || rawUrl.startsWith('//')) throw new Error('Only local STL asset paths are supported')
  let url: string
  try { url = decodeURIComponent(rawUrl) } catch { throw new Error('Invalid asset path encoding') }
  if (/[?#\0\\]/.test(url) || url.split('/').some((piece) => piece === '..')) throw new Error('Unsafe asset path')
  if (!/\.stl$/i.test(url)) throw new Error('No STL file is available for this mesh')
  const assetPrefix = '/builds/_assets/'
  const buildPrefix = `/builds/${resolved.source.buildId}/`
  let root = resolved.baseDir
  let candidate: string
  if (url.startsWith(assetPrefix)) {
    root = deps.assetStoreDir
    const relative = url.slice(assetPrefix.length)
    if (!/^[\w.-]+\.stl$/i.test(relative)) throw new Error('Unsafe shared asset path')
    candidate = path.join(root, relative)
  } else if (url.startsWith(buildPrefix)) candidate = path.join(root, url.slice(buildPrefix.length))
  else if (url.startsWith('/')) throw new Error('Asset is outside this build')
  else candidate = path.resolve(resolved.buildDir, url)
  const file = await safeFile(root, candidate)
  const info = await stat(file)
  if (!info.isFile() || info.size > MAX_ASSET_BYTES) throw new Error('STL asset is not a regular file or exceeds the 128 MB download limit')
  return readFile(file)
}
const slug = (value: string) => value.normalize('NFKD').replace(/[^a-zA-Z0-9._-]+/g, '-').replace(/^[.-]+|[.-]+$/g, '').slice(0, 90) || 'part'

/** Canonical parsed STL geometry; exporter headers, normals and facet ordering
 * are irrelevant. Cyclic vertex starts are normalized while winding remains
 * significant. Coordinates use the same exact Float32 representation as the
 * shared STL parser, with no additional rounding/tolerance. */
export const geometryFingerprint = (bytes: Buffer): string => {
  const geometry = parseStl(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer)
  try {
    const positions = geometry.getAttribute('position')
    if (!positions || !positions.count || positions.count % 3) throw new Error('STL has no complete triangles')
    const triangles: Buffer[] = []
    for (let offset = 0; offset < positions.count; offset += 3) {
      const triangle = Buffer.allocUnsafe(36)
      for (let vertex = 0; vertex < 3; vertex += 1) {
        const point = [positions.getX(offset + vertex), positions.getY(offset + vertex), positions.getZ(offset + vertex)]
        for (let axis = 0; axis < 3; axis += 1) {
          const value = point[axis]
          if (!Number.isFinite(value)) throw new Error('STL contains nonfinite coordinates')
          triangle.writeFloatLE(Object.is(value, -0) ? 0 : value, (vertex * 3 + axis) * 4)
        }
      }
      const rotations = [triangle, Buffer.concat([triangle.subarray(12), triangle.subarray(0, 12)]), Buffer.concat([triangle.subarray(24), triangle.subarray(0, 24)])]
      rotations.sort(Buffer.compare)
      triangles.push(rotations[0])
    }
    triangles.sort(Buffer.compare)
    const hash = createHash('sha256')
    for (const triangle of triangles) hash.update(triangle)
    return hash.digest('hex')
  } finally { geometry.dispose() }
}
const endpoint = (name: string, query: WorkflowQuery, extra: Record<string, string> = {}) => {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries({ ...query, ...extra })) if (value !== undefined && value !== '') params.set(key, value)
  return `/__buildviz/workflows${name ? `/${name}` : ''}?${params}`
}

const scopeInstances = (manifest: BuildSceneManifest, item?: CatalogItem, strict = true) => {
  if (!item?.view) return manifest.instances
  const ids = new Set(item.view.instanceIds ?? [])
  const types = new Set(item.view.partTypes ?? [])
  if (strict) {
    for (const id of ids) if (!manifest.instances.some((instance) => instance.id === id)) throw new Error(`Saved selection instance "${id}" is missing from this revision`)
    for (const type of types) if (!manifest.instances.some((instance) => instance.partType === type)) throw new Error(`Saved selection part "${type}" is missing from this revision`)
  }
  return manifest.instances.filter((instance) => ids.has(instance.id) || types.has(instance.partType))
}

const inventory = async (deps: BuildWorkflowDeps, resolved: ResolvedSource, query: WorkflowQuery, instances: BuildInstance[], compareTypes?: Set<string>) => {
  const [workflowSidecar, specSidecar] = await Promise.all([readSidecar(resolved, 'workflow.json'), readSidecar(resolved, 'design_spec.yaml')])
  const metadata = workflowSidecar.text === null ? { schema: 1 as const, parts: {} } : validateWorkflowMetadata(JSON.parse(workflowSidecar.text))
  const specRaw = specSidecar.text ? yaml.load(specSidecar.text) : null
  const spec = specRaw && typeof specRaw === 'object' ? specRaw as { parts?: Record<string, unknown> } : {}
  const parts: WorkflowPart[] = []
  const buffers = new Map<string, Buffer>()
  const meshLoads = new Map<string, Promise<Buffer>>()
  const geometryHashes = new Map<string, string>()
  for (const partType of [...new Set(instances.map((instance) => instance.partType))].sort()) {
    const selected = instances.filter((instance) => instance.partType === partType)
    const explicit = Object.hasOwn(metadata.parts, partType) ? metadata.parts[partType] : undefined
    const inferred = inferredPart(spec.parts?.[partType])
    const classification = explicit ?? inferred
    const part: WorkflowPart = { partType, label: classification?.label ?? partType.replace(/_/g, ' '),
      kind: classification?.kind ?? 'unknown', quantity: selected.length, instanceIds: selected.map((instance) => instance.id),
      classificationSource: explicit ? 'workflow' : inferred ? 'design-spec' : 'unclassified',
      ...(classification ?? {}), files: [], errors: [] }
    // Purchased CAD and unclassified reference meshes are not print downloads.
    // A baseline still hashes a type that is explicitly printable in the target.
    if (part.kind !== 'printed' && !compareTypes?.has(partType)) { parts.push(part); continue }
    const byHash = new Map<string, WorkflowPart['files'][number]>()
    for (const instance of selected) {
      const mesh = resolved.manifest.meshes.find((entry) => entry.id === instance.meshId)
      if (!mesh?.url) {
        if (!part.errors.includes('No STL file is available for one or more selected instances.')) part.errors.push('No STL file is available for one or more selected instances.')
        continue
      }
      try {
        let pending = meshLoads.get(mesh.url)
        if (!pending) { pending = assetBytes(deps, resolved, mesh.url); meshLoads.set(mesh.url, pending) }
        const bytes = await pending
        const hash = createHash('sha256').update(bytes).digest('hex')
        let geometryHash = geometryHashes.get(hash)
        if (!geometryHash) { geometryHash = geometryFingerprint(bytes); geometryHashes.set(hash, geometryHash) }
        const existing = byHash.get(geometryHash)
        if (existing) { existing.quantity += 1; if (!existing.meshIds.includes(mesh.id)) existing.meshIds.push(mesh.id); continue }
        const id = createHash('sha256').update(`${partType}\0${geometryHash}`).digest('hex').slice(0, 24)
        buffers.set(id, bytes)
        byHash.set(geometryHash, { id, sha256: hash, geometrySha256: geometryHash, bytes: bytes.length, fileName: `${slug(part.label)}-${geometryHash.slice(0, 12)}.stl`,
          meshIds: [mesh.id], quantity: 1, previousQuantity: null, quantityToPrint: 0, change: 'unavailable',
          downloadUrl: endpoint('file', query, { file: id }) })
      } catch (error) {
        const code = (error as NodeJS.ErrnoException).code
        const message = code === 'ENOENT' ? 'STL asset is missing.' : code === 'EACCES' ? 'STL asset is unreadable.' : error instanceof Error ? error.message : 'STL asset could not be read.'
        if (!part.errors.includes(message)) part.errors.push(message)
      }
    }
    part.files = [...byHash.values()]
    parts.push(part)
  }
  return { metadata, parts, buffers, units: resolved.source.units, provenance: { workflow: workflowSidecar.provenance, designSpec: specSidecar.provenance } }
}

const readInternal = async (deps: BuildWorkflowDeps, rawQuery: WorkflowQuery) => {
  const resolved = await resolveSource(deps, rawQuery)
  const query: WorkflowQuery = { build: resolved.source.buildId, branch: resolved.source.branch,
    ...(rawQuery.version && rawQuery.version !== 'latest' ? { version: resolved.source.version } : {}), ...(rawQuery.catalog ? { catalog: rawQuery.catalog } : {}) }
  let item: CatalogItem | undefined
  if (rawQuery.catalog) {
    item = (await readCatalog(deps.catalogPath)).items.find((candidate) => candidate.id === rawQuery.catalog || candidate.aliases?.includes(rawQuery.catalog!))
    if (!item) throw new Error(`Unknown catalog item "${rawQuery.catalog}"`)
    const refs = [item.source, item.asBuilt, ...(item.milestones ?? []).map((milestone) => milestone.source)].filter(Boolean)
    if (!refs.some((ref) => ref!.buildId === resolved.source.buildId)) throw new Error('Catalog item does not reference this build')
    if (item.view && (item.source.buildId !== resolved.source.buildId || item.source.branch !== resolved.source.branch || item.source.version !== resolved.source.version)) {
      throw new Error('A saved assembly/view selection must use its exact catalog source revision')
    }
    if (item.view && resolved.source.storage !== 'snapshot') throw new Error('A saved selection requires its exact revision snapshot')
  }
  const selected = scopeInstances(resolved.manifest, item)
  const current = await inventory(deps, resolved, query, selected)
  const availableBaselines = await Promise.all(resolved.versions.filter((entry) => entry.name !== resolved.source.version).map(async (entry) => {
    const version = identifier(entry.name, 'baseline revision')
    return await maybeFile(resolved.baseDir, path.join(resolved.branchDir, 'versions', version, 'scene.json')) ? entry : null
  }))
  const baselines = availableBaselines.filter((entry) => entry !== null)
    .sort((a, b) => (Date.parse(b.pushedAt ?? '') || 0) - (Date.parse(a.pushedAt ?? '') || 0) || a.name.localeCompare(b.name, undefined, { numeric: true }))
  const currentTime = Date.parse(resolved.versions.find((entry) => entry.name === resolved.source.version)?.pushedAt ?? '')
  const previous = Number.isFinite(currentTime) ? baselines.find((entry) => (Date.parse(entry.pushedAt ?? '') || Infinity) < currentTime) : undefined
  const compare = rawQuery.compare === 'none' ? undefined : rawQuery.compare ? identifier(rawQuery.compare, 'compare') : previous?.name
  if (compare === resolved.source.version) throw new Error('Comparison must use a different revision')
  if (compare && !baselines.some((entry) => entry.name === compare)) throw new Error(`Unknown comparison revision "${compare}"`)
  if (compare) query.compare = compare
  else if (rawQuery.compare === 'none') query.compare = 'none'
  const warnings: string[] = []
  if (resolved.source.units !== 'mm') warnings.push(`This scene uses ${resolved.source.units ?? 'unspecified'} units. STL downloads are blocked because Bambu Studio expects millimeters; publish millimeter STL assets first.`)
  const printTypes = new Set(current.parts.filter((part) => part.kind === 'printed').map((part) => part.partType))
  const baseline = compare ? await resolveSource(deps, { ...query, version: compare }).then((source) => inventory(deps, source, query, scopeInstances(source.manifest, item, false), printTypes)) : null
  const comparisonComplete = (!baseline || baseline.units === resolved.source.units) && !baseline?.parts.some((part) => part.errors.length && printTypes.has(part.partType))
  if (!comparisonComplete) warnings.push('The baseline has missing printable assets or incompatible units. Changed STL downloads are unavailable until a complete compatible baseline is provided.')
  for (const part of current.parts) for (const file of part.files) {
    if (!baseline || !comparisonComplete) { file.quantityToPrint = file.quantity; file.change = 'not-compared'; continue }
    const priorPart = baseline.parts.find((entry) => entry.partType === part.partType)
    const priorFile = priorPart?.files.find((entry) => entry.geometrySha256 === file.geometrySha256)
    file.previousQuantity = priorFile?.quantity ?? 0
    file.change = priorFile ? priorFile.quantity === file.quantity ? 'unchanged' : 'quantity' : priorPart ? 'changed' : 'new'
    file.quantityToPrint = priorFile ? Math.max(0, file.quantity - priorFile.quantity) : file.quantity
  }
  const selectedTypes = new Set(selected.map((instance) => instance.partType))
  const applicable = (value: { partTypes?: string[] }) => !value.partTypes || value.partTypes.some((type) => selectedTypes.has(type))
  const scoped = !!item?.view
  const fullySelected = (type: string) => selected.filter((instance) => instance.partType === type).length === resolved.manifest.instances.filter((instance) => instance.partType === type).length
  const bomIncluded = (row: { partTypes?: string[] }) => applicable(row) && (!scoped || !!row.partTypes?.every((type) => selectedTypes.has(type) && fullySelected(type)))
  const duplicatesModeledPart = (row: WorkflowBomItem) => current.parts.some((part) => part.kind === 'purchased' && row.id === part.partType && row.quantity === part.quantity)
  const bomItems = (current.metadata.bom?.items ?? []).filter((row) => bomIncluded(row) && !duplicatesModeledPart(row))
  if (current.metadata.bom?.items?.some(duplicatesModeledPart)) warnings.push('Authored BOM rows that duplicate modeled purchased part IDs and quantities are counted once.')
  if (scoped && current.metadata.bom?.items?.some((row) => !bomIncluded(row))) warnings.push('BOM extras are omitted when their complete part selection is not included; authored quantities cannot be scaled to a partial assembly automatically.')
  const unknown = current.parts.filter((part) => part.kind === 'unknown')
  if (unknown.length) warnings.push(`${unknown.length} part type(s) have no confirmed manufacturing classification and are excluded from print downloads.`)
  const printed = current.parts.filter((part) => part.kind === 'printed')
  if (printed.some((part) => part.errors.length)) warnings.push('Some confirmed printable parts have missing or unsupported STL assets. The archive will report an error rather than silently omit them.')
  const response: BuildWorkflows = {
    schema: 1, source: resolved.source,
    scope: { ...(item ? { catalogId: item.id, name: item.name } : {}), selectedInstances: selected.length, totalInstances: resolved.manifest.instances.length },
    metadata: current.provenance, printed, purchased: current.parts.filter((part) => part.kind === 'purchased'),
    other: current.parts.filter((part) => part.kind === 'other'), unknown,
    bom: { ...(current.metadata.bom?.notes ? { notes: current.metadata.bom.notes } : {}), items: bomItems },
    instructions: (current.metadata.instructions ?? []).filter(applicable), runs: (current.metadata.runs ?? []).filter(applicable).map((run) => {
      if (run.association !== 'exact-revision' || (run.source?.buildId === resolved.source.buildId && run.source.branch === resolved.source.branch && run.source.version === resolved.source.version)) return run
      return { ...run, association: 'unverified' as const, summary: `${run.summary ?? ''} Recorded for ${run.source?.buildId} / ${run.source?.branch} / ${run.source?.version}; this selected revision differs.`.trim() }
    }),
    baselines,
    comparison: { version: compare ?? null, automatic: !rawQuery.compare,
      note: compare ? comparisonComplete ? `Compared STL triangle geometry and quantities with ${compare}; placement, STL header and facet-order changes do not require reprinting.` : 'Comparison is incomplete because baseline printable assets are missing or units differ.'
        : 'No earlier chronological revision is available. Choose a baseline to compare changed STLs.',
      removed: baseline?.parts.flatMap((part) => {
        const quantity = Math.max(0, part.quantity - (current.parts.find((currentPart) => currentPart.partType === part.partType)?.quantity ?? 0))
        return quantity ? [{ partType: part.partType, quantity }] : []
      }) ?? [] },
    downloads: { all: endpoint('download', query, { selection: 'all' }),
      changed: compare && comparisonComplete ? endpoint('download', query, { selection: 'changed' }) : null,
      quantities: endpoint('quantities', query) }, warnings,
  }
  return { response, buffers: current.buffers }
}

export const readBuildWorkflows = async (deps: BuildWorkflowDeps, query: WorkflowQuery): Promise<BuildWorkflows> => (await readInternal(deps, query)).response

const csvCell = (value: unknown) => {
  // Spreadsheet formula injection protection for authored labels/notes.
  let text = value === null || value === undefined ? '' : String(value)
  if (/^[=+@\-\t\r]/.test(text)) text = `'${text}`
  return `"${text.replace(/"/g, '""')}"`
}
const quantities = (response: BuildWorkflows, selection: 'all' | 'changed' = 'all') => {
  const rows: unknown[][] = [['part_type', 'label', 'filename', 'quantity', 'total_quantity', 'previous_quantity', 'change', 'material']]
  for (const part of response.printed) for (const file of part.files) {
    const count = selection === 'changed' ? file.quantityToPrint : file.quantity
    if (!count) continue
    rows.push([part.partType, part.label, archiveName(file.fileName, file.id, count), count, file.quantity, file.previousQuantity, file.change, part.material])
  }
  return Buffer.from(rows.map((row) => row.map(csvCell).join(',')).join('\r\n') + '\r\n', 'utf8')
}
const archiveName = (name: string, id: string, quantity: number) => `${slug(name.replace(/\.stl$/i, ''))}-${id.slice(0, 8)}-qty${quantity}.stl`

// Small stored ZIP writer: no external process, filesystem export, or dependency.
const crcTable = new Uint32Array(256).map((_, index) => {
  let value = index
  for (let bit = 0; bit < 8; bit += 1) value = value & 1 ? 0xedb88320 ^ value >>> 1 : value >>> 1
  return value >>> 0
})
const zip = (entries: Array<{ name: string; data: Buffer }>) => {
  if (entries.length > 65_535 || entries.reduce((sum, entry) => sum + entry.data.length, 0) > MAX_ARCHIVE_BYTES) throw new Error('STL archive exceeds the 512 MB or 65535-file limit')
  const locals: Buffer[] = []; const central: Buffer[] = []; let offset = 0
  for (const entry of entries) {
    const name = Buffer.from(entry.name, 'utf8')
    let crc = 0xffffffff
    for (const byte of entry.data) crc = crcTable[(crc ^ byte) & 255] ^ crc >>> 8
    crc = (crc ^ 0xffffffff) >>> 0
    const header = Buffer.alloc(30)
    header.writeUInt32LE(0x04034b50, 0); header.writeUInt16LE(20, 4); header.writeUInt16LE(0x800, 6)
    header.writeUInt32LE(crc, 14); header.writeUInt32LE(entry.data.length, 18); header.writeUInt32LE(entry.data.length, 22); header.writeUInt16LE(name.length, 26)
    locals.push(header, name, entry.data)
    const record = Buffer.alloc(46)
    record.writeUInt32LE(0x02014b50, 0); record.writeUInt16LE(20, 4); record.writeUInt16LE(20, 6); record.writeUInt16LE(0x800, 8)
    record.writeUInt32LE(crc, 16); record.writeUInt32LE(entry.data.length, 20); record.writeUInt32LE(entry.data.length, 24); record.writeUInt16LE(name.length, 28); record.writeUInt32LE(offset, 42)
    central.push(record, name); offset += header.length + name.length + entry.data.length
  }
  const end = Buffer.alloc(22)
  end.writeUInt32LE(0x06054b50, 0); end.writeUInt16LE(entries.length, 8); end.writeUInt16LE(entries.length, 10)
  end.writeUInt32LE(central.reduce((sum, buffer) => sum + buffer.length, 0), 12); end.writeUInt32LE(offset, 16)
  return Buffer.concat([...locals, ...central, end])
}

export const downloadBuildWorkflows = async (deps: BuildWorkflowDeps, query: WorkflowQuery, selection: 'all' | 'changed') => {
  if (selection !== 'all' && selection !== 'changed') throw new Error('selection must be all or changed')
  const { response, buffers } = await readInternal(deps, query)
  if (response.source.units !== 'mm') throw new Error('STL download requires millimeter scene assets; no implicit unit conversion is performed.')
  if (response.printed.some((part) => part.errors.length)) throw new Error('Cannot create an incomplete print archive: restore missing STL assets listed in the workflow inventory.')
  if (selection === 'changed' && !response.downloads.changed) throw new Error('Changed STL download requires a complete baseline revision')
  const entries = response.printed.flatMap((part) => part.files.flatMap((file) => {
    const count = selection === 'changed' ? file.quantityToPrint : file.quantity
    return count ? [{ name: archiveName(file.fileName, file.id, count), data: buffers.get(file.id)! }] : []
  }))
  if (!entries.length) throw new Error(selection === 'changed' ? 'No added or changed printable STL quantities were found.' : 'No confirmed printable STL files are available.')
  entries.push({ name: 'quantities.csv', data: quantities(response, selection) })
  entries.push({ name: 'README.txt', data: Buffer.from([
    `${response.source.name} — ${response.source.branch} / ${response.source.version}`,
    `Selection: ${response.scope.name ?? 'Full build'}; ${selection} printable STLs.`,
    'Extract the ZIP and import the STL files into Bambu Studio. Set copies using quantities.csv or each filename qty suffix.',
    'Each STL is the original asset geometry; assembly positions are not baked into it. Select material, orientation and print settings in your slicer.',
    selection === 'changed' ? 'For unchanged geometry with increased quantity, only the additional copies are listed.' : 'Quantities describe all selected instances in the source scene.',
    response.comparison.note, response.metadata.workflow.note,
    'This is a design export, not a record of what is physically installed.', '',
  ].join('\n')) })
  return { fileName: `${slug(response.source.buildId)}-${slug(response.source.version)}-${selection}-stls.zip`, bytes: zip(entries) }
}
export const downloadWorkflowFile = async (deps: BuildWorkflowDeps, query: WorkflowQuery, fileId: string) => {
  const { response, buffers } = await readInternal(deps, query)
  if (response.source.units !== 'mm') throw new Error('STL download requires millimeter scene assets; no implicit unit conversion is performed.')
  const file = response.printed.flatMap((part) => part.files).find((file) => file.id === fileId)
  if (!file) throw new Error('Unknown printable file in this build selection')
  // The same link appears in All and Changed; copy counts belong to that table
  // and ZIP, since a filename using total quantity would mislabel added copies.
  return { fileName: file.fileName, bytes: buffers.get(file.id)! }
}
export const downloadWorkflowQuantities = async (deps: BuildWorkflowDeps, query: WorkflowQuery) => {
  const { response } = await readInternal(deps, query)
  return { fileName: `${slug(response.source.buildId)}-${slug(response.source.version)}-quantities.csv`, bytes: quantities(response) }
}

/** Arrange the exact workflow inventory, preserving authored STL print poses. */
export const downloadWorkflowPlate = async (deps: BuildWorkflowDeps, query: WorkflowQuery, selection: 'all' | 'changed', printer: string = 'x1c') => {
  if (selection !== 'all' && selection !== 'changed') throw new Error('selection must be all or changed')
  const { response, buffers } = await readInternal(deps, query)
  if (response.source.units !== 'mm') throw new Error('Plate export requires millimeter assets.')
  if (response.printed.some(part => part.errors.length || !part.files.length)) throw new Error('Restore missing printable assets before exporting a plate.')
  if (selection === 'changed' && !response.downloads.changed) throw new Error('Changed plate requires a complete baseline revision.')
  const { bed, id } = resolvePrinter(printer)
  const inputs: PackInputPart[] = []
  const meshData = new Map<string, MeshTriData>()
  for (const part of response.printed) for (const file of part.files) {
    const count = selection === 'changed' ? file.quantityToPrint : file.quantity
    if (!count) continue
    if (!Number.isInteger(count) || inputs.length + count > 1000) throw new Error('Plate export supports at most 1000 whole pieces.')
    const bytes = buffers.get(file.id)
    if (!bytes) throw new Error('Printable asset unavailable.')
    const geometry = parseStl(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer)
    try {
      geometry.computeBoundingBox()
      const box = geometry.boundingBox!
      const min = box.min.toArray() as [number, number, number], max = box.max.toArray() as [number, number, number]
      if (![...min, ...max].every(Number.isFinite)) throw new Error('Invalid printable geometry bounds.')
      const position = geometry.getAttribute('position')
      const vertices = Array.from({ length: position.count * 3 }, (_, n) => position.array[n])
      const triangles = geometry.index ? Array.from(geometry.index.array) : Array.from({ length: position.count }, (_, n) => n)
      meshData.set(file.id, { vertices, triangles })
      for (let copy = 0; copy < count; copy++) inputs.push({
        instanceId: `${part.partType}-${file.id}-${copy}`, meshId: file.id, partType: part.partType, name: part.label, color: '#aaaaaa',
        orientation: { rotation: [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1], rotationEulerDeg: [0,0,0],
          footprint: { x: max[0]-min[0], y: max[1]-min[1] }, heightMm: max[2]-min[2],
          supportAreaMm2: 0, contactAreaMm2: 0, surfaceAreaMm2: 0, score: 0, kind: 'axis', fitsBed: true, box: { min, max } },
      })
    } finally { geometry.dispose() }
  }
  if (!inputs.length) throw new Error('No printable pieces in this selection.')
  const packed = packParts(inputs, { bed, printer: id, marginMm: 8, spacingMm: 8 })
  const entries = Array.from({ length: packed.totals.plateCount }, (_, plate) => ({
    name: `plate-${plate+1}.3mf`, data: buildPlate3mf(packed.parts.filter(part => part.plate === plate), meshData, plate * (bed.x + Math.max(bed.x, bed.y) * .15)),
  }))
  const stem = `${slug(response.source.buildId)}-${slug(response.source.version)}-${selection}`
  if (entries.length === 1) return { fileName: `${stem}-plate.3mf`, bytes: entries[0].data, contentType: 'model/3mf' }
  entries.push({ name: 'README.txt', data: Buffer.from('Open each 3MF in Bambu Studio. Parts are arranged with their STL orientations and requested quantities. Choose your printer, material and supports, then slice. These files contain no printer or filament settings.') })
  return { fileName: `${stem}-plates.zip`, bytes: zip(entries), contentType: 'application/zip' }
}
