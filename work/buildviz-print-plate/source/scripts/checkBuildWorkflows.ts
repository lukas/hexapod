// Mechanics-only workflow checks. Uses isolated files and mock HTTP, no ports.
import assert from 'node:assert/strict'
import { mkdir, mkdtemp, readFile, rm, symlink, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { Readable } from 'node:stream'
import type { IncomingMessage, ServerResponse } from 'node:http'
import type { BuildSceneManifest } from '../core/buildScene'
import type { WorkflowMetadata } from '../core/buildWorkflows'

const home = await mkdtemp(path.join(os.tmpdir(), 'buildviz-workflows-'))
process.env.BUILDVIZ_HOME = home
const { readBuildWorkflows, downloadWorkflowPlate, downloadBuildWorkflows, downloadWorkflowFile, validateWorkflowMetadata, geometryFingerprint } = await import('../hub/buildWorkflows')
const { serveHubAsset } = await import('../hub/hub')
const dir = path.join(home, 'robot')
const assetStoreDir = path.join(home, 'assets')
const catalogPath = path.join(home, 'catalog.json')
const registry = { builds: [{ id: 'test/robot', buildDir: dir, scenePath: path.join(dir, 'scene.json'), designSpecPath: null, name: 'Fixture', registeredAt: '2026-09-01T00:00:00Z' }] }
const deps = { getBuilds: () => registry.builds, assetStoreDir, catalogPath }
let count = 0
const check = (condition: unknown, label: string) => { assert.ok(condition, label); count += 1 }
const rejects = async (run: () => unknown, pattern: RegExp, label: string) => { await assert.rejects(async () => run(), pattern); count += 1; void label }
const stl = (width: number) => {
  const body = Buffer.alloc(134)
  body.writeUInt32LE(1, 80)
  body.writeFloatLE(width, 84 + 24)
  body.writeFloatLE(1, 84 + 40)
  return body
}
const transform = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
const scene = (newer: boolean): BuildSceneManifest => ({
  name: 'Workflow robot', units: 'mm', center: [0, 0, 0],
  meshes: [
    { id: 'plate', name: 'Plate', url: newer ? 'moved-plate.stl' : 'old-plate.stl' },
    { id: 'clamp', name: 'Clamp', url: 'clamp.stl' },
    { id: 'motor', name: 'Motor', url: 'motor.stl' },
    { id: 'tube', name: 'Tube', url: 'tube.stl' },
    { id: 'derived', name: 'Derived', url: 'derived.stl' },
    { id: 'unknown', name: 'Unknown', url: 'unknown.stl' },
  ],
  instances: [
    ...Array.from({ length: newer ? 3 : 2 }, (_, i) => ({ id: `plate${i}`, meshId: 'plate', name: 'Plate', partType: 'plate', role: 'structure', color: '#aaa', transform: [...transform.slice(0, 12), newer ? 100 : 0, i, 0, 1] })),
    ...['clamp', 'motor', 'tube', 'derived', 'unknown'].map((partType) => ({ id: partType, meshId: partType, name: partType, partType, role: 'structure', color: '#aaa', transform })),
  ],
})
const metadata: WorkflowMetadata = {
  schema: 1,
  parts: { plate: { kind: 'printed', label: '../../=Plate', material: 'PETG', evidence: 'Printed fixture plate.' },
    clamp: { kind: 'printed', label: 'Clamp' }, motor: { kind: 'purchased', label: 'Motor', url: 'https://example.com/motor' }, tube: { kind: 'other', label: 'Carbon tube' } },
  bom: { notes: 'Additional purchased parts, beyond modeled items.', items: [{ id: 'motor', label: 'Motor', quantity: 1, partTypes: ['motor'] }, { id: 'battery', label: 'Battery', quantity: 1 }, { id: 'screw', label: 'Plate screws', quantity: 8, partTypes: ['plate'] }, { id: 'clamp-bolt', label: 'Clamp bolt', quantity: 1, partTypes: ['clamp'] }] },
  instructions: [{ id: 'assembly', title: 'Plate assembly', text: 'Attach the plate.', partTypes: ['plate'] }],
  runs: [{ id: 'run', title: 'Family evaluation', url: 'https://example.com/run', kind: 'mujoco', association: 'robot-family', model: 'family-test' }, { id: 'older-run', title: 'Older revision evaluation', url: 'https://example.com/older', association: 'exact-revision', source: { buildId: 'test/robot', branch: 'main', version: 'v1' } }],
}
const unzipStored = (buffer: Buffer) => {
  const entries = new Map<string, Buffer>(); let offset = 0
  while (buffer.readUInt32LE(offset) === 0x04034b50) {
    const size = buffer.readUInt32LE(offset + 18); const nameLength = buffer.readUInt16LE(offset + 26); const extra = buffer.readUInt16LE(offset + 28)
    const name = buffer.toString('utf8', offset + 30, offset + 30 + nameLength)
    const start = offset + 30 + nameLength + extra
    entries.set(name, buffer.subarray(start, start + size)); offset = start + size
  }
  assert.equal(buffer.readUInt32LE(offset), 0x02014b50)
  return entries
}
const http = async (url: string, method = 'GET', payload?: unknown, readOnly = true) => {
  const incoming = Object.assign(Readable.from(payload === undefined ? [] : [JSON.stringify(payload)]), { method, url, headers: {} }) as unknown as IncomingMessage
  const headers: Record<string, unknown> = {}; let body: Buffer = Buffer.alloc(0)
  const response = { statusCode: 200, setHeader: (name: string, value: unknown) => { headers[name] = value }, end: (data?: unknown) => { body = Buffer.isBuffer(data) ? data : Buffer.from(String(data ?? '')) } }
  const handled = await serveHubAsset(incoming, response as unknown as ServerResponse, () => registry, 'http://127.0.0.1:5183', '2026-09-01T00:00:00Z', readOnly, 'secret', catalogPath)
  assert.ok(handled)
  return { ...response, headers, body }
}
try {
  await mkdir(assetStoreDir, { recursive: true })
  for (const revision of ['v1', 'v2']) {
    const revisionDir = path.join(dir, 'versions', revision)
    await mkdir(revisionDir, { recursive: true })
    await writeFile(path.join(revisionDir, 'scene.json'), JSON.stringify(scene(revision === 'v2')))
    await writeFile(path.join(revisionDir, revision === 'v2' ? 'moved-plate.stl' : 'old-plate.stl'), stl(1))
    await writeFile(path.join(revisionDir, 'clamp.stl'), stl(revision === 'v2' ? 3 : 2))
    await writeFile(path.join(revisionDir, 'derived.stl'), stl(5))
  }
  const regenerated = stl(5)
  regenerated.write('A different exporter header', 0)
  await writeFile(path.join(dir, 'versions/v2/derived.stl'), regenerated)
  check(geometryFingerprint(regenerated) === geometryFingerprint(stl(5)), 'binary STL exporter header is not a geometric change')
  const ascii = Buffer.from('solid plate\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 5 0 0\nvertex 0 1 0\nendloop\nendfacet\nendsolid plate\n')
  check(geometryFingerprint(ascii) === geometryFingerprint(stl(5)), 'ASCII and binary STL with identical vertices have the same geometry fingerprint')
  const twoFacets = Buffer.concat([stl(2).subarray(0, 84), stl(2).subarray(84), stl(3).subarray(84)])
  twoFacets.writeUInt32LE(2, 80)
  const reordered = Buffer.concat([twoFacets.subarray(0, 84), twoFacets.subarray(134), twoFacets.subarray(84, 134)])
  check(geometryFingerprint(twoFacets) === geometryFingerprint(reordered), 'facet ordering does not trigger reprinting')
  await writeFile(path.join(dir, 'scene.json'), JSON.stringify(scene(true)))
  await writeFile(path.join(dir, 'moved-plate.stl'), stl(99))
  await writeFile(path.join(dir, 'clamp.stl'), stl(3))
  await writeFile(path.join(dir, 'derived.stl'), stl(5))
  await writeFile(path.join(dir, 'meta.json'), JSON.stringify({ buildId: 'test/robot', defaultBranch: 'main', defaultVersion: 'v2', versions: [
    { name: 'v2', pushedAt: '2026-09-02T00:00:00Z', message: 'Changed clamp and added one plate.' }, { name: 'v1', pushedAt: '2026-09-01T00:00:00Z', message: 'Initial plate and clamp.' },
  ] }))
  await writeFile(path.join(dir, 'workflow.json'), JSON.stringify(metadata))
  await writeFile(path.join(dir, 'versions/v1/workflow.json'), JSON.stringify(metadata))
  await writeFile(path.join(dir, 'design_spec.yaml'), 'parts:\n  derived:\n    print_orientation: flat on bed\n  unknown:\n    cots: false\n  tube:\n    cots: false\n  plate:\n    cots: true\n')
  const query = { build: 'test/robot', branch: 'main', version: 'v2' }
  let response = await readBuildWorkflows(deps, query)
  check(response.source.storage === 'snapshot', 'exact default source uses snapshot')
  check(response.metadata.workflow.level === 'branch-fallback', 'current branch metadata fallback is disclosed')
  check((await readBuildWorkflows(deps, { ...query, version: 'v1' })).metadata.workflow.level === 'exact-revision', 'exact sidecar provenance is distinct')
  check(response.comparison.version === 'v1' && response.comparison.automatic, 'previous chronological revision selected')
  const plate = response.printed.find((part) => part.partType === 'plate')!
  check(plate.quantity === 3 && plate.files[0].change === 'quantity' && plate.files[0].quantityToPrint === 1 && plate.files[0].previousQuantity === 2, 'renamed URL and moved instances preserve geometry; only added copy prints')
  check(response.printed.find((part) => part.partType === 'clamp')!.files[0].change === 'changed', 'different STL bytes detect changed geometry')
  check(response.printed.find((part) => part.partType === 'derived')!.classificationSource === 'design-spec', 'explicit print orientation supplies evidence')
  check(response.printed.find((part) => part.partType === 'derived')!.files[0].change === 'unchanged', 'regenerated STL header remains unchanged in workflow comparison')
  check(response.purchased[0].quantity === 1 && !response.purchased[0].files.length && response.other[0].partType === 'tube', 'purchased and nonprinted parts remain separate without STL inference')
  check(response.unknown[0].partType === 'unknown', 'cots false alone does not classify printable parts')
  check(response.runs[0].association === 'robot-family', 'simulation run family association remains explicit')
  check(response.runs[1].association === 'unverified' && response.runs[1].summary?.includes('this selected revision differs'), 'an inherited exact run does not claim to match a different selected revision')
  check(!response.bom.items.some((item) => item.id === 'motor') && response.purchased.find((item) => item.partType === 'motor')?.quantity === 1, 'modeled purchased hardware is not counted twice when an authored BOM repeats it')
  // Existing inventory fixtures are single triangles; use closed solids for
  // actual print-export checks, then restore the inventory-only fixtures.
  const originals = new Map<string, Buffer>()
  for (const revision of ['v1','v2']) for (const [name,width] of [[revision === 'v1' ? 'old-plate.stl' : 'moved-plate.stl',1],['clamp.stl',revision === 'v1' ? 2 : 3],['derived.stl',5]] as const) {
    const filePath = path.join(dir,'versions',revision,name)
    originals.set(filePath,await readFile(filePath))
    const verts = [[0,0,0],[width,0,0],[0,1,0],[0,0,1]], faces = [[0,2,1],[0,1,3],[0,3,2],[1,2,3]]
    const bytes = Buffer.alloc(284); bytes.writeUInt32LE(4,80)
    faces.forEach((face,i) => face.forEach((v,j) => verts[v].forEach((val,k) => bytes.writeFloatLE(val,84+i*50+12+j*12+k*4))))
    await writeFile(filePath,bytes)
  }
  const tray = await downloadWorkflowPlate(deps, query, 'all')
  check(tray.fileName.endsWith('.3mf') && tray.contentType === 'model/3mf', 'single plate is direct 3MF')
  const { inflateRawSync } = await import('node:zlib')
  const modelXml = (bytes: Buffer) => {
    let offset = 0
    while (bytes.readUInt32LE(offset) === 0x04034b50) {
      const size = bytes.readUInt32LE(offset+18), n = bytes.readUInt16LE(offset+26), extra = bytes.readUInt16LE(offset+28)
      const name = bytes.toString('utf8', offset+30, offset+30+n), start = offset+30+n+extra
      if (name === '3D/3dmodel.model') return (bytes.readUInt16LE(offset+8) === 8 ? inflateRawSync(bytes.subarray(start,start+size)) : bytes.subarray(start,start+size)).toString()
      offset = start+size
    }
    throw new Error('Missing model')
  }
  const model = modelXml(tray.bytes)
  check((model.match(/<item /g) ?? []).length === 5, 'plate includes 3 plate copies, one derived part and one clamp, no purchased or unknown parts')
  check(!model.includes('p:name='), 'no unbound XML attributes')
  check(model.includes('unit="millimeter"'), '3MF units are mm')
  const changedTray = await downloadWorkflowPlate(deps, query, 'changed')
  check((modelXml(changedTray.bytes).match(/<item /g) ?? []).length === 2, 'changed tray uses additional and changed quantities')
  await rejects(() => downloadWorkflowPlate(deps, query, 'all', 'bad-printer'), /Unknown printer/, 'unknown printer rejected')
  const trayHttp = await http('/__buildviz/workflows/plate?build=test/robot&version=v2')
  check(trayHttp.statusCode === 200 && trayHttp.headers['Content-Type'] === 'model/3mf', 'tray route is available read-only')
  const crowded = scene(true)
  crowded.instances = Array.from({ length: 900 }, (_, n) => ({ ...crowded.instances[0], id: `copy${n}` }))
  await writeFile(path.join(dir, 'versions/v2/scene.json'), JSON.stringify(crowded))
  const trays = await downloadWorkflowPlate(deps, query, 'all')
  const plateFiles = [...unzipStored(trays.bytes)].filter(([name]) => name.endsWith('.3mf'))
  check(trays.fileName.endsWith('.zip') && plateFiles.length > 1, 'large selections split across trays')
  check(plateFiles.reduce((sum, [, bytes]) => sum + (modelXml(bytes).match(/<item /g) ?? []).length, 0) === 900, 'multi-tray export loses no copies')
  await writeFile(path.join(dir, 'versions/v2/scene.json'), JSON.stringify(scene(true)))
  await writeFile(path.join(dir, 'versions/v2/clamp.stl'), stl(3))
  const invalidTray = await http('/__buildviz/workflows/plate?build=test/robot&version=v2')
  check(invalidTray.statusCode === 400 && invalidTray.body.toString().includes('Clamp') && invalidTray.body.toString().includes('open edges'), 'HTTP rejects bad mesh with affected part name instead of downloading broken tray')
  for (const [filePath,bytes] of originals) await writeFile(filePath,bytes)
  const all = unzipStored((await downloadBuildWorkflows(deps, query, 'all')).bytes)
  check([...all.keys()].filter((name) => name.endsWith('.stl')).length === 3, 'full archive contains only confirmed printed files')
  check([...all.keys()].every((name) => !name.includes('/') && !name.startsWith('.')), 'archive filenames cannot traverse directories')
  const changed = unzipStored((await downloadBuildWorkflows(deps, query, 'changed')).bytes)
  check([...changed.keys()].filter((name) => name.endsWith('.stl')).length === 2, 'changed archive omits unchanged geometry')
  check([...changed.entries()].some(([name, bytes]) => name.includes('qty1') && bytes.equals(stl(1))), 'changed quantity archive includes original bytes and only delta count')
  check(changed.get('quantities.csv')!.toString().includes('previous_quantity'), 'archive includes readable quantity CSV')
  check((await downloadWorkflowFile(deps, query, plate.files[0].id)).bytes.equals(stl(1)), 'individual download uses exact selected revision bytes')
  check(new URL((await readBuildWorkflows(deps, { ...query, version: 'latest' })).downloads.all, 'http://test').searchParams.has('version') === false, 'latest working source stays working in download URLs')
  check((await readBuildWorkflows(deps, { ...query, compare: 'none' })).downloads.changed === null, 'explicit no-comparison suppresses changed download')
  check((await readBuildWorkflows(deps, { ...query, compare: 'none' })).printed.every((part) => part.files.every((file) => file.change === 'not-compared')), 'available STLs remain downloadable without a comparison baseline')
  await rejects(() => downloadWorkflowFile(deps, query, '../../private'), /Unknown printable file/, 'arbitrary paths are not file handles')
  await rejects(() => readBuildWorkflows(deps, { ...query, build: '../outside' }), /safe identifier/, 'build path traversal rejected')
  await rejects(() => readBuildWorkflows(deps, { ...query, version: 'missing' }), /Unknown revision/, 'missing revision never silently uses root')
  await rejects(() => validateWorkflowMetadata({ ...metadata, runs: [{ id: 'bad', title: 'Bad', url: 'javascript:alert(1)' }] }), /HTTP/, 'unsafe metadata links rejected')
  await rejects(() => validateWorkflowMetadata({ ...metadata, runs: [{ id: 'bad', title: 'Bad', url: 'https://example.com', association: 'exact-revision' }] }), /concrete source/, 'exact run claims require revision reference')
  check(validateWorkflowMetadata({ ...metadata, runs: [{ id: 'clip', title: 'Clip', url: '/builds/test/robot/report.html', videoUrl: '/builds/test/robot/workflow-assets/video.mp4' }] }).runs?.[0].videoUrl?.startsWith('/builds/'), 'root-relative authored media stays on its current hub')
  await rejects(() => validateWorkflowMetadata({ ...metadata, runs: [{ id: 'bad', title: 'Bad', url: '/\\external.example/clip.mp4' }] }), /unsafe URL/, 'backslash URL cannot turn root-relative link into external origin')
  await rejects(() => validateWorkflowMetadata({ ...metadata, runs: [{ id: 'bad', title: 'Bad', url: '//external.example/clip.mp4' }] }), /Invalid URL/, 'protocol-relative metadata link rejected')
  await writeFile(catalogPath, JSON.stringify({ schema: 1, items: [{ id: 'plate-view', name: 'One plate and clamp', kind: 'assembly', status: 'active', collection: 'Fixtures', description: 'Selected fixture parts.', source: { buildId: 'test/robot', branch: 'main', version: 'v2' }, view: { instanceIds: ['plate0'], partTypes: ['clamp'] } }] }))
  response = await readBuildWorkflows(deps, { ...query, catalog: 'plate-view' })
  check(response.scope.selectedInstances === 2 && response.printed.find((part) => part.partType === 'plate')?.quantity === 1, 'catalog selection unions exact instances and part types server-side')
  check(response.bom.items.length === 1 && response.bom.items[0].id === 'clamp-bolt', 'assembly BOM excludes unscoped and partially selected authored quantities')
  check(response.printed.find((part) => part.partType === 'plate')?.files[0].quantityToPrint === 0, 'baseline comparison applies the same instance scope')
  await rejects(() => readBuildWorkflows(deps, { ...query, version: 'v1', catalog: 'plate-view' }), /exact catalog source/, 'saved selection cannot be repointed at another revision')
  const downloadResponse = await http('/__buildviz/workflows/download?build=test%2Frobot&branch=main&version=v2&selection=changed')
  check(downloadResponse.statusCode === 200 && downloadResponse.body.readUInt32LE(0) === 0x04034b50 && downloadResponse.headers['Content-Type'] === 'application/zip', 'HTTP downloads work read-only without mutation credentials')
  check((await http('/__buildviz/workflows', 'POST', { buildId: 'test/robot', metadata })).statusCode === 403, 'workflow metadata mutation respects read-only')
  check((await http('/__buildviz/workflows', 'POST', { buildId: 'test/robot', metadata }, false)).statusCode === 401, 'workflow metadata mutation requires credentials')
  const basedScene = scene(true)
  basedScene.assetsBaseUrl = '/builds/_assets/'
  await writeFile(path.join(assetStoreDir, 'moved-plate.stl'), stl(1))
  await writeFile(path.join(dir, 'versions/v2/scene.json'), JSON.stringify(basedScene))
  const basedPlate = (await readBuildWorkflows(deps, query)).printed.find((part) => part.partType === 'plate')!
  check(basedPlate.files[0]?.geometrySha256 === plate.files[0].geometrySha256, 'relative mesh honors a safe manifest assetsBaseUrl')
  check(!(await downloadWorkflowFile(deps, query, basedPlate.files[0].id)).fileName.includes('-qty'), 'individual STL filename does not conflict with changed-copy quantity')
  basedScene.assetsBaseUrl = 'https://example.com/meshes'
  await writeFile(path.join(dir, 'versions/v2/scene.json'), JSON.stringify(basedScene))
  check((await readBuildWorkflows(deps, query)).printed.find((part) => part.partType === 'plate')!.errors.some((error) => error.includes('Only local')), 'remote assetsBaseUrl is rejected without network access')
  const badScene = scene(true)
  badScene.meshes[0].url = '../../../outside.stl'
  await writeFile(path.join(dir, 'versions/v2/scene.json'), JSON.stringify(badScene))
  response = await readBuildWorkflows(deps, query)
  check(response.printed.find((part) => part.partType === 'plate')!.errors.includes('Unsafe asset path'), 'relative asset traversal is reported without reading external bytes')
  await rejects(() => downloadWorkflowPlate(deps, query, 'all'), /missing printable/, 'plate rejects missing assets')
  await rejects(() => downloadBuildWorkflows(deps, query, 'all'), /incomplete print archive/, 'missing/unsafe files prevent silently incomplete archives')
  badScene.meshes[0].url = 'linked.stl'
  await writeFile(path.join(home, 'outside.stl'), stl(999))
  await symlink(path.join(home, 'outside.stl'), path.join(dir, 'versions/v2/linked.stl'))
  await writeFile(path.join(dir, 'versions/v2/scene.json'), JSON.stringify(badScene))
  check((await readBuildWorkflows(deps, query)).printed.find((part) => part.partType === 'plate')!.errors.some((error) => error.includes('symlink escapes')), 'symlink traversal cannot expose files outside build')
  badScene.meshes[0].url = 'https://example.com/plate.stl'
  await writeFile(path.join(dir, 'versions/v2/scene.json'), JSON.stringify(badScene))
  check((await readBuildWorkflows(deps, query)).printed.find((part) => part.partType === 'plate')!.errors.some((error) => error.includes('Only local')), 'remote geometry is never fetched')
  await writeFile(path.join(dir, 'versions/v2/scene.json'), JSON.stringify(scene(true)))
  await writeFile(path.join(dir, 'versions/v2/scene.json'), JSON.stringify({ ...scene(true), units: 'cm' }))
  check((await readBuildWorkflows(deps, query)).warnings.some((warning) => warning.includes('Bambu Studio expects millimeters')), 'non-mm source explicitly warns about slicer units')
  await rejects(() => downloadBuildWorkflows(deps, query, 'all'), /millimeter/, 'non-mm STL archive is blocked instead of silently exporting wrong scale')
  await rejects(() => downloadWorkflowFile(deps, query, plate.files[0].id), /millimeter/, 'non-mm individual STL download is blocked')
  await writeFile(path.join(dir, 'versions/v2/scene.json'), JSON.stringify(scene(true)))
  await rm(path.join(dir, 'versions/v1/old-plate.stl'))
  response = await readBuildWorkflows(deps, query)
  check(response.downloads.changed === null && response.warnings.some((warning) => warning.includes('baseline')), 'incomplete baseline blocks false change claims')
  check((await readFile(path.join(dir, 'workflow.json'), 'utf8')) === JSON.stringify(metadata), 'workflow reads/downloads do not mutate metadata')
  console.log(`Build workflow checks: ${count} passed`)
} finally { await rm(home, { recursive: true, force: true }) }
