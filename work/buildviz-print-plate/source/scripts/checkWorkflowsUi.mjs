// Read-only browser regression against the existing central hub. Every fixture
// build, workflow, and download response is intercepted; no hub data is written.
// BUILDVIZ_SCREENSHOTS=/path node scripts/checkWorkflowsUi.mjs
import assert from 'node:assert/strict'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { chromium } from 'playwright'

const base = process.env.BUILDVIZ_TEST_URL || 'http://127.0.0.1:5183/'
assert.ok(['127.0.0.1', 'localhost'].includes(new URL(base).hostname) && new URL(base).port === '5183', 'Use the existing local central hub on port 5183')
const artifacts = process.env.BUILDVIZ_SCREENSHOTS || '/tmp/buildviz-workflows-ui'
const origin = new URL(base).origin
const source = { buildId: 'workflow-test/robot', branch: 'main', version: 'v3' }
const versions = ['v3', 'v2', 'v1'].map((name, index) => ({ name, isDefault: index === 0, pushedAt: `2026-09-0${8 - index}T12:00:00Z`, message: `Revision ${name} records the bearing support and spacer assembly.` }))
const catalog = { schema: 1, items: [
  { id: 'workflow-robot', name: 'Workflow robot', collection: 'Test workshop', kind: 'robot', status: 'built', description: 'An installed robot with printed bracket and spacer revisions.', source },
  { id: 'workflow-assembly', name: 'Bearing assembly', collection: 'Test workshop', kind: 'assembly', status: 'active', parentId: 'workflow-robot', description: 'Printed support parts for the bearing.', source, view: { partTypes: ['bracket', 'spacer', 'cover'] } },
] }
const index = { schema: 2, builds: [{ id: source.buildId, project: 'workflow-test', build: 'robot', name: 'Workflow source robot', defaultBranch: 'main', defaultVersion: 'v3', versions }] }
const scene = { name: 'Workflow robot', units: 'mm', center: [0, 0, 0], meshes: [{ id: 'box', name: 'Test geometry', primitive: { kind: 'box', size: [25, 20, 8] } }], instances: ['bracket', 'spacer', 'cover'].map((partType, index) => ({ id: partType, partType, meshId: 'box', name: partType, color: '#778aa0', transform: [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, index * 35, 0, 0, 1] })) }
const endpoint = (name, compare = 'v2', extra = {}) => `/__buildviz/workflows/${name}?${new URLSearchParams({ build: source.buildId, branch: source.branch, version: source.version, catalog: 'workflow-assembly', compare, ...extra })}`
const printed = (partType, label, quantity, previousQuantity, quantityToPrint, change) => ({ partType, label, kind: 'printed', quantity, instanceIds: [partType], material: 'PETG', classificationSource: 'workflow', errors: [], files: [{ id: partType, fileName: `${partType}.stl`, meshIds: ['box'], sha256: partType.repeat(8), geometrySha256: partType.repeat(8), bytes: 100, quantity, previousQuantity, quantityToPrint, change, downloadUrl: endpoint('file', 'v2', { file: partType }) }] })
function fixture(compare = 'v2') {
  const value = {
    schema: 1, source: { ...source, name: 'Bearing assembly test', storage: 'snapshot', units: 'mm' },
    scope: { catalogId: 'workflow-assembly', name: 'Bearing assembly', selectedInstances: 3, totalInstances: 4 },
    metadata: { workflow: { level: 'exact-revision', file: 'workflow.json', note: 'Authored metadata for this exact revision.' }, designSpec: { level: 'missing', file: 'design_spec.yaml', note: 'No design spec has been attached.' } },
    printed: [printed('bracket', 'Bearing bracket', 6, 6, 6, 'changed'), printed('spacer', 'Joint spacer', 8, 6, 2, 'quantity'), printed('cover', 'Motor cover', 1, 1, 0, 'unchanged')],
    purchased: [{ partType: 'servo', label: 'STS motor', kind: 'purchased', quantity: 18, instanceIds: [], classificationSource: 'workflow', errors: [], files: [], url: 'https://example.com/servo', notes: 'Reuse installed motors where serviceable.' }],
    other: [], unknown: [{ partType: 'sensor', label: 'Unclassified sensor shell', kind: 'unknown', quantity: 1, instanceIds: [], classificationSource: 'unclassified', errors: [], files: [] }],
    bom: { notes: 'Fasteners are additional to the scene parts.', items: [{ id: 'bolt', label: 'M3 socket bolts', quantity: 36, unit: 'pieces', url: 'https://example.com/bolts' }, { id: 'unsafe', label: '=untrusted-label', quantity: 1, url: 'javascript:alert(1)' }] },
    instructions: [{ id: 'fit', title: 'Fit the bearing support', text: 'Place the bearing into the printed bracket. Check the fit before tightening the screws.', url: 'https://example.com/assembly' }, { id: 'plain', title: 'Authored text remains plain text', text: '<img src=x onerror=alert(1)>', url: 'javascript:alert(1)' }],
    runs: [{ id: 'walk', title: 'Slow walk evaluation', url: 'https://example.com/run', videoUrl: '/__buildviz/workflow-test-video.mp4', association: 'robot-family', model: 'STS three-bearing family', summary: 'A recorded family-level MuJoCo evaluation.' }, { id: 'unsafe', title: 'Unverified imported reference', url: 'javascript:alert(1)', videoUrl: 'data:text/html,unsafe', association: 'unverified' }],
    baselines: versions.slice(1), comparison: { version: compare, automatic: compare === 'v2', note: `Compared actual STL bytes and quantities with ${compare}; placement changes do not require reprinting.`, removed: [{ partType: 'old-cap', quantity: 2 }] },
    downloads: { all: endpoint('download', compare, { selection: 'all' }), changed: endpoint('download', compare, { selection: 'changed' }), quantities: endpoint('quantities', compare) }, warnings: ['One part type is unclassified and excluded from print downloads.'],
  }
  if (compare === 'v1') {
    value.printed = [printed('bracket', 'Bearing bracket', 6, 6, 0, 'unchanged'), printed('spacer', 'Joint spacer', 8, 4, 4, 'quantity'), printed('cover', 'Motor cover', 1, 0, 1, 'new')]
    for (const part of value.printed) for (const file of part.files) file.downloadUrl = endpoint('file', compare, { file: file.id })
  }
  value.printed[0].notes = 'Print both bearing brackets together and check the mating fit.'
  return value
}

await mkdir(artifacts, { recursive: true })
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || undefined })
const report = { checks: [], screenshots: [], errors: [] }
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 }, colorScheme: 'light', acceptDownloads: true })
  page.on('pageerror', (error) => report.errors.push(error.message))
  let mode = 'normal'
  let releaseBaseline
  let baselineObserved
  let holdBaseline = false
  const observedBaseline = new Promise((resolve) => { baselineObserved = resolve })
  const requests = []
  await page.route(`${origin}/__buildviz/catalog`, (route) => route.fulfill({ json: catalog }))
  await page.route(`${origin}/builds/index.json`, (route) => route.fulfill({ json: index }))
  await page.route(`${origin}/builds/workflow-test/**`, (route) => route.fulfill(route.request().url().endsWith('/scene.json') ? { json: scene } : { status: 404, body: 'Fixture sidecar unavailable' }))
  await page.route(`${origin}/__buildviz/workflow-test-video.mp4`, (route) => route.fulfill({ contentType: 'video/mp4', body: Buffer.alloc(0) }))
  await page.route((url) => url.origin === origin && url.pathname.startsWith('/__buildviz/workflows'), async (route) => {
    const url = new URL(route.request().url())
    requests.push(url)
    assert.equal(url.searchParams.get('build'), source.buildId)
    assert.equal(url.searchParams.get('branch'), source.branch)
    assert.equal(url.searchParams.get('version'), source.version)
    assert.equal(url.searchParams.get('catalog'), 'workflow-assembly')
    if (url.pathname.endsWith('/download')) return route.fulfill({ contentType: 'application/zip', headers: { 'Content-Disposition': `attachment; filename="fixture-${url.searchParams.get('selection')}-stls.zip"` }, body: Buffer.from(`PK fixture ${url.searchParams.get('selection')}`) })
    if (url.pathname.endsWith('/file')) return route.fulfill({ contentType: 'model/stl', headers: { 'Content-Disposition': `attachment; filename="${url.searchParams.get('file')}.stl"` }, body: 'solid fixture\nendsolid fixture\n' })
    if (mode === 'error') return route.fulfill({ status: 503, json: { error: 'Fixture inventory is temporarily unavailable.' } })
    const compare = url.searchParams.get('compare') || 'v2'
    if (compare === 'v1' && holdBaseline) {
      await new Promise((resolve) => { releaseBaseline = resolve; baselineObserved() })
    }
    const value = fixture(compare)
    if (mode === 'missing') { value.printed[0].files = []; value.printed[0].errors = ['bracket.stl is missing.'] }
    if (mode === 'empty') { value.printed = []; value.purchased = []; value.bom.items = []; value.unknown = []; value.instructions = []; value.runs = []; value.baselines = []; value.comparison.version = null; value.downloads.changed = null }
    if (mode === 'incomplete') { value.downloads.changed = null; value.comparison.note = 'Comparison is incomplete because baseline printable assets are missing.' }
    if (mode === 'units') value.source.units = 'm'
    if (mode === 'fresh') { value.baselines = []; value.comparison.version = null; value.downloads.changed = null; for (const part of value.printed) for (const file of part.files) file.change = 'not-compared' }
    return route.fulfill({ json: value })
  })
  const dialog = page.getByRole('dialog', { name: 'Build workflows', exact: true })
  const screenshot = async (name) => { const path = `${artifacts}/${name}.png`; await page.screenshot({ path }); report.screenshots.push(path) }
  const loaded = () => page.waitForFunction(() => document.querySelector('.workflow-content')?.getAttribute('aria-busy') === 'false')
  const goto = async (workflow = '') => {
    await page.goto(new URL(`?catalog=workflow-assembly&keep=literal${workflow ? `&workflow=${workflow}` : ''}`, base).href)
    await page.waitForSelector('[data-buildviz-ready="true"]')
    await page.waitForFunction(() => document.querySelector('.workflow-launch small')?.textContent !== '…')
  }
  const download = async (locator) => {
    // Chromium sends <a download> requests outside page.route interception.
    // Temporarily rely on the fixture endpoint's Content-Disposition instead;
    // the real-data smoke verifies the unchanged native download attributes.
    const hadDownload = await locator.evaluate((node) => node instanceof HTMLAnchorElement && node.hasAttribute('download'))
    if (hadDownload) await locator.evaluate((node) => node.removeAttribute('download'))
    const event = page.waitForEvent('download')
    await locator.click()
    const result = await event
    if (hadDownload) await locator.evaluate((node) => node.setAttribute('download', ''))
    assert.equal(await result.failure(), null, `Download ${result.url()}; intercepted ${requests.at(-1)?.href}`)
    return { name: result.suggestedFilename(), bytes: await readFile(await result.path()) }
  }

  await goto()
  assert.match(await page.getByRole('button', { name: 'Print parts', exact: true }).textContent(), /3 STLs/)
  for (const name of ['Purchased parts', 'Assembly', 'MuJoCo runs']) assert.ok(await page.locator('.workflow-shortcuts').getByRole('button', { name, exact: true }).isVisible())
  await page.getByRole('button', { name: 'Print parts', exact: true }).click()
  await loaded()
  assert.equal(await dialog.locator('tbody tr').count(), 3)
  assert.deepEqual(await dialog.locator('.workflow-quantity').allTextContents(), ['6', '8', '1'])
  assert.match(await dialog.locator('.workflow-footer').textContent(), /3 STL files · 15 pieces/)
  assert.equal(await dialog.locator('video').count(), 0)
  assert.equal(await dialog.locator('.workflow-part-notes').first().getAttribute('open'), null)
  await dialog.locator('.workflow-part-notes > summary').first().click()
  assert.ok(await dialog.getByText('Print both bearing brackets together and check the mating fit.', { exact: true }).isVisible())
  await dialog.locator('.workflow-part-notes > summary').first().click()
  assert.match((await download(dialog.getByRole('link', { name: 'Download STLs', exact: true }))).name, /all-stls\.zip$/)
  assert.match((await download(dialog.getByRole('link', { name: 'bracket.stl', exact: true }))).bytes.toString(), /solid fixture/)
  await screenshot('desktop-print-all')
  report.checks.push('Exact catalog/source request; all files, quantities, ZIP and individual download')

  await dialog.getByRole('button', { name: 'Changed STLs', exact: true }).click()
  assert.equal(await dialog.locator('tbody tr').count(), 2)
  assert.deepEqual(await dialog.locator('.workflow-quantity').allTextContents(), ['6', '2'])
  assert.match(await dialog.locator('.workflow-footer').textContent(), /2 STL files · 8 pieces/)
  assert.match((await download(dialog.getByRole('link', { name: 'Download changed STLs', exact: true }))).name, /changed-stls\.zip$/)
  holdBaseline = true
  await dialog.getByRole('combobox', { name: 'Baseline revision' }).selectOption('v1')
  await observedBaseline
  assert.ok(await dialog.getByRole('button', { name: 'Download changed STLs', exact: true }).isDisabled())
  assert.equal(await dialog.locator('tbody a[download]').count(), 0, 'No stale individual downloads while comparing')
  holdBaseline = false
  releaseBaseline()
  await loaded()
  assert.deepEqual(await dialog.locator('.workflow-quantity').allTextContents(), ['4', '1'])
  assert.match(await dialog.locator('.workflow-footer').textContent(), /2 STL files · 5 pieces/)
  assert.equal(new URL(await dialog.getByRole('link', { name: 'Download changed STLs', exact: true }).getAttribute('href')).searchParams.get('compare'), 'v1')
  await screenshot('desktop-print-changed')
  report.checks.push('Changed quantities, baseline selection, no stale downloads during pending comparison')

  await dialog.getByRole('tab', { name: 'Purchased parts', exact: true }).click()
  assert.equal(await dialog.locator('tbody tr').count(), 3)
  const csv = await download(dialog.getByRole('button', { name: 'Download BOM CSV', exact: true }))
  assert.match(csv.name, /purchased-parts\.csv$/)
  assert.match(csv.bytes.toString(), /"STS motor","18"/)
  assert.match(csv.bytes.toString(), /"M3 socket bolts","36"/)
  assert.match(csv.bytes.toString(), /"'=untrusted-label"/)
  assert.equal(await dialog.locator('a[href^="javascript:"]').count(), 0)
  await screenshot('desktop-purchased')
  report.checks.push('Purchased parts + authored BOM CSV; formula escaping and safe source links')

  await dialog.getByRole('tab', { name: 'Assembly', exact: true }).click()
  assert.ok(await dialog.getByText('Place the bearing into the printed bracket. Check the fit before tightening the screws.', { exact: true }).isVisible())
  assert.ok(await dialog.getByText('<img src=x onerror=alert(1)>', { exact: true }).isVisible())
  assert.equal(await dialog.locator('img, a[href^="javascript:"]').count(), 0)
  await dialog.getByRole('tab', { name: 'MuJoCo runs', exact: true }).click()
  assert.equal(await dialog.locator('video').count(), 1)
  assert.equal(await dialog.locator('video').getAttribute('controls'), '')
  assert.equal(await dialog.locator('video').getAttribute('preload'), 'metadata')
  assert.equal(await dialog.locator('video[src^="data:"], video[src^="javascript:"]').count(), 0)
  assert.ok(await dialog.getByText('Robot family · revision may differ', { exact: true }).isVisible())
  await screenshot('desktop-runs')
  await page.keyboard.press('Home')
  assert.equal(await dialog.getByRole('tab', { name: 'Print parts', exact: true }).getAttribute('aria-selected'), 'true')
  await page.keyboard.press('Escape')
  assert.equal(await dialog.isVisible(), false)
  assert.deepEqual([...new URL(page.url()).searchParams], [['catalog', 'workflow-assembly'], ['keep', 'literal']])
  assert.ok(await page.getByRole('button', { name: 'Print parts', exact: true }).evaluate((node) => node === document.activeElement))
  report.checks.push('Plain authored instructions, safe inline video links, keyboard tabs/Escape/focus return, source URL preserved')

  for (const [param, tab] of [['print', 'Print parts'], ['bom', 'Purchased parts'], ['assembly', 'Assembly'], ['runs', 'MuJoCo runs']]) {
    await goto(param)
    await dialog.waitFor()
    await loaded()
    assert.equal(await dialog.getByRole('tab', { name: tab, exact: true }).getAttribute('aria-selected'), 'true')
    await dialog.getByRole('button', { name: 'Close build workflows' }).click()
    assert.equal(new URL(page.url()).searchParams.get('catalog'), 'workflow-assembly')
    assert.equal(new URL(page.url()).searchParams.has('workflow'), false)
  }
  report.checks.push('All four workflow deep links and close preserves the selected assembly')

  mode = 'missing'
  await goto('print')
  await loaded()
  assert.ok(await dialog.getByText('Some printable files are missing', { exact: true }).isVisible())
  assert.ok(await dialog.getByRole('button', { name: 'Download STLs', exact: true }).isDisabled())
  assert.ok(await dialog.getByRole('link', { name: 'spacer.stl', exact: true }).isVisible())
  mode = 'units'
  await goto('print')
  await loaded()
  assert.ok(await dialog.getByText('STL export needs millimeter units', { exact: true }).isVisible())
  assert.ok(await dialog.getByRole('button', { name: 'Download STLs', exact: true }).isDisabled())
  assert.equal(await dialog.locator('tbody a[download]').count(), 0)
  mode = 'incomplete'
  await goto('print')
  await loaded()
  await dialog.getByRole('button', { name: 'Changed STLs', exact: true }).click()
  assert.ok(await dialog.getByText('Changed STLs cannot be determined from this incomplete baseline.', { exact: true }).isVisible())
  assert.ok(await dialog.getByRole('button', { name: 'Download changed STLs', exact: true }).isDisabled())
  mode = 'fresh'
  await goto('print')
  await loaded()
  assert.ok(await dialog.getByRole('link', { name: 'Download STLs', exact: true }).isVisible(), 'A first revision still offers all valid STLs')
  assert.equal(await dialog.locator('tbody a[download]').count(), 3)
  await dialog.getByRole('button', { name: 'Changed STLs', exact: true }).click()
  assert.ok(await dialog.getByRole('button', { name: 'Download changed STLs', exact: true }).isDisabled())
  mode = 'empty'
  await goto('print')
  await loaded()
  assert.ok(await dialog.getByText('No parts are classified as printable in this revision.', { exact: true }).isVisible())
  await dialog.getByRole('tab', { name: 'Assembly', exact: true }).click()
  assert.ok(await dialog.getByText('No authored assembly instructions have been attached to this revision.', { exact: true }).isVisible())
  await dialog.getByRole('tab', { name: 'MuJoCo runs', exact: true }).click()
  assert.ok(await dialog.getByText('No MuJoCo runs have been linked to this design.', { exact: true }).isVisible())
  mode = 'error'
  await goto('print')
  await loaded()
  assert.ok(await dialog.getByRole('alert').isVisible())
  mode = 'normal'
  await dialog.getByRole('button', { name: 'Try again', exact: true }).click()
  await loaded()
  assert.equal(await dialog.locator('tbody tr').count(), 3)
  report.checks.push('Missing assets, non-millimeter units, incomplete baseline, empty data, load error and successful retry')

  await page.setViewportSize({ width: 390, height: 844 })
  await goto('print')
  await loaded()
  const bounds = await dialog.boundingBox()
  const primaryBounds = await dialog.getByRole('link', { name: 'Download STLs', exact: true }).boundingBox()
  assert.ok(bounds && bounds.x >= 0 && bounds.y >= 0 && bounds.x + bounds.width <= 390 && bounds.y + bounds.height <= 844)
  assert.ok(primaryBounds && primaryBounds.y >= 0 && primaryBounds.y + primaryBounds.height <= 844, 'Primary download must remain on screen')
  assert.ok(await dialog.evaluate((node) => node.scrollWidth <= node.clientWidth), 'Mobile dialog must not overflow horizontally')
  for (const tab of ['Print parts', 'Purchased parts', 'Assembly', 'MuJoCo runs']) assert.ok(await dialog.getByRole('tab', { name: tab, exact: true }).isVisible())
  await screenshot('mobile-print')
  await dialog.getByRole('tab', { name: 'MuJoCo runs', exact: true }).click()
  await screenshot('mobile-runs')
  await page.keyboard.press('Escape')
  assert.equal(await dialog.isVisible(), false)
  report.checks.push('390 × 844 mobile sheet, all tabs and primary action visible, no horizontal clipping')
  assert.equal(report.errors.length, 0, `Browser errors: ${report.errors.join('; ')}`)
  report.workflowRequests = requests.length
  report.outcome = 'passed'
  console.log(JSON.stringify(report, null, 2))
} catch (error) {
  report.outcome = 'failed'
  report.failure = error.stack
  throw error
} finally {
  await writeFile(`${artifacts}/report.json`, JSON.stringify(report, null, 2))
  await browser.close()
}
