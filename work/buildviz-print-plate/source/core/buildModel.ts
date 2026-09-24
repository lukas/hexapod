// ---------------------------------------------------------------------------
// Shared data model: PROJECT -> BUILD (assembly) -> NAMED, BRANCH-LIKE VERSION
//
// This module is the single source of truth for the project/build/version
// types and the PURE helpers that operate on them (no Node or DOM
// dependencies), so the browser viewer (`src/`), the CLI, and the build-index
// enumeration (`hub/buildsIndex.ts`) all agree on one shape.
//
// A build's stable id is a "/"-separated slug path whose FIRST segment is the
// PROJECT and whose remaining segments name the BUILD (assembly) within that
// project, e.g. "spider/chassis". A single-segment id like "hexapod-prototype"
// is a project with one same-named build. Versions are NAMED branches stored at
// <build>/versions/<name>/scene.json; one is the default (mirrored at the build
// root scene.json). The canonical human address is `project/build@version`
// (e.g. "spider/chassis@with-dome").
// ---------------------------------------------------------------------------

// New builds default their first/working version to "main"; "latest" is always
// accepted as an alias for whatever the default version is.
export const DEFAULT_VERSION_NAME = 'main'

// A build's versions are grouped into BRANCHES (like git branches): each branch
// carries its own named-version history and its own default version. The
// default branch ("main" unless meta says otherwise) lives at the build root —
// exactly the pre-branch layout, so branch-less builds are simply builds whose
// only branch is the default. Other branches live under branches/<name>/ with
// the same internal layout (scene.json = branch default, versions/<v>/...).
export const DEFAULT_BRANCH_NAME = 'main'

export type BuildVersionEntry = {
  name: string
  isDefault: boolean
  // ISO timestamp of when this version was last pushed/updated. Sourced from the
  // build's meta.json when present, otherwise filled from the version
  // scene.json's filesystem mtime (see versionSceneMtime) so static/on-disk and
  // demo builds still surface a "last updated" time. Null only in the
  // truly-impossible case where no scene file exists for the version.
  pushedAt?: string | null
  // Optional changelog / commit note describing what changed in this version,
  // set at publish time via `push`/`freeze --message`. Additive and
  // backward-compatible: omitted entirely for versions published without one.
  reason?: string
  message?: string
  messageSource?: 'retrospective'
  messageUpdatedAt?: string
}

// One branch of a build in the index: its own default version + version list.
export type BuildBranchEntry = {
  name: string
  isDefault: boolean
  defaultVersion: string
  versions: BuildVersionEntry[]
}

export type BuildsIndexBuild = {
  // Full slug path used everywhere (cache dir, ?build=, asset URLs).
  id: string
  // First id segment.
  project: string
  // Remaining id segments (the assembly name within the project).
  build: string
  name: string | null
  // Default-branch mirror (back-compat): defaultVersion/versions always
  // describe the DEFAULT branch so older consumers keep working unchanged.
  defaultVersion: string
  versions: BuildVersionEntry[]
  // Branch tree (additive; absent for older indexes = single default branch).
  defaultBranch?: string
  branches?: BuildBranchEntry[]
}

export type BuildsIndexProject = {
  id: string
  name: string
  builds: BuildsIndexBuild[]
}

export type BuildsIndex = {
  // Bumped when the shape changes so readers can branch; the viewer also
  // tolerates the absence of `projects` for older callers.
  schema: 2
  projects: BuildsIndexProject[]
  // Flat list of every build (each appears once). Retained for simple tooling
  // and for viewers that walk a flat list.
  builds: BuildsIndexBuild[]
}

export type CacheVersionMeta = {
  name: string
  pushedAt: string
  // Optional changelog / commit note for this version (see BuildVersionEntry.message).
  // Stored in the per-version meta.json records; absent when none was supplied.
  reason?: string
  message?: string
  messageSource?: 'retrospective'
  messageUpdatedAt?: string
}

// Per-branch record in a build's meta.json: the branch's own default version
// and version history. The default branch's records are ALSO mirrored in the
// top-level defaultVersion/versions fields for back-compat readers.
export type CacheBranchMeta = {
  name: string
  defaultVersion?: string
  versions: CacheVersionMeta[]
}

// On-disk meta written next to a build (cache builds always have it; on-disk
// project builds may have one after `buildviz migrate`). `latestVersion` is the
// legacy field kept for back-compat reads.
export type BuildMeta = {
  schema?: number
  buildId: string
  project?: string
  build?: string
  name: string | null
  createdAt: string
  updatedAt: string
  defaultVersion?: string
  latestVersion?: string
  versions: CacheVersionMeta[]
  // Branch bookkeeping (additive): absent means "one default branch".
  defaultBranch?: string
  branches?: CacheBranchMeta[]
}

// Split a build id into its project (first segment) and build (the rest). A
// single-segment id is a project whose build shares its name.
export const splitProjectBuild = (buildId: string): { project: string; build: string } => {
  const segments = buildId.split('/').filter(Boolean)
  if (segments.length === 0) return { project: buildId, build: buildId }
  if (segments.length === 1) return { project: segments[0], build: segments[0] }
  return { project: segments[0], build: segments.slice(1).join('/') }
}

// Inverse of `splitProjectBuild`: rebuild a stable id from its project and build
// parts. A single-segment id splits to `project === build`, so re-joining must
// collapse that case back to one segment (otherwise "spider" round-trips to
// "spider/spider"); a genuinely nested id keeps every segment.
export const joinProjectBuild = (project: string, build: string): string =>
  project === build ? project : `${project}/${build}`

// Parse a `project/build[@ref[@ref]]` address. The explicit two-ref form is
// `project/build@branch@version`. The one-ref form `project/build@x` is
// AMBIGUOUS between a branch and a version on the default branch: it is
// returned as `version` with branch null, and consumers that know the build's
// branch list (loadBuild, the hub) reinterpret it as a branch when `x` names
// one (see disambiguateBranchRef). "@" never appears in a canonical id
// (canonicalizeBuildId slugifies it away), so the split is unambiguous.
export const parseBuildAddress = (
  raw: string,
): { buildId: string; branch: string | null; version: string | null } => {
  const firstAt = raw.indexOf('@')
  if (firstAt <= 0) return { buildId: raw, branch: null, version: null }
  const buildId = raw.slice(0, firstAt)
  const refs = raw
    .slice(firstAt + 1)
    .split('@')
    .map((ref) => ref.trim())
    .filter((ref) => ref.length > 0)
  if (refs.length === 0) return { buildId, branch: null, version: null }
  if (refs.length === 1) return { buildId, branch: null, version: refs[0] }
  return { buildId, branch: refs[0], version: refs[1] }
}

// Resolve the one-ref `@x` ambiguity against a build's known branch names: a
// ref that names a branch means "that branch's default version"; anything else
// stays a version on the default branch.
export const disambiguateBranchRef = (
  ref: string | null,
  branchNames: Iterable<string>,
): { branch: string | null; version: string | null } => {
  if (!ref) return { branch: null, version: null }
  for (const name of branchNames) {
    if (name === ref) return { branch: ref, version: null }
  }
  return { branch: null, version: ref }
}

// Order version names so numeric suffixes sort numerically (v2 before v10), the
// default-ish names ("main", "latest") float to the front, and arbitrary names
// fall back to a stable locale order.
export const compareVersionNames = (a: string, b: string) => {
  const rank = (name: string) => (name === 'main' ? 0 : name === 'latest' ? 1 : 2)
  const rankDelta = rank(a) - rank(b)
  if (rankDelta !== 0) return rankDelta
  const matchA = a.match(/^v(\d+)$/)
  const matchB = b.match(/^v(\d+)$/)
  if (matchA && matchB) return Number(matchA[1]) - Number(matchB[1])
  return a.localeCompare(b, undefined, { numeric: true })
}

// Pick the next free auto-incrementing "v<N>" version name given the existing
// names, using the SAME v(\d+) ordering as compareVersionNames: existing v1,v2
// yield v3; no numeric versions yet yields v1. Non-"v<N>" names (main, latest,
// with-dome, ...) are ignored, so `--bump` always lands on a fresh numeric slot
// that sorts after every existing numeric version.
export const nextBumpVersion = (existing: Iterable<string>): string => {
  let max = 0
  for (const name of existing) {
    const match = /^v(\d+)$/.exec(name)
    if (match) max = Math.max(max, Number(match[1]))
  }
  return `v${max + 1}`
}

// Decide which versions to KEEP vs PRUNE for a per-build retention cap. The
// default version is ALWAYS kept; beyond that the NEWEST (by pushedAt) versions
// are kept until `keepVersions` remain, and the rest (oldest first) are pruned.
// A cap of undefined/<=0 keeps everything. This is the pure selection shared by
// the hub cache (`push --keep`) and on-disk `freeze --keep`; callers do the fs
// removal of the returned `pruned` directories themselves.
export const selectVersionsToPrune = (
  entries: { name: string; pushedAt?: string }[],
  keepVersions: number | undefined,
  defaultVersion: string,
): { keep: string[]; pruned: string[] } => {
  if (!keepVersions || keepVersions <= 0 || entries.length <= keepVersions) {
    return { keep: entries.map((entry) => entry.name), pruned: [] }
  }
  const byNewest = [...entries].sort((a, b) => (b.pushedAt ?? '').localeCompare(a.pushedAt ?? ''))
  const keep = new Set<string>([defaultVersion])
  for (const entry of byNewest) {
    if (keep.size >= keepVersions) break
    keep.add(entry.name)
  }
  return {
    keep: entries.filter((entry) => keep.has(entry.name)).map((entry) => entry.name),
    pruned: entries.filter((entry) => !keep.has(entry.name)).map((entry) => entry.name),
  }
}

// Version names are single-segment slugs (no "/"). Branch-friendly characters
// (letters, numbers, dots, underscores, dashes) are kept; everything else is
// collapsed to a dash so "With Dome!" becomes "with-dome".
export const canonicalizeVersionName = (raw: string) =>
  raw
    .normalize('NFKD')
    .toLowerCase()
    .replaceAll(/[^a-z0-9._-]+/g, '-')
    .replaceAll(/-+/g, '-')
    .replace(/^[-]+|[-]+$/g, '')

// Maximum stored length for a version's changelog message. Long notes are
// truncated (with an ellipsis) so a stray multi-KB blob can't bloat meta.json /
// the index; the viewer further truncates/tooltips for display.
export const MAX_VERSION_MESSAGE_LENGTH = 500

// Normalize a user-supplied changelog/commit message for a version: collapse
// surrounding whitespace and cap the length, returning undefined for an
// empty/whitespace-only/absent value so "no message" stays truly absent
// (additive + backward-compatible). Interior newlines are preserved so a commit
// body survives; the viewer decides how to render them.
export const normalizeVersionMessage = (raw: unknown): string | undefined => {
  if (typeof raw !== 'string') return undefined
  const trimmed = raw.trim()
  if (trimmed.length === 0) return undefined
  return trimmed.length > MAX_VERSION_MESSAGE_LENGTH
    ? `${trimmed.slice(0, MAX_VERSION_MESSAGE_LENGTH - 1).trimEnd()}…`
    : trimmed
}

// The default version is whatever meta records (new `defaultVersion`, then the
// legacy `latestVersion`), falling back to "main".
export const resolveDefaultVersion = (
  meta: Pick<BuildMeta, 'defaultVersion' | 'latestVersion'> | null,
) => meta?.defaultVersion ?? meta?.latestVersion ?? DEFAULT_VERSION_NAME

// The default branch is whatever meta records, falling back to "main". A build
// with no branch bookkeeping is a single-default-branch build.
export const resolveDefaultBranch = (meta: Pick<BuildMeta, 'defaultBranch'> | null) =>
  meta?.defaultBranch ?? DEFAULT_BRANCH_NAME

// A branch's default version: its own meta record first; for the default
// branch fall back to the top-level default; otherwise "main".
export const resolveBranchDefaultVersion = (
  meta: BuildMeta | null,
  branch: string,
): string => {
  const record = meta?.branches?.find((entry) => entry.name === branch)
  if (record?.defaultVersion) return record.defaultVersion
  if (branch === resolveDefaultBranch(meta)) return resolveDefaultVersion(meta)
  return DEFAULT_VERSION_NAME
}

// Branch names use the same slug rules as version names.
export const canonicalizeBranchName = canonicalizeVersionName

// Group flat build entries into projects (keyed by the first id segment).
export const groupBuildsByProject = (builds: BuildsIndexBuild[]): BuildsIndexProject[] => {
  const byProject = new Map<string, BuildsIndexBuild[]>()
  for (const build of builds) {
    const list = byProject.get(build.project) ?? []
    list.push(build)
    byProject.set(build.project, list)
  }
  return [...byProject.entries()]
    .map(([id, projectBuilds]) => ({
      id,
      name: id,
      builds: projectBuilds.sort((a, b) => a.id.localeCompare(b.id)),
    }))
    .sort((a, b) => a.id.localeCompare(b.id))
}

export const buildsIndexFrom = (builds: BuildsIndexBuild[]): BuildsIndex => {
  const sorted = [...builds].sort((a, b) => a.id.localeCompare(b.id))
  return {
    schema: 2,
    projects: groupBuildsByProject(sorted),
    builds: sorted,
  }
}
