import { useState } from 'react'
import { isLoopbackHost } from './hostEnv'

// "Export plates" control. A browser cannot write files, so this calls the hub's
// POST /__buildviz/pack-export endpoint, which runs pack + the 3MF/STL plate
// export server-side and returns the absolute output paths. Any BuildViz hub —
// local OR remote — performs the write, so the control is always shown and
// usable; it simply POSTs to the hub endpoints and surfaces a friendly error if
// the backend turns out not to be a hub (e.g. a plain static file server).
// "Open folder" reveals a directory on the *hub host*, which only makes sense
// when the viewer is loaded from the same machine, so that one button is gated
// to loopback hosts.

// Friendly message shown when an action POST cannot reach a BuildViz hub backend
// (network error, or the server answered with something other than the hub's
// JSON — e.g. a static file server with no /__buildviz/* endpoints).
const NO_HUB_MESSAGE = 'Export needs a BuildViz hub backend (this server is not a BuildViz hub).'

// Parse a hub JSON response, mapping non-JSON / non-hub answers to the friendly
// no-hub message instead of a raw parse error.
const readHubJson = async <T,>(response: Response): Promise<T> => {
  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) {
    throw new Error(NO_HUB_MESSAGE)
  }
  try {
    return (await response.json()) as T
  } catch {
    throw new Error(NO_HUB_MESSAGE)
  }
}

type ExportFormat = '3mf' | 'stl'

type ExportFile = {
  plate: number
  fileName: string
  path: string
  partCount: number
}

type ExportResponse = {
  ok?: boolean
  error?: string
  outDir?: string
  format?: string
  plateCount?: number
  partCount?: number
  files?: ExportFile[]
  assembly?: string | null
  printer?: string | null
  // Relative viewer scene path (e.g. /builds/<id>/buildviz_pack.json) plus a
  // ready-to-navigate "?…" search string that loads the packed plate layout.
  viewerScene?: string | null
  viewerUrl?: string | null
}

type ExportPanelProps = {
  buildId: string
  version: string | null
  // When a focus group is selected, scope the export to that assembly (leg).
  assembly: string | null
  open: boolean
  modeKey: string
  onToggleOpen: (open: boolean) => void
}

const PRINTERS: Array<{ id: string; label: string }> = [
  { id: 'x1c', label: 'Bambu X1C (256³)' },
  { id: 'h2d', label: 'Bambu H2D (350×320×325)' },
]

export const ExportPanel = ({
  buildId,
  version,
  assembly,
  open,
  modeKey,
  onToggleOpen,
}: ExportPanelProps) => {
  const [format, setFormat] = useState<ExportFormat>('3mf')
  const [printer, setPrinter] = useState<string>('x1c')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ExportResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  // Feedback for the post-export actions ("Open folder" / "Show in viewer"),
  // kept separate from the export error so a failed open does not clear results.
  const [actionError, setActionError] = useState<string | null>(null)

  const showOpenFolder = isLoopbackHost()

  const runExport = async () => {
    setLoading(true)
    setError(null)
    setActionError(null)
    setResult(null)
    try {
      let response: Response
      try {
        response = await fetch('/__buildviz/pack-export', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            buildId,
            version: version ?? undefined,
            format,
            printer,
            assembly: assembly ?? undefined,
          }),
        })
      } catch {
        // Network-level failure (no server, CORS, etc.): treat as "no hub".
        throw new Error(NO_HUB_MESSAGE)
      }
      // A static file server has no POST endpoint and typically answers 404/405
      // with HTML; surface the friendly no-hub message rather than a parse error.
      if (response.status === 404 || response.status === 405 || response.status === 501) {
        throw new Error(NO_HUB_MESSAGE)
      }
      const body = await readHubJson<ExportResponse>(response)
      if (!response.ok || body.ok === false) {
        throw new Error(body.error ?? `Export failed (${response.status})`)
      }
      setResult(body)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught))
    } finally {
      setLoading(false)
    }
  }

  const copyPaths = () => {
    if (!result?.files) return
    const text = [result.outDir ?? '', ...result.files.map((file) => file.path)].join('\n')
    void navigator.clipboard?.writeText(text)
  }

  // Ask the hub to reveal the output directory in the local OS file manager.
  // The hub validates the path is inside an allowed root before opening it.
  const openFolder = async () => {
    if (!result?.outDir) return
    setActionError(null)
    try {
      let response: Response
      try {
        response = await fetch('/__buildviz/open-path', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: result.outDir }),
        })
      } catch {
        throw new Error(NO_HUB_MESSAGE)
      }
      if (response.status === 404 || response.status === 405 || response.status === 501) {
        throw new Error(NO_HUB_MESSAGE)
      }
      const body = await readHubJson<{ ok?: boolean; error?: string }>(response)
      if (!response.ok || body.ok === false) {
        throw new Error(body.error ?? `Open failed (${response.status})`)
      }
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : String(caught))
    }
  }

  // Load the packed plate layout (the buildviz_pack.json the export emitted)
  // in the viewer via the ?scene= override, matching the CLI's `pack --emit`
  // viewer URL.
  const showInViewer = () => {
    if (!result?.viewerUrl) return
    window.location.search = result.viewerUrl
  }

  const scopeLabel = assembly ? `assembly ${assembly}` : 'full build'
  const badge = loading
    ? 'Exporting…'
    : result
      ? `${result.plateCount ?? result.files?.length ?? 0} plate file(s)`
      : `${format.toUpperCase()} · ${scopeLabel}`

  return (
    <details
      className="control-group export-controls"
      open={open}
      key={`export-${modeKey}`}
      onToggle={(event) => onToggleOpen(event.currentTarget.open)}
    >
      <summary>
        <span>Export plates</span>
        <small>{badge}</small>
      </summary>
      <div className="control-content export-content">
        <div className="export-options">
          <label className="select-control">
            <span>Format</span>
            <select
              value={format}
              onChange={(event) => setFormat(event.target.value as ExportFormat)}
              disabled={loading}
            >
              <option value="3mf">3MF (Bambu project)</option>
              <option value="stl">STL (merged per plate)</option>
            </select>
          </label>
          <label className="select-control">
            <span>Printer</span>
            <select
              value={printer}
              onChange={(event) => setPrinter(event.target.value)}
              disabled={loading}
            >
              {PRINTERS.map((entry) => (
                <option key={entry.id} value={entry.id}>
                  {entry.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <p className="export-scope">
          Scope: <strong>{scopeLabel}</strong>
          {assembly ? ' (from the current focus)' : ''}
        </p>
        <div className="export-actions">
          <button type="button" onClick={runExport} disabled={loading}>
            {loading ? 'Exporting…' : 'Export plates'}
          </button>
        </div>

        {error ? <p className="export-error">{error}</p> : null}

        {result ? (
          <div className="export-result">
            <div className="export-result-head">
              <span>
                {result.plateCount ?? result.files?.length ?? 0} {(result.format ?? format).toUpperCase()}{' '}
                plate file(s)
                {typeof result.partCount === 'number' ? ` · ${result.partCount} part(s)` : ''}
              </span>
              <div className="export-head-actions">
                {result.viewerUrl ? (
                  <button type="button" className="export-copy" onClick={showInViewer}>
                    Show in viewer
                  </button>
                ) : null}
                <button type="button" className="export-copy" onClick={copyPaths}>
                  Copy paths
                </button>
              </div>
            </div>
            <div className="export-dir-row">
              <code className="export-path export-dir">{result.outDir}</code>
              {showOpenFolder ? (
                <button type="button" className="export-open" onClick={openFolder}>
                  Open folder
                </button>
              ) : null}
            </div>
            {actionError ? <p className="export-error">{actionError}</p> : null}
            <ul className="export-files">
              {result.files?.map((file) => (
                <li key={file.fileName}>
                  <code className="export-path">{file.path}</code>
                  <small>
                    {file.partCount} part{file.partCount === 1 ? '' : 's'}
                  </small>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </details>
  )
}
