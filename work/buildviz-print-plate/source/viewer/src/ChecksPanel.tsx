import { useEffect, useMemo, useState } from 'react'
import type { BuildSceneManifest, SceneCheck } from '../../core/buildScene'
import {
  CHECK_STATUS_COLOR,
  checkKindLabel,
  checksToHighlights,
  geometryChecks,
  staticChecks,
  summarizeChecks,
  sweptChecks,
} from '../../checks/buildvizChecks'
import { checkAssembly, sweepOverlaps } from '../../checks/buildvizGeometry'
import {
  buildSweepSamples,
  defaultJointValues,
  poseInstanceArrays,
  type JointValues,
} from '../../core/buildvizKinematics'

type ChecksSource = 'static' | 'manifest' | 'sidecar' | 'live'

type ChecksPanelProps = {
  manifest: BuildSceneManifest
  // Sidecar (buildviz_checks.json) URL alongside the scene, or null when unknown
  // (e.g. diff view). Static manifest checks still run.
  sidecarUrl: string | null
  // Live overlap/clearance checks default to the VISIBLE + FOCUSED instance
  // subset (mirrors the viewer's own visibility model) so the pass stays
  // interactive on the largest builds; a "full-scene" action runs everything.
  visiblePartTypes: Set<string>
  focusGroup: string | null
  // Phase 3: current scrubber pose, included as a sample in the swept overlap run
  // so "what you see" is part of the worst-case envelope. Undefined / no joints
  // hides the swept-checks action entirely.
  jointValues?: JointValues
  open: boolean
  modeKey: string
  onToggleOpen: (open: boolean) => void
}

type SidecarPayload = { checks?: SceneCheck[] }

// Scope a live run ran over: the visible/focused subset, or the whole scene. A
// swept run also reports how many posed samples it evaluated.
type LiveScope = {
  kind: 'visible' | 'full' | 'sweep' | 'sweep-full'
  instanceCount: number
  totalMs: number
  sampleCount?: number
}

const SOURCE_LABEL: Record<ChecksSource, string> = {
  static: 'manifest-only checks',
  manifest: 'scene.checks',
  sidecar: 'buildviz_checks.json sidecar',
  live: 'live (computed in browser)',
}

// An allowed/intended interference: a mesh_overlap that did NOT fail because it
// matched a typed checksConfig.allowedInterferences entry (or the legacy
// ignoreOverlapPairs blanket), plus the passing declared_interference audit
// rows — surfaced as pass / intentional so they stay visible but muteable.
const isAllowedMating = (check: SceneCheck) =>
  (check.kind === 'mesh_overlap' || check.kind === 'declared_interference') &&
  check.status === 'pass'

// Push a subset of checks to the shared viewer highlight API. Pass an empty list
// to clear. Only warn/fail records actually paint (see checksToHighlights).
const applyHighlights = (checks: SceneCheck[]) => {
  if (checks.length === 0) {
    window.buildviz?.clearHighlights()
    return
  }
  const { parts, points, regions } = checksToHighlights(checks)
  window.buildviz?.setHighlights({ parts, points, regions })
}

export const ChecksPanel = ({
  manifest,
  sidecarUrl,
  visiblePartTypes,
  focusGroup,
  jointValues,
  open,
  modeKey,
  onToggleOpen,
}: ChecksPanelProps) => {
  const [issuesOnly, setIssuesOnly] = useState(false)
  // Triage: hide allowed/intended interferences (the green `pass (allowed)`
  // overlap rows from allowedInterferences / legacy ignoreOverlapPairs) so only
  // unexpected interferences remain.
  const [muteAllowed, setMuteAllowed] = useState(false)
  const [kindFilter, setKindFilter] = useState<string>('all')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [liveScope, setLiveScope] = useState<LiveScope | null>(null)
  // Override from an async source (sidecar fetch or a live in-browser run). When
  // null we fall back to the synchronously-derived base checks below.
  const [override, setOverride] = useState<{ checks: SceneCheck[]; source: ChecksSource } | null>(null)

  // Base checks are derived during render: scene.checks if the manifest carries
  // them, otherwise the cheap manifest-only static checks.
  const baseChecks = useMemo(
    () => (manifest.checks && manifest.checks.length > 0 ? manifest.checks : staticChecks(manifest)),
    [manifest],
  )
  const baseSource: ChecksSource = manifest.checks && manifest.checks.length > 0 ? 'manifest' : 'static'

  // Reset the async override + selection when the build changes. Storing the
  // previous prop in state and adjusting during render (rather than in an effect)
  // is the React-recommended pattern for deriving state from a changed prop.
  const [prevManifest, setPrevManifest] = useState(manifest)
  if (prevManifest !== manifest) {
    setPrevManifest(manifest)
    setOverride(null)
    setSelectedId(null)
    setError(null)
    setLiveScope(null)
    setKindFilter('all')
  }

  const checks = override?.checks ?? baseChecks
  const source = override?.source ?? baseSource

  // Load a buildviz_checks.json sidecar when present (it already includes the
  // static + geometry findings emitted by `buildviz check`). The manifest's own
  // scene.checks take precedence, so the fetch is skipped in that case.
  useEffect(() => {
    if (!sidecarUrl || (manifest.checks && manifest.checks.length > 0)) return
    let cancelled = false
    void (async () => {
      try {
        const response = await fetch(sidecarUrl)
        if (!response.ok) return
        const contentType = response.headers.get('content-type') ?? ''
        if (!contentType.includes('application/json')) return
        const payload = (await response.json()) as SidecarPayload
        if (cancelled || !Array.isArray(payload.checks) || payload.checks.length === 0) return
        setOverride({ checks: payload.checks, source: 'sidecar' })
      } catch {
        // No sidecar is the common, expected case — stay on static checks.
      }
    })()

    return () => {
      cancelled = true
    }
  }, [manifest, sidecarUrl])

  const summary = useMemo(() => summarizeChecks(checks), [checks])
  // Kinds present, for the per-kind filter dropdown. Sorted by display label.
  const kinds = useMemo(
    () => [...new Set(checks.map((check) => check.kind))].sort((a, b) =>
      checkKindLabel(a).localeCompare(checkKindLabel(b)),
    ),
    [checks],
  )
  const allowedCount = useMemo(() => checks.filter(isAllowedMating).length, [checks])

  const visibleChecks = useMemo(
    () =>
      [...checks]
        .filter((check) => (issuesOnly ? check.status !== 'pass' : true))
        .filter((check) => (muteAllowed ? !isAllowedMating(check) : true))
        .filter((check) => (kindFilter === 'all' ? true : check.kind === kindFilter))
        .sort((a, b) => severity(b.status) - severity(a.status)),
    [checks, issuesOnly, muteAllowed, kindFilter],
  )

  const badge =
    summary.fail > 0 || summary.warn > 0
      ? [summary.fail > 0 ? `${summary.fail} fail` : null, summary.warn > 0 ? `${summary.warn} warn` : null]
          .filter(Boolean)
          .join(' · ')
      : summary.total > 0
        ? 'All clear'
        : 'No checks'

  // "Highlight all" / the issues-only badge act on un-triaged issues only, so
  // muting allowed matings here too keeps it consistent with the list.
  const issueChecks = useMemo(
    () => checks.filter((check) => check.status !== 'pass' && !isAllowedMating(check)),
    [checks],
  )

  const selectCheck = (check: SceneCheck) => {
    if (selectedId === check.id) {
      setSelectedId(null)
      applyHighlights([])
      return
    }
    setSelectedId(check.id)
    applyHighlights([check])
  }

  // The live overlap/clearance pass is O(n²) in the broad phase, so by default
  // it is scoped to the instances the viewer is actually showing (the visible
  // part types intersected with the focused group). An instance is in scope when
  // its partType is visible AND it matches the active focus — the same predicate
  // the viewer uses. An empty visible set means "all visible".
  const inScope = (partType: string, instanceFocus: string | undefined | null) => {
    const visible = visiblePartTypes.size === 0 || visiblePartTypes.has(partType)
    const focusMatch = !focusGroup || instanceFocus === focusGroup
    return visible && focusMatch
  }

  // Phase 2: compute mesh overlap / clearance / connectivity in the browser via
  // three-mesh-bvh, fetching the scene's STL assets directly. `full` runs the
  // whole scene; otherwise only the visible/focused subset is evaluated.
  const runLive = async (full: boolean) => {
    setRunning(true)
    setError(null)
    try {
      const instances = full
        ? manifest.instances
        : manifest.instances.filter((instance) => inScope(instance.partType, instance.focusGroup))
      // Only load the meshes the scoped instances reference — this is what keeps
      // the visible-subset pass fast on huge builds (fewer STL fetches + BVHs).
      const usedMeshIds = new Set(instances.map((instance) => instance.meshId))
      const meshes = full
        ? manifest.meshes
        : manifest.meshes.filter((mesh) => usedMeshIds.has(mesh.id))
      const scoped = { ...manifest, instances, meshes }
      const report = await checkAssembly(scoped, {
        loadMesh: async (mesh) => {
          if (!mesh.url) return null
          const response = await fetch(mesh.url)
          if (!response.ok) return null
          return response.arrayBuffer()
        },
      })
      setOverride({
        checks: [...staticChecks(scoped), ...geometryChecks(report, manifest.checksConfig)],
        source: 'live',
      })
      setLiveScope({
        kind: full ? 'full' : 'visible',
        instanceCount: instances.length,
        totalMs: report.timings.totalMs,
      })
      setSelectedId(null)
      applyHighlights([])
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught))
    } finally {
      setRunning(false)
    }
  }

  const hasJoints = (manifest.joints?.length ?? 0) > 0

  // Phase 3: re-evaluate overlaps across the mechanism's swept motion and report
  // the worst-case envelope per pair. By default the sweep is scoped to the
  // visible/focused instances (a sweep is naturally scoped to the moving limb),
  // reusing the cached per-geometry BVHs; `full` sweeps the whole scene.
  const runSweep = async (full: boolean) => {
    if (!hasJoints) return
    setRunning(true)
    setError(null)
    try {
      const scopeIds = full
        ? undefined
        : new Set(
            manifest.instances
              .filter((instance) => inScope(instance.partType, instance.focusGroup))
              .map((instance) => instance.id),
          )
      const samples = buildSweepSamples(manifest, { scopeInstanceIds: scopeIds })
      // Fold the current scrubber pose in as an extra sample, so the worst case
      // always includes whatever the user is currently looking at.
      const home = defaultJointValues(manifest.joints)
      const current = jointValues ?? home
      const movedFromHome = manifest.joints?.some(
        (joint) => Math.abs((current[joint.id] ?? 0) - (home[joint.id] ?? 0)) > 1e-6,
      )
      if (movedFromHome) {
        samples.push({
          id: 'current',
          label: 'current pose',
          jointValues: current,
          overrides: poseInstanceArrays(manifest, current),
        })
      }

      const instances = full
        ? manifest.instances
        : manifest.instances.filter((instance) => inScope(instance.partType, instance.focusGroup))
      const usedMeshIds = new Set(instances.map((instance) => instance.meshId))
      const meshes = full ? manifest.meshes : manifest.meshes.filter((mesh) => usedMeshIds.has(mesh.id))
      const scoped = { ...manifest, instances, meshes }

      const report = await sweepOverlaps(scoped, samples, {
        clearanceMm: manifest.checksConfig?.clearanceMm,
        minPenetrationMm: manifest.checksConfig?.minPenetrationMm,
        toleranceMm: manifest.checksConfig?.toleranceMm,
        loadMesh: async (mesh) => {
          if (!mesh.url) return null
          const response = await fetch(mesh.url)
          if (!response.ok) return null
          return response.arrayBuffer()
        },
      })
      setOverride({
        checks: [...staticChecks(scoped), ...sweptChecks(report)],
        source: 'live',
      })
      setLiveScope({
        kind: full ? 'sweep-full' : 'sweep',
        instanceCount: report.instanceCount,
        totalMs: report.timings.totalMs,
        sampleCount: report.sampleCount,
      })
      setSelectedId(null)
      applyHighlights([])
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught))
    } finally {
      setRunning(false)
    }
  }

  return (
    <details
      className="control-group checks-controls"
      open={open}
      key={`checks-${modeKey}`}
      onToggle={(event) => onToggleOpen(event.currentTarget.open)}
    >
      <summary>
        <span>Checks</span>
        <small className={summary.fail > 0 ? 'has-fail' : summary.warn > 0 ? 'has-warn' : ''}>{badge}</small>
      </summary>
      <div className="control-content checks-content">
        <div className="checks-actions">
          <button
            type="button"
            onClick={() => void runLive(false)}
            disabled={running}
            title="Compute overlaps/clearance for the visible + focused parts only"
          >
            {running ? 'Running…' : 'Run live checks'}
          </button>
          <button
            type="button"
            onClick={() => void runLive(true)}
            disabled={running}
            title="Compute overlaps/clearance for every instance in the scene"
          >
            Run full-scene checks
          </button>
          {hasJoints ? (
            <button
              type="button"
              onClick={() => void runSweep(false)}
              disabled={running}
              title="Sweep the joints through their range and report the worst-case overlap envelope (visible + focused parts)"
            >
              {running ? 'Running…' : 'Run swept checks'}
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => {
              setSelectedId(null)
              applyHighlights(issueChecks)
            }}
            disabled={issueChecks.length === 0}
          >
            Highlight all
          </button>
          <button
            type="button"
            onClick={() => {
              setSelectedId(null)
              applyHighlights([])
            }}
          >
            Clear
          </button>
        </div>
        <div className="checks-filters">
          <label className="checkbox-control checks-filter">
            <input
              type="checkbox"
              checked={issuesOnly}
              onChange={(event) => setIssuesOnly(event.currentTarget.checked)}
            />
            <span>Show only fails/warns</span>
          </label>
          <label className="checkbox-control checks-filter">
            <input
              type="checkbox"
              checked={muteAllowed}
              onChange={(event) => setMuteAllowed(event.currentTarget.checked)}
              disabled={allowedCount === 0}
            />
            <span>Mute allowed matings{allowedCount > 0 ? ` (${allowedCount})` : ''}</span>
          </label>
          {kinds.length > 1 ? (
            <label className="select-control checks-kind-filter">
              <span>Kind</span>
              <select value={kindFilter} onChange={(event) => setKindFilter(event.currentTarget.value)}>
                <option value="all">All kinds ({summary.total})</option>
                {kinds.map((kind) => (
                  <option key={kind} value={kind}>
                    {checkKindLabel(kind)} ({summary.byKind[kind].fail + summary.byKind[kind].warn + summary.byKind[kind].pass})
                  </option>
                ))}
              </select>
            </label>
          ) : null}
        </div>
        {error ? <p className="checks-error">{error}</p> : null}
        {visibleChecks.length === 0 ? (
          <p className="checks-empty">{issuesOnly ? 'No issues found.' : 'No checks available.'}</p>
        ) : (
          <ul className="checks-list">
            {visibleChecks.map((check) => (
              <li key={check.id}>
                <button
                  type="button"
                  className={`check-row status-${check.status} ${selectedId === check.id ? 'selected' : ''}`}
                  onClick={() => selectCheck(check)}
                  title={check.instances?.length ? check.instances.join(', ') : undefined}
                >
                  <span
                    className="check-status-dot"
                    style={{ background: CHECK_STATUS_COLOR[check.status] }}
                    aria-hidden="true"
                  />
                  <span className="check-kind">{checkKindLabel(check.kind)}</span>
                  <span className="check-label">{check.label}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        <small className="checks-source">
          source: {SOURCE_LABEL[source]}
          {source === 'live' && liveScope
            ? liveScope.kind === 'sweep' || liveScope.kind === 'sweep-full'
              ? ` · swept ${liveScope.kind === 'sweep-full' ? 'full scene' : 'visible/focused'}: ` +
                `${liveScope.instanceCount} parts × ${liveScope.sampleCount ?? 0} poses in ${liveScope.totalMs}ms`
              : ` · ${liveScope.kind === 'full' ? 'full scene' : 'visible/focused'}: ${liveScope.instanceCount} parts in ${liveScope.totalMs}ms`
            : ''}
        </small>
      </div>
    </details>
  )
}

const severity = (status: SceneCheck['status']) => (status === 'fail' ? 2 : status === 'warn' ? 1 : 0)
