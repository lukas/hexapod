import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { mkdtemp, readFile, mkdir, rm, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { Readable } from 'node:stream'
import type { IncomingMessage, ServerResponse } from 'node:http'
import { AnalysisConflictError, VersionConflictError, publishErrorResponse, sameScene } from './publishPolicy'
import { newVersionCommand } from '../core/publishCommand'

// No server/port, and no access to the real hub's registry or versions.
const testHome = await mkdtemp(path.join(os.tmpdir(), 'buildviz-publish-test-'))
process.env.BUILDVIZ_HOME = testHome
const { pushLayoutFromPayload: push, pushAnalysisFromPayload: analysis, serveHubAsset, cacheBuildDir, registryPath } = await import('./hub')
after(() => rm(testHome, { recursive: true, force: true }))

const baseUrl = 'http://127.0.0.1:5183'
const scene = (revision = 1) => ({ name: 'Test bracket', units: 'mm', center: [0, 0, 0],
  meshes: [{ id: 'bracket', name: 'bracket.stl', url: `/builds/_assets/revision-${revision}.stl` }],
  instances: [], revision })
const payload = (buildId: string, revision = 1) => ({ buildId, message: `Bracket revision ${revision}: exercise version preservation.`, scene: scene(revision), designSpec: 'parts: {}\n' })
const meta = (id: string) => readFile(path.join(cacheBuildDir(id), 'meta.json'), 'utf8')
const versionScene = (id: string, version: string) => readFile(path.join(cacheBuildDir(id), 'versions', version, 'scene.json'), 'utf8')

test('default push creates v1 then v2; returned URLs pin even the default', async () => {
  const id = 'policy/default'
  const first = await push(payload(id), baseUrl)
  const oldScene = await versionScene(id, 'v1')
  const second = await push({ ...payload(id, 2), bump: false }, baseUrl)
  assert.equal(first.written.version, 'v1')
  assert.equal(second.written.version, 'v2')
  assert.equal(second.written.defaultVersion, 'v2')
  assert.equal(await versionScene(id, 'v1'), oldScene)
  assert.equal(new URL(first.url).searchParams.get('version'), 'v1')
  assert.equal(new URL(second.url).searchParams.get('version'), 'v2')
})

test('review bump keeps v6 default and selects v12 after v11', async () => {
  const id = 'policy/review'
  await push({ ...payload(id), version: 'v6' }, baseUrl)
  await push({ ...payload(id, 2), version: 'v11', setDefault: false }, baseUrl)
  const next = await push({ ...payload(id, 3), setDefault: false }, baseUrl)
  assert.equal(next.written.version, 'v12')
  assert.equal(next.written.defaultVersion, 'v6')
})

test('identical retry preserves scene, spec, original message, timestamps and registry', async () => {
  const id = 'policy/retry'
  await push({ ...payload(id), version: 'v1' }, baseUrl)
  const before = await meta(id)
  const beforeRegistry = await readFile(registryPath, 'utf8')
  const beforeScene = await versionScene(id, 'v1')
  const retry = await push({ ...payload(id), version: 'v1', message: 'retry message', keepVersions: 1 }, baseUrl)
  assert.equal(retry.written.unchanged, true)
  assert.equal(retry.written.message, payload(id).message)
  assert.equal(await meta(id), before)
  assert.equal(await versionScene(id, 'v1'), beforeScene)
  assert.equal(await readFile(registryPath, 'utf8'), beforeRegistry)
})

test('changed named default AND nondefault reject, even with old bypass flags', async () => {
  const id = 'policy/conflict'
  await push({ ...payload(id), version: 'main' }, baseUrl)
  await push({ ...payload(id, 2), version: 'v3', setDefault: false }, baseUrl)
  const before = await meta(id)
  for (const version of ['main', 'v3']) {
    const saved = await versionScene(id, version)
    await assert.rejects(push({ ...payload(id, 5), version, bump: true, noSnapshot: true, setDefault: true }, baseUrl),
      (error: unknown) => {
        assert.ok(error instanceof VersionConflictError)
        const response = publishErrorResponse(error)
        assert.equal(response.status, 409)
        assert.ok('code' in response.body)
        assert.ok('suggestedVersion' in response.body)
        assert.equal(response.body.code, 'VERSION_ALREADY_EXISTS')
        assert.equal(response.body.suggestedVersion, 'v4')
        assert.match(response.body.error, /Remove --version and use --bump/)
        return true
      })
    assert.equal(await versionScene(id, version), saved)
  }
  assert.equal(await meta(id), before)
})

test('spec-only changes reject; an omitted spec on retry preserves the stored spec', async () => {
  const id = 'policy/spec'
  await push({ ...payload(id), version: 'v1' }, baseUrl)
  const before = await meta(id)
  await assert.rejects(push({ ...payload(id), version: 'v1', designSpec: 'parts: {new: {}}\n' }, baseUrl), VersionConflictError)
  const retry = await push({ ...payload(id), version: 'v1', designSpec: undefined }, baseUrl)
  assert.ok(retry.written.unchanged)
  assert.equal(await meta(id), before)
  const next = await push({ ...payload(id, 2), designSpec: undefined }, baseUrl)
  assert.equal(await readFile(path.join(next.written.branchDir, 'versions', 'v2', 'design_spec.yaml'), 'utf8'), 'parts: {}\n')
})

test('re-promoting identical content changes only the default, not version history', async () => {
  const id = 'policy/promote'
  await push({ ...payload(id), version: 'v1' }, baseUrl)
  await push({ ...payload(id, 2), version: 'v2', setDefault: false }, baseUrl)
  const before = JSON.parse(await meta(id))
  const promoted = await push({ ...payload(id, 2), version: 'v2', setDefault: true, message: 'Promote reviewed bracket without changing geometry.' }, baseUrl)
  assert.ok(promoted.written.unchanged)
  assert.equal(promoted.written.defaultVersion, 'v2')
  assert.deepEqual(JSON.parse(await meta(id)).versions, before.versions)
  assert.equal(await readFile(path.join(cacheBuildDir(id), 'scene.json'), 'utf8'), await versionScene(id, 'v2'))
})

test('uploaded mesh bytes are compared after content-addressed URL normalization', async () => {
  const id = 'policy/uploads'
  const asset = (text: string) => [{ meshId: 'bracket', data: Buffer.from(text).toString('base64'), ext: 'stl' }]
  const first = await push({ ...payload(id), version: 'v1', assets: asset('old mesh') }, baseUrl)
  assert.equal(first.uploads.count, 1)
  const retry = await push({ ...payload(id), version: 'v1', assets: asset('old mesh') }, baseUrl)
  assert.ok(retry.written.unchanged)
  await assert.rejects(push({ ...payload(id), version: 'v1', assets: asset('new mesh') }, baseUrl), VersionConflictError)
})

test('concurrent bumps get distinct version names and retain shared registry entries', async () => {
  const id = 'policy/concurrent'
  const results = await Promise.all(Array.from({ length: 8 }, (_, i) => push(payload(id, i), baseUrl)))
  assert.equal(new Set(results.map((result) => result.written.version)).size, 8)
  assert.equal(JSON.parse(await meta(id)).versions.length, 8)
  const separate = await Promise.all(['policy/parallel-a', 'policy/parallel-b'].map((buildId) => push(payload(buildId), baseUrl)))
  const registry = JSON.parse(await readFile(registryPath, 'utf8'))
  for (const result of separate) assert.ok(registry.builds.some((entry: {id: string}) => entry.id === result.registration.id))
})

test('concurrent same-name changes allow one creation and reject the other', async () => {
  const id = 'policy/race'
  const results = await Promise.allSettled([1, 2].map((rev) => push({ ...payload(id, rev), version: 'v1' }, baseUrl)))
  assert.equal(results.filter((entry) => entry.status === 'fulfilled').length, 1)
  assert.equal(results.filter((entry) => entry.status === 'rejected').length, 1)
})

test('branches have independent numbering and promotion preserves both histories', async () => {
  const id = 'policy/branches'
  await push(payload(id), baseUrl)
  const alternate = await push({ ...payload(id, 2), branch: 'alternative' }, baseUrl)
  assert.equal(alternate.written.version, 'v1')
  await push({ ...payload(id, 3), branch: 'alternative', setDefaultBranch: true }, baseUrl)
  const histories = JSON.parse(await meta(id)).branches
  assert.equal(histories.find((entry: {name: string}) => entry.name === 'main').versions.length, 1)
  assert.equal(histories.find((entry: {name: string}) => entry.name === 'alternative').versions.length, 2)
  assert.equal(JSON.parse(await versionScene(id, 'v1')).revision, 2)
  assert.equal(JSON.parse(await readFile(path.join(cacheBuildDir(id), 'branches', 'main', 'versions', 'v1', 'scene.json'), 'utf8')).revision, 1)
})

test('legacy root-only version is reserved and archived under its original name', async () => {
  const id = 'policy/legacy'
  const dir = cacheBuildDir(id)
  await mkdir(dir, { recursive: true })
  const original = JSON.stringify(scene())
  await writeFile(path.join(dir, 'scene.json'), original)
  await assert.rejects(push({ ...payload(id, 2), version: 'main' }, baseUrl), VersionConflictError)
  await push(payload(id, 2), baseUrl)
  assert.equal(await versionScene(id, 'main'), original)
  assert.equal(JSON.parse(await meta(id)).defaultVersion, 'v1')
})

test('analysis retries preserve metadata, reject changes and pin source version in link', async () => {
  const id = 'policy/analysis'
  const build = await push(payload(id), baseUrl)
  const input = { buildId: id, name: 'v1-detail', scene: scene(), sourceVersion: 'v1', sourceBranch: 'main', message: 'original' }
  const first = await analysis(input, build.registry, baseUrl)
  const retry = await analysis({ ...input, message: 'retry' }, build.registry, baseUrl)
  assert.ok(retry.unchanged)
  assert.deepEqual(retry.analysis, first.analysis)
  assert.equal(new URL(first.url).searchParams.get('version'), 'v1')
  for (const edit of [{ scene: scene(2) }, { sourceVersion: 'v2' }, { sourceBranch: 'other' }]) {
    await assert.rejects(analysis({ ...input, ...edit }, build.registry, baseUrl), (error: unknown) => {
      assert.ok(error instanceof AnalysisConflictError)
      assert.equal(publishErrorResponse(error).status, 409)
      return true
    })
  }
  const next = await analysis({ ...input, name: 'v2-detail', scene: scene(2), sourceVersion: 'v2' }, build.registry, baseUrl)
  assert.ok(next.isNew)
})

test('canonical comparison ignores formatting/key order, not meaningful scene edits', () => {
  assert.ok(sameScene('{"b":2, "a":1}', { a: 1, b: 2 }))
  assert.ok(!sameScene('{"a":[1,2]}', { a: [2, 1] }))
  assert.ok(!sameScene('not json', {}))
  assert.equal(publishErrorResponse(new Error('invalid payload')).status, 400)
})

test('viewer command creates a review, quotes identifiers and never reuses viewed version', () => {
  const command = newVersionCommand('prototype_sts3215/premade-chorn-56', 'main')
  assert.match(command, /--bump --no-default/)
  assert.match(command, /--upload-assets/)
  assert.ok(!command.includes('--version'))
  assert.ok(newVersionCommand("user's/build", 'test').includes("'user'\\''s/build'"))
})

test('real HTTP handler advertises policy, returns 409, and keeps auth/read-only gates', async () => {
  const registry = { builds: [] as Awaited<ReturnType<typeof push>>['registry']['builds'] }
  const request = async (url: string, body?: unknown, key = 'test-key', readOnly = false) => {
    const req = Object.assign(Readable.from(body ? [Buffer.from(JSON.stringify(body))] : []), {
      url, method: body ? 'POST' : 'GET', headers: { 'x-api-key': key },
    }) as unknown as IncomingMessage
    let text = ''
    const res = { statusCode: 200, setHeader: () => undefined, end: (value: string) => { text = value } }
    await serveHubAsset(req, res as unknown as ServerResponse, () => registry, baseUrl, 'test-start', readOnly, 'test-key')
    return { status: res.statusCode, body: JSON.parse(text) }
  }
  const id = 'policy/http'
  const first = await request('/__buildviz/push', payload(id))
  assert.equal(first.status, 200)
  assert.equal(first.body.version, 'v1')
  const before = await meta(id)
  const conflict = await request('/__buildviz/push', { ...payload(id, 2), version: 'v1' })
  assert.equal(conflict.status, 409)
  assert.equal(conflict.body.code, 'VERSION_ALREADY_EXISTS')
  assert.equal(conflict.body.suggestedVersion, 'v2')
  assert.equal(await meta(id), before)
  const retry = await request('/__buildviz/push', { ...payload(id), version: 'v1' })
  assert.equal(retry.body.unchanged, true)
  assert.match(retry.body.summary, /unchanged/)
  assert.equal((await request('/__buildviz/status')).body.publishPolicy.existingVersion, 'reject-changes')
  assert.equal((await request('/__buildviz/push', payload(id), 'wrong')).status, 401)
  assert.equal((await request('/__buildviz/push', payload(id), 'test-key', true)).status, 403)
})
