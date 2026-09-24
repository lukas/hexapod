import { existsSync } from 'node:fs'
import { readFile, readdir, stat } from 'node:fs/promises'
import path from 'node:path'

// The project/build/version data model (types + pure helpers) lives in the
// node-free `core/buildModel.ts` so the browser viewer and this CLI-side
// enumeration share one source of truth. This module adds only the on-disk
// (Node fs) enumeration on top of that model.
import {
  type BuildBranchEntry,
  type BuildMeta,
  type BuildsIndex,
  type BuildsIndexBuild,
  type BuildVersionEntry,
  type CacheVersionMeta,
  buildsIndexFrom,
  compareVersionNames,
  resolveBranchDefaultVersion,
  resolveDefaultBranch,
  resolveDefaultVersion,
  splitProjectBuild,
} from '../core/buildModel'

export {
  DEFAULT_BRANCH_NAME,
  DEFAULT_VERSION_NAME,
  buildsIndexFrom,
  canonicalizeBranchName,
  canonicalizeVersionName,
  compareVersionNames,
  disambiguateBranchRef,
  groupBuildsByProject,
  nextBumpVersion,
  normalizeVersionMessage,
  parseBuildAddress,
  resolveBranchDefaultVersion,
  resolveDefaultBranch,
  resolveDefaultVersion,
  selectVersionsToPrune,
  splitProjectBuild,
} from '../core/buildModel'
export type {
  BuildBranchEntry,
  BuildMeta,
  BuildVersionEntry,
  BuildsIndex,
  BuildsIndexBuild,
  BuildsIndexProject,
  CacheBranchMeta,
  CacheVersionMeta,
} from '../core/buildModel'

// A branch's on-disk root: the default branch lives at the build root (the
// pre-branch layout); every other branch under branches/<name>/.
export const branchRootDir = (buildDir: string, branch: string, defaultBranch: string) =>
  branch === defaultBranch ? buildDir : path.join(buildDir, 'branches', branch)

// Names of the branch directories that actually carry content (a scene.json or
// a versions/<name> snapshot).
export const listBranchDirs = async (buildDir: string) => {
  const branchesDir = path.join(buildDir, 'branches')
  if (!existsSync(branchesDir)) return []
  const entries = await readdir(branchesDir, { withFileTypes: true })
  const names: string[] = []
  for (const entry of entries) {
    if (!entry.isDirectory()) continue
    const dir = path.join(branchesDir, entry.name)
    if (existsSync(path.join(dir, 'scene.json')) || (await listVersionDirs(dir)).length > 0) {
      names.push(entry.name)
    }
  }
  return names.sort(compareVersionNames)
}

export const readSceneName = async (scenePath: string) => {
  try {
    const manifest = JSON.parse(await readFile(scenePath, 'utf8')) as { name?: string }
    return typeof manifest.name === 'string' ? manifest.name : null
  } catch {
    return null
  }
}

export const readBuildMeta = async (buildDir: string): Promise<BuildMeta | null> => {
  const metaPath = path.join(buildDir, 'meta.json')
  if (!existsSync(metaPath)) return null
  try {
    return JSON.parse(await readFile(metaPath, 'utf8')) as BuildMeta
  } catch {
    return null
  }
}

// Names of the version directories that actually carry a scene.json.
export const listVersionDirs = async (buildDir: string) => {
  const versionsDir = path.join(buildDir, 'versions')
  if (!existsSync(versionsDir)) return []

  const entries = await readdir(versionsDir, { withFileTypes: true })
  return entries
    .filter(
      (entry) =>
        entry.isDirectory() && existsSync(path.join(versionsDir, entry.name, 'scene.json')),
    )
    .map((entry) => entry.name)
    .sort(compareVersionNames)
}

// Back-compat alias: older call sites import listBuildVersions.
export const listBuildVersions = listVersionDirs

// Filesystem FALLBACK for a version's "last updated" time when meta.json carries
// no explicit pushedAt for it (static/on-disk builds, demo builds, `register`ed
// project dirs with no meta, or a versions/<name> snapshot not listed in meta).
// The mtime of that version's scene.json is the best available signal: a
// non-default version lives at versions/<name>/scene.json, while the DEFAULT
// version may only exist mirrored at the build-root scene.json (no
// versions/<default> dir materialized), so the root scene is tried as a
// fallback. Returns an ISO string, or null only when no scene file exists.
export const versionSceneMtime = async (
  buildDir: string,
  name: string,
  isDefault: boolean,
): Promise<string | null> => {
  const candidates = [path.join(buildDir, 'versions', name, 'scene.json')]
  if (isDefault) candidates.push(path.join(buildDir, 'scene.json'))
  for (const candidate of candidates) {
    try {
      const info = await stat(candidate)
      if (info.isFile()) return info.mtime.toISOString()
    } catch {
      // Missing/unreadable candidate: fall through to the next one.
    }
  }
  return null
}

// Produce the ordered, default-flagged version list for a build. The default
// version always appears (it is mirrored at the build root scene.json even when
// no versions/<default> directory exists yet), followed by the other named
// branches. The default is listed first.
export const describeBuildVersions = async (
  buildDir: string,
  defaultVersion: string,
  versionMeta?: CacheVersionMeta[],
): Promise<BuildVersionEntry[]> => {
  const dirs = await listVersionDirs(buildDir)
  const hasRootScene = existsSync(path.join(buildDir, 'scene.json'))
  const names = new Set(dirs)
  if (hasRootScene) names.add(defaultVersion)
  if (names.size === 0) return []
  // Map each version name to its last push/update time from meta (when present),
  // so the index can surface a "last updated" timestamp per version. The
  // optional per-version changelog message rides alongside it.
  const pushedAtByName = new Map<string, string>()
  const messageByName = new Map<string, string>()
  for (const entry of versionMeta ?? []) {
    const name = entry.name ?? (entry as unknown as { version?: string }).version
    if (name && entry.pushedAt) pushedAtByName.set(name, entry.pushedAt)
    if (name && typeof entry.message === 'string' && entry.message.length > 0) {
      messageByName.set(name, entry.message)
    }
  }
  const ordered = [
    defaultVersion,
    ...[...names].filter((name) => name !== defaultVersion).sort(compareVersionNames),
  ].filter((name, index, all) => all.indexOf(name) === index && names.has(name))
  // Prefer the explicit meta.json pushedAt; otherwise fall back to the version
  // scene.json's mtime so EVERY version surfaces a "last updated" time. Only the
  // truly-impossible case (no scene file at all) yields null.
  return Promise.all(
    ordered.map(async (name) => {
      const isDefault = name === defaultVersion
      const pushedAt =
        pushedAtByName.get(name) ?? (await versionSceneMtime(buildDir, name, isDefault))
      const message = messageByName.get(name)
      const provenance = versionMeta?.find((entry) => entry.name === name)
      return { name, isDefault, pushedAt: pushedAt ?? null, ...(message ? { message } : {}),
        ...(provenance?.reason ? { reason: provenance.reason } : {}),
        ...(provenance?.messageSource ? { messageSource: provenance.messageSource } : {}),
        ...(provenance?.messageUpdatedAt ? { messageUpdatedAt: provenance.messageUpdatedAt } : {}),
      }
    }),
  )
}

// Produce the full branch tree for a build: the default branch (rooted at the
// build dir, described by the top-level meta fields) plus every branches/<name>
// directory (described by its meta.branches record when present).
export const describeBuildBranches = async (
  buildDir: string,
  meta: BuildMeta | null,
): Promise<BuildBranchEntry[]> => {
  const defaultBranch = resolveDefaultBranch(meta)
  const defaultVersion = resolveDefaultVersion(meta)
  const branches: BuildBranchEntry[] = [
    {
      name: defaultBranch,
      isDefault: true,
      defaultVersion,
      versions: await describeBuildVersions(buildDir, defaultVersion, meta?.versions),
    },
  ]
  const onDisk = await listBranchDirs(buildDir)
  const recorded = (meta?.branches ?? []).map((entry) => entry.name)
  const names = [...new Set([...onDisk, ...recorded])]
    .filter((name) => name !== defaultBranch)
    .sort(compareVersionNames)
  for (const name of names) {
    const dir = branchRootDir(buildDir, name, defaultBranch)
    if (!existsSync(dir)) continue
    const branchMeta = meta?.branches?.find((entry) => entry.name === name)
    const branchDefault = resolveBranchDefaultVersion(meta, name)
    const versions = await describeBuildVersions(dir, branchDefault, branchMeta?.versions)
    if (versions.length === 0) continue
    branches.push({ name, isDefault: false, defaultVersion: branchDefault, versions })
  }
  return branches
}

const describeBuild = async (buildDir: string, id: string): Promise<BuildsIndexBuild> => {
  const { project, build } = splitProjectBuild(id)
  const meta = await readBuildMeta(buildDir)
  const defaultVersion = resolveDefaultVersion(meta)
  const scenePath = path.join(buildDir, 'scene.json')
  const name = meta?.name ?? (existsSync(scenePath) ? await readSceneName(scenePath) : null)
  const branches = await describeBuildBranches(buildDir, meta)
  const defaultBranch = resolveDefaultBranch(meta)
  return {
    id,
    project,
    build,
    name,
    defaultVersion,
    // Mirror of the default branch's versions (back-compat for old readers).
    versions: branches.find((entry) => entry.isDefault)?.versions ?? [],
    defaultBranch,
    branches,
  }
}

// Enumerate builds under a builds root into the hierarchical index. Build ids
// may contain "/" (project/build, or deeper), so directories are walked
// recursively: a directory is a build when it has a scene.json or a
// versions/<name> snapshot, and we keep descending into other subdirectories
// (but never into versions/ or branches/, which belong to the build itself) so
// a project directory can also hold child builds.
export const enumerateBuilds = async (buildsRoot: string): Promise<BuildsIndex> => {
  if (!existsSync(buildsRoot)) return buildsIndexFrom([])

  const ids: string[] = []
  const dirById = new Map<string, string>()

  const visit = async (dir: string, idPrefix: string) => {
    if (idPrefix) {
      const scenePath = path.join(dir, 'scene.json')
      const versions = await listVersionDirs(dir)
      if (existsSync(scenePath) || versions.length > 0) {
        ids.push(idPrefix)
        dirById.set(idPrefix, dir)
      }
    }

    const entries = await readdir(dir, { withFileTypes: true })
    await Promise.all(
      entries
        .filter(
          (entry) => entry.isDirectory() && entry.name !== 'versions' && entry.name !== 'branches',
        )
        .map((entry) =>
          visit(path.join(dir, entry.name), idPrefix ? `${idPrefix}/${entry.name}` : entry.name),
        ),
    )
  }

  await visit(buildsRoot, '')

  const builds = await Promise.all(ids.map((id) => describeBuild(dirById.get(id)!, id)))
  return buildsIndexFrom(builds)
}
