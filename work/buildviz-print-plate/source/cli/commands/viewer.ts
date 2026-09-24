import { mkdir } from 'node:fs/promises'
import path from 'node:path'
import {
  loadBuild,
  buildViewerUrl,
} from '../cliBuild'

// `buildviz screenshot`: drive a headless browser against the viewer.

export const screenshotBuild = async (
  build: Awaited<ReturnType<typeof loadBuild>>,
  partType: string,
  outPath: string,
  baseUrl: string,
  isolate = false,
) => {
  const { chromium } = await import('playwright')
  // --isolate rides the single-part deep link: only the part, camera framed on it.
  const url = new URL(
    buildViewerUrl(build, baseUrl, { part: partType, isolate: isolate ? '1' : undefined }),
  )

  const browser = await chromium.launch()
  try {
    const page = await browser.newPage({ viewport: { width: 1400, height: 950 } })
    await page.goto(url.toString(), { waitUntil: 'networkidle' })
    await page.waitForSelector('[data-buildviz-ready="true"]', { timeout: 15_000 })
    await mkdir(path.dirname(path.resolve(outPath)), { recursive: true })
    await page.screenshot({ path: outPath, fullPage: true })
    console.log(`Wrote ${outPath}`)
  } finally {
    await browser.close()
  }
}

