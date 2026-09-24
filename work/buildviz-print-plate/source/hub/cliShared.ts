// ---------------------------------------------------------------------------
// Shared CLI primitives used by BOTH the command layer (cli/buildviz.ts)
// and the hub/server/daemon layer (hub/hub.ts): argument parsing, build-id
// canonicalization/validation, project/build resolution, and build-directory
// discovery. These are pure-ish helpers (Node fs/child_process at most, no hub
// state, no server logic), so factoring them here keeps buildviz.ts and hub.ts
// free of a circular import while sharing one source of truth.
// ---------------------------------------------------------------------------
import { spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { splitProjectBuild } from '../core/buildModel'

export type CliOptions = Record<string, string | boolean>

export const printJson = (value: unknown) => {
  console.log(JSON.stringify(value, null, 2))
}

// Repository root (one directory up from scripts/). Shared so the CLI and the
// hub resolve the same Vite project root, package.json, and public/builds path.
export const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

// The single ~/.buildviz directory every layer reads/writes (discovery file,
// registry, version cache, hub log, usage log). It lives here — the cycle-free
// shared module both hub.ts and usageLog.ts import — so there is exactly one
// source of truth and no hub <-> usageLog import cycle.
// Optional isolated data root for embedded hubs and integration tests.
export const buildvizHome = process.env.BUILDVIZ_HOME
  ? path.resolve(process.env.BUILDVIZ_HOME)
  : path.join(os.homedir(), '.buildviz')

// Single-dash short flags map to their long-flag (option) name. Only flags
// listed here are recognized as options; any other "-foo" token stays a
// positional, preserving prior behavior. "-m" is the changelog message alias
// shared by `push`/`freeze`.
const SHORT_FLAG_ALIASES: Record<string, string> = { m: 'message' }

// A token begins a NEW flag (so it can never be consumed as the previous flag's
// value): any "--long" option, or a recognized short alias like "-m". A bare
// "-5"/"-x" that is NOT a known alias is left as a potential value/positional so
// negative-number values and existing behavior are preserved.
const flagNameFor = (token: string): string | null => {
  if (token.startsWith('--')) return token.slice(2)
  if (token.length > 1 && token.startsWith('-') && SHORT_FLAG_ALIASES[token.slice(1)] !== undefined) {
    return SHORT_FLAG_ALIASES[token.slice(1)]
  }
  return null
}

export const parseArgs = (args: string[]) => {
  const positional: string[] = []
  const options: CliOptions = {}

  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index]
    const key = flagNameFor(arg)

    if (key === null) {
      positional.push(arg)
      continue
    }

    // A flag takes the next token as its value unless that token is itself a
    // flag (a boolean flag like --bump must not swallow a following -m/--other).
    const next = args[index + 1]
    if (next === undefined || flagNameFor(next) !== null) {
      options[key] = true
    } else {
      options[key] = next
      index += 1
    }
  }

  return { positional, options }
}

export const optionString = (options: CliOptions, ...names: string[]) => {
  for (const name of names) {
    const value = options[name]
    if (typeof value === 'string') return value
  }
  return undefined
}

export const readJson = async <T>(filePath: string) =>
  JSON.parse(await readFile(filePath, 'utf8')) as T

export const isAbsoluteWebUrl = (value: string) => /^[a-z][a-z0-9+.-]*:/i.test(value)

// Canonicalize a (possibly human-friendly) build id into the single stable form
// used EVERYWHERE: the cache directory name, the registry key, the index.json
// id, and the ?build= URL param. A human label like "Hexapod STS" becomes the
// slug "hexapod-sts" so that every update resolves to the same build entry and
// accumulates versions instead of failing validation (or worse, overwriting a
// differently-cased/spaced path). "/" is preserved as the hierarchy separator
// and each segment is slugified independently. The human name is kept separately
// (scene.name / --name) so the menu still shows "Hexapod STS".
export const canonicalizeBuildId = (raw: string) =>
  raw
    .split('/')
    .map((segment) =>
      segment
        .normalize('NFKD')
        .toLowerCase()
        .replaceAll(/[^a-z0-9._-]+/g, '-')
        .replaceAll(/-+/g, '-')
        .replace(/^[-]+|[-]+$/g, ''),
    )
    .filter((segment) => segment.length > 0)
    .join('/')

export const buildIdFromDir = (buildDir: string) =>
  canonicalizeBuildId(path.basename(buildDir)) || 'local-build'

// Compose a "<project>/<build>" build id from project + build slugs. Either may
// itself already be a "/"-path; the result is canonicalized to the stable slug.
export const composeBuildId = (project: string, build: string) =>
  canonicalizeBuildId([project, build].filter((part) => part && part.length > 0).join('/'))

// Best-effort project slug for the current directory: the git repository name
// (toplevel) when inside a repo, else the working-directory name. Used to
// auto-derive --project when it is omitted.
export const autoProjectSlug = (cwd: string) => {
  const top = spawnSync('git', ['rev-parse', '--show-toplevel'], { cwd, encoding: 'utf8' })
  const repoDir =
    top.status === 0 && top.stdout.trim().length > 0 ? top.stdout.trim() : cwd
  return canonicalizeBuildId(path.basename(repoDir)) || 'project'
}

// Resolve the project/build/build-id from the CLI flags, with sensible
// auto-derivation when flags are omitted:
//   --build-id <project/build>      explicit, wins outright
//   --project / --build             composed into <project>/<build>
//   (omitted)                       project from repo/dir, build from dir/scene
// `dirHint` seeds the build name when --build is omitted; `nameHint` (e.g. the
// scene name) is a secondary fallback.
export const resolveProjectBuild = (
  options: CliOptions,
  dirHint: string | undefined,
  nameHint?: string,
): { project: string; build: string; buildId: string; derived: string[] } => {
  const derived: string[] = []
  const explicitId = optionString(options, 'build-id', 'buildId')
  const projectOpt = optionString(options, 'project')
  const buildOpt = optionString(options, 'build')

  if (explicitId) {
    const buildId = canonicalizeBuildId(explicitId)
    if (!buildId) throw new Error(`Build id "${explicitId}" has no usable characters.`)
    const { project, build } = splitProjectBuild(buildId)
    return { project, build, buildId, derived }
  }

  let project = projectOpt ? canonicalizeBuildId(projectOpt) : ''
  if (!project) {
    project = autoProjectSlug(process.cwd())
    derived.push(`project "${project}" (from repo/dir)`)
  }

  let build = buildOpt ? canonicalizeBuildId(buildOpt) : ''
  if (!build) {
    const fromDir = dirHint ? canonicalizeBuildId(path.basename(dirHint)) : ''
    const fromName = nameHint ? canonicalizeBuildId(nameHint) : ''
    build = fromDir || fromName || project
    derived.push(`build "${build}" (from ${fromDir ? 'directory' : fromName ? 'scene name' : 'project'})`)
  }

  const buildId = composeBuildId(project, build)
  if (!buildId) throw new Error('Could not derive a project/build id; pass --project and --build.')
  const split = splitProjectBuild(buildId)
  return { project: split.project, build: split.build, buildId, derived }
}

// Build ids may contain "/" as a path separator to form a hierarchy, e.g.
// "prototype_v1/chassis" or "prototype_v1/leg/coxa". Each segment is restricted
// to URL- and filesystem-safe characters, and "." / ".." segments are rejected
// so a slashed id can never escape the cache/build root. Ids are canonicalized
// (see canonicalizeBuildId) before reaching here, so this is a final safety net.
export const assertValidBuildId = (buildId: string) => {
  const segments = buildId.split('/')
  const valid =
    segments.length > 0 &&
    segments.every(
      (segment) => /^[A-Za-z0-9._-]+$/.test(segment) && segment !== '.' && segment !== '..',
    )
  if (!valid) {
    throw new Error(
      `Invalid build id "${buildId}". Use letters, numbers, dots, underscores, or dashes, ` +
        'with "/" to separate hierarchy segments (e.g. prototype_v1/chassis).',
    )
  }
}

const hasPreferredStlDir = (dir: string) =>
  ['stl', 'stls', 'stl_prototype', 'meshes', 'assets', 'fasteners'].some((name) =>
    existsSync(path.join(dir, name)),
  )

const discoverBuildDir = (startDir: string) => {
  let current = path.resolve(startDir)

  while (true) {
    if (
      existsSync(path.join(current, 'scene.json')) ||
      existsSync(path.join(current, 'design_spec.yaml')) ||
      hasPreferredStlDir(current)
    ) {
      return current
    }

    const parent = path.dirname(current)
    if (parent === current) return path.resolve(startDir)
    current = parent
  }
}

export const resolveBuildDirOption = (options: CliOptions, positional: string[]) => {
  const explicit = optionString(options, 'dir', 'build-dir') ?? positional[0]
  return explicit ? path.resolve(process.cwd(), explicit) : discoverBuildDir(process.cwd())
}
