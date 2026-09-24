import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { BuildWorkflows as WorkflowData, WorkflowFile, WorkflowPart } from '../../core/buildWorkflows'
import './BuildWorkflows.css'

type BuildWorkflowsProps = {
  buildId: string
  branch?: string
  version?: string
  catalogId?: string
  onFocusParts?: (partTypes: string[]) => void
}
const TABS = [
  { id: 'print', label: 'Print parts' },
  { id: 'purchased', label: 'Purchased parts' },
  { id: 'assembly', label: 'Assembly' },
  { id: 'runs', label: 'MuJoCo runs' },
] as const
type Tab = (typeof TABS)[number]['id']
const workflowParam: Record<Tab, string> = { print: 'print', purchased: 'bom', assembly: 'assembly', runs: 'runs' }
const initialTab = () => {
  const value = new URLSearchParams(window.location.search).get('workflow')
  return TABS.find((item) => workflowParam[item.id] === value)?.id
}
const changeLabel: Record<WorkflowFile['change'], string> = {
  new: 'New', changed: 'Geometry changed', quantity: 'Quantity changed', unchanged: 'Unchanged', unavailable: 'STL unavailable', 'not-compared': 'Not compared',
}
const safeUrl = (raw: string | undefined) => {
  if (!raw) return undefined
  try {
    const url = new URL(raw, window.location.href)
    return ['http:', 'https:'].includes(url.protocol) ? url.href : undefined
  } catch { return undefined }
}
const downloadUrl = (raw: string | undefined | null) => {
  const url = safeUrl(raw ?? undefined)
  return url && new URL(url).origin === window.location.origin ? url : undefined
}
const countLabel = (count: number, singular: string, plural = `${singular}s`) => `${count} ${count === 1 ? singular : plural}`

function PartLabel({ part, onFocus, showNotes = false }: { part: WorkflowPart; onFocus?: (partTypes: string[]) => void; showNotes?: boolean }) {
  return <><strong>{part.label}</strong>{part.material ? <small>{part.material}</small> : null}{showNotes && part.notes ? <details className="workflow-part-notes"><summary>Notes</summary><p>{part.notes}</p></details> : null}{onFocus ? <button type="button" className="workflow-text-button" onClick={() => onFocus([part.partType])}>Show in model</button> : null}</>
}

function exportBom(data: WorkflowData) {
  const rows = [
    ['Part', 'Quantity', 'Unit', 'Source', 'Notes'],
    ...data.purchased.map((part) => [part.label, part.quantity, 'pieces', part.url ?? '', part.notes ?? '']),
    ...data.bom.items.map((part) => [part.label, part.quantity, part.unit ?? 'pieces', part.url ?? '', part.notes ?? '']),
  ]
  const csv = rows.map((row) => row.map((value) => {
    const text = String(value)
    return `"${(/^[=+@\-\t\r]/.test(text) ? `'${text}` : text).replaceAll('"', '""')}"`
  }).join(',')).join('\r\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `${data.source.buildId.replaceAll('/', '-')}-${data.source.version}-purchased-parts.csv`
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

// A source change discards the previous revision's download URLs and comparison.
export function BuildWorkflows(props: BuildWorkflowsProps) {
  return <BuildWorkflowsForSource key={[props.buildId, props.branch, props.version, props.catalogId].join('|')} {...props} />
}

function BuildWorkflowsForSource({ buildId, branch, version, catalogId, onFocusParts }: BuildWorkflowsProps) {
  const [tab, setTab] = useState<Tab>(() => initialTab() ?? 'print')
  const [open, setOpen] = useState(() => Boolean(initialTab()))
  const [printer, setPrinter] = useState('x1c')
  const [plateBusy, setPlateBusy] = useState(false)
  const [plateError, setPlateError] = useState<string | null>(null)
  const [selection, setSelection] = useState<'all' | 'changed'>('all')
  const [compare, setCompare] = useState<string>()
  const [data, setData] = useState<WorkflowData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(true)
  const [retry, setRetry] = useState(0)
  const dialogRef = useRef<HTMLDialogElement>(null)
  const id = useId()
  const params = useMemo(() => {
    const value = new URLSearchParams({ build: buildId })
    if (branch) value.set('branch', branch)
    if (version) value.set('version', version)
    if (catalogId) value.set('catalog', catalogId)
    if (compare) value.set('compare', compare)
    return value.toString()
  }, [buildId, branch, version, catalogId, compare])

  useEffect(() => {
    const controller = new AbortController()
    fetch(`/__buildviz/workflows?${params}`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          const body = await response.json().catch(() => null)
          throw new Error(body?.error || `Build files could not be loaded (${response.status}).`)
        }
        const result = await response.json() as WorkflowData
        if (result.schema !== 1 || !Array.isArray(result.printed)) throw new Error('This hub does not provide build workflows yet.')
        return result
      })
      .then((result) => { if (!controller.signal.aborted) { setData(result); setBusy(false) } })
      .catch((reason: unknown) => { if (!controller.signal.aborted) { setError(reason instanceof Error ? reason.message : 'Build files could not be loaded.'); setBusy(false) } })
    return () => controller.abort()
  }, [params, retry])

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    else if (!open && dialog.open) dialog.close()
  }, [open])

  const allRows = data?.printed.flatMap((part) => part.files.map((file) => ({ part, file }))) ?? []
  const rows = selection === 'all' ? allRows : data?.downloads.changed ? allRows.filter(({ file }) => file.change !== 'unchanged') : []
  const downloadableRows = rows.filter(({ file }) => file.change !== 'unavailable' && (selection === 'all' || file.quantityToPrint > 0))
  const uniqueFiles = new Set(downloadableRows.map(({ file }) => file.id)).size
  const allFileCount = new Set(allRows.filter(({ file }) => file.change !== 'unavailable').map(({ file }) => file.id)).size
  const quantity = downloadableRows.reduce((total, { file }) => total + (selection === 'all' ? file.quantity : file.quantityToPrint), 0)
  const zipUrl = data && downloadUrl(selection === 'all' ? data.downloads.all : data.downloads.changed)
  const missingParts = data?.printed.filter((part) => part.errors.length || part.files.length === 0) ?? []
  const millimeterUnits = data?.source.units === 'mm'
  const downloadPlate = async () => {
    if (!zipUrl) return
    setPlateBusy(true); setPlateError(null)
    try {
      const url = new URL(zipUrl)
      url.pathname = '/__buildviz/workflows/plate'
      url.searchParams.set('printer', printer)
      const response = await fetch(url)
      if (!response.ok) throw new Error((await response.json()).error || 'Plate export failed.')
      const blobUrl = URL.createObjectURL(await response.blob())
      const a = document.createElement('a'); a.href = blobUrl
      a.download = response.headers.get('Content-Disposition')?.match(/filename="([^"]+)"/)?.[1] ?? 'print-plate.3mf'
      a.click(); setTimeout(() => URL.revokeObjectURL(blobUrl), 1000)
    } catch (reason) { setPlateError(reason instanceof Error ? reason.message : 'Plate export failed.') }
    finally { setPlateBusy(false) }
  }
  const changeTab = (next: Tab) => {
    setTab(next)
    const url = new URL(window.location.href)
    url.searchParams.set('workflow', workflowParam[next])
    window.history.replaceState(null, '', url)
  }
  const showTab = (next: Tab) => { changeTab(next); setOpen(true) }
  const closeWorkflow = () => {
    setOpen(false)
    const url = new URL(window.location.href)
    url.searchParams.delete('workflow')
    window.history.replaceState(null, '', url)
  }
  const focusParts = onFocusParts ? (partTypes: string[]) => { closeWorkflow(); onFocusParts(partTypes) } : undefined

  return <div className="build-workflows">
    <button type="button" className="workflow-launch" aria-label="Print parts" aria-haspopup="dialog" onClick={() => showTab('print')}>
      <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M5 7V2h10v5M5 14H2V7h16v7h-3M5 11h10v7H5zM14 9h1" /></svg>
      <span>Print parts</span><small>{busy && !data ? '…' : data ? countLabel(allFileCount, 'STL') : 'Open'}</small>
    </button>
    <div className="workflow-shortcuts" aria-label="Build workflows">
      {TABS.slice(1).map((item) => <button key={item.id} type="button" onClick={() => showTab(item.id)}>{item.label}</button>)}
    </div>
    {createPortal(<dialog ref={dialogRef} className="workflow-dialog" aria-labelledby={`${id}-title`} onCancel={closeWorkflow} onClose={closeWorkflow} onClick={(event) => {
      if (event.target !== event.currentTarget) return
      const rect = event.currentTarget.getBoundingClientRect()
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) closeWorkflow()
    }}>
      <header className="workflow-header">
        <div><h2 id={`${id}-title`}>Build workflows</h2><p>{data?.source.name ?? buildId} <span>· {data?.source.branch ?? branch ?? 'default branch'} / {data?.source.version ?? version ?? 'current revision'}</span></p></div>
        <button type="button" className="workflow-close" aria-label="Close build workflows" onClick={closeWorkflow}>×</button>
      </header>
      <div className="workflow-tabs" role="tablist" aria-label="Build workflows" onKeyDown={(event) => {
        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
        event.preventDefault()
        const index = TABS.findIndex((item) => item.id === tab)
        const nextIndex = event.key === 'Home' ? 0 : event.key === 'End' ? TABS.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + TABS.length) % TABS.length
        changeTab(TABS[nextIndex].id)
        document.getElementById(`${id}-tab-${TABS[nextIndex].id}`)?.focus()
      }}>
        {TABS.map((item) => <button key={item.id} id={`${id}-tab-${item.id}`} type="button" role="tab" aria-selected={tab === item.id} aria-controls={`${id}-panel`} tabIndex={tab === item.id ? 0 : -1} onClick={() => changeTab(item.id)}>{item.label}</button>)}
      </div>
      <div id={`${id}-panel`} role="tabpanel" aria-labelledby={`${id}-tab-${tab}`} className="workflow-content" aria-busy={busy} tabIndex={0}>
        {error ? <div className="workflow-empty" role="alert"><p>{error}</p><button type="button" onClick={() => { setBusy(true); setError(null); setRetry((value) => value + 1) }}>Try again</button></div> : null}
        {busy && !data ? <p className="workflow-empty" role="status">Reading files for this revision…</p> : null}
        {data && !error ? <>
          {data.scope.catalogId ? <p className="workflow-scope">{data.scope.name ?? 'Selected assembly'} · {data.scope.selectedInstances} of {data.scope.totalInstances} model parts</p> : null}
          {tab === 'print' ? <>
            <div className="workflow-print-controls">
              <div className="workflow-selection" role="group" aria-label="STL selection">
                <button type="button" aria-pressed={selection === 'all'} onClick={() => setSelection('all')}>All STLs</button>
                <button type="button" aria-pressed={selection === 'changed'} onClick={() => setSelection('changed')}>Changed STLs</button>
              </div>
              <label className="workflow-baseline">Compare with<select aria-label="Baseline revision" value={compare ?? data.comparison.version ?? ''} disabled={data.baselines.length === 0} onChange={(event) => { setBusy(true); setError(null); setCompare(event.target.value || undefined) }}>
                {!data.comparison.version && !compare ? <option value="">No earlier revision</option> : null}
                {data.baselines.map((baseline) => <option key={baseline.name} value={baseline.name}>{baseline.name}{baseline.message ? ` · ${baseline.message}` : ''}</option>)}
              </select></label>
            </div>
            <p className="workflow-note">{busy ? 'Comparing STL files…' : data.comparison.note}</p>
            {!millimeterUnits ? <div className="workflow-notice"><strong>STL export needs millimeter units</strong><p>This source uses “{data.source.units || 'unspecified'}” units. Record or convert the source to millimeters before downloading STLs.</p></div> : null}
            {rows.length ? <div className="workflow-table-wrap"><table className="workflow-files"><thead><tr><th>Printable part</th><th>{selection === 'changed' ? 'To print' : 'Quantity'}</th><th>STL file</th></tr></thead><tbody>
              {rows.map(({ part, file }) => <tr key={`${part.partType}-${file.id}`}><td><PartLabel part={part} onFocus={focusParts} showNotes />{data.downloads.changed ? <small className={`workflow-change workflow-change-${file.change}`}>{changeLabel[file.change]}{file.change === 'quantity' && file.previousQuantity !== null ? ` · ${file.previousQuantity} → ${file.quantity}` : ''}</small> : null}</td><td className="workflow-quantity">{selection === 'changed' ? file.quantityToPrint : file.quantity}</td><td>{file.change !== 'unavailable' && downloadUrl(file.downloadUrl) ? busy || !millimeterUnits ? <span>{file.fileName}</span> : <a href={downloadUrl(file.downloadUrl)} download>{file.fileName}</a> : <span>Unavailable</span>}</td></tr>)}
            </tbody></table></div> : <p className="workflow-empty">{selection === 'changed' ? data.downloads.changed ? 'No new or changed printable STLs in this revision.' : data.comparison.version ? 'Changed STLs cannot be determined from this incomplete baseline.' : 'Choose another revision to identify changed STLs.' : 'No parts are classified as printable in this revision.'}</p>}
            {missingParts.length ? <div className="workflow-notice"><strong>Some printable files are missing</strong><p>Restore these files to download a complete ZIP. Available STLs can still be downloaded individually.</p>{missingParts.map((part) => <p key={part.partType}>{part.label}: {part.errors.join(' ') || 'No STL file is available.'}</p>)}</div> : null}
            {selection === 'changed' && data.comparison.removed.length ? <details className="workflow-details"><summary>{countLabel(data.comparison.removed.length, 'removed part type')}</summary>{data.comparison.removed.map((part) => <p key={part.partType}>{part.partType} · {part.quantity} removed</p>)}</details> : null}
            {data.unknown.length ? <details className="workflow-details"><summary>{countLabel(data.unknown.length, 'unclassified part type')} · excluded from print downloads</summary><p>Printability has not been recorded for these parts.</p>{data.unknown.map((part) => <p key={part.partType}>{part.label} · quantity {part.quantity}</p>)}</details> : null}
            {data.other.length ? <details className="workflow-details"><summary>{countLabel(data.other.length, 'other part type')} · not classified for printing</summary>{data.other.map((part) => <p key={part.partType}>{part.label} · quantity {part.quantity}{part.notes ? ` · ${part.notes}` : ''}</p>)}</details> : null}
          </> : null}
          {tab === 'purchased' ? <>
            {data.bom.notes ? <p className="workflow-note">{data.bom.notes}</p> : null}
            {data.purchased.length || data.bom.items.length ? <div className="workflow-table-wrap"><table><thead><tr><th>Part</th><th>Quantity</th><th>Source</th></tr></thead><tbody>
              {data.purchased.map((part) => <tr key={part.partType}><td><PartLabel part={part} onFocus={focusParts} />{part.notes ? <small>{part.notes}</small> : null}</td><td className="workflow-quantity">{part.quantity}</td><td>{safeUrl(part.url) ? <a href={safeUrl(part.url)} target="_blank" rel="noreferrer">Source ↗</a> : 'Not recorded'}</td></tr>)}
              {data.bom.items.map((part) => <tr key={`bom-${part.id}`}><td><strong>{part.label}</strong>{part.notes ? <small>{part.notes}</small> : null}</td><td className="workflow-quantity">{part.quantity}{part.unit ? ` ${part.unit}` : ''}</td><td>{safeUrl(part.url) ? <a href={safeUrl(part.url)} target="_blank" rel="noreferrer">Source ↗</a> : 'Not recorded'}</td></tr>)}
            </tbody></table></div> : <p className="workflow-empty">No purchased parts have been recorded for this revision.</p>}
            {data.unknown.length ? <p className="workflow-note">{countLabel(data.unknown.length, 'part type')} still need classification; this list may be incomplete.</p> : null}
          </> : null}
          {tab === 'assembly' ? data.instructions.length ? <ol className="workflow-instructions">{data.instructions.map((instruction) => <li key={instruction.id}><h3>{instruction.title}</h3>{instruction.text ? <p>{instruction.text}</p> : null}{safeUrl(instruction.url) ? <a href={safeUrl(instruction.url)} target="_blank" rel="noreferrer">Open assembly reference ↗</a> : null}{focusParts && instruction.partTypes?.length ? <button type="button" className="workflow-text-button" onClick={() => focusParts(instruction.partTypes!)}>Show parts in model</button> : null}</li>)}</ol> : <p className="workflow-empty">No authored assembly instructions have been attached to this revision.</p> : null}
          {tab === 'runs' ? data.runs.length ? <ul className="workflow-runs">{data.runs.map((run) => <li key={run.id}><div><h3>{run.title}</h3><small>{run.association === 'exact-revision' ? 'This revision' : run.association === 'robot-family' ? 'Robot family · revision may differ' : 'Revision association unverified'}{run.status ? ` · ${run.status}` : ''}</small></div>{run.summary ? <p>{run.summary}</p> : null}{run.model ? <p className="workflow-note">Model: {run.model}</p> : null}{safeUrl(run.videoUrl) ? <video controls preload="metadata" playsInline src={safeUrl(run.videoUrl)} aria-label={`${run.title} video`} /> : null}<div className="workflow-run-links">{safeUrl(run.url) ? <a href={safeUrl(run.url)} target="_blank" rel="noreferrer">Open run ↗</a> : <span>Run link unavailable</span>}{safeUrl(run.videoUrl) ? <a href={safeUrl(run.videoUrl)} target="_blank" rel="noreferrer">Watch video ↗</a> : null}</div></li>)}</ul> : <p className="workflow-empty">No MuJoCo runs have been linked to this design.</p> : null}
          {data.warnings.length ? <details className="workflow-details"><summary>{countLabel(data.warnings.length, 'data note')}</summary>{data.warnings.map((warning, index) => <p key={index}>{warning}</p>)}</details> : null}
          {Object.values(data.metadata).some((provenance) => provenance.level !== 'exact-revision') ? <details className="workflow-details workflow-provenance"><summary>Where this information comes from</summary>{Object.values(data.metadata).map((provenance) => <p key={provenance.file}><strong>{provenance.file}</strong> · {provenance.note}</p>)}</details> : null}
        </> : null}
      </div>
      <footer className="workflow-footer">
        {data && !error && tab === 'print' ? <><div><strong>{countLabel(uniqueFiles, 'STL file')} · {countLabel(quantity, 'piece')}</strong><p>Download a 3MF tray with every selected copy laid out. Mesh integrity is checked before 3MF export. Keeps STL orientations; inspect supports in Bambu Studio before printing. Large selections download as a ZIP of trays.</p></div><label>Tray size <select aria-label="Tray size" value={printer} onChange={e => setPrinter(e.target.value)}><option value="x1c">256 × 256 mm (X1/P1/A1)</option><option value="h2d">350 × 320 mm (H2D)</option></select></label><button type="button" className="workflow-primary" disabled={!zipUrl || !uniqueFiles || busy || plateBusy || !millimeterUnits || missingParts.length > 0} onClick={() => void downloadPlate()}>{plateBusy ? 'Laying out tray…' : 'Download Bambu tray (.3mf)'}</button>{plateError ? <p role="alert">{plateError}</p> : null}{zipUrl && uniqueFiles > 0 && !busy && millimeterUnits && missingParts.length === 0 ? <a className="workflow-primary" href={zipUrl} download>Download {selection === 'changed' ? 'changed ' : ''}STLs</a> : <button type="button" className="workflow-primary" disabled>Download {selection === 'changed' ? 'changed ' : ''}STLs</button>}</> : null}
        {data && !error && tab === 'purchased' ? <><p>{countLabel(data.purchased.length + data.bom.items.length, 'line item')}</p><button type="button" className="workflow-primary" disabled={busy || data.purchased.length + data.bom.items.length === 0} onClick={() => exportBom(data)}>Download BOM CSV</button></> : null}
        {tab === 'assembly' || tab === 'runs' || !data || error ? <button type="button" onClick={closeWorkflow}>Back to model</button> : null}
      </footer>
    </dialog>, document.body)}
  </div>
}
