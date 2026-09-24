import * as THREE from 'three'
import { MeshBVH } from 'three-mesh-bvh'
import type { BuildMesh, BuildSceneManifest } from './buildScene'

// Schematic (engineering-style) drawings of a SINGLE part: orthographic
// projections straight down the world axes, drawn as an SVG sheet with
// visible edges solid, hidden edges dashed, and overall dimensions annotated.
//
// The pipeline is pure geometry (no renderer, no canvas), so it runs the same
// in the browser (viewer Drawings panel) and in Node (CLI / hub MCP tool):
//   1. weld the STL vertex soup so edges have real adjacency,
//   2. keep boundary edges, sharp (feature) edges, and per-view silhouette
//      edges — smooth tessellation edges (cylinder walls etc.) drop out,
//   3. classify sub-segments visible/hidden by raycasting toward the camera
//      against the part's own BVH (hidden-line removal),
//   4. project orthographically onto the view plane and lay the requested
//      views out on one dimensioned sheet (third-angle-style grid).
//
// Coordinates are millimetres end to end; the SVG viewBox is in mm so the
// drawing is intrinsically to scale.

export type DrawingViewName = 'front' | 'back' | 'left' | 'right' | 'top' | 'bottom'

export const DRAWING_VIEW_NAMES: DrawingViewName[] = ['front', 'back', 'left', 'right', 'top', 'bottom']

export type DrawingOptions = {
  /** Views to draw. Default: front, right, top (classic three-view). */
  views?: DrawingViewName[]
  /** Draw hidden (occluded) edges as dashed lines. Default true. */
  includeHidden?: boolean
  /** Dihedral angle (deg) at/above which an edge is a feature edge. Default 25. */
  featureAngleDeg?: number
  /** Title printed on the sheet (part name). */
  title?: string
  /** Extra subtitle line (build id / version). */
  subtitle?: string
}

export type DrawingViewStats = {
  view: DrawingViewName
  /** Projected extents of the part in this view (mm). */
  widthMm: number
  heightMm: number
  visibleSegments: number
  hiddenSegments: number
}

export type PartDrawing = {
  svg: string
  views: DrawingViewStats[]
  /** Local-frame bounding box of the part (mm). */
  bboxMm: { min: [number, number, number]; max: [number, number, number]; size: [number, number, number] }
  triangleCount: number
}

// Z-up view bases. `dir` is the viewing direction (camera looks along it);
// `up` is screen-up; screen-right = dir × up. Front looks along +Y (camera at
// -Y), right looks along -X (camera at +X), top looks along -Z (camera above).
const VIEW_BASES: Record<DrawingViewName, { dir: [number, number, number]; up: [number, number, number] }> = {
  front: { dir: [0, 1, 0], up: [0, 0, 1] },
  back: { dir: [0, -1, 0], up: [0, 0, 1] },
  right: { dir: [-1, 0, 0], up: [0, 0, 1] },
  left: { dir: [1, 0, 0], up: [0, 0, 1] },
  top: { dir: [0, 0, -1], up: [0, 1, 0] },
  bottom: { dir: [0, 0, 1], up: [0, -1, 0] },
}

// Third-angle-style sheet grid (col, row). Front is the anchor; top sits above
// it, right to its right, etc. Views not requested leave their cell empty.
const VIEW_CELLS: Record<DrawingViewName, [number, number]> = {
  top: [1, 0],
  left: [0, 1],
  front: [1, 1],
  right: [2, 1],
  back: [3, 1],
  bottom: [1, 2],
}

type Segment2 = { x1: number; y1: number; x2: number; y2: number }

type WeldedEdge = {
  a: THREE.Vector3
  b: THREE.Vector3
  n1: THREE.Vector3
  n2: THREE.Vector3 | null
  sharp: boolean
}

const DEGENERATE_AREA_MM2 = 1e-6

// Weld the STL vertex soup by quantized position and build the unique-edge
// list with adjacent face normals — the input for feature/silhouette tests.
const buildEdgeGraph = (geometry: THREE.BufferGeometry, featureAngleDeg: number): WeldedEdge[] => {
  const position = geometry.attributes.position as THREE.BufferAttribute
  const index = geometry.index
  const triangleCount = (index ? index.count : position.count) / 3

  const box = geometry.boundingBox ?? new THREE.Box3().setFromBufferAttribute(position)
  const size = new THREE.Vector3()
  box.getSize(size)
  const weld = Math.max(1e-4, size.length() * 1e-6)
  const invWeld = 1 / weld

  const vertexIds = new Map<string, number>()
  const vertexPos: THREE.Vector3[] = []
  const readVertex = (triangle: number, corner: number, out: THREE.Vector3) => {
    const i = index ? index.getX(triangle * 3 + corner) : triangle * 3 + corner
    out.set(position.getX(i), position.getY(i), position.getZ(i))
  }
  const idFor = (v: THREE.Vector3) => {
    const key = `${Math.round(v.x * invWeld)},${Math.round(v.y * invWeld)},${Math.round(v.z * invWeld)}`
    let id = vertexIds.get(key)
    if (id === undefined) {
      id = vertexIds.size
      vertexIds.set(key, id)
      vertexPos.push(v.clone())
    }
    return id
  }

  const edges = new Map<number, { ia: number; ib: number; n1: THREE.Vector3; n2: THREE.Vector3 | null }>()
  const a = new THREE.Vector3()
  const b = new THREE.Vector3()
  const c = new THREE.Vector3()
  const ab = new THREE.Vector3()
  const ac = new THREE.Vector3()

  for (let t = 0; t < triangleCount; t += 1) {
    readVertex(t, 0, a)
    readVertex(t, 1, b)
    readVertex(t, 2, c)
    ab.subVectors(b, a)
    ac.subVectors(c, a)
    const normal = new THREE.Vector3().crossVectors(ab, ac)
    const area = normal.length() * 0.5
    const ia = idFor(a)
    const ib = idFor(b)
    const ic = idFor(c)
    if (area <= DEGENERATE_AREA_MM2 || ia === ib || ib === ic || ia === ic) continue
    normal.multiplyScalar(1 / (area * 2))
    for (const [u, v] of [
      [ia, ib],
      [ib, ic],
      [ic, ia],
    ]) {
      const lo = Math.min(u, v)
      const hi = Math.max(u, v)
      const key = lo * 0x4000000 + hi
      const entry = edges.get(key)
      if (entry) {
        if (!entry.n2) entry.n2 = normal
        // >2 adjacent faces (non-manifold): keep the first two — good enough
        // for a schematic.
      } else {
        edges.set(key, { ia: lo, ib: hi, n1: normal, n2: null })
      }
    }
  }

  const sharpCos = Math.cos((featureAngleDeg * Math.PI) / 180)
  const out: WeldedEdge[] = []
  for (const entry of edges.values()) {
    const sharp = entry.n2 ? entry.n1.dot(entry.n2) < sharpCos : false
    out.push({
      a: vertexPos[entry.ia],
      b: vertexPos[entry.ib],
      n1: entry.n1,
      n2: entry.n2,
      sharp,
    })
  }
  return out
}

// Classify sub-segments of `edge` as visible/hidden in view direction `dir` by
// casting a ray from each sub-segment midpoint toward the camera. The origin
// is nudged toward the camera AND along the local outward normal so the ray
// clears the faces the edge itself lies on (silhouette edges graze the surface
// in the view direction, which is exactly the hard case).
const classifyEdge = (
  edge: WeldedEdge,
  dir: THREE.Vector3,
  bvh: MeshBVH,
  stepMm: number,
  epsMm: number,
  visibleOut: Array<[THREE.Vector3, THREE.Vector3]>,
  hiddenOut: Array<[THREE.Vector3, THREE.Vector3]>,
) => {
  const length = edge.a.distanceTo(edge.b)
  const pieces = Math.min(12, Math.max(1, Math.round(length / stepMm)))
  const toCamera = dir.clone().multiplyScalar(-1)
  const outward = edge.n2 ? edge.n1.clone().add(edge.n2).normalize() : edge.n1.clone()

  const mid = new THREE.Vector3()
  const origin = new THREE.Vector3()
  let runStart = 0
  let runVisible: boolean | null = null

  const flush = (endT: number) => {
    if (runVisible === null || endT <= runStart) return
    const p1 = edge.a.clone().lerp(edge.b, runStart)
    const p2 = edge.a.clone().lerp(edge.b, endT)
    ;(runVisible ? visibleOut : hiddenOut).push([p1, p2])
  }

  for (let i = 0; i < pieces; i += 1) {
    const t0 = i / pieces
    const t1 = (i + 1) / pieces
    mid.copy(edge.a).lerp(edge.b, (t0 + t1) / 2)
    origin.copy(mid).addScaledVector(toCamera, epsMm).addScaledVector(outward, epsMm * 0.5)
    const hits = bvh.raycast(new THREE.Ray(origin.clone(), toCamera), THREE.DoubleSide)
    const visible = hits.length === 0
    if (runVisible === null) {
      runVisible = visible
      runStart = t0
    } else if (visible !== runVisible) {
      flush(t0)
      runVisible = visible
      runStart = t0
    }
  }
  flush(1)
}

const fmt = (value: number) => {
  const rounded = Math.round(value * 100) / 100
  return Object.is(rounded, -0) ? '0' : String(rounded)
}

const escapeXml = (text: string) =>
  text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

// Segments → compact SVG path ("M x y L x y" pairs).
const segmentsToPath = (segments: Segment2[]) =>
  segments.map((s) => `M${fmt(s.x1)} ${fmt(s.y1)}L${fmt(s.x2)} ${fmt(s.y2)}`).join('')

// A dimension line with extension lines, arrowheads and a centred label.
// Horizontal when `horizontal`, else vertical. All coordinates sheet-local mm.
const dimensionSvg = (
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  offset: number,
  label: string,
  horizontal: boolean,
): string => {
  const parts: string[] = []
  const arrow = 1.6
  if (horizontal) {
    const y = y1 + offset
    parts.push(`<path class="dim" d="M${fmt(x1)} ${fmt(y1 + 1)}L${fmt(x1)} ${fmt(y + 1.5)}M${fmt(x2)} ${fmt(y2 + 1)}L${fmt(x2)} ${fmt(y + 1.5)}M${fmt(x1)} ${fmt(y)}L${fmt(x2)} ${fmt(y)}"/>`)
    parts.push(`<path class="dim" d="M${fmt(x1)} ${fmt(y)}l${arrow} ${-arrow / 2.6}v${fmt(arrow / 1.3)}zM${fmt(x2)} ${fmt(y)}l${-arrow} ${-arrow / 2.6}v${fmt(arrow / 1.3)}z" fill="currentColor"/>`)
    parts.push(`<text class="dim-text" x="${fmt((x1 + x2) / 2)}" y="${fmt(y - 1.2)}" text-anchor="middle">${escapeXml(label)}</text>`)
  } else {
    const x = x1 - offset
    parts.push(`<path class="dim" d="M${fmt(x1 - 1)} ${fmt(y1)}L${fmt(x - 1.5)} ${fmt(y1)}M${fmt(x2 - 1)} ${fmt(y2)}L${fmt(x - 1.5)} ${fmt(y2)}M${fmt(x)} ${fmt(y1)}L${fmt(x)} ${fmt(y2)}"/>`)
    parts.push(`<path class="dim" d="M${fmt(x)} ${fmt(y1)}l${-arrow / 2.6} ${arrow}h${fmt(arrow / 1.3)}zM${fmt(x)} ${fmt(y2)}l${-arrow / 2.6} ${-arrow}h${fmt(arrow / 1.3)}z" fill="currentColor"/>`)
    parts.push(`<text class="dim-text" x="${fmt(x - 1.6)}" y="${fmt((y1 + y2) / 2)}" text-anchor="middle" transform="rotate(-90 ${fmt(x - 1.6)} ${fmt((y1 + y2) / 2)})">${escapeXml(label)}</text>`)
  }
  return parts.join('')
}

type ProjectedView = {
  view: DrawingViewName
  visible: Segment2[]
  hidden: Segment2[]
  /** Projected bbox, y-up flipped to SVG (y grows down), normalized to 0,0. */
  widthMm: number
  heightMm: number
}

/**
 * Generate a multi-view schematic drawing of one part.
 *
 * `geometry` is the part's LOCAL mesh geometry (untransformed STL), so the
 * drawing is in the part's own frame with its native axes.
 */
export const generatePartDrawing = (
  geometry: THREE.BufferGeometry,
  options: DrawingOptions = {},
): PartDrawing => {
  const views = (options.views && options.views.length > 0 ? options.views : ['front', 'right', 'top']).filter(
    (view, i, all): view is DrawingViewName => DRAWING_VIEW_NAMES.includes(view as DrawingViewName) && all.indexOf(view) === i,
  )
  if (views.length === 0) throw new Error(`No valid views requested. Valid: ${DRAWING_VIEW_NAMES.join(', ')}`)
  const includeHidden = options.includeHidden ?? true
  const featureAngleDeg = options.featureAngleDeg ?? 25

  if (!geometry.boundingBox) geometry.computeBoundingBox()
  const box = geometry.boundingBox ?? new THREE.Box3()
  const size = new THREE.Vector3()
  box.getSize(size)
  const diag = Math.max(size.length(), 1e-3)
  const triangleCount = (geometry.index ? geometry.index.count : geometry.attributes.position.count) / 3

  const bvh = (geometry.boundsTree as MeshBVH | undefined) ?? new MeshBVH(geometry)
  const edges = buildEdgeGraph(geometry, featureAngleDeg)

  // Sub-segment sampling density for hidden-line classification: fine enough
  // that visibility transitions land near the right spot, bounded per edge.
  const stepMm = Math.max(0.5, diag / 80)
  const epsMm = Math.max(0.02, diag * 1.5e-3)

  const projected: ProjectedView[] = []
  const dirV = new THREE.Vector3()
  const upV = new THREE.Vector3()
  const rightV = new THREE.Vector3()

  for (const view of views) {
    const basis = VIEW_BASES[view]
    dirV.set(...basis.dir)
    upV.set(...basis.up)
    rightV.crossVectors(dirV, upV)

    const visible3: Array<[THREE.Vector3, THREE.Vector3]> = []
    const hidden3: Array<[THREE.Vector3, THREE.Vector3]> = []
    for (const edge of edges) {
      const d1 = edge.n1.dot(dirV)
      const d2 = edge.n2 ? edge.n2.dot(dirV) : 0
      const silhouette = edge.n2 !== null && d1 * d2 < 0
      const boundary = edge.n2 === null
      if (!boundary && !edge.sharp && !silhouette) continue
      classifyEdge(edge, dirV, bvh, stepMm, epsMm, visible3, includeHidden ? hidden3 : [])
    }

    const project = (segments: Array<[THREE.Vector3, THREE.Vector3]>): Segment2[] =>
      segments.map(([p1, p2]) => ({
        x1: p1.dot(rightV),
        y1: -p1.dot(upV),
        x2: p2.dot(rightV),
        y2: -p2.dot(upV),
      }))
    const visible = project(visible3)
    const hidden = project(hidden3)

    // Normalize the view to its own origin so sheet layout is a translate.
    let minX = Infinity
    let minY = Infinity
    let maxX = -Infinity
    let maxY = -Infinity
    for (const s of [...visible, ...hidden]) {
      minX = Math.min(minX, s.x1, s.x2)
      minY = Math.min(minY, s.y1, s.y2)
      maxX = Math.max(maxX, s.x1, s.x2)
      maxY = Math.max(maxY, s.y1, s.y2)
    }
    if (!Number.isFinite(minX)) {
      minX = 0
      minY = 0
      maxX = 0
      maxY = 0
    }
    for (const s of [...visible, ...hidden]) {
      s.x1 -= minX
      s.y1 -= minY
      s.x2 -= minX
      s.y2 -= minY
    }
    projected.push({ view, visible, hidden, widthMm: maxX - minX, heightMm: maxY - minY })
  }

  // ---- Sheet layout (third-angle grid) -------------------------------------
  // Space reserved around each view for its dimension annotations + label.
  const dimPad = 12
  const cellGap = 10
  const cols = new Map<number, number>()
  const rows = new Map<number, number>()
  for (const pv of projected) {
    const [col, row] = VIEW_CELLS[pv.view]
    cols.set(col, Math.max(cols.get(col) ?? 0, pv.widthMm + dimPad + 6))
    rows.set(row, Math.max(rows.get(row) ?? 0, pv.heightMm + dimPad + 8))
  }
  const colOrder = [...cols.keys()].sort((a, b) => a - b)
  const rowOrder = [...rows.keys()].sort((a, b) => a - b)
  const colX = new Map<number, number>()
  const rowY = new Map<number, number>()
  let cursor = cellGap
  for (const col of colOrder) {
    colX.set(col, cursor)
    cursor += (cols.get(col) ?? 0) + cellGap
  }
  const sheetW = Math.max(cursor, 80)
  const titleH = options.title ? 14 : 6
  cursor = cellGap + titleH
  for (const row of rowOrder) {
    rowY.set(row, cursor)
    cursor += (rows.get(row) ?? 0) + cellGap
  }
  const sheetH = cursor

  const body: string[] = []
  const stats: DrawingViewStats[] = []
  for (const pv of projected) {
    const [col, row] = VIEW_CELLS[pv.view]
    // Anchor each view inside its cell, leaving the dimension margin on the
    // left/bottom (height dim on the left, width dim + label below).
    const ox = (colX.get(col) ?? 0) + dimPad
    const oy = rowY.get(row) ?? 0
    const group: string[] = [`<g transform="translate(${fmt(ox)} ${fmt(oy)})">`]
    if (pv.hidden.length > 0) group.push(`<path class="hidden-edge" d="${segmentsToPath(pv.hidden)}"/>`)
    if (pv.visible.length > 0) group.push(`<path class="edge" d="${segmentsToPath(pv.visible)}"/>`)
    group.push(dimensionSvg(0, pv.heightMm, pv.widthMm, pv.heightMm, 5, fmt(pv.widthMm), true))
    group.push(dimensionSvg(0, 0, 0, pv.heightMm, 5, fmt(pv.heightMm), false))
    group.push(
      `<text class="view-label" x="${fmt(pv.widthMm / 2)}" y="${fmt(pv.heightMm + 11)}" text-anchor="middle">${pv.view.toUpperCase()}</text>`,
    )
    group.push('</g>')
    body.push(group.join(''))
    stats.push({
      view: pv.view,
      widthMm: Math.round(pv.widthMm * 100) / 100,
      heightMm: Math.round(pv.heightMm * 100) / 100,
      visibleSegments: pv.visible.length,
      hiddenSegments: pv.hidden.length,
    })
  }

  const header: string[] = []
  if (options.title) {
    header.push(`<text class="title" x="${fmt(cellGap)}" y="8">${escapeXml(options.title)}</text>`)
    const sub = [
      options.subtitle,
      `bbox ${fmt(size.x)} × ${fmt(size.y)} × ${fmt(size.z)} mm`,
      'units: mm',
      includeHidden ? 'dashed = hidden' : null,
    ]
      .filter(Boolean)
      .join('  ·  ')
    header.push(`<text class="subtitle" x="${fmt(cellGap)}" y="13">${escapeXml(sub)}</text>`)
  }

  const svg = [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${fmt(sheetW)} ${fmt(sheetH)}" width="${fmt(sheetW * 4)}" height="${fmt(sheetH * 4)}" font-family="ui-sans-serif, system-ui, sans-serif">`,
    '<style>',
    '.edge{stroke:#111;stroke-width:0.35;fill:none;stroke-linecap:round}',
    '.hidden-edge{stroke:#999;stroke-width:0.22;fill:none;stroke-dasharray:1.6 1.1;stroke-linecap:round}',
    '.dim{stroke:#2563eb;stroke-width:0.15;fill:none;color:#2563eb}',
    '.dim-text{font-size:3px;fill:#2563eb}',
    '.view-label{font-size:3.4px;font-weight:600;fill:#333;letter-spacing:0.4px}',
    '.title{font-size:4.6px;font-weight:700;fill:#111}',
    '.subtitle{font-size:2.8px;fill:#555}',
    '</style>',
    `<rect x="0" y="0" width="${fmt(sheetW)}" height="${fmt(sheetH)}" fill="#fff"/>`,
    ...header,
    ...body,
    '</svg>',
  ].join('\n')

  return {
    svg,
    views: stats,
    bboxMm: {
      min: [box.min.x, box.min.y, box.min.z].map((v) => Math.round(v * 100) / 100) as [number, number, number],
      max: [box.max.x, box.max.y, box.max.z].map((v) => Math.round(v * 100) / 100) as [number, number, number],
      size: [size.x, size.y, size.z].map((v) => Math.round(v * 100) / 100) as [number, number, number],
    },
    triangleCount,
  }
}

/**
 * Resolve a user-supplied part reference against a manifest: a partType (the
 * usual case), a mesh id, or an instance id. Throws with the available part
 * types when nothing matches.
 */
export const resolvePartMesh = (
  manifest: BuildSceneManifest,
  partRef: string,
): { mesh: BuildMesh; partType: string; instanceCount: number } => {
  const ref = partRef.trim()
  const byPartType = manifest.instances.find((instance) => instance.partType === ref)
  const byInstance = byPartType ?? manifest.instances.find((instance) => instance.id === ref)
  const meshId = byInstance?.meshId ?? (manifest.meshes.some((mesh) => mesh.id === ref) ? ref : null)
  const mesh = meshId ? manifest.meshes.find((entry) => entry.id === meshId) : undefined
  if (!mesh) {
    const partTypes = [...new Set(manifest.instances.map((instance) => instance.partType))].sort()
    throw new Error(
      `No part "${ref}" in this build. Pass a partType, mesh id, or instance id. ` +
        `Part types: ${partTypes.slice(0, 60).join(', ')}${partTypes.length > 60 ? ', …' : ''}`,
    )
  }
  const partType = byInstance?.partType ?? manifest.instances.find((instance) => instance.meshId === mesh.id)?.partType ?? mesh.id
  const instanceCount = manifest.instances.filter((instance) => instance.meshId === mesh.id).length
  return { mesh, partType, instanceCount }
}

/** Parse a comma/space separated views string ("front,top right") into view names. */
export const parseDrawingViews = (raw: string | undefined): DrawingViewName[] | undefined => {
  if (!raw) return undefined
  const wanted = raw
    .split(/[\s,]+/)
    .map((entry) => entry.trim().toLowerCase())
    .filter(Boolean)
  if (wanted.length === 0) return undefined
  if (wanted.includes('all')) return [...DRAWING_VIEW_NAMES]
  const invalid = wanted.filter((entry) => !DRAWING_VIEW_NAMES.includes(entry as DrawingViewName))
  if (invalid.length > 0) {
    throw new Error(`Unknown view(s): ${invalid.join(', ')}. Valid: ${DRAWING_VIEW_NAMES.join(', ')}, all`)
  }
  return wanted as DrawingViewName[]
}
