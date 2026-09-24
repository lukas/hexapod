// Per-part history: an APPEND-ONLY ledger (part_history.json next to each
// branch's meta.json) recording, for every partType in a build, which pushed
// version changed its geometry, design-spec entry, or instance count.
//
// Why a ledger instead of walking versions/ on demand: version retention
// prunes old versions/<name>/ dirs, but the ledger keeps their part events
// forever, so "when did the clamp cap grow its hook?" stays answerable long
// after the snapshot is gone.
//
// Change detection is cheap because pushed meshes are content-addressed: a
// mesh's /builds/_assets/<sha256> URL doubles as its geometry fingerprint
// (register'ed on-disk builds fall back to the raw URL string, which still
// flags renames but not silent in-place edits). Descriptions come from the
// design_spec.yaml `parts:` map snapshotted alongside each version's scene.
//
// The ledger self-heals: `ensurePartHistory` (called on every read and after
// every push) indexes any version dirs not yet in the ledger, and rebuilds
// from the first divergence if an already-indexed version's scene bytes
// changed (an in-place overwrite of the default version).
import { createHash } from 'node:crypto'
import { existsSync } from 'node:fs'
import { readFile, rename, stat, writeFile } from 'node:fs/promises'
import path from 'node:path'
import yaml from 'js-yaml'
import type { BuildSceneManifest } from '../core/buildScene'
import {
  branchRootDir,
  compareVersionNames,
  listVersionDirs,
  readBuildMeta,
  resolveDefaultBranch,
  resolveDefaultVersion,
  resolveBranchDefaultVersion,
  type BuildMeta,
  type CacheVersionMeta,
} from './buildsIndex'

const LEDGER_FILE = 'part_history.json'
const LEDGER_SCHEMA = 1
const MAX_DESCRIPTION_CHARS = 4000

export type PartHistoryEvent = {
  version: string
  pushedAt: string | null
  /** Optional changelog note attached to the version (push -m). */
  message?: string
  /** What changed at this version: added/removed/geometry/description/spec/count. */
  changes: string[]
  /** Content-address (or raw URL) of the part's mesh(es) at this version. */
  meshKey: string | null
  instanceCount: number
  /** The design_spec parts.<type>.description at this version (truncated). */
  description: string | null
}

export type PartHistoryLedger = {
  schema: number
  buildId: string
  branch: string
  updatedAt: string
  /** Versions already folded into the ledger, in indexing order. */
  indexed: Array<{ name: string; sceneSha1: string; pushedAt: string | null }>
  parts: Record<string, PartHistoryEvent[]>
}

type PartState = {
  meshKey: string | null
  instanceCount: number
  description: string | null
  specHash: string | null
}

// ---------------------------------------------------------------------------
// Per-version part-state extraction

const sha1 = (text: string | Buffer) => createHash('sha1').update(text).digest('hex')

// A pushed mesh URL is /builds/_assets/<content-hash>[.ext]; use the hash as
// the geometry key. Anything else (relative path, http URL) is used verbatim.
const meshKeyFromUrl = (url: string | undefined | null): string | null => {
  if (!url) return null
  const assetMatch = url.match(/\/_assets\/([A-Za-z0-9]+)(?:\.[A-Za-z0-9]+)?$/)
  return assetMatch ? assetMatch[1] : url
}

const truncate = (text: string) =>
  text.length > MAX_DESCRIPTION_CHARS ? `${text.slice(0, MAX_DESCRIPTION_CHARS)}…` : text

/** Extract the per-partType state map from one version's scene + spec files. */
const collectPartStates = async (versionDir: string): Promise<Map<string, PartState>> => {
  const manifest = JSON.parse(
    await readFile(path.join(versionDir, 'scene.json'), 'utf8'),
  ) as BuildSceneManifest

  const meshUrlById = new Map<string, string | null>()
  for (const mesh of manifest.meshes ?? []) {
    meshUrlById.set(mesh.id, meshKeyFromUrl(mesh.url) ?? (mesh.primitive ? sha1(JSON.stringify(mesh.primitive)) : null))
  }

  // Design-spec `parts:` map (description + full node hash for change detection).
  let specParts: Record<string, unknown> = {}
  const specPath = path.join(versionDir, 'design_spec.yaml')
  if (existsSync(specPath)) {
    try {
      const spec = yaml.load(await readFile(specPath, 'utf8')) as { parts?: Record<string, unknown> } | null
      if (spec && typeof spec === 'object' && spec.parts && typeof spec.parts === 'object') {
        specParts = spec.parts as Record<string, unknown>
      }
    } catch {
      // An unparseable spec contributes no descriptions for this version.
    }
  }

  const states = new Map<string, PartState>()
  const meshKeys = new Map<string, Set<string>>()
  for (const instance of manifest.instances ?? []) {
    const partType = instance.partType || instance.name || instance.meshId
    if (!partType) continue
    const state = states.get(partType) ?? {
      meshKey: null,
      instanceCount: 0,
      description: null,
      specHash: null,
    }
    state.instanceCount += 1
    const key = meshUrlById.get(instance.meshId)
    if (key) {
      const keys = meshKeys.get(partType) ?? new Set<string>()
      keys.add(key)
      meshKeys.set(partType, keys)
    }
    states.set(partType, state)
  }
  for (const [partType, state] of states) {
    const keys = meshKeys.get(partType)
    // Multiple distinct meshes under one partType (mirrored variants) combine
    // into one stable key so ANY of them changing flags a geometry event.
    state.meshKey = keys && keys.size > 0 ? [...keys].sort().join('+') : null
    const specNode = specParts[partType]
    if (specNode !== undefined) {
      state.specHash = sha1(JSON.stringify(specNode))
      const description =
        specNode && typeof specNode === 'object' && 'description' in (specNode as Record<string, unknown>)
          ? (specNode as Record<string, unknown>).description
          : null
      state.description = typeof description === 'string' ? truncate(description) : null
    }
  }
  return states
}

// ---------------------------------------------------------------------------
// Ledger maintenance

const ledgerPath = (branchDir: string) => path.join(branchDir, LEDGER_FILE)

const readLedger = async (branchDir: string): Promise<PartHistoryLedger | null> => {
  try {
    const ledger = JSON.parse(await readFile(ledgerPath(branchDir), 'utf8')) as PartHistoryLedger
    return ledger.schema === LEDGER_SCHEMA ? ledger : null
  } catch {
    return null
  }
}

const writeLedger = async (branchDir: string, ledger: PartHistoryLedger) => {
  // Write-then-rename so a concurrent read never sees a torn file.
  const tmp = `${ledgerPath(branchDir)}.tmp`
  await writeFile(tmp, `${JSON.stringify(ledger, null, 2)}\n`, 'utf8')
  await rename(tmp, ledgerPath(branchDir))
}

/** Replay events to the last-known state of every part (for diffing onward). */
const replayStates = (parts: Record<string, PartHistoryEvent[]>): Map<string, PartState & { present: boolean }> => {
  const states = new Map<string, PartState & { present: boolean }>()
  for (const [partType, events] of Object.entries(parts)) {
    const last = events[events.length - 1]
    if (!last) continue
    states.set(partType, {
      meshKey: last.meshKey,
      instanceCount: last.instanceCount,
      description: last.description,
      // specHash is not persisted per event; description changes cover the
      // searchable text, and geometry has its own key. Spec-only changes to
      // other fields re-flag on the next full rebuild only.
      specHash: null,
      present: !last.changes.includes('removed'),
    })
  }
  return states
}

const versionMetaMaps = (versionMeta: CacheVersionMeta[] | undefined) => {
  const pushedAt = new Map<string, string>()
  const message = new Map<string, string>()
  for (const entry of versionMeta ?? []) {
    const name = entry.name ?? (entry as unknown as { version?: string }).version
    if (!name) continue
    if (entry.pushedAt) pushedAt.set(name, entry.pushedAt)
    if (typeof entry.message === 'string' && entry.message.length > 0) message.set(name, entry.message)
  }
  return { pushedAt, message }
}

/**
 * Bring one branch's part-history ledger up to date with the version snapshots
 * on disk. Append-only for versions that were pruned from disk; re-indexes
 * from the first on-disk version whose scene bytes no longer match the ledger.
 */
export const ensurePartHistory = async (
  buildDir: string,
  buildId: string,
  branch?: string,
): Promise<PartHistoryLedger> => {
  const meta = await readBuildMeta(buildDir)
  const defaultBranch = resolveDefaultBranch(meta)
  const branchName = branch && branch.trim() ? branch.trim() : defaultBranch
  const branchDir = branchRootDir(buildDir, branchName, defaultBranch)
  if (!existsSync(branchDir)) {
    throw new Error(`No branch "${branchName}" for this build (missing ${path.relative(buildDir, branchDir)}/).`)
  }
  const branchMeta = meta?.branches?.find((entry) => entry.name === branchName)
  const { pushedAt: pushedAtByName, message: messageByName } = versionMetaMaps(
    branchName === defaultBranch ? (meta?.versions ?? branchMeta?.versions) : branchMeta?.versions,
  )
  const defaultVersion =
    branchName === defaultBranch
      ? resolveDefaultVersion(meta)
      : resolveBranchDefaultVersion(meta, branchName)

  // Versions with real snapshot dirs, plus the default version mirrored at the
  // branch root when it has no versions/<name>/ dir of its own.
  const versionDirNames = await listVersionDirs(branchDir)
  const onDisk = versionDirNames.map((name) => ({
    name,
    dir: path.join(branchDir, 'versions', name),
    pushedAt: pushedAtByName.get(name) ?? null,
  }))
  if (!versionDirNames.includes(defaultVersion) && existsSync(path.join(branchDir, 'scene.json'))) {
    onDisk.push({ name: defaultVersion, dir: branchDir, pushedAt: pushedAtByName.get(defaultVersion) ?? null })
  }
  // Index in CONTENT-chronological order: by pushedAt (mtime fallback), with
  // name order as the tiebreak. This matters for in-place overwrites of the
  // default version: the auto-snapshot (e.g. v3) preserves the PRIOR bytes and
  // carries the prior push time, while the overwritten version (v2) is newer —
  // so the true sequence is v1 → v3 → v2, not the name order v1 → v2 → v3.
  for (const entry of onDisk) {
    if (entry.pushedAt) continue
    entry.pushedAt = await stat(path.join(entry.dir, 'scene.json')).then(
      (info) => info.mtime.toISOString(),
      () => null,
    )
  }
  onDisk.sort((a, b) => {
    if (a.pushedAt && b.pushedAt && a.pushedAt !== b.pushedAt) return a.pushedAt < b.pushedAt ? -1 : 1
    return compareVersionNames(a.name, b.name)
  })

  const prior = await readLedger(branchDir)
  const ledger: PartHistoryLedger = prior ?? {
    schema: LEDGER_SCHEMA,
    buildId,
    branch: branchName,
    updatedAt: new Date().toISOString(),
    indexed: [],
    parts: {},
  }
  // The same branch dir can be reached under different addresses (e.g. a
  // directory walk that descends into branches/ sees it as its own "build"),
  // so the labels always reflect THIS caller's canonical address.
  ledger.buildId = buildId
  ledger.branch = branchName

  // Fingerprint every on-disk version's scene bytes.
  const shaByName = new Map<string, string>()
  for (const { name, dir } of onDisk) {
    shaByName.set(name, sha1(await readFile(path.join(dir, 'scene.json'))))
  }

  // Keep the ledger prefix that is still trustworthy: entries for versions no
  // longer on disk (pruned — nothing to re-verify) and on-disk entries whose
  // scene bytes are unchanged AND still sit in the same relative order. Stop
  // at the first mismatch (an in-place overwrite reorders the sequence, since
  // the overwritten version becomes the newest content) and re-index onward.
  const onDiskOrder = onDisk.map((entry) => entry.name)
  let orderCursor = 0
  const keptIndexed: PartHistoryLedger['indexed'] = []
  for (const entry of ledger.indexed) {
    const currentSha = shaByName.get(entry.name)
    if (currentSha === undefined) {
      keptIndexed.push(entry) // Pruned from disk; its events are append-only history.
      continue
    }
    if (currentSha !== entry.sceneSha1) break
    // Strictly consecutive: the ledger's on-disk entries must be EXACTLY the
    // next on-disk versions in chronological order — any skip or reorder means
    // the sequence changed (in-place overwrite / late snapshot) → re-index.
    if (entry.name !== onDiskOrder[orderCursor]) break
    orderCursor += 1
    keptIndexed.push(entry)
  }
  const keptNames = new Set(keptIndexed.map((entry) => entry.name))
  const toProcess = onDisk.filter((entry) => !keptNames.has(entry.name))
  if (toProcess.length === 0 && keptIndexed.length === ledger.indexed.length) {
    if (prior && (prior.buildId !== buildId || prior.branch !== branchName)) {
      await writeLedger(branchDir, ledger)
    }
    return ledger
  }

  // Truncate events back to the kept prefix, then replay forward.
  const parts: Record<string, PartHistoryEvent[]> = {}
  for (const [partType, events] of Object.entries(ledger.parts)) {
    const keptEvents = events.filter((event) => keptNames.has(event.version))
    if (keptEvents.length > 0) parts[partType] = keptEvents
  }
  const states = replayStates(parts)

  for (const { name, dir, pushedAt } of toProcess) {
    let nextStates: Map<string, PartState>
    try {
      nextStates = await collectPartStates(dir)
    } catch {
      continue // A malformed snapshot contributes no events.
    }
    const message = messageByName.get(name)

    for (const [partType, next] of nextStates) {
      const priorState = states.get(partType)
      const changes: string[] = []
      if (!priorState || !priorState.present) changes.push('added')
      else {
        if (priorState.meshKey !== next.meshKey) changes.push('geometry')
        if ((priorState.description ?? null) !== (next.description ?? null)) changes.push('description')
        if (priorState.instanceCount !== next.instanceCount) changes.push('count')
      }
      if (changes.length > 0) {
        const events = parts[partType] ?? (parts[partType] = [])
        events.push({
          version: name,
          pushedAt,
          ...(message ? { message } : {}),
          changes,
          meshKey: next.meshKey,
          instanceCount: next.instanceCount,
          description: next.description,
        })
      }
      states.set(partType, { ...next, present: true })
    }
    // Parts present before but absent now → removed.
    for (const [partType, state] of states) {
      if (!state.present || nextStates.has(partType)) continue
      const events = parts[partType] ?? (parts[partType] = [])
      events.push({
        version: name,
        pushedAt,
        ...(message ? { message } : {}),
        changes: ['removed'],
        meshKey: null,
        instanceCount: 0,
        description: state.description,
      })
      states.set(partType, { ...state, present: false })
    }

    keptIndexed.push({ name, sceneSha1: shaByName.get(name)!, pushedAt })
  }

  const next: PartHistoryLedger = {
    schema: LEDGER_SCHEMA,
    buildId,
    branch: branchName,
    updatedAt: new Date().toISOString(),
    indexed: keptIndexed,
    parts,
  }
  await writeLedger(branchDir, next)
  return next
}

// ---------------------------------------------------------------------------
// Read/query surface

export type PartSummary = {
  partType: string
  present: boolean
  instanceCount: number
  revisionCount: number
  firstSeen: { version: string; pushedAt: string | null } | null
  lastChanged: { version: string; pushedAt: string | null; changes: string[] } | null
  description: string | null
}

export const summarizeParts = (ledger: PartHistoryLedger): PartSummary[] =>
  Object.entries(ledger.parts)
    .map(([partType, events]) => {
      const first = events[0] ?? null
      const last = events[events.length - 1] ?? null
      return {
        partType,
        present: last ? !last.changes.includes('removed') : false,
        instanceCount: last?.instanceCount ?? 0,
        revisionCount: events.length,
        firstSeen: first ? { version: first.version, pushedAt: first.pushedAt } : null,
        lastChanged: last ? { version: last.version, pushedAt: last.pushedAt, changes: last.changes } : null,
        description: last?.description ?? null,
      }
    })
    .sort((a, b) => a.partType.localeCompare(b.partType))

export type PartSearchHit = {
  buildId: string
  branch: string
  partType: string
  /** Events whose own text matched at least one query term. */
  events: PartHistoryEvent[]
  /** Whether the partType NAME itself matched (events may then be empty). */
  nameMatched: boolean
}

const eventText = (event: PartHistoryEvent) =>
  [event.version, event.message ?? '', event.changes.join(' '), event.description ?? '']
    .join('\n')
    .toLowerCase()

/**
 * Search one ledger: every whitespace-separated term must appear somewhere in
 * a part's corpus (build id + branch + part name + all of its events'
 * version/message/changes/description text). Returns the matched parts with
 * the specific events that contain at least one term.
 */
export const searchPartHistory = (ledger: PartHistoryLedger, query: string): PartSearchHit[] => {
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean)
  if (terms.length === 0) return []
  const address = `${ledger.buildId}@${ledger.branch}`.toLowerCase()
  const hits: PartSearchHit[] = []
  for (const [partType, events] of Object.entries(ledger.parts)) {
    const name = partType.toLowerCase()
    const texts = events.map(eventText)
    const corpus = `${address}\n${name}\n${texts.join('\n')}`
    if (!terms.every((term) => corpus.includes(term))) continue
    const matchedEvents = events.filter((_, index) => terms.some((term) => texts[index].includes(term)))
    hits.push({
      buildId: ledger.buildId,
      branch: ledger.branch,
      partType,
      events: matchedEvents,
      nameMatched: terms.some((term) => name.includes(term)),
    })
  }
  return hits.sort((a, b) => b.events.length - a.events.length || a.partType.localeCompare(b.partType))
}

/** All branch names of a build that could carry a ledger (default first). */
export const partHistoryBranches = async (buildDir: string): Promise<string[]> => {
  const meta: BuildMeta | null = await readBuildMeta(buildDir)
  const defaultBranch = resolveDefaultBranch(meta)
  const others = (meta?.branches ?? [])
    .map((entry) => entry.name)
    .filter((name) => name !== defaultBranch)
  return [defaultBranch, ...others]
}
