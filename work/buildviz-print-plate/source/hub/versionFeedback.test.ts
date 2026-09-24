import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { Readable } from 'node:stream'
import type { IncomingMessage, ServerResponse } from 'node:http'
import { normalizeVersionReason } from '../core/versionFeedback'
import { newVersionCommand } from '../core/publishCommand'

// Isolated filesystem and in-memory HTTP handlers: no real hub or ports.
const testHome = await mkdtemp(path.join(os.tmpdir(), 'buildviz-feedback-test-'))
process.env.BUILDVIZ_HOME = testHome
const { pushLayoutFromPayload: push, cacheBuildDir, serveHubAsset } = await import('./hub')
const { readVersionFeedback: read, recordVersionFeedback: record } = await import('./versionFeedback')
const { buildIndexEntryFor } = await import('./hub')
after(() => rm(testHome, { recursive: true, force: true }))
const base = 'http://127.0.0.1:5183'
const registry = { builds: [] as Awaited<ReturnType<typeof push>>['registry']['builds'] }
const ctx = { getBuilds: () => registry.builds, readOnly: false }
const input = (buildId: string, version = 'v1') => ({
  buildId, version, message: `Revise roof geometry for ${version} to inspect screw access.`, reason: 'Previous roof blocked the driver; expose screw access, fit still untested.',
  scene: { name: 'Roof test', units: 'mm', center: [0, 0, 0], meshes: [], instances: [], revision: version },
  designSpec: 'parts: {}\n',
})
async function publish(buildId: string, version = 'v1', extra = {}) {
  const result = await push({ ...input(buildId, version), ...extra }, base)
  registry.builds = result.registry.builds
  return result
}
const finding = (buildId: string, extra = {}) => ({
  buildId, branch: 'main', version: 'v1', kind: 'issue', basis: 'user-report',
  message: 'Driver access is blocked by the roof.', parts: ['roof', 'base'],
  evidence: 'User assembly review; not yet independently measured.', ...extra,
})
const file = (buildId: string, name: string) => readFile(path.join(cacheBuildDir(buildId), name), 'utf8')
async function request(url: string, body?: unknown, key = 'test-key', readOnly = false, method?: string) {
  const req = Object.assign(Readable.from(body ? [Buffer.from(JSON.stringify(body))] : []), {
    url, method: method ?? (body ? 'POST' : 'GET'), headers: { 'x-api-key': key, host: '127.0.0.1:5183' },
  }) as unknown as IncomingMessage
  let output = ''
  const res = { statusCode: 200, setHeader: () => undefined, end: (value: string) => { output = value } }
  await serveHubAsset(req, res as unknown as ServerResponse, () => registry, base, 'test', readOnly, 'test-key')
  return { status: res.statusCode, body: JSON.parse(output) }
}
const rpc = (name: string, args: object) => ({ jsonrpc: '2.0', id: 1, method: 'tools/call', params: { name, arguments: args } })

test('publish reason survives index, retries and promotion; missing reason warns compatibly', async () => {
  const id = 'feedback/reason'
  const first = await publish(id)
  assert.equal(first.written.reason, input(id).reason)
  assert.match(first.nextSteps, /Before revising/)
  const before = await file(id, 'meta.json')
  const retry = await publish(id, 'v1', { reason: 'Cannot replace original reason' })
  assert.equal(retry.written.reason, input(id).reason)
  assert.equal(await file(id, 'meta.json'), before)
  const index = await buildIndexEntryFor(id, cacheBuildDir(id), null)
  assert.equal(index.versions[0].reason, input(id).reason)
  const legacy = await publish(id, 'v2', { reason: undefined })
  assert.ok(legacy.warnings.some((warning) => warning.includes('Missing version reason')))
  assert.equal(legacy.written.reason, null)
  const promoted = await publish(id, 'v1', { reason: 'retry', setDefault: true })
  assert.equal(promoted.written.reason, input(id).reason)
  assert.equal(normalizeVersionReason('  Needed for access  '), 'Needed for access')
  assert.throws(() => normalizeVersionReason(42), /must be text/)
  assert.throws(() => normalizeVersionReason('x'.repeat(2001)), /2000/)
  assert.match(newVersionCommand(id, 'main'), /--reason/)
})

test('feedback appends, deduplicates retries, and leaves all published bytes untouched', async () => {
  const id = 'feedback/append'
  await publish(id)
  const paths = ['meta.json', 'scene.json', 'design_spec.yaml', 'versions/v1/scene.json', 'versions/v1/design_spec.yaml']
  const before = await Promise.all(paths.map((name) => file(id, name)))
  const original = finding(id, { id: 'driver-access' })
  const first = await record(ctx, original)
  const journal = await file(id, 'version-feedback.json')
  const retry = await record(ctx, original)
  assert.equal(retry.unchanged, true)
  assert.deepEqual(retry.entry, first.entry)
  assert.equal(await file(id, 'version-feedback.json'), journal)
  await assert.rejects(record(ctx, { ...original, message: 'Rewrite original issue' }), /different content/)
  await record(ctx, finding(id, { id: 'clarification', kind: 'note', message: 'Access was checked with the roof installed.' }))
  assert.equal((await read(ctx, original)).entries.length, 2)
  assert.deepEqual(await Promise.all(paths.map((name) => file(id, name))), before)
})

test('concurrent appends do not lose findings or duplicate stable IDs', async () => {
  const id = 'feedback/concurrent'
  await publish(id)
  await Promise.all(Array.from({ length: 12 }, (_, i) => record(ctx, finding(id, { id: `finding-${i}` }))))
  await Promise.all(Array.from({ length: 4 }, () => record(ctx, finding(id, { id: 'same' }))))
  assert.equal((await read(ctx, finding(id))).entries.length, 13)
})

test('writes require exact existing version and explicit evidence basis', async () => {
  const id = 'feedback/validation'
  await publish(id)
  for (const version of [undefined, '', 'latest', '../v1', '..', '/v1', 'V1', 'v999']) {
    await assert.rejects(record(ctx, finding(id, { version })))
  }
  await assert.rejects(record(ctx, finding(id, { branch: 'other' })), /Unknown version/)
  await assert.rejects(record(ctx, finding('/tmp/outside')), /Unknown registered build/)
  await assert.rejects(record(ctx, finding(id, { basis: undefined })), /basis is required/)
  await assert.rejects(record(ctx, finding(id, { parts: 'roof' })), /array/)
  await assert.rejects(record(ctx, finding(id, { message: 'x'.repeat(4001) })), /4000/)
  await assert.rejects(record(ctx, finding(id, { relatedVersion: 'v999' })), /must exist/)
})

test('resolution links original issue and actual evidence, never just a newer publish', async () => {
  const id = 'feedback/resolution'
  await publish(id)
  const issue = await record(ctx, finding(id))
  await publish(id, 'v2')
  assert.equal((await read(ctx, finding(id))).entries.length, 1)
  const resolution = finding(id, { kind: 'resolution', relatedVersion: 'v2', relatedFeedbackId: issue.entry.id,
    basis: 'test-result', message: 'Fixture test confirms driver clearance on v2.', evidence: 'Synthetic test fixture: 3 mm measured clearance.' })
  await assert.rejects(record(ctx, { ...resolution, evidence: undefined }), /resolution requires/)
  await assert.rejects(record(ctx, { ...resolution, relatedFeedbackId: undefined }), /resolution requires/)
  await assert.rejects(record(ctx, { ...resolution, basis: 'hypothesis' }), /resolution requires/)
  await assert.rejects(record(ctx, { ...resolution, version: 'v2' }), /exact branch\/version/)
  await record(ctx, resolution)
  const learned = await read(ctx, finding(id))
  assert.equal(learned.entries[0].kind, 'issue')
  assert.equal(learned.entries[1].kind, 'resolution')
  assert.equal((await read(ctx, { ...finding(id), version: 'v2' })).entries.length, 0)
})

test('branches and promotion retain feedback on the original named branch', async () => {
  const id = 'feedback/branches'
  await publish(id)
  await record(ctx, finding(id, { id: 'main-issue' }))
  await publish(id, 'v1', { branch: 'experiment' })
  await record(ctx, finding(id, { branch: 'experiment', id: 'experiment-issue' }))
  await publish(id, 'v2', { branch: 'experiment', setDefaultBranch: true })
  assert.equal((await read(ctx, finding(id))).entries[0].id, 'main-issue')
  assert.equal((await read(ctx, finding(id, { branch: 'experiment' }))).entries[0].id, 'experiment-issue')
  await record(ctx, finding(id, { id: 'main-after-promotion' }))
  assert.equal((await read(ctx, finding(id))).entries.length, 2)
})

test('invalid journal fails closed rather than erasing earlier findings', async () => {
  const id = 'feedback/corrupt'
  await publish(id)
  await writeFile(path.join(cacheBuildDir(id), 'version-feedback.json'), '{broken')
  await assert.rejects(record(ctx, finding(id)))
  assert.equal(await file(id, 'version-feedback.json'), '{broken')
})

test('recorded lessons remain readable and can receive follow-up after geometry retention', async () => {
  const id = 'feedback/retention'
  await publish(id)
  await record(ctx, finding(id, { id: 'preserved-issue' }))
  await publish(id, 'v2', { setDefault: true, keepVersions: 1 })
  assert.equal((await read(ctx, finding(id))).entries[0].id, 'preserved-issue')
  await record(ctx, finding(id, { kind: 'note', message: 'Earlier geometry was pruned; findings preserved.', relatedVersion: 'v2' }))
  assert.equal((await read(ctx, finding(id))).entries.length, 2)
})

test('HTTP auth/read-only protection, public reads, method safety and reason roundtrip', async () => {
  const id = 'feedback/http'
  const pushed = await request('/__buildviz/push', input(id))
  assert.equal(pushed.body.reason, input(id).reason)
  assert.match(pushed.body.nextSteps, /validation/)
  assert.equal((await request('/__buildviz/feedback', finding(id), 'wrong')).status, 401)
  assert.equal((await request('/__buildviz/feedback', finding(id), 'test-key', true)).status, 403)
  assert.equal((await request('/__buildviz/feedback', finding(id), 'test-key', false, 'DELETE')).status, 405)
  assert.equal((await request('/__buildviz/feedback', finding(id))).status, 200)
  const readResult = await request(`/__buildviz/feedback?buildId=${id}&version=v1`, undefined, 'wrong', true)
  assert.equal(readResult.status, 200)
  assert.equal(readResult.body.entries.length, 1)
  assert.equal((await request(`/__buildviz/feedback?buildId=${id}`)).status, 400)
})

test('MCP encourages the learning loop and exposes guarded read/write tools', async () => {
  const id = 'feedback/mcp'
  await publish(id)
  const initialize = await request('/mcp', { jsonrpc: '2.0', id: 1, method: 'initialize' })
  assert.match(initialize.body.result.instructions, /WHY/)
  assert.match(initialize.body.result.instructions, /not proof of a fix/)
  const list = await request('/mcp', { jsonrpc: '2.0', id: 1, method: 'tools/list' })
  assert.ok(list.body.result.tools.some((tool: { name: string }) => tool.name === 'record_version_feedback'))
  const publishing = list.body.result.tools.find((tool: { name: string }) => tool.name === 'publish_revision')
  assert.ok(publishing.inputSchema.properties.reason, 'Catalog publication accepts a distinct motivation')
  for (const name of ['list_catalog', 'get_workflows', 'set_workflows', 'create_view']) {
    assert.ok(list.body.result.tools.some((tool: { name: string }) => tool.name === name), `Preserve ${name}`)
  }
  const write = await request('/mcp', rpc('record_version_feedback', finding(id)))
  assert.ok(!write.body.result.isError)
  const build = await request('/mcp', rpc('get_build', { buildId: id, version: 'v1' }))
  const result = JSON.parse(build.body.result.content[0].text)
  assert.equal(result.feedback.entries.length, 1)
  assert.equal(result.versionHistory[0].reason, input(id).reason)
  const blocked = await request('/mcp', rpc('record_version_feedback', finding(id)), 'test-key', true)
  assert.equal(blocked.body.result.isError, true)
  assert.match(blocked.body.result.content[0].text, /READ-ONLY/)
  assert.equal((await read(ctx, finding(id))).entries.length, 1)
})
