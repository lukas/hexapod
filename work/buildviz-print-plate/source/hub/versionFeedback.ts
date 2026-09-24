import { randomUUID } from 'node:crypto'
import { readFile, rename, writeFile, unlink } from 'node:fs/promises'
import path from 'node:path'
import { isDeepStrictEqual } from 'node:util'
import { describeBuildBranches, readBuildMeta, resolveDefaultBranch } from './buildsIndex'
import { serializeBuildMutation } from './publishPolicy'
import {
  FEEDBACK_BASES, FEEDBACK_KINDS, VERSION_LEARNING_GUIDANCE,
  type VersionFeedback, type VersionFeedbackEntry,
} from '../core/versionFeedback'

type Registry = { getBuilds: () => Array<{ id: string; buildDir: string }>; readOnly: boolean }
type Args = Record<string, unknown>

const textField = (raw: unknown, name: string, max: number, required = false) => {
  if (raw === undefined && !required) return undefined
  if (typeof raw !== 'string' || !raw.trim() || raw.trim().length > max) {
    throw new Error(`${name} must be non-empty text, at most ${max} characters.`)
  }
  return raw.trim()
}

const exactName = (raw: unknown, name: string) => {
  const value = textField(raw, name, 160, true)!
  if (!/^[a-z0-9._-]+$/.test(value) || value === '.' || value === '..' || value === 'latest') {
    throw new Error(`${name} must be an exact published name, not a path or "latest" alias.`)
  }
  return value
}

async function target(ctx: Registry, args: Args) {
  const buildId = textField(args.buildId, 'buildId', 500, true)!
  const entry = ctx.getBuilds().find((build) => build.id === buildId)
  if (!entry) throw new Error(`Unknown registered build "${buildId}".`)
  const meta = await readBuildMeta(entry.buildDir)
  const branch = args.branch === undefined ? resolveDefaultBranch(meta) : exactName(args.branch, 'branch')
  const version = exactName(args.version, 'version')
  const branches = await describeBuildBranches(entry.buildDir, meta)
  const versions = branches.find((item) => item.name === branch)?.versions ?? []
  const file = path.join(entry.buildDir, 'version-feedback.json')
  const versionMeta = versions.find((item) => item.name === version)
  // Retention may remove geometry but must not make its recorded lessons
  // inaccessible. Existing findings prove the exact target once existed.
  const hasArchivedFindings = !versionMeta && (await readEntries(file)).some((item) => item.branch === branch && item.version === version)
  if (!versionMeta && !hasArchivedFindings) throw new Error(`Unknown version "${buildId}@${branch}@${version}". Choose an exact published version.`)
  // Lives outside branch roots / version snapshots, so promotion and retention
  // cannot move feedback to a different branch or rewrite published geometry.
  return { buildId, branch, version, versionMeta, versions, file }
}

async function readEntries(file: string): Promise<VersionFeedbackEntry[]> {
  let body: string
  try { body = await readFile(file, 'utf8') } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return []
    throw error
  }
  const log = JSON.parse(body)
  if (log.schema !== 1 || !Array.isArray(log.entries)) throw new Error('Invalid version feedback journal; refusing to replace it.')
  return log.entries
}

const view = (resolved: Awaited<ReturnType<typeof target>>, entries: VersionFeedbackEntry[]): VersionFeedback => ({
  buildId: resolved.buildId, branch: resolved.branch, version: resolved.version,
  ...(resolved.versionMeta?.message ? { message: resolved.versionMeta.message } : {}),
  ...(resolved.versionMeta?.reason ? { reason: resolved.versionMeta.reason } : {}),
  entries: entries.filter((entry) => entry.branch === resolved.branch && entry.version === resolved.version),
  guidance: VERSION_LEARNING_GUIDANCE,
})

export async function readVersionFeedback(ctx: Registry, args: Args) {
  const resolved = await target(ctx, args)
  return view(resolved, await readEntries(resolved.file))
}

export const recordVersionFeedback = (ctx: Registry, args: Args) => serializeBuildMutation(async () => {
  if (ctx.readOnly) throw new Error('Version feedback writes are disabled on this READ-ONLY hub.')
  const resolved = await target(ctx, args)
  if (!FEEDBACK_KINDS.includes(args.kind as VersionFeedbackEntry['kind'])) {
    throw new Error(`kind is required: ${FEEDBACK_KINDS.join(', ')}.`)
  }
  if (!FEEDBACK_BASES.includes(args.basis as VersionFeedbackEntry['basis'])) {
    throw new Error(`basis is required: ${FEEDBACK_BASES.join(', ')}. Do not present a hypothesis as an observed failure.`)
  }
  const message = textField(args.message, 'message', 4000, true)!
  const id = textField(args.id, 'id', 160) ?? randomUUID()
  const evidence = textField(args.evidence, 'evidence', 2000)
  const relatedFeedbackId = textField(args.relatedFeedbackId, 'relatedFeedbackId', 160)
  const relatedVersion = args.relatedVersion === undefined ? undefined : exactName(args.relatedVersion, 'relatedVersion')
  if (relatedVersion && !resolved.versions.some((entry) => entry.name === relatedVersion)) {
    throw new Error(`relatedVersion "${relatedVersion}" must exist on branch "${resolved.branch}".`)
  }
  let parts: string[] | undefined
  if (args.parts !== undefined) {
    if (!Array.isArray(args.parts) || args.parts.length > 50) throw new Error('parts must be an array of at most 50 part identifiers.')
    parts = [...new Set(args.parts.map((part) => textField(part, 'part', 300, true)!))]
  }
  const entries = await readEntries(resolved.file)
  const related = relatedFeedbackId ? entries.find((entry) => entry.id === relatedFeedbackId) : undefined
  if (relatedFeedbackId && (!related || related.branch !== resolved.branch || related.version !== resolved.version)) {
    throw new Error('relatedFeedbackId must identify feedback on this exact branch/version. Record follow-up on the original version.')
  }
  if (args.kind === 'resolution' && (related?.kind !== 'issue' || !evidence || args.basis === 'hypothesis')) {
    throw new Error('A resolution requires relatedFeedbackId of an issue, evidence of validation, and a non-hypothesis basis. Use a note for a proposed fix.')
  }
  const content = {
    id, branch: resolved.branch, version: resolved.version,
    kind: args.kind as VersionFeedbackEntry['kind'], basis: args.basis as VersionFeedbackEntry['basis'], message,
    ...(parts?.length ? { parts } : {}), ...(evidence ? { evidence } : {}),
    ...(relatedVersion ? { relatedVersion } : {}), ...(relatedFeedbackId ? { relatedFeedbackId } : {}),
  }
  const existing = entries.find((entry) => entry.id === id)
  if (existing) {
    if (!isDeepStrictEqual(existing, { ...content, createdAt: existing.createdAt })) throw new Error('Feedback id already exists with different content. Append a new entry; history cannot be edited.')
    return { ...view(resolved, entries), entry: existing, unchanged: true }
  }
  const entry: VersionFeedbackEntry = { ...content, createdAt: new Date().toISOString() }
  const next = [...entries, entry]
  const temporary = `${resolved.file}.${randomUUID()}.tmp`
  try {
    await writeFile(temporary, `${JSON.stringify({ schema: 1, entries: next }, null, 2)}\n`, { flag: 'wx' })
    await rename(temporary, resolved.file)
  } finally {
    await unlink(temporary).catch((error: NodeJS.ErrnoException) => { if (error.code !== 'ENOENT') throw error })
  }
  return { ...view(resolved, next), entry, unchanged: false }
})
