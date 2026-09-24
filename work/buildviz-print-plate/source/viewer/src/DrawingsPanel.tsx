import { useEffect, useMemo, useRef, useState } from 'react'
import type { BuildSceneManifest } from '../../core/buildScene'
import { parseStl } from '../../core/geometryEngine'
import {
  DRAWING_VIEW_NAMES,
  generatePartDrawing,
  resolvePartMesh,
  type DrawingViewName,
  type PartDrawing,
} from '../../core/schematicDrawing'

// Drawings: schematic engineering drawings (orthographic axis views with
// dimensions + hidden lines) of a single part, generated in the browser from
// the part's STL — the human-facing twin of the hub's get_part_drawing MCP
// tool. The sheet opens as a MODAL over the main screen with the generation
// options (part, views, hidden lines) in its toolbar; the sidebar control
// group is just the launcher. Drawings generate AUTOMATICALLY whenever the
// selected part or options change — there is no explicit Generate button.

type DrawingsPanelProps = {
  manifest: BuildSceneManifest
  /** Label stamped on the sheet subtitle, e.g. "prototype_sts3215@main@v58". */
  buildLabel: string
  /**
   * External "draw this part" request (from the viewer's right-click menu).
   * A new nonce opens the modal, selects the part, and generates immediately.
   */
  request?: { partType: string; nonce: number } | null
  /**
   * Render the sidebar launcher group. When the user hides the Drawings panel
   * via the Panels picker this is false, but the component stays mounted so
   * the right-click → drawing modal keeps working.
   */
  showLauncher?: boolean
  open: boolean
  modeKey: string
  onToggleOpen: (open: boolean) => void
}

const DEFAULT_VIEWS: DrawingViewName[] = ['front', 'right', 'top']

// Freehand annotation stroke, recorded in the sheet's own viewBox coordinates
// (millimetres), so scribbles stay glued to the drawing at any display size
// and can be embedded 1:1 into the downloaded SVG.
type Stroke = { color: string; points: Array<[number, number]> }

const SCRIBBLE_COLORS = ['#e11d48', '#2563eb', '#16a34a', '#111111']

const strokePath = (stroke: Stroke) => {
  const [first, ...rest] = stroke.points
  if (!first) return ''
  // A click without movement still leaves a visible dot (round linecap).
  if (rest.length === 0) return `M${first[0]} ${first[1]}l0.01 0`
  return `M${first[0]} ${first[1]}` + rest.map(([x, y]) => `L${x} ${y}`).join('')
}

/** Parse "viewBox=\"0 0 W H\"" out of the generated sheet. */
const sheetSize = (svg: string): { w: number; h: number } => {
  const match = svg.match(/viewBox="0 0 ([\d.]+) ([\d.]+)"/)
  return match ? { w: Number(match[1]), h: Number(match[2]) } : { w: 100, h: 100 }
}

/** Inject the scribbles into the sheet SVG text (before </svg>). */
const svgWithAnnotations = (svg: string, strokes: Stroke[], strokeWidth: number) => {
  if (strokes.length === 0) return svg
  const paths = strokes
    .map((stroke) => `<path d="${strokePath(stroke)}" stroke="${stroke.color}"/>`)
    .join('')
  const group =
    `<g class="annotations" fill="none" stroke-width="${strokeWidth}" ` +
    'stroke-linecap="round" stroke-linejoin="round" opacity="0.9">' +
    paths +
    '</g>'
  return svg.replace('</svg>', `${group}</svg>`)
}

export const DrawingsPanel = ({
  manifest,
  buildLabel,
  request,
  showLauncher = true,
  open,
  modeKey,
  onToggleOpen,
}: DrawingsPanelProps) => {
  const partTypes = useMemo(
    () => [...new Set(manifest.instances.map((instance) => instance.partType).filter(Boolean))].sort(),
    [manifest],
  )
  const [modalOpen, setModalOpen] = useState(false)
  const [part, setPart] = useState('')
  const [views, setViews] = useState<Set<DrawingViewName>>(new Set(DEFAULT_VIEWS))
  const [includeHidden, setIncludeHidden] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [drawing, setDrawing] = useState<{ part: string; result: PartDrawing } | null>(null)
  // Scribble layer: pen on/off, ink color, committed strokes, and the stroke
  // being drawn right now (kept separate so pointermove only re-renders it).
  const [scribble, setScribble] = useState(true)
  const [inkColor, setInkColor] = useState(SCRIBBLE_COLORS[0])
  const [strokes, setStrokes] = useState<Stroke[]>([])
  const [currentStroke, setCurrentStroke] = useState<Stroke | null>(null)

  // Signature of the last generation kicked off (part + options); the
  // auto-generate effect skips when it already ran for the current inputs so
  // e.g. closing and reopening the modal keeps the sheet AND its scribbles.
  const generatedSignatureRef = useRef('')
  // Monotonic run id: with auto-generation, quick option toggles can overlap
  // async runs, and only the latest may write its result into state.
  const runIdRef = useRef(0)

  // Reset when the build changes (React-recommended derive-during-render).
  const [prevManifest, setPrevManifest] = useState(manifest)
  if (prevManifest !== manifest) {
    setPrevManifest(manifest)
    setPart('')
    setDrawing(null)
    setError(null)
    setModalOpen(false)
  }
  // Ref writes are not allowed during render, so the signature reset that
  // accompanies the state reset above lives in its own manifest-keyed effect.
  useEffect(() => {
    generatedSignatureRef.current = ''
  }, [manifest])

  const generate = async (partRef: string = part) => {
    if (!partRef) return
    const runId = ++runIdRef.current
    setRunning(true)
    setError(null)
    try {
      const { mesh, partType } = resolvePartMesh(manifest, partRef)
      if (!mesh.url) throw new Error(`Mesh "${mesh.id}" has no asset URL.`)
      const response = await fetch(mesh.url)
      if (!response.ok) throw new Error(`Failed to fetch mesh (${response.status}).`)
      const geometry = parseStl(await response.arrayBuffer())
      const ordered = DRAWING_VIEW_NAMES.filter((view) => views.has(view))
      const result = generatePartDrawing(geometry, {
        views: ordered.length > 0 ? ordered : DEFAULT_VIEWS,
        includeHidden,
        title: partType,
        subtitle: buildLabel,
      })
      if (runId !== runIdRef.current) return
      setDrawing({ part: partType, result })
      setStrokes([])
      setCurrentStroke(null)
    } catch (caught) {
      if (runId !== runIdRef.current) return
      setError(caught instanceof Error ? caught.message : String(caught))
      setDrawing(null)
      // A failed run must not "claim" its signature, or reopening the modal
      // (same inputs) would show the error forever instead of retrying.
      generatedSignatureRef.current = ''
    } finally {
      if (runId === runIdRef.current) setRunning(false)
    }
  }
  const generateRef = useRef<(partRef?: string) => Promise<void>>(async () => {})
  useEffect(() => {
    generateRef.current = generate
  })

  // Act on a right-click "draw this part" request exactly once per nonce: open
  // the modal on the requested part; the auto-generate effect below draws it.
  const handledNonceRef = useRef(0)
  useEffect(() => {
    if (!request || request.nonce === handledNonceRef.current) return
    handledNonceRef.current = request.nonce
    setPart(request.partType)
    setModalOpen(true)
  }, [request])

  // Auto-generate: whenever the modal is open with a part selected and the
  // part/views/hidden-lines inputs differ from the last generated sheet,
  // regenerate immediately — no Generate button to click.
  const signature = `${part}|${DRAWING_VIEW_NAMES.filter((view) => views.has(view)).join(',')}|${includeHidden}`
  useEffect(() => {
    if (!modalOpen || !part) return
    if (generatedSignatureRef.current === signature) return
    generatedSignatureRef.current = signature
    void generateRef.current(part)
  }, [modalOpen, part, signature])

  // Escape closes the modal (unless typing in a field).
  useEffect(() => {
    if (!modalOpen) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setModalOpen(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [modalOpen])

  const toggleView = (view: DrawingViewName) => {
    setViews((current) => {
      const next = new Set(current)
      if (next.has(view)) next.delete(view)
      else next.add(view)
      return next
    })
  }

  // Sheet dimensions (viewBox mm) drive the scribble overlay's coordinate
  // space and a sensible ink width relative to the sheet size.
  const sheet = useMemo(() => (drawing ? sheetSize(drawing.result.svg) : null), [drawing])
  const inkWidth = sheet ? Math.min(1.5, Math.max(0.45, sheet.w / 450)) : 0.6

  const scribblePoint = (event: React.PointerEvent<SVGSVGElement>): [number, number] => {
    const clamp = (value: number, hi: number) => Math.min(hi, Math.max(0, Math.round(value * 20) / 20))
    // Map screen px → viewBox mm through the SVG's own transform: exact under
    // any preserveAspectRatio letterboxing, unlike linear bounding-rect math.
    const ctm = event.currentTarget.getScreenCTM()
    if (!ctm) return [0, 0]
    const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(ctm.inverse())
    return [clamp(point.x, sheet?.w ?? 1), clamp(point.y, sheet?.h ?? 1)]
  }

  const onScribbleDown = (event: React.PointerEvent<SVGSVGElement>) => {
    if (!scribble || event.button !== 0) return
    event.currentTarget.setPointerCapture(event.pointerId)
    setCurrentStroke({ color: inkColor, points: [scribblePoint(event)] })
  }

  const onScribbleMove = (event: React.PointerEvent<SVGSVGElement>) => {
    if (!currentStroke) return
    const point = scribblePoint(event)
    setCurrentStroke((stroke) => (stroke ? { ...stroke, points: [...stroke.points, point] } : stroke))
  }

  const onScribbleUp = () => {
    if (!currentStroke) return
    setStrokes((all) => [...all, currentStroke])
    setCurrentStroke(null)
  }

  const download = () => {
    if (!drawing) return
    const svg = svgWithAnnotations(drawing.result.svg, strokes, inkWidth)
    const blob = new Blob([svg], { type: 'image/svg+xml' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${drawing.part.replace(/[^\w.-]+/g, '_')}_drawing.svg`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <>
      {showLauncher ? (
      <details
        className="control-group drawings-controls"
        open={open}
        key={`drawings-${modeKey}`}
        onToggle={(event) => onToggleOpen(event.currentTarget.open)}
      >
        <summary>
          <span>Drawings</span>
          <small>{drawing ? drawing.part : 'schematic views'}</small>
        </summary>
        <div className="control-content drawings-content">
          <p className="drawings-hint">
            Dimensioned orthographic views of a single part. Also available by right-clicking a part
            in the 3D view.
          </p>
          <div className="drawings-actions">
            <button type="button" onClick={() => setModalOpen(true)}>
              {drawing ? `Open drawing (${drawing.part})` : 'Open drawings…'}
            </button>
          </div>
        </div>
      </details>
      ) : null}

      {modalOpen ? (
        <div className="drawings-modal-backdrop" onClick={() => setModalOpen(false)}>
          <div
            className="drawings-modal"
            role="dialog"
            aria-label="Schematic part drawing"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="drawings-modal-toolbar">
              <label className="select-control drawings-part">
                <span>Part</span>
                <select value={part} onChange={(event) => setPart(event.currentTarget.value)}>
                  <option value="">Select a part…</option>
                  {partTypes.map((partType) => (
                    <option key={partType} value={partType}>
                      {partType}
                    </option>
                  ))}
                </select>
              </label>
              <div className="drawings-views">
                {DRAWING_VIEW_NAMES.map((view) => (
                  <label key={view} className="checkbox-control">
                    <input type="checkbox" checked={views.has(view)} onChange={() => toggleView(view)} />
                    <span>{view}</span>
                  </label>
                ))}
              </div>
              <label className="checkbox-control">
                <input
                  type="checkbox"
                  checked={includeHidden}
                  onChange={(event) => setIncludeHidden(event.currentTarget.checked)}
                />
                <span>Hidden lines</span>
              </label>
              {drawing ? (
                <div className="drawings-scribble-tools">
                  <button
                    type="button"
                    className={`drawings-pen ${scribble ? 'active' : ''}`}
                    onClick={() => setScribble((current) => !current)}
                    title="Scribble on the drawing (freehand pen)"
                    aria-pressed={scribble}
                  >
                    ✏️ Scribble
                  </button>
                  {SCRIBBLE_COLORS.map((color) => (
                    <button
                      key={color}
                      type="button"
                      className={`drawings-ink ${inkColor === color ? 'active' : ''}`}
                      style={{ background: color }}
                      onClick={() => {
                        setInkColor(color)
                        setScribble(true)
                      }}
                      aria-label={`Ink color ${color}`}
                    />
                  ))}
                  <button
                    type="button"
                    onClick={() => setStrokes((all) => all.slice(0, -1))}
                    disabled={strokes.length === 0}
                    title="Remove the last stroke"
                  >
                    Undo
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setStrokes([])
                      setCurrentStroke(null)
                    }}
                    disabled={strokes.length === 0 && !currentStroke}
                    title="Remove all scribbles"
                  >
                    Clear
                  </button>
                </div>
              ) : null}
              <div className="drawings-modal-buttons">
                {running ? <span className="drawings-running">Drawing…</span> : null}
                <button type="button" onClick={download} disabled={!drawing}>
                  Download SVG
                </button>
                <button
                  type="button"
                  className="drawings-close"
                  onClick={() => setModalOpen(false)}
                  aria-label="Close drawing"
                  title="Close (Esc)"
                >
                  ✕
                </button>
              </div>
            </div>
            {error ? <p className="drawings-error">{error}</p> : null}
            <div className="drawings-modal-sheet">
              {drawing ? (
                <div className="drawings-sheet">
                  <div
                    className="drawings-sheet-svg"
                    // The SVG is generated locally from mesh geometry (no user HTML).
                    dangerouslySetInnerHTML={{ __html: drawing.result.svg }}
                  />
                  {sheet ? (
                    <svg
                      className={`drawings-scribble ${scribble ? 'active' : ''}`}
                      viewBox={`0 0 ${sheet.w} ${sheet.h}`}
                      onPointerDown={onScribbleDown}
                      onPointerMove={onScribbleMove}
                      onPointerUp={onScribbleUp}
                      onPointerCancel={onScribbleUp}
                    >
                      <g fill="none" strokeWidth={inkWidth} strokeLinecap="round" strokeLinejoin="round" opacity={0.9}>
                        {strokes.map((stroke, index) => (
                          <path key={index} d={strokePath(stroke)} stroke={stroke.color} />
                        ))}
                        {currentStroke ? <path d={strokePath(currentStroke)} stroke={currentStroke.color} /> : null}
                      </g>
                    </svg>
                  ) : null}
                </div>
              ) : (
                <p className="drawings-empty">
                  {running
                    ? 'Generating drawing…'
                    : 'Pick a part above — or right-click a part in the 3D view. The drawing generates automatically.'}
                </p>
              )}
            </div>
            {drawing ? (
              <small className="drawings-meta">
                {drawing.part} · bbox {drawing.result.bboxMm.size.join(' × ')} mm ·{' '}
                {drawing.result.views.map((view) => view.view).join(', ')} · units mm
              </small>
            ) : null}
          </div>
        </div>
      ) : null}
    </>
  )
}
