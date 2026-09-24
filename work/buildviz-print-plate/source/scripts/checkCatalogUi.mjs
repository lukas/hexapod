// Browser regression checks against a running hub; never starts a server or
// writes hub data. All fixture catalog/index/scene responses are intercepted.
// node scripts/checkCatalogUi.mjs (BUILDVIZ_TEST_URL defaults to the :5183 hub)
import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { chromium } from 'playwright'

const base = process.env.BUILDVIZ_TEST_URL || 'http://127.0.0.1:5183/'
const screenshotDir = process.env.BUILDVIZ_SCREENSHOTS || '/tmp/buildviz-catalog-ui'
const revisionMessage = 'Add clearance around the upper bearing so the bracket can be assembled without forcing the printed support. Preserve the lower mounting pattern for the existing chassis.'
const source = { buildId: 'catalog-test/robot', branch: 'main', version: 'v2' }
const secondSource = { buildId: 'catalog-test/second', branch: 'main', version: 'v7' }
const catalog = { schema: 1, items: [
  { id: 'robot-one', name: 'First robot', kind: 'robot', collection: 'Hexapods', status: 'built', description: 'Original robot with printed leg brackets and the installed chassis.', source, asBuilt: { ...source, version: 'v1', evidence: 'Recorded from the physical assembly.' }, milestones: [{ name: 'First assembly', description: 'Record the original installed assembly before changing the bracket.', source: { ...source, version: 'v1' } }] },
  { id: 'robot-two', name: 'Second robot', kind: 'robot', collection: 'Hexapods', status: 'built', description: 'Second robot with an updated bearing arrangement.', source: secondSource, aliases: ['deck upgrade'] },
  { id: 'robot-metal', name: 'Metal C-clamp robot', kind: 'robot', collection: 'Hexapods', status: 'planned', description: 'Next robot using purchased metal brackets.', source },
  { id: 'robot-chassis', name: 'Chassis assembly', kind: 'assembly', collection: 'Hexapods', status: 'active', description: 'The top plate in the current robot design.', parentId: 'robot-one', source, view: { partTypes: ['plate'] } },
  { id: 'second-chassis', name: 'Chassis assembly', kind: 'assembly', collection: 'Hexapods', status: 'active', description: 'A different robot chassis with its own source history.', parentId: 'robot-two', source: secondSource, aliases: ['deck'], view: { partTypes: ['plate'] } },
  { id: 'second-mount', name: 'A bearing mount', kind: 'assembly', collection: 'Hexapods', status: 'active', description: 'Another assembly on the same robot.', parentId: 'robot-two', source: secondSource, view: { partTypes: ['bearing'] } },
  { id: 'bearing-view', name: 'Bearing access view', kind: 'view', collection: 'Hexapods', status: 'active', description: 'Inspect the upper bearing without the surrounding plate.', parentId: 'robot-one', source, view: { instanceIds: ['bearing'] } },
  { id: 'missing-view', name: 'Missing part view', kind: 'view', collection: 'Hexapods', status: 'active', description: 'Preserve a removed part reference so the missing target is visible.', parentId: 'robot-one', source, view: { instanceIds: ['removed-part'] } },
  { id: 'old-study', name: 'Retired mounting experiment', kind: 'study', collection: 'Hexapods', status: 'archived', description: 'Archived mounting study.', parentId: 'robot-one', source },
] }
const index = { schema: 2, builds: [{ id: source.buildId, project: 'catalog-test', build: 'robot', name: 'Source robot scene', defaultBranch: 'main', defaultVersion: 'v2', versions: [
  { name: 'v2', isDefault: true, pushedAt: '2026-09-08T10:00:00Z', message: revisionMessage },
  { name: 'v1', isDefault: false, pushedAt: '2026-08-01T10:00:00Z', message: 'Record the first installed assembly with printed brackets.' },
] }, { id: secondSource.buildId, project: 'catalog-test', build: 'second', name: 'Second source', defaultBranch: 'main', defaultVersion: 'v7', versions: [
  { name: 'v7', isDefault: true, pushedAt: '2026-09-08T11:00:00Z', message: 'Update the second robot chassis around its bearing supports.' },
] }] }
const catBuilds = [
  ['crank-quadruped', 'Single motor cute cat walking toy', 'v44'],
  ['tt-build-cradles', 'TT cat side build cradles', 'v1'],
  ['tt-crank-quadruped', 'Single TT motor cute cat walking toy', 'v28'],
].map(([build, name, version]) => ({ id: `single-motor-cat/${build}`, project: 'single-motor-cat', build, name, defaultBranch: 'main', defaultVersion: version, versions: [{ name: version, isDefault: true }] }))
index.builds.push(...catBuilds)
const translate = (x, y, z) => [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, x, y, z, 1]
const scene = { name: 'Catalog test assembly', units: 'mm', center: [0, 0, 0], meshes: [
  { id: 'plate', name: 'Chassis plate', primitive: { kind: 'box', size: [90, 60, 5] } },
  { id: 'bearing', name: 'Bearing', primitive: { kind: 'cylinder', radius: 12, depth: 10 } },
], instances: [
  { id: 'plate', meshId: 'plate', name: 'Top plate', partType: 'plate', role: 'Chassis structure', color: '#64748b', transform: translate(0, 0, 0) },
  { id: 'bearing', meshId: 'bearing', name: 'Upper bearing', partType: 'bearing', role: 'Yaw pivot', color: '#d6a54d', transform: translate(20, 0, 15) },
] }

await mkdir(screenshotDir, { recursive: true })
const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || undefined })
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 }, colorScheme: 'light' })
  const errors = []
  const requestedScenes = []
  page.on('pageerror', (error) => errors.push(error.message))
  // Scoped auth for hosted viewer reads. Never attach the key to CDN or other
  // third-party requests; fixture routes below continue to intercept all data.
  if (process.env.BUILDVIZ_API_KEY) {
    const origin = new URL(base).origin
    await page.route(`${origin}/**`, (route) => route.continue({ headers: { ...route.request().headers(), 'X-API-Key': process.env.BUILDVIZ_API_KEY } }))
  }
  await page.route('**/__buildviz/catalog', (route) => route.fulfill({ json: catalog }))
  await page.route('**/builds/index.json', (route) => route.fulfill({ json: index }))
  await page.route(/\/builds\/(catalog-test|single-motor-cat)\//, (route) => {
    if (route.request().url().endsWith('/scene.json')) {
      requestedScenes.push(new URL(route.request().url()).pathname)
      return route.fulfill({ json: scene })
    }
    return route.fulfill({ status: 404, body: 'Fixture sidecar unavailable' })
  })
  await page.goto(base)
  await page.waitForSelector('.catalog-robot-card')
  assert.equal(await page.locator('.catalog-robot-card').count(), 3)
  await page.screenshot({ path: `${screenshotDir}/desktop-home.png`, fullPage: true })
  assert.equal(await page.getByRole('navigation', { name: 'First robot assemblies' }).getByRole('link', { name: 'Chassis assembly' }).count(), 1)
  await page.getByRole('button', { name: 'Jump to project or assembly', exact: true }).click()
  const quickDialog = page.getByRole('dialog', { name: 'Jump to project or assembly', exact: true })
  await page.getByRole('searchbox', { name: 'Search projects and assemblies' }).fill('chassis')
  assert.equal(await quickDialog.getByRole('link').count(), 2)
  assert.ok(await quickDialog.getByRole('link', { name: 'Chassis assembly — First robot', exact: true }).isVisible())
  assert.ok(await quickDialog.getByRole('link', { name: 'Chassis assembly — Second robot', exact: true }).isVisible())
  await page.getByRole('searchbox', { name: 'Search projects and assemblies' }).fill('Second deck')
  assert.equal(await quickDialog.locator('a[href="?catalog=second-chassis"], a[href="?catalog=second-mount"]').count(), 2, 'Alias and owning robot can be searched together')
  assert.equal(await quickDialog.getByRole('link').first().getAttribute('href'), '?catalog=second-chassis', 'A part matching deck directly must rank above a part matching only its robot alias')
  await page.getByRole('searchbox', { name: 'Search projects and assemblies' }).fill('not-a-real-assembly')
  assert.ok(await quickDialog.getByRole('status').isVisible())
  await page.keyboard.press('Escape')
  assert.equal(await quickDialog.count(), 0)
  assert.ok(await page.getByRole('button', { name: 'Jump to project or assembly', exact: true }).evaluate((button) => button === document.activeElement))
  await page.getByRole('button', { name: 'Jump to project or assembly', exact: true }).click()
  await quickDialog.getByRole('button', { name: 'Projects', exact: true }).click()
  assert.equal(await quickDialog.getByRole('link').count(), 2, 'Projects tab includes sources absent from the catalog')
  await quickDialog.locator('a[href="?project=single-motor-cat"]').click()
  await page.getByRole('heading', { name: 'Single motor cat', exact: true }).waitFor()
  assert.equal(await page.getByRole('navigation', { name: 'Single motor cat builds' }).getByRole('link').count(), 3)
  await page.screenshot({ path: `${screenshotDir}/desktop-cat-project.png` })
  await page.getByRole('link', { name: 'Single TT motor cute cat walking toy' }).click()
  await page.waitForSelector('[data-buildviz-ready="true"]')
  assert.equal(new URL(page.url()).search, '?build=single-motor-cat%2Ftt-crank-quadruped')
  assert.match(requestedScenes.at(-1), /\/single-motor-cat\/tt-crank-quadruped\/scene\.json$/)
  assert.match(await page.getByRole('button', { name: 'Jump to project or assembly', exact: true }).textContent(), /Single TT motor cute cat walking toy/)
  assert.equal(await page.locator('.viewer-canvas').getAttribute('data-buildviz-visible-instances'), '2')
  await page.goto(new URL('?project=single-motor-cat&build=tt-crank-quadruped', base).href)
  await page.waitForSelector('[data-buildviz-ready="true"]')
  assert.match(requestedScenes.at(-1), /\/single-motor-cat\/tt-crank-quadruped\/scene\.json$/)
  await page.goto(new URL('?projects=1', base).href)
  await page.getByRole('navigation', { name: 'All projects' }).waitFor()
  assert.equal(await page.getByRole('navigation', { name: 'All projects' }).getByRole('link').count(), 2)
  await page.goto(new URL('?project=unknown-project', base).href)
  await page.getByRole('heading', { name: 'Project unavailable' }).waitFor()
  assert.equal(await page.locator('.viewer-canvas').count(), 0)
  await page.goto(base)
  await page.getByRole('button', { name: 'Jump to project or assembly', exact: true }).click()
  await page.getByRole('searchbox', { name: 'Search projects and assemblies' }).fill('one motor cat')
  assert.ok(await quickDialog.locator('a[href="?project=single-motor-cat"]').isVisible())
  assert.equal(await quickDialog.locator('a[href^="?build=single-motor-cat"]').count(), 3, 'One/single motor cat search includes all uncatalogued project builds')
  assert.equal(await quickDialog.locator('a[href^="?build=catalog-test"]').count(), 0, 'Catalog-covered sources are not repeated as raw builds')
  await page.screenshot({ path: `${screenshotDir}/desktop-cat-search.png` })
  // Clearing an old saved-view context must also work for raw project builds.
  await page.evaluate(() => history.replaceState(null, '', '?catalog=bearing-view&configuration=as-built&catalogContext=robot-one&version=old&compare=old'))
  await quickDialog.locator('a[href="?build=single-motor-cat%2Ftt-crank-quadruped"]').click()
  await page.waitForSelector('[data-buildviz-ready="true"]')
  assert.equal(new URL(page.url()).search, '?build=single-motor-cat%2Ftt-crank-quadruped')
  assert.equal(await page.locator('.viewer-canvas').getAttribute('data-buildviz-visible-instances'), '2')
  await page.goto(base)
  await page.getByRole('link', { name: 'First robot', exact: true }).click()
  await page.waitForSelector('[data-buildviz-ready="true"]')
  assert.equal(await page.locator('.viewer-canvas').getAttribute('data-buildviz-visible-instances'), '2')
  assert.match(requestedScenes.at(-1), /\/versions\/v2\/scene\.json$/, 'A pinned revision must use its snapshot even when it is the default')
  assert.equal(await page.locator('.catalog-about').getAttribute('open'), null, 'Long descriptions start collapsed')
  const aboveFold = await page.locator('.build-dropdown-message').evaluate((message) => {
    const bounds = message.getBoundingClientRect()
    const panel = document.querySelector('.controls-panel').getBoundingClientRect()
    return bounds.top >= panel.top && bounds.bottom <= panel.bottom
  })
  assert.ok(aboveFold, 'Current revision description must fit in the visible desktop sidebar')
  await page.screenshot({ path: `${screenshotDir}/desktop-robot.png` })
  await page.locator('.revision-history > summary').click()
  assert.equal(await page.locator('.revision-history li p').first().textContent(), revisionMessage)
  await page.screenshot({ path: `${screenshotDir}/desktop-history.png` })
  await page.getByRole('link', { name: 'As built', exact: true }).click()
  await page.waitForSelector('[data-buildviz-ready="true"]')
  assert.match(requestedScenes.at(-1), /\/versions\/v1\/scene\.json$/)
  assert.ok(await page.getByText('Recorded from the physical assembly.').isVisible())
  // A jump from an inspection URL must not carry any old configuration,
  // revision, scene, analysis, or comparison into the destination assembly.
  await page.evaluate(() => history.replaceState(null, '', `${location.href}&version=old&compare=old&milestone=0&analysis=old&scene=old.json`))
  await page.keyboard.press('Control+k')
  await page.getByRole('searchbox', { name: 'Search projects and assemblies' }).fill('Second deck')
  await page.keyboard.press('ArrowDown')
  await page.keyboard.press('Enter')
  await page.waitForURL('**/?catalog=second-chassis')
  await page.waitForSelector('[data-buildviz-ready="true"]')
  assert.equal(new URL(page.url()).search, '?catalog=second-chassis')
  assert.match(requestedScenes.at(-1), /\/catalog-test\/second\/versions\/v7\/scene\.json$/)
  assert.equal(await page.locator('.viewer-canvas').getAttribute('data-buildviz-visible-instances'), '1')
  await page.keyboard.press('Control+k')
  await page.getByRole('searchbox', { name: 'Search projects and assemblies' }).fill('First chassis')
  await page.keyboard.press('Enter')
  await page.waitForURL('**/?catalog=robot-chassis')
  await page.waitForSelector('[data-buildviz-ready="true"]')
  assert.match(requestedScenes.at(-1), /\/catalog-test\/robot\/versions\/v2\/scene\.json$/)
  await page.goto(new URL('?catalog=bearing-view', base).href)
  await page.waitForSelector('[data-buildviz-ready="true"]')
  assert.equal(await page.locator('.viewer-canvas').getAttribute('data-buildviz-source-instances'), '2')
  assert.equal(await page.locator('.viewer-canvas').getAttribute('data-buildviz-visible-instances'), '1')
  await page.screenshot({ path: `${screenshotDir}/desktop-saved-view.png` })
  await page.goto(new URL('?catalog=robot-chassis', base).href)
  await page.waitForSelector('[data-buildviz-ready="true"]')
  assert.equal(await page.locator('.viewer-canvas').getAttribute('data-buildviz-visible-instances'), '1')
  await page.goto(new URL('?catalog=missing-view', base).href)
  await page.waitForSelector('[data-buildviz-ready="true"]')
  assert.ok(await page.getByRole('alert').isVisible())
  assert.equal(await page.locator('.viewer-canvas').getAttribute('data-buildviz-visible-instances'), '0')
  await page.goto(new URL('?catalog=not-in-catalog', base).href)
  await page.getByRole('heading', { name: 'Catalog item unavailable' }).waitFor()
  assert.ok(await page.getByRole('heading', { name: 'Catalog item unavailable' }).isVisible())
  await page.goto(new URL('?catalog=robot-two&configuration=as-built', base).href)
  await page.getByText('An installed configuration has not been recorded for this item.').waitFor()
  assert.ok(await page.getByText('An installed configuration has not been recorded for this item.').isVisible())
  // A slow viewer index refresh must not erase the project inventory that the
  // app already fetched. Hold refreshes until after we use the jump picker.
  await page.addInitScript(() => {
    if (!new URLSearchParams(location.search).has('delayIndexRefresh')) return
    const fetchNormally = window.fetch.bind(window)
    const refreshAllowed = new Promise((resolve) => { window.resumeIndexRefresh = resolve })
    window.fetch = async (...args) => {
      if (String(args[0]).includes('/builds/index.json') && document.querySelector('.catalog-quick-trigger')) await refreshAllowed
      return fetchNormally(...args)
    }
  })
  await page.goto(new URL('?catalog=robot-one&delayIndexRefresh=1', base).href)
  await page.getByRole('button', { name: 'Jump to project or assembly', exact: true }).click()
  await page.getByRole('searchbox', { name: 'Search projects and assemblies' }).fill('one motor cat')
  assert.equal(await quickDialog.getByRole('link').count(), 4, 'All cat destinations must be available before the viewer refresh completes')
  assert.equal(await page.locator('[data-buildviz-ready="true"]').count(), 0, 'The viewer refresh should still be held')
  await page.evaluate(() => window.resumeIndexRefresh())
  await page.waitForSelector('[data-buildviz-ready="true"]')
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto(base)
  await page.waitForSelector('.catalog-robot-card')
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'Mobile catalog must not overflow horizontally')
  await page.screenshot({ path: `${screenshotDir}/mobile-home.png`, fullPage: true })
  await page.goto(new URL('?catalog=bearing-view', base).href)
  await page.waitForSelector('[data-buildviz-ready="true"]')
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'Mobile viewer must not overflow horizontally')
  await page.screenshot({ path: `${screenshotDir}/mobile-view.png` })
  await page.getByRole('button', { name: 'Jump to project or assembly', exact: true }).click()
  await page.getByRole('searchbox', { name: 'Search projects and assemblies' }).fill('Second deck')
  const menuBounds = await quickDialog.boundingBox()
  assert.ok(menuBounds && menuBounds.x >= 0 && menuBounds.y >= 0 && menuBounds.x + menuBounds.width <= 390 && menuBounds.y + menuBounds.height <= 844, 'Mobile jump menu must fit inside the viewport')
  await page.screenshot({ path: `${screenshotDir}/mobile-quick-nav.png` })
  await quickDialog.getByRole('link', { name: 'Chassis assembly — Second robot', exact: true }).click()
  await page.waitForURL('**/?catalog=second-chassis')
  await page.waitForSelector('[data-buildviz-ready="true"]')
  assert.equal(await page.locator('.viewer-canvas').getAttribute('data-buildviz-visible-instances'), '1')
  await page.route('**/__buildviz/catalog', (route) => route.fulfill({ status: 404 }))
  await page.goto(new URL('?project=single-motor-cat', base).href)
  await page.getByRole('heading', { name: 'Single motor cat', exact: true }).waitFor()
  assert.equal(await page.getByRole('navigation', { name: 'Single motor cat builds' }).getByRole('link').count(), 3, 'Project browsing works without any catalog')
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'Mobile project page must not overflow')
  await page.screenshot({ path: `${screenshotDir}/mobile-cat-project.png`, fullPage: true })
  await page.goto(new URL('?build=catalog-test%2Frobot', base).href)
  await page.waitForSelector('[data-buildviz-ready="true"]')
  assert.equal(await page.locator('.viewer-canvas').getAttribute('data-buildviz-visible-instances'), '2')
  assert.deepEqual(errors, [])
  console.log(`PASS: project discovery, uncatalogued builds, clean cross-project jumps, catalog navigation, revision descriptions, as-built pins, saved view/assembly filtering, missing-reference guards, responsive layout, and legacy fallback. Screenshots: ${screenshotDir}`)
} finally {
  await browser.close()
}
