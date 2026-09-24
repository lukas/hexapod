#!/usr/bin/env node
import { spawnSync } from 'node:child_process'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const packageRoot = dirname(dirname(fileURLToPath(import.meta.url)))
const tsxBin = join(packageRoot, 'node_modules', 'tsx', 'dist', 'cli.mjs')
const cliEntry = join(packageRoot, 'cli', 'buildviz.ts')

const result = spawnSync(process.execPath, [tsxBin, cliEntry, ...process.argv.slice(2)], {
  stdio: 'inherit',
})

if (result.error) {
  console.error(result.error.message)
  process.exitCode = 1
} else {
  process.exitCode = result.status ?? 0
}
