import { useState } from 'react'
import type { BuildSceneManifest } from '../../core/buildScene'
import { massProperties, type MassReport } from '../../checks/buildvizMass'

// Mass panel: estimate weight + weight distribution from the meshes, in the
// browser (same engine as `buildviz mass` and the MCP get_mass_properties
// tool). The CoM can be pinned into the 3D view through the shared highlight
// API, so "where is this thing balanced" is a one-click answer.

type MassPanelProps = {
  manifest: BuildSceneManifest
  open: boolean
  modeKey: string
  onToggleOpen: (open: boolean) => void
}

const formatGrams = (grams: number) =>
  grams >= 1000 ? `${(grams / 1000).toFixed(2)} kg` : `${Math.round(grams * 10) / 10} g`

const COM_HIGHLIGHT_COLOR = '#a855f7'

export const MassPanel = ({ manifest, open, modeKey, onToggleOpen }: MassPanelProps) => {
  const [report, setReport] = useState<MassReport | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [comShown, setComShown] = useState(false)

  // A new scene invalidates the previous estimate and any CoM marker. Render-
  // time reset from a changed prop (the ChecksPanel prevManifest pattern).
  const [prevManifest, setPrevManifest] = useState(manifest)
  if (prevManifest !== manifest) {
    setPrevManifest(manifest)
    setReport(null)
    setError(null)
    if (comShown) window.buildviz?.clearHighlights()
    setComShown(false)
  }

  const run = async () => {
    setRunning(true)
    setError(null)
    try {
      const result = await massProperties(manifest, {
        loadMesh: async (mesh) => {
          if (!mesh.url) return null
          const response = await fetch(mesh.url)
          if (!response.ok) return null
          return response.arrayBuffer()
        },
      })
      setReport(result)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught))
    } finally {
      setRunning(false)
    }
  }

  const toggleCom = () => {
    if (!report) return
    if (comShown) {
      window.buildviz?.clearHighlights()
      setComShown(false)
      return
    }
    window.buildviz?.setHighlights({
      points: [
        {
          id: 'center-of-mass',
          point: report.centerOfMassMm,
          color: COM_HIGHLIGHT_COLOR,
          label: 'CoM',
          annotation: `Center of mass · ${formatGrams(report.totalGrams)} total`,
          radiusMm: 6,
        },
      ],
    })
    setComShown(true)
  }

  return (
    <details
      className="control-group mass-controls"
      open={open}
      key={`mass-${modeKey}`}
      onToggle={(event) => onToggleOpen(event.currentTarget.open)}
    >
      <summary>
        <span>Mass</span>
        <small>{report ? formatGrams(report.totalGrams) : 'estimate'}</small>
      </summary>
      <div className="control-content mass-content">
        <div className="mass-actions">
          <button
            type="button"
            onClick={() => void run()}
            disabled={running}
            title="Estimate weight from mesh volumes × density (checksConfig.partMassesGrams overrides win)"
          >
            {running ? 'Estimating…' : report ? 'Re-estimate' : 'Estimate mass'}
          </button>
          {report ? (
            <button type="button" onClick={toggleCom} className={comShown ? 'active' : ''}>
              {comShown ? 'Hide CoM' : 'Show CoM'}
            </button>
          ) : null}
        </div>
        {error ? <p className="mass-error">{error}</p> : null}
        {report ? (
          <>
            <p className="mass-summary">
              <strong>{formatGrams(report.totalGrams)}</strong> over {report.instanceCount} instances
              <br />
              CoM [{report.centerOfMassMm.join(', ')}] mm · in bounds{' '}
              {report.centerOfMassFraction.map((f) => `${Math.round(f * 100)}%`).join(' / ')}
            </p>
            {report.configuredMassPartTypes.length === 0 ? (
              <p className="mass-note">
                No known part masses configured (checksConfig.partMassesGrams) — bought parts like
                servos and batteries are weighed as solid plastic.
              </p>
            ) : null}
            <ul className="mass-breakdown">
              {report.byPartType.slice(0, 14).map((entry) => (
                <li key={entry.partType} title={`${entry.count} × ${entry.unitGrams} g (${entry.source})`}>
                  <span className="mass-bar" style={{ width: `${Math.max(2, entry.share * 100)}%` }} />
                  <span className="mass-part">{entry.partType}</span>
                  <span className="mass-grams">{formatGrams(entry.totalGrams)}</span>
                </li>
              ))}
            </ul>
            {report.byGroup.length > 1 ? (
              <div className="mass-groups">
                {report.byGroup.map((group) => (
                  <div key={group.group}>
                    <span className="mass-part">{group.group}</span>
                    <span className="mass-grams">
                      {formatGrams(group.totalGrams)} ({Math.round(group.share * 100)}%)
                    </span>
                  </div>
                ))}
              </div>
            ) : null}
            {report.missingMeshes.length > 0 ? (
              <p className="mass-note">Not weighed (missing meshes): {report.missingMeshes.join(', ')}</p>
            ) : null}
          </>
        ) : (
          <p className="mass-note">
            Computes volume and center of mass per part from the meshes. Densities and known masses
            come from the scene's checksConfig.
          </p>
        )}
      </div>
    </details>
  )
}
