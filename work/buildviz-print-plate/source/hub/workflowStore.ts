import { randomUUID } from 'node:crypto'
import { existsSync } from 'node:fs'
import { readFile, realpath, rename, unlink, writeFile } from 'node:fs/promises'
import path from 'node:path'
import type { WorkflowMetadata } from '../core/buildWorkflows'
import { loadBuild } from './buildLoad'
import { validateWorkflowMetadata } from './buildWorkflows'
import { withCatalogMutation } from './catalogStore'

type StoreDeps = { getBuilds: () => Array<{ id: string; buildDir: string }> }
export type WorkflowWrite = { buildId: string; branch?: string; version?: string; metadata: unknown }

const checkedRef = (value: string | undefined, label: string) => {
  if (value !== undefined && !/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/.test(value)) throw new Error(`Invalid ${label}.`)
  return value
}

export const readStoredWorkflowMetadata = async (deps: StoreDeps, input: Omit<WorkflowWrite, 'metadata'>) => {
  const entry = deps.getBuilds().find((candidate) => candidate.id === input.buildId)
  if (!entry) throw new Error(`No registered build “${input.buildId}”.`)
  const build = await loadBuild(entry.buildDir, checkedRef(input.version, 'version'), checkedRef(input.branch, 'branch'))
  const base = await realpath(entry.buildDir)
  for (const dir of [...new Set([build.buildDir, build.branchDir, build.baseDir])]) {
    const candidate = path.join(dir, 'workflow.json')
    if (!existsSync(candidate)) continue
    const file = await realpath(candidate)
    if (!file.startsWith(`${base}${path.sep}`)) throw new Error('Workflow metadata is outside this build.')
    return { metadata: validateWorkflowMetadata(JSON.parse(await readFile(file, 'utf8'))), inherited: dir !== build.buildDir }
  }
  return { metadata: null, inherited: false }
}

/** Changes manufacturing/document metadata only; never creates a geometry revision. */
export const setBuildWorkflowMetadata = async (deps: StoreDeps, input: WorkflowWrite) => withCatalogMutation(async () => {
  const entry = deps.getBuilds().find((candidate) => candidate.id === input.buildId)
  if (!entry) throw new Error(`No registered build “${input.buildId}”.`)
  const branch = checkedRef(input.branch, 'branch')
  const version = checkedRef(input.version, 'version')
  if (version === 'latest') throw new Error('Omit version for the working copy, or name an exact revision.')
  const metadata: WorkflowMetadata = validateWorkflowMetadata(input.metadata)
  const text = `${JSON.stringify(metadata, null, 2)}\n`
  if (Buffer.byteLength(text) > 4 * 1024 * 1024) throw new Error('Workflow metadata exceeds 4 MB.')
  const build = await loadBuild(entry.buildDir, version, branch)
  if (version && build.buildDir === build.branchDir) throw new Error('This revision has no snapshot. Freeze it first, or omit version to annotate the working copy.')
  const base = await realpath(entry.buildDir)
  const dir = await realpath(build.buildDir)
  if (dir !== base && !dir.startsWith(`${base}${path.sep}`)) throw new Error('Workflow destination is outside this build.')
  const partTypes = new Set(build.index.manifest.instances.map((instance) => instance.partType))
  const unknown = Object.keys(metadata.parts).filter((partType) => !partTypes.has(partType))
  if (unknown.length) throw new Error(`Part types absent from this revision: ${unknown.join(', ')}.`)
  for (const record of [...(metadata.bom?.items ?? []), ...(metadata.instructions ?? []), ...(metadata.runs ?? [])]) {
    if (record.partTypes?.some((partType) => !partTypes.has(partType))) throw new Error(`“${record.id}” references a part type absent from this revision.`)
  }
  const file = path.join(dir, 'workflow.json')
  if (existsSync(file) && await readFile(file, 'utf8') === text) return { ok: true, changed: false, buildId: entry.id, branch: build.branch, version: version ?? null }
  const temporary = path.join(dir, `.workflow-${randomUUID()}.tmp`)
  try {
    await writeFile(temporary, text, { encoding: 'utf8', flag: 'wx' })
    await rename(temporary, file)
  } finally {
    await unlink(temporary).catch(() => undefined)
  }
  return { ok: true, changed: true, buildId: entry.id, branch: build.branch, version: version ?? null }
})
