import * as THREE from 'three'
import type { InstanceGeometry } from './geometryEngine'

// Section FIGURES: true cross-section outlines of a placed assembly on an
// axis-aligned world plane, rendered as a labeled 2D SVG figure — the
// "matplotlib section plot" an agent would otherwise hand-write per question
// (before/after outlines overlaid, multiple cut heights, axis grid, legend).
//
// Unlike checks/buildvizGeometry's slice (an occupancy GRID for area/thickness
// metrics), this extracts the real mesh/plane intersection: every triangle
// crossing the plane contributes an exact segment (BVH shapecast prunes the
// rest), segments are welded into closed loops per instance, and the loops are
// drawn to scale with even-odd fill so holes read as holes.
//
// Pure geometry (three + three-mesh-bvh only), browser- and Node-safe: callers
// load instances with buildInstanceGeometries and hand them in. The same
// generator backs the CLI `section` command and the hub MCP tool
// `get_section_figure`.

export type SectionAxis = 'x' | 'y' | 'z'

export type SectionPlaneSpec = { axis: SectionAxis; value: number }

/** In-plane 2D axes (u, v) for a cut normal to `axis`, in world axis names. */
export const SECTION_UV: Record<SectionAxis, ['x' | 'y', 'y' | 'z']> = {
  z: ['x', 'y'],
  y: ['x', 'z'],
  x: ['y', 'z'],
}

const AXIS_INDEX: Record<SectionAxis, number> = { x: 0, y: 1, z: 2 }

// Cut planes are biased off the requested value by this much (mm) so a cut at
// a face plane (z=0 through the top of a sheet, the common case) slices solid
// material instead of degenerating on coplanar facets.
const PLANE_BIAS_MM = 1.5e-3
// Endpoint weld quantum (mm) for chaining segments into loops: adjacent
// triangles crossing a shared edge produce float-identical points; 2 µm-scale
// welding absorbs the noise without merging real geometry.
const WELD_MM = 2e-3
const fmt = (value: number) => {
  const rounded = Math.round(value * 100) / 100
  return Object.is(rounded, -0) ? '0' : String(rounded)
}
const escapeXml = (text: string) =>
  text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

export type SectionLoop = {
  /** Ordered (u, v) points in section-plane mm. */
  points: Array<[number, number]>
  closed: boolean
}

export type InstanceSectionOutline = {
  instanceId: string
  partType: string
  loops: SectionLoop[]
}

/** One build's outlines on one plane. */
export type PlaneOutlines = {
  plane: SectionPlaneSpec
  instances: InstanceSectionOutline[]
  segmentCount: number
  /** Net section area (outers minus holes, by nesting parity), mm². */
  areaMm2: number
}

// ---------------------------------------------------------------------------
// Contour extraction

const triPlaneSegment = (
  a: THREE.Vector3,
  b: THREE.Vector3,
  c: THREE.Vector3,
  plane: THREE.Plane,
  out: Array<[THREE.Vector3, THREE.Vector3]>,
) => {
  const da = plane.distanceToPoint(a)
  const db = plane.distanceToPoint(b)
  const dc = plane.distanceToPoint(c)
  const crossings: THREE.Vector3[] = []
  const edge = (p: THREE.Vector3, q: THREE.Vector3, dp: number, dq: number) => {
    if ((dp > 0 && dq > 0) || (dp < 0 && dq < 0) || dp === dq) return
    const t = dp / (dp - dq)
    if (!(t >= 0 && t <= 1)) return
    crossings.push(p.clone().lerp(q, t))
  }
  edge(a, b, da, db)
  edge(b, c, db, dc)
  edge(c, a, dc, da)
  if (crossings.length >= 2) out.push([crossings[0], crossings[1]])
}

/** Extract one instance's section segments on a world plane, in world coords. */
const instanceSegments = (
  instance: InstanceGeometry,
  axis: SectionAxis,
  value: number,
): Array<[THREE.Vector3, THREE.Vector3]> => {
  const axisIndex = AXIS_INDEX[axis]
  if (value < instance.worldMin[axisIndex] || value > instance.worldMax[axisIndex]) return []

  const normal = new THREE.Vector3()
  normal.setComponent(axisIndex, 1)
  const worldPlane = new THREE.Plane(normal, -value)
  // Express the plane in the instance's local frame so we can shapecast the
  // untransformed BVH; applyMatrix4(inverse) maps world-plane points to local.
  const localPlane = worldPlane.clone().applyMatrix4(instance.inverse)

  const segments: Array<[THREE.Vector3, THREE.Vector3]> = []
  instance.mesh.bvh.shapecast({
    intersectsBounds: (box: THREE.Box3) => localPlane.intersectsBox(box),
    intersectsTriangle: (tri: { a: THREE.Vector3; b: THREE.Vector3; c: THREE.Vector3 }) => {
      triPlaneSegment(tri.a, tri.b, tri.c, localPlane, segments)
      return false // keep traversing: we want every crossing triangle
    },
  })
  for (const segment of segments) {
    segment[0].applyMatrix4(instance.matrix)
    segment[1].applyMatrix4(instance.matrix)
  }
  return segments
}

// Chain welded 2D segments into ordered loops. Open chains (non-watertight
// meshes) are kept and drawn too — they are real geometry, just not fillable.
const chainLoops = (segments: Array<[[number, number], [number, number]]>): SectionLoop[] => {
  const invWeld = 1 / WELD_MM
  const keyOf = (p: [number, number]) => `${Math.round(p[0] * invWeld)},${Math.round(p[1] * invWeld)}`
  const nodePoint = new Map<string, [number, number]>()
  const adjacency = new Map<string, Array<{ segment: number; to: string }>>()

  const endpoints: Array<[string, string]> = []
  segments.forEach((segment, index) => {
    const ka = keyOf(segment[0])
    const kb = keyOf(segment[1])
    endpoints.push([ka, kb])
    if (ka === kb) return // degenerate sliver
    if (!nodePoint.has(ka)) nodePoint.set(ka, segment[0])
    if (!nodePoint.has(kb)) nodePoint.set(kb, segment[1])
    for (const [from, to] of [
      [ka, kb],
      [kb, ka],
    ] as const) {
      const list = adjacency.get(from)
      if (list) list.push({ segment: index, to })
      else adjacency.set(from, [{ segment: index, to }])
    }
  })

  const used = new Set<number>()
  const loops: SectionLoop[] = []
  const takeStep = (from: string): { segment: number; to: string } | null => {
    for (const step of adjacency.get(from) ?? []) {
      if (!used.has(step.segment)) return step
    }
    return null
  }

  segments.forEach((_, index) => {
    if (used.has(index)) return
    const [ka, kb] = endpoints[index]
    if (ka === kb) {
      used.add(index)
      return
    }
    used.add(index)
    const keys: string[] = [ka, kb]
    // Extend forward from the tail…
    for (;;) {
      const tail = keys[keys.length - 1]
      if (tail === keys[0]) break
      const step = takeStep(tail)
      if (!step) break
      used.add(step.segment)
      keys.push(step.to)
    }
    // …and backward from the head if still open.
    if (keys[keys.length - 1] !== keys[0]) {
      for (;;) {
        const step = takeStep(keys[0])
        if (!step) break
        used.add(step.segment)
        keys.unshift(step.to)
        if (keys[0] === keys[keys.length - 1]) break
      }
    }
    const closed = keys.length > 3 && keys[0] === keys[keys.length - 1]
    if (closed) keys.pop()
    if (keys.length < 3 && !closed) {
      if (keys.length < 2) return
    }
    const points = keys.map((key) => nodePoint.get(key)).filter((p): p is [number, number] => Boolean(p))
    if (points.length >= (closed ? 3 : 2)) loops.push({ points, closed })
  })
  return loops
}

const loopSignedArea = (points: Array<[number, number]>) => {
  let sum = 0
  for (let i = 0; i < points.length; i += 1) {
    const [u1, v1] = points[i]
    const [u2, v2] = points[(i + 1) % points.length]
    sum += u1 * v2 - u2 * v1
  }
  return sum / 2
}

const pointInLoop = (point: [number, number], loop: Array<[number, number]>) => {
  let inside = false
  for (let i = 0, j = loop.length - 1; i < loop.length; j = i, i += 1) {
    const [ui, vi] = loop[i]
    const [uj, vj] = loop[j]
    if (vi > point[1] !== vj > point[1] && point[0] < ((uj - ui) * (point[1] - vi)) / (vj - vi) + ui) {
      inside = !inside
    }
  }
  return inside
}

// Net area of one instance's loop set: nesting parity decides outer (+) vs
// hole (−), matching the even-odd fill the SVG uses.
const netArea = (loops: SectionLoop[]) => {
  const closed = loops.filter((loop) => loop.closed)
  let total = 0
  for (const loop of closed) {
    let depth = 0
    for (const other of closed) {
      if (other === loop) continue
      if (pointInLoop(loop.points[0], other.points)) depth += 1
    }
    total += (depth % 2 === 0 ? 1 : -1) * Math.abs(loopSignedArea(loop.points))
  }
  return total
}

/**
 * Cut every instance with one world plane and return per-instance loops in
 * section (u, v) coordinates.
 */
export const sectionOutlines = (
  instances: InstanceGeometry[],
  plane: SectionPlaneSpec,
): PlaneOutlines => {
  const [uAxis, vAxis] = SECTION_UV[plane.axis]
  const uIndex = AXIS_INDEX[uAxis]
  const vIndex = AXIS_INDEX[vAxis]
  const value = plane.value + PLANE_BIAS_MM
  const outlines: InstanceSectionOutline[] = []
  let segmentCount = 0
  let areaMm2 = 0
  for (const instance of instances) {
    const segments3 = instanceSegments(instance, plane.axis, value)
    if (segments3.length === 0) continue
    segmentCount += segments3.length
    const segments2 = segments3.map(
      ([p, q]) =>
        [
          [p.getComponent(uIndex), p.getComponent(vIndex)],
          [q.getComponent(uIndex), q.getComponent(vIndex)],
        ] as [[number, number], [number, number]],
    )
    const loops = chainLoops(segments2)
    if (loops.length === 0) continue
    areaMm2 += netArea(loops)
    outlines.push({ instanceId: instance.instanceId, partType: instance.partType, loops })
  }
  return {
    plane,
    instances: outlines,
    segmentCount,
    areaMm2: Math.round(areaMm2 * 10) / 10,
  }
}

/**
 * Return translated copies of placed instances (shared mesh geometry, new
 * transforms). Used to bring a compare build whose scene uses a different
 * world frame (e.g. robot-standing z offset) into the base build's frame.
 */
export const translateInstances = (
  instances: InstanceGeometry[],
  offset: [number, number, number],
): InstanceGeometry[] =>
  instances.map((instance) => {
    const matrix = new THREE.Matrix4()
      .makeTranslation(offset[0], offset[1], offset[2])
      .multiply(instance.matrix)
    return {
      ...instance,
      matrix,
      inverse: matrix.clone().invert(),
      worldMin: [
        instance.worldMin[0] + offset[0],
        instance.worldMin[1] + offset[1],
        instance.worldMin[2] + offset[2],
      ] as [number, number, number],
      worldMax: [
        instance.worldMax[0] + offset[0],
        instance.worldMax[1] + offset[1],
        instance.worldMax[2] + offset[2],
      ] as [number, number, number],
    }
  })

// ---------------------------------------------------------------------------
// Figure rendering

/** One build's worth of input: placed instances + optional per-instance colors. */
export type SectionSource = {
  instances: InstanceGeometry[]
  /** instanceId -> scene color; missing entries fall back to a palette. */
  colors?: Map<string, string>
  /** Legend label, e.g. "rigid-hip@main". */
  label?: string
}

export type SectionFigureOptions = {
  planes: SectionPlaneSpec[]
  /** Plot window in section (u, v) mm; default = data bounds + 5% pad. */
  window?: { min: [number, number]; max: [number, number] }
  title?: string
  subtitle?: string
}

export type SectionPlaneStats = {
  axis: SectionAxis
  value: number
  instanceCount: number
  loopCount: number
  areaMm2: number
  compareLoopCount: number | null
  compareAreaMm2: number | null
}

export type SectionFigure = {
  svg: string
  /** World axis names of the figure's horizontal and vertical axes. */
  axes: [string, string]
  window: { min: [number, number]; max: [number, number] }
  planes: SectionPlaneStats[]
}

const PART_PALETTE = ['#8b93a6', '#7ba1d1', '#c8a15a', '#7fb08a', '#b08bb5', '#a1b3c4', '#d1907b', '#90a8b0']
const PLANE_PALETTE = ['#374151', '#1c7c3c', '#1d4ed8', '#b45309', '#7c3aed', '#0f766e']
const COMPARE_COLOR = '#c0392b'

const niceStep = (span: number) => {
  const raw = span / 8
  const power = 10 ** Math.floor(Math.log10(Math.max(raw, 1e-6)))
  for (const mult of [1, 2, 5, 10]) {
    if (raw <= mult * power) return mult * power
  }
  return 10 * power
}

const loopsToPath = (loops: SectionLoop[], toX: (u: number) => number, toY: (v: number) => number) =>
  loops
    .map((loop) => {
      const cmds = loop.points.map(
        (point, i) => `${i === 0 ? 'M' : 'L'}${fmt(toX(point[0]))} ${fmt(toY(point[1]))}`,
      )
      return cmds.join('') + (loop.closed ? 'Z' : '')
    })
    .join('')

/**
 * Generate a labeled 2D section figure: the base build's outlines on one or
 * more parallel cut planes, optionally overlaid with a compare build's
 * outlines (dashed) for before/after review.
 *
 * Rendering rules: with ONE plane the base build is drawn as filled part
 * silhouettes (even-odd, scene part colors); with SEVERAL planes everything is
 * drawn as outlines colored per plane so the cuts can be compared. The compare
 * build is always dashed-red outlines on top.
 */
export const generateSectionFigure = (
  base: SectionSource,
  options: SectionFigureOptions,
  compare?: SectionSource,
): SectionFigure => {
  if (options.planes.length === 0) throw new Error('At least one cut plane is required.')
  const axis = options.planes[0].axis
  if (options.planes.some((plane) => plane.axis !== axis)) {
    throw new Error('All cut planes in one figure must share the same axis.')
  }
  const [uAxis, vAxis] = SECTION_UV[axis]

  const baseCuts = options.planes.map((plane) => sectionOutlines(base.instances, plane))
  const compareCuts = compare ? options.planes.map((plane) => sectionOutlines(compare.instances, plane)) : null

  // ---- Window ---------------------------------------------------------------
  let uMin = Infinity
  let vMin = Infinity
  let uMax = -Infinity
  let vMax = -Infinity
  for (const cut of [...baseCuts, ...(compareCuts ?? [])]) {
    for (const outline of cut.instances) {
      for (const loop of outline.loops) {
        for (const [u, v] of loop.points) {
          if (u < uMin) uMin = u
          if (v < vMin) vMin = v
          if (u > uMax) uMax = u
          if (v > vMax) vMax = v
        }
      }
    }
  }
  if (!Number.isFinite(uMin)) {
    uMin = 0
    vMin = 0
    uMax = 1
    vMax = 1
  }
  const pad = Math.max((uMax - uMin) * 0.05, (vMax - vMin) * 0.05, 2)
  const window = options.window ?? {
    min: [uMin - pad, vMin - pad] as [number, number],
    max: [uMax + pad, vMax + pad] as [number, number],
  }
  const spanU = Math.max(window.max[0] - window.min[0], 1e-3)
  const spanV = Math.max(window.max[1] - window.min[1], 1e-3)

  // ---- Sheet layout ----------------------------------------------------------
  const fs = Math.max(2.4, Math.min(6, Math.max(spanU, spanV) / 55)) // font size, mm
  const marginLeft = fs * 4.6
  const marginBottom = fs * 3.6
  const marginRight = fs * 1.2
  const marginTop = (options.title ? fs * 2.1 : 0) + (options.subtitle ? fs * 1.5 : 0) + fs * 0.9
  // Widen the sheet if the title/subtitle would overflow a narrow window.
  const titleW = options.title ? options.title.length * fs * 0.74 : 0
  const subtitleW = options.subtitle ? options.subtitle.length * fs * 0.53 : 0
  let sheetW = Math.max(marginLeft + spanU + marginRight, marginLeft + Math.max(titleW, subtitleW) + fs)
  const sheetH = marginTop + spanV + marginBottom
  const toX = (u: number) => marginLeft + (u - window.min[0])
  const toY = (v: number) => marginTop + (window.max[1] - v)

  const body: string[] = []

  // Grid + axis labels.
  const step = niceStep(Math.max(spanU, spanV))
  const grid: string[] = []
  const ticks: string[] = []
  for (let u = Math.ceil(window.min[0] / step) * step; u <= window.max[0] + 1e-9; u += step) {
    grid.push(`M${fmt(toX(u))} ${fmt(marginTop)}V${fmt(marginTop + spanV)}`)
    ticks.push(
      `<text class="tick" x="${fmt(toX(u))}" y="${fmt(marginTop + spanV + fs * 1.2)}" text-anchor="middle">${fmt(u)}</text>`,
    )
  }
  for (let v = Math.ceil(window.min[1] / step) * step; v <= window.max[1] + 1e-9; v += step) {
    grid.push(`M${fmt(marginLeft)} ${fmt(toY(v))}H${fmt(marginLeft + spanU)}`)
    ticks.push(
      `<text class="tick" x="${fmt(marginLeft - fs * 0.5)}" y="${fmt(toY(v) + fs * 0.36)}" text-anchor="end">${fmt(v)}</text>`,
    )
  }
  body.push(`<path class="grid" d="${grid.join('')}"/>`)
  body.push(...ticks)
  body.push(
    `<text class="axis" x="${fmt(marginLeft + spanU / 2)}" y="${fmt(sheetH - fs * 0.5)}" text-anchor="middle">${uAxis} (mm)</text>`,
  )
  body.push(
    `<text class="axis" x="${fmt(fs * 1.1)}" y="${fmt(marginTop + spanV / 2)}" text-anchor="middle" transform="rotate(-90 ${fmt(fs * 1.1)} ${fmt(marginTop + spanV / 2)})">${vAxis} (mm)</text>`,
  )

  // Content, clipped to the plot window.
  const clipped: string[] = [`<g clip-path="url(#plot)">`]
  const fillMode = options.planes.length === 1
  const partColor = new Map<string, string>()
  const colorFor = (outline: InstanceSectionOutline) => {
    const sceneColor = base.colors?.get(outline.instanceId)
    if (sceneColor) return sceneColor
    let color = partColor.get(outline.partType)
    if (!color) {
      color = PART_PALETTE[partColor.size % PART_PALETTE.length]
      partColor.set(outline.partType, color)
    }
    return color
  }

  baseCuts.forEach((cut, planeIndex) => {
    for (const outline of cut.instances) {
      const path = loopsToPath(outline.loops, toX, toY)
      if (!path) continue
      if (fillMode) {
        clipped.push(
          `<path fill="${colorFor(outline)}" fill-opacity="0.82" fill-rule="evenodd" stroke="#39414f" stroke-width="${fmt(fs * 0.09)}" d="${path}"/>`,
        )
      } else {
        const stroke = PLANE_PALETTE[planeIndex % PLANE_PALETTE.length]
        clipped.push(
          `<path fill="none" stroke="${stroke}" stroke-width="${fmt(fs * 0.16)}" stroke-linejoin="round" d="${path}"/>`,
        )
      }
    }
  })
  compareCuts?.forEach((cut) => {
    for (const outline of cut.instances) {
      const path = loopsToPath(outline.loops, toX, toY)
      if (!path) continue
      clipped.push(
        `<path fill="none" stroke="${COMPARE_COLOR}" stroke-width="${fmt(fs * 0.13)}" stroke-dasharray="${fmt(fs * 0.55)} ${fmt(fs * 0.4)}" stroke-linejoin="round" d="${path}"/>`,
      )
    }
  })
  clipped.push('</g>')
  body.push(...clipped)
  body.push(
    `<rect x="${fmt(marginLeft)}" y="${fmt(marginTop)}" width="${fmt(spanU)}" height="${fmt(spanV)}" fill="none" stroke="#8a8f98" stroke-width="${fmt(fs * 0.07)}"/>`,
  )

  // Legend: parts (fill mode) or planes (multi-plane), plus the compare entry.
  const legendRows: Array<{ color: string; label: string; dashed?: boolean; filled?: boolean }> = []
  if (fillMode) {
    const parts = new Map<string, string>()
    for (const outline of baseCuts[0].instances) {
      if (!parts.has(outline.partType)) parts.set(outline.partType, colorFor(outline))
    }
    const entries = [...parts.entries()]
    for (const [partType, color] of entries.slice(0, 9)) legendRows.push({ color, label: partType, filled: true })
    if (entries.length > 9) legendRows.push({ color: '#666', label: `… +${entries.length - 9} more part types` })
  } else {
    options.planes.forEach((plane, index) => {
      legendRows.push({
        color: PLANE_PALETTE[index % PLANE_PALETTE.length],
        // Base label only when a compare overlay needs disambiguating.
        label: `${plane.axis} = ${fmt(plane.value)}${compare && base.label ? ` (${base.label})` : ''}`,
      })
    })
  }
  if (compare) {
    legendRows.push({ color: COMPARE_COLOR, label: compare.label ?? 'compare', dashed: true })
  }
  if (legendRows.length > 0) {
    const rowH = fs * 1.35
    const widest = Math.max(...legendRows.map((row) => row.label.length))
    const legendW = fs * 2.6 + widest * fs * 0.52
    // Outside the plot, top-right: never occludes content (small windows
    // used to disappear behind an in-plot legend).
    const lx = marginLeft + spanU + fs * 0.8
    const ly = marginTop
    sheetW = Math.max(sheetW, lx + legendW + fs * 0.8)
    body.push(
      `<rect x="${fmt(lx)}" y="${fmt(ly)}" width="${fmt(legendW)}" height="${fmt(legendRows.length * rowH + fs * 0.6)}" fill="#fff" fill-opacity="0.88" stroke="#b6bcc6" stroke-width="${fmt(fs * 0.05)}"/>`,
    )
    legendRows.forEach((row, index) => {
      const cy = ly + fs * 0.55 + rowH * index + rowH / 2
      if (row.filled) {
        body.push(
          `<rect x="${fmt(lx + fs * 0.5)}" y="${fmt(cy - fs * 0.42)}" width="${fmt(fs * 1.3)}" height="${fmt(fs * 0.84)}" fill="${row.color}" fill-opacity="0.82" stroke="#39414f" stroke-width="${fmt(fs * 0.05)}"/>`,
        )
      } else {
        body.push(
          `<path stroke="${row.color}" stroke-width="${fmt(fs * 0.16)}"${row.dashed ? ` stroke-dasharray="${fmt(fs * 0.55)} ${fmt(fs * 0.4)}"` : ''} d="M${fmt(lx + fs * 0.5)} ${fmt(cy)}h${fmt(fs * 1.3)}"/>`,
        )
      }
      body.push(
        `<text class="legend" x="${fmt(lx + fs * 2.2)}" y="${fmt(cy + fs * 0.36)}">${escapeXml(row.label)}</text>`,
      )
    })
  }

  const header: string[] = []
  if (options.title) {
    header.push(`<text class="title" x="${fmt(marginLeft)}" y="${fmt(fs * 1.5)}">${escapeXml(options.title)}</text>`)
  }
  if (options.subtitle) {
    header.push(
      `<text class="subtitle" x="${fmt(marginLeft)}" y="${fmt((options.title ? fs * 2.1 : 0) + fs * 1.1)}">${escapeXml(options.subtitle)}</text>`,
    )
  }

  const svg = [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${fmt(sheetW)} ${fmt(sheetH)}" width="${fmt(sheetW * 4)}" height="${fmt(sheetH * 4)}" font-family="ui-sans-serif, system-ui, sans-serif">`,
    '<style>',
    `.grid{stroke:#d9dde3;stroke-width:${fmt(fs * 0.045)};fill:none}`,
    `.tick{font-size:${fmt(fs * 0.85)}px;fill:#5a6068}`,
    `.axis{font-size:${fmt(fs)}px;fill:#343a42;font-weight:600}`,
    `.legend{font-size:${fmt(fs * 0.9)}px;fill:#23272e}`,
    `.title{font-size:${fmt(fs * 1.25)}px;font-weight:700;fill:#111}`,
    `.subtitle{font-size:${fmt(fs * 0.9)}px;fill:#555}`,
    '</style>',
    `<defs><clipPath id="plot"><rect x="${fmt(marginLeft)}" y="${fmt(marginTop)}" width="${fmt(spanU)}" height="${fmt(spanV)}"/></clipPath></defs>`,
    `<rect x="0" y="0" width="${fmt(sheetW)}" height="${fmt(sheetH)}" fill="#fff"/>`,
    ...header,
    ...body,
    '</svg>',
  ].join('\n')

  return {
    svg,
    axes: [uAxis, vAxis],
    window: {
      min: [Math.round(window.min[0] * 100) / 100, Math.round(window.min[1] * 100) / 100],
      max: [Math.round(window.max[0] * 100) / 100, Math.round(window.max[1] * 100) / 100],
    },
    planes: options.planes.map((plane, index) => ({
      axis: plane.axis,
      value: plane.value,
      instanceCount: baseCuts[index].instances.length,
      loopCount: baseCuts[index].instances.reduce((sum, outline) => sum + outline.loops.length, 0),
      areaMm2: baseCuts[index].areaMm2,
      compareLoopCount: compareCuts
        ? compareCuts[index].instances.reduce((sum, outline) => sum + outline.loops.length, 0)
        : null,
      compareAreaMm2: compareCuts ? compareCuts[index].areaMm2 : null,
    })),
  }
}

// ---------------------------------------------------------------------------
// Shared argument parsing (CLI flag values and MCP string args)

/** Parse "z=0" / "z=0,z=-4" / "x=12.5" into plane specs (one shared axis). */
export const parseSectionPlanes = (raw: string | undefined): SectionPlaneSpec[] => {
  if (!raw || !raw.trim()) throw new Error('Missing cut plane(s); use e.g. "z=0" or "z=0,z=-4".')
  const planes = raw.split(',').map((entry) => {
    const match = entry.trim().match(/^([xyz])\s*=\s*(-?\d+(?:\.\d+)?)$/i)
    if (!match) throw new Error(`Invalid plane "${entry.trim()}". Use axis=value, e.g. z=0.`)
    return { axis: match[1].toLowerCase() as SectionAxis, value: Number(match[2]) }
  })
  if (new Set(planes.map((plane) => plane.axis)).size > 1) {
    throw new Error('All cut planes in one figure must share the same axis.')
  }
  return planes
}

/**
 * Parse a 2D window like "x=55:135,y=-40:40". Axis names must be the section's
 * own in-plane axes for the given cut axis (e.g. x and y for a z cut).
 */
export const parseSectionWindow = (
  raw: string | undefined,
  axis: SectionAxis,
): { min: [number, number]; max: [number, number] } | undefined => {
  if (!raw || !raw.trim()) return undefined
  const [uAxis, vAxis] = SECTION_UV[axis]
  const ranges = new Map<string, [number, number]>()
  for (const segment of raw.split(',')) {
    const match = segment.trim().match(/^([xyz])\s*=\s*(-?\d+(?:\.\d+)?):(-?\d+(?:\.\d+)?)$/i)
    if (!match) throw new Error(`Invalid window segment "${segment.trim()}". Use axis=lo:hi.`)
    ranges.set(match[1].toLowerCase(), [Number(match[2]), Number(match[3])])
  }
  const u = ranges.get(uAxis)
  const v = ranges.get(vAxis)
  if (!u || !v) {
    throw new Error(`Window for a ${axis} cut needs both in-plane axes: ${uAxis}=lo:hi,${vAxis}=lo:hi.`)
  }
  return { min: [Math.min(...u), Math.min(...v)], max: [Math.max(...u), Math.max(...v)] }
}
