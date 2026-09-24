// ---------------------------------------------------------------------------
// BuildViz hub: the machine-wide, cross-process server + daemon + version cache.
//
// This module owns everything about the hub as a long-lived service:
//   * Identity + discovery: the buildviz-hub signature, ~/.buildviz/server.json,
//     and the GET /__buildviz/status verification gate.
//   * The HTTP surface: the Vite-backed server that serves /builds/index.json,
//     /builds/<id>/... assets, and the /__buildviz/* endpoints, for both the hub
//     and the single-build local viewer.
//   * Persistence: the registry (~/.buildviz/registry.json) and the per-build
//     version cache layout under ~/.buildviz/cache/<project>/<build>/.
//   * Daemon lifecycle: detached double-fork/setsid start, pidfile, rolling log,
//     stop/status/restart, autostart-on-demand for push/register/send.
//
// cli/buildviz.ts is the CLI parser/dispatcher; it imports the named API
// below (startLocalServer, runHubCommand, registerWithHub, pushToHub,
// printHubStatus, plus path constants and discovery helpers) and calls into it.
// Shared, hub-agnostic primitives (arg parsing, build-id helpers, build-dir
// discovery) live in hub/cliShared.ts so the two modules never import each
// other.
// ---------------------------------------------------------------------------
import { execFile, spawn, spawnSync } from 'node:child_process'
import { createHash, timingSafeEqual } from 'node:crypto'
import { closeSync, createReadStream, existsSync, openSync, readFileSync } from 'node:fs'
import { cp, mkdir, readFile, readdir, realpath, rename, rm, stat, unlink, writeFile } from 'node:fs/promises'
import type { IncomingMessage, ServerResponse } from 'node:http'
import os from 'node:os'
import path from 'node:path'
import { createServer } from 'vite'
import type { BuildSceneManifest, Vec3 } from '../core/buildScene'
import { specCoverage, type SpecCoverage } from '../core/buildvizCore'
import {
  DEFAULT_BRANCH_NAME,
  DEFAULT_VERSION_NAME,
  branchRootDir,
  buildsIndexFrom,
  canonicalizeBranchName,
  canonicalizeVersionName,
  compareVersionNames,
  describeBuildBranches,
  groupBuildsByProject,
  nextBumpVersion,
  normalizeVersionMessage,
  readBuildMeta,
  readSceneName,
  resolveBranchDefaultVersion,
  resolveDefaultBranch,
  resolveDefaultVersion,
  selectVersionsToPrune,
  splitProjectBuild,
  type BuildsIndexBuild,
  type CacheBranchMeta,
  type CacheVersionMeta,
} from './buildsIndex'
import { printJson } from './cliShared'
import { canonicalizeDiagramName, diagramDirFor, listDiagrams, readDiagram } from './diagramStore'
import { serveMcp } from './mcp'
import {
  ensurePartHistory,
  partHistoryBranches,
  searchPartHistory,
  summarizeParts,
  type PartSearchHit,
} from './partHistory'
import { buildPackedScene, parseBed, resolvePrinter } from '../checks/buildvizPacking'
import { exportPlateFiles, runPack, type ExportFormat } from '../checks/packExport'
import {
  assertValidBuildId,
  buildIdFromDir,
  buildvizHome,
  canonicalizeBuildId,
  isAbsoluteWebUrl,
  optionString,
  parseArgs,
  projectRoot,
  readJson,
  resolveBuildDirOption,
  resolveProjectBuild,
  type CliOptions,
} from './cliShared'
import { appendUsageEvent } from './usageLog'
import { parseBuildAddress } from '../core/buildModel'
import { normalizeVersionReason, VERSION_LEARNING_GUIDANCE, type VersionFeedback } from '../core/versionFeedback'
import { readVersionFeedback, recordVersionFeedback } from './versionFeedback'
import { requireRevisionDescription } from '../core/revisionDescription'
import {
  assertCatalogRevisionWritable, pinnedCatalogRevisions, readCatalog,
  resolveCatalogSource, upsertCatalogItems, withCatalogMutation,
} from './catalogStore'
import {
  downloadWorkflowPlate, downloadBuildWorkflows, downloadWorkflowFile, downloadWorkflowQuantities, readBuildWorkflows,
} from './buildWorkflows'
import { setBuildWorkflowMetadata } from './workflowStore'
import type { WorkflowQuery } from '../core/buildWorkflows'
import { AnalysisConflictError, PUBLISH_POLICY, VersionConflictError, publishErrorResponse, sameScene, serializeBuildMutation } from './publishPolicy'

// --- Canonical hub identity --------------------------------------------------
// The hub is the single cross-process target. Other programs MUST discover it
// via ~/.buildviz/server.json and verify it via GET /__buildviz/status before
// using it (see probeHubStatus). The signature below is what makes a hub a hub;
// a plain Vite dev server (npm run dev on 5173) serves /builds/index.json too,
// so the marker -- not the port or index -- is the source of truth.
export const HUB_SERVICE = 'buildviz-hub'
// The hub runs on its OWN default port so it can coexist permanently with a
// project's Vite dev server (which defaults to 5173). --port still overrides.
export const HUB_DEFAULT_PORT = 5183
// Default port for the local single-build viewer (`buildviz` / `buildviz serve`)
// and the project's own `npm run dev`; intentionally distinct from the hub.
export const SERVE_DEFAULT_PORT = 5173

// Vite root of the viewer app both servers boot. The viewer stays bundled with
// the hub (see plans/repo-split.md): viewer/ holds index.html + vite.config.ts,
// while public/ (bundled builds) stays at the repo root via publicDir.
const viewerRoot = path.join(projectRoot, 'viewer')

export const packageVersion = (() => {
  try {
    return (JSON.parse(readFileSync(path.join(projectRoot, 'package.json'), 'utf8')) as { version?: string })
      .version ?? '0.0.0'
  } catch {
    return '0.0.0'
  }
})()

type HubServerInfo = {
  // Identity marker written into ~/.buildviz/server.json so a reader can tell a
  // real hub discovery file from anything else before it trusts the URL.
  service?: string
  version?: string
  host: string
  port: number
  baseUrl: string
  pid: number
  startedAt: string
  // True when bound to a non-loopback host; the hub then serves read-only.
  readOnly?: boolean
}

export type HubBuildRegistration = {
  id: string
  name: string
  buildDir: string
  designSpecPath: string | null
  registeredAt: string
  // 'push' builds are hub-managed: their buildDir lives under the cache root and
  // their layouts/versions are written by POST /__buildviz/push. 'register'
  // builds point at an on-disk project directory the hub does not own.
  source?: 'register' | 'push'
}

type HubRegistry = {
  builds: HubBuildRegistration[]
}

// CacheVersionMeta ({ name, pushedAt }) is the shared model type. CacheMeta
// below is the CLI's STRICTER write-shape: readBuildMeta returns the tolerant
// BuildMeta (most fields optional), while the hub always writes every field.
export type CacheMeta = {
  schema: number
  buildId: string
  project: string
  build: string
  name: string | null
  createdAt: string
  updatedAt: string
  // The version mirrored at the build root scene.json (the build default —
  // i.e. the DEFAULT BRANCH's default version).
  defaultVersion: string
  // Legacy field kept on write for back-compat with older viewers/tools.
  latestVersion: string
  // Default-branch mirror (back-compat readers see the default branch here).
  versions: CacheVersionMeta[]
  // Branch bookkeeping: the default branch lives at the build root; every
  // other branch under branches/<name>/ with its own versions.
  defaultBranch: string
  branches: CacheBranchMeta[]
}

// Re-exported for back-compat with any consumer that imports it from the hub;
// the definition now lives in cliShared.ts (the cycle-free shared module).
export { buildvizHome }
export const serverInfoPath = path.join(buildvizHome, 'server.json')
export const registryPath = path.join(buildvizHome, 'registry.json')
// First-class daemon lifecycle files: the detached hub's pid (process-group
// leader) and a rolling stdout/stderr log.
const hubPidPath = path.join(buildvizHome, 'hub.pid')
const hubLogPath = path.join(buildvizHome, 'hub.log')
// Hub-managed builds pushed over HTTP live here. Each build keeps its current
// layout in scene.json plus an immutable snapshot per push under versions/<vN>/
// so old layouts stay viewable and diffable after restarts.
export const cacheRoot = path.join(buildvizHome, 'cache')
export const cacheBuildDir = (buildId: string) => path.join(cacheRoot, buildId)
const cacheMetaPath = (buildId: string) => path.join(cacheBuildDir(buildId), 'meta.json')

// Content-addressed store for binary assets uploaded with `push`. One file per
// unique byte sequence (sha256), shared across every build AND version, so
// identical meshes are stored exactly once (dedup). Served read-only at
// /builds/_assets/<hash>.<ext>. The "_assets" name is not a valid build id (it
// is filtered out of build discovery), so it never collides with a real build.
export const ASSET_STORE_ID = '_assets'
export const assetStoreDir = path.join(cacheRoot, ASSET_STORE_ID)
const assetStoreUrl = (fileName: string) => `/builds/${ASSET_STORE_ID}/${fileName}`

// Default cap for the TOTAL uploaded bytes in a single push (sum of all assets).
// Overridable per push via the CLI; the hub enforces it as defense in depth.
export const DEFAULT_MAX_UPLOAD_BYTES = 256 * 1024 * 1024

// Human-readable MB for cap messages: sub-1MB caps keep two decimals so a small
// `--max-upload-mb 0.1` does not render as a misleading "0MB".
const formatMb = (bytes: number): string => {
  const mb = bytes / (1024 * 1024)
  return `${mb.toFixed(mb < 1 ? 2 : 0)}MB`
}

// A conservative, filesystem-safe extension for a stored asset (defaults to stl).
const safeAssetExt = (ext: unknown): string => {
  if (typeof ext !== 'string') return 'stl'
  const cleaned = ext.replace(/^\./, '').toLowerCase().replace(/[^a-z0-9]+/g, '')
  return cleaned.length > 0 && cleaned.length <= 8 ? cleaned : 'stl'
}

// Store one asset's bytes content-addressed; returns the served URL plus whether
// the bytes already existed (dedup). Idempotent: identical bytes never rewrite.
const storeAssetBytes = async (
  bytes: Buffer,
  ext: string,
): Promise<{ url: string; hash: string; bytes: number; deduped: boolean }> => {
  const hash = createHash('sha256').update(bytes).digest('hex')
  const fileName = `${hash}.${safeAssetExt(ext)}`
  const filePath = path.join(assetStoreDir, fileName)
  const deduped = existsSync(filePath)
  if (!deduped) {
    await mkdir(assetStoreDir, { recursive: true })
    await writeFile(filePath, bytes)
  }
  return { url: assetStoreUrl(fileName), hash, bytes: bytes.length, deduped }
}

// Derive a build id from a build directory. Cache-managed builds can nest under
// hierarchical ids (e.g. ~/.buildviz/cache/prototype_v1/chassis), so the id is
// the cache-relative path; everything else falls back to the directory name.
export const buildIdForDir = (buildDir: string) => {
  const relative = path.relative(cacheRoot, buildDir)
  if (relative && !relative.startsWith('..') && !path.isAbsolute(relative)) {
    return relative.split(path.sep).join('/')
  }
  return path.basename(buildDir)
}

const ensureBuildvizHome = async () => {
  await mkdir(buildvizHome, { recursive: true })
}

const isLoopbackHost = (host: string) =>
  ['127.0.0.1', 'localhost', '::1'].includes(host)

// First non-internal IPv4 address of this machine, for `hub --lan` (bind to the
// private-network address so teammates on the same LAN/VPN can view). Throws a
// clear error when none is found (e.g. offline) so the user can pass --host.
const lanAddress = (): string => {
  const interfaces = os.networkInterfaces()
  for (const entries of Object.values(interfaces)) {
    for (const entry of entries ?? []) {
      if (entry.family === 'IPv4' && !entry.internal) return entry.address
    }
  }
  throw new Error(
    'Could not find a non-internal IPv4 address for --lan. Pass an explicit --host <addr>.',
  )
}

// Resolve the host to bind the hub to. Default is loopback (127.0.0.1). An
// explicit --host wins; --lan binds the machine's primary LAN IPv4. Any
// non-loopback bind switches the hub into READ-ONLY mode (see serveHubAsset).
const resolveBindHost = (options: CliOptions): string => {
  const explicit = optionString(options, 'host')
  if (explicit) return explicit
  if (options.lan) return lanAddress()
  return '127.0.0.1'
}

export const hubBaseUrl = (host: string, port: number) => `http://${host}:${port}`

const writeServerInfo = async (info: HubServerInfo) => {
  await ensureBuildvizHome()
  await writeFile(serverInfoPath, `${JSON.stringify(info, null, 2)}\n`, 'utf8')
}

export const readServerInfo = async () => {
  if (!existsSync(serverInfoPath)) return null
  return readJson<HubServerInfo>(serverInfoPath)
}

const readRegistry = async (): Promise<HubRegistry> => {
  if (!existsSync(registryPath)) return { builds: [] }
  const registry = await readJson<HubRegistry>(registryPath)
  return { builds: Array.isArray(registry.builds) ? registry.builds : [] }
}

const writeRegistry = async (registry: HubRegistry) => {
  await ensureBuildvizHome()
  await writeFile(registryPath, `${JSON.stringify(registry, null, 2)}\n`, 'utf8')
}

const parsePort = (value: string | undefined, fallback = SERVE_DEFAULT_PORT) => {
  if (!value) return fallback
  const port = Number(value)
  if (!Number.isInteger(port) || port <= 0 || port > 65535) {
    throw new Error(`Invalid port: ${value}`)
  }
  return port
}

const mimeTypeForPath = (filePath: string) => {
  const extension = path.extname(filePath).toLowerCase()
  const mimeTypes: Record<string, string> = {
    '.css': 'text/css',
    '.html': 'text/html',
    '.js': 'text/javascript',
    '.json': 'application/json',
    '.map': 'application/json',
    '.md': 'text/plain; charset=utf-8',
    '.mp4': 'video/mp4',
    '.png': 'image/png',
    '.stl': 'model/stl',
    '.svg': 'image/svg+xml',
    '.txt': 'text/plain',
    '.webm': 'video/webm',
    '.yaml': 'text/yaml',
    '.yml': 'text/yaml',
  }
  return mimeTypes[extension] ?? 'application/octet-stream'
}

const sendFile = async (response: ServerResponse, filePath: string | null, request?: IncomingMessage) => {
  try {
    if (!filePath) {
      response.statusCode = 404
      response.end('Not found')
      return
    }
    const info = await stat(filePath)
    if (!info.isFile()) {
      response.statusCode = 404
      response.end('Not found')
      return
    }

    response.statusCode = 200
    const contentType = mimeTypeForPath(filePath)
    response.setHeader('Content-Type', contentType)
    response.setHeader('Content-Length', String(info.size))
    let range: { start: number; end: number } | undefined
    if (contentType.startsWith('video/')) {
      response.setHeader('Accept-Ranges', 'bytes')
      const requested = request?.headers.range
      if (requested && !request?.headers['if-range']) {
        const match = /^bytes=(\d*)-(\d*)$/.exec(requested)
        const start = match?.[1] ? Number(match[1]) : Math.max(0, info.size - Number(match?.[2]))
        const end = match?.[1] && match[2] ? Math.min(Number(match[2]), info.size - 1) : info.size - 1
        if (!match || (!match[1] && !match[2]) || !Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start > end || start >= info.size) {
          response.statusCode = 416
          response.setHeader('Content-Range', `bytes */${info.size}`)
          response.setHeader('Content-Length', '0')
          response.end()
          return
        }
        range = { start, end }
        response.statusCode = 206
        response.setHeader('Content-Range', `bytes ${start}-${end}/${info.size}`)
        response.setHeader('Content-Length', String(end - start + 1))
      }
    }
    if (request?.method === 'HEAD') { response.end(); return }
    const stream = createReadStream(filePath, range)
    stream.on('error', () => response.destroy())
    stream.pipe(response)
  } catch {
    response.statusCode = 404
    response.end('Not found')
  }
}

const rewriteLocalMeshUrl = (url: string | undefined, publicBase: string) => {
  if (!url) return url
  if (/^[a-z][a-z0-9+.-]*:/i.test(url)) return url

  // Absolute /builds/<id>/... URLs are kept as-is so a manifest can reference
  // its own assets, a parent build's assets (versions), or another registered
  // build's assets (pushed layouts) without being rewritten to the wrong id.
  if (/^\/builds\/[^/]+\/.+$/.test(url)) return url

  return url.startsWith('/')
    ? url
    : `${publicBase}/${url.replace(/^\.\//, '')}`
}

const sendJson = (response: ServerResponse, value: unknown) => {
  const body = JSON.stringify(value, null, 2)
  response.statusCode = 200
  response.setHeader('Content-Type', 'application/json')
  response.setHeader('Content-Length', String(Buffer.byteLength(body)))
  response.end(body)
}

// Like sendJson, but tags the response with a content-derived ETag and honors a
// matching If-None-Match with a 304. This lets the viewer poll /builds/index.json
// cheaply: an unchanged index round-trips as a tiny header-only 304 (no body),
// so live menu refresh stays nearly free. Cache-Control: no-cache forces the
// browser to revalidate (send If-None-Match) rather than serve a stale 200.
const sendJsonWithEtag = (request: IncomingMessage, response: ServerResponse, value: unknown) => {
  const body = JSON.stringify(value, null, 2)
  const etag = `"${createHash('sha1').update(body).digest('hex')}"`
  response.setHeader('ETag', etag)
  response.setHeader('Cache-Control', 'no-cache')
  if (request.headers['if-none-match'] === etag) {
    response.statusCode = 304
    response.end()
    return
  }
  response.statusCode = 200
  response.setHeader('Content-Type', 'application/json')
  response.setHeader('Content-Length', String(Buffer.byteLength(body)))
  response.end(body)
}

const sendJsonError = (response: ServerResponse, statusCode: number, message: string) => {
  response.statusCode = statusCode
  response.setHeader('Content-Type', 'application/json')
  response.end(JSON.stringify({ ok: false, error: message }, null, 2))
}

const sendPublishError = (response: ServerResponse, error: unknown) => {
  const result = publishErrorResponse(error)
  response.statusCode = result.status
  response.setHeader('Content-Type', 'application/json')
  response.end(JSON.stringify(result.body, null, 2))
}

const readRequestJson = async <T>(request: IncomingMessage, maxBytes = 64 * 1024 * 1024) => {
  const chunks: Buffer[] = []
  let size = 0
  for await (const chunk of request) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)
    size += buffer.length
    if (size > maxBytes) throw new Error('Request body too large')
    chunks.push(buffer)
  }
  return JSON.parse(Buffer.concat(chunks).toString('utf8')) as T
}

const registrationFromPayload = async (payload: {
  buildDir?: unknown
  buildId?: unknown
  designSpecPath?: unknown
  name?: unknown
}) => {
  if (typeof payload.buildDir !== 'string' || payload.buildDir.length === 0) {
    throw new Error('register requires buildDir')
  }

  const buildDir = path.resolve(payload.buildDir)
  const buildId = typeof payload.buildId === 'string' && payload.buildId.length > 0
    ? canonicalizeBuildId(payload.buildId)
    : buildIdFromDir(buildDir)
  assertValidBuildId(buildId)

  const scenePath = path.join(buildDir, 'scene.json')
  const designSpecPath = path.resolve(
    typeof payload.designSpecPath === 'string' && payload.designSpecPath.length > 0
      ? payload.designSpecPath
      : path.join(buildDir, 'design_spec.yaml'),
  )

  // A build only requires a valid scene.json. design_spec.yaml is optional;
  // when it is absent we register the build without a design spec path.
  if (!existsSync(scenePath)) throw new Error(`Missing scene.json in ${buildDir}`)

  const sceneName = await readSceneName(scenePath)
  return {
    id: buildId,
    name: typeof payload.name === 'string' && payload.name.length > 0 ? payload.name : sceneName ?? buildId,
    buildDir,
    designSpecPath: existsSync(designSpecPath) ? designSpecPath : null,
    registeredAt: new Date().toISOString(),
  } satisfies HubBuildRegistration
}

const assertCatalogRegistrationTarget = async (buildId: string, buildDir: string, registry: HubRegistry) => {
  const previous = registry.builds.find((build) => build.id === buildId)
  if (!previous) return
  const oldDirectory = await realpath(previous.buildDir).catch(() => path.resolve(previous.buildDir))
  const newDirectory = await realpath(buildDir).catch(() => path.resolve(buildDir))
  if (oldDirectory === newDirectory) return
  const catalog = await readCatalog()
  const referenced = catalog.items.some((item) =>
    item.source.buildId === buildId || item.asBuilt?.buildId === buildId ||
    item.milestones?.some((milestone) => milestone.source.buildId === buildId))
  if (referenced) throw new Error(`Build "${buildId}" is referenced by the catalog and cannot be rebound to a different directory; register a new build identity instead`)
}

const upsertRegistration = async (registration: HubBuildRegistration) => {
  const registry = await readRegistry()
  await assertCatalogRegistrationTarget(registration.id, registration.buildDir, registry)
  const builds = registry.builds.filter((build) => build.id !== registration.id)
  builds.push(registration)
  builds.sort((a, b) => a.id.localeCompare(b.id))
  const nextRegistry = { builds }
  await writeRegistry(nextRegistry)
  return nextRegistry
}

export const buildIndexEntryFor = async (
  buildId: string,
  buildDir: string,
  fallbackName: string | null,
): Promise<BuildsIndexBuild> => {
  const { project, build } = splitProjectBuild(buildId)
  const meta = await readBuildMeta(buildDir)
  const defaultVersion = resolveDefaultVersion(meta)
  const scenePath = path.join(buildDir, 'scene.json')
  const name =
    fallbackName ?? meta?.name ?? (existsSync(scenePath) ? await readSceneName(scenePath) : null)
  const branches = await describeBuildBranches(buildDir, meta)
  return {
    id: buildId,
    project,
    build,
    name,
    defaultVersion,
    versions: branches.find((entry) => entry.isDefault)?.versions ?? [],
    defaultBranch: resolveDefaultBranch(meta),
    branches,
  }
}

const registeredBuildsIndex = async (registry: HubRegistry) => {
  const builds = await Promise.all(
    registry.builds.map((build) => buildIndexEntryFor(build.id, build.buildDir, build.name)),
  )
  return buildsIndexFrom(builds)
}

// Resolve a request path under /builds/ to a registered build plus the asset
// path inside it. Build ids can contain "/" (a hierarchy), so we match the
// longest registered id that is a path prefix of the request. This lets
// /builds/prototype_v1/chassis/scene.json and its nested mesh assets resolve to
// the "prototype_v1/chassis" build even when "prototype_v1/leg" also exists.
const resolveBuildAssetRequest = (registry: HubRegistry, restPath: string) => {
  let match: { build: HubBuildRegistration; relative: string } | null = null
  for (const build of registry.builds) {
    const prefix = `${build.id}/`
    if (restPath.startsWith(prefix)) {
      const relative = restPath.slice(prefix.length)
      if (!match || build.id.length > match.build.id.length) {
        match = { build, relative }
      }
    }
  }
  return match
}

const buildPublicBase = (buildId: string) => `/builds/${buildId}`

// Version directory names under an arbitrary branch root (the build root for
// the default branch, branches/<name>/ for the rest).
const versionNamesIn = async (branchDir: string) => {
  const versionsDir = path.join(branchDir, 'versions')
  if (!existsSync(versionsDir)) return []
  const entries = await readdir(versionsDir, { withFileTypes: true })
  return entries
    .filter((entry) => entry.isDirectory() && existsSync(path.join(versionsDir, entry.name, 'scene.json')))
    .map((entry) => entry.name)
    .sort(compareVersionNames)
}

const cacheVersionNames = async (buildId: string) => versionNamesIn(cacheBuildDir(buildId))

const readCacheMeta = async (buildId: string): Promise<CacheMeta | null> => {
  const metaPath = cacheMetaPath(buildId)
  if (!existsSync(metaPath)) return null
  try {
    return await readJson<CacheMeta>(metaPath)
  } catch {
    return null
  }
}

const normalizeSceneAssets = (
  scene: BuildSceneManifest,
  assetsBaseUrl: string | undefined,
): BuildSceneManifest => {
  if (!assetsBaseUrl) return scene
  const base = assetsBaseUrl.replace(/\/+$/, '')
  return {
    ...scene,
    meshes: scene.meshes.map((mesh) => {
      if (!mesh.url) return mesh
      // Absolute http(s) URLs and absolute /-rooted paths are left untouched so
      // callers can point at external assets or another registered build.
      if (isAbsoluteWebUrl(mesh.url) || mesh.url.startsWith('/')) return mesh
      return { ...mesh, url: `${base}/${mesh.url.replace(/^\.\//, '')}` }
    }),
  }
}

const assertSceneManifest = (scene: unknown): BuildSceneManifest => {
  if (!scene || typeof scene !== 'object') {
    throw new Error('push requires a "scene" object (the scene.json contents)')
  }
  const candidate = scene as Partial<BuildSceneManifest>
  if (!Array.isArray(candidate.meshes)) throw new Error('scene.meshes must be an array')
  if (!Array.isArray(candidate.instances)) throw new Error('scene.instances must be an array')
  const center: Vec3 = Array.isArray(candidate.center) && candidate.center.length === 3
    ? (candidate.center as Vec3)
    : [0, 0, 0]
  // Record an explicit schemaVersion when the producer supplied a valid integer;
  // drop a malformed value so the cached scene stays clean (additive, optional).
  const schemaVersion =
    typeof candidate.schemaVersion === 'number' && Number.isInteger(candidate.schemaVersion)
      ? candidate.schemaVersion
      : undefined
  return {
    ...(candidate as BuildSceneManifest),
    name: typeof candidate.name === 'string' && candidate.name.length > 0 ? candidate.name : 'Pushed build',
    units: candidate.units ?? 'mm',
    center,
    ...(schemaVersion !== undefined ? { schemaVersion } : {}),
    meshes: candidate.meshes as BuildSceneManifest['meshes'],
    instances: candidate.instances as BuildSceneManifest['instances'],
  }
}

// Publish one immutable NAMED version on one BRANCH of a hub-cached build.
// The default branch lives at the build root (versions/<v>/scene.json, default
// mirrored at scene.json — the pre-branch layout, so branch-less pushes are
// byte-identical to before); every other branch lives under branches/<name>/
// with the same internal layout. Pushing a NEW version name adds a parallel
// snapshot. Reusing a name is allowed ONLY for identical content (a retry).
// Existing scene/spec bytes and the original changelog/timestamp stay intact.
const writeCacheLayout = async (
  buildId: string,
  version: string,
  scene: BuildSceneManifest,
  designSpecText: string | null,
  name: string,
  setDefault: boolean,
  // Optional retention cap: keep at most this many cached versions per build
  // (the default version is always kept). Undefined / <= 0 means keep-all.
  keepVersions?: number,
  // Changelog for a new version; identical retries retain the original note.
  message?: string,
  // The branch this version belongs to. The first push of a NEW build defines
  // the build's default branch (usually "main").
  branch: string = DEFAULT_BRANCH_NAME,
  reason?: string,
) => {
  assertValidBuildId(buildId)
  const { project, build } = splitProjectBuild(buildId)
  const dir = cacheBuildDir(buildId)
  const previousMeta = await readCacheMeta(buildId)
  // The first push of a brand-new build defines the default branch; after
  // that, meta owns it (changed only via promoteBranchToDefault).
  const defaultBranch = previousMeta ? resolveDefaultBranch(previousMeta) : branch
  const isDefaultBranch = branch === defaultBranch
  const branchDir = branchRootDir(dir, branch, defaultBranch)
  const existing = await versionNamesIn(branchDir)
  const branchScenePath = path.join(branchDir, 'scene.json')
  const isNewBranch = existing.length === 0 && !existsSync(branchScenePath)
  const isNewBuild = !previousMeta && isDefaultBranch && isNewBranch
  const priorDefault = resolveBranchDefaultVersion(previousMeta, branch)
  // Legacy caches may have only the root scene. Reserve/preserve its original
  // name before making any new version default, rather than silently losing it.
  const legacyRoot = !isNewBranch && !existing.includes(priorDefault) && existsSync(branchScenePath)
  if (legacyRoot) existing.push(priorDefault)
  const isNewVersion = !existing.includes(version)
  // The first version on a branch, or an explicit --set-default, owns that
  // branch's default; otherwise the existing default is preserved (so pushing
  // a new snapshot does not steal "default" from the working version).
  const defaultVersion = setDefault || isNewBuild || isNewBranch ? version : priorDefault

  const body = `${JSON.stringify(scene, null, 2)}\n`
  const versionDir = path.join(branchDir, 'versions', version)
  const priorDir = legacyRoot && version === priorDefault ? branchDir : versionDir
  const oldBody = !isNewVersion ? await readFile(path.join(priorDir, 'scene.json'), 'utf8') : null
  const oldSpec = !isNewVersion && existsSync(path.join(priorDir, 'design_spec.yaml'))
    ? await readFile(path.join(priorDir, 'design_spec.yaml'), 'utf8') : null
  const effectiveSpec = designSpecText ?? (isNewVersion ? await readCacheSpecText(branchDir, priorDefault) : oldSpec)
  if (oldBody !== null && (!sameScene(oldBody, scene) || effectiveSpec !== oldSpec)) {
    throw new VersionConflictError(buildId, branch, version, existing)
  }
  const unchanged = oldBody !== null
  const priorBranchRecord = previousMeta?.branches?.find((entry) => entry.name === branch)
  const priorBranchVersions =
    priorBranchRecord?.versions ?? (isDefaultBranch ? previousMeta?.versions ?? [] : [])
  const priorVersion = priorBranchVersions.find((entry) => entry.name === version)
  if (unchanged && defaultVersion === priorDefault && previousMeta) {
    return {
      version, defaultVersion, branch, defaultBranch, isNewVersion, isNewBuild, isNewBranch,
      unchanged, versions: existing.sort(compareVersionNames), pruned: [] as string[], snapshot: null,
      message: priorVersion?.message ?? null, reason: priorVersion?.reason ?? null, cacheDir: dir, branchDir, meta: previousMeta,
    }
  }

  if (legacyRoot) {
    const legacyDir = path.join(branchDir, 'versions', priorDefault)
    await mkdir(legacyDir, { recursive: true })
    await cp(branchScenePath, path.join(legacyDir, 'scene.json'))
    const rootSpec = path.join(branchDir, 'design_spec.yaml')
    if (existsSync(rootSpec)) await cp(rootSpec, path.join(legacyDir, 'design_spec.yaml'))
  }
  // Keep the deployed catalog's pins and authored workflows intact. The
  // universal version guard above runs before these preservation writes.
  const pins = pinnedCatalogRevisions(await readCatalog()).filter((pin) =>
    pin.buildId === buildId && pin.branch === branch)
  await assertCatalogRevisionWritable(
    { buildId, branch, version }, oldBody, oldBody ?? body, oldSpec, effectiveSpec,
  )
  for (const pin of pins) {
    const pinnedDir = path.join(branchDir, 'versions', pin.version)
    if (!existsSync(path.join(pinnedDir, 'scene.json')) && pin.version === priorDefault && existsSync(branchScenePath)) {
      await mkdir(pinnedDir, { recursive: true })
      await cp(branchScenePath, path.join(pinnedDir, 'scene.json'))
    }
    const spec = path.join(branchDir, 'design_spec.yaml')
    if (!existsSync(path.join(pinnedDir, 'design_spec.yaml'))) {
      await mkdir(pinnedDir, { recursive: true })
      if (existsSync(spec)) await cp(spec, path.join(pinnedDir, 'design_spec.yaml'))
      else await writeFile(path.join(pinnedDir, 'design_spec.yaml'), '', 'utf8')
    }
  }
  if (defaultVersion === version && priorDefault !== version && existsSync(branchScenePath)) {
    const priorSnapshotDir = path.join(branchDir, 'versions', priorDefault)
    await mkdir(priorSnapshotDir, { recursive: true })
    const workflow = path.join(branchDir, 'workflow.json')
    if (existsSync(workflow) && !existsSync(path.join(priorSnapshotDir, 'workflow.json'))) {
      await cp(workflow, path.join(priorSnapshotDir, 'workflow.json'))
    }
  }
  if (!unchanged) {
    await mkdir(versionDir, { recursive: true })
    await writeFile(path.join(versionDir, 'scene.json'), body, 'utf8')
    if (effectiveSpec !== null) {
      await writeFile(path.join(versionDir, 'design_spec.yaml'), effectiveSpec, 'utf8')
    }
  }
  // Mirror the branch's default version at the branch root (the BUILD root for
  // the default branch) for back-compat resolution.
  if (defaultVersion === version) {
    await writeFile(branchScenePath, oldBody ?? body, 'utf8')
    if (effectiveSpec !== null) {
      await writeFile(path.join(branchDir, 'design_spec.yaml'), effectiveSpec, 'utf8')
    } else {
      await rm(path.join(branchDir, 'design_spec.yaml'), { force: true })
    }
  }

  const now = new Date().toISOString()
  // Version bookkeeping is per-branch: the branch's own meta record, falling
  // back to the top-level list for the default branch of pre-branch metas.
  const priorVersions = priorBranchVersions.filter(
    (entry) => entry.name !== version,
  )
  // A retry/promotion never changes a published version's original message.
  const versionMessage = unchanged ? priorVersion?.message : message
  const versionReason = unchanged ? priorVersion?.reason : reason
  let allVersionEntries: CacheVersionMeta[] = [
    ...priorVersions,
    { ...(unchanged ? priorVersion : {}), name: version, pushedAt: unchanged ? priorVersion?.pushedAt ?? previousMeta?.updatedAt ?? now : now,
      ...(versionMessage ? { message: versionMessage } : {}), ...(versionReason ? { reason: versionReason } : {}) },
  ]
  if (legacyRoot && priorDefault !== version && !allVersionEntries.some((entry) => entry.name === priorDefault)) {
    allVersionEntries.push({
      name: priorDefault,
      pushedAt: previousMeta?.updatedAt ?? now,
    })
  }

  // Retention: when a per-build cap is set, prune the OLDEST non-default cached
  // versions ON THIS BRANCH (by pushedAt) until at most `keepVersions` remain.
  // The branch default is always retained; keep-all stays the default.
  const protectedNames = new Set(pins.map((pin) => pin.version))
  const { pruned: candidates } = selectVersionsToPrune(allVersionEntries, unchanged ? undefined : keepVersions, defaultVersion)
  const pruned = candidates.filter((version) => !protectedNames.has(version))
  if (pruned.length > 0) {
    const prunedNames = new Set(pruned)
    for (const entryName of pruned) {
      await rm(path.join(branchDir, 'versions', entryName), { recursive: true, force: true }).catch(() => {})
    }
    allVersionEntries = allVersionEntries.filter((entry) => !prunedNames.has(entry.name))
  }

  // --- Branch records ---------------------------------------------------------
  // Every branch gets a record; the default branch's record is ALSO mirrored in
  // the top-level defaultVersion/versions fields for back-compat readers. When
  // an older (pre-branch) meta gains its first non-default branch, synthesize
  // the default branch's record from those top-level fields.
  const otherBranches = (previousMeta?.branches ?? []).filter((entry) => entry.name !== branch)
  if (!isDefaultBranch && !otherBranches.some((entry) => entry.name === defaultBranch)) {
    otherBranches.unshift({
      name: defaultBranch,
      defaultVersion: resolveDefaultVersion(previousMeta),
      versions: previousMeta?.versions ?? [],
    })
  }
  const branches: CacheBranchMeta[] = [
    ...otherBranches,
    { name: branch, defaultVersion, versions: allVersionEntries },
  ].sort((a, b) =>
    a.name === defaultBranch ? -1 : b.name === defaultBranch ? 1 : compareVersionNames(a.name, b.name),
  )
  const topDefaultVersion = isDefaultBranch ? defaultVersion : resolveDefaultVersion(previousMeta)
  const topVersions = isDefaultBranch ? allVersionEntries : previousMeta?.versions ?? []

  const meta: CacheMeta = {
    schema: 2,
    buildId,
    project,
    build,
    name,
    createdAt: previousMeta?.createdAt ?? now,
    updatedAt: now,
    defaultVersion: topDefaultVersion,
    latestVersion: topDefaultVersion,
    versions: topVersions,
    defaultBranch,
    branches,
  }
  await writeFile(cacheMetaPath(buildId), `${JSON.stringify(meta, null, 2)}\n`, 'utf8')

  const prunedSet = new Set(pruned)
  const names = new Set<string>([...existing, version])
  const allVersions = [...names].filter((entryName) => !prunedSet.has(entryName))
  return {
    version,
    defaultVersion,
    branch,
    defaultBranch,
    isNewVersion,
    isNewBuild,
    isNewBranch,
    unchanged,
    versions: allVersions.sort(compareVersionNames),
    pruned,
    snapshot: null,
    message: versionMessage ?? null,
    reason: versionReason ?? null,
    cacheDir: dir,
    branchDir,
    meta,
  }
}

// Make <branch> the build's DEFAULT branch by physically swapping directory
// roles: the current root content (the old default branch) moves under
// branches/<oldDefault>/, and branches/<branch>/ moves up to the build root —
// preserving the invariant that the default branch is always the pre-branch
// root layout (so branch-unaware consumers keep resolving the default).
const promoteBranchToDefault = async (buildId: string, branch: string) => {
  const dir = cacheBuildDir(buildId)
  const previousMeta = await readCacheMeta(buildId)
  const defaultBranch = resolveDefaultBranch(previousMeta)
  if (branch === defaultBranch) return previousMeta

  const branchDir = path.join(dir, 'branches', branch)
  if (!existsSync(path.join(branchDir, 'scene.json'))) {
    throw new Error(`Cannot promote branch "${branch}" of ${buildId}: it has no scene.json.`)
  }

  // 1) Demote the old default: move every root entry except meta.json and the
  //    branches/ container into branches/<oldDefault>/.
  const oldDefaultDir = path.join(dir, 'branches', defaultBranch)
  await mkdir(oldDefaultDir, { recursive: true })
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    if (entry.name === 'branches' || entry.name === 'meta.json' || entry.name === 'version-feedback.json') continue
    await rename(path.join(dir, entry.name), path.join(oldDefaultDir, entry.name))
  }
  // 2) Promote the new default: move branch contents up to the build root.
  for (const entry of await readdir(branchDir, { withFileTypes: true })) {
    await rename(path.join(branchDir, entry.name), path.join(dir, entry.name))
  }
  await rm(branchDir, { recursive: true, force: true })

  // 3) Rewrite meta: swap defaultBranch and re-mirror the top-level fields.
  // Ensure the DEMOTED branch keeps its bookkeeping even when the prior meta
  // predated branches (its history lived only in the top-level fields).
  const branchRecords = [...(previousMeta?.branches ?? [])]
  if (!branchRecords.some((entry) => entry.name === defaultBranch)) {
    branchRecords.push({
      name: defaultBranch,
      defaultVersion: resolveDefaultVersion(previousMeta),
      versions: previousMeta?.versions ?? [],
    })
  }
  const now = new Date().toISOString()
  const promoted = branchRecords.find((entry) => entry.name === branch)
  const meta: CacheMeta = {
    schema: 2,
    buildId,
    project: splitProjectBuild(buildId).project,
    build: splitProjectBuild(buildId).build,
    name: previousMeta?.name ?? null,
    createdAt: previousMeta?.createdAt ?? now,
    updatedAt: now,
    defaultVersion: promoted?.defaultVersion ?? DEFAULT_VERSION_NAME,
    latestVersion: promoted?.defaultVersion ?? DEFAULT_VERSION_NAME,
    versions: promoted?.versions ?? [],
    defaultBranch: branch,
    branches: branchRecords.sort((a, b) =>
      a.name === branch ? -1 : b.name === branch ? 1 : compareVersionNames(a.name, b.name),
    ),
  }
  await writeFile(cacheMetaPath(buildId), `${JSON.stringify(meta, null, 2)}\n`, 'utf8')
  return meta
}

type PushAssetUpload = {
  /** The scene mesh.id whose url should point at the stored bytes. */
  meshId?: unknown
  /** Base64-encoded file bytes. */
  data?: unknown
  /** File extension (defaults to stl). */
  ext?: unknown
}

// --- design_spec.yaml integration -------------------------------------------
// The design spec is the versioned record of WHAT each part is for and WHY it
// changed — the hub treats it as a first-class part of a version, and WARNS
// (never blocks) whenever that record is missing or has drifted from the
// geometry: a missing/unparseable spec, scene parts with no spec entry, spec
// entries for parts that no longer exist, geometry that changed without a spec
// update, and (for registered dirs) a spec older than the geometry it describes.

const specWarningsFromCoverage = (coverage: SpecCoverage, context: string): string[] => {
  if (!coverage.hasSpec) {
    return [
      `No design_spec.yaml for ${context} — its parts' purpose and design intent are unrecorded. ` +
        'Add one with a parts: entry per part type (see DESIGN_YAML_SPEC.md); push accepts --design-spec <file>.',
    ]
  }
  if (!coverage.parses) {
    return [`design_spec.yaml for ${context} did not parse as a YAML mapping — fix it so the recorded intent stays machine-readable.`]
  }
  if (!coverage.hasParts) {
    return [`design_spec.yaml for ${context} has no parts: section — add an entry per scene part type.`]
  }
  const warnings: string[] = []
  if (coverage.uncovered.length > 0) {
    warnings.push(
      `design_spec.yaml does not match the scene: ${coverage.uncovered.length} scene part type(s) have no entry ` +
        `(${coverage.uncovered.slice(0, 10).join(', ')}) — record each part's purpose in the same change that adds its geometry.`,
    )
  }
  if (coverage.stale.length > 0) {
    warnings.push(
      `design_spec.yaml has ${coverage.stale.length} entrie(s) with no matching scene part ` +
        `(${coverage.stale.slice(0, 10).join(', ')}) — stale drift; remove or rename them so the spec matches the scene.`,
    )
  }
  if (coverage.uncoveredWires.length > 0) {
    warnings.push(
      `${coverage.uncoveredWires.length} published wire(s) have no wiring: entry in design_spec.yaml ` +
        `(${coverage.uncoveredWires.slice(0, 10).join(', ')}) — record each wire's purpose alongside its route.`,
    )
  }
  if (coverage.staleWires.length > 0) {
    warnings.push(
      `design_spec.yaml wiring: has ${coverage.staleWires.length} entrie(s) with no matching scene route ` +
        `(${coverage.staleWires.slice(0, 10).join(', ')}) — remove or rename them so the spec matches the wiring.`,
    )
  }
  return warnings
}

// Effective design spec for a cached version: the version's own file, falling
// back to the branch root's — the same fallback the viewer uses. `branchDir`
// is the branch's on-disk root (the build root for the default branch).
const readCacheSpecText = async (branchDir: string, version: string): Promise<string | null> => {
  const candidates = [
    path.join(branchDir, 'versions', version, 'design_spec.yaml'),
    path.join(branchDir, 'design_spec.yaml'),
  ]
  for (const candidate of candidates) {
    if (existsSync(candidate)) return await readFile(candidate, 'utf8').catch(() => null)
  }
  return null
}

const readCacheVersionSceneBody = async (branchDir: string, version: string): Promise<string | null> => {
  const file = path.join(branchDir, 'versions', version, 'scene.json')
  return existsSync(file) ? await readFile(file, 'utf8').catch(() => null) : null
}

const safeMtime = async (target: string): Promise<number | null> => {
  try {
    return (await stat(target)).mtimeMs
  } catch {
    return null
  }
}

// Spec warnings for a registered on-disk build directory: coverage vs its
// scene.json plus a freshness check (scene.json or any locally-referenced mesh
// modified more recently than design_spec.yaml means the geometry was updated
// without updating the recorded intent).
const registrationSpecWarnings = async (registration: HubBuildRegistration): Promise<string[]> => {
  const scenePath = path.join(registration.buildDir, 'scene.json')
  let manifest: BuildSceneManifest
  try {
    manifest = JSON.parse(await readFile(scenePath, 'utf8')) as BuildSceneManifest
  } catch {
    return []
  }
  if (!manifest || !Array.isArray(manifest.instances)) return []
  const specText = registration.designSpecPath
    ? await readFile(registration.designSpecPath, 'utf8').catch(() => null)
    : null
  const warnings = specWarningsFromCoverage(specCoverage(manifest, specText), registration.id)

  if (registration.designSpecPath && specText !== null) {
    const specMtime = await safeMtime(registration.designSpecPath)
    if (specMtime !== null) {
      const newer: string[] = []
      const sceneMtime = await safeMtime(scenePath)
      if (sceneMtime !== null && sceneMtime > specMtime) newer.push('scene.json')
      let meshNewer = false
      for (const mesh of manifest.meshes ?? []) {
        if (typeof mesh.url !== 'string' || mesh.url.length === 0) continue
        if (isAbsoluteWebUrl(mesh.url) || mesh.url.startsWith('/')) continue
        const meshMtime = await safeMtime(path.resolve(registration.buildDir, mesh.url))
        if (meshMtime !== null && meshMtime > specMtime) {
          meshNewer = true
          break
        }
      }
      if (meshNewer) newer.push('referenced mesh geometry')
      if (newer.length > 0) {
        warnings.push(
          `design_spec.yaml is older than ${newer.join(' and ')} — the geometry was updated without updating the spec; ` +
            'confirm the recorded rationale/dimensions still match, and edit the spec in the same change as the geometry.',
        )
      }
    }
  }
  return warnings
}

type PushPayload = {
  buildId?: unknown
  version?: unknown
  // The branch the version belongs to. Omitted ⇒ the build's default branch
  // (exactly the pre-branch behavior). A new name creates the branch.
  branch?: unknown
  // Make the pushed branch the build's DEFAULT branch (--set-default-branch).
  setDefaultBranch?: unknown
  // Auto-pick the next free v<N> when no explicit version is given (the server
  // owns the numbering because only it knows the branch's existing versions).
  bump?: unknown
  // Legacy flag accepted for compatibility; never bypasses version protection.
  noSnapshot?: unknown
  setDefault?: unknown
  name?: unknown
  // REQUIRED changelog/commit note naming the version being created/bumped;
  // pushes without one are rejected (400).
  message?: unknown
  reason?: unknown
  scene?: unknown
  designSpec?: unknown
  assetsBaseUrl?: unknown
  keepVersions?: unknown
  // Optional binary asset uploads (item: self-contained pushes). Each carries a
  // meshId + base64 bytes; the hub stores them content-hashed and rewrites the
  // matching mesh url. Omitted/empty ⇒ behaves exactly as a no-upload push.
  assets?: unknown
  /** Total upload size cap (bytes); enforced server-side as defense in depth. */
  maxUploadBytes?: unknown
}

// Decode + store the uploaded assets (if any) and return a map of meshId → the
// content-addressed served url, plus a summary for the response. Enforces the
// total-size cap. Pushes without uploads return an empty map (no-op).
const storePushAssets = async (
  payload: PushPayload,
): Promise<{
  urlByMeshId: Map<string, string>
  uploaded: Array<{ meshId: string; url: string; bytes: number; deduped: boolean }>
  totalBytes: number
  dedupedBytes: number
}> => {
  const urlByMeshId = new Map<string, string>()
  const uploaded: Array<{ meshId: string; url: string; bytes: number; deduped: boolean }> = []
  if (!Array.isArray(payload.assets) || payload.assets.length === 0) {
    return { urlByMeshId, uploaded, totalBytes: 0, dedupedBytes: 0 }
  }

  const cap = numberOrUndefined(payload.maxUploadBytes) ?? DEFAULT_MAX_UPLOAD_BYTES
  let totalBytes = 0
  let dedupedBytes = 0
  for (const raw of payload.assets as PushAssetUpload[]) {
    const meshId = typeof raw.meshId === 'string' ? raw.meshId : ''
    const data = typeof raw.data === 'string' ? raw.data : ''
    if (!meshId || !data) {
      throw new Error('Each uploaded asset requires a "meshId" and base64 "data".')
    }
    const bytes = Buffer.from(data, 'base64')
    totalBytes += bytes.length
    if (totalBytes > cap) {
      throw new Error(
        `Uploaded assets exceed the size cap (${formatMb(cap)}). ` +
          'Raise it with --max-upload-mb, or push fewer/smaller meshes.',
      )
    }
    const stored = await storeAssetBytes(bytes, raw.ext as string)
    if (stored.deduped) dedupedBytes += stored.bytes
    urlByMeshId.set(meshId, stored.url)
    uploaded.push({ meshId, url: stored.url, bytes: stored.bytes, deduped: stored.deduped })
  }
  return { urlByMeshId, uploaded, totalBytes, dedupedBytes }
}

const publishSerially = serializeBuildMutation
export const pushLayoutFromPayload = (payload: PushPayload, baseUrl: string) =>
  publishSerially(() => publishLayout(payload, baseUrl))

const publishLayout = async (payload: PushPayload, baseUrl: string) => {
  const rawBuildId = typeof payload.buildId === 'string' ? payload.buildId.trim() : ''
  if (!rawBuildId) throw new Error('push requires a "buildId"')
  const buildId = canonicalizeBuildId(rawBuildId)
  if (!buildId) {
    throw new Error(`Build id "${rawBuildId}" has no usable characters; use letters or numbers.`)
  }
  assertValidBuildId(buildId)

  await assertCatalogRegistrationTarget(buildId, cacheBuildDir(buildId), await readRegistry())
  const explicitVersion =
    typeof payload.version === 'string' && payload.version.trim().length > 0
      ? canonicalizeVersionName(payload.version)
      : ''
  if (typeof payload.version === 'string' && payload.version.trim().length > 0 && !explicitVersion) {
    throw new Error(`Version "${String(payload.version)}" has no usable characters.`)
  }
  // Branch: an explicit --branch targets (or creates) that branch; omitted ⇒
  // the build's default branch, which is also what a brand-new build's first
  // push defines.
  const rawBranch = typeof payload.branch === 'string' ? payload.branch.trim() : ''
  const requestedBranch = rawBranch ? canonicalizeBranchName(rawBranch) : ''
  if (rawBranch && !requestedBranch) {
    throw new Error(`Branch "${rawBranch}" has no usable characters.`)
  }
  const priorMeta = await readCacheMeta(buildId)
  const defaultBranch = priorMeta ? resolveDefaultBranch(priorMeta) : requestedBranch || DEFAULT_BRANCH_NAME
  const branch = requestedBranch || defaultBranch
  const branchDir = branchRootDir(cacheBuildDir(buildId), branch, defaultBranch)
  // Omission is the safe path, including old clients that send bump:false.
  const reservedVersions = await versionNamesIn(branchDir)
  if (existsSync(path.join(branchDir, 'scene.json'))) reservedVersions.push(resolveBranchDefaultVersion(priorMeta, branch))
  const version = explicitVersion || nextBumpVersion(reservedVersions)
  const setDefault = payload.setDefault === true || (!explicitVersion && payload.setDefault !== false)
  const setDefaultBranch = payload.setDefaultBranch === true

  const scene = assertSceneManifest(payload.scene)
  const assetsBaseUrl = typeof payload.assetsBaseUrl === 'string' && payload.assetsBaseUrl.length > 0
    ? payload.assetsBaseUrl
    : undefined
  const designSpecText = typeof payload.designSpec === 'string' && payload.designSpec.length > 0
    ? payload.designSpec
    : null
  const name = typeof payload.name === 'string' && payload.name.length > 0
    ? payload.name
    : scene.name
  // A version message is REQUIRED: every pushed version needs a changelog-style
  // note naming the change (the viewer shows it in the version dropdown, the
  // "new version" pill, diffs, and per-part history — without one the version
  // reads as an anonymous blob).
  const message = requireRevisionDescription(payload.message)
  const reason = normalizeVersionReason(payload.reason)

  // Store any uploaded binary assets content-hashed (dedup across builds AND
  // versions), THEN rewrite the matching mesh urls to the stored, hub-served
  // path. Done after assetsBaseUrl normalization so an uploaded mesh always wins
  // (its bytes live in the cache and need no external/relative resolution).
  const uploads = await storePushAssets(payload)
  const baseNormalized = normalizeSceneAssets(scene, assetsBaseUrl)
  const normalized = {
    ...baseNormalized,
    name,
    meshes: baseNormalized.meshes.map((mesh) => {
      const url = uploads.urlByMeshId.get(mesh.id)
      return url ? { ...mesh, url } : mesh
    }),
  }
  const keepVersions = numberOrUndefined(payload.keepVersions)

  // --- design_spec integration: warn when intent is missing or went stale ----
  // Prior state is captured BEFORE the write so "did this push change the
  // geometry without updating the spec?" compares against the version being
  // overwritten. The effective spec for the new state is the pushed text or,
  // when none was pushed, whatever the version already resolved to.
  const baselineVersion = resolveBranchDefaultVersion(priorMeta, branch)
  const priorSceneBody = await readCacheVersionSceneBody(branchDir, baselineVersion)
  const priorSpecText = await readCacheSpecText(branchDir, baselineVersion)

  const written = await writeCacheLayout(
    buildId,
    version,
    normalized,
    designSpecText,
    name,
    setDefault,
    keepVersions,
    message,
    branch,
    reason,
  )
  // Promote AFTER the write so the pushed content participates in the swap.
  if (setDefaultBranch && written.branch !== written.defaultBranch) {
    await promoteBranchToDefault(buildId, written.branch)
    written.defaultBranch = written.branch
    written.branchDir = written.cacheDir
  }
  const designSpecPath = existsSync(path.join(written.cacheDir, 'design_spec.yaml'))
    ? path.join(written.cacheDir, 'design_spec.yaml')
    : null
  const registration: HubBuildRegistration = {
    id: buildId,
    name,
    buildDir: written.cacheDir,
    designSpecPath,
    registeredAt: new Date().toISOString(),
    source: 'push',
  }
  const priorRegistry = await readRegistry()
  const existingRegistration = priorRegistry.builds.find((entry) => entry.id === buildId)
  const registry = written.unchanged && existingRegistration
    ? priorRegistry : await upsertRegistration(registration)

  const addressContext =
    written.branch === written.defaultBranch
      ? `${buildId}@${written.version}`
      : `${buildId}@${written.branch}@${written.version}`
  const effectiveSpecText = await readCacheSpecText(written.branchDir, version)
  const warnings = specWarningsFromCoverage(specCoverage(normalized, effectiveSpecText), addressContext)
  if (!written.reason && !written.unchanged) {
    warnings.push('Missing version reason: explain WHY this revision is needed with --reason "<problem/user request; intended improvement; tradeoffs>" (API: reason). If fixing an earlier version, record its issue with feedback; a change summary alone loses the learning history.')
  }
  if (written.unchanged) {
    warnings.push('Identical retry: published geometry, design spec, original message and timestamp were preserved.')
  }
  if (payload.noSnapshot === true) {
    warnings.push('noSnapshot is obsolete for push and cannot disable published-version protection. Use a new version for changes.')
  }
  if (normalized.meshes.some((mesh) => mesh.url && !/^\/builds\/_assets\/[a-f0-9]{64}\./.test(mesh.url))) {
    warnings.push('Some mesh URLs are not content-addressed snapshots. Use --upload-assets with local relative mesh files to preserve geometry bytes; external/mutable URLs can change independently of this version.')
  }
  // Same serialization writeCacheLayout persists, so this equality check sees
  // exactly the bytes a re-push would overwrite.
  const newSceneBody = `${JSON.stringify(normalized, null, 2)}\n`
  const geometryChangedWithoutSpec =
    !written.unchanged && priorSceneBody !== null && priorSceneBody !== newSceneBody && effectiveSpecText === priorSpecText
  if (geometryChangedWithoutSpec) {
    warnings.push(
      'Geometry changed but design_spec.yaml was not updated — the --message records why, but confirm the ' +
        "spec's rationale/dimensions still describe the new geometry.",
    )
  }

  return {
    registration: written.unchanged && existingRegistration ? existingRegistration : registration,
    written,
    registry,
    warnings,
    nextSteps: VERSION_LEARNING_GUIDANCE,
    uploads: {
      count: uploads.uploaded.length,
      totalBytes: uploads.totalBytes,
      dedupedBytes: uploads.dedupedBytes,
      assets: uploads.uploaded,
    },
    url: hubViewUrl(
      baseUrl,
      buildId,
      written.version,
      { branch: written.branch === written.defaultBranch ? undefined : written.branch },
    ),
  }
}

// --- named analyses ---------------------------------------------------------
// An analysis is a NAMED derived scene attached to a build (stress fields,
// thermal maps, ...) rather than a standalone build: it lives in the build's
// dir under analyses/<slug>/ and shows up as a page on the build in the
// viewer, so result overlays never pollute the builds index.

type PushAnalysisPayload = {
  buildId?: unknown
  /** Immutable page slug; changed results require a new name. */
  name?: unknown
  displayName?: unknown
  message?: unknown
  /** The build version/branch the analysis was computed FROM (labels only). */
  sourceVersion?: unknown
  sourceBranch?: unknown
  scene?: unknown
  assetsBaseUrl?: unknown
  assets?: unknown
  maxUploadBytes?: unknown
}

type AnalysisMeta = {
  name: string
  displayName?: string
  message?: string
  sourceVersion?: string
  sourceBranch?: string
  createdAt: string
  updatedAt: string
}

const analysesDirFor = (buildDir: string) => path.join(buildDir, 'analyses')

const listAnalyses = async (buildDir: string): Promise<AnalysisMeta[]> => {
  const root = analysesDirFor(buildDir)
  if (!existsSync(root)) return []
  const entries = await readdir(root, { withFileTypes: true })
  const analyses: AnalysisMeta[] = []
  for (const entry of entries) {
    if (!entry.isDirectory()) continue
    if (!existsSync(path.join(root, entry.name, 'scene.json'))) continue
    const meta = await readJson<AnalysisMeta>(path.join(root, entry.name, 'meta.json')).catch(() => null)
    analyses.push({ ...(meta ?? { createdAt: '', updatedAt: '' }), name: entry.name })
  }
  return analyses.sort((a, b) => (b.updatedAt || '').localeCompare(a.updatedAt || ''))
}

export const pushAnalysisFromPayload = (
  payload: PushAnalysisPayload,
  registry: HubRegistry,
  baseUrl: string,
) => publishSerially(() => publishAnalysis(payload, registry, baseUrl))

const publishAnalysis = async (
  payload: PushAnalysisPayload,
  registry: HubRegistry,
  baseUrl: string,
) => {
  const rawBuildId = typeof payload.buildId === 'string' ? payload.buildId.trim() : ''
  if (!rawBuildId) throw new Error('push-analysis requires a "buildId"')
  const buildId = canonicalizeBuildId(rawBuildId)
  assertValidBuildId(buildId)
  const build = registry.builds.find((entry) => entry.id === buildId)
  if (!build) {
    throw new Error(`Build "${buildId}" is not on this hub — push the build first, then attach analyses.`)
  }

  const rawName = typeof payload.name === 'string' ? payload.name.trim() : ''
  const slug = rawName ? canonicalizeVersionName(rawName) : ''
  if (!slug) throw new Error('push-analysis requires a "name" (the analysis page slug).')

  const scene = assertSceneManifest(payload.scene)
  const assetsBaseUrl =
    typeof payload.assetsBaseUrl === 'string' && payload.assetsBaseUrl.length > 0
      ? payload.assetsBaseUrl
      : undefined
  // Same asset pipeline as push: uploaded bytes land content-hashed in the
  // shared store, so an analysis is always self-contained on the hub.
  const uploads = await storePushAssets(payload as PushPayload)
  const baseNormalized = normalizeSceneAssets(scene, assetsBaseUrl)
  const normalized = {
    ...baseNormalized,
    meshes: baseNormalized.meshes.map((mesh) => {
      const url = uploads.urlByMeshId.get(mesh.id)
      return url ? { ...mesh, url } : mesh
    }),
  }

  const dir = path.join(analysesDirFor(build.buildDir), slug)
  const priorMeta = await readJson<AnalysisMeta>(path.join(dir, 'meta.json')).catch(() => null)
  const now = new Date().toISOString()
  const meta: AnalysisMeta = {
    name: slug,
    displayName:
      (typeof payload.displayName === 'string' && payload.displayName.trim()) || normalized.name || slug,
    message: normalizeVersionMessage(payload.message) ?? undefined,
    sourceVersion: typeof payload.sourceVersion === 'string' && payload.sourceVersion ? payload.sourceVersion : undefined,
    sourceBranch: typeof payload.sourceBranch === 'string' && payload.sourceBranch ? payload.sourceBranch : undefined,
    createdAt: priorMeta?.createdAt || now,
    updatedAt: now,
  }
  const priorScene = existsSync(path.join(dir, 'scene.json'))
    ? await readFile(path.join(dir, 'scene.json'), 'utf8') : null
  const unchanged = priorScene !== null
  if (unchanged && (!sameScene(priorScene, normalized) ||
    priorMeta?.sourceVersion !== meta.sourceVersion || priorMeta?.sourceBranch !== meta.sourceBranch)) {
    throw new AnalysisConflictError(buildId, slug)
  }
  if (!unchanged) {
    await mkdir(dir, { recursive: true })
    await writeFile(path.join(dir, 'scene.json'), `${JSON.stringify(normalized, null, 2)}\n`)
    await writeFile(path.join(dir, 'meta.json'), `${JSON.stringify(meta, null, 2)}\n`)
  }

  return {
    buildId,
    analysis: unchanged ? priorMeta ?? meta : meta,
    isNew: !unchanged,
    unchanged,
    uploads: {
      count: uploads.uploaded.length,
      totalBytes: uploads.totalBytes,
      dedupedBytes: uploads.dedupedBytes,
      assets: uploads.uploaded,
    },
    url: hubViewUrl(baseUrl, buildId, meta.sourceVersion ?? null, { analysis: slug, branch: meta.sourceBranch }),
  }
}

type PackExportPayload = {
  buildId?: unknown
  branch?: unknown
  version?: unknown
  printer?: unknown
  bed?: unknown
  assembly?: unknown
  format?: unknown
  angle?: unknown
  spacing?: unknown
  margin?: unknown
}

const numberOrUndefined = (value: unknown): number | undefined => {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string' && value.trim().length > 0) {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) return parsed
  }
  return undefined
}

// Run pack + plate export server-side for a build the hub knows about, writing
// one Bambu-ingestible file per plate (3MF default, STL fallback) under the
// build's plates/ dir, and returning the absolute output paths. This is the
// filesystem-backed counterpart to the viewer's "Export plates" button, which
// cannot write files itself.
const packExportFromPayload = async (payload: PackExportPayload, registry: HubRegistry) => {
  const rawBuildId = typeof payload.buildId === 'string' ? payload.buildId.trim() : ''
  if (!rawBuildId) throw new Error('pack-export requires a "buildId"')
  const buildId = canonicalizeBuildId(rawBuildId)
  const build = registry.builds.find((entry) => entry.id === buildId)
  if (!build) {
    throw new Error(`No registered build "${buildId}" on this hub. Register or push it first.`)
  }

  const meta = await readBuildMeta(build.buildDir)
  const defaultBranch = resolveDefaultBranch(meta)
  const branch =
    typeof payload.branch === 'string' && payload.branch.trim().length > 0
      ? canonicalizeBranchName(payload.branch)
      : defaultBranch
  const defaultVersion = resolveBranchDefaultVersion(meta, branch)
  const requested =
    typeof payload.version === 'string' && payload.version.trim().length > 0
      ? canonicalizeVersionName(payload.version)
      : defaultVersion
  const version = requested || defaultVersion
  const resolved = await resolveVersionScene(build.buildDir, version, branch)
  if (!resolved) {
    throw new Error(
      branch === defaultBranch
        ? `No version "${version}" for build ${buildId}.`
        : `No version "${version}" on branch "${branch}" for build ${buildId}.`,
    )
  }
  const manifest = await readJson<BuildSceneManifest>(resolved.scenePath)

  // Resolve printer/bed exactly like the CLI: a custom bed wins, else a named
  // printer (default X1C).
  const bedOpt = typeof payload.bed === 'string' ? payload.bed : undefined
  const printerOpt = typeof payload.printer === 'string' ? payload.printer : undefined
  const bed = bedOpt ? parseBed(bedOpt) : resolvePrinter(printerOpt).bed
  const printerId = bedOpt ? null : resolvePrinter(printerOpt).id

  const formatOpt = (typeof payload.format === 'string' ? payload.format : '3mf').toLowerCase()
  if (formatOpt !== '3mf' && formatOpt !== 'stl') {
    throw new Error(`Unknown format "${formatOpt}". Use 3mf or stl.`)
  }
  const format = formatOpt as ExportFormat
  const assembly = typeof payload.assembly === 'string' && payload.assembly.trim().length > 0
    ? payload.assembly.trim()
    : undefined

  // Mesh urls in a stored scene are absolute (/builds/<folder>/stl/foo.stl) or
  // relative; the "<folder>" segment may be the original on-disk dir name rather
  // than the hub's hierarchical build id, so map back to files under the build
  // directory (never outside it) by stripping a leading "/builds/" and then
  // dropping leading path segments until a file resolves under buildDir.
  const resolveMeshPath = (url: string | undefined) => {
    if (!url || isAbsoluteWebUrl(url)) return null
    let rest = url.replace(/^\.?\//, '')
    if (rest.startsWith('builds/')) rest = rest.slice('builds/'.length)
    const segments = rest.split('/').filter(Boolean)
    for (let drop = 0; drop < segments.length; drop += 1) {
      const candidate = safePathInside(build.buildDir, segments.slice(drop).join('/'))
      if (candidate && existsSync(candidate)) return candidate
    }
    return null
  }

  const { result, meshData, skipped } = await runPack(manifest, {
    loadMesh: async (mesh) => {
      const filePath = resolveMeshPath(mesh.url)
      if (!filePath || !existsSync(filePath)) return null
      const buffer = await readFile(filePath)
      return buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength) as ArrayBuffer
    },
    bed,
    printerId,
    assembly,
    supportAngleDeg: numberOrUndefined(payload.angle),
    spacingMm: numberOrUndefined(payload.spacing),
    marginMm: numberOrUndefined(payload.margin),
  })

  const outDir = path.join(build.buildDir, 'plates')
  const exported = await exportPlateFiles({ result, meshData, bed, format, outDir })

  // Also (re)emit the viewer-renderable layout scene next to the resolved
  // scene.json — the SAME buildviz_pack.json the CLI's `pack --emit` writes —
  // so the panel's "Show in viewer" button can load the packed plate layout
  // through the viewer's ?scene= override. Mesh urls are reused verbatim from
  // the source build, so the hub that serves this file also serves the meshes.
  const packScene = buildPackedScene(result, manifest.name, manifest.meshes)
  const packScenePath = path.join(resolved.base, 'buildviz_pack.json')
  await writeFile(packScenePath, `${JSON.stringify(packScene, null, 2)}\n`, 'utf8')
  const branchPrefix = branch === defaultBranch ? '' : `/branches/${encodeURIComponent(branch)}`
  const viewerScene = resolved.versioned
    ? `/builds/${buildId}${branchPrefix}/versions/${version}/buildviz_pack.json`
    : `/builds/${buildId}${branchPrefix}/buildviz_pack.json`
  const viewerParams = new URLSearchParams()
  const { project, build: buildName } = splitProjectBuild(buildId)
  viewerParams.set('project', project)
  viewerParams.set('build', buildName)
  if (branch !== defaultBranch) viewerParams.set('branch', branch)
  if (resolved.versioned) viewerParams.set('version', version)
  viewerParams.set('scene', viewerScene)
  const viewerUrl = `?${viewerParams.toString()}`

  return {
    buildId,
    branch,
    version,
    assembly: assembly ?? null,
    printer: printerId,
    bed,
    format: exported.format,
    plateCount: exported.plateCount,
    partCount: result.totals.partCount,
    skipped,
    outDir: exported.outDir,
    files: exported.files,
    viewerScene,
    viewerUrl,
  }
}

// --- Reveal a folder in the OS file manager (POST /__buildviz/open-path) ------
// The viewer's "Open folder" button asks the hub to reveal an export directory
// locally. This crosses from the browser to a native shell action, so it is
// sandboxed hard:
//   * The requested path must resolve (via realpath, so symlinks are followed)
//     to a real DIRECTORY.
//   * That real path must sit INSIDE an allowed root — the project root,
//     ~/.buildviz, or a registered build's own directory (which is where
//     plates/ is written). Roots are themselves realpath'd so a symlinked root
//     (e.g. macOS /var -> /private/var) still matches.
//   * The file manager is launched with execFile (NO shell), passing the
//     validated directory as a single argument array element, so nothing the
//     caller sends is ever interpreted by a shell.
const fileManagerCommand = (): string | null => {
  switch (process.platform) {
    case 'darwin':
      return 'open'
    case 'win32':
      return 'explorer'
    case 'linux':
      return 'xdg-open'
    default:
      return null
  }
}

const openInFileManager = (dir: string) =>
  new Promise<void>((resolve, reject) => {
    const command = fileManagerCommand()
    if (!command) {
      reject(new Error(`Opening a folder is not supported on platform "${process.platform}".`))
      return
    }
    // No shell: the directory is a single argv element, never a shell string.
    execFile(command, [dir], (error) => {
      // Windows explorer.exe exits non-zero even on success; only treat a real
      // spawn/launch failure (or a non-zero exit elsewhere) as an error.
      if (error && process.platform !== 'win32') {
        reject(error)
        return
      }
      resolve()
    })
  })

// The set of directory roots the open-path endpoint will reveal, realpath'd so
// prefix checks are done against canonical (symlink-free) paths.
const openPathAllowedRoots = async (registry: HubRegistry): Promise<string[]> => {
  const candidates = new Set<string>([projectRoot, buildvizHome, ...registry.builds.map((b) => b.buildDir)])
  const resolved: string[] = []
  for (const candidate of candidates) {
    try {
      resolved.push(await realpath(candidate))
    } catch {
      // A root that does not exist on disk simply contributes no prefix.
    }
  }
  return resolved
}

// Validate a caller-supplied path for the open-path endpoint, returning the
// canonical directory to open or throwing a clear error. Rejects anything that
// is missing, not a directory, or (after resolving symlinks) escapes the
// allowed roots.
const resolveOpenablePath = async (rawPath: unknown, registry: HubRegistry): Promise<string> => {
  if (typeof rawPath !== 'string' || rawPath.trim().length === 0) {
    throw new Error('open-path requires a "path" string.')
  }
  const requested = path.resolve(rawPath)
  let resolvedPath: string
  try {
    resolvedPath = await realpath(requested)
  } catch {
    throw new Error(`Path does not exist: ${requested}`)
  }
  const info = await stat(resolvedPath)
  if (!info.isDirectory()) {
    throw new Error(`Not a directory: ${resolvedPath}`)
  }
  const roots = await openPathAllowedRoots(registry)
  const inside = roots.some(
    (root) => resolvedPath === root || resolvedPath.startsWith(`${root}${path.sep}`),
  )
  if (!inside) {
    throw new Error(
      `Refusing to open "${resolvedPath}": it is outside the allowed roots ` +
        '(the project directory, ~/.buildviz, or a registered build directory).',
    )
  }
  return resolvedPath
}

// --- Locate a build's STL directory (GET /__buildviz/stl-dir) ----------------
// Every assembly in the viewer offers an "Open STL folder" link when the STLs
// can be found on this host's disk. Given a build (plus optional branch and
// version), read the scene manifest the hub would serve for that selection and
// map each mesh's .stl URL back to the file it is served from:
//   * /builds/_assets/<file>   -> the shared content-addressed store (pushed builds)
//   * /builds/<build id>/<rel> -> inside that registered build's directory
//   * a relative path          -> relative to the scene.json's own directory
// The answer is the directory holding the most referenced on-disk STL files,
// or null when none resolve (the viewer then simply shows no link).
const resolveStlDir = async (
  registry: HubRegistry,
  buildId: string,
  version: string | null,
  branch: string | null,
): Promise<{ path: string; fileCount: number } | null> => {
  const id = canonicalizeBuildId(buildId)
  const entry = registry.builds.find((build) => build.id === id)
  if (!entry) {
    throw new Error(
      `No build "${buildId}" on this hub. Known: ${registry.builds.map((build) => build.id).join(', ')}`,
    )
  }

  // Resolve which scene.json the selection refers to (same rules as serving).
  let scenePath: string
  if (version) {
    const resolved = await resolveVersionScene(entry.buildDir, version, branch)
    if (!resolved) return null
    scenePath = resolved.scenePath
  } else if (branch) {
    const meta = await readBuildMeta(entry.buildDir)
    scenePath = path.join(branchRootDir(entry.buildDir, branch, resolveDefaultBranch(meta)), 'scene.json')
  } else {
    scenePath = path.join(entry.buildDir, 'scene.json')
  }
  if (!existsSync(scenePath)) return null

  let manifest: BuildSceneManifest
  try {
    manifest = await readJson<BuildSceneManifest>(scenePath)
  } catch {
    return null
  }

  const sceneDir = path.dirname(scenePath)
  const counts = new Map<string, number>()
  for (const mesh of manifest.meshes ?? []) {
    const url = mesh.url
    if (!url || !/\.stl$/i.test(url) || isAbsoluteWebUrl(url)) continue
    let filePath: string | null = null
    if (url.startsWith('/builds/')) {
      const rest = decodeURIComponent(url.slice('/builds/'.length))
      if (rest.startsWith(`${ASSET_STORE_ID}/`)) {
        filePath = safePathInside(assetStoreDir, rest.slice(`${ASSET_STORE_ID}/`.length))
      } else {
        const matched = resolveBuildAssetRequest(registry, rest)
        if (matched) filePath = safePathInside(matched.build.buildDir, matched.relative)
      }
    } else if (!url.startsWith('/')) {
      // A raw on-disk manifest may reference meshes relative to its scene.json.
      filePath = path.resolve(sceneDir, url)
    }
    if (!filePath || !existsSync(filePath)) continue
    const dir = path.dirname(filePath)
    counts.set(dir, (counts.get(dir) ?? 0) + 1)
  }

  let best: { path: string; fileCount: number } | null = null
  for (const [dir, fileCount] of counts) {
    if (!best || fileCount > best.fileCount) best = { path: dir, fileCount }
  }
  return best
}

// Walk the cache tree to find every cache-managed build. A build id can be a
// hierarchy (e.g. prototype_v1/chassis), so builds may nest several directories
// deep. A directory is a build when it has a scene.json or any versions/v<N>
// snapshot; we recurse into other subdirectories (but never into versions/) so
// intermediate group directories can themselves hold child builds.
const findCacheBuilds = async (): Promise<string[]> => {
  if (!existsSync(cacheRoot)) return []
  const found: string[] = []

  const visit = async (dir: string, idPrefix: string) => {
    if (idPrefix) {
      const hasScene = existsSync(path.join(dir, 'scene.json'))
      const versions = await cacheVersionNames(idPrefix)
      if (hasScene || versions.length > 0) found.push(idPrefix)
    }

    const entries = await readdir(dir, { withFileTypes: true })
    await Promise.all(
      entries.map(async (entry) => {
        // Skip "versions" snapshots, per-build "branches" containers, attached
        // "analyses" pages, and the top-level content-addressed asset store
        // ("_assets") — none are builds.
        if (!entry.isDirectory() || entry.name === 'versions' || entry.name === 'branches') return
        if (entry.name === 'analyses') return
        if (!idPrefix && entry.name === ASSET_STORE_ID) return
        const childId = idPrefix ? `${idPrefix}/${entry.name}` : entry.name
        await visit(path.join(dir, entry.name), childId)
      }),
    )
  }

  await visit(cacheRoot, '')
  return found
}

const restoreCacheBuilds = async (registry: HubRegistry): Promise<HubRegistry> => {
  const cacheBuildIds = await findCacheBuilds()
  const byId = new Map(registry.builds.map((build) => [build.id, build]))
  let changed = false

  for (const buildId of cacheBuildIds) {
    if (byId.has(buildId)) continue

    const dir = cacheBuildDir(buildId)
    const scenePath = path.join(dir, 'scene.json')
    const meta = await readCacheMeta(buildId)
    const designSpecPath = existsSync(path.join(dir, 'design_spec.yaml'))
      ? path.join(dir, 'design_spec.yaml')
      : null
    const name = meta?.name ?? (existsSync(scenePath) ? await readSceneName(scenePath) : null) ?? buildId
    byId.set(buildId, {
      id: buildId,
      name,
      buildDir: dir,
      designSpecPath,
      registeredAt: meta?.updatedAt ?? new Date().toISOString(),
      source: 'push',
    })
    changed = true
  }

  if (!changed) return registry
  const builds = [...byId.values()].sort((a, b) => a.id.localeCompare(b.id))
  const merged = { builds }
  await writeRegistry(merged)
  return merged
}

// Drop registry entries whose source directory no longer exists so a restarted
// hub serves a consistent set instead of advertising builds whose scene.json
// would 404. restoreCacheBuilds (run first) re-adds cache-backed builds that DO
// exist on disk; this prunes the remainder:
//   - directory-registered builds (e.g. `register`/`send`) whose buildDir was
//     moved or deleted, and
//   - cache/push builds whose cache dir was wiped.
// Each pruned entry is logged with a clear warning and removed from registry.json
// (rather than crashing or silently producing an inconsistent index). A pruned
// build can always be re-registered/re-pushed later.
const pruneDeadBuilds = async (registry: HubRegistry): Promise<HubRegistry> => {
  const alive: HubBuildRegistration[] = []
  const dead: HubBuildRegistration[] = []
  for (const build of registry.builds) {
    if (existsSync(build.buildDir)) alive.push(build)
    else dead.push(build)
  }
  if (dead.length === 0) return registry
  for (const build of dead) {
    console.warn(
      `Warning: pruning build "${build.id}" — its source directory no longer exists (${build.buildDir}). ` +
        'Removed from the registry; re-register or re-push to restore it.',
    )
  }
  const merged = { builds: alive }
  await writeRegistry(merged)
  return merged
}

const sendLocalManifest = async (
  response: ServerResponse,
  scenePath: string,
  publicBase: string,
  designSpecUrl: string,
) => {
  try {
    const manifest = await readJson<BuildSceneManifest>(scenePath)
    const rewritten: BuildSceneManifest = {
      ...manifest,
      designSpecUrl,
      meshes: manifest.meshes.map((mesh) => ({
        ...mesh,
        url: rewriteLocalMeshUrl(mesh.url, publicBase),
      })),
    }
    sendJson(response, rewritten)
  } catch (error) {
    response.statusCode = 500
    response.end(error instanceof Error ? error.message : String(error))
  }
}

// Resolve a requested named version to a scene.json on disk. A non-default
// version is served from versions/<name>/; the DEFAULT version is served from
// the build root scene.json (where it is mirrored), so a URL like
// /builds/<id>/versions/main/scene.json still resolves even when no
// versions/main directory was materialized (e.g. a migrated on-disk build).
const resolveVersionScene = async (buildDir: string, version: string, branch?: string | null) => {
  const meta = await readBuildMeta(buildDir)
  const defaultBranch = resolveDefaultBranch(meta)
  const branchName = branch && branch.length > 0 ? branch : defaultBranch
  const base = branchRootDir(buildDir, branchName, defaultBranch)
  const versionDir = path.join(base, 'versions', version)
  if (existsSync(path.join(versionDir, 'scene.json'))) {
    return { scenePath: path.join(versionDir, 'scene.json'), base: versionDir, versioned: true }
  }
  if (
    version === resolveBranchDefaultVersion(meta, branchName) &&
    existsSync(path.join(base, 'scene.json'))
  ) {
    return { scenePath: path.join(base, 'scene.json'), base, versioned: false }
  }
  return null
}

const safePathInside = (root: string, relativePath: string) => {
  const decoded = decodeURIComponent(relativePath).replace(/^\/+/, '')
  const resolved = path.resolve(root, decoded)
  if (resolved !== root && !resolved.startsWith(`${root}${path.sep}`)) {
    return null
  }
  return resolved
}

const serveLocalAsset = async (
  request: IncomingMessage,
  response: ServerResponse,
  buildDir: string,
  designSpecPath: string | null,
) => {
  const requestUrl = request.url ? new URL(request.url, 'http://127.0.0.1') : null
  const pathname = requestUrl?.pathname ?? '/'

  if (pathname.startsWith('/__buildviz')) {
    response.statusCode = 404
    response.end('Not found')
    return true
  }

  if (pathname === '/builds/index.json') {
    const entry = await buildIndexEntryFor('local', buildDir, null)
    sendJsonWithEtag(request, response, buildsIndexFrom([entry]))
    return true
  }

  const buildMatch = pathname.match(/^\/builds\/local\/(.+)$/)
  if (buildMatch) {
    if (buildMatch[1] === 'scene.json') {
      await sendLocalManifest(
        response,
        path.join(buildDir, 'scene.json'),
        '/builds/local',
        '/builds/local/design_spec.yaml',
      )
      return true
    }

    if (buildMatch[1] === 'design_spec.yaml') {
      await sendFile(response, designSpecPath)
      return true
    }

    if (buildMatch[1] === 'analyses.json') {
      sendJson(response, { buildId: 'local', analyses: await listAnalyses(buildDir) })
      return true
    }
    const localAnalysisMatch = buildMatch[1].match(/^analyses\/([^/]+)\/scene\.json$/)
    if (localAnalysisMatch) {
      const analysisPath = path.join(analysesDirFor(buildDir), localAnalysisMatch[1], 'scene.json')
      if (!existsSync(analysisPath)) {
        response.statusCode = 404
        response.end('Not found')
        return true
      }
      await sendLocalManifest(
        response,
        analysisPath,
        `/builds/local/analyses/${encodeURIComponent(localAnalysisMatch[1])}`,
        '/builds/local/design_spec.yaml',
      )
      return true
    }

    // Branch-scoped manifests for the single-build local viewer (same layout
    // as the hub: branches/<b>/scene.json and branches/<b>/versions/<v>/...).
    const branchMatch = buildMatch[1].match(/^branches\/([^/]+)\/(scene\.json|versions\/([^/]+)\/scene\.json)$/)
    if (branchMatch) {
      const branchName = branchMatch[1]
      const branchBase = `/builds/local/branches/${encodeURIComponent(branchName)}`
      const localMeta = await readBuildMeta(buildDir)
      const branchDir = branchRootDir(buildDir, branchName, resolveDefaultBranch(localMeta))
      if (!existsSync(branchDir)) {
        response.statusCode = 404
        response.end('Not found')
        return true
      }
      if (branchMatch[2] === 'scene.json') {
        await sendLocalManifest(
          response,
          path.join(branchDir, 'scene.json'),
          branchBase,
          '/builds/local/design_spec.yaml',
        )
        return true
      }
      const versionName = branchMatch[3]
      const resolved = await resolveVersionScene(buildDir, versionName, branchName)
      if (!resolved) {
        response.statusCode = 404
        response.end('Not found')
        return true
      }
      await sendLocalManifest(
        response,
        resolved.scenePath,
        resolved.versioned ? `${branchBase}/versions/${encodeURIComponent(versionName)}` : branchBase,
        '/builds/local/design_spec.yaml',
      )
      return true
    }

    const versionMatch = buildMatch[1].match(/^versions\/([^/]+)\/scene\.json$/)
    if (versionMatch) {
      const version = versionMatch[1]
      const resolved = await resolveVersionScene(buildDir, version)
      if (!resolved) {
        response.statusCode = 404
        response.end('Not found')
        return true
      }
      const designSpecUrl = existsSync(path.join(resolved.base, 'design_spec.yaml'))
        ? (resolved.versioned ? `/builds/local/versions/${version}/design_spec.yaml` : '/builds/local/design_spec.yaml')
        : '/builds/local/design_spec.yaml'
      await sendLocalManifest(
        response,
        resolved.scenePath,
        resolved.versioned ? `/builds/local/versions/${version}` : '/builds/local',
        designSpecUrl,
      )
      return true
    }

    const filePath = safePathInside(buildDir, buildMatch[1])
    if (!filePath) {
      response.statusCode = 403
      response.end('Forbidden')
      return true
    }
    await sendFile(response, filePath)
    return true
  }

  return false
}

// Mutation / host-action endpoints that are DISABLED when the hub is bound to a
// non-loopback address (read-only remote view). These either write to disk
// (push, pack-export) or run a native shell action on the host (open-path runs
// `open`), so they must never be reachable from another machine. View/read
// endpoints (the app, /builds/..., GET status/builds) stay available.
const READ_ONLY_BLOCKED_MESSAGE =
  'This BuildViz hub is bound to a non-loopback address and runs READ-ONLY: ' +
  'push, pack-export, register, and open-path are disabled. Run the hub on ' +
  'loopback (127.0.0.1) to use mutation/host-action endpoints.'

// --- API key auth -----------------------------------------------------------
// When the hub is started with an API key (--api-key or BUILDVIZ_API_KEY), the
// mutation/host-action endpoints and the MCP endpoint require it. Viewing (the
// app, /builds/..., GET status/builds) stays open. The key is accepted as
// `Authorization: Bearer <key>`, an `X-API-Key` header, or a `?key=` query
// parameter, and compared in constant time.
export const resolveHubApiKey = (options: CliOptions): string | undefined =>
  optionString(options, 'api-key', 'apiKey') ?? (process.env.BUILDVIZ_API_KEY || undefined)

const requestHasApiKey = (
  request: IncomingMessage,
  requestUrl: URL | null,
  apiKey: string,
): boolean => {
  const authorization = request.headers.authorization
  const bearer = authorization?.toLowerCase().startsWith('bearer ')
    ? authorization.slice(7).trim()
    : undefined
  const headerKey = request.headers['x-api-key']
  const candidate =
    bearer ??
    (typeof headerKey === 'string' ? headerKey : undefined) ??
    requestUrl?.searchParams.get('key') ??
    ''
  const candidateDigest = createHash('sha256').update(candidate).digest()
  const keyDigest = createHash('sha256').update(apiKey).digest()
  return timingSafeEqual(candidateDigest, keyDigest)
}

const API_KEY_BLOCKED_MESSAGE =
  'This BuildViz hub requires an API key for this endpoint. Send it as ' +
  '`Authorization: Bearer <key>`, an `X-API-Key` header, or a `?key=` query parameter.'

export const serveHubAsset = async (
  request: IncomingMessage,
  response: ServerResponse,
  getRegistry: () => HubRegistry,
  baseUrl: string,
  startedAt: string,
  readOnly: boolean,
  apiKey?: string,
  catalogFile?: string,
) => {
  const requestUrl = request.url ? new URL(request.url, 'http://127.0.0.1') : null
  const pathname = requestUrl?.pathname ?? '/'

  const isMutationPath =
    (pathname === '/__buildviz/feedback' && request.method !== 'GET') ||
    (pathname === '/__buildviz/catalog' && request.method !== 'GET') ||
    (pathname === '/__buildviz/workflows' && request.method !== 'GET') ||
    pathname === '/__buildviz/revisions/metadata' ||
    pathname === '/__buildviz/push' ||
    pathname === '/__buildviz/push-analysis' ||
    pathname === '/__buildviz/pack-export' ||
    pathname === '/__buildviz/open-path' ||
    // stl-dir is a read, but it reveals host filesystem paths and exists only
    // to power the native open-path action, so it is gated the same way.
    pathname === '/__buildviz/stl-dir' ||
    pathname === '/__buildviz/register'

  // Hard gate: when read-only, reject every mutation / host-action endpoint
  // BEFORE any handler runs, regardless of method, so a non-loopback client can
  // never push, export, register, or trigger the native open-path shell action.
  if (readOnly && isMutationPath) {
    sendJsonError(response, 403, READ_ONLY_BLOCKED_MESSAGE)
    return true
  }

  // API key gate: with a key configured, mutations and the MCP endpoint
  // require it (viewing stays open).
  if (apiKey && (isMutationPath || pathname === '/mcp') && !requestHasApiKey(request, requestUrl, apiKey)) {
    sendJsonError(response, 401, API_KEY_BLOCKED_MESSAGE)
    return true
  }

  if (pathname === '/mcp') {
    return serveMcp(request, response, {
      getBuilds: () => getRegistry().builds,
      serverVersion: packageVersion,
      readOnly,
      catalogPath: catalogFile,
      assetStoreDir,
      publishRevision: async (payload) => {
        const result = await pushLayoutFromPayload(payload, baseUrl)
        getRegistry().builds = result.registry.builds
        await ensurePartHistory(result.written.cacheDir, result.registration.id, result.written.branch).catch(() => undefined)
        return {
          ok: true, buildId: result.registration.id, branch: result.written.branch,
          version: result.written.version, message: result.written.message,
          reason: result.written.reason, nextSteps: result.nextSteps,
          warnings: result.warnings, url: result.url,
        }
      },
    })
  }

  if (pathname === '/__buildviz/feedback') {
    const ctx = { getBuilds: () => getRegistry().builds, readOnly }
    try {
      if (request.method === 'GET') {
        const args = Object.fromEntries(requestUrl!.searchParams)
        sendJsonWithEtag(request, response, await readVersionFeedback(ctx, args))
      } else if (request.method === 'POST') {
        const result = await recordVersionFeedback(ctx, await readRequestJson<Record<string, unknown>>(request, 32 * 1024))
        sendJson(response, { ok: true, ...result })
      } else {
        sendJsonError(response, 405, 'Use GET to read or POST to append version feedback.')
      }
    } catch (error) {
      sendJsonError(response, 400, error instanceof Error ? error.message : String(error))
    }
    return true
  }

  if (pathname === '/__buildviz/workflows' && request.method === 'POST') {
    try {
      const payload = await readRequestJson<Parameters<typeof setBuildWorkflowMetadata>[1]>(request)
      sendJson(response, await setBuildWorkflowMetadata({ getBuilds: () => getRegistry().builds }, payload))
    } catch (error) { sendJsonError(response, 400, error instanceof Error ? error.message : String(error)) }
    return true
  }
  if ((pathname === '/__buildviz/workflows' || pathname.startsWith('/__buildviz/workflows/')) && request.method === 'GET') {
    const params = requestUrl!.searchParams
    const query: WorkflowQuery = { build: params.get('build') ?? '',
      ...Object.fromEntries(['branch', 'version', 'compare', 'catalog'].flatMap((key) => params.has(key) ? [[key, params.get(key)!]] : [])) }
    const deps = { getBuilds: () => getRegistry().builds, catalogPath: catalogFile, assetStoreDir }
    try {
      if (pathname === '/__buildviz/workflows') sendJsonWithEtag(request, response, await readBuildWorkflows(deps, query))
      else {
        const action = pathname.slice('/__buildviz/workflows/'.length)
        const download = action === 'download' ? await downloadBuildWorkflows(deps, query, (params.get('selection') ?? 'all') as 'all' | 'changed')
          : action === 'plate' ? await downloadWorkflowPlate(deps, query, (params.get('selection') ?? 'all') as 'all' | 'changed', params.get('printer') ?? 'x1c')
          : action === 'file' ? await downloadWorkflowFile(deps, query, params.get('file') ?? '')
            : action === 'quantities' ? await downloadWorkflowQuantities(deps, query) : null
        if (!download) sendJsonError(response, 404, 'Unknown workflow download')
        else {
          response.setHeader('Content-Type', 'contentType' in download ? String(download.contentType) : action === 'download' ? 'application/zip' : action === 'quantities' ? 'text/csv; charset=utf-8' : 'model/stl')
          response.setHeader('Content-Disposition', `attachment; filename="${download.fileName}"`)
          response.setHeader('Content-Length', download.bytes.length)
          response.setHeader('Cache-Control', 'no-store')
          response.setHeader('X-Content-Type-Options', 'nosniff')
          response.end(download.bytes)
        }
      }
    } catch (error) {
      const message = (error as NodeJS.ErrnoException).code ? 'Workflow source or metadata file is unavailable.' : error instanceof Error ? error.message : String(error)
      sendJsonError(response, 400, message)
    }
    return true
  }

  if (pathname === '/__buildviz/catalog' && request.method === 'GET') {
    try { sendJsonWithEtag(request, response, await readCatalog(catalogFile)) }
    catch (error) { sendJsonError(response, 500, error instanceof Error ? error.message : String(error)) }
    return true
  }
  if (pathname === '/__buildviz/catalog' && request.method === 'POST') {
    try {
      const payload = await readRequestJson<{ items?: unknown }>(request)
      sendJson(response, await upsertCatalogItems({ getBuilds: () => getRegistry().builds, catalogPath: catalogFile }, payload.items))
    } catch (error) { sendJsonError(response, 400, error instanceof Error ? error.message : String(error)) }
    return true
  }
  if (pathname === '/__buildviz/revisions/metadata' && request.method === 'PATCH') {
    try {
      const payload = await readRequestJson<Record<string, unknown>>(request)
      const result = await withCatalogMutation(async () => {
        const { source } = await resolveCatalogSource({ getBuilds: () => getRegistry().builds }, payload, 'Revision', true, false)
        const message = requireRevisionDescription(payload.message)
        const entry = getRegistry().builds.find((entry) => entry.id === source.buildId)!
        const meta = await readBuildMeta(entry.buildDir)
        const branches = await describeBuildBranches(entry.buildDir, meta)
        const branch = branches.find((entry) => entry.name === source.branch)!
        const revision = branch.versions.find((entry) => entry.name === source.version)!
        if (payload.ifMessageMissing === true && revision.message?.trim()) {
          return { ok: true, updated: false, message: revision.message }
        }
        const updated = { name: revision.name, pushedAt: revision.pushedAt ?? undefined,
          message, messageSource: 'retrospective' as const, messageUpdatedAt: new Date().toISOString() }
        const records = branches.map((branch) => {
          const recorded = meta?.branches?.find((record) => record.name === branch.name)
          const versions = new Map<string, Omit<CacheVersionMeta, 'pushedAt'> & { pushedAt?: string }>(branch.versions.map(({ name, pushedAt, message, messageSource, messageUpdatedAt }) =>
            [name, { name, pushedAt: pushedAt ?? undefined, message, messageSource, messageUpdatedAt }]))
          for (const version of recorded?.versions ?? []) versions.set(version.name, version)
          if (branch.name === source.branch) versions.set(updated.name, updated)
          return { ...recorded, name: branch.name, defaultVersion: branch.defaultVersion, versions: [...versions.values()] }
        })
        const next = { ...meta, branches: records,
          ...(source.branch === resolveDefaultBranch(meta) ? {
            versions: [...(meta?.versions ?? []).filter((version) => version.name !== source.version), updated],
          } : {}),
        }
        const target = path.join(entry.buildDir, 'meta.json')
        const temporary = `${target}.catalog-update.tmp`
        await writeFile(temporary, `${JSON.stringify(next, null, 2)}\n`, 'utf8')
        await rename(temporary, target)
        return { ok: true, updated: true, ...updated }
      })
      sendJson(response, result)
    } catch (error) { sendJsonError(response, 400, error instanceof Error ? error.message : String(error)) }
    return true
  }

  // --- Diagrams (standalone presentation documents; see hub/diagramStore.ts).
  // Read-only HTTP surface: the index for discovery, diagram.json for the
  // viewer's live poll (ETag/304 keeps it cheap), and snapshotted part assets.
  // All mutations go through the MCP diagram tools.
  if (pathname === '/diagrams/index.json' && request.method === 'GET') {
    sendJsonWithEtag(request, response, { diagrams: await listDiagrams() })
    return true
  }
  const diagramMatch = pathname.match(/^\/diagrams\/([^/]+)\/(.+)$/)
  if (diagramMatch && request.method === 'GET') {
    let name: string
    try {
      name = canonicalizeDiagramName(decodeURIComponent(diagramMatch[1]))
    } catch {
      sendJsonError(response, 404, `Unknown diagram "${diagramMatch[1]}"`)
      return true
    }
    if (diagramMatch[2] === 'diagram.json') {
      try {
        const { doc } = await readDiagram(name)
        sendJsonWithEtag(request, response, doc)
      } catch (error) {
        sendJsonError(response, 404, error instanceof Error ? error.message : String(error))
      }
      return true
    }
    await sendFile(response, safePathInside(diagramDirFor(name), diagramMatch[2]))
    return true
  }

  if (pathname === '/__buildviz/status' && request.method === 'GET') {
    // The unmistakable hub signature: clients verify `service`/`version` here
    // before trusting the endpoint (a dev server cannot produce this).
    sendJson(response, {
      ok: true,
      service: HUB_SERVICE,
      version: packageVersion,
      // Advertise the bind mode so a client/teammate knows mutations are off.
      readOnly,
      // Advertise whether mutation + MCP endpoints require an API key.
      authRequired: Boolean(apiKey),
      publishPolicy: PUBLISH_POLICY,
      versionFeedback: { endpoint: '/__buildviz/feedback', appendOnly: true, exactVersionRequired: true },
      agentGuidance: VERSION_LEARNING_GUIDANCE,
      server: {
        service: HUB_SERVICE,
        version: packageVersion,
        host: new URL(baseUrl).hostname,
        port: Number(new URL(baseUrl).port),
        baseUrl,
        pid: process.pid,
        startedAt,
        readOnly,
      },
      registryPath,
      serverInfoPath,
      ...(await registeredBuildsIndex(getRegistry())),
    })
    return true
  }

  if (pathname === '/__buildviz/builds' && request.method === 'GET') {
    sendJson(response, { ok: true, ...(await registeredBuildsIndex(getRegistry())) })
    return true
  }

  // Per-part history (read-only). Ledgers are refreshed lazily on read and
  // eagerly after every push, so this reflects the latest pushed versions.
  //   ?build=<id>                       -> per-part summaries (one row per partType)
  //   ?build=<id>&part=<partType>      -> that part's full change timeline
  //   ?q=<terms>[&build=<id>]          -> search names + descriptions + messages
  //                                        (all builds on the hub when build is omitted)
  //   &branch=<name>                    -> non-default branch (default: build's default)
  if (pathname === '/__buildviz/part-history' && request.method === 'GET') {
    try {
      const buildParam = requestUrl?.searchParams.get('build')?.trim() || null
      const partParam = requestUrl?.searchParams.get('part')?.trim() || null
      const queryParam = requestUrl?.searchParams.get('q')?.trim() || null
      const branchParam = requestUrl?.searchParams.get('branch')?.trim() || undefined
      const registry = getRegistry()

      const resolveEntry = (rawId: string) => {
        const id = canonicalizeBuildId(rawId)
        const entry = registry.builds.find((build) => build.id === id)
        if (!entry) {
          throw new Error(
            `No build "${rawId}" on this hub. Known: ${registry.builds.map((build) => build.id).join(', ')}`,
          )
        }
        return entry
      }

      if (queryParam) {
        const targets = buildParam ? [resolveEntry(buildParam)] : registry.builds
        const hits: PartSearchHit[] = []
        for (const target of targets) {
          // No explicit branch: search EVERY branch of the build.
          const branches = branchParam ? [branchParam] : await partHistoryBranches(target.buildDir)
          for (const branchName of branches) {
            try {
              const ledger = await ensurePartHistory(target.buildDir, target.id, branchName)
              hits.push(...searchPartHistory(ledger, queryParam))
            } catch {
              // A build/branch without version snapshots contributes no hits.
            }
          }
        }
        sendJson(response, { ok: true, query: queryParam, hitCount: hits.length, hits })
        return true
      }

      if (!buildParam) {
        sendJsonError(response, 400, 'part-history requires ?build=<id> (or ?q=<terms> to search).')
        return true
      }
      const entry = resolveEntry(buildParam)
      const ledger = await ensurePartHistory(entry.buildDir, entry.id, branchParam)
      if (partParam) {
        const events = ledger.parts[partParam]
        if (!events) {
          const known = Object.keys(ledger.parts).sort().join(', ')
          sendJsonError(
            response,
            404,
            `No part "${partParam}" in ${entry.id}@${ledger.branch}. Known parts: ${known || '(none)'}`,
          )
          return true
        }
        sendJson(response, {
          ok: true,
          buildId: entry.id,
          branch: ledger.branch,
          partType: partParam,
          indexedVersions: ledger.indexed.map((indexed) => indexed.name),
          events,
        })
        return true
      }
      sendJson(response, {
        ok: true,
        buildId: entry.id,
        branch: ledger.branch,
        indexedVersions: ledger.indexed.map((indexed) => indexed.name),
        parts: summarizeParts(ledger),
      })
      return true
    } catch (error) {
      sendJsonError(response, 400, error instanceof Error ? error.message : String(error))
      return true
    }
  }

  if (pathname === '/__buildviz/register' && request.method === 'POST') {
    try {
      const registration = await registrationFromPayload(await readRequestJson(request))
      await withCatalogMutation(async () => {
        const registry = await upsertRegistration(registration)
        getRegistry().builds = registry.builds
      })
      const url = hubViewUrl(baseUrl, registration.id, null)
      const warnings = await registrationSpecWarnings(registration)
      for (const warning of warnings) console.warn(`[register] ${registration.id}: ⚠ ${warning}`)
      sendJson(response, { ok: true, summary: `Registered ${registration.id}.`, build: registration, url, warnings })
    } catch (error) {
      sendJsonError(response, 400, error instanceof Error ? error.message : String(error))
    }
    return true
  }

  if (pathname === '/__buildviz/push' && request.method === 'POST') {
    try {
      // Allow large bodies here: a self-contained push base64-encodes its mesh
      // bytes inline, so the JSON can be much bigger than the default cap.
      const payload = await readRequestJson<PushPayload>(request, 512 * 1024 * 1024)
      const result = await withCatalogMutation(() => pushLayoutFromPayload(payload, baseUrl))
      getRegistry().builds = result.registry.builds
      for (const warning of result.warnings) {
        console.warn(`[push] ${result.registration.id}@${result.written.version}: ⚠ ${warning}`)
      }
      // Fold the new version into the per-part history ledger NOW, before any
      // later retention prune could drop the snapshot unindexed. Best-effort:
      // an indexing failure never fails the push.
      try {
        await ensurePartHistory(result.written.cacheDir, result.registration.id, result.written.branch)
      } catch (error) {
        console.warn(
          `[push] ${result.registration.id}: part-history indexing failed — ${error instanceof Error ? error.message : String(error)}`,
        )
      }
      const pushedAddress =
        result.written.branch === result.written.defaultBranch
          ? `${result.registration.id}@${result.written.version}`
          : `${result.registration.id}@${result.written.branch}@${result.written.version}`
      sendJson(response, {
        ok: true,
        summary: `Pushed ${pushedAddress} (${result.written.unchanged ? 'unchanged; published version preserved' : result.written.isNewBranch ? 'new branch' : 'new version'}).`,
        warnings: result.warnings,
        build: result.registration,
        version: result.written.version,
        defaultVersion: result.written.defaultVersion,
        branch: result.written.branch,
        defaultBranch: result.written.defaultBranch,
        isNewVersion: result.written.isNewVersion,
        isNewBuild: result.written.isNewBuild,
        isNewBranch: result.written.isNewBranch,
        unchanged: result.written.unchanged,
        versions: result.written.versions,
        pruned: result.written.pruned,
        snapshot: result.written.snapshot,
        message: result.written.message,
        reason: result.written.reason,
        nextSteps: result.nextSteps,
        cacheDir: result.written.cacheDir,
        uploads: result.uploads,
        url: result.url,
      })
    } catch (error) {
      sendPublishError(response, error)
    }
    return true
  }

  if (pathname === '/__buildviz/push-analysis' && request.method === 'POST') {
    try {
      const payload = await readRequestJson<PushAnalysisPayload>(request, 512 * 1024 * 1024)
      const result = await pushAnalysisFromPayload(payload, getRegistry(), baseUrl)
      sendJson(response, {
        ok: true,
        summary: `${result.isNew ? 'Attached' : 'Unchanged'} analysis "${result.analysis.name}" on ${result.buildId}.`,
        ...result,
      })
    } catch (error) {
      sendPublishError(response, error)
    }
    return true
  }

  if (pathname === '/__buildviz/pack-export' && request.method === 'POST') {
    try {
      const payload = await readRequestJson<PackExportPayload>(request)
      const result = await packExportFromPayload(payload, getRegistry())
      sendJson(response, {
        ok: true,
        summary: `Exported ${result.plateCount} ${result.format.toUpperCase()} plate file(s) for ${result.buildId}.`,
        ...result,
      })
    } catch (error) {
      sendJsonError(response, 400, error instanceof Error ? error.message : String(error))
    }
    return true
  }

  // Where do this build's STL files live on disk? Powers the viewer's
  // "Open STL folder" link (resolve here, reveal via POST open-path).
  if (pathname === '/__buildviz/stl-dir' && request.method === 'GET') {
    try {
      const buildParam = requestUrl?.searchParams.get('build')?.trim()
      if (!buildParam) {
        sendJsonError(response, 400, 'stl-dir requires ?build=<id>.')
        return true
      }
      const version = requestUrl?.searchParams.get('version')?.trim() || null
      const branch = requestUrl?.searchParams.get('branch')?.trim() || null
      const found = await resolveStlDir(getRegistry(), buildParam, version, branch)
      if (!found) {
        sendJsonError(response, 404, `No on-disk STL files found for ${buildParam}.`)
        return true
      }
      sendJson(response, { ok: true, path: found.path, fileCount: found.fileCount })
    } catch (error) {
      sendJsonError(response, 400, error instanceof Error ? error.message : String(error))
    }
    return true
  }

  if (pathname === '/__buildviz/open-path' && request.method === 'POST') {
    try {
      const payload = await readRequestJson<{ path?: unknown }>(request)
      const dir = await resolveOpenablePath(payload.path, getRegistry())
      await openInFileManager(dir)
      sendJson(response, { ok: true, summary: `Opened ${dir} in the file manager.`, path: dir })
    } catch (error) {
      sendJsonError(response, 400, error instanceof Error ? error.message : String(error))
    }
    return true
  }

  if (pathname.startsWith('/__buildviz')) {
    sendJsonError(response, 404, 'Not found')
    return true
  }

  if (pathname === '/builds/index.json') {
    sendJsonWithEtag(request, response, await registeredBuildsIndex(getRegistry()))
    return true
  }

  if (!pathname.startsWith('/builds/')) return false

  // Decode the whole path so both literal "/" separators and percent-encoded
  // ("%2F") slashes in a hierarchical build id resolve to the same build.
  const restPath = decodeURIComponent(pathname.slice('/builds/'.length))

  // Content-addressed asset store: /builds/_assets/<hash>.<ext>. These are the
  // bytes uploaded with `push`, shared across builds/versions, served read-only.
  // (Available off-loopback too — they are reads, not mutations.)
  if (restPath.startsWith(`${ASSET_STORE_ID}/`)) {
    const fileName = restPath.slice(`${ASSET_STORE_ID}/`.length)
    const filePath = safePathInside(assetStoreDir, fileName)
    await sendFile(response, filePath, request)
    return true
  }

  const matched = resolveBuildAssetRequest(getRegistry(), restPath)
  if (!matched) return false

  const { build, relative } = matched
  const publicBase = buildPublicBase(build.id)
  if (relative === 'scene.json') {
    await sendLocalManifest(
      response,
      path.join(build.buildDir, 'scene.json'),
      publicBase,
      `${publicBase}/design_spec.yaml`,
    )
    return true
  }

  if (relative === 'design_spec.yaml') {
    await sendFile(response, build.designSpecPath)
    return true
  }

  // Named analyses attached to this build: a list plus per-analysis scenes.
  if (relative === 'analyses.json') {
    sendJson(response, { buildId: build.id, analyses: await listAnalyses(build.buildDir) })
    return true
  }
  const analysisSceneMatch = relative.match(/^analyses\/([^/]+)\/scene\.json$/)
  if (analysisSceneMatch) {
    const analysisPath = path.join(analysesDirFor(build.buildDir), analysisSceneMatch[1], 'scene.json')
    if (!existsSync(analysisPath)) {
      response.statusCode = 404
      response.end('Not found')
      return true
    }
    await sendLocalManifest(
      response,
      analysisPath,
      `${publicBase}/analyses/${encodeURIComponent(analysisSceneMatch[1])}`,
      `${publicBase}/design_spec.yaml`,
    )
    return true
  }

  // Branch-scoped requests: /builds/<id>/branches/<b>/... mirrors the root
  // layout per branch (scene.json = the branch's default version;
  // versions/<v>/scene.json = a named version on that branch). Non-manifest
  // files under branches/ fall through to the generic safe file serving below.
  const branchSceneMatch = relative.match(/^branches\/([^/]+)\/(scene\.json|design_spec\.yaml|versions\/([^/]+)\/(scene\.json|design_spec\.yaml))$/)
  if (branchSceneMatch) {
    const branchName = branchSceneMatch[1]
    const branchBase = `${publicBase}/branches/${encodeURIComponent(branchName)}`
    // The DEFAULT branch lives at the build root, so branches/<default>/...
    // aliases back to the root layout (mirrors the versions/<default> alias).
    const buildMeta = await readBuildMeta(build.buildDir)
    const branchDir = branchRootDir(build.buildDir, branchName, resolveDefaultBranch(buildMeta))
    const branchSpecPath = path.join(branchDir, 'design_spec.yaml')

    if (!existsSync(branchDir)) {
      response.statusCode = 404
      response.end('Not found')
      return true
    }
    const branchSpecUrl = existsSync(branchSpecPath)
      ? `${branchBase}/design_spec.yaml`
      : `${publicBase}/design_spec.yaml`
    const versionName = branchSceneMatch[3]

    if (branchSceneMatch[2] === 'scene.json') {
      await sendLocalManifest(response, path.join(branchDir, 'scene.json'), branchBase, branchSpecUrl)
      return true
    }
    if (branchSceneMatch[2] === 'design_spec.yaml') {
      await sendFile(response, existsSync(branchSpecPath) ? branchSpecPath : build.designSpecPath)
      return true
    }
    if (branchSceneMatch[4] === 'design_spec.yaml') {
      const versionSpecPath = path.join(branchDir, 'versions', versionName, 'design_spec.yaml')
      await sendFile(
        response,
        existsSync(versionSpecPath)
          ? versionSpecPath
          : existsSync(branchSpecPath)
            ? branchSpecPath
            : build.designSpecPath,
      )
      return true
    }
    const resolved = await resolveVersionScene(build.buildDir, versionName, branchName)
    if (!resolved) {
      response.statusCode = 404
      response.end('Not found')
      return true
    }
    const versionSpecUrl = existsSync(path.join(resolved.base, 'design_spec.yaml'))
      ? (resolved.versioned
          ? `${branchBase}/versions/${encodeURIComponent(versionName)}/design_spec.yaml`
          : branchSpecUrl)
      : branchSpecUrl
    await sendLocalManifest(
      response,
      resolved.scenePath,
      resolved.versioned ? `${branchBase}/versions/${encodeURIComponent(versionName)}` : branchBase,
      versionSpecUrl,
    )
    return true
  }

  const versionMatch = relative.match(/^versions\/([^/]+)\/scene\.json$/)
  if (versionMatch) {
    const version = versionMatch[1]
    const resolved = await resolveVersionScene(build.buildDir, version)
    if (!resolved) {
      response.statusCode = 404
      response.end('Not found')
      return true
    }
    const designSpecUrl = existsSync(path.join(resolved.base, 'design_spec.yaml'))
      ? (resolved.versioned
          ? `${publicBase}/versions/${encodeURIComponent(version)}/design_spec.yaml`
          : `${publicBase}/design_spec.yaml`)
      : `${publicBase}/design_spec.yaml`
    await sendLocalManifest(
      response,
      resolved.scenePath,
      resolved.versioned ? `${publicBase}/versions/${encodeURIComponent(version)}` : publicBase,
      designSpecUrl,
    )
    return true
  }

  const versionDesignSpecMatch = relative.match(/^versions\/([^/]+)\/design_spec\.yaml$/)
  if (versionDesignSpecMatch) {
    const versionDesignSpecPath = path.join(build.buildDir, 'versions', versionDesignSpecMatch[1], 'design_spec.yaml')
    await sendFile(response, existsSync(versionDesignSpecPath) ? versionDesignSpecPath : build.designSpecPath)
    return true
  }

  const filePath = safePathInside(build.buildDir, relative)
  if (!filePath) {
    response.statusCode = 403
    response.end('Forbidden')
    return true
  }
  await sendFile(response, filePath, request)
  return true
}

// The hub view URL for a build/version, using the discovered hub base URL.
// Always emits the project/build/version params the viewer understands.
const hubViewUrl = (
  baseUrl: string,
  buildId: string,
  version: string | null,
  extra: Record<string, string | undefined> = {},
) => {
  const url = new URL(baseUrl)
  const { project, build } = splitProjectBuild(buildId)
  url.searchParams.set('project', project)
  url.searchParams.set('build', build)
  if (version) url.searchParams.set('version', version)
  Object.entries(extra).forEach(([key, value]) => {
    if (value) url.searchParams.set(key, value)
  })
  return url.toString()
}

// Best-effort access log for a handled hub request. Records ONLY route metadata
// (method, path with the query string stripped, status, duration, read-only
// mode) — never request/response bodies — so a later usage audit is conclusive.
// Fire-and-forget: appendUsageEvent never throws and we do not await it, so a
// request is never delayed or affected by logging.
const logHubRequest = (
  request: IncomingMessage,
  response: ServerResponse,
  startedMs: number,
  readOnly: boolean,
) => {
  // Strip the query string entirely (it can carry benign-but-noisy params and
  // we never want to persist anything but the route itself).
  const pathname = (request.url ?? '/').split('?')[0]
  if (!pathname.startsWith('/__buildviz') && !pathname.startsWith('/builds')) return
  void appendUsageEvent({
    source: 'hub',
    method: request.method ?? '?',
    path: pathname,
    status: response.statusCode,
    durationMs: Date.now() - startedMs,
    readOnly,
  })
}

export const startLocalServer = async (args: string[]) => {
  const { positional, options } = parseArgs(args)
  const buildDir = resolveBuildDirOption(options, positional)
  const scenePath = path.join(buildDir, 'scene.json')
  const resolvedDesignSpecPath = path.resolve(
    process.cwd(),
    optionString(options, 'design-spec', 'designSpec', 'design_spec') ?? path.join(buildDir, 'design_spec.yaml'),
  )
  // design_spec.yaml is optional; serve it only when it is present.
  const designSpecPath = existsSync(resolvedDesignSpecPath) ? resolvedDesignSpecPath : null
  const host = optionString(options, 'host') ?? '127.0.0.1'
  const port = parsePort(optionString(options, 'port'))

  if (!existsSync(scenePath)) {
    throw new Error(`Missing scene.json in ${buildDir}`)
  }

  const openPath = '/?build=local'
  // The local server provides its own /builds/index.json for the "local" build.
  process.env.BUILDVIZ_LOCAL_SERVE = '1'
  const server = await createServer({
    root: viewerRoot,
    plugins: [
      {
        name: 'buildviz-local-assets',
        configureServer(viteServer) {
          viteServer.middlewares.use((request, response, next) => {
            void serveLocalAsset(request, response, buildDir, designSpecPath).then((handled) => {
              if (!handled) next()
            })
          })
        },
      },
    ],
    server: {
      host,
      open: options['no-open'] ? false : openPath,
      port,
      strictPort: true,
    },
  })

  await server.listen()
  const url = `http://${host}:${port}${openPath}`
  console.log(`BuildViz serving ${buildDir}`)
  console.log(`design_spec.yaml: ${designSpecPath ?? 'none (optional)'}`)
  console.log(url)
  server.printUrls()
}

const startHubServer = async (args: string[]) => {
  const { options } = parseArgs(args)
  const host = resolveBindHost(options)
  const port = parsePort(optionString(options, 'port'), HUB_DEFAULT_PORT)
  const baseUrl = hubBaseUrl(host, port)
  const startedAt = new Date().toISOString()
  // Any non-loopback bind serves READ-ONLY: mutation + host-action endpoints
  // are disabled (see serveHubAsset). The trust model is private-network only.
  const readOnly = !isLoopbackHost(host)
  // Optional API key (--api-key / BUILDVIZ_API_KEY): when set, mutation
  // endpoints and /mcp require it. Useful when the hub is published through a
  // reverse proxy / tunnel where the loopback-bind trust model doesn't apply.
  const apiKey = resolveHubApiKey(options)
  // Make the in-memory build set consistent on every (re)start:
  //   1. restoreCacheBuilds re-adds hub-managed (pushed) builds found under the
  //      cache so pushed layouts and their versions survive a restart even if
  //      registry.json was lost.
  //   2. pruneDeadBuilds drops entries whose source directory has vanished
  //      (e.g. a moved/deleted on-disk project) so the hub never advertises a
  //      build whose assets would 404.
  const registry = await pruneDeadBuilds(await restoreCacheBuilds(await readRegistry()))

  if (readOnly) {
    console.warn(
      `\n⚠ BuildViz hub is binding to ${host}:${port} (NON-loopback). It will be reachable by\n` +
        '  other machines on this network. There is NO app-level authentication — the trust\n' +
        '  model is private-network only (use a LAN/VPN you trust, e.g. Tailscale).\n' +
        '  READ-ONLY mode is ON: push, pack-export, register, and open-path are DISABLED.\n' +
        '  Teammates can VIEW builds and read data; they cannot modify anything or run host\n' +
        '  actions. Bind to 127.0.0.1 (the default) for full local read/write access.\n',
    )
  }

  // The hub provides /builds/index.json and /builds/<id>/... from registered project directories.
  process.env.BUILDVIZ_LOCAL_SERVE = '1'
  const server = await createServer({
    root: viewerRoot,
    plugins: [
      {
        name: 'buildviz-hub-assets',
        configureServer(viteServer) {
          viteServer.middlewares.use((request, response, next) => {
            const startedMs = Date.now()
            void serveHubAsset(request, response, () => registry, baseUrl, startedAt, readOnly, apiKey).then((handled) => {
              if (handled) logHubRequest(request, response, startedMs, readOnly)
              if (!handled) next()
            })
          })
        },
      },
    ],
    server: {
      host,
      open: options['no-open'] ? false : '/',
      port,
      strictPort: true,
    },
  })

  await server.listen()
  await writeServerInfo({
    service: HUB_SERVICE,
    version: packageVersion,
    host,
    port,
    baseUrl,
    pid: process.pid,
    startedAt,
    readOnly,
  })

  console.log(
    `BuildViz hub (${HUB_SERVICE} v${packageVersion}) running at ${baseUrl}` +
      (readOnly ? ' [READ-ONLY remote bind]' : ''),
  )
  console.log(
    apiKey
      ? 'API key auth: ENABLED for mutation endpoints and /mcp (Authorization: Bearer / X-API-Key / ?key=).'
      : 'API key auth: disabled (set BUILDVIZ_API_KEY or pass --api-key to require a key for mutations and /mcp).',
  )
  console.log(`MCP endpoint: ${baseUrl}/mcp (Streamable HTTP)`)
  console.log(`Discovery file: ${serverInfoPath}`)
  console.log(`Registry file: ${registryPath}`)
  console.log('Register a project with: npx buildviz register . --project <project> --build <build>')
  server.printUrls()
}

// --- First-class hub daemon lifecycle ----------------------------------------

const hubStatusEndpoint = (baseUrl: string) => `${baseUrl.replace(/\/+$/, '')}/__buildviz/status`

type HubStatusResponse = {
  ok: boolean
  service: string
  version: string
  readOnly?: boolean
  server: HubServerInfo
  projects?: { id: string; name: string; builds: BuildsIndexBuild[] }[]
  builds: BuildsIndexBuild[]
}

// Quick liveness probe of a hub's HTTP status endpoint AND positive identity
// check. Returns the parsed status only when the endpoint answers with the
// buildviz-hub JSON signature; returns null when nothing is listening, the hub
// is unhealthy, OR something else (e.g. a plain Vite dev server serving HTML,
// or any other JSON service) is on the port. This is the single verification
// gate every client uses, so a dev server can never masquerade as the hub.
// Never hangs: the request is aborted after timeoutMs.
const probeHubStatus = async (baseUrl: string, timeoutMs = 2000): Promise<HubStatusResponse | null> => {
  try {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    const response = await fetch(hubStatusEndpoint(baseUrl), { signal: controller.signal }).finally(() =>
      clearTimeout(timer),
    )
    if (!response.ok) return null
    // A dev server typically returns the SPA index.html (text/html) here; bail
    // before trying to parse it as JSON.
    const contentType = response.headers.get('content-type') ?? ''
    if (!contentType.includes('application/json')) return null
    const body = (await response.json()) as Partial<HubStatusResponse>
    if (body.ok === true && body.service === HUB_SERVICE) {
      return body as HubStatusResponse
    }
    return null
  } catch {
    return null
  }
}

const pidAlive = (pid: number) => {
  try {
    process.kill(pid, 0)
    return true
  } catch (error) {
    // ESRCH => no such process; EPERM => exists but not ours (still "alive").
    return (error as NodeJS.ErrnoException).code === 'EPERM'
  }
}

const readHubPid = () => {
  if (!existsSync(hubPidPath)) return null
  const pid = Number(readFileSync(hubPidPath, 'utf8').trim())
  return Number.isInteger(pid) && pid > 0 ? pid : null
}

const clearHubDiscovery = async () => {
  await Promise.all([
    unlink(hubPidPath).catch(() => {}),
    unlink(serverInfoPath).catch(() => {}),
  ])
}

// Poll until the hub answers GET /__buildviz/status or the deadline passes.
const waitForHubReady = async (baseUrl: string, timeoutMs = 30_000) => {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    const status = await probeHubStatus(baseUrl, 1500)
    if (status) return status
    await new Promise((resolve) => setTimeout(resolve, 300))
  }
  return null
}

// Best-effort kill of whatever is LISTENing on a TCP port (covers foreground
// hubs and stale daemons whose pidfile was lost). Uses lsof, which is present on
// macOS/Linux; failures are swallowed.
const killPortListeners = (port: number, signal: NodeJS.Signals) => {
  const result = spawnSync('lsof', ['-ti', `tcp:${port}`, '-sTCP:LISTEN'], { encoding: 'utf8' })
  if (result.status !== 0 || !result.stdout) return []
  const pids = result.stdout
    .split('\n')
    .map((value) => Number(value.trim()))
    .filter((pid) => Number.isInteger(pid) && pid > 0)
  for (const pid of pids) {
    try {
      process.kill(pid, signal)
    } catch {
      // Already gone; ignore.
    }
  }
  return pids
}

// Spawn the hub as a detached process-group leader with stdio redirected to the
// log file, record its pid, and wait until it answers. Returns the ready status
// (or an "already running" marker). Throws if it never becomes ready. No output.
const spawnDetachedHub = async (host: string, port: number) => {
  const baseUrl = hubBaseUrl(host, port)
  const existing = await probeHubStatus(baseUrl)
  if (existing) return { baseUrl, pid: existing.server.pid, status: existing, alreadyRunning: true as const }

  await ensureBuildvizHome()
  const logFd = openSync(hubLogPath, 'a')
  let pid: number | undefined
  try {
    const entry = path.join(projectRoot, 'bin', 'buildviz.mjs')
    const child = spawn(
      process.execPath,
      [entry, 'hub', '--no-open', '--host', host, '--port', String(port)],
      { detached: true, stdio: ['ignore', logFd, logFd] },
    )
    child.unref()
    pid = child.pid
    if (pid) await writeFile(hubPidPath, `${pid}\n`, 'utf8')
  } finally {
    closeSync(logFd)
  }

  const status = await waitForHubReady(baseUrl)
  if (!status) {
    throw new Error(`Hub did not become ready at ${baseUrl} within 30s. See ${hubLogPath}.`)
  }
  return { baseUrl, pid, status, alreadyRunning: false as const }
}

const startHubDetached = async (options: CliOptions) => {
  const host = resolveBindHost(options)
  const port = parsePort(optionString(options, 'port'), HUB_DEFAULT_PORT)
  if (!isLoopbackHost(host) && !options.json) {
    console.warn(
      `⚠ Binding the detached hub to ${host}:${port} (non-loopback). It runs READ-ONLY ` +
        '(push/pack-export/register/open-path disabled) with no auth — private-network trust only.',
    )
  }
  const { baseUrl, pid, status, alreadyRunning } = await spawnDetachedHub(host, port)

  const result = {
    ok: true,
    detached: true,
    alreadyRunning,
    url: baseUrl,
    pid,
    pidFile: hubPidPath,
    logPath: hubLogPath,
    builds: status.builds.length,
  }
  if (options.json) {
    printJson(result)
    return
  }
  console.log(
    alreadyRunning
      ? `BuildViz hub already running at ${baseUrl}`
      : `BuildViz hub started (detached) at ${baseUrl}`,
  )
  console.log(`PID: ${pid ?? status.server.pid} · builds: ${status.builds.length}`)
  console.log(`Logs: ${hubLogPath}`)
  console.log('Stop with: npx buildviz hub stop')
}

const stopHub = async (options: CliOptions) => {
  const serverInfo = await readServerInfo()
  const host = optionString(options, 'host') ?? serverInfo?.host ?? '127.0.0.1'
  const port = optionString(options, 'port')
    ? parsePort(optionString(options, 'port'))
    : serverInfo?.port ?? HUB_DEFAULT_PORT
  const baseUrl = serverInfo?.baseUrl ?? hubBaseUrl(host, port)

  const wasRunning = (await probeHubStatus(baseUrl)) !== null
  const killed = new Set<number>()

  const groupPid = readHubPid()
  if (groupPid && pidAlive(groupPid)) {
    try {
      process.kill(-groupPid, 'SIGTERM')
      killed.add(groupPid)
    } catch {
      try {
        process.kill(groupPid, 'SIGTERM')
        killed.add(groupPid)
      } catch {
        // already gone
      }
    }
  }
  if (serverInfo?.pid && pidAlive(serverInfo.pid)) {
    try {
      process.kill(serverInfo.pid, 'SIGTERM')
      killed.add(serverInfo.pid)
    } catch {
      // already gone
    }
  }
  killPortListeners(port, 'SIGTERM').forEach((pid) => killed.add(pid))

  await new Promise((resolve) => setTimeout(resolve, 400))
  // Escalate to SIGKILL if anything is still answering on the port.
  if (await probeHubStatus(baseUrl)) {
    if (groupPid) {
      try {
        process.kill(-groupPid, 'SIGKILL')
      } catch {
        // ignore
      }
    }
    killPortListeners(port, 'SIGKILL').forEach((pid) => killed.add(pid))
    await new Promise((resolve) => setTimeout(resolve, 300))
  }

  await clearHubDiscovery()
  const stillUp = (await probeHubStatus(baseUrl)) !== null
  const result = {
    ok: !stillUp,
    stopped: wasRunning && !stillUp,
    wasRunning,
    url: baseUrl,
    killedPids: [...killed],
  }
  if (options.json) {
    printJson(result)
    return
  }
  if (!wasRunning && killed.size === 0) {
    console.log(`No running BuildViz hub found at ${baseUrl}. Cleared any stale discovery files.`)
    return
  }
  if (stillUp) {
    console.log(`Failed to stop the hub at ${baseUrl}. Tried pids: ${[...killed].join(', ') || 'none'}.`)
    return
  }
  console.log(`Stopped BuildViz hub at ${baseUrl} (pids: ${[...killed].join(', ') || 'none'}).`)
}

// Resolve a VERIFIED live hub, optionally auto-starting a detached one when none
// is reachable. Autostart is ON by default for write commands; pass
// --no-autostart to opt out. The resolution is deliberately strict:
//   1. Read discovery (~/.buildviz/server.json).
//   2. Trust it ONLY if GET /__buildviz/status returns the buildviz-hub
//      signature (probeHubStatus). This rejects a dead pid AND a non-hub on the
//      port (e.g. a plain Vite dev server) -- a dev server can never be used as
//      the hub.
//   3. If discovery is missing/stale/points at a non-hub, clear it and (for
//      write commands) autostart a fresh detached hub on the CANONICAL port so
//      we never bind onto a dev server's port.
const ensureHubRunning = async (options: CliOptions): Promise<HubServerInfo> => {
  const serverInfo = await readServerInfo()
  if (serverInfo && (await probeHubStatus(serverInfo.baseUrl))) return serverInfo

  // Discovery is missing, stale (dead pid), or points at a non-hub endpoint.
  // Drop the misleading discovery before autostarting so nothing reuses a stale
  // port (which might belong to an unrelated dev server).
  if (serverInfo) await clearHubDiscovery()

  const autostart = !(options['no-autostart'] ?? options.noAutostart)
  if (autostart) {
    const host = optionString(options, 'host') ?? '127.0.0.1'
    // Always autostart on the canonical hub port (or an explicit --port), never
    // on the possibly-bogus port from stale discovery.
    const port = parsePort(optionString(options, 'port'), HUB_DEFAULT_PORT)
    if (!options.json) {
      const reason = serverInfo ? 'stale/non-hub discovery' : 'no discovery file'
      console.error(
        `No verified BuildViz hub (${reason}); auto-starting a detached hub at ${hubBaseUrl(host, port)} ...`,
      )
    }
    await spawnDetachedHub(host, port)
    const restarted = await readServerInfo()
    if (restarted && (await probeHubStatus(restarted.baseUrl))) return restarted
  }

  if (!serverInfo) {
    throw new Error(
      `No BuildViz hub discovery file at ${serverInfoPath}. Start one with: npx buildviz hub --detach`,
    )
  }
  throw new Error(
    `BuildViz hub discovery at ${serverInfoPath} did not resolve to a verified ${HUB_SERVICE} ` +
      '(stale, or a non-hub server is on the port). ' +
      'Start one with: npx buildviz hub --detach (or pass --no-autostart to fail fast).',
  )
}

export const runHubCommand = async (args: string[]) => {
  const { positional, options } = parseArgs(args)
  const sub = positional[0]
  if (sub === 'stop') return stopHub(options)
  if (sub === 'status') return printHubStatus(args.filter((arg) => arg !== 'status'))
  if (sub === 'restart') {
    await stopHub(options)
    return startHubDetached(options)
  }
  const detach = Boolean(options.detach ?? options.detached ?? options.background)
  if (detach) return startHubDetached(options)
  // Foreground hub (default). Drop a leading "start" subcommand if present.
  return startHubServer(sub === 'start' ? args.filter((arg) => arg !== 'start') : args)
}

const fetchJson = async <T>(url: string, init?: RequestInit) => {
  // If the environment carries the hub API key, attach it so CLI commands
  // (register/push/status) work against a key-protected hub transparently.
  const apiKey = process.env.BUILDVIZ_API_KEY
  const headers = { ...(init?.headers as Record<string, string> | undefined) }
  if (apiKey && !headers['X-API-Key']) headers['X-API-Key'] = apiKey
  const response = await fetch(url, { ...init, headers })
  const text = await response.text()
  const body = text ? JSON.parse(text) as T & { error?: string } : ({} as T & { error?: string })
  if (!response.ok) throw new Error(body.error ?? `${response.status} ${response.statusText}`)
  return body as T
}

export const feedbackToHub = async (args: string[]) => {
  const { positional, options } = parseArgs(args)
  const address = parseBuildAddress(positional[0] ?? '')
  const version = optionString(options, 'version') ?? address.version
  const branch = optionString(options, 'branch') ?? address.branch
  if (!address.buildId || !version || version === 'latest') {
    throw new Error('feedback requires an exact version: buildviz feedback project/build@v12 [--branch main]. Use --kind issue --basis user-report -m "what went wrong" to append; omit write flags to read.')
  }
  const remote = optionString(options, 'url')
  const baseUrl = remote ? new URL(remote).origin : (await ensureHubRunning(options)).baseUrl
  const apiKey = resolveHubApiKey(options)
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(apiKey ? { 'X-API-Key': apiKey } : {}) }
  const mutation = ['kind', 'basis', 'message', 'id', 'parts', 'evidence', 'related-version', 'related-feedback-id'].some((key) => options[key] !== undefined)
  const payload = {
    buildId: address.buildId, version, ...(branch ? { branch } : {}),
    kind: optionString(options, 'kind'), basis: optionString(options, 'basis'),
    message: optionString(options, 'message'), id: optionString(options, 'id'),
    parts: optionString(options, 'parts')?.split(',').map((part) => part.trim()).filter(Boolean),
    evidence: optionString(options, 'evidence'),
    relatedVersion: optionString(options, 'related-version'),
    relatedFeedbackId: optionString(options, 'related-feedback-id'),
  }
  const query = new URLSearchParams({ buildId: address.buildId, version, ...(branch ? { branch } : {}) })
  const result = await fetchJson<VersionFeedback & { entry?: { id: string }; unchanged?: boolean }>(
    `${baseUrl}/__buildviz/feedback${mutation ? '' : `?${query}`}`,
    { method: mutation ? 'POST' : 'GET', headers, ...(mutation ? { body: JSON.stringify(payload) } : {}) },
  )
  if (options.json) { printJson(result); return }
  console.log(`${result.buildId}@${result.branch}@${result.version}`)
  console.log(`Why: ${result.reason ?? 'Not recorded at publish time. Add a retrospective note; do not rewrite the version.'}`)
  if (result.entry) console.log(`${result.unchanged ? 'Unchanged feedback' : 'Recorded feedback'}: ${result.entry.id}`)
  for (const entry of result.entries) {
    console.log(`- [${entry.kind}; ${entry.basis}] ${entry.message} (${entry.id})`)
    if (entry.parts?.length) console.log(`  Parts: ${entry.parts.join(', ')}`)
    if (entry.evidence) console.log(`  Evidence: ${entry.evidence}`)
    if (entry.relatedVersion) console.log(`  Related version: ${entry.relatedVersion}`)
  }
  if (!result.entries.length) console.log('No feedback recorded. This does not mean the version was validated.')
  console.log(result.guidance)
}

export const registerWithHub = async (args: string[]) => {
  const { positional, options } = parseArgs(args)
  const serverInfo = await ensureHubRunning(options)
  const buildDir = resolveBuildDirOption(options, positional)
  const designSpecPath = path.resolve(
    process.cwd(),
    optionString(options, 'design-spec', 'designSpec', 'design_spec') ?? path.join(buildDir, 'design_spec.yaml'),
  )
  const sceneName = existsSync(path.join(buildDir, 'scene.json'))
    ? await readSceneName(path.join(buildDir, 'scene.json'))
    : null
  const { project, build, buildId, derived } = resolveProjectBuild(
    options,
    buildDir,
    sceneName ?? undefined,
  )
  assertValidBuildId(buildId)

  const result = await fetchJson<{
    ok: true
    summary: string
    build: HubBuildRegistration
    url: string
    warnings?: string[]
  }>(`${serverInfo.baseUrl}/__buildviz/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      buildDir,
      buildId,
      designSpecPath,
      name: optionString(options, 'name'),
    }),
  })

  if (options.json) {
    printJson({ ...result, project, build })
    return
  }

  console.log(result.summary)
  if (derived.length > 0) console.log(`Auto-derived ${derived.join(', ')}.`)
  console.log(`Project: ${project} · Build: ${build} · id: ${buildId}`)
  console.log(`Build directory: ${result.build.buildDir}`)
  for (const warning of result.warnings ?? []) {
    console.warn(`⚠ ${warning}`)
  }
  console.log(`View: ${result.url}`)
}

const readStdin = async () => {
  if (process.stdin.isTTY) return ''
  const chunks: Buffer[] = []
  for await (const chunk of process.stdin) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk))
  }
  return Buffer.concat(chunks).toString('utf8')
}

export const pushToHub = async (args: string[]) => {
  const { positional, options } = parseArgs(args)
  const serverInfo = await ensureHubRunning(options)

  // Read the scene first so an omitted --build can fall back to the scene name.
  const sceneFile = optionString(options, 'scene', 'scene-file', 'sceneFile') ?? positional[0]
  const sceneText = sceneFile
    ? await readFile(path.resolve(process.cwd(), sceneFile), 'utf8')
    : await readStdin()
  if (!sceneText.trim()) {
    throw new Error('push requires a scene via --scene <file> or piped JSON on stdin')
  }

  let scene: unknown
  try {
    scene = JSON.parse(sceneText)
  } catch (error) {
    throw new Error(
      `Could not parse scene JSON: ${error instanceof Error ? error.message : String(error)}`,
      { cause: error },
    )
  }
  const sceneName =
    scene && typeof scene === 'object' && typeof (scene as { name?: unknown }).name === 'string'
      ? ((scene as { name: string }).name)
      : undefined

  // Derive project/build from flags (or repo/dir/scene when omitted). The build
  // dir hint is the scene file's directory, if any.
  const dirHint = sceneFile ? path.dirname(path.resolve(process.cwd(), sceneFile)) : undefined
  const { project, build, buildId, derived } = resolveProjectBuild(options, dirHint, sceneName)
  assertValidBuildId(buildId)

  const versionOpt = optionString(options, 'version')
  const bump = !versionOpt || Boolean(options.bump)
  // New version by default, also when speaking to an older hub that needs bump.
  const version = versionOpt ? canonicalizeVersionName(versionOpt) : undefined
  if (versionOpt && !version) throw new Error(`Version "${versionOpt}" has no usable characters.`)
  // --branch targets (or creates) a named branch inside the build; omitted ⇒
  // the build's default branch. --set-default-branch promotes it afterwards.
  const branchOpt = optionString(options, 'branch')
  const branch = branchOpt ? canonicalizeBranchName(branchOpt) : undefined
  if (branchOpt && !branch) throw new Error(`Branch "${branchOpt}" has no usable characters.`)
  const setDefaultBranch = Boolean(options['set-default-branch'] ?? options.setDefaultBranch)
  const noSnapshot = Boolean(options['no-snapshot'] ?? options.noSnapshot)
  // REQUIRED changelog/commit note for the version being created/bumped (-m).
  // Checked here, before assets are read and the payload is POSTed, so the
  // failure is instant; the hub enforces the same rule server-side.
  const message = requireRevisionDescription(optionString(options, 'message', 'msg'))
  const reason = normalizeVersionReason(optionString(options, 'reason'))
  // --bump makes the new version the default (like --set-default) unless the
  // caller opts out with --no-default; an explicit --set-default always wins.
  const explicitSetDefault = Boolean(options['set-default'] ?? options.setDefault ?? options.default)
  const optOutDefault = Boolean(options['no-default'] ?? options['no-set-default'])
  const setDefault = explicitSetDefault || (bump && !optOutDefault)

  const designSpecFile = optionString(options, 'design-spec', 'designSpec', 'design_spec')
  let designSpec = designSpecFile
    ? await readFile(path.resolve(process.cwd(), designSpecFile), 'utf8')
    : undefined
  // The design spec is the versioned record of each part's purpose, so pushes
  // carry it by default: with no explicit --design-spec, a design_spec.yaml
  // sitting next to the pushed scene file is auto-attached.
  let autoSpecPath: string | null = null
  if (designSpec === undefined && dirHint) {
    const candidate = path.join(dirHint, 'design_spec.yaml')
    if (existsSync(candidate)) {
      const text = await readFile(candidate, 'utf8').catch(() => null)
      if (text !== null) {
        designSpec = text
        autoSpecPath = candidate
      }
    }
  }
  const assetsBaseUrl = optionString(options, 'assets-base-url', 'assetsBaseUrl')
  const keepOpt = optionString(options, 'keep', 'keep-versions', 'keepVersions')
  let keepVersions: number | undefined
  if (keepOpt !== undefined) {
    const parsed = Number(keepOpt)
    if (!Number.isInteger(parsed) || parsed < 1) {
      throw new Error(`Invalid --keep "${keepOpt}"; use a positive integer (versions to retain per build).`)
    }
    keepVersions = parsed
  }

  // Optional binary asset upload: read each scene mesh's local file and ship the
  // bytes so the pushed build is self-contained in the cache (no external/
  // reachable-URL requirement). Opt-in via --upload-assets / --upload; OFF by
  // default so pushes without it behave exactly as before.
  const uploadAssets = Boolean(
    options['upload-assets'] ?? options.uploadAssets ?? options.upload,
  )
  const maxUploadMbOpt = optionString(options, 'max-upload-mb', 'maxUploadMb')
  let maxUploadBytes = DEFAULT_MAX_UPLOAD_BYTES
  if (maxUploadMbOpt !== undefined) {
    const parsed = Number(maxUploadMbOpt)
    if (!Number.isFinite(parsed) || parsed <= 0) {
      throw new Error(`Invalid --max-upload-mb "${maxUploadMbOpt}"; use a positive number of megabytes.`)
    }
    maxUploadBytes = Math.round(parsed * 1024 * 1024)
  }

  let assets: Array<{ meshId: string; data: string; ext: string }> | undefined
  if (uploadAssets) {
    const assetsDirOpt = optionString(options, 'assets-dir', 'assetsDir')
    const baseDir = assetsDirOpt
      ? path.resolve(process.cwd(), assetsDirOpt)
      : dirHint ?? process.cwd()
    const meshes = Array.isArray((scene as { meshes?: unknown }).meshes)
      ? ((scene as { meshes: Array<{ id?: unknown; url?: unknown }> }).meshes)
      : []
    assets = []
    let totalBytes = 0
    const seenFiles = new Set<string>()
    for (const mesh of meshes) {
      const meshId = typeof mesh.id === 'string' ? mesh.id : ''
      const url = typeof mesh.url === 'string' ? mesh.url : ''
      // Only upload locally-resolvable relative urls; absolute http(s) and
      // /-rooted urls are already reachable and left untouched.
      if (!meshId || !url || isAbsoluteWebUrl(url) || url.startsWith('/')) continue
      const filePath = path.resolve(baseDir, url.replace(/^\.\//, ''))
      if (!existsSync(filePath)) continue
      const bytes = await readFile(filePath)
      totalBytes += bytes.length
      if (totalBytes > maxUploadBytes) {
        throw new Error(
          `Asset upload exceeds ${formatMb(maxUploadBytes)} ` +
            `(at ${path.relative(process.cwd(), filePath)}). Raise --max-upload-mb or push fewer meshes.`,
        )
      }
      seenFiles.add(filePath)
      assets.push({ meshId, data: bytes.toString('base64'), ext: path.extname(filePath).slice(1) || 'stl' })
    }
    if (assets.length === 0) {
      console.warn(
        'Warning: --upload-assets set but no locally-resolvable relative mesh files were found; ' +
          'pushing the scene without uploads.',
      )
      assets = undefined
    }
  }

  const result = await fetchJson<{
    ok: true
    summary: string
    warnings?: string[]
    build: HubBuildRegistration
    version: string
    defaultVersion: string
    branch: string
    defaultBranch: string
    isNewVersion: boolean
    isNewBuild: boolean
    isNewBranch?: boolean
    unchanged?: boolean
    versions: string[]
    pruned: string[]
    snapshot?: string | null
    message?: string | null
    reason?: string | null
    nextSteps?: string
    cacheDir: string
    uploads?: { count: number; totalBytes: number; dedupedBytes: number }
    url: string
  }>(`${serverInfo.baseUrl}/__buildviz/push`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      buildId,
      version,
      branch,
      setDefaultBranch,
      bump,
      noSnapshot,
      setDefault,
      name: optionString(options, 'name'),
      message,
      reason,
      scene,
      designSpec,
      assetsBaseUrl,
      keepVersions,
      assets,
      maxUploadBytes: assets ? maxUploadBytes : undefined,
    }),
  })

  if (options.json) {
    printJson({ ...result, project, build, designSpecAttached: designSpec !== undefined })
    return
  }

  // Clear, unambiguous feedback: exactly which project/build/version it landed
  // as, and the view URL using the DISCOVERED hub base URL.
  const landed = result.unchanged
    ? 'unchanged; published version preserved'
    : result.isNewBuild
    ? 'created new build'
    : result.isNewBranch
      ? 'created new branch'
      : result.isNewVersion
        ? 'created new version'
        : 'updated existing version — older hub; upgrade for overwrite protection'
  const pushedAddress =
    result.branch && result.branch !== result.defaultBranch
      ? `${project}/${build}@${result.branch}@${result.version}`
      : `${project}/${build}@${result.version}`
  console.log(`Pushed ${pushedAddress} (${landed}).`)
  if (result.branch && result.branch !== result.defaultBranch) {
    console.log(`Branch: ${result.branch} (default branch is "${result.defaultBranch}").`)
  } else if (setDefaultBranch && result.branch) {
    console.log(`Branch: ${result.branch} is now the default branch.`)
  }
  if (derived.length > 0) console.log(`Auto-derived ${derived.join(', ')}.`)
  const otherVersions = result.versions.filter((name) => name !== result.version)
  console.log(
    `Version: ${result.version}${result.version === result.defaultVersion ? ' (default)' : ''}` +
      (otherVersions.length > 0 ? ` · others untouched: ${otherVersions.join(', ')}` : ''),
  )
  if (result.message) console.log(`Message: ${result.message}`)
  if (result.reason) console.log(`Why: ${result.reason}`)
  console.log(`Next: ${result.nextSteps ?? VERSION_LEARNING_GUIDANCE}`)
  if (result.snapshot) {
    console.log(
      `Older hub preserved a snapshot as "${result.snapshot}". Upgrade the hub to protect existing version names.`,
    )
  }
  if (result.pruned && result.pruned.length > 0) {
    console.log(`Retention: pruned ${result.pruned.length} old version(s) — ${result.pruned.join(', ')}.`)
  }
  if (result.uploads && result.uploads.count > 0) {
    const mb = (bytes: number) => `${(bytes / (1024 * 1024)).toFixed(1)}MB`
    const deduped = result.uploads.dedupedBytes > 0 ? ` (${mb(result.uploads.dedupedBytes)} deduped)` : ''
    console.log(
      `Uploaded ${result.uploads.count} asset(s), ${mb(result.uploads.totalBytes)}${deduped} — ` +
        'build is self-contained in the cache.',
    )
  }
  if (!versionOpt && !result.isNewBuild && result.defaultVersion !== result.version) {
    console.log(
      `Created "${result.version}"; the default stays "${result.defaultVersion}" (--no-default).`,
    )
  }
  if (autoSpecPath) {
    console.log(`Design spec: attached ${path.relative(process.cwd(), autoSpecPath)} (found next to the scene).`)
  }
  for (const warning of result.warnings ?? []) {
    console.warn(`⚠ ${warning}`)
  }
  console.log(`View: ${result.url}`)
  console.log(`Hub: ${serverInfo.baseUrl} (from ${serverInfoPath})`)
}

// CLI: attach a named analysis page (a derived scene, e.g. an FEA stress
// field) to an EXISTING build on the hub. Assets are always uploaded so the
// page is self-contained; changed results require a new page name.
export const pushAnalysisToHub = async (args: string[]) => {
  const { positional, options } = parseArgs(args)
  const serverInfo = await ensureHubRunning(options)

  const rawBuildId = positional[0] ?? optionString(options, 'build', 'build-id', 'buildId')
  if (!rawBuildId) {
    throw new Error('push-analysis requires a build id: buildviz push-analysis <project/build> --name <slug> --scene <file>')
  }
  const name = optionString(options, 'name', 'analysis')
  if (!name) throw new Error('push-analysis requires --name <slug> (the analysis page name).')

  const sceneFile = optionString(options, 'scene', 'scene-file', 'sceneFile') ?? positional[1]
  const sceneText = sceneFile
    ? await readFile(path.resolve(process.cwd(), sceneFile), 'utf8')
    : await readStdin()
  if (!sceneText.trim()) {
    throw new Error('push-analysis requires a scene via --scene <file> or piped JSON on stdin')
  }
  const scene = JSON.parse(sceneText) as { meshes?: Array<{ id?: unknown; url?: unknown }> }

  const dirHint = sceneFile ? path.dirname(path.resolve(process.cwd(), sceneFile)) : undefined
  const assetsDirOpt = optionString(options, 'assets-dir', 'assetsDir')
  const baseDir = assetsDirOpt ? path.resolve(process.cwd(), assetsDirOpt) : dirHint ?? process.cwd()

  const maxUploadMbOpt = optionString(options, 'max-upload-mb', 'maxUploadMb')
  let maxUploadBytes = DEFAULT_MAX_UPLOAD_BYTES
  if (maxUploadMbOpt !== undefined) {
    const parsed = Number(maxUploadMbOpt)
    if (!Number.isFinite(parsed) || parsed <= 0) {
      throw new Error(`Invalid --max-upload-mb "${maxUploadMbOpt}"; use a positive number of megabytes.`)
    }
    maxUploadBytes = Math.round(parsed * 1024 * 1024)
  }

  // Analyses must be self-contained on the hub (they outlive the local tmp
  // dirs FEA tools write to), so local relative mesh files are ALWAYS shipped.
  const assets: Array<{ meshId: string; data: string; ext: string }> = []
  let totalBytes = 0
  for (const mesh of Array.isArray(scene.meshes) ? scene.meshes : []) {
    const meshId = typeof mesh.id === 'string' ? mesh.id : ''
    const url = typeof mesh.url === 'string' ? mesh.url : ''
    if (!meshId || !url || isAbsoluteWebUrl(url) || url.startsWith('/')) continue
    const filePath = path.resolve(baseDir, url.replace(/^\.\//, ''))
    if (!existsSync(filePath)) continue
    const bytes = await readFile(filePath)
    totalBytes += bytes.length
    if (totalBytes > maxUploadBytes) {
      throw new Error(
        `Asset upload exceeds ${formatMb(maxUploadBytes)} ` +
          `(at ${path.relative(process.cwd(), filePath)}). Raise --max-upload-mb.`,
      )
    }
    assets.push({ meshId, data: bytes.toString('base64'), ext: path.extname(filePath).slice(1) || 'stl' })
  }

  const result = await fetchJson<{
    ok: true
    summary: string
    buildId: string
    analysis: AnalysisMeta
    isNew: boolean
    uploads?: { count: number; totalBytes: number; dedupedBytes: number }
    url: string
  }>(`${serverInfo.baseUrl}/__buildviz/push-analysis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      buildId: rawBuildId,
      name,
      displayName: optionString(options, 'display-name', 'displayName'),
      message: normalizeVersionMessage(optionString(options, 'message', 'msg')),
      sourceVersion: optionString(options, 'source-version', 'sourceVersion'),
      sourceBranch: optionString(options, 'source-branch', 'sourceBranch'),
      scene,
      assets: assets.length > 0 ? assets : undefined,
      maxUploadBytes: assets.length > 0 ? maxUploadBytes : undefined,
    }),
  })

  if (options.json) {
    printJson(result)
    return
  }
  console.log(result.summary)
  if (result.analysis.sourceVersion) {
    console.log(`Source: ${result.buildId}@${result.analysis.sourceVersion}`)
  }
  if (result.analysis.message) console.log(`Message: ${result.analysis.message}`)
  if (result.uploads && result.uploads.count > 0) {
    const mb = (bytes: number) => `${(bytes / (1024 * 1024)).toFixed(1)}MB`
    console.log(`Uploaded ${result.uploads.count} asset(s), ${mb(result.uploads.totalBytes)}.`)
  }
  console.log(`View: ${result.url}`)
}

// Detect a NON-hub server listening on a port (used to warn about the stray
// dev server on :5173). Returns true when something answers on the port but its
// /__buildviz/status is not the hub signature.
const isNonHubListening = async (host: string, port: number) => {
  const base = hubBaseUrl(host, port)
  if (await probeHubStatus(base, 800)) return false
  try {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 800)
    const response = await fetch(base, { signal: controller.signal }).finally(() => clearTimeout(timer))
    return response.status > 0
  } catch {
    return false
  }
}

export const printHubStatus = async (args: string[]) => {
  const { options } = parseArgs(args)
  const serverInfo = await readServerInfo()
  const pidFromFile = readHubPid()
  if (!serverInfo) {
    const result = { ok: false, running: false, summary: 'No BuildViz hub discovery file found.', serverInfoPath }
    if (options.json) printJson(result)
    else {
      console.log(result.summary)
      console.log('Start one with: npx buildviz hub --detach')
    }
    return
  }

  // Bounded probe so status never hangs when the hub is dead.
  const status = await probeHubStatus(serverInfo.baseUrl, 3000)
  if (status) {
    // Warn if a non-hub server is also up on the common dev port, the usual
    // source of "wrong server / missing builds" confusion.
    const devPortBusy =
      serverInfo.port !== SERVE_DEFAULT_PORT &&
      (await isNonHubListening('127.0.0.1', SERVE_DEFAULT_PORT))
    if (options.json) {
      printJson({
        ...status,
        running: true,
        canonical: true,
        hubBaseUrl: serverInfo.baseUrl,
        serverInfoPath,
        devServerOnDefaultPort: devPortBusy ? hubBaseUrl('127.0.0.1', SERVE_DEFAULT_PORT) : null,
        pidFile: hubPidPath,
        daemonPid: pidFromFile,
        logPath: hubLogPath,
      })
      return
    }
    const projects = status.projects ?? groupBuildsByProject(status.builds)
    console.log(`BuildViz hub (canonical cross-process target) — verified ${status.service} v${status.version}`)
    if (status.readOnly) {
      console.log(
        'Mode: READ-ONLY (non-loopback bind) — push/pack-export/register/open-path are disabled; ' +
          'view + read only.',
      )
    }
    console.log(`Hub URL: ${serverInfo.baseUrl}  ← open this; it is the ONLY server projects should use`)
    console.log(`(resolved from ${serverInfoPath} — never hardcode a port)`)
    console.log(`PID: ${status.server.pid}${pidFromFile ? ` · daemon pid: ${pidFromFile}` : ''}`)
    console.log(`Logs: ${hubLogPath}`)
    if (devPortBusy) {
      console.log(
        `Warning: a NON-hub server is listening on :${SERVE_DEFAULT_PORT} ` +
          `(${hubBaseUrl('127.0.0.1', SERVE_DEFAULT_PORT)}). That is a project Vite dev server, ` +
          'not the hub — do not push to it or open it expecting hub builds.',
      )
    } else {
      console.log(`A project may also run its own Vite dev server (npm run dev, default :${SERVE_DEFAULT_PORT}); that is local-only and never the hub.`)
    }
    console.log(`Projects: ${projects.length} · Builds: ${status.builds.length}`)
    projects.forEach((project) => {
      console.log(`▸ ${project.id}`)
      project.builds.forEach((build) => {
        const versions = build.versions
          .map((entry) => (entry.isDefault ? `${entry.name} (default)` : entry.name))
          .join(', ')
        console.log(`  - ${build.build}: ${build.name ?? build.build}${versions ? ` — ${versions}` : ''}`)
      })
    })
    return
  }

  const result = {
    ok: false,
    running: false,
    summary: `Found ${serverInfoPath}, but no verified ${HUB_SERVICE} is responding there (stale discovery, or a non-hub server is on the port).`,
    server: serverInfo,
  }
  if (options.json) printJson(result)
  else {
    console.log(result.summary)
    console.log(`Last known URL: ${serverInfo.baseUrl}`)
    console.log('Start one with: npx buildviz hub --detach (or clear it with: npx buildviz hub stop)')
  }
}
