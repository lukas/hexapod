// Run against the BuildViz dev server: node scripts/checkSceneLoading.mjs
// Uses installed Chrome, or PLAYWRIGHT_CHANNEL for another installed browser.
// BUILDVIZ_TEST_URL can target a deployed viewer with the same wired build.
import assert from 'node:assert/strict'
import { chromium } from 'playwright'

const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome' })
try {
  const page = await browser.newPage()
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.addInitScript(() => {
    window.sceneDrawCalls = 0
    for (const context of [WebGLRenderingContext, WebGL2RenderingContext]) {
      for (const name of ['drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced']) {
        const original = context.prototype[name]
        if (!original) continue
        context.prototype[name] = function (...args) {
          window.sceneDrawCalls++
          return original.apply(this, args)
        }
      }
    }
  })
  let releaseMeshes
  const meshGate = new Promise((resolve) => { releaseMeshes = resolve })
  let pendingMeshes = 0
  await page.route('**/*.stl', async (route) => {
    pendingMeshes++
    await meshGate
    await route.continue()
  })
  await page.goto(process.env.BUILDVIZ_TEST_URL || 'http://127.0.0.1:5173/?build=hexapod-prototype')
  await page.waitForSelector('.viewer-canvas canvas')
  await page.waitForTimeout(750)
  assert.ok(pendingMeshes > 0, 'The test must hold real mesh downloads')
  assert.equal(await page.locator('.viewer-canvas').getAttribute('data-buildviz-ready'), 'false')
  assert.equal(await page.evaluate(() => window.sceneDrawCalls), 0,
    'Nothing should draw before the assembly and camera are ready')
  releaseMeshes()
  await page.waitForSelector('[data-buildviz-ready="true"]', { timeout: 30000 })
  assert.ok(await page.evaluate(() => window.sceneDrawCalls) > 0,
    'The complete scene should render after meshes arrive')
  await page.getByLabel('Show wires').uncheck()
  await page.getByLabel('Show wires').check()
  assert.deepEqual(errors, [])
  console.log('PASS: delayed meshes stay blank, then the assembly renders; wire toggle works.')
} finally {
  await browser.close()
}
