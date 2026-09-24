// Persistence + part resolution for DIAGRAMS (see core/diagramModel.ts).
//
// Diagrams are standalone presentation documents, stored hub-side under
// ~/.buildviz/diagrams/<name>/ as diagram.json + meta.json (+ assets/ with
// content-hashed STL snapshots for placed build parts). They are deliberately
// NOT builds: no branches, no versions, no checks — just a canvas an agent
// composes over MCP and the human opens at /?diagram=<name>.
//
// `part` elements reference a build part (buildId + partType/mesh/instance).
// At write time the referenced mesh bytes are snapshotted into the diagram's
// own assets/ dir (content-addressed, so re-writes dedupe), which keeps every
// diagram self-contained: it keeps rendering even if the source build is
// re-pushed, pruned, or deleted.

import { existsSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { mkdir, readdir, rm, unlink, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { canonicalizeVersionName } from '../core/buildModel'
import { resolvePartMesh } from '../core/schematicDrawing'
import {
  validateDiagramDocument,
  type DiagramCamera,
  type DiagramDocument,
  type DiagramElement,
  type DiagramPart,
} from '../core/diagramModel'
import { loadBuild, makeLoadMesh } from './buildLoad'
import { buildvizHome, readJson } from './cliShared'

export const diagramsRoot = path.join(buildvizHome, 'diagrams')
export const diagramDirFor = (name: string) => path.join(diagramsRoot, name)

export type DiagramMeta = {
  name: string
  title: string
  createdAt: string
  updatedAt: string
  elementCount: number
}

/** Registry access the store needs to resolve part references (hub provides it). */
export type DiagramStoreDeps = {
  getBuilds: () => Array<{ id: string; buildDir: string }>
}

export const canonicalizeDiagramName = (raw: unknown): string => {
  const name = canonicalizeVersionName(String(raw ?? ''))
  if (!name) {
    throw new Error('Diagram "name" must contain at least one letter or digit (it becomes the URL slug).')
  }
  return name
}

export const listDiagrams = async (): Promise<DiagramMeta[]> => {
  if (!existsSync(diagramsRoot)) return []
  const entries = await readdir(diagramsRoot, { withFileTypes: true })
  const diagrams: DiagramMeta[] = []
  for (const entry of entries) {
    if (!entry.isDirectory()) continue
    const dir = path.join(diagramsRoot, entry.name)
    if (!existsSync(path.join(dir, 'diagram.json'))) continue
    const meta = await readJson<DiagramMeta>(path.join(dir, 'meta.json')).catch(() => null)
    diagrams.push({
      name: entry.name,
      title: meta?.title ?? entry.name,
      createdAt: meta?.createdAt ?? '',
      updatedAt: meta?.updatedAt ?? '',
      elementCount: meta?.elementCount ?? 0,
    })
  }
  return diagrams.sort((a, b) => (b.updatedAt || '').localeCompare(a.updatedAt || ''))
}

export const readDiagram = async (
  name: string,
): Promise<{ meta: DiagramMeta | null; doc: DiagramDocument }> => {
  const dir = diagramDirFor(canonicalizeDiagramName(name))
  const docPath = path.join(dir, 'diagram.json')
  if (!existsSync(docPath)) {
    const known = (await listDiagrams()).map((diagram) => diagram.name).join(', ')
    throw new Error(`No diagram "${name}" on this hub. Known diagrams: ${known || '(none)'}`)
  }
  const doc = await readJson<DiagramDocument>(docPath)
  const meta = await readJson<DiagramMeta>(path.join(dir, 'meta.json')).catch(() => null)
  return { meta, doc }
}

// Snapshot one part element's mesh into the diagram's assets dir and return the
// element with its resolved `mesh` filled in. Content-addressed file names make
// this idempotent across re-writes and shared between elements.
const resolvePartElement = async (
  deps: DiagramStoreDeps,
  name: string,
  element: DiagramPart,
): Promise<DiagramPart> => {
  const entry = deps.getBuilds().find((build) => build.id === element.buildId.trim())
  if (!entry) {
    const known = deps.getBuilds().map((build) => build.id).join(', ')
    throw new Error(
      `Diagram element "${element.id}": no build "${element.buildId}" on this hub. Known builds: ${known || '(none)'}`,
    )
  }
  const build = await loadBuild(entry.buildDir, element.version, element.branch)
  const manifest = build.index.manifest
  let resolved: ReturnType<typeof resolvePartMesh>
  try {
    resolved = resolvePartMesh(manifest, element.part)
  } catch (error) {
    throw new Error(
      `Diagram element "${element.id}": ${error instanceof Error ? error.message : String(error)}`,
      { cause: error },
    )
  }
  const sourceColor = manifest.instances.find((instance) => instance.meshId === resolved.mesh.id)?.color

  const bytes = await makeLoadMesh(build)(resolved.mesh)
  if (bytes) {
    const buffer = Buffer.from(bytes)
    const hash = createHash('sha256').update(buffer).digest('hex')
    const fileName = `${hash}.stl`
    const assetsDir = path.join(diagramDirFor(name), 'assets')
    if (!existsSync(path.join(assetsDir, fileName))) {
      await mkdir(assetsDir, { recursive: true })
      await writeFile(path.join(assetsDir, fileName), buffer)
    }
    return {
      ...element,
      mesh: {
        url: `/diagrams/${encodeURIComponent(name)}/assets/${fileName}`,
        ...(sourceColor ? { sourceColor } : {}),
        partType: resolved.partType,
      },
    }
  }
  if (resolved.mesh.primitive) {
    return {
      ...element,
      mesh: {
        primitive: resolved.mesh.primitive,
        ...(sourceColor ? { sourceColor } : {}),
        partType: resolved.partType,
      },
    }
  }
  throw new Error(
    `Diagram element "${element.id}": mesh bytes for "${resolved.mesh.id}" are not on this hub ` +
      '(push the build with --upload-assets) and the mesh has no primitive fallback.',
  )
}

const resolveDocumentParts = async (
  deps: DiagramStoreDeps,
  name: string,
  doc: DiagramDocument,
): Promise<DiagramDocument> => {
  const elements: DiagramElement[] = []
  for (const element of doc.elements) {
    elements.push(element.kind === 'part' ? await resolvePartElement(deps, name, element) : element)
  }
  return { ...doc, elements }
}

// Drop asset files no element references anymore, so a heavily-iterated diagram
// does not accumulate stale part snapshots.
const pruneUnreferencedAssets = async (name: string, doc: DiagramDocument) => {
  const assetsDir = path.join(diagramDirFor(name), 'assets')
  if (!existsSync(assetsDir)) return
  const referenced = new Set(
    doc.elements.flatMap((element) =>
      element.kind === 'part' && element.mesh?.url ? [path.basename(element.mesh.url)] : [],
    ),
  )
  for (const entry of await readdir(assetsDir)) {
    if (!referenced.has(entry)) await unlink(path.join(assetsDir, entry)).catch(() => undefined)
  }
}

const persist = async (
  name: string,
  doc: DiagramDocument,
  priorMeta: DiagramMeta | null,
): Promise<DiagramMeta> => {
  const dir = diagramDirFor(name)
  const now = new Date().toISOString()
  const meta: DiagramMeta = {
    name,
    title: doc.title,
    createdAt: priorMeta?.createdAt || now,
    updatedAt: now,
    elementCount: doc.elements.length,
  }
  await mkdir(dir, { recursive: true })
  await writeFile(path.join(dir, 'diagram.json'), `${JSON.stringify(doc, null, 2)}\n`)
  await writeFile(path.join(dir, 'meta.json'), `${JSON.stringify(meta, null, 2)}\n`)
  await pruneUnreferencedAssets(name, doc)
  return meta
}

/** Create a diagram, or fully replace one that already exists (same name). */
export const createDiagram = async (
  deps: DiagramStoreDeps,
  rawName: unknown,
  input: unknown,
): Promise<{ meta: DiagramMeta; doc: DiagramDocument; isNew: boolean }> => {
  const name = canonicalizeDiagramName(rawName)
  const doc = await resolveDocumentParts(deps, name, validateDiagramDocument(input))
  const priorMeta = await readJson<DiagramMeta>(path.join(diagramDirFor(name), 'meta.json')).catch(
    () => null,
  )
  const meta = await persist(name, doc, priorMeta)
  return { meta, doc, isNew: priorMeta === null }
}

export type DiagramPatch = {
  title?: unknown
  notes?: unknown
  background?: unknown
  camera?: unknown
  upsertElements?: unknown
  removeElementIds?: unknown
}

/** Apply a partial update: retitle, replace notes/camera, upsert or remove
 *  elements by id. Everything not mentioned is left untouched. */
export const updateDiagram = async (
  deps: DiagramStoreDeps,
  rawName: unknown,
  patch: DiagramPatch,
): Promise<{ meta: DiagramMeta; doc: DiagramDocument }> => {
  const name = canonicalizeDiagramName(rawName)
  const { meta: priorMeta, doc: prior } = await readDiagram(name)

  const removeIds = new Set(
    Array.isArray(patch.removeElementIds) ? patch.removeElementIds.map(String) : [],
  )
  const upserts = Array.isArray(patch.upsertElements)
    ? (patch.upsertElements as DiagramElement[])
    : []
  const upsertIds = new Set(
    upserts.map((element) => (element as { id?: unknown })?.id).filter((id) => typeof id === 'string'),
  )
  const elements = [
    ...prior.elements.filter((element) => !removeIds.has(element.id) && !upsertIds.has(element.id)),
    ...upserts,
  ]

  const missing = [...removeIds].filter((id) => !prior.elements.some((element) => element.id === id))
  if (missing.length > 0) {
    throw new Error(
      `removeElementIds not in diagram "${name}": ${missing.join(', ')}. ` +
        `Present ids: ${prior.elements.map((element) => element.id).join(', ') || '(none)'}`,
    )
  }

  const candidate: Record<string, unknown> = {
    ...prior,
    ...(patch.title !== undefined ? { title: patch.title } : {}),
    ...(patch.notes !== undefined ? { notes: patch.notes === null ? undefined : patch.notes } : {}),
    ...(patch.background !== undefined
      ? { background: patch.background === null ? undefined : patch.background }
      : {}),
    ...(patch.camera !== undefined
      ? { camera: patch.camera === null ? undefined : (patch.camera as DiagramCamera) }
      : {}),
    elements,
  }
  // JSON round-trip drops the keys explicitly cleared to undefined above.
  const doc = await resolveDocumentParts(
    deps,
    name,
    validateDiagramDocument(JSON.parse(JSON.stringify(candidate))),
  )
  const meta = await persist(name, doc, priorMeta)
  return { meta, doc }
}

export const deleteDiagram = async (rawName: unknown): Promise<void> => {
  const name = canonicalizeDiagramName(rawName)
  const dir = diagramDirFor(name)
  if (!existsSync(path.join(dir, 'diagram.json'))) {
    const known = (await listDiagrams()).map((diagram) => diagram.name).join(', ')
    throw new Error(`No diagram "${name}" on this hub. Known diagrams: ${known || '(none)'}`)
  }
  await rm(dir, { recursive: true, force: true })
}
