import assert from 'node:assert/strict'
import { mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { requireRevisionDescription } from '../core/revisionDescription'

for (const invalid of [undefined, '', '   ', 'v12', 'update', 'Regenerate build', 'new version']) {
  assert.throws(() => requireRevisionDescription(invalid), /what changed and why/)
}
const description = 'Add yaw-horn access holes so the screws can be tightened with the servo installed.'
assert.equal(requireRevisionDescription(`  ${description}  `), description)
assert.equal(requireRevisionDescription('Thicken the chassis around the yaw bearing pockets.'), 'Thicken the chassis around the yaw bearing pockets.')

const scratch = await mkdtemp(path.join(os.tmpdir(), 'buildviz-description-check-'))
process.env.BUILDVIZ_HOME = path.join(scratch, 'hub')
const dir = path.join(process.env.BUILDVIZ_HOME, 'cache', 'fixture', 'robot')
const { migrateOneBuild, freezeBuild, cacheCommand } = await import('../cli/commands/versionsCmd')
try {
  await mkdir(dir, { recursive: true })
  const scene = { name: 'Fixture', units: 'mm', meshes: [], instances: [] }
  await writeFile(path.join(dir, 'scene.json'), JSON.stringify(scene))
  await mkdir(path.join(dir, 'versions', 'v95'), { recursive: true })
  await writeFile(path.join(dir, 'versions', 'v95', 'scene.json'), JSON.stringify(scene))
  const note = { name: 'v95', pushedAt: '2026-09-01T00:00:00.000Z', message: description, messageSource: 'retrospective' }
  const branch = { name: 'reinforcement', defaultVersion: 'r1', versions: [{ name: 'r1', pushedAt: '2026-08-01T00:00:00.000Z', message: 'Add an independent reinforcement study.' }] }
  await writeFile(path.join(dir, 'meta.json'), JSON.stringify({
    schema: 2, buildId: 'fixture/robot', name: 'Fixture', defaultVersion: 'v95',
    createdAt: note.pushedAt, updatedAt: note.pushedAt, versions: [note],
    defaultBranch: 'main', branches: [branch],
  }))
  const original = await readFile(path.join(dir, 'meta.json'), 'utf8')
  await migrateOneBuild(dir, 'fixture/robot', true)
  assert.equal(await readFile(path.join(dir, 'meta.json'), 'utf8'), original, 'Dry-run must not write metadata')
  await migrateOneBuild(dir, 'fixture/robot', false)
  const result = JSON.parse(await readFile(path.join(dir, 'meta.json'), 'utf8'))
  assert.deepEqual(result.versions, [note], 'Migration must preserve description, provenance, and original timestamp')
  assert.deepEqual(result.branches.find((item: { name: string }) => item.name === 'reinforcement'), branch)
  assert.equal((await migrateOneBuild(dir, 'fixture/robot', true)).changed, false, 'Metadata migration should be idempotent')
  await writeFile(path.join(process.env.BUILDVIZ_HOME, 'catalog.json'), JSON.stringify({ schema: 1, items: [{
    id: 'fixture', name: 'Fixture robot', kind: 'robot', collection: 'fixtures', status: 'built',
    description: 'Published fixture for verifying revision protection.', source: { buildId: 'fixture/robot' },
    asBuilt: { buildId: 'fixture/robot', branch: 'main', version: 'v95' },
  }] }))
  await assert.rejects(freezeBuild([dir], { version: 'v95', force: true, message: description }), /referenced by/)
  await assert.rejects(cacheCommand(['rm', 'fixture/robot'], {}), /referenced by/)
  await freezeBuild([dir], { bump: true, keep: '1', message: 'Add a working revision while preserving the installed assembly.', json: true })
  const retained = JSON.parse(await readFile(path.join(dir, 'meta.json'), 'utf8'))
  assert.equal(retained.defaultVersion, 'v96')
  assert.deepEqual(retained.versions.find((item: { name: string }) => item.name === 'v95'), note,
    'Retention must preserve pinned revisions and their retrospective provenance')
  await assert.rejects(cacheCommand(['rm', 'fixture/robot'], { version: 'v95' }), /referenced by/)
  console.log('PASS: descriptions required; migration preserves history; CLI protects installed revision from overwrite, deletion, and pruning.')
} finally {
  await rm(scratch, { recursive: true, force: true })
}
