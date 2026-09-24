// Build loading + shared result plumbing, HUB layer (see plans/repo-split.md).
//
// These used to live in cli/cliBuild.ts, but they are not CLI-specific: the
// hub's MCP server needs to load builds from the cache, resolve their asset
// bytes, and wrap results in the same JSON envelope the CLI prints. Moving
// them here keeps the dependency edges legal (hub -> checks/core only; the
// CLI re-exports these so command modules are unchanged).
import { existsSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import type { BuildMesh, BuildSceneManifest } from '../core/buildScene'
import { createBuildIndex } from '../core/buildvizCore'
import {
  branchRootDir,
  describeBuildVersions,
  disambiguateBranchRef,
  listBranchDirs,
  parseBuildAddress,
  readBuildMeta,
  resolveBranchDefaultVersion,
  resolveDefaultBranch,
  splitProjectBuild,
} from './buildsIndex'
import { canonicalizeBuildId, readJson } from './cliShared'
import {
  ASSET_STORE_ID,
  assetStoreDir,
  buildIdForDir,
  cacheBuildDir,
} from './hub'

export const resolveBuildDir = (buildDir: string) => {
  const resolved = path.resolve(process.cwd(), buildDir)
  // Allow read commands (versions, diff, inspect, ...) to target a hub-managed
  // build by its id when no matching local directory exists, e.g.
  // `buildviz versions pushed-demo` resolves to ~/.buildviz/cache/pushed-demo.
  if (!existsSync(resolved)) {
    // Try the literal id first, then its canonical slug so a human id like
    // "Hexapod STS" resolves to ~/.buildviz/cache/hexapod-sts the same way push
    // stored it. This keeps `buildviz versions "Hexapod STS"` and
    // `buildviz diff "Hexapod STS" v1 v2` working with the friendly id.
    const candidates = [buildDir, canonicalizeBuildId(buildDir)]
    for (const candidate of candidates) {
      if (!candidate) continue
      const cacheCandidate = cacheBuildDir(candidate)
      if (existsSync(path.join(cacheCandidate, 'scene.json')) || existsSync(path.join(cacheCandidate, 'versions'))) {
        return cacheCandidate
      }
    }
  }
  return resolved
}

export const loadBuild = async (buildDirArg: string, version?: string, branch?: string) => {
  // Accept a `project/build[@branch][@version]` address; explicit --version /
  // --branch options win over any @refs in the argument. The one-ref form
  // (`build@x`) is ambiguous between a branch and a version on the default
  // branch, so it is disambiguated against the build's known branch names.
  const address = parseBuildAddress(buildDirArg)
  const baseDir = resolveBuildDir(address.buildId)
  const meta = await readBuildMeta(baseDir)
  const defaultBranch = resolveDefaultBranch(meta)

  const branchNames = new Set<string>([
    defaultBranch,
    ...(meta?.branches ?? []).map((entry) => entry.name),
    ...(await listBranchDirs(baseDir)),
  ])
  let requestedBranch: string | undefined = branch ?? address.branch ?? undefined
  let requestedVersion: string | null | undefined = version ?? address.version
  if (!requestedBranch && address.version) {
    // `@x` with no explicit branch: a ref naming a branch means that branch
    // (its default version, unless --version also given); otherwise it stays a
    // version on the default branch.
    const resolvedRef = disambiguateBranchRef(address.version, branchNames)
    if (resolvedRef.branch) {
      requestedBranch = resolvedRef.branch
      requestedVersion = version ?? null
    }
  }

  const resolvedBranch = requestedBranch ?? defaultBranch
  const branchDir = branchRootDir(baseDir, resolvedBranch, defaultBranch)
  if (!existsSync(branchDir)) {
    throw new Error(
      `No branch "${resolvedBranch}" for build ${buildIdForDir(baseDir)}. ` +
        `Known branches: ${[...branchNames].join(', ')}.`,
    )
  }
  const branchDefaultVersion = resolveBranchDefaultVersion(meta, resolvedBranch)

  // The branch's default version (its name, "latest", or omitted) lives at the
  // branch root scene.json; any other named version under versions/<name>/.
  const isDefault =
    !requestedVersion || requestedVersion === 'latest' || requestedVersion === branchDefaultVersion
  let buildDir = branchDir
  let resolvedVersion = branchDefaultVersion
  // An explicitly named revision prefers its snapshot even while it is also
  // the default. A registered source's live root may be regenerated outside
  // the hub; exact revision reads must not silently follow that working copy.
  if (requestedVersion && requestedVersion !== 'latest') {
    const snapshotDir = path.join(branchDir, 'versions', requestedVersion)
    if (existsSync(path.join(snapshotDir, 'scene.json'))) buildDir = snapshotDir
  }
  if (!isDefault) {
    const candidate = path.join(branchDir, 'versions', requestedVersion as string)
    if (!existsSync(path.join(candidate, 'scene.json'))) {
      const known = await describeBuildVersions(branchDir, branchDefaultVersion)
      const where =
        resolvedBranch === defaultBranch ? '' : ` on branch "${resolvedBranch}"`
      throw new Error(
        `No version "${requestedVersion}"${where} for build ${buildIdForDir(baseDir)}. ` +
          `Known versions: ${known.map((entry) => entry.name).join(', ') || '(none)'}.`,
      )
    }
    buildDir = candidate
    resolvedVersion = requestedVersion as string
  }

  const scenePath = path.join(buildDir, 'scene.json')
  const versionDesignSpecPath = path.join(buildDir, 'design_spec.yaml')
  const branchDesignSpecPath = path.join(branchDir, 'design_spec.yaml')
  const designSpecPath = existsSync(versionDesignSpecPath)
    ? versionDesignSpecPath
    : existsSync(branchDesignSpecPath)
      ? branchDesignSpecPath
      : path.join(baseDir, 'design_spec.yaml')

  if (!existsSync(scenePath)) {
    throw new Error(`Missing scene manifest: ${scenePath}`)
  }

  const manifest = await readJson<BuildSceneManifest>(scenePath)
  const designSpecText = existsSync(designSpecPath)
    ? await readFile(designSpecPath, 'utf8')
    : null

  return {
    baseDir,
    buildDir,
    branchDir,
    buildId: buildIdForDir(baseDir),
    branch: resolvedBranch,
    defaultBranch,
    isDefaultBranch: resolvedBranch === defaultBranch,
    version: resolvedVersion,
    defaultVersion: branchDefaultVersion,
    isDefaultVersion: isDefault,
    designSpecPath: existsSync(designSpecPath) ? designSpecPath : null,
    index: createBuildIndex(manifest, designSpecText),
  }
}

export const resolveAssetPath = (build: Awaited<ReturnType<typeof loadBuild>>, assetUrl: string | undefined) => {
  if (!assetUrl) return build.buildDir
  // Content-addressed assets uploaded via `push` are served from the shared
  // store at /builds/_assets/<hash>.<ext>; resolve them to that store so local
  // geometry commands (check/bom/identify/mesh) find the bytes for cached builds.
  const assetStorePrefix = `/builds/${ASSET_STORE_ID}/`
  if (assetUrl.startsWith(assetStorePrefix)) {
    return path.join(assetStoreDir, assetUrl.slice(assetStorePrefix.length))
  }
  const publicPrefix = `/builds/${build.buildId}/`
  if (assetUrl.startsWith(publicPrefix)) {
    // Absolute /builds/<id>/ URLs are rooted at the base build directory so
    // version manifests can reference the parent build's mesh assets.
    return path.join(build.baseDir, assetUrl.slice(publicPrefix.length))
  }
  return path.resolve(build.buildDir, assetUrl.replace(/^\.\//, '').replace(/^\//, ''))
}

export const apiEnvelope = (
  ok: boolean,
  build: Awaited<ReturnType<typeof loadBuild>>,
  summary: string,
  results: unknown,
  warnings: unknown[] = [],
  errors: unknown[] = [],
) => ({
  ok,
  build: {
    id: build.buildId,
    buildId: build.buildId,
    version: build.version,
    name: build.index.manifest.name,
    units: build.index.manifest.units,
    path: path.relative(process.cwd(), build.buildDir) || build.buildDir,
  },
  summary,
  results,
  warnings,
  errors,
})

export const parseNumberOption = (value: string | undefined, label: string) => {
  if (value === undefined) return undefined
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 0) {
    throw new Error(`Invalid ${label}: ${value}`)
  }
  return parsed
}

export const makeLoadMesh =
  (build: Awaited<ReturnType<typeof loadBuild>>) => async (mesh: BuildMesh): Promise<ArrayBuffer | null> => {
    const assetPath = resolveAssetPath(build, mesh.url)
    if (!mesh.url || !existsSync(assetPath)) return null
    const buffer = await readFile(assetPath)
    return buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength) as ArrayBuffer
  }

export const viewerDesignSpecUrl = (build: Awaited<ReturnType<typeof loadBuild>>) =>
  build.buildDir !== build.branchDir && existsSync(path.join(build.buildDir, 'design_spec.yaml'))
    ? `/builds/${build.buildId}/versions/${build.version}/design_spec.yaml`
    : `/builds/${build.buildId}/design_spec.yaml`

export const buildViewerUrl = (
  build: Awaited<ReturnType<typeof loadBuild>>,
  baseUrl: string,
  params: Record<string, string | undefined>,
) => {
  const url = new URL(baseUrl)
  const { project, build: buildName } = splitProjectBuild(build.buildId)
  url.searchParams.set('project', project)
  url.searchParams.set('build', buildName)
  if (!build.isDefaultVersion) url.searchParams.set('version', build.version)
  url.searchParams.set('designSpec', viewerDesignSpecUrl(build))
  Object.entries(params).forEach(([key, value]) => {
    if (value) url.searchParams.set(key, value)
  })
  return url.toString()
}
