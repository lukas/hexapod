import { existsSync } from 'node:fs'
import { cp, mkdir, readFile, readdir, rm, stat, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { normalizeVersionReason, VERSION_LEARNING_GUIDANCE } from '../../core/versionFeedback'
import type { BuildSceneManifest } from '../../core/buildScene'
import { requireRevisionDescription } from '../../core/revisionDescription'
import { pinnedCatalogRevisions, readCatalog } from '../../hub/catalogStore'
import {
  DEFAULT_BRANCH_NAME,
  DEFAULT_VERSION_NAME,
  canonicalizeVersionName,
  compareVersionNames,
  describeBuildVersions,
  groupBuildsByProject,
  listBuildVersions,
  nextBumpVersion,
  parseBuildAddress,
  readBuildMeta,
  readSceneName,
  resolveDefaultVersion,
  selectVersionsToPrune,
  splitProjectBuild,
  type BuildsIndexBuild,
  type CacheVersionMeta,
} from '../../hub/buildsIndex'
import {
  printCacheList,
  printDiff,
  printJson,
  printVersionTree,
} from '../cliFormat'
import { diffManifests, summarizeDiff } from '../../core/buildDiff'
import {
  canonicalizeBuildId,
  optionString,
  readJson,
  type CliOptions,
} from '../../hub/cliShared'
import {
  buildIdForDir,
  buildIndexEntryFor,
  cacheBuildDir,
  cacheRoot,
  type CacheMeta,
} from '../../hub/hub'
import {
  loadBuild,
  meshContentHashes,
  resolveBuildDir,
  walkBuildDirs,
  onDiskBuildsRoot,
} from '../cliBuild'
import {
  ensurePartHistory,
  partHistoryBranches,
  searchPartHistory,
  summarizeParts,
  type PartHistoryEvent,
  type PartSearchHit,
} from '../../hub/partHistory'

// Versioning commands: `versions`, `migrate`, `freeze`, `cache`, `diff`.

// Two supported forms:
//   buildviz diff <project/build@from> <project/build@to>  (named versions —
//     refs may be branch-qualified, e.g. build@branch@version or build@branch)
//   buildviz diff <build-dir> <from-version> <to-version>  (legacy positional)
export const diffCommand = async (positional: string[], options: CliOptions) => {
  const buildDir = positional[0]
  const addressForm =
    positional.length === 2 &&
    (positional[0].includes('@') || positional[1].includes('@'))

  let fromBuild: Awaited<ReturnType<typeof loadBuild>>
  let toBuild: Awaited<ReturnType<typeof loadBuild>>
  if (addressForm) {
    const fromAddress = parseBuildAddress(positional[0])
    const toAddress = parseBuildAddress(positional[1])
    if (fromAddress.buildId !== toAddress.buildId) {
      throw new Error(
        `diff compares two named versions of the SAME build, but got ` +
          `"${fromAddress.buildId}" and "${toAddress.buildId}". ` +
          `Try: buildviz diff ${fromAddress.buildId}@${fromAddress.version ?? 'main'} ${fromAddress.buildId}@<other-version>`,
      )
    }
    // loadBuild parses the full address itself (including @branch@version and
    // branch-name disambiguation), so pass the raw argument through.
    fromBuild = await loadBuild(positional[0])
    toBuild = await loadBuild(positional[1])
  } else {
    const fromVersion = positional[1]
    const toVersion = positional[2]
    if (!fromVersion || !toVersion) {
      throw new Error(
        'Usage: buildviz diff <project/build@from> <project/build@to>\n' +
          '   or: buildviz diff <build-dir> <from-version> <to-version>',
      )
    }
    const branch = optionString(options, 'branch')
    fromBuild = await loadBuild(buildDir, fromVersion, branch)
    toBuild = await loadBuild(buildDir, toVersion, branch)
  }
  const diff = diffManifests(fromBuild.index.manifest, toBuild.index.manifest, {
    from: await meshContentHashes(fromBuild),
    to: await meshContentHashes(toBuild),
  })
  const result = {
    ok: true,
    build: {
      id: toBuild.buildId,
      buildId: toBuild.buildId,
      name: toBuild.index.manifest.name,
      units: toBuild.index.manifest.units,
      path: path.relative(process.cwd(), toBuild.baseDir) || toBuild.baseDir,
    },
    from: {
      branch: fromBuild.branch,
      version: fromBuild.version,
      path: path.relative(process.cwd(), fromBuild.buildDir),
    },
    to: {
      branch: toBuild.branch,
      version: toBuild.version,
      path: path.relative(process.cwd(), toBuild.buildDir),
    },
    summary: summarizeDiff(diff),
    results: diff,
  }

  if (options.json) {
    printJson(result)
  } else {
    const label = (build: typeof fromBuild) =>
      build.isDefaultBranch ? build.version : `${build.branch}@${build.version}`
    printDiff(result.build.id, label(fromBuild), label(toBuild), diff)
  }
}

export const browseVersions = async (arg: string | undefined, options: CliOptions) => {
  if (arg) {
    const address = parseBuildAddress(arg)
    const baseDir = resolveBuildDir(address.buildId)
    const isConcreteBuild =
      existsSync(path.join(baseDir, 'scene.json')) || existsSync(path.join(baseDir, 'versions'))
    if (isConcreteBuild) {
      const id = buildIdForDir(baseDir)
      const entry = await buildIndexEntryFor(id, baseDir, null)
      const branches = entry.branches ?? []
      const versionCount = branches.reduce((total, branchEntry) => total + branchEntry.versions.length, 0)
      const result = {
        ok: true,
        build: {
          id: entry.id,
          buildId: entry.id,
          project: entry.project,
          build: entry.build,
          path: path.relative(process.cwd(), baseDir) || baseDir,
        },
        summary:
          branches.length > 1
            ? `${branches.length} branch(es), ${versionCount} version(s); default branch "${entry.defaultBranch}".`
            : `${entry.versions.length} version(s); default "${entry.defaultVersion}".`,
        results: {
          defaultVersion: entry.defaultVersion,
          versions: entry.versions,
          defaultBranch: entry.defaultBranch,
          branches,
        },
      }
      if (options.json) {
        printJson(result)
      } else if (branches.length > 1) {
        console.log(`Branches for ${entry.id} (project ${entry.project} · build ${entry.build}):`)
        for (const branchEntry of branches) {
          console.log(`- ${branchEntry.name}${branchEntry.isDefault ? ' (default branch)' : ''}:`)
          const chronological = [...branchEntry.versions].sort((a, b) => (b.pushedAt ?? '').localeCompare(a.pushedAt ?? ''))
          chronological.forEach((version) =>
            console.log(`    ${version.name}${version.isDefault ? ' (current)' : ''} · ${version.pushedAt ?? 'Date unknown'}\n      ${version.message ?? 'Description not recorded.'}`),
          )
        }
      } else {
        console.log(`Versions for ${entry.id} (project ${entry.project} · build ${entry.build}):`)
        const chronological = [...entry.versions].sort((a, b) => (b.pushedAt ?? '').localeCompare(a.pushedAt ?? ''))
        chronological.forEach((version) =>
          console.log(`- ${version.name}${version.isDefault ? ' (current)' : ''} · ${version.pushedAt ?? 'Date unknown'}\n  ${version.message ?? 'Description not recorded.'}`),
        )
      }
      return
    }
  }

  const dirs = [
    ...(await walkBuildDirs(cacheRoot)),
    ...(await walkBuildDirs(onDiskBuildsRoot)),
  ]
  const seen = new Set<string>()
  const all: BuildsIndexBuild[] = []
  for (const { id, dir } of dirs) {
    if (seen.has(id)) continue
    seen.add(id)
    all.push(await buildIndexEntryFor(id, dir, null))
  }

  const filter = arg ? canonicalizeBuildId(arg) : null
  const filtered = filter
    ? all.filter((build) => build.project === filter || build.id === filter || build.id.startsWith(`${filter}/`))
    : all
  const projects = groupBuildsByProject(filtered)

  if (options.json) {
    printJson({ ok: true, summary: `${filtered.length} build(s) across ${projects.length} project(s).`, results: { projects } })
    return
  }
  if (projects.length === 0) {
    console.log(arg ? `No builds found for "${arg}".` : 'No builds found. Push one with: buildviz push --project <p> --build <b> --scene scene.json')
    return
  }
  printVersionTree(projects)
}

// Migrate existing builds to the explicit project/build/named-version layout by
// writing/normalizing meta.json. Non-destructive: scene files are never moved,
// auto-numbered versions (v1, v2, ...) are preserved as named versions, and the
// build default is recorded (legacy `latestVersion` is honored). Covers both
// the hub cache and on-disk public/builds.
export const migrateOneBuild = async (buildDir: string, id: string, dryRun: boolean) => {
  const meta = await readBuildMeta(buildDir)
  const { project, build } = splitProjectBuild(id)
  const versionDirs = await listBuildVersions(buildDir)
  const hasRoot = existsSync(path.join(buildDir, 'scene.json'))

  let defaultVersion = meta?.defaultVersion ?? meta?.latestVersion
  if (!defaultVersion) {
    if (versionDirs.includes(DEFAULT_VERSION_NAME)) defaultVersion = DEFAULT_VERSION_NAME
    else if (hasRoot) defaultVersion = DEFAULT_VERSION_NAME
    else defaultVersion = versionDirs[0] ?? DEFAULT_VERSION_NAME
  }

  // Preserve pushedAt timestamps recorded under either the new `name` or the
  // legacy `version` key.
  const priorPushedAt = new Map<string, string>()
  const priorVersionMeta = new Map<string, CacheVersionMeta>()
  for (const entry of meta?.versions ?? []) {
    const name = entry.name ?? (entry as unknown as { version?: string }).version
    if (name) {
      priorPushedAt.set(name, entry.pushedAt)
      priorVersionMeta.set(name, entry)
    }
  }
  const now = new Date().toISOString()
  const names = new Set<string>(versionDirs)
  for (const name of priorPushedAt.keys()) names.add(name)
  if (hasRoot) names.add(defaultVersion)
  const versions = [...names]
    .sort(compareVersionNames)
    .map((name) => ({
      ...priorVersionMeta.get(name),
      name,
      pushedAt: priorPushedAt.get(name) ?? meta?.updatedAt ?? now,
    }))

  const scenePath = path.join(buildDir, 'scene.json')
  const name = meta?.name ?? (hasRoot ? await readSceneName(scenePath) : null)
  // Branch bookkeeping: the default branch record mirrors the top-level fields;
  // any other existing branch records are preserved untouched.
  const defaultBranch = meta?.defaultBranch ?? DEFAULT_BRANCH_NAME
  const otherBranches = (meta?.branches ?? []).filter((entry) => entry.name !== defaultBranch)
  const nextMeta: CacheMeta = {
    schema: 2,
    buildId: id,
    project,
    build,
    name,
    createdAt: meta?.createdAt ?? now,
    updatedAt: now,
    defaultVersion,
    latestVersion: defaultVersion,
    versions,
    defaultBranch,
    branches: [{ name: defaultBranch, defaultVersion, versions }, ...otherBranches],
  }

  const before = meta
    ? JSON.stringify({ ...meta, updatedAt: undefined })
    : null
  const after = JSON.stringify({ ...nextMeta, updatedAt: undefined })
  const changed = before !== after
  if (changed && !dryRun) {
    await writeFile(path.join(buildDir, 'meta.json'), `${JSON.stringify(nextMeta, null, 2)}\n`, 'utf8')
  }
  return {
    id,
    project,
    build,
    defaultVersion,
    versions: versions.map((entry) => entry.name),
    hadMeta: meta !== null,
    changed,
  }
}

export const migrateBuilds = async (options: CliOptions) => {
  const dryRun = Boolean(options['dry-run'] ?? options.dryRun)
  const cacheDirs = await walkBuildDirs(cacheRoot)
  const onDiskDirs = options['cache-only'] ? [] : await walkBuildDirs(onDiskBuildsRoot)

  const cache = await Promise.all(cacheDirs.map(({ id, dir }) => migrateOneBuild(dir, id, dryRun)))
  const onDisk = await Promise.all(onDiskDirs.map(({ id, dir }) => migrateOneBuild(dir, id, dryRun)))
  const all = [...cache, ...onDisk]
  const changedCount = all.filter((entry) => entry.changed).length

  if (options.json) {
    printJson({
      ok: true,
      dryRun,
      summary: `${dryRun ? 'Would migrate' : 'Migrated'} ${changedCount} of ${all.length} build(s).`,
      results: { cache, onDisk },
    })
    return
  }

  console.log(
    `${dryRun ? 'Would migrate' : 'Migrated'} ${changedCount} of ${all.length} build(s) ` +
      'to the project/build/named-version model.',
  )
  for (const entry of all) {
    const flag = entry.changed ? (dryRun ? 'would update' : 'updated') : 'ok'
    console.log(
      `- ${entry.id}: project ${entry.project} · build ${entry.build} · default ${entry.defaultVersion} ` +
        `· versions [${entry.versions.join(', ')}] (${flag})`,
    )
  }
  if (changedCount > 0 && dryRun) console.log('Re-run without --dry-run to write meta.json files.')
}

// --- freeze: write the on-disk versions/<name>/ layout in place ---------------

// Copy a manifest's relative-URL mesh assets (and only those) from srcDir into
// destDir, preserving their relative paths so a versions/<name>/ dir is
// self-contained. Absolute http(s) and /-rooted urls are left untouched (the
// hub/viewer resolve those without a local copy).
export const copyRelativeAssets = async (
  manifest: BuildSceneManifest,
  srcDir: string,
  destDir: string,
): Promise<string[]> => {
  const copied: string[] = []
  const seen = new Set<string>()
  for (const mesh of manifest.meshes) {
    const url = mesh.url
    if (!url || /^[a-z][a-z0-9+.-]*:/i.test(url) || url.startsWith('/')) continue
    const rel = url.replace(/^\.\//, '')
    if (seen.has(rel)) continue
    seen.add(rel)
    const src = path.join(srcDir, rel)
    if (!existsSync(src)) continue
    const dest = path.join(destDir, rel)
    await mkdir(path.dirname(dest), { recursive: true })
    await cp(src, dest)
    copied.push(rel)
  }
  return copied
}

export const freezeBuild = async (positional: string[], options: CliOptions) => {
  const dirArg = positional[0]
  if (!dirArg) {
    throw new Error('Usage: buildviz freeze <build-dir> (--version <name> | --bump) (-m <text> | --message <text>) [--set-default] [--force] [--keep <n>] [--no-snapshot]')
  }
  const buildDir = path.resolve(process.cwd(), dirArg)
  const scenePath = path.join(buildDir, 'scene.json')
  if (!existsSync(scenePath)) throw new Error(`Missing scene.json in ${buildDir}`)

  const meta = await readBuildMeta(buildDir)
  const existingVersions = await listBuildVersions(buildDir)

  const versionOpt = optionString(options, 'version')
  const bump = Boolean(options.bump)
  let version: string
  if (versionOpt) {
    const canonical = canonicalizeVersionName(versionOpt)
    if (!canonical) throw new Error(`Version "${versionOpt}" has no usable characters.`)
    version = canonical
  } else if (bump) {
    // Auto-pick the next free v<N> from the on-disk versions (e.g. v1 → v2).
    version = nextBumpVersion(existingVersions)
  } else {
    throw new Error('freeze requires --version <name> or --bump (auto next v<N>).')
  }

  const force = Boolean(options.force)
  const noSnapshot = Boolean(options['no-snapshot'] ?? options.noSnapshot)
  // REQUIRED changelog/commit note for the version being frozen (-m). Applies to
  // the frozen version only, never to an auto-snapshot of the prior default.
  // Re-freezing a version that ALREADY carries a message may omit -m (the
  // existing note is kept rather than clobbered).
  const rawMessage = optionString(options, 'message', 'msg')
  const message = rawMessage === undefined ? undefined : requireRevisionDescription(rawMessage)
  const reason = normalizeVersionReason(optionString(options, 'reason'))
  const versionHasMessage = (meta?.versions ?? []).some((entry) => {
    const name = entry.name ?? (entry as unknown as { version?: string }).version
    return name === version && typeof entry.message === 'string' && entry.message.length > 0
  })
  if (!message && !versionHasMessage) {
    throw new Error(
      'freeze requires a version description — pass -m "<one or two sentences: what changed and why>" ' +
        '(alias --message/--msg). It shows in the viewer version dropdown, diffs, and per-part history.',
    )
  }
  // --bump makes the frozen version the default (like --set-default) unless the
  // caller opts out with --no-default; an explicit --set-default always wins.
  const explicitSetDefault = Boolean(options['set-default'] ?? options.setDefault ?? options.default)
  const optOutDefault = Boolean(options['no-default'] ?? options['no-set-default'])
  const setDefault = explicitSetDefault || (bump && !optOutDefault)

  const keepOpt = optionString(options, 'keep', 'keep-versions', 'keepVersions')
  let keepVersions: number | undefined
  if (keepOpt !== undefined) {
    const parsed = Number(keepOpt)
    if (!Number.isInteger(parsed) || parsed < 1) {
      throw new Error(`Invalid --keep "${keepOpt}"; use a positive integer (versions to retain per build).`)
    }
    keepVersions = parsed
  }

  const versionDir = path.join(buildDir, 'versions', version)
  if (existsSync(path.join(versionDir, 'scene.json')) && !force) {
    throw new Error(
      `versions/${version}/scene.json already exists (named versions are immutable). Pass --force to overwrite, or use --bump for the next v<N>.`,
    )
  }

  const manifest = await readJson<BuildSceneManifest>(scenePath)
  const designSpecPath = path.join(buildDir, 'design_spec.yaml')
  const hasDesignSpec = existsSync(designSpecPath)
  const buildId = meta?.buildId ?? buildIdForDir(buildDir)
  const { project, build } = splitProjectBuild(buildId)
  const sceneBody = `${JSON.stringify(manifest, null, 2)}\n`
  const pinnedVersions = new Set(pinnedCatalogRevisions(await readCatalog())
    .filter((reference) => reference.buildId === buildId && reference.branch === (meta?.defaultBranch ?? DEFAULT_BRANCH_NAME))
    .map((reference) => reference.version))
  if (pinnedVersions.has(version)) {
    throw new Error(`${buildId}@${version} is referenced by a saved view, milestone, or as-built record. Use --bump to preserve that revision and its assets.`)
  }

  // Resolve the default version (the frozen one wins with --set-default/--bump;
  // a brand-new meta defaults to the frozen version when nothing else exists).
  const priorDefault = meta ? resolveDefaultVersion(meta) : null
  const rootIsDefaultBranch = existsSync(scenePath)
  const defaultVersion = setDefault
    ? version
    : priorDefault ?? (rootIsDefaultBranch ? DEFAULT_VERSION_NAME : version)

  // --- Auto-snapshot the prior default before an in-place overwrite ----------
  // When freezing OVER the existing default version (same name) with changed
  // content, preserve the prior default's bytes under a fresh v<N> first, so
  // history accumulates (parallels push). The prior default's bytes live at
  // versions/<default>/ when it was already materialized there; the build root
  // is the source we are about to (re)freeze, so it is never the "prior" copy.
  let snapshotVersion: string | null = null
  const priorDefaultScene = priorDefault
    ? path.join(buildDir, 'versions', priorDefault, 'scene.json')
    : null
  if (
    !noSnapshot &&
    defaultVersion === version &&
    priorDefault === version &&
    priorDefaultScene &&
    existsSync(priorDefaultScene)
  ) {
    const oldBody = await readFile(priorDefaultScene, 'utf8').catch(() => null)
    if (oldBody !== null && oldBody !== sceneBody) {
      snapshotVersion = nextBumpVersion([...existingVersions, version])
      const snapDir = path.join(buildDir, 'versions', snapshotVersion)
      const priorDir = path.dirname(priorDefaultScene)
      await mkdir(snapDir, { recursive: true })
      await writeFile(path.join(snapDir, 'scene.json'), oldBody, 'utf8')
      const priorSpec = path.join(priorDir, 'design_spec.yaml')
      if (existsSync(priorSpec)) await cp(priorSpec, path.join(snapDir, 'design_spec.yaml'))
      const priorWorkflow = path.join(priorDir, 'workflow.json')
      if (existsSync(priorWorkflow)) await cp(priorWorkflow, path.join(snapDir, 'workflow.json'))
      try {
        await copyRelativeAssets(await readJson<BuildSceneManifest>(priorDefaultScene), priorDir, snapDir)
      } catch {
        // A malformed prior scene contributes no relative assets to the snapshot.
      }
    }
  }

  // 1. Materialize versions/<name>/ with the scene, spec, and relative assets.
  await mkdir(versionDir, { recursive: true })
  await writeFile(path.join(versionDir, 'scene.json'), sceneBody, 'utf8')
  if (hasDesignSpec) {
    await cp(designSpecPath, path.join(versionDir, 'design_spec.yaml'))
  }
  const workflowPath = path.join(buildDir, 'workflow.json')
  if (existsSync(workflowPath)) await cp(workflowPath, path.join(versionDir, 'workflow.json'))
  else await rm(path.join(versionDir, 'workflow.json'), { force: true })
  const copiedAssets = await copyRelativeAssets(manifest, buildDir, versionDir)

  // Stealing "default" away from a prior default that lived ONLY at the build
  // root (no versions/<prior>/ snapshot) would orphan it once we overwrite the
  // root. Snapshot the current root into versions/<prior>/ first so the prior
  // default survives as a named version — matching push's keep-every-version model.
  if (
    defaultVersion === version &&
    priorDefault &&
    priorDefault !== version &&
    !existsSync(path.join(buildDir, 'versions', priorDefault, 'scene.json'))
  ) {
    const priorDir = path.join(buildDir, 'versions', priorDefault)
    await mkdir(priorDir, { recursive: true })
    await writeFile(path.join(priorDir, 'scene.json'), sceneBody, 'utf8')
    if (hasDesignSpec) await cp(designSpecPath, path.join(priorDir, 'design_spec.yaml'))
    if (existsSync(workflowPath)) await cp(workflowPath, path.join(priorDir, 'workflow.json'))
    await copyRelativeAssets(manifest, buildDir, priorDir)
  }

  // The frozen scene is mirrored to the build root when it becomes the default
  // (the root scene.json is the default version's home).
  if (defaultVersion === version) {
    await writeFile(scenePath, sceneBody, 'utf8')
    if (hasDesignSpec) await cp(path.join(versionDir, 'design_spec.yaml'), designSpecPath)
  }

  // 2. Build the version list, then apply --keep retention (prune oldest
  //    non-default version dirs) so snapshots cannot grow the build unbounded.
  const now = new Date().toISOString()
  const priorPushedAt = new Map<string, string>()
  const priorMessage = new Map<string, string>()
  for (const entry of meta?.versions ?? []) {
    const name = entry.name ?? (entry as unknown as { version?: string }).version
    if (name) priorPushedAt.set(name, entry.pushedAt)
    if (name && typeof entry.message === 'string' && entry.message.length > 0) {
      priorMessage.set(name, entry.message)
    }
  }
  const versionDirs = await listBuildVersions(buildDir)
  const names = new Set<string>([...versionDirs, version])
  if (rootIsDefaultBranch) names.add(defaultVersion)
  // The frozen version takes the new --message (falling back to its existing one
  // so re-freezing without -m doesn't clobber it); an auto-snapshot inherits the
  // prior default's message (the content it preserves); others keep theirs.
  const messageFor = (name: string): string | undefined => {
    if (name === version) return message ?? priorMessage.get(version)
    if (name === snapshotVersion) return priorMessage.get(version)
    return priorMessage.get(name)
  }
  let versions = [...names].sort(compareVersionNames).map((name) => {
    const versionMessage = messageFor(name)
    const priorReason = meta?.versions.find((entry) => entry.name === (name === snapshotVersion ? version : name))?.reason
    const versionReason = name === version ? reason ?? priorReason : priorReason
    const priorMetadata = name === version ? undefined : meta?.versions?.find((entry) =>
      entry.name === (name === snapshotVersion ? version : name))
    return {
      ...priorMetadata,
      name,
      // The freshly frozen version is "now"; the snapshot carries the prior
      // default's age so retention treats it as older than the new default.
      pushedAt:
        name === version
          ? now
          : name === snapshotVersion
            ? meta?.updatedAt ?? now
            : priorPushedAt.get(name) ?? meta?.updatedAt ?? now,
      ...(versionMessage ? { message: versionMessage } : {}),
      ...(versionReason ? { reason: versionReason } : {}),
    }
  })

  const { pruned: candidates } = selectVersionsToPrune(versions, keepVersions, defaultVersion)
  const pruned = candidates.filter((name) => !pinnedVersions.has(name))
  if (pruned.length > 0) {
    const prunedNames = new Set(pruned)
    for (const name of pruned) {
      await rm(path.join(buildDir, 'versions', name), { recursive: true, force: true }).catch(() => {})
    }
    versions = versions.filter((entry) => !prunedNames.has(entry.name))
  }

  // 3. Write/refresh meta.json with the SAME shape push uses. freeze operates
  //    on the branch layout rooted at <build-dir> (the default branch when the
  //    dir is a build root); other branch records are preserved untouched.
  const freezeDefaultBranch = meta?.defaultBranch ?? DEFAULT_BRANCH_NAME
  const freezeOtherBranches = (meta?.branches ?? []).filter(
    (entry) => entry.name !== freezeDefaultBranch,
  )
  const nextMeta: CacheMeta = {
    schema: 2,
    buildId,
    project,
    build,
    name: meta?.name ?? manifest.name ?? null,
    createdAt: meta?.createdAt ?? now,
    updatedAt: now,
    defaultVersion,
    latestVersion: defaultVersion,
    versions,
    defaultBranch: freezeDefaultBranch,
    branches: [
      { name: freezeDefaultBranch, defaultVersion, versions },
      ...freezeOtherBranches,
    ],
  }
  await writeFile(path.join(buildDir, 'meta.json'), `${JSON.stringify(nextMeta, null, 2)}\n`, 'utf8')

  const result = {
    ok: true,
    summary: `Froze ${buildId}@${version}${defaultVersion === version ? ' (default)' : ''} into versions/${version}/.`,
    buildId,
    project,
    build,
    version,
    defaultVersion,
    setDefault: defaultVersion === version,
    message: message ?? null,
    reason: versions.find((entry) => entry.name === version)?.reason ?? null,
    nextSteps: VERSION_LEARNING_GUIDANCE,
    warnings: versions.find((entry) => entry.name === version)?.reason ? [] : ['Missing version reason. Supply --reason explaining why this revision is needed.'],
    snapshot: snapshotVersion,
    pruned,
    versionDir: path.relative(process.cwd(), versionDir) || versionDir,
    copiedAssets,
    versions: versions.map((entry) => entry.name),
  }
  if (options.json) {
    printJson(result)
    return
  }
  console.log(result.summary)
  for (const warning of result.warnings) console.warn(warning)
  console.log(result.nextSteps)
  console.log(`Copied ${copiedAssets.length} mesh asset(s) into versions/${version}/.`)
  if (snapshotVersion) {
    console.log(
      `Snapshot: preserved the prior default as "${snapshotVersion}" before overwriting ` +
        `"${defaultVersion}" in place (pass --no-snapshot to overwrite without history).`,
    )
  }
  if (pruned.length > 0) {
    console.log(`Retention: pruned ${pruned.length} old version(s) — ${pruned.join(', ')}.`)
  }
  // A message is guaranteed here: either -m was passed or the version already
  // carried one (kept on re-freeze).
  const finalMessage = message ?? priorMessage.get(version)
  if (finalMessage) console.log(`Message: ${finalMessage}${message ? '' : ' (kept from prior freeze)'}`)
  console.log(`Versions: ${result.versions.join(', ')} · default ${defaultVersion}`)
  console.log('The viewer, `buildviz versions`, and `buildviz diff` pick it up unchanged.')
}

// --- history: per-part change history (searchable) ---------------------------

const formatEventLine = (event: PartHistoryEvent) => {
  const when = event.pushedAt ? event.pushedAt.slice(0, 16).replace('T', ' ') : '(no date)'
  const message = event.message ? ` — "${event.message}"` : ''
  return `${event.version.padEnd(8)} ${when}  [${event.changes.join(', ')}]${message}`
}

const printPartTimeline = (partType: string, events: PartHistoryEvent[]) => {
  console.log(`${partType} — ${events.length} recorded change(s):`)
  for (const event of events) {
    console.log(`  ${formatEventLine(event)}`)
    if (event.description && event.changes.includes('description')) {
      const excerpt = event.description.length > 200 ? `${event.description.slice(0, 200)}…` : event.description
      console.log(`           ${excerpt.replace(/\s+/g, ' ')}`)
    }
  }
}

// `buildviz history <build> [<part-type>]` — per-part summaries or one part's
// timeline; `buildviz history [--build <id>] --search "<terms>"` — search part
// names + history text (every cached build when no build is given). History is
// derived from pushed version snapshots and kept in an append-only ledger
// (part_history.json), so it survives version-retention pruning.
export const historyCommand = async (positional: string[], options: CliOptions) => {
  const search = optionString(options, 'search', 'q')
  const branch = optionString(options, 'branch')
  const buildArg = positional[0] ?? optionString(options, 'build', 'build-id')

  const resolveTarget = (rawId: string) => {
    const address = parseBuildAddress(rawId)
    const dir = resolveBuildDir(address.buildId)
    if (!existsSync(dir)) throw new Error(`No build directory found for "${rawId}".`)
    // History is branch-scoped, so a single "@x" ref is read as a branch name.
    return { id: buildIdForDir(dir), dir, branch: branch ?? address.branch ?? address.version ?? undefined }
  }

  if (search) {
    // The cache walk descends into branches/<name>/ dirs too; those are NOT
    // standalone builds — each real build expands into its branches below.
    const targets = buildArg
      ? [resolveTarget(buildArg)]
      : (await walkBuildDirs(cacheRoot))
          .filter(({ id }) => !id.includes('/branches/'))
          .map(({ id, dir }) => ({ id, dir, branch }))
    const hits: PartSearchHit[] = []
    for (const target of targets) {
      const branches = target.branch ? [target.branch] : await partHistoryBranches(target.dir)
      for (const branchName of branches) {
        try {
          const ledger = await ensurePartHistory(target.dir, target.id, branchName)
          hits.push(...searchPartHistory(ledger, search))
        } catch {
          // Builds/branches without version snapshots contribute no hits.
        }
      }
    }
    if (options.json) {
      printJson({ ok: true, summary: `${hits.length} part(s) matched "${search}".`, results: { query: search, hits } })
      return
    }
    if (hits.length === 0) {
      console.log(`No part history matched "${search}".`)
      return
    }
    for (const hit of hits) {
      console.log(`\n${hit.buildId}@${hit.branch} · ${hit.partType}${hit.nameMatched ? ' (name match)' : ''}`)
      for (const event of hit.events) console.log(`  ${formatEventLine(event)}`)
      if (hit.events.length === 0) console.log('  (matched by name only)')
    }
    return
  }

  if (!buildArg) {
    throw new Error(
      'Usage: buildviz history <build|project/build[@branch]> [<part-type>] [--branch <name>] [--json]\n' +
        '   or: buildviz history [--build <id>] --search "<terms>" [--json]',
    )
  }
  const target = resolveTarget(buildArg)
  const ledger = await ensurePartHistory(target.dir, target.id, target.branch)
  const partArg = positional[1]

  if (partArg) {
    const events = ledger.parts[partArg]
    if (!events) {
      const known = Object.keys(ledger.parts).sort().join(', ')
      throw new Error(`No part "${partArg}" in ${target.id}@${ledger.branch}. Known parts: ${known || '(none)'}`)
    }
    if (options.json) {
      printJson({
        ok: true,
        summary: `${events.length} recorded change(s) for ${partArg} in ${target.id}@${ledger.branch}.`,
        results: { buildId: target.id, branch: ledger.branch, partType: partArg, events },
      })
      return
    }
    printPartTimeline(partArg, events)
    return
  }

  const parts = summarizeParts(ledger)
  if (options.json) {
    printJson({
      ok: true,
      summary: `${parts.length} part(s) with history in ${target.id}@${ledger.branch}.`,
      results: {
        buildId: target.id,
        branch: ledger.branch,
        indexedVersions: ledger.indexed.map((entry) => entry.name),
        parts,
      },
    })
    return
  }
  console.log(
    `Part history for ${target.id}@${ledger.branch} ` +
      `(${ledger.indexed.length} indexed version(s): ${ledger.indexed[0]?.name ?? '—'}..${ledger.indexed[ledger.indexed.length - 1]?.name ?? '—'}):`,
  )
  for (const part of parts) {
    const last = part.lastChanged
    console.log(
      `- ${part.partType.padEnd(28)} ${String(part.revisionCount).padStart(3)} change(s)` +
        `  first ${part.firstSeen?.version ?? '—'}  last ${last?.version ?? '—'}` +
        `${last ? ` [${last.changes.join(', ')}]` : ''}${part.present ? '' : '  (removed)'}`,
    )
  }
  console.log('\nOne part: buildviz history <build> <part-type> · search: buildviz history --search "<terms>"')
}

// --- cache: inspect / prune the hub version cache ----------------------------

export const dirSizeBytes = async (dir: string): Promise<number> => {
  if (!existsSync(dir)) return 0
  let total = 0
  const entries = await readdir(dir, { withFileTypes: true })
  await Promise.all(
    entries.map(async (entry) => {
      const entryPath = path.join(dir, entry.name)
      if (entry.isDirectory()) {
        total += await dirSizeBytes(entryPath)
      } else {
        try {
          total += (await stat(entryPath)).size
        } catch {
          // A file that vanished mid-walk contributes nothing.
        }
      }
    }),
  )
  return total
}

export const cacheCommand = async (positional: string[], options: CliOptions) => {
  const sub = positional[0]
  if (sub === 'ls' || sub === 'list' || sub === undefined) {
    const dirs = await walkBuildDirs(cacheRoot)
    const builds = []
    let totalBytes = 0
    for (const { id, dir } of dirs.sort((a, b) => a.id.localeCompare(b.id))) {
      const meta = await readBuildMeta(dir)
      const defaultVersion = resolveDefaultVersion(meta)
      const entries = await describeBuildVersions(dir, defaultVersion)
      const pushedAtByName = new Map<string, string>()
      for (const entry of meta?.versions ?? []) {
        const name = entry.name ?? (entry as unknown as { version?: string }).version
        if (name) pushedAtByName.set(name, entry.pushedAt)
      }
      const versionsDir = path.join(dir, 'versions')
      const versionsTreeBytes = existsSync(versionsDir) ? await dirSizeBytes(versionsDir) : 0
      const rootOnlyBytes = (await dirSizeBytes(dir)) - versionsTreeBytes
      const versions = []
      for (const entry of entries) {
        const vdir = path.join(versionsDir, entry.name)
        const sizeBytes = existsSync(vdir)
          ? await dirSizeBytes(vdir)
          : entry.isDefault
            ? rootOnlyBytes
            : 0
        versions.push({
          name: entry.name,
          isDefault: entry.isDefault,
          sizeBytes,
          pushedAt: pushedAtByName.get(entry.name) ?? null,
        })
      }
      const sizeBytes = await dirSizeBytes(dir)
      totalBytes += sizeBytes
      builds.push({
        id,
        name: meta?.name ?? null,
        defaultVersion,
        versionCount: entries.length,
        versions,
        sizeBytes,
      })
    }
    const result = { ok: true, cacheRoot, builds, totalBytes }
    if (options.json) {
      printJson({ ok: true, summary: `${builds.length} cached build(s).`, results: result })
    } else {
      printCacheList(result)
    }
    return
  }

  if (sub === 'rm' || sub === 'remove' || sub === 'prune') {
    const idArg = positional[1]
    if (!idArg) throw new Error('Usage: buildviz cache rm <project/build> [--version <name>]')
    const buildId = canonicalizeBuildId(idArg)
    const dir = cacheBuildDir(buildId)
    if (!existsSync(dir)) throw new Error(`No cached build "${buildId}" under ${cacheRoot}.`)

    const versionOpt = optionString(options, 'version')
    const catalog = await readCatalog()
    const protectedRevisions = pinnedCatalogRevisions(catalog)
    if (versionOpt) {
      const version = canonicalizeVersionName(versionOpt)
      const meta = await readBuildMeta(dir)
      const defaultVersion = resolveDefaultVersion(meta)
      if (protectedRevisions.some((reference) => reference.buildId === buildId &&
          reference.branch === (meta?.defaultBranch ?? DEFAULT_BRANCH_NAME) && reference.version === version)) {
        throw new Error(`${buildId}@${version} is referenced by a saved view, milestone, or as-built record and cannot be removed.`)
      }
      if (version === defaultVersion) {
        throw new Error(
          `"${version}" is the default version of ${buildId}; remove the whole build (omit --version) ` +
            'or push/freeze a different default first.',
        )
      }
      const versionDir = path.join(dir, 'versions', version)
      if (!existsSync(versionDir)) throw new Error(`No version "${version}" cached for ${buildId}.`)
      await rm(versionDir, { recursive: true, force: true })
      if (meta) {
        const nextVersions = (meta.versions ?? []).filter((entry) => {
          const name = entry.name ?? (entry as unknown as { version?: string }).version
          return name !== version
        })
        await writeFile(
          path.join(dir, 'meta.json'),
          `${JSON.stringify({ ...meta, versions: nextVersions, updatedAt: new Date().toISOString() }, null, 2)}\n`,
          'utf8',
        )
      }
      const result = { ok: true, summary: `Removed ${buildId}@${version} from the cache.`, buildId, version }
      if (options.json) printJson(result)
      else console.log(result.summary)
      return
    }

    const referencesBuild = (id: string) => id === buildId || id.startsWith(`${buildId}/`)
    if (catalog.items.some((item) => referencesBuild(item.source.buildId)) ||
        protectedRevisions.some((reference) => referencesBuild(reference.buildId))) {
      throw new Error(`${buildId} is referenced by the catalog and cannot be removed.`)
    }
    await rm(dir, { recursive: true, force: true })
    const result = {
      ok: true,
      summary: `Removed cached build ${buildId} (${cacheBuildDir(buildId)}).`,
      buildId,
      note: 'A running hub still lists it until it restarts (it prunes dead builds on restart).',
    }
    if (options.json) printJson(result)
    else {
      console.log(result.summary)
      console.log(result.note)
    }
    return
  }

  throw new Error('Usage: buildviz cache ls | buildviz cache rm <project/build> [--version <name>]')
}
