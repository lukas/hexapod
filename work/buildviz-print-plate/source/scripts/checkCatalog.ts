// Isolated hub HTTP/MCP integration check. No listening sockets or live data.
import assert from 'node:assert/strict'
import { existsSync } from 'node:fs'
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { Readable } from 'node:stream'
import type { IncomingMessage, ServerResponse } from 'node:http'
import type { CatalogItem } from '../core/catalogModel'

const temporaryHome = await mkdtemp(path.join(os.tmpdir(), 'buildviz-catalog-test-'))
process.env.BUILDVIZ_HOME = temporaryHome
const { serveHubAsset, cacheBuildDir } = await import('../hub/hub')
const { readCatalog, upsertCatalogItems } = await import('../hub/catalogStore')
type Registry = Parameters<typeof serveHubAsset>[2] extends () => infer T ? T : never
const registry: Registry = { builds: [] }
let assertions = 0
const check = (condition: unknown, label: string) => { assert.ok(condition, label); assertions += 1 }

const request = async (method: string, url: string, payload?: unknown, options: { readOnly?: boolean; authenticated?: boolean } = {}) => {
  const incoming = Object.assign(Readable.from(payload === undefined ? [] : [Buffer.from(JSON.stringify(payload))]), {
    method, url, headers: { host: '127.0.0.1:5183', ...(options.authenticated === false ? {} : { 'x-api-key': 'test-secret' }) },
  }) as unknown as IncomingMessage
  const headers: Record<string, unknown> = {}
  let body = ''
  const outgoing = {
    statusCode: 200,
    setHeader: (name: string, value: unknown) => { headers[name] = value },
    end: (value?: unknown) => { body = value === undefined ? '' : String(value) },
  }
  const handled = await serveHubAsset(incoming, outgoing as unknown as ServerResponse,
    () => registry, 'http://127.0.0.1:5183', new Date().toISOString(), options.readOnly ?? false, 'test-secret')
  assert.equal(handled, true)
  return { status: outgoing.statusCode, body: body ? JSON.parse(body) : undefined, headers }
}
const mcp = async (name: string, args: Record<string, unknown> = {}, readOnly = false) => {
  const response = await request('POST', '/mcp', {
    jsonrpc: '2.0', id: 1, method: 'tools/call', params: { name, arguments: args },
  }, { readOnly })
  const result = response.body.result as { isError?: boolean; content: Array<{ text: string }> }
  return { error: result.isError ?? false, result: result.isError ? result.content[0].text : JSON.parse(result.content[0].text) }
}
const scene = (name = 'Test robot') => ({
  name, units: 'mm', center: [0, 0, 0],
  meshes: [{ id: 'plate', name: 'Plate', primitive: { kind: 'box', size: [10, 10, 1] } }],
  instances: [{ id: 'chassis', meshId: 'plate', name: 'Chassis', partType: 'body', role: 'structure', color: '#aaa',
    transform: [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1] }],
})
const push = (version: string, extra: Record<string, unknown> = {}) => request('POST', '/__buildviz/push', {
  buildId: 'test/robot', version, setDefault: true, scene: scene(version),
  message: `Record ${version} chassis design for mounting review.`, ...extra,
})

try {
  check((await push('v1')).status === 200, 'initial geometry publication succeeds')
  const workflowMetadata = { schema: 1, parts: { body: { kind: 'printed', evidence: 'Fixture fabrication record.' } }, instructions: [{ id: 'assembly', title: 'Assembly', text: 'Attach the printed chassis using the fixture mounting holes.' }] }
  check((await mcp('set_workflows', { buildId: 'test/robot', metadata: workflowMetadata })).error === false,
    'MCP writes authored workflows independently of geometry')
  const workflows = await mcp('get_workflows', { buildId: 'test/robot' })
  check(!workflows.error && workflows.result.printed.length === 1 && workflows.result.authoredMetadata.instructions.length === 1,
    'MCP workflows expose classified parts and preserve complete authored metadata for updates')
  check((await mcp('set_workflows', { buildId: 'test/robot', metadata: workflowMetadata }, true)).error,
    'workflow writes obey read-only mode')
  check((await request('POST', '/__buildviz/workflows', { buildId: 'test/robot', metadata: workflowMetadata }, { authenticated: false })).status === 401,
    'HTTP workflow writes require authentication')
  check((await mcp('set_workflows', { buildId: 'test/robot', metadata: { schema: 1, parts: { absent: { kind: 'printed' } } } })).error,
    'classification cannot reference a part absent from the selected revision')
  check((await mcp('set_workflows', { buildId: 'test/robot', branch: '../escape', metadata: workflowMetadata })).error,
    'workflow metadata path traversal is rejected')
  check((await mcp('set_workflows', { buildId: 'test/robot', metadata: { ...workflowMetadata, instructions: [{ id: 'bad', title: 'Unsafe', url: 'javascript:alert(1)' }] } })).error,
    'workflow reference URLs cannot execute script')
  check((await push('invalid', { message: 'update' })).status === 400, 'generic revision message rejected')
  const source = { buildId: 'test/robot', branch: 'main', version: 'v1' }
  const robot: CatalogItem = {
    id: 'robot-one', name: 'Robot one', kind: 'robot', collection: 'Robots', status: 'built',
    description: 'The robot assembled for the test fixture.', source: { buildId: 'test/robot' },
    asBuilt: { ...source, evidence: 'Fixture assembled in this test.' }, aliases: ['old-robot-name'],
  }
  const catalogWrite = await request('POST', '/__buildviz/catalog', { items: [robot] })
  check(catalogWrite.status === 200 && catalogWrite.body.items.length === 1, 'catalog roundtrip creates classified robot')
  const liveRoot = path.join(cacheBuildDir('test/robot'), 'scene.json')
  const originalRoot = await readFile(liveRoot, 'utf8')
  await writeFile(liveRoot, JSON.stringify(scene('External working copy change')))
  check((await mcp('get_scene', source)).result.name === 'v1',
    'explicit default revision reads its snapshot instead of a changed working root')
  await writeFile(liveRoot, originalRoot)
  check((await request('GET', '/__buildviz/catalog', undefined, { readOnly: true, authenticated: false })).body.items[0].id === robot.id,
    'catalog is viewable without write credentials in read-only mode')
  check((await request('POST', '/__buildviz/catalog', { items: [robot] }, { authenticated: false })).status === 401,
    'catalog mutation requires API key')
  check((await request('POST', '/__buildviz/catalog', { items: [robot] }, { readOnly: true })).status === 403,
    'catalog mutation respects read-only mode')
  const reboundDirectory = path.join(temporaryHome, 'other-robot')
  await mkdir(reboundDirectory)
  await writeFile(path.join(reboundDirectory, 'scene.json'), JSON.stringify(scene('Unrelated geometry')))
  check((await request('POST', '/__buildviz/register', { buildId: 'test/robot', buildDir: reboundDirectory })).status === 400,
    'register cannot rebind a catalog identity to other geometry')
  check((await request('POST', '/__buildviz/register', { buildId: 'test/robot', buildDir: cacheBuildDir('test/robot') })).status === 200,
    'same-directory registration remains supported')
  const before = await readFile(path.join(temporaryHome, 'catalog.json'), 'utf8')
  const invalid = await request('POST', '/__buildviz/catalog', { items: [
    { ...robot, name: 'Should not be saved' }, { ...robot, id: 'bad-source', source: { buildId: 'absent' } },
  ] })
  check(invalid.status === 400 && await readFile(path.join(temporaryHome, 'catalog.json'), 'utf8') === before,
    'invalid batch changes nothing')
  const view = await mcp('create_view', {
    id: 'body-view', name: 'Body inspection', parentId: robot.id, description: 'Inspect the chassis attachment points.',
    source, instanceIds: ['chassis'],
  })
  check(!view.error && view.result.item.kind === 'view', 'MCP creates view without publishing geometry')
  check((await mcp('create_view', {
    id: 'bad-view', name: 'Missing part', parentId: robot.id, description: 'Inspect missing part.', source, instanceIds: ['absent'],
  })).error, 'view rejects missing instance')
  check((await mcp('create_view', {
    id: 'floating-view', name: 'Floating view', parentId: robot.id, description: 'Inspect current chassis.',
    source: { buildId: 'test/robot', branch: 'main', version: 'latest' }, partTypes: ['body'],
  })).error, 'view rejects moving latest alias')
  check((await mcp('upsert_catalog_item', { item: { ...robot, parentId: 'body-view' } })).error,
    'catalog rejects invalid parent/cycle')
  check((await mcp('get_catalog_item', { id: 'old-robot-name' })).result.id === robot.id, 'MCP resolves aliases')
  const filtered = await mcp('list_catalog', { kind: 'view', query: 'attachment' })
  check(!filtered.error && filtered.result.items.length === 1, 'MCP filters type and descriptive search')
  check((await mcp('upsert_catalog_item', { item: robot }, true)).error, 'MCP writes respect read-only mode')
  check((await push('v1', { scene: scene('Changed pinned geometry') })).status === 409, 'pinned geometry cannot be overwritten')
  check((await push('v1', { scene: scene('v1'), designSpec: 'changed spec' })).status === 409, 'pinned design spec cannot be overwritten')
  check((await push('v2')).status === 200, 'new revision preserves as-built source')
  check((await push('v3', { keepVersions: 1 })).status === 200, 'retention publication succeeds')
  check(existsSync(path.join(cacheBuildDir('test/robot'), 'versions', 'v1', 'scene.json')), 'retention preserves catalog pin')
  check(!existsSync(path.join(cacheBuildDir('test/robot'), 'versions', 'v2', 'scene.json')), 'retention still removes unpinned old revisions')
  const current = await readCatalog()
  check(current.items.find((item) => item.id === robot.id)?.asBuilt?.version === 'v1', 'current design updates do not move as-built evidence')
  const missingSnapshot = await request('POST', '/__buildviz/catalog', { items: [{
    ...robot, id: 'bad-revision', asBuilt: { ...source, version: 'v999' },
  }] })
  check(missingSnapshot.status === 400, 'pin to missing revision rejected')
  // Clear a legacy description, then add metadata without changing its date/scene.
  const metaFile = path.join(cacheBuildDir('test/robot'), 'meta.json')
  const legacyMeta = JSON.parse(await readFile(metaFile, 'utf8'))
  const originalTime = legacyMeta.versions.find((version: { name: string }) => version.name === 'v1').pushedAt
  for (const version of legacyMeta.versions) if (version.name === 'v1') delete version.message
  for (const branch of legacyMeta.branches) for (const version of branch.versions) if (version.name === 'v1') delete version.message
  await writeFile(metaFile, JSON.stringify(legacyMeta))
  const pinnedSceneBefore = await readFile(path.join(cacheBuildDir('test/robot'), 'versions/v1/scene.json'), 'utf8')
  const backfill = await request('PATCH', '/__buildviz/revisions/metadata', {
    ...source, message: 'Record the original chassis plate before mounting changes.', ifMessageMissing: true,
  })
  check(backfill.status === 200 && backfill.body.updated, 'legacy revision description backfills without new geometry')
  const repeat = await request('PATCH', '/__buildviz/revisions/metadata', {
    ...source, message: 'This description must not replace the existing explanation.', ifMessageMissing: true,
  })
  check(!repeat.body.updated, 'description backfill preserves existing text')
  const inspected = await mcp('get_build', source)
  check(!inspected.error && inspected.result.revision.messageSource === 'retrospective' && inspected.result.revision.pushedAt === originalTime,
    'MCP exposes description provenance and retains original revision date')
  check(inspected.result.versions.includes('v1') && inspected.result.revisions.some((revision: { name: string; message?: string }) => revision.name === 'v1' && revision.message),
    'MCP keeps legacy version names and adds full revision records')
  check(await readFile(path.join(cacheBuildDir('test/robot'), 'versions/v1/scene.json'), 'utf8') === pinnedSceneBefore,
    'metadata backfill does not touch pinned geometry')
  check((await mcp('publish_revision', { buildId: 'test/unclassified', message: 'Add a revised bracket to study screw access.', scene: scene() })).error,
    'MCP publication requires new-entity classification')
  const study: CatalogItem = {
    id: 'bracket-study', name: 'Bracket access study', kind: 'study', collection: 'Robots', parentId: robot.id,
    description: 'Explore bracket changes that improve screw access.', status: 'active', source: { buildId: 'test/bracket' },
  }
  const selectedAssembly: CatalogItem = {
    id: 'selected-chassis', name: 'Robot chassis', kind: 'assembly', collection: 'Robots', parentId: robot.id,
    description: 'The chassis selected from the complete robot revision.', status: 'active', source,
    view: { partTypes: ['body'] },
  }
  await upsertCatalogItems({ getBuilds: () => registry.builds }, [selectedAssembly])
  const parentBeforeSelectionPublish = await readFile(liveRoot, 'utf8')
  const parentMetaBeforeSelectionPublish = await readFile(metaFile, 'utf8')
  const catalogBeforeSelectionPublish = await readFile(path.join(temporaryHome, 'catalog.json'), 'utf8')
  const selectedPublish = await mcp('publish_revision', {
    itemId: selectedAssembly.id, scene: scene('Only the selected chassis'),
    message: 'Change the selected chassis plate to inspect its mounting holes.',
  })
  check(selectedPublish.error && selectedPublish.result.includes('selects parts'),
    'selected assembly cannot publish partial geometry into its parent source')
  const { view: selection, ...withoutSelection } = selectedAssembly
  check((await mcp('publish_revision', {
    item: withoutSelection, scene: scene('Attempt to remove selection during publication'),
    message: 'Change the selected chassis plate to inspect its mounting holes.',
  })).error, 'publication cannot bypass stored assembly selection by omitting it from input')
  check((await mcp('publish_revision', {
    item: { ...withoutSelection, id: 'new-selected-chassis', view: selection },
    scene: scene('New selected chassis'), message: 'Change the selected chassis plate to inspect its mounting holes.',
  })).error, 'new selected assembly also requires independent geometry before publication')
  check(await readFile(liveRoot, 'utf8') === parentBeforeSelectionPublish &&
    await readFile(metaFile, 'utf8') === parentMetaBeforeSelectionPublish &&
    await readFile(path.join(temporaryHome, 'catalog.json'), 'utf8') === catalogBeforeSelectionPublish,
    'rejected selection publication preserves parent geometry, history, and catalog')
  const sharedSourceStudy = await mcp('publish_revision', {
    item: { ...study, id: 'shared-source-study', source: { buildId: 'test/robot' } },
    branch: ' MAIN ', scene: scene('Partial robot study'),
    message: 'Try a smaller chassis plate as a separate geometry experiment.',
  })
  check(sharedSourceStudy.error && sharedSourceStudy.result.includes('already publishes') &&
    await readFile(liveRoot, 'utf8') === parentBeforeSelectionPublish &&
    await readFile(metaFile, 'utf8') === parentMetaBeforeSelectionPublish,
    'new study cannot claim an existing geometry owner source, including normalized branch aliases')
  const separateBranchStudy = await mcp('publish_revision', {
    item: { ...study, id: 'separate-branch-study', source: { buildId: 'test/robot', branch: 'chassis-study' } },
    scene: scene('Chassis study on its own branch'), message: 'Try a smaller chassis plate on a separate design branch.',
  })
  check(!separateBranchStudy.error && separateBranchStudy.result.branch === 'chassis-study' &&
    await readFile(liveRoot, 'utf8') === parentBeforeSelectionPublish &&
    (await readCatalog()).items.find((item) => item.id === robot.id)?.asBuilt?.version === 'v1',
    'new study on a separate branch publishes without changing parent geometry or as-built pin')
  const parentRevision = await mcp('publish_revision', {
    itemId: robot.id, scene: scene('Complete robot with improved chassis'),
    message: 'Revise the complete robot chassis to improve mounting access.',
  })
  check(!parentRevision.error && parentRevision.result.item.kind === 'robot' &&
    parentRevision.result.item.asBuilt.version === 'v1',
    'the parent robot can still publish complete geometry while selected assemblies reference its history')
  const published = await mcp('publish_revision', {
    item: study, scene: scene('Bracket access study'), message: 'Add an access opening so the mounting screw can be tightened.',
  })
  check(!published.error && published.result.version === 'v1' && published.result.item.parentId === robot.id,
    'MCP publishes and classifies a new study')
  const revised = await mcp('publish_revision', {
    itemId: study.id, scene: scene('Larger access opening'), message: 'Enlarge the access opening for a standard hex driver.',
    reason: 'The earlier opening restricted driver access; enlarge it while keeping the existing mounting pattern.',
  })
  check(!revised.error && revised.result.version === 'v2' && revised.result.item.kind === 'study' && revised.result.item.parentId === robot.id,
    'subsequent publication preserves identity and classification')
  check(revised.result.reason?.includes('restricted driver access') && revised.result.nextSteps?.includes('validation'),
    'catalog publication round-trips the revision reason and prompts follow-up validation')
  check((await mcp('publish_revision', {
    itemId: study.id, branch: 'alternate-experiment', scene: scene(),
    message: 'Try an alternate opening shape for comparison.',
  })).error && !existsSync(path.join(cacheBuildDir('test/bracket'), 'branches/alternate-experiment')),
    'publishing an alternate branch cannot silently repoint an existing entity')
  const beforeInvalidPublish = registry.builds.length
  check((await mcp('publish_revision', {
    item: { ...study, id: 'orphan-study', source: { buildId: 'test/orphan' }, parentId: 'missing-parent' },
    scene: scene(), message: 'Add a bracket variant to inspect mounting access.',
  })).error && registry.builds.length === beforeInvalidPublish, 'publication rejects bad classification before writing geometry')
  // Concurrent upserts are serialized and preserve both updates.
  await Promise.all(['left', 'right'].map((suffix) => upsertCatalogItems({ getBuilds: () => registry.builds }, [{
    ...study, id: `${suffix}-study`, name: `${suffix} study`, source: { buildId: 'test/bracket' },
  }])))
  check((await readCatalog()).items.filter((item) => item.id === 'left-study' || item.id === 'right-study').length === 2,
    'concurrent catalog upserts do not lose records')
  await upsertCatalogItems({ getBuilds: () => registry.builds }, [{ ...study, id: 'archived-study', status: 'archived' }])
  check(!(await mcp('list_catalog')).result.items.some((item: CatalogItem) => item.id === 'archived-study') &&
    (await mcp('list_catalog', { includeArchived: true })).result.items.some((item: CatalogItem) => item.id === 'archived-study'),
    'MCP hides archived items unless explicitly included')
  const legacy = await request('POST', '/__buildviz/push', {
    buildId: 'test/legacy', version: 'v1', scene: scene(), message: 'Import the original plate geometry for reference.',
  })
  check(legacy.status === 200, 'legacy root-only fixture created')
  await rm(path.join(cacheBuildDir('test/legacy'), 'versions/v1'), { recursive: true })
  const rootOnlySource = { buildId: 'test/legacy', branch: 'main', version: 'v1' }
  check((await request('PATCH', '/__buildviz/revisions/metadata', {
    ...rootOnlySource, message: 'Explain the imported plate layout without changing geometry.',
  })).status === 200, 'metadata-only backfill accepts a concrete root-only default')
  check((await request('POST', '/__buildviz/catalog', { items: [{
    ...study, id: 'root-only-pin', source: rootOnlySource,
  }] })).status === 400, 'catalog pins still reject unmaterialized default snapshots')
  await request('POST', '/__buildviz/push', {
    buildId: 'test/unclaimed', version: 'v1', scene: scene(), message: 'Import an independent chassis component for inspection.',
  })
  await upsertCatalogItems({ getBuilds: () => registry.builds }, [{
    ...selectedAssembly, id: 'unclaimed-selection', source: { buildId: 'test/unclaimed', branch: 'main', version: 'v1' },
  }, {
    ...selectedAssembly, id: 'unclaimed-view', kind: 'view', source: { buildId: 'test/unclaimed', branch: 'main', version: 'v1' },
  }])
  const claim = await mcp('publish_revision', {
    item: { ...study, id: 'independent-chassis', kind: 'assembly', source: { buildId: 'test/unclaimed' } },
    scene: scene('Independent revised chassis'), message: 'Revise the independently published chassis mounting plate.',
  })
  check(!claim.error && claim.result.item.kind === 'assembly' && claim.result.version === 'v2' &&
    existsSync(path.join(cacheBuildDir('test/unclaimed'), 'versions/v1/scene.json')),
    'views and selected assemblies do not prevent classifying an unowned source or lose their pinned revision')
  console.log(`Catalog integration: ${assertions} checks passed (HTTP, MCP, atomic validation, revision metadata, and pin preservation).`)
} finally {
  await rm(temporaryHome, { recursive: true, force: true })
}
