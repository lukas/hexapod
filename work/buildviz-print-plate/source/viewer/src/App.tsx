import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import { BuildViewer } from './BuildViewer'
import { ChecksPanel } from './ChecksPanel'
import { MassPanel } from './MassPanel'
import { DrawingsPanel } from './DrawingsPanel'
import { ExportPanel } from './ExportPanel'
import { isLoopbackHost } from './hostEnv'
import { MotionPanel } from './MotionPanel'
import type { BuildSceneManifest } from '../../core/buildScene'
import { routeDisplayColor } from '../../core/buildWiring'
import { defaultJointValues, type JointValues } from '../../core/buildvizKinematics'
import {
  diffManifests,
  instanceDiffStatuses,
  type DiffStatus,
  type ManifestDiff,
} from '../../core/buildDiff'
import {
  DEFAULT_BRANCH_NAME,
  DEFAULT_VERSION_NAME,
  compareVersionNames,
  groupBuildsByProject,
  joinProjectBuild,
  splitProjectBuild,
  type BuildBranchEntry,
  type BuildVersionEntry,
  type BuildsIndexBuild as BuildsIndexEntry,
  type BuildsIndexProject as ProjectGroup,
} from '../../core/buildModel'
import { compactLayoutQuery, isCompactLayout } from './compactLayout'
import type { CatalogItem } from '../../core/catalogModel'
import { CatalogDetails, CatalogHome, CatalogSidebar, ProjectBrowser, RevisionHistory } from './CatalogPanel'
import { CatalogQuickNav } from './CatalogQuickNav'
import { BuildWorkflows } from './BuildWorkflows'
import { sourceHref, sourceProblem } from './catalogLinks'
import { newVersionCommand } from '../../core/publishCommand'
import { VersionFeedbackPanel } from './VersionFeedbackPanel'

// With the tabbed sidebar each tab holds only one or two panels, so panels
// default open everywhere (mass stays collapsed: its breakdown list is long).
const getInitialControlsOpen = () => ({
  focus: true,
  tools: true,
  wiring: true,
  motion: true,
  checks: true,
  mass: false,
  diff: true,
  export: true,
  drawings: true,
  partTypes: true,
})

// Sidebar tab groups: the panel stack was one long accordion, which didn't
// scale — grouped tabs show one focused set at a time on desktop and mobile.
type SidebarTabId = 'view' | 'diff' | 'motion' | 'checks' | 'output'

// Sidebar panels the user can hide ENTIRELY (beyond collapsing): the "Panels"
// picker under the build dropdown. Hidden ids persist across sessions.
const PANEL_DEFS = [
  { id: 'focus', label: 'Focus' },
  { id: 'tools', label: 'Tools' },
  { id: 'wiring', label: 'Wiring' },
  { id: 'motion', label: 'Motion' },
  { id: 'diff', label: 'Diff' },
  { id: 'checks', label: 'Checks' },
  { id: 'mass', label: 'Mass' },
  { id: 'export', label: 'Export' },
  { id: 'drawings', label: 'Drawings' },
  { id: 'partTypes', label: 'Part Types' },
] as const
type PanelId = (typeof PANEL_DEFS)[number]['id']
const HIDDEN_PANELS_KEY = 'buildviz.hiddenPanels'

const readHiddenPanels = (): Set<PanelId> => {
  try {
    const raw = window.localStorage.getItem(HIDDEN_PANELS_KEY)
    const parsed = raw ? (JSON.parse(raw) as unknown) : []
    const known = new Set<string>(PANEL_DEFS.map((def) => def.id))
    return new Set(
      (Array.isArray(parsed) ? parsed : []).filter(
        (id): id is PanelId => typeof id === 'string' && known.has(id),
      ),
    )
  } catch {
    return new Set()
  }
}

// Data model: PROJECT -> BUILD (assembly) -> BRANCH -> NAMED VERSION. Types
// and pure helpers live in core/buildModel (shared with the CLI). The index
// lists builds whose stable id is "<project>/<build>"; each build has one or
// more branches (the default branch lives at the build root, others under
// branches/<name>/), and each branch has named versions (one default, mirrored
// at the branch root). The canonical address is project/build@branch@version.
// URL params: ?project=&build=&branch=&version=&compare=; compare accepts a
// plain version (same branch) or "branch@version" for a cross-branch diff. The
// legacy ?build=<full-id> form is still resolved for back-compat.
type BuildSelection = {
  buildId: string
  project: string
  build: string
  branch: string | null
  version: string | null
  compare: string | null
  /** Named analysis page attached to the build (?analysis=<slug>): the viewer
   * renders the analysis' derived scene instead of the build scene. */
  analysis: string | null
  manifestOverride: string | null
}

// A named analysis attached to a build (see hub analyses/<slug>/): a derived
// result scene (FEA stress fields, ...) listed at /builds/<id>/analyses.json.
type AnalysisEntry = {
  name: string
  displayName?: string
  message?: string
  sourceVersion?: string
  sourceBranch?: string
  createdAt?: string
  updatedAt?: string
}

type DiffView = {
  manifest: BuildSceneManifest
  diff: ManifestDiff
  statuses: Record<string, DiffStatus>
}

const getBuildSelection = (): BuildSelection => {
  const params = new URLSearchParams(window.location.search)
  const projectParam = params.get('project')
  const buildParam = params.get('build')
  // New form: ?project=spider&build=chassis. Legacy form: ?build=<full id>
  // (which may itself contain "/"). Fall back to the default demo build.
  // joinProjectBuild inverts splitProjectBuild so a single-segment id
  // (project === build) round-trips to one segment instead of being doubled.
  const buildId =
    projectParam && buildParam
      ? joinProjectBuild(projectParam, buildParam)
      : buildParam || 'hexapod-prototype'
  const { project, build } = splitProjectBuild(buildId)
  return {
    buildId,
    project,
    build,
    branch: params.get('branch'),
    version: params.get('version'),
    compare: params.get('compare'),
    analysis: params.get('analysis'),
    manifestOverride: params.get('manifest') || params.get('scene'),
  }
}

// Switch the analysis page in place, keeping the rest of the address
// (project/build/branch/version) untouched. null returns to the build scene.
const navigateToAnalysis = (slug: string | null) => {
  const params = new URLSearchParams(window.location.search)
  if (slug) params.set('analysis', slug)
  else params.delete('analysis')
  window.location.search = params.toString()
}

// Session color overrides are kept in React state and mirrored to localStorage,
// keyed by build id, so a user's per-partType colors survive a reload but stay
// scoped to that build. Reads/writes are defensive — any storage failure or
// malformed payload simply falls back to "no overrides".
const colorStorageKey = (buildId: string) => `buildviz:partTypeColors:${buildId}`

const loadStoredPartTypeColors = (buildId: string): Record<string, string> => {
  try {
    const raw = window.localStorage.getItem(colorStorageKey(buildId))
    if (!raw) return {}
    const parsed = JSON.parse(raw) as unknown
    if (!parsed || typeof parsed !== 'object') return {}
    return Object.fromEntries(
      Object.entries(parsed as Record<string, unknown>).filter(
        ([, value]) => typeof value === 'string',
      ),
    ) as Record<string, string>
  } catch {
    return {}
  }
}

// Human-friendly "last updated" label for a version's pushedAt timestamp:
// recent times read as "just now"/"3h ago"/"2d ago"; older ones fall back to a
// short date. The full ISO-derived locale string rides along for a hover title.
// Returns null for missing/unparseable timestamps so the caller hides the badge.
const formatLastUpdated = (iso: string | null | undefined): { relative: string; full: string } | null => {
  if (!iso) return null
  const date = new Date(iso)
  const ms = date.getTime()
  if (Number.isNaN(ms)) return null

  const diffSec = Math.max(0, Math.round((Date.now() - ms) / 1000))
  const minute = 60
  const hour = 60 * minute
  const day = 24 * hour

  let relative: string
  if (diffSec < 45) {
    relative = 'just now'
  } else if (diffSec < hour) {
    relative = `${Math.max(1, Math.round(diffSec / minute))}m ago`
  } else if (diffSec < day) {
    relative = `${Math.round(diffSec / hour)}h ago`
  } else if (diffSec < 7 * day) {
    relative = `${Math.round(diffSec / day)}d ago`
  } else {
    relative = date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
  }

  return { relative, full: date.toLocaleString() }
}

// Clip a changelog message to a single short line for compact spots (native
// <option> labels, the update pill) where multi-line wrapping isn't available.
// The full text still rides along in a title/tooltip at the call site.
const clipMessage = (message: string, max = 60): string => {
  const oneLine = message.replace(/\s+/g, ' ').trim()
  return oneLine.length > max ? `${oneLine.slice(0, max - 1).trimEnd()}…` : oneLine
}

// --- Branch helpers ----------------------------------------------------------
// A build's default branch lives at the build root (the pre-branch layout);
// every other branch under branches/<name>/ with the same internal layout. An
// index without branch data (older hub) is a single-default-branch build.
const defaultBranchOf = (entry: BuildsIndexEntry | null) =>
  entry?.defaultBranch ?? DEFAULT_BRANCH_NAME

const resolveActiveBranch = (branch: string | null, entry: BuildsIndexEntry | null) =>
  branch && branch.length > 0 ? branch : defaultBranchOf(entry)

const branchEntryFor = (branch: string | null, entry: BuildsIndexEntry | null): BuildBranchEntry | null => {
  const name = resolveActiveBranch(branch, entry)
  return entry?.branches?.find((candidate) => candidate.name === name) ?? null
}

// The versions of the branch being viewed (falling back to the build's
// default-branch mirror for older indexes without branch data).
const branchVersionsFor = (branch: string | null, entry: BuildsIndexEntry | null): BuildVersionEntry[] =>
  branchEntryFor(branch, entry)?.versions ?? entry?.versions ?? []

const branchDefaultVersionFor = (branch: string | null, entry: BuildsIndexEntry | null) => {
  const branchEntry = branchEntryFor(branch, entry)
  if (branchEntry) return branchEntry.defaultVersion
  const name = resolveActiveBranch(branch, entry)
  return name === defaultBranchOf(entry)
    ? entry?.defaultVersion ?? DEFAULT_VERSION_NAME
    : DEFAULT_VERSION_NAME
}

const isDefaultVersion = (
  version: string | null,
  branch: string | null,
  entry: BuildsIndexEntry | null,
) => !version || version === 'latest' || version === branchDefaultVersionFor(branch, entry)

// A branch's default version lives at the branch root scene.json (the BUILD
// root for the default branch); any other named version under versions/<name>/.
// (The hub/local servers also fall back to the branch root when
// versions/<default> is requested but not materialized.)
const manifestUrlFor = (
  buildId: string,
  branch: string | null,
  version: string | null,
  entry: BuildsIndexEntry | null,
  pinned = false,
) => {
  const activeBranch = resolveActiveBranch(branch, entry)
  const base =
    activeBranch === defaultBranchOf(entry)
      ? `/builds/${buildId}`
      : `/builds/${buildId}/branches/${encodeURIComponent(activeBranch)}`
  return !(pinned && version && version !== 'latest') && isDefaultVersion(version, branch, entry)
    ? `${base}/scene.json`
    : `${base}/versions/${encodeURIComponent(version!)}/scene.json`
}

// A compare ref is either a plain version on the SAME branch as the viewed
// scene, or "branch@version" (or "branch@", meaning that branch's default) for
// a cross-branch diff.
const parseCompareRef = (
  compare: string,
  activeBranch: string | null,
  entry: BuildsIndexEntry | null,
): { branch: string | null; version: string | null } => {
  const at = compare.indexOf('@')
  if (at > 0) {
    const version = compare.slice(at + 1)
    return { branch: compare.slice(0, at), version: version.length > 0 ? version : null }
  }
  return { branch: resolveActiveBranch(activeBranch, entry), version: compare }
}

// Resolve the version name actually being viewed for a build entry, mirroring
// BuildDropdown's activeVersion logic: an explicit ?version= wins, otherwise the
// viewed branch's default version. Used by the live-refresh "new version" detection.
const resolveActiveVersion = (selection: BuildSelection, entry: BuildsIndexEntry | null) =>
  !selection.version || selection.version === 'latest'
    ? branchDefaultVersionFor(selection.branch, entry)
    : selection.version

const getDesignSpecUrl = () => {
  const params = new URLSearchParams(window.location.search)
  return params.get('designSpec')
}

const navigateToBuild = (
  buildId: string,
  branch: string | null,
  version: string | null,
  compare: string | null,
) => {
  const params = new URLSearchParams()
  const { project, build } = splitProjectBuild(buildId)
  params.set('project', project)
  params.set('build', build)
  if (branch) params.set('branch', branch)
  if (version && version !== 'latest') params.set('version', version)
  if (compare) params.set('compare', compare)
  const previous = new URLSearchParams(window.location.search)
  const catalogContext = previous.get('catalog') ?? previous.get('catalogContext')
  if (catalogContext) params.set('catalogContext', catalogContext)
  window.location.search = params.toString()
}

// Renders the "to" version with the removed instances from the "from" version
// ghosted in, so the diff can show added, removed, moved, and changed parts.
const buildDiffView = (
  fromManifest: BuildSceneManifest,
  toManifest: BuildSceneManifest,
): DiffView => {
  const diff = diffManifests(fromManifest, toManifest)
  const toMeshIds = new Set(toManifest.meshes.map((mesh) => mesh.id))
  const toInstanceIds = new Set(toManifest.instances.map((instance) => instance.id))

  return {
    manifest: {
      ...toManifest,
      meshes: [
        ...toManifest.meshes,
        ...fromManifest.meshes.filter((mesh) => !toMeshIds.has(mesh.id)),
      ],
      instances: [
        ...toManifest.instances,
        ...fromManifest.instances.filter((instance) => !toInstanceIds.has(instance.id)),
      ],
    },
    diff,
    statuses: instanceDiffStatuses(diff),
  }
}

type VersionUpdateHint = { label: string; target: string; key: string; message?: string }

// "Open STL folder": every assembly gets a link that reveals its STL directory
// in the OS file manager, whenever that is possible — the viewer must be loaded
// from the same machine as the hub (loopback) and the hub must be able to
// locate the build's STL files on disk. The hub resolves the directory
// (GET /__buildviz/stl-dir); the click reveals it via the existing sandboxed
// POST /__buildviz/open-path. When either half is unavailable (remote hub,
// static file server, meshes not on disk) the link simply does not render.
const StlFolderLink = ({ selection }: { selection: BuildSelection }) => {
  const { buildId, branch } = selection
  // "latest" is the viewer's alias for the branch default; the hub resolves
  // the default from the root scene.json, so omit the param entirely.
  const version = !selection.version || selection.version === 'latest' ? null : selection.version
  const selectionKey = `${buildId}@${branch ?? ''}@${version ?? ''}`

  // Results are stored WITH the selection key they were fetched for, so
  // navigating to another build/version hides a stale link immediately without
  // a reset-in-effect (same pattern as the design-spec warnings in App).
  const [fetched, setFetched] = useState<{ key: string; path: string; fileCount: number } | null>(
    null,
  )
  const [openError, setOpenError] = useState<{ key: string; message: string } | null>(null)

  useEffect(() => {
    if (!isLoopbackHost() || !buildId) return
    const params = new URLSearchParams({ build: buildId })
    if (branch) params.set('branch', branch)
    if (version) params.set('version', version)
    let cancelled = false
    void (async () => {
      try {
        const response = await fetch(`/__buildviz/stl-dir?${params.toString()}`)
        const contentType = response.headers.get('content-type') ?? ''
        if (!response.ok || !contentType.includes('application/json')) return
        const body = (await response.json()) as { ok?: boolean; path?: string; fileCount?: number }
        if (!cancelled && body.ok && body.path) {
          setFetched({ key: selectionKey, path: body.path, fileCount: body.fileCount ?? 0 })
        }
      } catch {
        // No hub behind this server (or network hiccup): show no link.
      }
    })()
    return () => {
      cancelled = true
    }
  }, [buildId, branch, version, selectionKey])

  const info = fetched && fetched.key === selectionKey ? fetched : null
  if (!info) return null
  const error = openError && openError.key === selectionKey ? openError.message : null

  const openFolder = async () => {
    setOpenError(null)
    try {
      const response = await fetch('/__buildviz/open-path', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: info.path }),
      })
      const body = (await response.json()) as { ok?: boolean; error?: string }
      if (!response.ok || body.ok === false) {
        throw new Error(body.error ?? `Open failed (${response.status})`)
      }
    } catch (caught) {
      setOpenError({
        key: selectionKey,
        message: caught instanceof Error ? caught.message : String(caught),
      })
    }
  }

  return (
    <div className="stl-folder">
      <button
        type="button"
        className="stl-folder-link"
        onClick={() => void openFolder()}
        title={`Reveal ${info.path} in the file manager`}
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z" />
        </svg>
        <span>Open STL folder</span>
        <small>
          {info.fileCount} STL{info.fileCount === 1 ? '' : 's'}
        </small>
      </button>
      {error ? <p className="stl-folder-error">{error}</p> : null}
    </div>
  )
}

type BuildDropdownProps = {
  hasCatalogContext?: boolean
  buildsIndex: BuildsIndexEntry[] | null
  projects: ProjectGroup[]
  selection: BuildSelection
  currentBuildEntry: BuildsIndexEntry | null
  diffCounts: ManifestDiff['counts'] | null
  // A subtle, dismissible "new version available" affordance for the viewed
  // build, surfaced by the live index poll. null when there is nothing new.
  versionUpdate: VersionUpdateHint | null
  onApplyVersionUpdate: () => void
  onDismissVersionUpdate: () => void
  // Design-spec warnings for the viewed build/version (missing spec, scene
  // parts with no entry, stale entries). Empty ⇒ no badge.
  specWarnings: string[]
}

// Compact, collapsed-by-default selector for the PROJECT -> BUILD -> named
// VERSION model. The trigger shows "project / build @ version"; the popover
// holds cascading Project, Build, and Version selects (plus Compare for the
// diff view). Native <select>s keep it compact and mobile-friendly, matching
// the bottom-drawer layout.
const BuildDropdown = ({
  hasCatalogContext,
  buildsIndex,
  projects,
  selection,
  currentBuildEntry,
  diffCounts,
  versionUpdate,
  onApplyVersionUpdate,
  onDismissVersionUpdate,
  specWarnings,
}: BuildDropdownProps) => {
  const [open, setOpen] = useState(false)
  const [specOpen, setSpecOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return

    const handlePointerDown = (event: PointerEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false)
        triggerRef.current?.focus()
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open])

  const selectedProject = currentBuildEntry?.project ?? selection.project
  const selectedBuildLabel = currentBuildEntry?.name ?? selection.build
  const projectBuilds = projects.find((project) => project.id === selectedProject)?.builds ?? []
  // Branches of the viewed build (older indexes without branch data behave as a
  // single default branch). Versions are always scoped to the ACTIVE branch.
  const branches = currentBuildEntry?.branches ?? []
  const defaultBranch = defaultBranchOf(currentBuildEntry)
  const activeBranch = resolveActiveBranch(selection.branch, currentBuildEntry)
  const versions = branchVersionsFor(selection.branch, currentBuildEntry)
  const activeVersion =
    !selection.version || selection.version === 'latest'
      ? branchDefaultVersionFor(selection.branch, currentBuildEntry)
      : selection.version
  // The URL param for a branch: omitted for the default branch (clean URLs,
  // back-compat with pre-branch links).
  const branchParamFor = (name: string) => (name === defaultBranch ? null : name)
  // "Last updated" badge for whatever version is currently being viewed
  // (respecting ?version=). pushedAt is the explicit meta time when known and
  // otherwise the version scene.json's mtime fallback (filled by the index), so
  // this is hidden only in the truly-impossible no-scene case.
  const activeVersionEntry = versions.find((version) => version.name === activeVersion)
  const activeVersionPushedAt = activeVersionEntry?.pushedAt
  const lastUpdated = formatLastUpdated(activeVersionPushedAt)
  // The currently-viewed version's optional changelog note, shown by the badge.
  const activeVersionMessage = activeVersionEntry?.message
  const publishCommand = newVersionCommand(selection.buildId, activeBranch)
  const [publishCopyStatus, setPublishCopyStatus] = useState('')

  const selectProject = (projectId: string) => {
    const first = projects.find((project) => project.id === projectId)?.builds[0]
    if (first) {
      setOpen(false)
      navigateToBuild(first.id, null, null, null)
    }
  }

  return (
    <div className="build-dropdown" ref={containerRef}>
      <button
        type="button"
        ref={triggerRef}
        className={`build-dropdown-trigger ${open ? 'open' : ''}`}
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        <span className="build-dropdown-meta">
          <span className="build-dropdown-label">{hasCatalogContext ? 'Revision & comparison' : selectedProject}</span>
          <span className="build-dropdown-name">{hasCatalogContext ? activeVersion : selectedBuildLabel}</span>
          <span className="build-dropdown-tags">
            <small>
              @{hasCatalogContext ? activeBranch : activeBranch === defaultBranch ? activeVersion : `${activeBranch}@${activeVersion}`}
            </small>
            {selection.compare ? <small>vs {selection.compare}</small> : null}
          </span>
        </span>
        <svg className="build-dropdown-chevron" viewBox="0 0 24 24" aria-hidden="true">
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      {diffCounts ? (
        <div className="diff-legend">
          <span className="diff-chip diff-added">{diffCounts.addedInstances} added</span>
          <span className="diff-chip diff-removed">{diffCounts.removedInstances} removed</span>
          <span className="diff-chip diff-changed">
            {diffCounts.movedInstances + diffCounts.changedInstances} moved/changed
          </span>
        </div>
      ) : null}

      {lastUpdated ? (
        <p className="build-dropdown-updated" title={`Last updated ${lastUpdated.full}`}>
          updated {lastUpdated.relative}
        </p>
      ) : null}

      {activeVersionMessage ? (
        <p className="build-dropdown-message" title={activeVersionMessage}>
          {activeVersionEntry?.messageSource === 'retrospective' ? <small className="revision-retrospective">Description reconstructed later</small> : null}
          {activeVersionMessage}
        </p>
      ) : null}

      <VersionFeedbackPanel key={`${selection.buildId}@${activeBranch}@${activeVersion}`}
        buildId={selection.buildId} branch={activeBranch} version={activeVersion}
        reason={activeVersionEntry?.reason} />

      {specWarnings.length > 0 ? (
        <div className="build-dropdown-spec">
          <button
            type="button"
            className="build-dropdown-spec-toggle"
            aria-expanded={specOpen}
            onClick={() => setSpecOpen((current) => !current)}
            title={specWarnings.join('\n')}
          >
            <span aria-hidden="true">⚠</span>
            <span>
              design spec: {specWarnings.length} warning{specWarnings.length === 1 ? '' : 's'}
            </span>
          </button>
          {specOpen ? (
            <ul className="build-dropdown-spec-list">
              {specWarnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
              <li className="build-dropdown-spec-hint">
                design_spec.yaml records what each part is for — update it in the same change that
                alters geometry.
              </li>
            </ul>
          ) : null}
        </div>
      ) : null}

      {versionUpdate ? (
        <div className="build-dropdown-update" role="status">
          <button
            type="button"
            className="build-dropdown-update-apply"
            onClick={onApplyVersionUpdate}
            title={versionUpdate.message ? `Load ${versionUpdate.target}: ${versionUpdate.message}` : `Load ${versionUpdate.target}`}
          >
            <span className="build-dropdown-update-dot" aria-hidden="true" />
            <span className="build-dropdown-update-text">
              <span>{versionUpdate.label} available</span>
              {versionUpdate.message ? (
                <small className="build-dropdown-update-message">{clipMessage(versionUpdate.message, 80)}</small>
              ) : null}
            </span>
          </button>
          <button
            type="button"
            className="build-dropdown-update-dismiss"
            onClick={onDismissVersionUpdate}
            aria-label="Dismiss new version notice"
            title="Dismiss"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M6 6l12 12M18 6 6 18" />
            </svg>
          </button>
        </div>
      ) : null}

      {open ? (
        <div
          className="build-dropdown-panel"
          role="dialog"
          aria-label="Select a project, build, and version"
        >
          {buildsIndex === null ? (
            <p className="build-menu-note">
              No build index found. Serve a <code>/builds/index.json</code> to list builds.
            </p>
          ) : (
            <div className="build-dropdown-selects">
              <label className="select-control">
                <span>Project</span>
                <select
                  value={selectedProject}
                  onChange={(event) => selectProject(event.target.value)}
                >
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.id}
                    </option>
                  ))}
                </select>
              </label>
              <label className="select-control">
                <span>Build</span>
                <select
                  value={currentBuildEntry?.id ?? selection.buildId}
                  onChange={(event) => {
                    setOpen(false)
                    navigateToBuild(event.target.value, null, null, null)
                  }}
                >
                  {projectBuilds.map((entry) => (
                    <option key={entry.id} value={entry.id}>
                      {entry.name ?? entry.build}
                    </option>
                  ))}
                </select>
              </label>
              {branches.length > 1 ? (
                <label className="select-control">
                  <span>Branch</span>
                  <select
                    value={activeBranch}
                    onChange={(event) =>
                      navigateToBuild(selection.buildId, branchParamFor(event.target.value), null, null)
                    }
                  >
                    {branches.map((branch) => (
                      <option key={branch.name} value={branch.name}>
                        {branch.name}
                        {branch.isDefault ? ' (default)' : ''}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
              {versions.length > 0 ? (
                <label className="select-control">
                  <span>Version</span>
                  <select
                    value={activeVersion}
                    onChange={(event) =>
                      navigateToBuild(
                        selection.buildId,
                        selection.branch,
                        event.target.value,
                        selection.compare,
                      )
                    }
                  >
                    {versions.map((version) => (
                      <option key={version.name} value={version.name} title={version.message ?? undefined}>
                        {version.name}
                        {version.isDefault ? ' (default)' : ''}
                        {version.message ? ` — ${clipMessage(version.message)}` : ''}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
              <details className="build-publish-help">
                <summary>Publish a new version…</summary>
                <p>Keep this version for comparison. Publish edits as a new version;
                  don’t replace an existing version name.</p>
                <p>First read this version’s issues and lessons. Use <code>--reason</code> to
                  explain why the next revision is needed, and <code>-m</code> for what changed.
                  Record problems on the affected older version; return with validation evidence.</p>
                <textarea aria-label="New version publish command" readOnly value={publishCommand}
                  rows={5} onFocus={(event) => event.currentTarget.select()} />
                <button type="button" onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(publishCommand)
                    setPublishCopyStatus('Copied. No build was changed.')
                  } catch {
                    setPublishCopyStatus('Select and copy the command above.')
                  }
                }}>Copy new-version command</button>
                <p>Run in your project directory with the updated scene. The CLI uses
                  your local hub. This uploads meshes and keeps the current default;
                  remove <code>--no-default</code> to promote the new version.</p>
                <span role="status">{publishCopyStatus}</span>
              </details>
              {versions.length > 1 || branches.length > 1 ? (
                <label className="select-control">
                  <span>Compare with</span>
                  <select
                    value={selection.compare ?? ''}
                    onChange={(event) =>
                      navigateToBuild(
                        selection.buildId,
                        selection.branch,
                        selection.version,
                        event.target.value || null,
                      )
                    }
                  >
                    <option value="">None</option>
                    {branches.length > 1 ? (
                      // Cross-branch compare: group options per branch. Same-
                      // branch refs stay plain version names; other branches use
                      // the "branch@version" ref form.
                      branches.map((branch) => (
                        <optgroup key={branch.name} label={branch.name}>
                          {branch.versions.map((version) => (
                            <option
                              key={`${branch.name}@${version.name}`}
                              value={
                                branch.name === activeBranch
                                  ? version.name
                                  : `${branch.name}@${version.name}`
                              }
                            >
                              {branch.name}@{version.name}
                            </option>
                          ))}
                        </optgroup>
                      ))
                    ) : (
                      versions.map((version) => (
                        <option key={version.name} value={version.name}>
                          {version.name}
                        </option>
                      ))
                    )}
                  </select>
                </label>
              ) : null}
            </div>
          )}
        </div>
      ) : null}
    </div>
  )
}

type DiffPanelProps = {
  diff: ManifestDiff
  fromVersion: string
  toVersion: string
  // The "to" version's optional changelog note, shown in the panel header so a
  // reviewer sees what that revision claims to change. Absent ⇒ nothing extra.
  toMessage?: string
  open: boolean
  modeKey: string
  onToggleOpen: (open: boolean) => void
}

// Compare-mode diff summary: counts plus the added / removed / moved / changed
// instance lists. Clicking an entry highlights that instance in the viewer via
// the same window.buildviz channel the Checks + Part Types lists use, so the
// reviewer can jump straight to a changed part.
const DiffPanel = ({ diff, fromVersion, toVersion, toMessage, open, modeKey, onToggleOpen }: DiffPanelProps) => {
  const { instances, meshes, counts } = diff
  const highlightInstance = (instanceId: string, note: string) => {
    window.buildviz?.setHighlights({ parts: [{ instanceId, annotation: note }] })
  }
  const total =
    counts.addedInstances + counts.removedInstances + counts.movedInstances + counts.changedInstances

  const rows: Array<{ key: string; cls: string; instanceId: string; label: string; note: string }> = [
    ...instances.added.map((item) => ({
      key: `a-${item.instanceId}`,
      cls: 'diff-added',
      instanceId: item.instanceId,
      label: `+ ${item.instanceId}`,
      note: `Added (${item.partType})`,
    })),
    ...instances.removed.map((item) => ({
      key: `r-${item.instanceId}`,
      cls: 'diff-removed',
      instanceId: item.instanceId,
      label: `− ${item.instanceId}`,
      note: `Removed (${item.partType})`,
    })),
    ...instances.moved.map((item) => ({
      key: `m-${item.instanceId}`,
      cls: 'diff-changed',
      instanceId: item.instanceId,
      label: `~ ${item.instanceId}`,
      note: `Moved [${item.translationMm.join(', ')}] mm (${item.partType})`,
    })),
    ...instances.changed.map((item) => ({
      key: `c-${item.instanceId}`,
      cls: 'diff-changed',
      instanceId: item.instanceId,
      label: `~ ${item.instanceId}`,
      note: `Changed: ${item.changes.join(', ')} (${item.partType})`,
    })),
  ]

  return (
    <details
      className="control-group diff-panel"
      open={open}
      key={`diff-${modeKey}`}
      onToggle={(event) => onToggleOpen(event.currentTarget.open)}
    >
      <summary>
        <span>Diff</span>
        <small>
          {fromVersion} → {toVersion}
        </small>
      </summary>
      <div className="control-content diff-panel-content">
        {toMessage ? (
          <p className="diff-message" title={toMessage}>
            <strong>{toVersion}:</strong> {toMessage}
          </p>
        ) : null}
        <div className="diff-counts">
          <span className="diff-chip diff-added">{counts.addedInstances} added</span>
          <span className="diff-chip diff-removed">{counts.removedInstances} removed</span>
          <span className="diff-chip diff-changed">{counts.movedInstances} moved</span>
          <span className="diff-chip diff-changed">{counts.changedInstances} changed</span>
        </div>
        <p className="diff-meshes-note">
          Meshes: {counts.addedMeshes} added · {counts.removedMeshes} removed · {counts.changedMeshes} changed.
        </p>
        {total === 0 ? (
          <p className="diff-empty">No instance-level changes between these versions.</p>
        ) : (
          <ul className="diff-list">
            {rows.map((row) => (
              <li key={row.key}>
                <button
                  type="button"
                  className={`diff-row ${row.cls}`}
                  onClick={() => highlightInstance(row.instanceId, row.note)}
                  title={`Highlight ${row.instanceId} — ${row.note}`}
                >
                  <span className="diff-row-id">{row.label}</span>
                  <span className="diff-row-note">{row.note}</span>
                </button>
              </li>
            ))}
            {meshes.changed.length > 0
              ? meshes.changed.map((mesh) => (
                  <li key={`mesh-${mesh.meshId}`}>
                    <span className="diff-row diff-changed diff-row-static">
                      <span className="diff-row-id">⬡ {mesh.meshId}</span>
                      <span className="diff-row-note">mesh changed: {mesh.changes.join(', ')}</span>
                    </span>
                  </li>
                ))
              : null}
          </ul>
        )}
      </div>
    </details>
  )
}

type RawVersion = string | { name?: unknown; isDefault?: unknown; pushedAt?: unknown; message?: unknown; reason?: unknown; messageSource?: unknown; messageUpdatedAt?: unknown }
type RawBranch = { name?: unknown; isDefault?: unknown; defaultVersion?: unknown; versions?: unknown }
type RawBuildEntry = {
  id?: unknown
  project?: unknown
  build?: unknown
  name?: unknown
  defaultVersion?: unknown
  versions?: unknown
  defaultBranch?: unknown
  branches?: unknown
}

// Normalize an index build entry into the viewer shape, tolerating both the new
// hierarchical format (versions as { name, isDefault }, plus project/build/
// defaultVersion) and any older format (versions as a string[]). The default
// version is always present and flagged.
const normalizeVersionList = (rawVersions: RawVersion[], defaultHint: string | null) => {
  let versions: BuildVersionEntry[] = rawVersions
    .map((entry) =>
      typeof entry === 'string'
        ? { name: entry, isDefault: false, pushedAt: null }
        : {
            name: typeof entry.name === 'string' ? entry.name : '',
            isDefault: entry.isDefault === true,
            pushedAt: typeof entry.pushedAt === 'string' ? entry.pushedAt : null,
            ...(typeof entry.message === 'string' && entry.message.length > 0
              ? { message: entry.message }
              : {}),
            ...(typeof entry.reason === 'string' && entry.reason.length > 0 ? { reason: entry.reason } : {}),
            ...(entry.messageSource === 'retrospective' ? { messageSource: 'retrospective' as const } : {}),
            ...(typeof entry.messageUpdatedAt === 'string' ? { messageUpdatedAt: entry.messageUpdatedAt } : {}),
          },
    )
    .filter((entry) => entry.name.length > 0)
  const defaultVersion =
    defaultHint ?? versions.find((entry) => entry.isDefault)?.name ?? DEFAULT_VERSION_NAME
  if (!versions.some((entry) => entry.name === defaultVersion)) {
    versions = [{ name: defaultVersion, isDefault: true, pushedAt: null }, ...versions]
  }
  versions = versions.map((entry) => ({
    name: entry.name,
    isDefault: entry.name === defaultVersion,
    pushedAt: entry.pushedAt ?? null,
    ...(entry.message ? { message: entry.message } : {}),
    ...(entry.reason ? { reason: entry.reason } : {}),
    ...(entry.messageSource ? { messageSource: entry.messageSource } : {}),
    ...(entry.messageUpdatedAt ? { messageUpdatedAt: entry.messageUpdatedAt } : {}),
  }))
  return { versions, defaultVersion }
}

const normalizeIndexEntry = (raw: RawBuildEntry): BuildsIndexEntry => {
  const id = typeof raw.id === 'string' ? raw.id : ''
  const split = splitProjectBuild(id)
  const { versions, defaultVersion } = normalizeVersionList(
    Array.isArray(raw.versions) ? (raw.versions as RawVersion[]) : [],
    typeof raw.defaultVersion === 'string' ? raw.defaultVersion : null,
  )
  // Branch tree (additive): older indexes carry none, which the viewer treats
  // as a single default branch mirroring the top-level version list.
  const defaultBranch = typeof raw.defaultBranch === 'string' ? raw.defaultBranch : DEFAULT_BRANCH_NAME
  const rawBranches = Array.isArray(raw.branches) ? (raw.branches as RawBranch[]) : []
  let branches: BuildBranchEntry[] = rawBranches
    .filter((entry) => typeof entry.name === 'string' && entry.name.length > 0)
    .map((entry) => {
      const branchNormalized = normalizeVersionList(
        Array.isArray(entry.versions) ? (entry.versions as RawVersion[]) : [],
        typeof entry.defaultVersion === 'string' ? entry.defaultVersion : null,
      )
      return {
        name: entry.name as string,
        isDefault: (entry.name as string) === defaultBranch,
        defaultVersion: branchNormalized.defaultVersion,
        versions: branchNormalized.versions,
      }
    })
  if (!branches.some((entry) => entry.isDefault)) {
    branches = [{ name: defaultBranch, isDefault: true, defaultVersion, versions }, ...branches]
  }
  return {
    id,
    project: typeof raw.project === 'string' ? raw.project : split.project,
    build: typeof raw.build === 'string' ? raw.build : split.build,
    name: typeof raw.name === 'string' ? raw.name : null,
    defaultVersion,
    versions,
    defaultBranch,
    branches,
  }
}

// Conditional fetch of /builds/index.json, shared by the initial load and the
// live poller. The caller passes the last seen ETag + raw body so an unchanged
// index is a no-op:
//   * a matching If-None-Match returns 304 (the hub sets a content ETag), and
//   * as a server-agnostic fallback, an identical raw body is treated the same.
// This keeps the poll cheap and prevents needless React churn. 'error' (network
// hiccup, non-JSON, malformed) is reported separately from a real empty index so
// the poller can simply keep showing the current menu on a transient failure.
type IndexFetchResult =
  | { status: 'unchanged' }
  | { status: 'error' }
  | { status: 'ok'; builds: BuildsIndexEntry[]; etag: string | null; bodyText: string }

const fetchBuildsIndex = async (prevEtag: string | null, prevBody: string | null): Promise<IndexFetchResult> => {
  try {
    const headers: Record<string, string> = {}
    if (prevEtag) headers['If-None-Match'] = prevEtag
    const response = await fetch('/builds/index.json', { headers, cache: 'no-cache' })
    if (response.status === 304) return { status: 'unchanged' }
    if (!response.ok) return { status: 'error' }
    const contentType = response.headers.get('content-type') ?? ''
    if (!contentType.includes('application/json')) return { status: 'error' }
    const bodyText = await response.text()
    if (prevBody !== null && bodyText === prevBody) return { status: 'unchanged' }
    let index: { builds?: unknown[] }
    try {
      index = JSON.parse(bodyText) as { builds?: unknown[] }
    } catch {
      return { status: 'error' }
    }
    if (!Array.isArray(index.builds)) return { status: 'error' }
    const builds = index.builds.map((entry) => normalizeIndexEntry(entry as RawBuildEntry))
    return { status: 'ok', builds, etag: response.headers.get('etag'), bodyText }
  } catch {
    return { status: 'error' }
  }
}

const loadManifest = async (manifestUrl: string) => {
  const response = await fetch(manifestUrl)
  const body = await response.text()
  const contentType = response.headers.get('content-type') ?? 'unknown content type'

  if (!response.ok) {
    throw new Error(`Could not load ${manifestUrl}: ${response.status} ${response.statusText}`)
  }

  if (!contentType.includes('application/json')) {
    throw new Error(
      `Expected JSON at ${manifestUrl}, got ${contentType}. First bytes: ${body.slice(0, 40)}`,
    )
  }

  return JSON.parse(body) as BuildSceneManifest
}

type CatalogContext = { item: CatalogItem; items: CatalogItem[]; source: CatalogItem['source']; configuration: string }

function BuildApp({ catalog, selectedSource, catalogItems = [], initialBuilds = [] }: { catalog?: CatalogContext; selectedSource?: CatalogItem['source']; catalogItems?: CatalogItem[]; initialBuilds?: BuildsIndexEntry[] }) {
  const [manifest, setManifest] = useState<BuildSceneManifest | null>(null)
  const [diffView, setDiffView] = useState<DiffView | null>(null)
  const [buildsIndex, setBuildsIndex] = useState<BuildsIndexEntry[] | null>(null)
  // Gate manifest loading until the build index has been fetched so we know each
  // build's default version (and thus the correct scene.json URL).
  const [indexLoaded, setIndexLoaded] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [visiblePartTypes, setVisiblePartTypes] = useState<Set<string>>(new Set())
  const [highlightedPartType, setHighlightedPartType] = useState<string | null>(null)
  // Part type of the instance currently selected in the 3D view (reported by
  // BuildViewer); its row in the Part Types list is marked and scrolled to.
  const [selectedPartType, setSelectedPartType] = useState<string | null>(null)
  // Per-partType color overrides for this build, seeded from localStorage. The
  // buildId comes from the URL and is stable for the page's lifetime, so it is
  // safe to read once here for the initial state.
  const [partTypeColors, setPartTypeColors] = useState<Record<string, string>>(() =>
    loadStoredPartTypeColors(getBuildSelection().buildId),
  )
  const [focusGroup, setFocusGroup] = useState<string | null>(null)
  // Phase 3 pose scrubber state. Resets to the home pose whenever the build (and
  // thus its joints) changes; empty for scenes that carry no joints.
  const [jointValues, setJointValues] = useState<JointValues>({})
  const [rulerMode, setRulerMode] = useState(false)
  // Wires layer (routes[] rendered as tubes). On by default when the scene
  // publishes wires; the Wiring control group only renders when routes exist.
  const [showWires, setShowWires] = useState(!catalog?.item.view)
  const [pickerMode, setPickerMode] = useState(false)
  // Free-text filter for the Part Types list (find a type/instance fast in large
  // builds). Matches the part type name plus any instance name/id of that type.
  const [partTypeFilter, setPartTypeFilter] = useState('')
  const [usesCompactControls, setUsesCompactControls] = useState(isCompactLayout)
  const [openControls, setOpenControls] = useState(getInitialControlsOpen)
  const [activeTab, setActiveTab] = useState<SidebarTabId>('view')
  // Mobile only: the bottom sheet can be minimized to a slim handle so the
  // 3D view gets the whole screen. Desktop CSS ignores the class entirely.
  const [sheetCollapsed, setSheetCollapsed] = useState(false)
  // Pending "draw this part" request from the viewer's right-click menu.
  const [drawingRequest, setDrawingRequest] = useState<{ partType: string; nonce: number } | null>(null)
  // Panels the user has hidden entirely via the "Panels" picker (persisted).
  const [hiddenPanels, setHiddenPanels] = useState<Set<PanelId>>(readHiddenPanels)
  const [panelPickerOpen, setPanelPickerOpen] = useState(false)
  // Live index refresh bookkeeping. The ETag + last raw body let the poller skip
  // a no-op refresh cheaply; the baseline refs snapshot the current build's
  // versions at the moment its scene loaded, so we can detect a newly published
  // version (or an in-place re-push of the viewed version) WITHOUT disturbing the
  // loaded scene. dismissedUpdateKey hides the "new version" hint until something
  // newer arrives.
  const indexEtagRef = useRef<string | null>(null)
  const indexBodyRef = useRef<string | null>(null)
  // The viewed build's version baseline, snapshotted once when its scene loads.
  // State (not a ref) so the version-update comparison can run during render.
  const [versionBaseline, setVersionBaseline] = useState<{
    names: Set<string>
    activePushedAt: string | null
  } | null>(null)
  const [dismissedUpdateKey, setDismissedUpdateKey] = useState<string | null>(null)
  const selection = useMemo(() => {
    const original = getBuildSelection()
    if (!selectedSource) return original
    return {
      ...original,
      ...splitProjectBuild(selectedSource.buildId),
      buildId: selectedSource.buildId,
      branch: selectedSource.branch ?? null,
      version: selectedSource.version ?? null,
      manifestOverride: null,
      analysis: null,
    }
  }, [selectedSource])
  const projects = useMemo(() => groupBuildsByProject(buildsIndex ?? []), [buildsIndex])
  const currentBuildEntry = useMemo(
    () => buildsIndex?.find((entry) => entry.id === selection.buildId) ?? null,
    [buildsIndex, selection.buildId],
  )
  const manifestUrl = useMemo(
    () =>
      selection.manifestOverride ??
      (selection.analysis
        ? `/builds/${selection.buildId}/analyses/${encodeURIComponent(selection.analysis)}/scene.json`
        : manifestUrlFor(selection.buildId, selection.branch, selection.version, currentBuildEntry, Boolean(selectedSource))),
    [selection, currentBuildEntry, selectedSource],
  )
  // The "from" scene URL in compare mode. Resolved alongside manifestUrl so the
  // load effect can depend on plain URL STRINGS rather than the currentBuildEntry
  // object: a live index refresh that re-creates the entry (same default version)
  // keeps these strings stable, so the loaded scene is never reloaded out from
  // under the user just because the menu options refreshed.
  const compareManifestUrl = useMemo(() => {
    if (!selection.compare || selection.manifestOverride) return null
    // The compare ref may be a plain version (same branch) or a cross-branch
    // "branch@version" / "branch@" ref.
    const ref = parseCompareRef(selection.compare, selection.branch, currentBuildEntry)
    return manifestUrlFor(selection.buildId, ref.branch, ref.version, currentBuildEntry)
  }, [selection, currentBuildEntry])
  const designSpecUrl = useMemo(() => selectedSource?.version && selectedSource.version !== 'latest'
    ? manifestUrl.replace(/scene\.json$/, 'design_spec.yaml')
    : getDesignSpecUrl(), [selectedSource, manifestUrl])
  // The checks sidecar lives next to scene.json (buildviz_checks.json). It is not
  // meaningful for the synthetic diff scene, so it is skipped in compare mode.
  const checksSidecarUrl = useMemo(
    () =>
      selection.compare || selection.analysis || !manifestUrl.endsWith('scene.json')
        ? null
        : `${manifestUrl.slice(0, -'scene.json'.length)}buildviz_checks.json`,
    [manifestUrl, selection.compare, selection.analysis],
  )

  // Named analyses attached to the viewed build (independent of the index; an
  // empty/missing list simply hides the Analyses picker).
  const [analyses, setAnalyses] = useState<AnalysisEntry[]>([])
  useEffect(() => {
    if (selection.manifestOverride) return
    let cancelled = false
    fetch(`/builds/${selection.buildId}/analyses.json`)
      .then((response) => (response.ok ? response.json() : null))
      .then((payload: { analyses?: AnalysisEntry[] } | null) => {
        if (!cancelled && payload && Array.isArray(payload.analyses)) setAnalyses(payload.analyses)
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [selection.buildId, selection.manifestOverride])
  const activeAnalysis = selection.analysis
    ? analyses.find((entry) => entry.name === selection.analysis) ?? { name: selection.analysis }
    : null

  useEffect(() => {
    const mediaQuery = window.matchMedia(compactLayoutQuery)
    const updateControlsMode = (event: MediaQueryListEvent) => {
      setUsesCompactControls(event.matches)
    }

    mediaQuery.addEventListener('change', updateControlsMode)

    return () => mediaQuery.removeEventListener('change', updateControlsMode)
  }, [])

  useEffect(() => {
    // Wait for the index (which carries each build's default version) before
    // resolving scene URLs, unless an explicit ?manifest=/?scene= override is set.
    if (!indexLoaded && !selection.manifestOverride) return
    let cancelled = false

    const load = async () => {
      if (compareManifestUrl) {
        const [fromManifest, toManifest] = await Promise.all([
          loadManifest(compareManifestUrl),
          loadManifest(manifestUrl),
        ])
        const view = buildDiffView(fromManifest, toManifest)
        if (cancelled) return
        setDiffView(view)
        setManifest(view.manifest)
        setVisiblePartTypes(new Set(view.manifest.instances.map((instance) => instance.partType)))
        return
      }

      const nextManifest = await loadManifest(manifestUrl)
      if (cancelled) return
      setDiffView(null)
      setManifest(nextManifest)
      setVisiblePartTypes(new Set(nextManifest.instances.map((instance) => instance.partType)))
    }

    load().catch((error: unknown) => {
      if (cancelled) return
      setLoadError(error instanceof Error ? error.message : String(error))
    })

    return () => {
      cancelled = true
    }
  }, [indexLoaded, manifestUrl, compareManifestUrl, selection.manifestOverride])

  // Snapshot the viewed build's version baseline from a freshly fetched index so
  // later polls can tell "a version appeared / the viewed version was re-pushed"
  // apart from "nothing changed". Skipped for ?manifest=/?scene= overrides, where
  // the loaded scene is not an index version.
  const captureVersionBaseline = (builds: BuildsIndexEntry[]) => {
    if (selection.manifestOverride) return
    const entry = builds.find((build) => build.id === selection.buildId) ?? null
    const active = resolveActiveVersion(selection, entry)
    // Scope the baseline to the VIEWED branch so a push to another branch never
    // surfaces a misleading "new version" hint for this scene.
    const versions = branchVersionsFor(selection.branch, entry)
    setVersionBaseline({
      names: new Set(versions.map((version) => version.name)),
      activePushedAt: versions.find((version) => version.name === active)?.pushedAt ?? null,
    })
  }

  useEffect(() => {
    let cancelled = false

    void fetchBuildsIndex(null, null).then((result) => {
      if (cancelled) return
      if (result.status === 'ok') {
        indexEtagRef.current = result.etag
        indexBodyRef.current = result.bodyText
        captureVersionBaseline(result.builds)
        setBuildsIndex(result.builds)
      } else {
        setBuildsIndex(null)
      }
      setIndexLoaded(true)
    })

    return () => {
      cancelled = true
    }
    // selection is stable for the page's lifetime (URL-derived), so this runs once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Live menu refresh: poll /builds/index.json on an interval so newly published
  // builds/versions and refreshed "last updated" badges appear without a manual
  // reload. The poll is conditional (ETag / raw-body compare) so an unchanged
  // index is a no-op with no React churn; it pauses while the tab is hidden and
  // refreshes immediately on return; transient errors keep the current menu.
  // Only the available menu OPTIONS update here — never the loaded scene.
  useEffect(() => {
    const POLL_MS = 5000
    let cancelled = false
    let timer: ReturnType<typeof setInterval> | null = null

    const poll = async () => {
      if (cancelled || document.hidden) return
      const result = await fetchBuildsIndex(indexEtagRef.current, indexBodyRef.current)
      if (cancelled || result.status !== 'ok') return
      indexEtagRef.current = result.etag
      indexBodyRef.current = result.bodyText
      setBuildsIndex(result.builds)
    }

    const start = () => {
      if (timer === null) timer = setInterval(() => void poll(), POLL_MS)
    }
    const stop = () => {
      if (timer !== null) {
        clearInterval(timer)
        timer = null
      }
    }
    const handleVisibility = () => {
      if (document.hidden) {
        stop()
      } else {
        void poll()
        start()
      }
    }

    if (!document.hidden) start()
    document.addEventListener('visibilitychange', handleVisibility)

    return () => {
      cancelled = true
      stop()
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [])

  // Mirror the chosen colors to localStorage (keyed by build id) so they persist
  // across reloads. Removing the key when empty keeps storage tidy after a reset.
  useEffect(() => {
    try {
      const key = colorStorageKey(selection.buildId)
      if (Object.keys(partTypeColors).length === 0) {
        window.localStorage.removeItem(key)
      } else {
        window.localStorage.setItem(key, JSON.stringify(partTypeColors))
      }
    } catch {
      // Ignore storage failures (private mode, quota) — colors still work in-session.
    }
  }, [partTypeColors, selection.buildId])

  // Reset the pose scrubber to the home pose when the build (and its joints)
  // changes. Adjusting state during render off a changed prop is the
  // React-recommended pattern (mirrors ChecksPanel's prevManifest reset).
  const [prevJointsManifest, setPrevJointsManifest] = useState(manifest)
  if (prevJointsManifest !== manifest) {
    setPrevJointsManifest(manifest)
    setJointValues(defaultJointValues(manifest?.joints))
  }

  const partTypes = useMemo(
    () => [...new Set(manifest?.instances.map((instance) => instance.partType) ?? [])].sort(),
    [manifest],
  )
  // Searchable haystack per part type: the type name plus every instance's name
  // and id, so a query can find a part by type OR by a specific instance.
  const partTypeSearchText = useMemo(() => {
    const map: Record<string, string> = {}
    for (const instance of manifest?.instances ?? []) {
      const prior = map[instance.partType] ?? instance.partType
      map[instance.partType] = `${prior} ${instance.name} ${instance.id}`.toLowerCase()
    }
    return map
  }, [manifest])
  const filteredPartTypes = useMemo(() => {
    const query = partTypeFilter.trim().toLowerCase()
    if (!query) return partTypes
    return partTypes.filter((partType) => (partTypeSearchText[partType] ?? partType.toLowerCase()).includes(query))
  }, [partTypes, partTypeSearchText, partTypeFilter])
  // Default color per part type (first instance of each type wins), used to seed
  // the color swatch and to detect when a chosen color matches the default.
  const defaultPartTypeColors = useMemo(() => {
    const map: Record<string, string> = {}
    for (const instance of manifest?.instances ?? []) {
      if (!(instance.partType in map)) map[instance.partType] = instance.color
    }
    return map
  }, [manifest])
  const focusGroups = useMemo(
    () =>
      [...new Set(manifest?.instances.map((instance) => instance.focusGroup).filter(Boolean) ?? [])]
        .sort()
        .map((group) => group as string),
    [manifest],
  )
  const controlsModeKey = usesCompactControls ? 'compact' : 'desktop'
  const diffCounts = diffView?.diff.counts ?? null
  // Compare the live (polled) index for the VIEWED build against the baseline
  // captured when its scene loaded, to surface an opt-in "new version available"
  // hint without ever auto-switching the scene. A brand-new version name (a bump
  // or a new branch) wins; otherwise an in-place re-push of the version currently
  // on screen (its pushedAt advanced) shows an "updated — reload" hint. The
  // target is the newest new version (or the current one for a re-push). `key`
  // folds in the target's timestamp so a later push re-surfaces a dismissed hint.
  const versionUpdate = useMemo(() => {
    if (selection.manifestOverride || !versionBaseline || !currentBuildEntry) return null
    // Only the VIEWED branch's versions participate (matching the baseline).
    const branchVersions = branchVersionsFor(selection.branch, currentBuildEntry)
    const newNames = branchVersions
      .map((version) => version.name)
      .filter((name) => !versionBaseline.names.has(name))
    const pushedAtFor = (name: string) =>
      branchVersions.find((version) => version.name === name)?.pushedAt ?? null
    const messageFor = (name: string) =>
      branchVersions.find((version) => version.name === name)?.message

    if (newNames.length > 0) {
      const target = [...newNames].sort(compareVersionNames).at(-1) as string
      const label = newNames.length > 1 ? `${newNames.length} new versions` : `new version ${target}`
      // Only annotate with the note when a single version arrived (with multiple,
      // the target's note alone could misrepresent the others).
      const message = newNames.length === 1 ? messageFor(target) : undefined
      return { label, target, key: `${target}@${pushedAtFor(target) ?? ''}`, message }
    }

    const active = resolveActiveVersion(selection, currentBuildEntry)
    const livePushedAt = pushedAtFor(active)
    if (
      versionBaseline.activePushedAt !== null &&
      livePushedAt !== null &&
      livePushedAt !== versionBaseline.activePushedAt
    ) {
      return { label: `${active} updated`, target: active, key: `${active}@${livePushedAt}`, message: messageFor(active) }
    }
    return null
  }, [currentBuildEntry, selection, versionBaseline])
  const visibleVersionUpdate = versionUpdate && versionUpdate.key !== dismissedUpdateKey ? versionUpdate : null
  const applyVersionUpdate = () => {
    if (!versionUpdate) return
    navigateToBuild(selection.buildId, selection.branch, versionUpdate.target, selection.compare)
  }
  const dismissVersionUpdate = () => {
    if (versionUpdate) setDismissedUpdateKey(versionUpdate.key)
  }
  const selectedFocusLabel = focusGroup
    ? focusGroup === 'chassis'
      ? 'Chassis'
      : `Leg ${focusGroup}`
    : 'Full build'
  const enabledToolCount = Number(rulerMode) + Number(pickerMode)
  const visiblePartTypeCount = visiblePartTypes.size
  const setControlOpen = (control: keyof typeof openControls, open: boolean) => {
    setOpenControls((current) => (current[control] === open ? current : { ...current, [control]: open }))
  }

  // Right-click → "Schematic drawing" on a part in the 3D viewer: open the
  // Drawings panel and have it generate for that part. The nonce makes
  // repeated requests for the same part re-fire.
  const requestDrawing = (partType: string) => {
    setDrawingRequest({ partType, nonce: Date.now() })
    setControlOpen('drawings', true)
  }

  const showPanel = (id: PanelId) => !hiddenPanels.has(id)
  const togglePanel = (id: PanelId) => {
    setHiddenPanels((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  // Sidebar tabs: a tab is offered only when it has at least one panel to
  // show for the current scene (and the user hasn't hidden them all).
  const sceneLoaded = Boolean(manifest && !diffView)
  const wiringAvailable = Boolean(manifest && (manifest.routes?.length ?? 0) > 0)
  const motionAvailable = Boolean(
    manifest &&
      !diffView &&
      ((manifest.joints?.length ?? 0) > 0 || (manifest.animations?.length ?? 0) > 0),
  )
  const sidebarTabDefs: Array<{ id: SidebarTabId; label: string; available: boolean }> = [
    {
      id: 'view',
      label: 'View',
      available:
        showPanel('focus') ||
        showPanel('tools') ||
        (showPanel('wiring') && wiringAvailable) ||
        showPanel('partTypes'),
    },
    { id: 'diff', label: 'Diff', available: Boolean(diffView) && showPanel('diff') },
    { id: 'motion', label: 'Motion', available: motionAvailable && showPanel('motion') },
    {
      id: 'checks',
      label: 'Checks',
      available: sceneLoaded && (showPanel('checks') || showPanel('mass')),
    },
    {
      id: 'output',
      label: 'Export',
      available: sceneLoaded && (showPanel('export') || showPanel('drawings')),
    },
  ]
  const sidebarTabs = sidebarTabDefs.filter((tab) => tab.available)
  // Jump straight to the Diff tab when a compare view loads (adjust-during-
  // render pattern, same as the joints reset above).
  const [prevDiffForTab, setPrevDiffForTab] = useState(diffView)
  if (prevDiffForTab !== diffView) {
    setPrevDiffForTab(diffView)
    if (diffView) setActiveTab('diff')
  }
  // If the active tab is not offered (panel hidden, compare left, scene
  // changed), fall back to the first available one without extra renders.
  const resolvedTab: SidebarTabId = sidebarTabs.some((tab) => tab.id === activeTab)
    ? activeTab
    : sidebarTabs[0]?.id ?? 'view'
  useEffect(() => {
    try {
      window.localStorage.setItem(HIDDEN_PANELS_KEY, JSON.stringify([...hiddenPanels]))
    } catch {
      // Private-mode storage failures just mean the choice doesn't persist.
    }
  }, [hiddenPanels])

  const togglePartType = (partType: string) => {
    setVisiblePartTypes((current) => {
      const next = new Set(current)
      if (next.has(partType)) {
        next.delete(partType)
      } else {
        next.add(partType)
      }

      return next
    })
  }

  // Scroll the selected part's type into view within the Part Types list so a
  // click in the 3D view is easy to trace back. 'nearest' keeps it a minimal
  // nudge (and a no-op when the row is hidden by the filter or a collapsed
  // panel, since display:none rows have no scroll geometry).
  const partTypeListRef = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    if (!selectedPartType) return
    const rows = partTypeListRef.current?.querySelectorAll<HTMLElement>('.part-type-row') ?? []
    for (const row of rows) {
      if (row.dataset.partType === selectedPartType) {
        row.scrollIntoView({ block: 'nearest' })
        break
      }
    }
  }, [selectedPartType])

  // "Only": isolate a single part type. Clicking it again while isolated
  // restores every type — the same toggle-back feel as isolate in the 3D view.
  const showOnlyPartType = (partType: string) => {
    setVisiblePartTypes((current) =>
      current.size === 1 && current.has(partType) ? new Set(partTypes) : new Set([partType]),
    )
  }

  const setAllPartTypesVisible = (visible: boolean) => {
    setVisiblePartTypes(visible ? new Set(partTypes) : new Set<string>())
  }

  // Single-select toggle: clicking a part type's name highlights every instance
  // of that type in the viewer via the shared window.buildviz highlight API (the
  // same channel the Checks panel uses), so the two never paint at once — the
  // latest click wins. Clicking the active type again clears it.
  const toggleHighlightPartType = (partType: string) => {
    const next = highlightedPartType === partType ? null : partType
    setHighlightedPartType(next)
    if (next) {
      window.buildviz?.setHighlights({ parts: [{ partType: next }] })
    } else {
      window.buildviz?.clearHighlights()
    }
  }

  // Choosing a color recolors every instance of the part type in the viewer. If
  // the chosen color is the type's default, drop the override entirely so the
  // row reverts to its unmodified state.
  const setPartTypeColor = (partType: string, color: string) => {
    setPartTypeColors((current) => {
      if (color.toLowerCase() === (defaultPartTypeColors[partType] ?? '').toLowerCase()) {
        if (!(partType in current)) return current
        const next = { ...current }
        delete next[partType]
        return next
      }
      return { ...current, [partType]: color }
    })
  }

  const resetPartTypeColor = (partType: string) => {
    setPartTypeColors((current) => {
      if (!(partType in current)) return current
      const next = { ...current }
      delete next[partType]
      return next
    })
  }

  // Design-spec warnings for the viewed build/version, reported up by the
  // viewer once the spec fetch settles (the same coverage rule the hub warns
  // on at push/register). Warnings are stored with the selection they were
  // computed FOR, so navigating away hides a stale badge immediately — no
  // reset effect needed; the next build's viewer reports fresh warnings.
  const specSelectionKey = `${selection.buildId}@${selection.branch ?? ''}@${selection.version ?? ''}`
  const [specWarningsFor, setSpecWarningsFor] = useState<{ key: string; warnings: string[] }>({
    key: specSelectionKey,
    warnings: [],
  })
  const specWarnings = specWarningsFor.key === specSelectionKey ? specWarningsFor.warnings : []
  const reportSpecWarnings = useCallback(
    (warnings: string[]) => setSpecWarningsFor({ key: specSelectionKey, warnings }),
    [specSelectionKey],
  )

  const savedView = catalog?.item.view
  const viewSelection = useMemo(() => {
    if (!manifest || !savedView) return null
    const ids = new Set(savedView.instanceIds ?? [])
    const types = new Set(savedView.partTypes ?? [])
    const missing = [
      ...[...ids].filter((id) => !manifest.instances.some((instance) => instance.id === id)),
      ...[...types].filter((type) => !manifest.instances.some((instance) => instance.partType === type)),
    ]
    return {
      ids: new Set(manifest.instances.filter((instance) => ids.has(instance.id) || types.has(instance.partType)).map((instance) => instance.id)),
      missing,
    }
  }, [manifest, savedView])

  return (
    <main className="app-shell">
      <section className="workspace">
        <aside className={`controls-panel ${sheetCollapsed ? 'sheet-collapsed' : ''}`}>
          <button
            type="button"
            className="sheet-toggle"
            onClick={() => setSheetCollapsed((current) => !current)}
            aria-expanded={!sheetCollapsed}
            aria-label={sheetCollapsed ? 'Show controls' : 'Hide controls'}
            title={sheetCollapsed ? 'Show controls' : 'Hide controls'}
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="m6 9 6 6 6-6" />
            </svg>
            {sheetCollapsed ? <span>Controls</span> : null}
          </button>
          <CatalogQuickNav items={catalog?.items ?? catalogItems} currentId={catalog?.item.id} builds={buildsIndex ?? initialBuilds} currentBuildId={selection.buildId} />
          {catalog ? <CatalogSidebar {...catalog} /> : <a className="catalog-back" href="/">← Workshop</a>}
          {viewSelection && manifest ? <p className="catalog-evidence catalog-view-notice">Showing {viewSelection.ids.size} of {manifest.instances.length} source parts. <a href={sourceHref(catalog!.source)}>Open full source</a></p> : null}
          {viewSelection?.missing.length ? <p className="catalog-notice catalog-view-notice" role="alert">This saved view references unavailable parts: {viewSelection.missing.join(', ')}. Only the matching parts are shown.</p> : null}
          <BuildDropdown
            hasCatalogContext={Boolean(catalog)}
            buildsIndex={buildsIndex}
            projects={projects}
            selection={selection}
            currentBuildEntry={currentBuildEntry}
            diffCounts={diffCounts}
            versionUpdate={visibleVersionUpdate}
            onApplyVersionUpdate={applyVersionUpdate}
            onDismissVersionUpdate={dismissVersionUpdate}
            specWarnings={specWarnings}
          />
          {!selection.manifestOverride && !selection.analysis ? <BuildWorkflows buildId={selection.buildId} branch={selection.branch ?? undefined} version={selection.version ?? undefined} catalogId={catalog?.item.view ? catalog.item.id : undefined} /> : null}
          <RevisionHistory build={currentBuildEntry} branch={selection.branch} version={selection.version} contextId={catalog?.item.kind !== 'view' ? catalog?.item.id : undefined} />
          {catalog ? <CatalogDetails {...catalog} /> : null}

          {/* A ?scene= override may show something other than the selected
              build, so the STL link (which is keyed to the selection) hides. */}
          {!selection.manifestOverride ? <StlFolderLink selection={selection} /> : null}

          {activeAnalysis ? (
            <div className="analysis-banner">
              <div className="analysis-banner-text">
                <strong>{activeAnalysis.displayName ?? activeAnalysis.name}</strong>
                <small>
                  analysis page
                  {activeAnalysis.sourceVersion ? ` · from @${activeAnalysis.sourceVersion}` : ''}
                </small>
                {activeAnalysis.message ? <small title={activeAnalysis.message}>{clipMessage(activeAnalysis.message, 80)}</small> : null}
              </div>
              <button type="button" onClick={() => navigateToAnalysis(null)}>
                Back to build
              </button>
            </div>
          ) : null}

          {analyses.length > 0 && !selection.manifestOverride ? (
            <details className="control-group analyses-controls">
              <summary>
                <span>Analyses</span>
                <small>
                  {activeAnalysis
                    ? activeAnalysis.displayName ?? activeAnalysis.name
                    : `${analyses.length} page${analyses.length === 1 ? '' : 's'}`}
                </small>
              </summary>
              <div className="control-content focus-options">
                <button
                  type="button"
                  className={!selection.analysis ? 'active' : ''}
                  onClick={() => navigateToAnalysis(null)}
                >
                  Build (no analysis)
                </button>
                {analyses.map((entry) => (
                  <button
                    type="button"
                    key={entry.name}
                    className={selection.analysis === entry.name ? 'active' : ''}
                    title={entry.message ?? entry.displayName ?? entry.name}
                    onClick={() => navigateToAnalysis(entry.name)}
                  >
                    {entry.displayName ?? entry.name}
                    {entry.sourceVersion ? <small> @{entry.sourceVersion}</small> : null}
                  </button>
                ))}
              </div>
            </details>
          ) : null}

          {sidebarTabs.length > 1 ? (
            <label className="sidebar-section-select">
              <span className="visually-hidden">Sidebar section</span>
              <select
                value={resolvedTab}
                onChange={(event) => setActiveTab(event.target.value as SidebarTabId)}
              >
                {sidebarTabs.map((tab) => (
                  <option key={tab.id} value={tab.id}>
                    {tab.label}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          <div className="tab-panel" hidden={resolvedTab !== 'view'}>
          {showPanel('focus') ? (
          <details
            className="control-group focus-controls"
            open={openControls.focus}
            key={`focus-${controlsModeKey}`}
            onToggle={(event) => setControlOpen('focus', event.currentTarget.open)}
          >
            <summary>
              <span>Focus</span>
              <small>{selectedFocusLabel}</small>
            </summary>
            <div className="control-content focus-options">
              <button
                type="button"
                className={!focusGroup ? 'active' : ''}
                onClick={() => setFocusGroup(null)}
              >
                Full build
              </button>
              {focusGroups.map((group) => (
                <button
                  type="button"
                  key={group}
                  className={focusGroup === group ? 'active' : ''}
                  onClick={() => setFocusGroup(group)}
                >
                  {group === 'chassis' ? 'Chassis' : `Leg ${group}`}
                </button>
              ))}
            </div>
          </details>
          ) : null}

          {showPanel('tools') ? (
          <details
            className="control-group"
            open={openControls.tools}
            key={`tools-${controlsModeKey}`}
            onToggle={(event) => setControlOpen('tools', event.currentTarget.open)}
          >
            <summary>
              <span>Tools</span>
              <small>{enabledToolCount ? `${enabledToolCount} active` : 'Measure and pick'}</small>
            </summary>
            <div className="control-content tool-grid">
              <button
                type="button"
                className={`tool-button icon-button ${rulerMode ? 'active' : ''}`}
                onClick={() => {
                  setPickerMode(false)
                  setRulerMode((current) => !current)
                }}
                aria-label="Ruler: hover model edges to measure their length"
                aria-pressed={rulerMode}
                data-tooltip="Ruler: hover model edges to measure their length."
                title="Ruler: hover model edges to measure their length."
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 17 17 4l3 3L7 20l-3-3Z" />
                  <path d="m14 7 3 3M11 10l2 2M8 13l3 3" />
                </svg>
              </button>
              <button
                type="button"
                className={`tool-button icon-button ${pickerMode ? 'active' : ''}`}
                onClick={() => {
                  setRulerMode(false)
                  setPickerMode((current) => !current)
                }}
                aria-label="Picker: hover a point to show local object XYZ coordinates"
                aria-pressed={pickerMode}
                data-tooltip="Picker: hover a point to show local object XYZ coordinates."
                title="Picker: hover a point to show local object XYZ coordinates."
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 3v4M12 17v4M3 12h4M17 12h4" />
                  <circle cx="12" cy="12" r="4" />
                  <path d="m15 15 4 4" />
                </svg>
              </button>
            </div>
          </details>
          ) : null}

          {showPanel('wiring') && manifest && (manifest.routes?.length ?? 0) > 0 ? (
            <details
              className="control-group"
              open={openControls.wiring}
              key={`wiring-${controlsModeKey}`}
              onToggle={(event) => setControlOpen('wiring', event.currentTarget.open)}
            >
              <summary>
                <span>Wiring</span>
                <small>
                  {manifest.routes?.length} wire{(manifest.routes?.length ?? 0) === 1 ? '' : 's'}
                  {showWires ? '' : ' (hidden)'}
                </small>
              </summary>
              <div className="control-content wiring-options">
                <label className="wiring-toggle">
                  <input
                    type="checkbox"
                    checked={showWires}
                    onChange={(event) => setShowWires(event.target.checked)}
                  />
                  <span>Show wires</span>
                </label>
                <ul className="wiring-list">
                  {(manifest.routes ?? []).map((route) => (
                    <li key={route.id} title={route.kind ? `${route.kind} wire` : undefined}>
                      <span
                        className="wiring-swatch"
                        style={{ background: routeDisplayColor(route) }}
                        aria-hidden="true"
                      />
                      <span className="wiring-label">{route.label ?? route.id}</span>
                      {route.diameterMm ? <small>{route.diameterMm}mm</small> : null}
                    </li>
                  ))}
                </ul>
              </div>
            </details>
          ) : null}
          </div>

          <div className="tab-panel" hidden={resolvedTab !== 'diff'}>
          {showPanel('diff') && diffView ? (
            <DiffPanel
              diff={diffView.diff}
              fromVersion={selection.compare ?? 'from'}
              toVersion={selection.version ?? currentBuildEntry?.defaultVersion ?? 'to'}
              toMessage={
                currentBuildEntry?.versions.find(
                  (version) =>
                    version.name === (selection.version ?? currentBuildEntry?.defaultVersion),
                )?.message
              }
              open={openControls.diff}
              modeKey={controlsModeKey}
              onToggleOpen={(value) => setControlOpen('diff', value)}
            />
          ) : null}
          </div>

          <div className="tab-panel" hidden={resolvedTab !== 'motion'}>
          {showPanel('motion') &&
          manifest &&
          !diffView &&
          ((manifest.joints && manifest.joints.length > 0) ||
            (manifest.animations && manifest.animations.length > 0)) ? (
            <MotionPanel
              joints={manifest.joints ?? []}
              poses={manifest.poses ?? []}
              animations={manifest.animations ?? []}
              jointValues={jointValues}
              onChange={setJointValues}
              open={openControls.motion}
              modeKey={controlsModeKey}
              onToggleOpen={(value) => setControlOpen('motion', value)}
            />
          ) : null}
          </div>

          <div className="tab-panel" hidden={resolvedTab !== 'checks'}>
          {showPanel('checks') && manifest && !diffView ? (
            <ChecksPanel
              manifest={manifest}
              sidecarUrl={checksSidecarUrl}
              visiblePartTypes={visiblePartTypes}
              focusGroup={focusGroup}
              jointValues={jointValues}
              open={openControls.checks}
              modeKey={controlsModeKey}
              onToggleOpen={(value) => setControlOpen('checks', value)}
            />
          ) : null}

          {showPanel('mass') && manifest && !diffView ? (
            <MassPanel
              manifest={manifest}
              open={openControls.mass}
              modeKey={controlsModeKey}
              onToggleOpen={(value) => setControlOpen('mass', value)}
            />
          ) : null}
          </div>

          <div className="tab-panel" hidden={resolvedTab !== 'output'}>
          {showPanel('export') && manifest && !diffView ? (
            <ExportPanel
              buildId={selection.buildId}
              version={selection.version}
              assembly={focusGroup}
              open={openControls.export}
              modeKey={controlsModeKey}
              onToggleOpen={(value) => setControlOpen('export', value)}
            />
          ) : null}
          </div>

          {/* DrawingsPanel stays mounted outside the tab containers: its
              modal (a fixed overlay) must keep working when the right-click
              "Schematic drawing" fires from any tab. */}
          {manifest && !diffView ? (
            <DrawingsPanel
              manifest={manifest}
              buildLabel={[
                selection.buildId || manifest.name || 'scene',
                selection.branch,
                selection.version ?? currentBuildEntry?.defaultVersion,
              ]
                .filter(Boolean)
                .join('@')}
              request={drawingRequest}
              showLauncher={showPanel('drawings') && resolvedTab === 'output'}
              open={openControls.drawings}
              modeKey={controlsModeKey}
              onToggleOpen={(value) => setControlOpen('drawings', value)}
            />
          ) : null}

          <div className="tab-panel" hidden={resolvedTab !== 'view'}>
          {showPanel('partTypes') ? (
          <details
            className="control-group part-type-controls"
            open={openControls.partTypes}
            key={`part-types-${controlsModeKey}`}
            onToggle={(event) => setControlOpen('partTypes', event.currentTarget.open)}
          >
            <summary>
              <span>Part Types</span>
              <small>
                {visiblePartTypeCount}/{partTypes.length} visible
              </small>
            </summary>
            <div className="control-content part-type-list" ref={partTypeListRef}>
              {partTypes.length > 0 ? (
                <div className="part-type-search">
                  <input
                    type="search"
                    className="part-type-search-input"
                    placeholder="Filter part types or instances…"
                    value={partTypeFilter}
                    onChange={(event) => setPartTypeFilter(event.target.value)}
                    aria-label="Filter part types or instances"
                  />
                  {partTypeFilter ? (
                    <button
                      type="button"
                      className="part-type-search-clear"
                      onClick={() => setPartTypeFilter('')}
                      aria-label="Clear part type filter"
                      title="Clear filter"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M6 6l12 12M18 6 6 18" />
                      </svg>
                    </button>
                  ) : null}
                </div>
              ) : null}
              {partTypes.length > 1 ? (
                <div className="part-type-bulk">
                  <button
                    type="button"
                    onClick={() => setAllPartTypesVisible(true)}
                    disabled={visiblePartTypeCount === partTypes.length}
                    title="Make every part type visible"
                  >
                    Show all
                  </button>
                  <button
                    type="button"
                    onClick={() => setAllPartTypesVisible(false)}
                    disabled={visiblePartTypeCount === 0}
                    title="Hide every part type"
                  >
                    Hide all
                  </button>
                </div>
              ) : null}
              {partTypeFilter && filteredPartTypes.length === 0 ? (
                <p className="part-type-empty">No part types match “{partTypeFilter}”.</p>
              ) : null}
              {filteredPartTypes.map((partType) => {
                const isHighlighted = highlightedPartType === partType
                const hasCustomColor = partType in partTypeColors
                const isOnlyVisible = visiblePartTypeCount === 1 && visiblePartTypes.has(partType)
                const swatchColor =
                  partTypeColors[partType] ?? defaultPartTypeColors[partType] ?? '#888888'
                return (
                  <div
                    key={partType}
                    data-part-type={partType}
                    className={`part-type-row ${isHighlighted ? 'highlighted' : ''} ${
                      hasCustomColor ? 'has-custom-color' : ''
                    } ${selectedPartType === partType ? 'selected' : ''}`}
                  >
                    <input
                      type="checkbox"
                      className="part-type-visibility"
                      checked={visiblePartTypes.has(partType)}
                      onChange={() => togglePartType(partType)}
                      aria-label={`Toggle visibility of ${partType}`}
                      title={`Toggle visibility of ${partType}`}
                    />
                    <button
                      type="button"
                      className="part-type-highlight"
                      onClick={() => toggleHighlightPartType(partType)}
                      aria-pressed={isHighlighted}
                      title={
                        isHighlighted
                          ? `Clear highlight on ${partType}`
                          : `Highlight all ${partType} in the build`
                      }
                    >
                      {partType}
                    </button>
                    <button
                      type="button"
                      className={`part-type-only ${isOnlyVisible ? 'engaged' : ''}`}
                      onClick={() => showOnlyPartType(partType)}
                      title={
                        isOnlyVisible
                          ? 'Show all part types again'
                          : `Show only ${partType} (hide every other part type)`
                      }
                    >
                      {isOnlyVisible ? 'all' : 'only'}
                    </button>
                    {/* Hover/focus-revealed color control. The swatch wraps a
                        native color input; the reset appears once a custom color
                        is set (and on mobile the whole control is always shown). */}
                    <div className="part-type-color">
                      <label
                        className="part-type-color-swatch"
                        style={{ background: swatchColor }}
                        title={`Set color for ${partType}`}
                      >
                        <span className="visually-hidden">Set color for {partType}</span>
                        <input
                          type="color"
                          className="part-type-color-input"
                          value={swatchColor}
                          onChange={(event) => setPartTypeColor(partType, event.target.value)}
                          aria-label={`Set color for ${partType}`}
                        />
                      </label>
                      {hasCustomColor ? (
                        <button
                          type="button"
                          className="part-type-color-reset"
                          onClick={() => resetPartTypeColor(partType)}
                          aria-label={`Reset ${partType} to its default color`}
                          title={`Reset ${partType} to its default color`}
                        >
                          <svg viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M3 12a9 9 0 1 0 3-6.7M3 4v4h4" />
                          </svg>
                        </button>
                      ) : null}
                    </div>
                  </div>
                )
              })}
            </div>
          </details>
          ) : null}
          </div>

          {/* "Panels" picker (hide panels entirely) lives at the bottom, out
              of the way of everyday browsing. Its menu opens upward. */}
          <div className="panel-manager">
            <button
              type="button"
              className="panel-manager-trigger"
              onClick={() => setPanelPickerOpen((current) => !current)}
              aria-expanded={panelPickerOpen}
              title="Choose which panels are shown in this sidebar"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 6h16M4 12h10M4 18h7" />
              </svg>
              Panels
              {hiddenPanels.size > 0 ? <small>{hiddenPanels.size} hidden</small> : null}
            </button>
            {panelPickerOpen ? (
              <div className="panel-manager-menu">
                {PANEL_DEFS.map((def) => (
                  <label key={def.id} className="checkbox-control">
                    <input
                      type="checkbox"
                      checked={!hiddenPanels.has(def.id)}
                      onChange={() => togglePanel(def.id)}
                    />
                    <span>{def.label}</span>
                  </label>
                ))}
              </div>
            ) : null}
          </div>
        </aside>

        {manifest ? (
          <BuildViewer
            manifest={manifest}
            designSpecUrl={designSpecUrl}
            visiblePartTypes={visiblePartTypes}
            visibleInstanceIds={viewSelection?.ids}
            focusGroup={focusGroup}
            rulerMode={rulerMode}
            pickerMode={pickerMode}
            diffStatuses={diffView?.statuses ?? null}
            partTypeColors={partTypeColors}
            jointValues={jointValues}
            onSpecWarnings={reportSpecWarnings}
            showWires={showWires}
            onRequestDrawing={requestDrawing}
            onSelectedPartType={setSelectedPartType}
          />
        ) : (
          <section className="viewer-shell empty-viewer">
            <div>
              <h2>{loadError ? 'Could not load build' : `Loading ${selection.buildId}...`}</h2>
              <p>
                {loadError ?? 'Waiting for the exported scene manifest and STL assets to load.'}
              </p>
            </div>
          </section>
        )}
      </section>
    </main>
  )
}

function App() {
  const [catalogState, setCatalogState] = useState<{ items: CatalogItem[]; builds: BuildsIndexEntry[] | null } | null>(null)
  const params = useMemo(() => new URLSearchParams(window.location.search), [])
  useEffect(() => {
    let cancelled = false
    void Promise.all([
      fetch('/__buildviz/catalog').then((response) => response.ok ? response.json() : null).catch(() => null),
      fetchBuildsIndex(null, null),
    ]).then(([payload, index]) => {
      if (cancelled) return
      const items = payload?.schema === 1 && Array.isArray(payload.items) ? payload.items as CatalogItem[] : []
      setCatalogState({ items, builds: index.status === 'ok' ? index.builds : null })
    })
    return () => { cancelled = true }
  }, [])
  if (!catalogState) return <main className="catalog-loading">Loading workshop…</main>
  const { items, builds } = catalogState
  const catalogId = params.get('catalog')
  const contextId = params.get('catalogContext')
  const explicitBuild = params.has('build') || params.has('scene') || params.has('manifest')
  const item = items.find((candidate) => candidate.id === (catalogId ?? contextId))
  if (catalogId && !item) return <main className="catalog-error"><h2>Catalog item unavailable</h2><p>“{catalogId}” is not in this hub’s catalog. Its source may still be available through an existing build link.</p><a href="/">Back to workshop</a></main>
  if (!catalogId && !explicitBuild && (params.has('project') || params.has('projects'))) return <ProjectBrowser items={items} builds={builds} projectId={params.has('project') ? params.get('project')! : undefined} />
  if (!catalogId && !explicitBuild && items.length) return <CatalogHome items={items} builds={builds} />
  if (catalogId && item) {
    const milestoneParam = params.get('milestone')
    const milestoneIndex = milestoneParam !== null && /^\d+$/.test(milestoneParam) ? Number(milestoneParam) : -1
    const milestone = item.milestones?.[milestoneIndex]
    const asBuilt = params.get('configuration') === 'as-built'
    const source = asBuilt ? item.asBuilt : milestoneParam !== null ? milestone?.source : item.source
    const problem = source ? sourceProblem(source, builds) : asBuilt ? 'An installed configuration has not been recorded for this item.' : 'This milestone is not in the catalog.'
    if (problem || !source) return <main className="catalog-error"><a href="/">← Workshop</a><h2>{item.name}</h2><p className="catalog-notice">{problem}</p><p>The referenced geometry has not been replaced with another revision.</p></main>
    const configuration = asBuilt ? 'as built' : milestone ? `milestone: ${milestone.name}` : item.kind === 'view' ? 'saved view' : 'current design'
    return <BuildApp selectedSource={source} catalogItems={items} initialBuilds={builds ?? []} catalog={{ item, items, source, configuration }} />
  }
  const selection = getBuildSelection()
  const matches = items.filter((candidate) => candidate.kind !== 'view' && candidate.source.buildId === selection.buildId && (candidate.source.branch ?? 'main') === (selection.branch ?? builds?.find((build) => build.id === selection.buildId)?.defaultBranch ?? 'main'))
  const linkedItem = item && [item.source, item.asBuilt, ...(item.milestones?.map((milestone) => milestone.source) ?? [])].some((ref) => ref?.buildId === selection.buildId) ? item : undefined
  const contextItem = linkedItem ?? (matches.length === 1 ? matches[0] : undefined)
  const source = { buildId: selection.buildId, branch: selection.branch ?? undefined, version: selection.version ?? undefined }
  return <BuildApp catalogItems={items} initialBuilds={builds ?? []} catalog={contextItem ? { item: contextItem, items, source, configuration: 'revision' } : undefined} />
}

export default App
