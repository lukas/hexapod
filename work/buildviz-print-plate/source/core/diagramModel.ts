// BuildViz DIAGRAM document model.
//
// A diagram is a standalone PRESENTATION document — not a build. An agent
// composes one when it wants to explain something to the human: place shapes
// and real build parts in 3D, draw arrows between them, and pin text callouts.
// Diagrams live on the hub under ~/.buildviz/diagrams/<name>/ and render in a
// dedicated viewer mode (/?diagram=<name>) with none of the build chrome.
//
// This module is the shared, browser-safe layer: types + validation only. The
// hub-side store (hub/diagramStore.ts) adds persistence and resolves `part`
// elements to concrete mesh assets; the viewer (viewer/src/DiagramViewer.tsx)
// renders the document. Agents author these documents sight-unseen over MCP,
// so validation is strict but every rejection names the element and problem.

import type { PrimitiveMesh, Vec3 } from './buildScene'

export const DIAGRAM_SCHEMA = 'buildviz-diagram/1'

export const DIAGRAM_ELEMENT_KINDS = [
  'box',
  'sphere',
  'cylinder',
  'line',
  'arrow',
  'text',
  'callout',
  'part',
] as const

export type DiagramElementKind = (typeof DIAGRAM_ELEMENT_KINDS)[number]

type ElementBase = {
  /** Unique id within the diagram; update_diagram upserts elements by id. */
  id: string
  /** Short floating label pinned to the element in the viewer. */
  label?: string
  /** CSS color, e.g. "#f97316". Each kind has a sensible default. */
  color?: string
  /** Solid opacity 0..1 (box / sphere / cylinder / part). Default 1. */
  opacity?: number
}

export type DiagramBox = ElementBase & {
  kind: 'box'
  /** Center [x,y,z] mm. */
  at: Vec3
  /** Extents [x,y,z] mm. */
  size: Vec3
  /** Rotation about X, Y, Z in degrees (applied XYZ order). */
  rotationDeg?: Vec3
  wireframe?: boolean
}

export type DiagramSphere = ElementBase & {
  kind: 'sphere'
  at: Vec3
  radiusMm: number
}

export type DiagramCylinder = ElementBase & {
  kind: 'cylinder'
  /** Axis runs from `from` to `to` (both [x,y,z] mm). */
  from: Vec3
  to: Vec3
  radiusMm: number
}

export type DiagramLine = ElementBase & {
  kind: 'line'
  /** Polyline through 2+ points, [x,y,z] mm each. */
  points: Vec3[]
  dashed?: boolean
}

export type DiagramArrow = ElementBase & {
  kind: 'arrow'
  from: Vec3
  /** The arrow HEAD sits at `to`. */
  to: Vec3
  /** Shaft radius mm. Default scales with arrow length. */
  shaftMm?: number
}

export type DiagramText = ElementBase & {
  kind: 'text'
  /** Anchor [x,y,z] mm; drawn as a screen-facing text overlay. */
  at: Vec3
  text: string
  /** Font size in px. Default 14. */
  sizePx?: number
}

export type DiagramCallout = ElementBase & {
  kind: 'callout'
  /** The point the callout points AT ([x,y,z] mm). */
  at: Vec3
  text: string
  /** Screen offset [x,y] px of the bubble from the anchor. Default [28,-28]. */
  offsetPx?: [number, number]
}

/** Mesh resolution written by the HUB when a part element is stored: the
 *  referenced build part's geometry snapshotted into the diagram's own assets
 *  so the diagram stays self-contained (renders even if the build moves on). */
export type DiagramPartMesh = {
  url?: string
  primitive?: PrimitiveMesh
  /** The instance color the part has in its source build (viewer default). */
  sourceColor?: string
  partType?: string
}

export type DiagramPart = ElementBase & {
  kind: 'part'
  /** Source build id, e.g. "prototype_sts3215" or "project/build". */
  buildId: string
  /** partType, mesh id, or instance id inside that build. */
  part: string
  branch?: string
  version?: string
  /** Placement of the part's LOCAL frame origin, [x,y,z] mm. Default [0,0,0]. */
  at?: Vec3
  rotationDeg?: Vec3
  /** Uniform scale factor. Default 1. */
  scale?: number
  /** Resolved by the hub at write time; never authored directly. */
  mesh?: DiagramPartMesh
}

export type DiagramElement =
  | DiagramBox
  | DiagramSphere
  | DiagramCylinder
  | DiagramLine
  | DiagramArrow
  | DiagramText
  | DiagramCallout
  | DiagramPart

export type DiagramCamera = {
  /** Camera position [x,y,z] mm (Z-up, like the build viewer). */
  position: Vec3
  /** Orbit target [x,y,z] mm. */
  target: Vec3
}

export type DiagramDocument = {
  schema: typeof DIAGRAM_SCHEMA
  title: string
  /** Free-form presenter notes shown in the side panel (plain text). */
  notes?: string
  /** Canvas background CSS color. Default "#0f172a". */
  background?: string
  /** Initial camera. Omit to auto-frame the elements. */
  camera?: DiagramCamera
  elements: DiagramElement[]
}

export const MAX_DIAGRAM_ELEMENTS = 500
export const MAX_DIAGRAM_TEXT_LENGTH = 2000
export const MAX_DIAGRAM_NOTES_LENGTH = 20_000

const isFiniteNumber = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value)

export const isDiagramVec3 = (value: unknown): value is Vec3 =>
  Array.isArray(value) && value.length === 3 && value.every(isFiniteNumber)

const isShortString = (value: unknown, max: number): value is string =>
  typeof value === 'string' && value.length > 0 && value.length <= max

// One element's problems, each prefixed with its position/id so an agent can
// fix exactly the offending element ("elements[3] (arrow \"load\"): ...").
const elementProblems = (value: unknown, index: number): string[] => {
  const where = (element: Record<string, unknown>) => {
    const id = typeof element.id === 'string' ? ` "${element.id}"` : ''
    const kind = typeof element.kind === 'string' ? element.kind : 'element'
    return `elements[${index}] (${kind}${id})`
  }
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    return [`elements[${index}]: must be an object`]
  }
  const element = value as Record<string, unknown>
  const label = where(element)
  const problems: string[] = []
  const need = (condition: boolean, message: string) => {
    if (!condition) problems.push(`${label}: ${message}`)
  }

  need(isShortString(element.id, 80), 'needs a unique string "id" (≤80 chars)')
  need(
    DIAGRAM_ELEMENT_KINDS.includes(element.kind as DiagramElementKind),
    `"kind" must be one of ${DIAGRAM_ELEMENT_KINDS.join(', ')}`,
  )
  if (element.label !== undefined) need(isShortString(element.label, 200), '"label" must be a string ≤200 chars')
  if (element.color !== undefined) need(isShortString(element.color, 40), '"color" must be a CSS color string')
  if (element.opacity !== undefined) {
    need(
      isFiniteNumber(element.opacity) && element.opacity > 0 && element.opacity <= 1,
      '"opacity" must be a number in (0, 1]',
    )
  }
  const vec = (key: string, required: boolean) => {
    if (element[key] === undefined) {
      need(!required, `needs "${key}" as [x,y,z] mm`)
      return
    }
    need(isDiagramVec3(element[key]), `"${key}" must be [x,y,z] (three finite numbers, mm)`)
  }
  const positive = (key: string, required: boolean) => {
    if (element[key] === undefined) {
      need(!required, `needs a positive "${key}" (mm)`)
      return
    }
    need(isFiniteNumber(element[key]) && (element[key] as number) > 0, `"${key}" must be a positive number (mm)`)
  }
  const text = (key: string, required: boolean, max = MAX_DIAGRAM_TEXT_LENGTH) => {
    if (element[key] === undefined) {
      need(!required, `needs string "${key}"`)
      return
    }
    need(isShortString(element[key], max), `"${key}" must be a non-empty string ≤${max} chars`)
  }

  switch (element.kind) {
    case 'box':
      vec('at', true)
      vec('size', true)
      if (isDiagramVec3(element.size)) {
        need(element.size.every((extent) => extent > 0), '"size" extents must all be > 0')
      }
      if (element.rotationDeg !== undefined) vec('rotationDeg', false)
      break
    case 'sphere':
      vec('at', true)
      positive('radiusMm', true)
      break
    case 'cylinder':
      vec('from', true)
      vec('to', true)
      positive('radiusMm', true)
      break
    case 'line':
      need(
        Array.isArray(element.points) && element.points.length >= 2 && element.points.every(isDiagramVec3),
        '"points" must be 2+ [x,y,z] points',
      )
      break
    case 'arrow':
      vec('from', true)
      vec('to', true)
      if (element.shaftMm !== undefined) positive('shaftMm', false)
      break
    case 'text':
      vec('at', true)
      text('text', true)
      if (element.sizePx !== undefined) positive('sizePx', false)
      break
    case 'callout':
      vec('at', true)
      text('text', true)
      if (element.offsetPx !== undefined) {
        need(
          Array.isArray(element.offsetPx) && element.offsetPx.length === 2 && element.offsetPx.every(isFiniteNumber),
          '"offsetPx" must be [x,y] pixels',
        )
      }
      break
    case 'part':
      text('buildId', true, 200)
      text('part', true, 200)
      if (element.at !== undefined) vec('at', false)
      if (element.rotationDeg !== undefined) vec('rotationDeg', false)
      if (element.scale !== undefined) positive('scale', false)
      break
    default:
      break
  }
  return problems
}

/** Validate a whole diagram document; throws one Error listing every problem. */
export const validateDiagramDocument = (value: unknown): DiagramDocument => {
  const problems: string[] = []
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new Error('Diagram must be a JSON object.')
  }
  const doc = value as Record<string, unknown>
  if (!isShortString(doc.title, 200)) problems.push('"title" must be a non-empty string ≤200 chars')
  if (doc.notes !== undefined && !isShortString(doc.notes, MAX_DIAGRAM_NOTES_LENGTH)) {
    problems.push(`"notes" must be a non-empty string ≤${MAX_DIAGRAM_NOTES_LENGTH} chars`)
  }
  if (doc.background !== undefined && !isShortString(doc.background, 40)) {
    problems.push('"background" must be a CSS color string')
  }
  if (doc.camera !== undefined) {
    const camera = doc.camera as Record<string, unknown> | null
    if (
      typeof camera !== 'object' ||
      camera === null ||
      !isDiagramVec3(camera.position) ||
      !isDiagramVec3(camera.target)
    ) {
      problems.push('"camera" must be { position: [x,y,z], target: [x,y,z] }')
    }
  }
  if (!Array.isArray(doc.elements)) {
    problems.push('"elements" must be an array')
  } else {
    if (doc.elements.length > MAX_DIAGRAM_ELEMENTS) {
      problems.push(`too many elements (${doc.elements.length}; cap ${MAX_DIAGRAM_ELEMENTS})`)
    }
    doc.elements.forEach((element, index) => problems.push(...elementProblems(element, index)))
    const ids = doc.elements
      .map((element) => (element as { id?: unknown })?.id)
      .filter((id): id is string => typeof id === 'string')
    const duplicates = ids.filter((id, index) => ids.indexOf(id) !== index)
    if (duplicates.length > 0) {
      problems.push(`duplicate element ids: ${[...new Set(duplicates)].join(', ')}`)
    }
  }
  if (problems.length > 0) {
    throw new Error(`Invalid diagram: ${problems.join('; ')}`)
  }
  return {
    schema: DIAGRAM_SCHEMA,
    title: doc.title as string,
    ...(doc.notes !== undefined ? { notes: doc.notes as string } : {}),
    ...(doc.background !== undefined ? { background: doc.background as string } : {}),
    ...(doc.camera !== undefined ? { camera: doc.camera as DiagramCamera } : {}),
    elements: doc.elements as DiagramElement[],
  }
}
