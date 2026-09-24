import { existsSync } from 'node:fs'
import { mkdir, readFile, rename, rm, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { randomUUID } from 'node:crypto'
import type { BuildSceneManifest } from '../core/buildScene'
import {
  CATALOG_KINDS, CATALOG_STATUSES,
  type Catalog, type CatalogItem, type CatalogRevision, type CatalogSource,
} from '../core/catalogModel'
import { branchRootDir, describeBuildBranches, readBuildMeta, resolveDefaultBranch } from './buildsIndex'
import { buildvizHome } from './cliShared'

export const catalogPath = path.join(buildvizHome, 'catalog.json')
export type CatalogStoreDeps = {
  getBuilds: () => Array<{ id: string; buildDir: string }>
  /** Isolated store path for embedded callers and tests. */
  catalogPath?: string
}

// Catalog validation and publication share this queue: a pin cannot appear
// halfway through a push's overwrite/retention operation.
let mutationTail: Promise<unknown> = Promise.resolve()
export const withCatalogMutation = <T>(action: () => Promise<T>): Promise<T> => {
  const result = mutationTail.then(action)
  mutationTail = result.catch(() => undefined)
  return result
}

export const readCatalog = async (file = catalogPath): Promise<Catalog> => {
  let body: string
  try { body = await readFile(file, 'utf8') } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return { schema: 1, items: [] }
    throw error
  }
  const value = JSON.parse(body) as Catalog
  if (value.schema !== 1 || !Array.isArray(value.items)) throw new Error(`Invalid catalog at ${file}`)
  return value
}

const object = (raw: unknown, label: string): Record<string, unknown> => {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw new Error(`${label} must be an object`)
  return raw as Record<string, unknown>
}
const text = (raw: unknown, label: string): string => {
  if (typeof raw !== 'string' || !raw.trim()) throw new Error(`${label} must be nonempty text`)
  if (raw.length > 10_000) throw new Error(`${label} is too long`)
  return raw.trim()
}
const referenceName = (raw: unknown, label: string, allowSlash = false) => {
  const value = text(raw, label)
  if (!(allowSlash ? /^[a-zA-Z0-9][a-zA-Z0-9._/-]*$/ : /^[a-zA-Z0-9][a-zA-Z0-9._-]*$/).test(value) ||
      value.split('/').some((part) => !part || part === '.' || part === '..')) {
    throw new Error(`${label} must be a safe identifier`)
  }
  return value
}
const textArray = (raw: unknown, label: string) => {
  if (!Array.isArray(raw)) throw new Error(`${label} must be an array`)
  return [...new Set(raw.map((value) => text(value, label)))]
}

export const resolveCatalogSource = async (
  deps: CatalogStoreDeps, raw: unknown, label: string, pinned = false,
  requireSnapshot = true,
): Promise<{ source: CatalogSource; manifest: BuildSceneManifest }> => {
  const value = object(raw, label)
  const buildId = referenceName(value.buildId, `${label}.buildId`, true)
  const entry = deps.getBuilds().find((build) => build.id === buildId)
  if (!entry) throw new Error(`${label}: build "${buildId}" is not on this hub`)
  const meta = await readBuildMeta(entry.buildDir)
  const branches = await describeBuildBranches(entry.buildDir, meta)
  const requestedBranch = value.branch === undefined ? undefined : referenceName(value.branch, `${label}.branch`)
  if (pinned && !requestedBranch) throw new Error(`${label} requires a concrete branch and version`)
  const branch = requestedBranch ?? resolveDefaultBranch(meta)
  const branchEntry = branches.find((entry) => entry.name === branch)
  if (!branchEntry) throw new Error(`${label}: no branch "${branch}" in "${buildId}"`)
  const requestedVersion = value.version === undefined ? undefined : referenceName(value.version, `${label}.version`)
  if ((pinned && !requestedVersion) || requestedVersion === 'latest') {
    throw new Error(`${label} requires a concrete version; "latest" is not a revision`)
  }
  const version = requestedVersion ?? branchEntry.defaultVersion
  if (!branchEntry.versions.some((entry) => entry.name === version)) {
    throw new Error(`${label}: no revision "${version}" on ${buildId}@${branch}`)
  }
  const dir = branchRootDir(entry.buildDir, branch, resolveDefaultBranch(meta))
  const snapshot = path.join(dir, 'versions', version, 'scene.json')
  if (!existsSync(snapshot) && (version !== branchEntry.defaultVersion || (requestedVersion && requireSnapshot))) {
    throw new Error(`${label}: revision ${buildId}@${branch}@${version} has no immutable snapshot; freeze it before pinning`)
  }
  const file = existsSync(snapshot) ? snapshot : path.join(dir, 'scene.json')
  const manifest = JSON.parse(await readFile(file, 'utf8')) as BuildSceneManifest
  return {
    source: { buildId, ...(requestedBranch || requestedVersion ? { branch } : {}),
      ...(requestedVersion ? { version } : {}) },
    manifest,
  }
}

export const validateCatalogItem = async (
  deps: CatalogStoreDeps, raw: unknown,
  publication?: { source: CatalogSource; manifest: BuildSceneManifest },
): Promise<CatalogItem> => {
  const value = object(raw, 'Catalog item')
  const id = referenceName(value.id, 'id', true)
  if (!CATALOG_KINDS.includes(value.kind as CatalogItem['kind'])) throw new Error(`${id}: invalid kind`)
  if (!CATALOG_STATUSES.includes(value.status as CatalogItem['status'])) throw new Error(`${id}: invalid status`)
  const kind = value.kind as CatalogItem['kind']
  const { source, manifest } = publication ?? await resolveCatalogSource(deps, value.source, `${id}.source`, kind === 'view' || value.view !== undefined)
  const item: CatalogItem = {
    id, name: text(value.name, `${id}.name`), kind,
    collection: text(value.collection, `${id}.collection`),
    description: text(value.description, `${id}.description`),
    status: value.status as CatalogItem['status'], source,
  }
  if (value.parentId !== undefined) item.parentId = referenceName(value.parentId, `${id}.parentId`, true)
  if (value.aliases !== undefined) item.aliases = textArray(value.aliases, `${id}.aliases`)
  if (value.asBuilt !== undefined) {
    if (kind !== 'robot') throw new Error(`${id}: only robots have an asBuilt configuration`)
    const asBuilt = object(value.asBuilt, `${id}.asBuilt`)
    const resolved = await resolveCatalogSource(deps, asBuilt, `${id}.asBuilt`, true)
    item.asBuilt = resolved.source as CatalogRevision
    if (asBuilt.evidence !== undefined) item.asBuilt.evidence = text(asBuilt.evidence, `${id}.asBuilt.evidence`)
  }
  if (value.milestones !== undefined) {
    if (!Array.isArray(value.milestones)) throw new Error(`${id}.milestones must be an array`)
    item.milestones = await Promise.all(value.milestones.map(async (rawMilestone) => {
      const milestone = object(rawMilestone, `${id}.milestone`)
      const resolved = await resolveCatalogSource(deps, milestone.source, `${id}.milestone.source`, true)
      return { name: text(milestone.name, `${id}.milestone.name`),
        description: text(milestone.description, `${id}.milestone.description`),
        source: resolved.source as CatalogRevision }
    }))
  }
  if (value.view !== undefined || kind === 'view') {
    if (kind !== 'view' && kind !== 'assembly') throw new Error(`${id}: selection is only valid on a view or assembly`)
    const view = object(value.view, `${id}.view`)
    item.view = {}
    if (view.instanceIds !== undefined) item.view.instanceIds = textArray(view.instanceIds, `${id}.view.instanceIds`)
    if (view.partTypes !== undefined) item.view.partTypes = textArray(view.partTypes, `${id}.view.partTypes`)
    if (!item.view.instanceIds?.length && !item.view.partTypes?.length) {
      throw new Error(`${id}: a view requires at least one instanceId or partType`)
    }
    const instances = new Set(manifest.instances.map((instance) => instance.id))
    const partTypes = new Set(manifest.instances.map((instance) => instance.partType))
    for (const instance of item.view.instanceIds ?? []) {
      if (!instances.has(instance)) throw new Error(`${id}: instance "${instance}" is absent from the pinned revision`)
    }
    for (const part of item.view.partTypes ?? []) {
      if (!partTypes.has(part)) throw new Error(`${id}: partType "${part}" is absent from the pinned revision`)
    }
  }
  return item
}

export const validateCatalogRelationships = (items: CatalogItem[]) => {
  const byId = new Map(items.map((item) => [item.id, item]))
  const aliases = new Set(byId.keys())
  for (const item of items) {
    for (const alias of item.aliases ?? []) {
      if (aliases.has(alias)) throw new Error(`Catalog alias "${alias}" is ambiguous`)
      aliases.add(alias)
    }
    const seen = new Set([item.id])
    let current = item
    while (current.parentId) {
      if (seen.has(current.parentId)) throw new Error(`Catalog parent cycle at "${item.id}"`)
      const parent = byId.get(current.parentId)
      if (!parent) throw new Error(`${current.id}: parent "${current.parentId}" does not exist`)
      if (parent.kind === 'view') throw new Error(`${current.id}: a view cannot contain catalog items`)
      if (parent.collection !== current.collection) throw new Error(`${current.id}: parent must be in the same collection`)
      seen.add(parent.id)
      current = parent
    }
  }
}

export const writeCatalogAtomically = async (catalog: Catalog, file = catalogPath) => {
  await mkdir(path.dirname(file), { recursive: true })
  const temporary = `${file}.${randomUUID()}.tmp`
  try {
    await writeFile(temporary, `${JSON.stringify(catalog, null, 2)}\n`, 'utf8')
    await rename(temporary, file)
  } finally { await rm(temporary, { force: true }) }
}

/** Caller already holds withCatalogMutation (used when publishing + classifying). */
export const upsertCatalogItemsUnlocked = async (deps: CatalogStoreDeps, rawItems: unknown): Promise<Catalog> => {
  if (!Array.isArray(rawItems) || rawItems.length === 0) throw new Error('items must be a nonempty array')
  const incoming = await Promise.all(rawItems.map((item) => validateCatalogItem(deps, item)))
  if (new Set(incoming.map((item) => item.id)).size !== incoming.length) throw new Error('Duplicate item ids in catalog update')
  const previous = await readCatalog(deps.catalogPath)
  const byId = new Map(previous.items.map((item) => [item.id, item]))
  for (const item of incoming) {
    const prior = byId.get(item.id)
    // An ordinary metadata update does not accidentally clear physical evidence.
    byId.set(item.id, { ...item,
      ...(prior?.asBuilt && !item.asBuilt ? { asBuilt: prior.asBuilt } : {}),
      ...(prior?.milestones && !item.milestones ? { milestones: prior.milestones } : {}),
    })
  }
  const catalog: Catalog = { schema: 1, items: [...byId.values()] }
  validateCatalogRelationships(catalog.items)
  await writeCatalogAtomically(catalog, deps.catalogPath)
  return catalog
}
export const upsertCatalogItems = (deps: CatalogStoreDeps, rawItems: unknown) =>
  withCatalogMutation(() => upsertCatalogItemsUnlocked(deps, rawItems))

export const pinnedCatalogRevisions = (catalog: Catalog): CatalogRevision[] => {
  const pins = new Map<string, CatalogRevision>()
  for (const item of catalog.items) {
    const sources = [item.source, item.asBuilt, ...(item.milestones ?? []).map((milestone) => milestone.source)]
    for (const source of sources) {
      if (source?.branch && source.version) {
        const pin = source as CatalogRevision
        pins.set(JSON.stringify([pin.buildId, pin.branch, pin.version]), pin)
      }
    }
  }
  return [...pins.values()]
}

export const assertCatalogRevisionWritable = async (
  reference: CatalogRevision, priorScene: string | null, nextScene: string,
  priorSpec: string | null, nextSpec: string | null, file = catalogPath,
) => {
  const pinned = pinnedCatalogRevisions(await readCatalog(file)).some((pin) =>
    pin.buildId === reference.buildId && pin.branch === reference.branch && pin.version === reference.version)
  if (!pinned) return
  const sameScene = priorScene !== null && JSON.stringify(JSON.parse(priorScene)) === JSON.stringify(JSON.parse(nextScene))
  if (!sameScene || (nextSpec !== null && nextSpec !== priorSpec)) {
    throw new Error(`${reference.buildId}@${reference.branch}@${reference.version} is pinned by the catalog; publish a new revision instead`)
  }
}
