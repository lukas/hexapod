import { useEffect, useMemo, useRef, useState } from 'react'
import { load as loadYaml } from 'js-yaml'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js'
import type { BuildInstance, BuildMesh, BuildSceneManifest, Vec3 } from '../../core/buildScene'
import { specCoverage } from '../../core/buildvizCore'
import { resolveRoute, routeDisplayColor, sampleRoute } from '../../core/buildWiring'
import type { DiffStatus } from '../../core/buildDiff'
import { poseInstanceMatrices, type JointValues } from '../../core/buildvizKinematics'
import { printMeshForPart, printableStl, stlFilename } from './partStl'
import { isCoarsePointer, isCompactLayout } from './compactLayout'

type BuildViewerProps = {
  manifest: BuildSceneManifest
  designSpecUrl?: string | null
  visiblePartTypes: Set<string>
  // A saved catalog view limits the source scene to this explicit selection.
  // Undefined means the whole scene; an empty set deliberately shows no parts.
  visibleInstanceIds?: Set<string>
  focusGroup: string | null
  rulerMode: boolean
  pickerMode: boolean
  diffStatuses?: Record<string, DiffStatus> | null
  // Per-partType color overrides chosen from the Part Types control. Applied in
  // the normal (non-highlight, non-diff) state; highlight still takes precedence.
  partTypeColors?: Record<string, string>
  // Phase 3 pose scrubber: joint values to drive forward kinematics. Null/empty
  // (or a scene with no joints) renders the static home pose, exactly as before.
  jointValues?: JointValues | null
  // Reports design-spec warnings (missing spec, uncovered scene parts, stale
  // entries) up to the shell so the version dropdown can badge them. Called
  // once the spec fetch for the current build has settled.
  onSpecWarnings?: (warnings: string[]) => void
  // Render the scene's wires/cables (routes[]) as tubes with anchor markers.
  // Ignored (nothing drawn) when the scene has no routes.
  showWires?: boolean
  // Right-click context menu: "Schematic drawing" hands the picked part's type
  // up to the shell, which opens the Drawings panel and generates the sheet.
  onRequestDrawing?: (partType: string) => void
  // Reports the part type of the currently selected instance (null when the
  // selection clears) so the shell can mirror it in the Part Types list.
  onSelectedPartType?: (partType: string | null) => void
}

type RenderedPart = {
  instance: BuildInstance
  mesh: THREE.Mesh
  baseMatrix: THREE.Matrix4
  material: THREE.MeshStandardMaterial
}

type DesignDimension = {
  label?: string
  value?: number | string
  axis?: string
  from_mm?: unknown
  to_mm?: unknown
  description?: string
}

type DesignFeature = {
  label?: string
  kind?: string
  purpose?: string
  render?: {
    anchor_mm?: unknown
    label_offset_mm?: unknown
  }
  dimensions?: Record<string, DesignDimension>
}

type DesignHole = {
  name?: string
  diameter_mm?: number
  position_mm?: unknown
  axis?: string
}

type DesignPart = {
  label?: string
  description?: string
  bounds_mm?: unknown
  features?: Record<string, DesignFeature>
  holes?: DesignHole[]
}

type DesignSpec = {
  parts?: Record<string, DesignPart>
}

type WorldLabel = {
  id: string
  text: string
  point: THREE.Vector3
  detail?: string
}

type WorldDimension = {
  id: string
  text: string
  from: THREE.Vector3
  to: THREE.Vector3
}

type WorldMeasurement = {
  from: THREE.Vector3
  to: THREE.Vector3
  length: number
  partName: string
}

type ScreenOverlays = {
  labels: Array<{ id: string; text: string; detail?: string; marker: number; x: number; y: number }>
  dimensions: Array<{ id: string; text: string; x1: number; y1: number; x2: number; y2: number }>
}

type ScreenAgentAnnotation = {
  id: string
  text: string
  color: string
  x: number
  y: number
}

type ScreenMeasurement = {
  label: string
  x1: number
  y1: number
  x2: number
  y2: number
  x: number
  y: number
}

type WorldPick = {
  point: THREE.Vector3
  localPoint: THREE.Vector3
  partName: string
  partType: string
}

type ScreenPick = {
  label: string
  detail: string
  x: number
  y: number
}

type ScreenPickMarker = {
  x: number
  y: number
}

type AgentPartHighlight =
  | string
  | {
      partType?: string
      instanceId?: string
      group?: string
      color?: string
      label?: string
      annotation?: string
    }

type AgentPointHighlight = {
  id?: string
  point: Vec3
  partType?: string
  instanceId?: string
  color?: string
  label?: string
  annotation?: string
  radiusMm?: number
}

type AgentLineHighlight = {
  id?: string
  from: Vec3
  to: Vec3
  partType?: string
  instanceId?: string
  color?: string
  label?: string
  annotation?: string
}

type AgentRegionHighlight = {
  id?: string
  min: Vec3
  max: Vec3
  partType?: string
  instanceId?: string
  color?: string
  label?: string
  annotation?: string
}

type AgentAnnotationHighlight = {
  id?: string
  text: string
  point?: Vec3
  partType?: string
  instanceId?: string
  color?: string
}

type AgentHighlightSpec = {
  frame?: boolean
  ghostOthers?: boolean
  parts?: AgentPartHighlight[]
  points?: AgentPointHighlight[]
  lines?: AgentLineHighlight[]
  regions?: AgentRegionHighlight[]
  annotations?: AgentAnnotationHighlight[]
  // Annotated review link: a human-review question pinned to the highlighted
  // parts. When present the viewer shows a prominent banner with the text. Built
  // by the in-viewer "Share review link" action on top of the same highlight API.
  question?: string
}

// True when a highlight spec actually targets something (any geometry highlight,
// not just a bare question). Used to decide whether a review link needs a
// fallback target (the selected part).
const hasHighlightTargets = (spec: AgentHighlightSpec) =>
  Boolean(
    (spec.parts && spec.parts.length > 0) ||
      (spec.points && spec.points.length > 0) ||
      (spec.lines && spec.lines.length > 0) ||
      (spec.regions && spec.regions.length > 0),
  )

declare global {
  interface Window {
    buildviz?: {
      setHighlights: (highlights: AgentHighlightSpec) => void
      clearHighlights: () => void
    }
  }
}

const emptyScreenOverlays: ScreenOverlays = { labels: [], dimensions: [] }
const defaultAgentHighlightColor = '#f97316'

const isVec3 = (value: unknown): value is Vec3 =>
  Array.isArray(value) &&
  value.length === 3 &&
  value.every((item) => typeof item === 'number' && Number.isFinite(item))

const parseDesignSpec = (source: string | null): DesignSpec | null => {
  if (!source) return null

  try {
    const parsed = loadYaml(source)
    return typeof parsed === 'object' && parsed !== null ? (parsed as DesignSpec) : null
  } catch {
    return null
  }
}

const formatValue = (value: unknown) =>
  value === undefined || value === null || value === '' ? '' : ` ${value}`

const formatLength = (length: number) => `${length.toFixed(length >= 10 ? 0 : 1)}mm`

const formatCoordinate = (value: number) => {
  const rounded = Math.abs(value) < 0.005 ? 0 : value
  return rounded.toFixed(2)
}

const transformPoint = (matrix: THREE.Matrix4, point: Vec3) =>
  new THREE.Vector3(...point).applyMatrix4(matrix)

const distanceToSegment = (point: THREE.Vector3, start: THREE.Vector3, end: THREE.Vector3) => {
  const segment = end.clone().sub(start)
  const lengthSquared = segment.lengthSq()
  if (lengthSquared === 0) return point.distanceTo(start)

  const t = THREE.MathUtils.clamp(point.clone().sub(start).dot(segment) / lengthSquared, 0, 1)
  return point.distanceTo(start.clone().add(segment.multiplyScalar(t)))
}

const vertexAt = (mesh: THREE.Mesh, index: number) => {
  const position = mesh.geometry.getAttribute('position')
  return new THREE.Vector3(position.getX(index), position.getY(index), position.getZ(index))
    .applyMatrix4(mesh.matrixWorld)
}

const measurementFromHit = (hit: THREE.Intersection<THREE.Object3D>) => {
  const mesh = hit.object instanceof THREE.Mesh ? hit.object : null
  if (!mesh || !hit.face) return null

  mesh.updateMatrixWorld(true)
  const vertices = [
    vertexAt(mesh, hit.face.a),
    vertexAt(mesh, hit.face.b),
    vertexAt(mesh, hit.face.c),
  ]
  const edges = [
    [vertices[0], vertices[1]],
    [vertices[1], vertices[2]],
    [vertices[2], vertices[0]],
  ] as const
  const [from, to] = edges.reduce((best, edge) =>
    distanceToSegment(hit.point, edge[0], edge[1]) < distanceToSegment(hit.point, best[0], best[1])
      ? edge
      : best,
  )

  return {
    from,
    to,
    length: from.distanceTo(to),
    partName: typeof mesh.userData.instanceName === 'string' ? mesh.userData.instanceName : 'edge',
  }
}

// A point pinned with the ruler: subsequent measurements run from here to the
// hovered/tapped surface point instead of snapping to a single edge.
type RulerAnchor = {
  point: THREE.Vector3
  partName: string
}

const instanceNameOfHit = (hit: THREE.Intersection<THREE.Object3D>) => {
  const name = hit.object.userData.instanceName
  return typeof name === 'string' ? name : 'part'
}

const anchorFromHit = (hit: THREE.Intersection<THREE.Object3D>): RulerAnchor => ({
  point: hit.point.clone(),
  partName: instanceNameOfHit(hit),
})

const measurementFromAnchor = (
  anchor: RulerAnchor,
  hit: THREE.Intersection<THREE.Object3D>,
): WorldMeasurement => {
  const hitName = instanceNameOfHit(hit)
  return {
    from: anchor.point.clone(),
    to: hit.point.clone(),
    length: anchor.point.distanceTo(hit.point),
    partName: hitName === anchor.partName ? hitName : `${anchor.partName} → ${hitName}`,
  }
}

const pickFromHit = (hit: THREE.Intersection<THREE.Object3D>): WorldPick | null => {
  const mesh = hit.object instanceof THREE.Mesh ? hit.object : null
  if (!mesh) return null

  mesh.updateMatrixWorld(true)
  const localPoint = mesh.worldToLocal(hit.point.clone())
  return {
    point: hit.point.clone(),
    localPoint,
    partName: typeof mesh.userData.instanceName === 'string' ? mesh.userData.instanceName : 'part',
    partType: typeof mesh.userData.partType === 'string' ? mesh.userData.partType : 'unknown',
  }
}

const decodeHighlightParam = (value: string) => {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

const parseInitialHighlightsFromUrl = (): AgentHighlightSpec => {
  const params = new URLSearchParams(window.location.search)
  const raw = params.get('highlight') ?? params.get('highlights')
  if (!raw) return {}

  try {
    const parsed = JSON.parse(decodeHighlightParam(raw))
    return typeof parsed === 'object' && parsed !== null ? (parsed as AgentHighlightSpec) : {}
  } catch (error) {
    console.warn('Could not parse BuildViz highlight URL parameter', error)
    return {}
  }
}

const partHighlightMatches = (highlight: AgentPartHighlight, instance: BuildInstance) => {
  if (typeof highlight === 'string') {
    return (
      highlight === instance.id ||
      highlight === instance.partType ||
      highlight === instance.focusGroup
    )
  }

  return Boolean(
    (highlight.instanceId && highlight.instanceId === instance.id) ||
      (highlight.partType && highlight.partType === instance.partType) ||
      (highlight.group && highlight.group === instance.focusGroup),
  )
}

const matchingPartHighlight = (highlights: AgentHighlightSpec, instance: BuildInstance) =>
  highlights.parts?.find((highlight) => partHighlightMatches(highlight, instance)) ?? null

const highlightColor = (
  highlight:
    | AgentPartHighlight
    | AgentPointHighlight
    | AgentLineHighlight
    | AgentRegionHighlight
    | AgentAnnotationHighlight
    | null,
) =>
  typeof highlight === 'object' && highlight?.color ? highlight.color : defaultAgentHighlightColor

const highlightAnnotation = (
  highlight: AgentPartHighlight | AgentPointHighlight | AgentLineHighlight | AgentRegionHighlight,
) => (typeof highlight === 'object' ? highlight.annotation ?? highlight.label : undefined)

const targetMatrixForHighlight = (
  highlight: { partType?: string; instanceId?: string },
  parts: RenderedPart[],
) => {
  if (highlight.instanceId) {
    return parts.find((part) => part.instance.id === highlight.instanceId)?.baseMatrix
  }
  if (highlight.partType) {
    return parts.find((part) => part.instance.partType === highlight.partType)?.baseMatrix
  }
  return null
}

const pointForHighlight = (
  point: Vec3,
  highlight: { partType?: string; instanceId?: string },
  parts: RenderedPart[],
) => {
  const matrix = targetMatrixForHighlight(highlight, parts)
  const vector = new THREE.Vector3(...point)
  return matrix ? vector.applyMatrix4(matrix) : vector
}

const partCenter = (part: RenderedPart) => {
  if (part.instance.centroid) return new THREE.Vector3(...part.instance.centroid)

  part.mesh.geometry.computeBoundingBox()
  const box = part.mesh.geometry.boundingBox
  if (!box) return new THREE.Vector3().setFromMatrixPosition(part.baseMatrix)
  return box.getCenter(new THREE.Vector3()).applyMatrix4(part.baseMatrix)
}

const targetPointForAnnotation = (
  annotation: { point?: Vec3; partType?: string; instanceId?: string },
  parts: RenderedPart[],
) => {
  if (annotation.point && isVec3(annotation.point)) {
    return pointForHighlight(annotation.point, annotation, parts)
  }

  const part = annotation.instanceId
    ? parts.find((item) => item.instance.id === annotation.instanceId)
    : annotation.partType
      ? parts.find((item) => item.instance.partType === annotation.partType)
      : null

  return part ? partCenter(part) : null
}

const makeRegionBox = (
  region: AgentRegionHighlight,
  parts: RenderedPart[],
) => {
  const corners = ([
    [region.min[0], region.min[1], region.min[2]],
    [region.max[0], region.min[1], region.min[2]],
    [region.min[0], region.max[1], region.min[2]],
    [region.max[0], region.max[1], region.min[2]],
    [region.min[0], region.min[1], region.max[2]],
    [region.max[0], region.min[1], region.max[2]],
    [region.min[0], region.max[1], region.max[2]],
    [region.max[0], region.max[1], region.max[2]],
  ] satisfies Vec3[]).map((point) => pointForHighlight(point, region, parts))

  const box = new THREE.Box3()
  corners.forEach((corner) => box.expandByPoint(corner))
  return box
}

const disposeHighlightObject = (object: THREE.Object3D) => {
  object.traverse((child) => {
    if (child instanceof THREE.Mesh || child instanceof THREE.Line) {
      child.geometry.dispose()
      const materials = Array.isArray(child.material) ? child.material : [child.material]
      materials.forEach((material) => material.dispose())
    }
  })
}

const rebuildAgentHighlightGroup = (
  group: THREE.Group,
  highlights: AgentHighlightSpec,
  parts: RenderedPart[],
) => {
  group.children.forEach(disposeHighlightObject)
  group.clear()

  highlights.points?.forEach((point, index) => {
    if (!isVec3(point.point)) return
    const marker = new THREE.Mesh(
      new THREE.SphereGeometry(point.radiusMm ?? 3, 20, 12),
      new THREE.MeshBasicMaterial({ color: point.color ?? defaultAgentHighlightColor, depthTest: false }),
    )
    marker.position.copy(pointForHighlight(point.point, point, parts))
    marker.renderOrder = 10
    marker.name = point.label ?? point.id ?? `agent-point-${index}`
    group.add(marker)
  })

  highlights.lines?.forEach((line, index) => {
    if (!isVec3(line.from) || !isVec3(line.to)) return
    const geometry = new THREE.BufferGeometry().setFromPoints([
      pointForHighlight(line.from, line, parts),
      pointForHighlight(line.to, line, parts),
    ])
    const marker = new THREE.Line(
      geometry,
      new THREE.LineBasicMaterial({
        color: line.color ?? defaultAgentHighlightColor,
        depthTest: false,
        linewidth: 4,
      }),
    )
    marker.renderOrder = 10
    marker.name = line.label ?? line.id ?? `agent-line-${index}`
    group.add(marker)
  })

  highlights.regions?.forEach((region, index) => {
    if (!isVec3(region.min) || !isVec3(region.max)) return
    const color = region.color ?? defaultAgentHighlightColor
    const box = makeRegionBox(region, parts)
    const name = region.label ?? region.id ?? `agent-region-${index}`

    // Translucent filled box shades the overlap/contact VOLUME in place, so an
    // interpenetration reads as a coloured blob localized to the actual region
    // rather than only an outline of the two whole parts. A degenerate (near
    // zero-extent) region still draws a small box so the contact stays visible.
    const size = box.getSize(new THREE.Vector3())
    const center = box.getCenter(new THREE.Vector3())
    const MIN_FILL_MM = 1
    const fill = new THREE.Mesh(
      new THREE.BoxGeometry(
        Math.max(size.x, MIN_FILL_MM),
        Math.max(size.y, MIN_FILL_MM),
        Math.max(size.z, MIN_FILL_MM),
      ),
      new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.32,
        depthWrite: false,
        depthTest: false,
      }),
    )
    fill.position.copy(center)
    fill.renderOrder = 9
    fill.name = `${name}-fill`
    group.add(fill)

    const helper = new THREE.Box3Helper(box, color)
    helper.renderOrder = 10
    helper.name = name
    group.add(helper)
  })
}

const buildAgentAnnotationPoints = (
  highlights: AgentHighlightSpec,
  parts: RenderedPart[],
) => {
  const annotations: Array<{ id: string; text: string; color: string; point: THREE.Vector3 }> = []

  highlights.parts?.forEach((partHighlight, index) => {
    const text = highlightAnnotation(partHighlight)
    if (!text) return
    const matchedParts = parts.filter((part) => partHighlightMatches(partHighlight, part.instance))
    matchedParts.forEach((part) => {
      annotations.push({
        id: `agent-part-${index}-${part.instance.id}`,
        text,
        color: highlightColor(partHighlight),
        point: partCenter(part),
      })
    })
  })

  highlights.points?.forEach((pointHighlight, index) => {
    const text = highlightAnnotation(pointHighlight)
    if (!text || !isVec3(pointHighlight.point)) return
    annotations.push({
      id: pointHighlight.id ?? `agent-point-${index}`,
      text,
      color: highlightColor(pointHighlight),
      point: pointForHighlight(pointHighlight.point, pointHighlight, parts),
    })
  })

  highlights.lines?.forEach((lineHighlight, index) => {
    const text = highlightAnnotation(lineHighlight)
    if (!text || !isVec3(lineHighlight.from) || !isVec3(lineHighlight.to)) return
    const from = pointForHighlight(lineHighlight.from, lineHighlight, parts)
    const to = pointForHighlight(lineHighlight.to, lineHighlight, parts)
    annotations.push({
      id: lineHighlight.id ?? `agent-line-${index}`,
      text,
      color: highlightColor(lineHighlight),
      point: from.add(to).multiplyScalar(0.5),
    })
  })

  highlights.regions?.forEach((regionHighlight, index) => {
    const text = highlightAnnotation(regionHighlight)
    if (!text || !isVec3(regionHighlight.min) || !isVec3(regionHighlight.max)) return
    annotations.push({
      id: regionHighlight.id ?? `agent-region-${index}`,
      text,
      color: highlightColor(regionHighlight),
      point: makeRegionBox(regionHighlight, parts).getCenter(new THREE.Vector3()),
    })
  })

  highlights.annotations?.forEach((annotation, index) => {
    const point = targetPointForAnnotation(annotation, parts)
    if (!point) return
    annotations.push({
      id: annotation.id ?? `agent-annotation-${index}`,
      text: annotation.text,
      color: highlightColor(annotation),
      point,
    })
  })

  return annotations
}

const projectAgentAnnotations = (
  highlights: AgentHighlightSpec,
  parts: RenderedPart[],
  camera: THREE.Camera,
  canvas: HTMLCanvasElement,
): ScreenAgentAnnotation[] => {
  const bounds = canvas.getBoundingClientRect()
  return buildAgentAnnotationPoints(highlights, parts)
    .map((annotation) => ({
      ...annotation,
      screen: projectPoint(annotation.point, camera, bounds),
    }))
    .filter((annotation) => annotation.screen.visible)
    .map((annotation) => ({
      id: annotation.id,
      text: annotation.text,
      color: annotation.color,
      x: annotation.screen.x,
      y: annotation.screen.y,
    }))
}

const buildWorldOverlays = (
  partSpec: DesignPart | undefined,
  partMatrix: THREE.Matrix4,
): { labels: WorldLabel[]; dimensions: WorldDimension[] } => {
  const labels: WorldLabel[] = []
  const dimensions: WorldDimension[] = []

  if (!partSpec) return { labels, dimensions }

  const featureEntries = Object.entries(partSpec.features ?? {})

  featureEntries.forEach(([featureId, feature]) => {
    const anchor = feature.render?.anchor_mm
    const offset = feature.render?.label_offset_mm
    if (isVec3(anchor)) {
      const labelPoint: Vec3 = isVec3(offset)
        ? [anchor[0] + offset[0], anchor[1] + offset[1], anchor[2] + offset[2]]
        : anchor
      labels.push({
        id: `feature-${featureId}`,
        text: feature.label ?? featureId,
        detail: feature.kind ?? feature.purpose,
        point: transformPoint(partMatrix, labelPoint),
      })
    }

    Object.entries(feature.dimensions ?? {}).forEach(([dimensionId, dimension]) => {
      if (isVec3(dimension.from_mm) && isVec3(dimension.to_mm)) {
        dimensions.push({
          id: `dimension-${featureId}-${dimensionId}`,
          text: `${dimension.label ?? dimensionId}${formatValue(dimension.value)}`,
          from: transformPoint(partMatrix, dimension.from_mm),
          to: transformPoint(partMatrix, dimension.to_mm),
        })
      }
    })
  })

  partSpec.holes?.forEach((hole) => {
    if (!isVec3(hole.position_mm)) return
    labels.push({
      id: `hole-${hole.name ?? labels.length}`,
      text: `${hole.name ?? 'hole'}${hole.diameter_mm ? ` diameter ${hole.diameter_mm}mm` : ''}`,
      detail: hole.axis ? `hole axis: ${hole.axis}` : undefined,
      point: transformPoint(partMatrix, hole.position_mm),
    })
  })

  return { labels, dimensions }
}

const buildMeshDimensionOverlays = (part: RenderedPart | undefined): WorldDimension[] => {
  if (!part) return []
  part.mesh.geometry.computeBoundingBox()
  const box = part.mesh.geometry.boundingBox
  if (!box) return []

  const min = box.min
  const max = box.max
  const size = box.getSize(new THREE.Vector3())
  const matrix = part.baseMatrix

  return [
    {
      id: 'mesh-bounds-x',
      text: `mesh X ${formatLength(size.x)}`,
      from: new THREE.Vector3(min.x, min.y, min.z).applyMatrix4(matrix),
      to: new THREE.Vector3(max.x, min.y, min.z).applyMatrix4(matrix),
    },
    {
      id: 'mesh-bounds-y',
      text: `mesh Y ${formatLength(size.y)}`,
      from: new THREE.Vector3(min.x, min.y, min.z).applyMatrix4(matrix),
      to: new THREE.Vector3(min.x, max.y, min.z).applyMatrix4(matrix),
    },
    {
      id: 'mesh-bounds-z',
      text: `mesh Z ${formatLength(size.z)}`,
      from: new THREE.Vector3(min.x, min.y, min.z).applyMatrix4(matrix),
      to: new THREE.Vector3(min.x, min.y, max.z).applyMatrix4(matrix),
    },
  ]
}

const projectPoint = (point: THREE.Vector3, camera: THREE.Camera, bounds: DOMRect) => {
  const projected = point.clone().project(camera)
  return {
    x: (projected.x * 0.5 + 0.5) * bounds.width,
    y: (-projected.y * 0.5 + 0.5) * bounds.height,
    visible: projected.z >= -1 && projected.z <= 1,
  }
}

const projectWorldOverlays = (
  overlays: { labels: WorldLabel[]; dimensions: WorldDimension[] },
  camera: THREE.Camera,
  canvas: HTMLCanvasElement,
): ScreenOverlays => {
  const bounds = canvas.getBoundingClientRect()
  return {
    labels: overlays.labels
      .map((label) => ({ ...label, screen: projectPoint(label.point, camera, bounds) }))
      .filter((label) => label.screen.visible)
      .map((label, index) => ({
        id: label.id,
        text: label.text,
        detail: label.detail,
        marker: index + 1,
        x: label.screen.x,
        y: label.screen.y,
      })),
    dimensions: overlays.dimensions
      .map((dimension) => ({
        ...dimension,
        start: projectPoint(dimension.from, camera, bounds),
        end: projectPoint(dimension.to, camera, bounds),
      }))
      .filter((dimension) => dimension.start.visible || dimension.end.visible)
      .map((dimension) => ({
        id: dimension.id,
        text: dimension.text,
        x1: dimension.start.x,
        y1: dimension.start.y,
        x2: dimension.end.x,
        y2: dimension.end.y,
      })),
  }
}

const projectMeasurement = (
  measurement: WorldMeasurement | null,
  camera: THREE.Camera,
  canvas: HTMLCanvasElement,
): ScreenMeasurement | null => {
  if (!measurement) return null

  const bounds = canvas.getBoundingClientRect()
  const start = projectPoint(measurement.from, camera, bounds)
  const end = projectPoint(measurement.to, camera, bounds)
  if (!start.visible && !end.visible) return null

  return {
    label: `${formatLength(measurement.length)} · ${measurement.partName}`,
    x1: start.x,
    y1: start.y,
    x2: end.x,
    y2: end.y,
    x: (start.x + end.x) / 2,
    y: (start.y + end.y) / 2 - 10,
  }
}

const projectRulerAnchor = (
  anchor: RulerAnchor | null,
  camera: THREE.Camera,
  canvas: HTMLCanvasElement,
): ScreenPickMarker | null => {
  if (!anchor) return null
  const screen = projectPoint(anchor.point, camera, canvas.getBoundingClientRect())
  return screen.visible ? { x: screen.x, y: screen.y } : null
}

const projectPick = (
  pick: WorldPick | null,
  camera: THREE.Camera,
  canvas: HTMLCanvasElement,
): ScreenPick | null => {
  if (!pick) return null

  const bounds = canvas.getBoundingClientRect()
  const screen = projectPoint(pick.point, camera, bounds)
  if (!screen.visible) return null

  const x = formatCoordinate(pick.localPoint.x)
  const y = formatCoordinate(pick.localPoint.y)
  const z = formatCoordinate(pick.localPoint.z)
  return {
    label: `${pick.partName}`,
    detail: `local XYZ: ${x}, ${y}, ${z} mm`,
    x: screen.x,
    y: screen.y,
  }
}

const projectPickMarker = (
  pick: WorldPick | null,
  camera: THREE.Camera,
  canvas: HTMLCanvasElement,
): ScreenPickMarker | null => {
  if (!pick) return null
  const bounds = canvas.getBoundingClientRect()
  const screen = projectPoint(pick.point, camera, bounds)
  return screen.visible ? { x: screen.x, y: screen.y } : null
}

// Resolve a relative mesh URL against the scene's optional assetsBaseUrl. Absolute
// http(s) and `/`-rooted URLs pass through untouched (mirrors normalizeSceneAssets),
// so a relative-URL scene resolves its STLs under static hosting / versioned dirs.
const resolveMeshUrl = (url: string, base?: string) =>
  !base || /^[a-z][a-z0-9+.-]*:/i.test(url) || url.startsWith('/')
    ? url
    : `${base.replace(/\/+$/, '')}/${url.replace(/^\.\//, '')}`

const makeGeometry = async (mesh: BuildMesh, assetsBaseUrl?: string) => {
  if (mesh.url) {
    const geometry = await new STLLoader().loadAsync(resolveMeshUrl(mesh.url, assetsBaseUrl))
    geometry.computeVertexNormals()
    return geometry
  }

  if (mesh.primitive?.kind === 'box') {
    return new THREE.BoxGeometry(...mesh.primitive.size)
  }

  if (mesh.primitive?.kind === 'cylinder') {
    return new THREE.CylinderGeometry(
      mesh.primitive.radius,
      mesh.primitive.radius,
      mesh.primitive.depth,
      mesh.primitive.radialSegments ?? 20,
    )
  }

  throw new Error(`Mesh "${mesh.id}" needs either a url or a primitive fallback.`)
}

const buildRootFromManifest = (manifest: BuildSceneManifest) => {
  const meshUrl = manifest.meshes.find((mesh) => mesh.url)?.url
  return meshUrl?.replace(/\/(?:stl_prototype|fasteners)\/.*$/, '') ?? null
}

const collectIndentedBlock = (lines: string[], startIndex: number, indent: number) => {
  const out: string[] = []
  for (let index = startIndex; index < lines.length; index += 1) {
    const line = lines[index]
    const lineIndent = line.match(/^ */u)?.[0].length ?? 0
    const isBlankOrComment = /^\s*(#.*)?$/.test(line)

    if (index > startIndex && !isBlankOrComment && lineIndent <= indent) break
    out.push(line)
  }

  return out.join('\n')
}

const findTopLevelSection = (lines: string[], sectionName: string) =>
  lines.findIndex((line) => line === `${sectionName}:`)

const findNestedYamlBlock = (source: string, sectionName: string, key: string) => {
  const lines = source.split('\n')
  const sectionIndex = findTopLevelSection(lines, sectionName)
  if (sectionIndex < 0) return null

  for (let index = sectionIndex + 1; index < lines.length; index += 1) {
    const line = lines[index]
    if (/^\S/.test(line) && !line.startsWith('#')) break

    const match = line.match(/^ {2}([A-Za-z0-9_]+):/)
    if (match?.[1] === key) {
      return `${sectionName}:\n${collectIndentedBlock(lines, index, 2)}`
    }
  }

  return null
}

const designSpecExcerpt = (source: string | null, partType: string) => {
  if (!source) return null

  const blocks = [
    findNestedYamlBlock(source, 'coordinate_systems', partType),
    findNestedYamlBlock(source, 'print_orientations', partType),
    findNestedYamlBlock(source, 'parts', partType),
  ].filter(Boolean)

  return blocks.length > 0 ? blocks.join('\n\n') : null
}

const initialSelectionFromUrl = (manifest: BuildSceneManifest) => {
  const params = new URLSearchParams(window.location.search)
  const requestedPart = params.get('part') ?? params.get('partType') ?? params.get('instance')
  if (!requestedPart) return { selectedId: null, isolatedId: null }

  const selectedId =
    manifest.instances.find(
      (instance) => instance.id === requestedPart || instance.partType === requestedPart,
    )?.id ?? null
  // ?part=…&isolate=1 is the single-part deep link: everything else hidden and
  // the camera framed on the part alone (anything but 0/false counts as on).
  const isolate = params.get('isolate')
  const isolated = Boolean(
    selectedId && isolate !== null && isolate !== '0' && isolate !== 'false',
  )
  return { selectedId, isolatedId: isolated ? selectedId : null }
}

const diffStatusColors: Record<DiffStatus, string> = {
  added: '#22c55e',
  removed: '#ef4444',
  moved: '#f59e0b',
  changed: '#f59e0b',
}

const applyPartState = (
  part: RenderedPart,
  visiblePartTypes: Set<string>,
  selectedId: string | null,
  hoveredId: string | null,
  focusGroup: string | null,
  isolatedId: string | null,
  highlights: AgentHighlightSpec,
  diffStatuses: Record<string, DiffStatus> | null,
  poseMatrices: Map<string, THREE.Matrix4> | null,
  partTypeColors: Record<string, string>,
  visibleInstanceIds?: Set<string>,
) => {
  // Phase 3: a posed instance gets its forward-kinematics world matrix (already
  // C(joint)·base); everything else stays at its static base transform.
  const posed = poseMatrices?.get(part.instance.id)
  part.mesh.matrix.copy(posed ?? part.baseMatrix)
  part.mesh.updateMatrixWorld(true)
  const matchedHighlight = matchingPartHighlight(highlights, part.instance)
  const diffStatus = diffStatuses?.[part.instance.id]

  const partIsVisible =
    visiblePartTypes.size === 0 || visiblePartTypes.has(part.instance.partType)
  const focusMatches = !focusGroup || part.instance.focusGroup === focusGroup
  const isolationMatches = !isolatedId || part.instance.id === isolatedId
  const catalogMatches = !visibleInstanceIds || visibleInstanceIds.has(part.instance.id)
  part.mesh.visible = catalogMatches && (Boolean(matchedHighlight) || (partIsVisible && focusMatches && isolationMatches))

  const selectedMatches = !selectedId || selectedId === part.instance.id
  const shouldDim = Boolean(!isolatedId && selectedId && !selectedMatches) ||
    Boolean(highlights.ghostOthers && highlights.parts?.length && !matchedHighlight)
  // Color precedence: diff status (compare mode) > highlight (keep the part's
  // base color so the orange emissive reads clearly) > user color override >
  // the instance's default color. In diff mode unchanged parts are muted so
  // added/removed/changed colors stand out.
  const overrideColor = partTypeColors[part.instance.partType]
  const normalColor = overrideColor ?? part.instance.color
  part.material.color.set(
    diffStatus
      ? diffStatusColors[diffStatus]
      : diffStatuses
        ? '#64748b'
        : matchedHighlight
          ? part.instance.color
          : normalColor,
  )
  part.material.opacity =
    shouldDim && !matchedHighlight ? 0.16 : diffStatus === 'removed' ? 0.35 : 1
  part.material.depthWrite = part.material.opacity === 1
  part.material.emissive.set(
    matchedHighlight
      ? highlightColor(matchedHighlight)
      : hoveredId === part.instance.id
        ? '#334155'
        : '#000000',
  )
  part.material.needsUpdate = true
}

// --- Wires layer (plans/wiring.md) -----------------------------------------
// Renders the scene's routes[] as Catmull-Rom tubes through the SAME sampled
// curve the wiring checks measure (core/buildWiring), plus small spheres at
// anchored (physically secured) waypoints. Instance-anchored waypoints follow
// the pose scrubber via the forward-kinematics overrides.

const disposeWiresGroup = (group: THREE.Group) => {
  const seen = new Set<THREE.BufferGeometry | THREE.Material>()
  group.children.forEach((child) => {
    const mesh = child as THREE.Mesh
    if (mesh.geometry && !seen.has(mesh.geometry)) {
      seen.add(mesh.geometry)
      mesh.geometry.dispose()
    }
    const material = mesh.material as THREE.Material | undefined
    if (material && !seen.has(material)) {
      seen.add(material)
      material.dispose()
    }
  })
  group.clear()
}

const rebuildWiresGroup = (
  group: THREE.Group,
  manifest: BuildSceneManifest,
  show: boolean,
  poseMatrices: Map<string, THREE.Matrix4> | null,
) => {
  disposeWiresGroup(group)
  if (!show) return
  const routes = manifest.routes ?? []
  if (routes.length === 0) return
  const overrides = poseMatrices
    ? Object.fromEntries([...poseMatrices].map(([id, matrix]) => [id, matrix.toArray()]))
    : undefined

  for (const route of routes) {
    const resolved = resolveRoute(manifest, route, overrides)
    if (resolved.points.length < 2) continue
    const sampled = sampleRoute(resolved.points)
    const curvePoints = sampled.samples.map((p) => new THREE.Vector3(p[0], p[1], p[2]))
    const curve = new THREE.CatmullRomCurve3(curvePoints, false, 'catmullrom', 0)
    const radius = Math.max((route.diameterMm ?? 1.5) / 2, 0.4)
    const material = new THREE.MeshStandardMaterial({
      color: new THREE.Color(routeDisplayColor(route)),
      roughness: 0.55,
      metalness: 0.05,
    })
    const tube = new THREE.Mesh(
      new THREE.TubeGeometry(curve, Math.max(curvePoints.length * 2, 32), radius, 10, false),
      material,
    )
    tube.name = `buildviz-wire-${route.id}`
    group.add(tube)

    const anchorGeometry = new THREE.SphereGeometry(Math.max(radius * 1.8, 1.1), 12, 12)
    resolved.points.forEach((point, index) => {
      if (!resolved.anchors[index]) return
      const marker = new THREE.Mesh(anchorGeometry, material)
      marker.position.set(point[0], point[1], point[2])
      group.add(marker)
    })
  }
}

export function BuildViewer({
  manifest,
  designSpecUrl: passedDesignSpecUrl,
  visiblePartTypes,
  visibleInstanceIds,
  focusGroup,
  rulerMode,
  pickerMode,
  diffStatuses = null,
  partTypeColors = {},
  jointValues = null,
  onSpecWarnings,
  showWires = true,
  onRequestDrawing,
  onSelectedPartType,
}: BuildViewerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const partsRef = useRef<RenderedPart[]>([])
  const worldOverlaysRef = useRef<{ labels: WorldLabel[]; dimensions: WorldDimension[] }>({
    labels: [],
    dimensions: [],
  })
  const worldMeasurementRef = useRef<WorldMeasurement | null>(null)
  const worldPickRef = useRef<WorldPick | null>(null)
  const rulerModeRef = useRef(false)
  const pickerModeRef = useRef(false)
  const initialAgentHighlights = useMemo(() => parseInitialHighlightsFromUrl(), [])
  const agentHighlightsRef = useRef<AgentHighlightSpec>(initialAgentHighlights)
  const agentHighlightGroupRef = useRef<THREE.Group | null>(null)
  const wiresGroupRef = useRef<THREE.Group | null>(null)
  const showWiresRef = useRef(showWires)
  // Forward-kinematics overrides for the current pose. Empty when the scene has
  // no joints or every joint is at home, so the static path is unchanged.
  const poseMatrices = useMemo(
    () =>
      jointValues && manifest.joints && manifest.joints.length > 0
        ? poseInstanceMatrices(manifest, jointValues)
        : null,
    [manifest, jointValues],
  )
  const poseMatricesRef = useRef<Map<string, THREE.Matrix4> | null>(poseMatrices)
  const latestStateRef = useRef({ visiblePartTypes, visibleInstanceIds, focusGroup, diffStatuses, partTypeColors })
  const initialSelection = useMemo(() => initialSelectionFromUrl(manifest), [manifest])
  const latestSelectionRef = useRef({
    selectedId: initialSelection.selectedId,
    hoveredId: null as string | null,
    isolatedId: initialSelection.isolatedId,
  })
  const [selectedId, setSelectedId] = useState<string | null>(() => initialSelection.selectedId)
  const [isolatedId, setIsolatedId] = useState<string | null>(() => initialSelection.isolatedId)
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  // Right-click context menu over a part (screen-fixed coords). Null = closed.
  const [contextMenu, setContextMenu] = useState<{
    x: number
    y: number
    instanceId: string
    partType: string
    name: string
  } | null>(null)
  const [downloadBusy, setDownloadBusy] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [sceneReady, setSceneReady] = useState(false)
  // On compact (phone-sized) layouts the YAML panel would cover most of the
  // viewer, so it starts minimized there; a tap on the header expands it.
  const [yamlCollapsed, setYamlCollapsed] = useState(() => isCompactLayout())
  // Touch-first device: hints talk about tap/long-press instead of click/hover.
  const coarsePointer = useMemo(() => isCoarsePointer(), [])
  const [agentHighlights, setAgentHighlights] = useState<AgentHighlightSpec>(() => initialAgentHighlights)
  const [screenOverlays, setScreenOverlays] = useState<ScreenOverlays>(emptyScreenOverlays)
  const [screenAgentAnnotations, setScreenAgentAnnotations] = useState<ScreenAgentAnnotation[]>([])
  const [screenMeasurement, setScreenMeasurement] = useState<ScreenMeasurement | null>(null)
  // Pinned ruler point: ref feeds the render loop / event handlers, state drives
  // the hint copy. Both always change together (see applyRulerAnchor).
  const rulerAnchorRef = useRef<RulerAnchor | null>(null)
  const [rulerAnchor, setRulerAnchorState] = useState<RulerAnchor | null>(null)
  const [screenRulerAnchor, setScreenRulerAnchor] = useState<ScreenPickMarker | null>(null)
  // Unpin when the ruler is toggled off (adjust-during-render; the ref mirror
  // is cleared by the rulerMode effect below).
  const [prevRulerMode, setPrevRulerMode] = useState(rulerMode)
  if (prevRulerMode !== rulerMode) {
    setPrevRulerMode(rulerMode)
    if (!rulerMode && rulerAnchor) setRulerAnchorState(null)
  }
  const [screenPick, setScreenPick] = useState<ScreenPick | null>(null)
  const [screenPickMarker, setScreenPickMarker] = useState<ScreenPickMarker | null>(null)
  // Annotated review link composer (item: share a highlighted + questioned view).
  const [reviewOpen, setReviewOpen] = useState(false)
  const [reviewQuestion, setReviewQuestion] = useState('')
  const [reviewCopied, setReviewCopied] = useState(false)
  const [partLinkCopied, setPartLinkCopied] = useState(false)
  const [designSpec, setDesignSpec] = useState<{
    url: string | null
    text: string | null
    error: string | null
  }>({ url: null, text: null, error: null })
  const designSpecUrl = useMemo(() => {
    if (passedDesignSpecUrl) return passedDesignSpecUrl
    if (manifest.designSpecUrl) return manifest.designSpecUrl

    const buildRoot = buildRootFromManifest(manifest)
    return buildRoot ? `${buildRoot}/design_spec.yaml` : null
  }, [manifest, passedDesignSpecUrl])

  const hoveredPart = useMemo(
    () => manifest.instances.find((instance) => instance.id === hoveredId),
    [hoveredId, manifest.instances],
  )
  const selectedPart = useMemo(
    () => manifest.instances.find((instance) => instance.id === selectedId),
    [selectedId, manifest.instances],
  )
  // Mirror the selection's part type up to the shell (Part Types list).
  const selectedPartType = selectedPart?.partType ?? null
  useEffect(() => {
    onSelectedPartType?.(selectedPartType)
  }, [onSelectedPartType, selectedPartType])
  const parsedDesignSpec = useMemo(
    () => (designSpec.url === designSpecUrl ? parseDesignSpec(designSpec.text) : null),
    [designSpec, designSpecUrl],
  )
  // Design-spec health for the badge next to the version dropdown: the same
  // coverage rule the hub warns on at push/register time (specCoverage in
  // core). null while the spec fetch for the current build is still in flight,
  // so a slow response never flashes a spurious "missing spec" badge.
  const specWarnings = useMemo<string[] | null>(() => {
    if (designSpecUrl && designSpec.url !== designSpecUrl) return null
    const text = designSpecUrl && !designSpec.error ? designSpec.text : null
    const coverage = specCoverage(manifest, text)
    if (!coverage.hasSpec) {
      return ['No design_spec.yaml — the parts\u2019 purpose and design intent are unrecorded.']
    }
    if (!coverage.parses) return ['design_spec.yaml did not parse as a YAML mapping.']
    if (!coverage.hasParts) return ['design_spec.yaml has no parts: section.']
    const warnings: string[] = []
    if (coverage.uncovered.length > 0) {
      warnings.push(
        `${coverage.uncovered.length} scene part type(s) have no design_spec entry: ${coverage.uncovered.slice(0, 10).join(', ')}.`,
      )
    }
    if (coverage.stale.length > 0) {
      warnings.push(
        `${coverage.stale.length} design_spec entrie(s) match no scene part: ${coverage.stale.slice(0, 10).join(', ')}.`,
      )
    }
    if (coverage.uncoveredWires.length > 0) {
      warnings.push(
        `${coverage.uncoveredWires.length} wire(s) have no design_spec wiring: entry: ${coverage.uncoveredWires.slice(0, 10).join(', ')}.`,
      )
    }
    if (coverage.staleWires.length > 0) {
      warnings.push(
        `${coverage.staleWires.length} wiring: entrie(s) match no scene route: ${coverage.staleWires.slice(0, 10).join(', ')}.`,
      )
    }
    return warnings
  }, [designSpec, designSpecUrl, manifest])
  useEffect(() => {
    if (specWarnings) onSpecWarnings?.(specWarnings)
  }, [specWarnings, onSpecWarnings])
  const selectedPartSpec = selectedPart ? parsedDesignSpec?.parts?.[selectedPart.partType] : undefined
  const selectedYaml = useMemo(() => {
    if (!selectedPart) return null
    return designSpecExcerpt(designSpec.url === designSpecUrl ? designSpec.text : null, selectedPart.partType)
  }, [designSpec, designSpecUrl, selectedPart])
  useEffect(() => {
    if (!selectedPart) {
      worldOverlaysRef.current = { labels: [], dimensions: [] }
      return
    }

    const overlays = buildWorldOverlays(
      selectedPartSpec,
      new THREE.Matrix4().fromArray(selectedPart.transform),
    )
    const selectedRenderedPart = partsRef.current.find((part) => part.instance.id === selectedPart.id)
    worldOverlaysRef.current = {
      labels: overlays.labels,
      dimensions: [...overlays.dimensions, ...buildMeshDimensionOverlays(selectedRenderedPart)],
    }
  }, [selectedPart, selectedPartSpec])

  useEffect(() => {
    if (!designSpecUrl) return

    let cancelled = false

    fetch(designSpecUrl)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`${response.status} ${response.statusText}`)
        }
        return response.text()
      })
      .then((text) => {
        if (!cancelled) setDesignSpec({ url: designSpecUrl, text, error: null })
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setDesignSpec({
            url: designSpecUrl,
            text: null,
            error: error instanceof Error ? error.message : String(error),
          })
        }
      })

    return () => {
      cancelled = true
    }
  }, [designSpecUrl])

  useEffect(() => {
    latestStateRef.current = { visiblePartTypes, visibleInstanceIds, focusGroup, diffStatuses, partTypeColors }
  }, [diffStatuses, focusGroup, visiblePartTypes, visibleInstanceIds, partTypeColors])

  useEffect(() => {
    latestSelectionRef.current = { selectedId, hoveredId, isolatedId }
  }, [hoveredId, isolatedId, selectedId])

  useEffect(() => {
    rulerModeRef.current = rulerMode
    if (!rulerMode) {
      worldMeasurementRef.current = null
      rulerAnchorRef.current = null
    }
  }, [rulerMode])

  useEffect(() => {
    pickerModeRef.current = pickerMode
    if (!pickerMode) {
      worldPickRef.current = null
    }
  }, [pickerMode])

  useEffect(() => {
    agentHighlightsRef.current = agentHighlights
    if (agentHighlightGroupRef.current) {
      rebuildAgentHighlightGroup(agentHighlightGroupRef.current, agentHighlights, partsRef.current)
    }
  }, [agentHighlights])

  // Rebuild the wires layer when the toggle flips or the pose changes (the
  // scene-init effect draws the initial state; anchored waypoints track the
  // posed instances through the same overrides the parts use). Wires are
  // hidden while a part is ISOLATED — a single-part view (double-click or a
  // ?part=…&isolate=1 deep link) shouldn't drown the part in the full
  // harness; the toggle takes back over when isolation ends.
  const wiresVisible = showWires && !isolatedId
  useEffect(() => {
    showWiresRef.current = wiresVisible
    if (wiresGroupRef.current) {
      rebuildWiresGroup(wiresGroupRef.current, manifest, wiresVisible, poseMatrices)
    }
  }, [manifest, poseMatrices, wiresVisible])

  useEffect(() => {
    window.buildviz = {
      setHighlights: (highlights) => setAgentHighlights(highlights),
      clearHighlights: () => setAgentHighlights({}),
    }

    const onSetHighlights = (event: Event) => {
      const detail = event instanceof CustomEvent ? event.detail : null
      if (detail && typeof detail === 'object') {
        setAgentHighlights(detail as AgentHighlightSpec)
      }
    }

    window.addEventListener('buildviz:set-highlights', onSetHighlights)
    return () => {
      window.removeEventListener('buildviz:set-highlights', onSetHighlights)
      if (window.buildviz?.setHighlights) {
        delete window.buildviz
      }
    }
  }, [])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target
      const isTyping =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement ||
        (target instanceof HTMLElement && target.isContentEditable)

      if (isTyping) return

      const key = event.key.toLowerCase()
      if (key === 'm' || key === 'y') {
        event.preventDefault()
        setYamlCollapsed((current) => !current)
      } else if (key === 'escape') {
        setYamlCollapsed(true)
        setContextMenu(null)
        setReviewOpen(false)
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    setSceneReady(false)
    setLoadError(null)
    let disposed = false
    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#0f172a')

    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 4000)
    camera.up.set(0, 0, 1)
    camera.position.set(150, -180, 115)
    cameraRef.current = camera

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    rendererRef.current = renderer
    container.appendChild(renderer.domElement)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.target.set(...manifest.center)

    scene.add(new THREE.HemisphereLight('#f8fafc', '#1e293b', 2.6))
    const keyLight = new THREE.DirectionalLight('#ffffff', 2.4)
    keyLight.position.set(100, -130, 220)
    scene.add(keyLight)

    const grid = new THREE.GridHelper(220, 22, '#334155', '#1e293b')
    grid.rotation.x = Math.PI / 2
    scene.add(grid)

    const agentHighlightGroup = new THREE.Group()
    agentHighlightGroup.name = 'buildviz-agent-highlights'
    agentHighlightGroupRef.current = agentHighlightGroup
    scene.add(agentHighlightGroup)

    const wiresGroup = new THREE.Group()
    wiresGroup.name = 'buildviz-wires'
    wiresGroupRef.current = wiresGroup
    scene.add(wiresGroup)
    rebuildWiresGroup(wiresGroup, manifest, showWiresRef.current, poseMatricesRef.current)

    const raycaster = new THREE.Raycaster()
    const pointer = new THREE.Vector2()
    type ScreenPointLike = { clientX: number; clientY: number }
    const pickHitAmong = (event: ScreenPointLike, meshes: THREE.Mesh[]) => {
      const bounds = renderer.domElement.getBoundingClientRect()
      pointer.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1
      pointer.y = -(((event.clientY - bounds.top) / bounds.height) * 2 - 1)
      raycaster.setFromCamera(pointer, camera)

      const hits = raycaster.intersectObjects(meshes, false)
      return hits[0] ?? null
    }
    const pickHit = (event: ScreenPointLike) =>
      pickHitAmong(
        event,
        partsRef.current.filter((part) => part.mesh.visible).map((part) => part.mesh),
      )

    // The ruler's ray targets: when a part is selected (click) or highlight
    // targets are active (Part Types highlight, checks panel, agent specs),
    // measure only those parts — the ray passes through everything else, so
    // occluding geometry can't steal the measurement. Null = no restriction.
    const rulerCandidates = (): THREE.Mesh[] | null => {
      const { selectedId } = latestSelectionRef.current
      if (selectedId) {
        const part = partsRef.current.find((entry) => entry.instance.id === selectedId)
        if (part?.mesh.visible) return [part.mesh]
      }
      const spec = agentHighlightsRef.current
      if (spec.parts && spec.parts.length > 0) {
        const meshes = partsRef.current
          .filter((part) => part.mesh.visible && matchingPartHighlight(spec, part.instance))
          .map((part) => part.mesh)
        if (meshes.length > 0) return meshes
      }
      return null
    }
    const rulerPickHit = (event: ScreenPointLike) => {
      const candidates = rulerCandidates()
      return candidates ? pickHitAmong(event, candidates) : pickHit(event)
    }

    const applyRulerAnchor = (anchor: RulerAnchor | null) => {
      rulerAnchorRef.current = anchor
      setRulerAnchorState(anchor)
      // Drop any stale edge measurement so the overlay doesn't show the old
      // line until the next hover/tap recomputes from the new anchor.
      worldMeasurementRef.current = null
    }

    const pickPart = (event: ScreenPointLike) => {
      const hit = pickHit(event)
      const hitId = hit?.object.userData.instanceId as string | undefined
      return hitId ?? null
    }

    // --- Touch interaction state -----------------------------------------
    // Touch has no hover, no right-click, and (on iOS Safari) no dblclick, so
    // the mouse gestures get touch equivalents: long-press opens the part
    // context menu, a manual double-tap detector drives isolation, and a tap
    // measures/picks in the tool modes. After a long-press or double-tap the
    // browser still synthesizes a click, which is swallowed so it doesn't
    // immediately clear the menu / toggle the selection.
    let longPressTimer: number | null = null
    let touchPress: { x: number; y: number } | null = null
    let lastTouchTap: { time: number; x: number; y: number } | null = null
    let suppressClicksUntil = 0
    let lastTouchIsolateAt = 0
    let lastTouchUpAt = 0

    const clearLongPress = () => {
      if (longPressTimer !== null) {
        window.clearTimeout(longPressTimer)
        longPressTimer = null
      }
    }

    const openContextMenuAt = (clientX: number, clientY: number) => {
      setDownloadError(null)
      const hit = pickHit({ clientX, clientY })
      const part = hit ? partsRef.current.find((entry) => entry.mesh === hit.object) : null
      if (!part) return
      setSelectedId(part.instance.id)
      setContextMenu({
        x: clientX,
        y: clientY,
        instanceId: part.instance.id,
        partType: part.instance.partType,
        name: part.instance.name || part.instance.partType,
      })
    }

    const isolatePartAt = (event: ScreenPointLike) => {
      if (rulerModeRef.current || pickerModeRef.current) return
      const hitId = pickPart(event)
      if (!hitId) return

      if (latestSelectionRef.current.isolatedId === hitId) {
        setSelectedId(null)
        setIsolatedId(null)
        return
      }

      setSelectedId(hitId)
      setIsolatedId(hitId)
    }

    const onPointerMove = (event: PointerEvent) => {
      if (event.pointerType === 'touch') {
        // A moving finger is an orbit/pan gesture, not a hover: cancel any
        // pending long-press and leave the hover state alone.
        if (
          touchPress &&
          Math.hypot(event.clientX - touchPress.x, event.clientY - touchPress.y) > 8
        ) {
          clearLongPress()
        }
        return
      }
      const hit = pickHit(event)
      const hitId = hit?.object.userData.instanceId as string | undefined
      setHoveredId(hitId ?? null)
      if (rulerModeRef.current) {
        const rulerHit = rulerPickHit(event)
        const anchor = rulerAnchorRef.current
        worldMeasurementRef.current = rulerHit
          ? anchor
            ? measurementFromAnchor(anchor, rulerHit)
            : measurementFromHit(rulerHit)
          : null
      } else {
        worldMeasurementRef.current = null
      }
      worldPickRef.current = pickerModeRef.current && hit ? pickFromHit(hit) : null
    }

    const onClick = (event: MouseEvent) => {
      if (Date.now() < suppressClicksUntil) return
      setContextMenu(null)
      if (rulerModeRef.current) {
        // Touch taps measure / pin in the pointerup handler; the click the
        // browser synthesizes afterwards must not re-pin over their result.
        if (Date.now() - lastTouchUpAt < 700) return
        // Click pins (or moves) the measuring start point; clicking empty
        // space unpins it and returns to plain edge measuring.
        const hit = rulerPickHit(event)
        applyRulerAnchor(hit ? anchorFromHit(hit) : null)
        return
      }
      if (pickerModeRef.current) return
      const hitId = pickPart(event)
      if (!hitId) {
        setSelectedId(null)
        setIsolatedId(null)
        return
      }
      if (latestSelectionRef.current.isolatedId === hitId) {
        setSelectedId(hitId)
        return
      }
      setSelectedId((current) => (current === hitId ? null : hitId))
    }

    const onDoubleClick = (event: MouseEvent) => {
      // The manual touch double-tap may already have handled this gesture on
      // browsers that DO fire dblclick for taps (it would undo the isolation).
      if (Date.now() - lastTouchIsolateAt < 700) return
      isolatePartAt(event)
    }

    // Right-click on a part opens a context menu (quiet click only: a
    // right-DRAG is an orbit-controls pan and must not pop the menu). The
    // native browser menu is suppressed on the canvas either way.
    let rightPress: { x: number; y: number } | null = null
    const onPointerDown = (event: PointerEvent) => {
      setContextMenu(null)
      if (event.button === 2) rightPress = { x: event.clientX, y: event.clientY }
      if (event.pointerType === 'touch' && event.isPrimary) {
        const { clientX, clientY } = event
        touchPress = { x: clientX, y: clientY }
        clearLongPress()
        longPressTimer = window.setTimeout(() => {
          longPressTimer = null
          suppressClicksUntil = Date.now() + 800
          openContextMenuAt(clientX, clientY)
        }, 500)
      }
    }
    const onPointerUp = (event: PointerEvent) => {
      if (event.pointerType === 'touch') {
        lastTouchUpAt = Date.now()
        clearLongPress()
        const wasTap =
          touchPress &&
          Math.hypot(event.clientX - touchPress.x, event.clientY - touchPress.y) <= 12
        touchPress = null
        if (wasTap && Date.now() >= suppressClicksUntil) {
          // Tool modes: a tap measures / picks, standing in for hover.
          if (rulerModeRef.current) {
            const hit = rulerPickHit(event)
            const anchor = rulerAnchorRef.current
            if (hit) {
              worldMeasurementRef.current = anchor
                ? measurementFromAnchor(anchor, hit)
                : measurementFromHit(hit)
            } else {
              // Tap on empty space: clear the measurement and unpin.
              worldMeasurementRef.current = null
              if (anchor) applyRulerAnchor(null)
            }
          } else if (pickerModeRef.current) {
            const hit = pickHit(event)
            worldPickRef.current = hit ? pickFromHit(hit) : null
          }
          const now = Date.now()
          if (
            lastTouchTap &&
            now - lastTouchTap.time < 450 &&
            Math.hypot(event.clientX - lastTouchTap.x, event.clientY - lastTouchTap.y) < 30
          ) {
            lastTouchTap = null
            lastTouchIsolateAt = now
            suppressClicksUntil = now + 500
            if (rulerModeRef.current) {
              // Touch stand-in for the desktop pin click: double-tap pins the
              // measuring start point at the tapped spot.
              const hit = rulerPickHit(event)
              if (hit) applyRulerAnchor(anchorFromHit(hit))
            } else {
              isolatePartAt(event)
            }
          } else {
            lastTouchTap = { time: now, x: event.clientX, y: event.clientY }
          }
        }
      }
      if (event.button !== 2 || !rightPress) return
      const moved = Math.hypot(event.clientX - rightPress.x, event.clientY - rightPress.y)
      rightPress = null
      if (moved > 5) return
      openContextMenuAt(event.clientX, event.clientY)
    }
    const onPointerCancel = () => {
      clearLongPress()
      touchPress = null
    }
    const onContextMenu = (event: MouseEvent) => event.preventDefault()

    renderer.domElement.addEventListener('pointermove', onPointerMove)
    renderer.domElement.addEventListener('click', onClick)
    renderer.domElement.addEventListener('dblclick', onDoubleClick)
    renderer.domElement.addEventListener('pointerdown', onPointerDown)
    renderer.domElement.addEventListener('pointerup', onPointerUp)
    renderer.domElement.addEventListener('pointercancel', onPointerCancel)
    renderer.domElement.addEventListener('contextmenu', onContextMenu)

    const resize = () => {
      // Track the container's real size. The desktop minimum height lives in
      // CSS (.viewer-canvas min-height); clamping here to 660px used to render
      // a cropped, mis-centered scene on phone-sized screens.
      const bounds = container.getBoundingClientRect()
      const width = Math.max(bounds.width, 1)
      const height = Math.max(bounds.height, 1)
      renderer.setSize(width, height)
      camera.aspect = width / height
      camera.updateProjectionMatrix()
    }

    const resizeObserver = new ResizeObserver(resize)
    resizeObserver.observe(container)
    resize()

    // World radius of the loaded build (set by loadScene), used to keep the
    // clip planes matched to the zoom level every frame. A far plane sized
    // once at load time used to clip large parts out of existence as soon as
    // the user zoomed out past it.
    let clipRadius = 1

    const render = () => {
      if (disposed) return
      controls.update()
      const viewDistance = camera.position.distanceTo(controls.target)
      const far = Math.max((viewDistance + clipRadius * 2) * 1.5, 500)
      const near = THREE.MathUtils.clamp(viewDistance / 1000, 0.1, Math.max(clipRadius / 100, 0.1))
      if (Math.abs(far - camera.far) > camera.far * 0.01 || Math.abs(near - camera.near) > camera.near * 0.05) {
        camera.far = far
        camera.near = near
        camera.updateProjectionMatrix()
      }
      renderer.render(scene, camera)
      const projectedOverlays = projectWorldOverlays(
        worldOverlaysRef.current,
        camera,
        renderer.domElement,
      )
      setScreenOverlays(projectedOverlays)
      setScreenMeasurement(projectMeasurement(worldMeasurementRef.current, camera, renderer.domElement))
      setScreenRulerAnchor(projectRulerAnchor(rulerAnchorRef.current, camera, renderer.domElement))
      setScreenPick(projectPick(worldPickRef.current, camera, renderer.domElement))
      setScreenPickMarker(projectPickMarker(worldPickRef.current, camera, renderer.domElement))
      setScreenAgentAnnotations(
        projectAgentAnnotations(agentHighlightsRef.current, partsRef.current, camera, renderer.domElement),
      )
      requestAnimationFrame(render)
    }

    const loadScene = async () => {
      try {
        const geometries = new Map<string, THREE.BufferGeometry>()
        await Promise.all(
          manifest.meshes.map(async (mesh) => {
            geometries.set(mesh.id, await makeGeometry(mesh, manifest.assetsBaseUrl))
          }),
        )
        // A build switch (or StrictMode cleanup) can finish before its meshes.
        // Never let that stale load populate the next scene's shared refs.
        if (disposed) return

        partsRef.current = manifest.instances.map((instance) => {
          const geometry = geometries.get(instance.meshId)
          if (!geometry) {
            throw new Error(`Instance "${instance.id}" references missing mesh "${instance.meshId}".`)
          }

          const material = new THREE.MeshStandardMaterial({
            color: instance.color,
            metalness: instance.partType.includes('SHCS') ? 0.55 : 0.08,
            roughness: 0.48,
            transparent: true,
          })
          const mesh = new THREE.Mesh(geometry, material)
          const baseMatrix = new THREE.Matrix4().fromArray(instance.transform)
          mesh.matrixAutoUpdate = false
          mesh.matrix.copy(baseMatrix)
          mesh.userData.instanceId = instance.id
          mesh.userData.instanceName = instance.name
          mesh.userData.partType = instance.partType
          scene.add(mesh)

          return { instance, mesh, baseMatrix, material }
        })

        partsRef.current.forEach((part) => {
          applyPartState(
            part,
            latestStateRef.current.visiblePartTypes,
            latestSelectionRef.current.selectedId,
            latestSelectionRef.current.hoveredId,
            latestStateRef.current.focusGroup,
            latestSelectionRef.current.isolatedId,
            agentHighlightsRef.current,
            latestStateRef.current.diffStatuses,
            poseMatricesRef.current,
            latestStateRef.current.partTypeColors,
            latestStateRef.current.visibleInstanceIds,
          )
        })
        container.dataset.buildvizVisibleInstances = String(partsRef.current.filter((part) => part.mesh.visible).length)
        rebuildAgentHighlightGroup(agentHighlightGroup, agentHighlightsRef.current, partsRef.current)

        const frameCamera = (center: THREE.Vector3, radius: number, farRadius = radius) => {
          const distance = radius / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))) * 1.8
          const direction = new THREE.Vector3(0.85, -1.2, 0.7).normalize()
          controls.target.copy(center)
          camera.position.copy(center).add(direction.multiplyScalar(distance))
          camera.near = Math.max(radius / 1000, 0.1)
          camera.far = farRadius * 12
          camera.updateProjectionMatrix()
          controls.update()
        }

        const centroidBounds = new THREE.Box3()
        manifest.instances.forEach((instance) => {
          if (instance.centroid) {
            centroidBounds.expandByPoint(new THREE.Vector3(...instance.centroid))
          }
        })
        // Union in the REAL mesh extents: centroid spread alone badly
        // underestimates the radius for scenes with few instances but large
        // meshes (e.g. a pegboard coupon + one holder), which sized the far
        // plane inside the largest part.
        partsRef.current.forEach((part) => centroidBounds.expandByObject(part.mesh))

        let buildRadius = 1
        if (!centroidBounds.isEmpty()) {
          const size = centroidBounds.getSize(new THREE.Vector3())
          buildRadius = Math.max(size.x, size.y, size.z, 1)
          clipRadius = buildRadius
          frameCamera(new THREE.Vector3(...manifest.center), buildRadius)
        }

        if (latestStateRef.current.visibleInstanceIds) {
          const viewBounds = new THREE.Box3()
          partsRef.current.forEach((part) => {
            if (latestStateRef.current.visibleInstanceIds?.has(part.instance.id)) viewBounds.expandByObject(part.mesh)
          })
          if (!viewBounds.isEmpty()) {
            const size = viewBounds.getSize(new THREE.Vector3())
            frameCamera(viewBounds.getCenter(new THREE.Vector3()), Math.max(size.x, size.y, size.z, 1), buildRadius)
          }
        }

        // A ?part=…&isolate=1 deep link reframes on the single part (far plane
        // stays sized for the whole build so un-isolating never clips it).
        const isolated = latestSelectionRef.current.isolatedId
        const isolatedMesh = isolated
          ? partsRef.current.find((part) => part.instance.id === isolated)?.mesh
          : null
        if (isolatedMesh) {
          const bounds = new THREE.Box3().expandByObject(isolatedMesh)
          if (!bounds.isEmpty()) {
            const size = bounds.getSize(new THREE.Vector3())
            frameCamera(
              bounds.getCenter(new THREE.Vector3()),
              Math.max(size.x, size.y, size.z, 1),
              buildRadius,
            )
          }
        }
        if (agentHighlightsRef.current.frame && agentHighlightsRef.current.parts?.length) {
          const bounds = new THREE.Box3()
          partsRef.current.forEach((part) => {
            if (part.mesh.visible && matchingPartHighlight(agentHighlightsRef.current, part.instance)) bounds.expandByObject(part.mesh)
          })
          if (!bounds.isEmpty()) {
            const size = bounds.getSize(new THREE.Vector3())
            frameCamera(bounds.getCenter(new THREE.Vector3()), Math.max(size.x, size.y, size.z, 1), buildRadius)
          }
        }
        // Wires are synchronous, but the assembly's meshes are not. Present
        // them together, only after applying the pose and framing the camera.
        render()
        setSceneReady(true)
      } catch (error) {
        if (disposed) return
        setLoadError(error instanceof Error ? error.message : String(error))
      }
    }

    void loadScene()

    return () => {
      disposed = true
      resizeObserver.disconnect()
      clearLongPress()
      renderer.domElement.removeEventListener('pointermove', onPointerMove)
      renderer.domElement.removeEventListener('click', onClick)
      renderer.domElement.removeEventListener('dblclick', onDoubleClick)
      renderer.domElement.removeEventListener('pointerdown', onPointerDown)
      renderer.domElement.removeEventListener('pointerup', onPointerUp)
      renderer.domElement.removeEventListener('pointercancel', onPointerCancel)
      renderer.domElement.removeEventListener('contextmenu', onContextMenu)
      setContextMenu(null)
      controls.dispose()
      disposeHighlightObject(agentHighlightGroup)
      scene.remove(agentHighlightGroup)
      disposeWiresGroup(wiresGroup)
      scene.remove(wiresGroup)
      wiresGroupRef.current = null
      partsRef.current.forEach(({ mesh, material }) => {
        scene.remove(mesh)
        material.dispose()
      })
      partsRef.current = []
      agentHighlightGroupRef.current = null
      renderer.dispose()
      renderer.domElement.remove()
      rendererRef.current = null
      cameraRef.current = null
    }
  }, [manifest])

  useEffect(() => {
    poseMatricesRef.current = poseMatrices
    partsRef.current.forEach((part) => {
      applyPartState(
        part,
        visiblePartTypes,
        selectedId,
        hoveredId,
        focusGroup,
        isolatedId,
        agentHighlights,
        diffStatuses,
        poseMatrices,
        partTypeColors,
        visibleInstanceIds,
      )
    })
    if (containerRef.current) containerRef.current.dataset.buildvizVisibleInstances = String(partsRef.current.filter((part) => part.mesh.visible).length)
  }, [agentHighlights, diffStatuses, focusGroup, hoveredId, isolatedId, poseMatrices, selectedId, visiblePartTypes, visibleInstanceIds, partTypeColors])

  // Keep ?part=&isolate= in sync with in-viewer isolation so the address bar
  // is itself the shareable single-part link (replaceState: no history spam).
  // A selection-only ?part= deep link (no isolate) is left untouched.
  useEffect(() => {
    const url = new URL(window.location.href)
    const hadIsolate = url.searchParams.has('isolate')
    if (isolatedId) {
      url.searchParams.set('part', isolatedId)
      url.searchParams.set('isolate', '1')
    } else if (hadIsolate) {
      url.searchParams.delete('isolate')
      url.searchParams.delete('part')
    }
    if (url.toString() !== window.location.href) {
      window.history.replaceState(null, '', url)
    }
  }, [isolatedId])

  // Single-part link: the same URL the isolation sync writes, buildable from
  // the right-click menu for any part without having to isolate it first.
  const copyPartLink = async (instanceId: string) => {
    const url = new URL(window.location.href)
    url.searchParams.set('part', instanceId)
    url.searchParams.set('isolate', '1')
    url.searchParams.delete('highlight')
    try {
      await navigator.clipboard.writeText(url.toString())
      setPartLinkCopied(true)
      window.setTimeout(() => setPartLinkCopied(false), 2000)
    } catch {
      setPartLinkCopied(false)
    }
  }

  // Build a shareable annotated review URL from the CURRENT highlights + the
  // typed question, reusing the same ?highlight= API the agent uses. Falls back
  // to the selected part when nothing is explicitly highlighted, so a reviewer
  // always lands on something.
  const buildReviewUrl = () => {
    const url = new URL(window.location.href)
    const spec: AgentHighlightSpec = { ...agentHighlights }
    if (!hasHighlightTargets(spec) && selectedId) {
      spec.parts = [{ instanceId: selectedId }]
    }
    const question = reviewQuestion.trim()
    if (spec.parts?.length) {
      spec.frame = true
      spec.ghostOthers = true
    }
    if (question) spec.question = question
    else delete spec.question
    url.searchParams.set('highlight', JSON.stringify(spec))
    return url.toString()
  }

  const reviewUrl = reviewOpen ? buildReviewUrl() : ''

  const copyReviewLink = async () => {
    try {
      await navigator.clipboard.writeText(buildReviewUrl())
      setReviewCopied(true)
      window.setTimeout(() => setReviewCopied(false), 2000)
    } catch {
      setReviewCopied(false)
    }
  }

  const reviewQuestionText = agentHighlights.question?.trim() ? agentHighlights.question.trim() : null

  // Mirrors the rulerCandidates() restriction so the hint explains why the
  // ruler ignores other parts.
  const rulerScopeNote = !rulerMode
    ? ''
    : selectedPart
    ? ' Measuring the selected part only.'
    : agentHighlights.parts && agentHighlights.parts.length > 0
    ? ' Measuring highlighted parts only.'
    : ''

  return (
    <section className="viewer-shell">
      <div
        ref={containerRef}
        className="viewer-canvas"
        aria-label={`${manifest.name} 3D viewer`}
        data-buildviz-ready={sceneReady ? 'true' : 'false'}
        data-buildviz-source-instances={manifest.instances.length}
      />
      <div className="viewer-overlay">
        <div>
          <strong>{hoveredPart?.name ?? selectedPart?.name ?? manifest.name}</strong>
          <span>
            {partLinkCopied
              ? 'Part link copied to clipboard.'
              : rulerMode
              ? (coarsePointer
                  ? rulerAnchor
                    ? 'Ruler: tap to measure from the pinned point. Double-tap to move the pin; tap empty space to unpin.'
                    : 'Ruler: tap an edge to measure it. Double-tap to pin a start point.'
                  : rulerAnchor
                  ? 'Ruler: hover to measure from the pinned point. Click to move it; click empty space to unpin.'
                  : 'Ruler: hover an edge to measure it. Click to pin a start point.') + rulerScopeNote
              : pickerMode
              ? coarsePointer
                ? 'Picker mode: tap a point to read local object XYZ coordinates.'
                : 'Picker mode: hover a point to read local object XYZ coordinates.'
              : isolatedId
              ? coarsePointer
                ? 'Isolated part. Double-tap it again or tap empty space to show the full build.'
                : 'Isolated part. Double-click it again or click empty space to show the full build.'
              : hoveredPart?.role ??
                selectedPart?.role ??
                (coarsePointer
                  ? 'Tap to inspect. Double-tap to isolate. Long-press for options.'
                  : 'Single-click to inspect. Double-click to isolate a part.')}
          </span>
        </div>
      </div>
      {reviewOpen ? (
        <div className="review-share-panel" role="dialog" aria-label="Share an annotated review link">
          <div className="review-share-head">
            <label htmlFor="review-question">Question / note for the reviewer</label>
            <button
              type="button"
              className="review-share-close"
              onClick={() => setReviewOpen(false)}
              aria-label="Close review link dialog"
              title="Close"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6 6l12 12M18 6 6 18" />
              </svg>
            </button>
          </div>
          <textarea
            id="review-question"
            className="review-share-question"
            value={reviewQuestion}
            onChange={(event) => setReviewQuestion(event.target.value)}
            placeholder="e.g. Is this bracket thick enough where it meets the servo?"
            rows={3}
          />
          <p className="review-share-hint">
            {hasHighlightTargets(agentHighlights)
              ? 'Uses the parts currently highlighted in the viewer.'
              : selectedId
              ? 'No highlights set — the selected part will be highlighted.'
              : 'Tip: highlight parts (or select one) first so the reviewer sees them.'}
          </p>
          <input className="review-share-url" type="text" readOnly value={reviewUrl} aria-label="Review link" />
          <div className="review-share-actions">
            <button type="button" className="review-share-copy" onClick={copyReviewLink}>
              {reviewCopied ? 'Copied!' : 'Copy link'}
            </button>
          </div>
        </div>
      ) : null}
      {contextMenu ? (
        <div
          className="part-context-menu"
          role="menu"
          style={{
            // Keep the menu on-screen when the press lands near the right or
            // bottom edge (easy to do on a phone).
            left: Math.max(8, Math.min(contextMenu.x, window.innerWidth - 200)),
            top: Math.max(8, Math.min(contextMenu.y, window.innerHeight - 290)),
          }}
        >
          <div className="part-context-menu-header">
            <strong>{contextMenu.name}</strong>
            {contextMenu.name !== contextMenu.partType ? <small>{contextMenu.partType}</small> : null}
          </div>
          <button
            type="button"
            role="menuitem"
            disabled={downloadBusy || manifest.instances.find(i => i.id === contextMenu.instanceId)?.cots === true || manifest.instances.find(i => i.id === contextMenu.instanceId)?.role === 'hardware'}
            onClick={async () => {
              const instance = manifest.instances.find(i => i.id === contextMenu.instanceId)
              if (!instance) return
              setDownloadBusy(true)
              setDownloadError(null)
              try {
                const source = printMeshForPart(manifest, instance)
                const geometry = await makeGeometry(source, manifest.assetsBaseUrl)
                let data: DataView
                try { data = printableStl(geometry) } finally { geometry.dispose() }
                const url = URL.createObjectURL(new Blob([new Uint8Array(data.buffer as ArrayBuffer, data.byteOffset, data.byteLength)], { type: 'model/stl' }))
                const link = document.createElement('a')
                link.href = url
                link.download = stlFilename(instance)
                document.body.appendChild(link)
                link.click()
                link.remove()
                window.setTimeout(() => URL.revokeObjectURL(url), 60000)
                setContextMenu(null)
              } catch (error) {
                setDownloadError(error instanceof Error ? error.message : 'Could not download STL. Please retry.')
              } finally {
                setDownloadBusy(false)
              }
            }}
            title="Download this part in its supplied print orientation, centered on the bed in millimeters"
          >
            {downloadBusy ? 'Preparing STL…' : 'Download print-ready STL'}
          </button>
          {downloadError ? <p role="alert">{downloadError}</p> : null}
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              onRequestDrawing?.(contextMenu.partType)
              setContextMenu(null)
            }}
            disabled={!onRequestDrawing}
            title="Generate a dimensioned schematic drawing (orthographic axis views) of this part"
          >
            Schematic drawing
          </button>
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setSelectedId(contextMenu.instanceId)
              setIsolatedId(contextMenu.instanceId)
              setContextMenu(null)
            }}
          >
            Isolate part
          </button>
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              void copyPartLink(contextMenu.instanceId)
              setContextMenu(null)
            }}
            title="Copy a shareable URL that opens this build with just this part isolated and framed"
          >
            Copy part link
          </button>
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setReviewOpen(true)
              setContextMenu(null)
            }}
            title="Create a shareable review link: this part highlighted plus a pinned question"
          >
            Share review link…
          </button>
        </div>
      ) : null}
      {reviewQuestionText ? (
        <div className="review-question-banner" role="note">
          <span className="review-question-label">Review question</span>
          <p>{reviewQuestionText}</p>
          <button
            type="button"
            className="review-question-dismiss"
            onClick={() => setAgentHighlights((current) => ({ ...current, question: undefined }))}
            aria-label="Dismiss review question"
            title="Dismiss"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M6 6l12 12M18 6 6 18" />
            </svg>
          </button>
        </div>
      ) : null}
      {selectedPart ||
      screenMeasurement ||
      screenRulerAnchor ||
      screenPick ||
      screenPickMarker ||
      screenAgentAnnotations.length > 0 ? (
        <div className="feature-overlay" aria-hidden="true">
          <svg className="dimension-overlay">
            {screenOverlays.dimensions.map((dimension) => (
              <g key={dimension.id}>
                <line
                  x1={dimension.x1}
                  y1={dimension.y1}
                  x2={dimension.x2}
                  y2={dimension.y2}
                />
                <circle cx={dimension.x1} cy={dimension.y1} r="3" />
                <circle cx={dimension.x2} cy={dimension.y2} r="3" />
                <text
                  x={(dimension.x1 + dimension.x2) / 2}
                  y={(dimension.y1 + dimension.y2) / 2 - 8}
                >
                  {dimension.text}
                </text>
              </g>
            ))}
            {screenMeasurement ? (
              <g className="ruler-measurement">
                <line
                  x1={screenMeasurement.x1}
                  y1={screenMeasurement.y1}
                  x2={screenMeasurement.x2}
                  y2={screenMeasurement.y2}
                />
                <circle cx={screenMeasurement.x1} cy={screenMeasurement.y1} r="4" />
                <circle cx={screenMeasurement.x2} cy={screenMeasurement.y2} r="4" />
                <text x={screenMeasurement.x} y={screenMeasurement.y}>
                  {screenMeasurement.label}
                </text>
              </g>
            ) : null}
            {screenRulerAnchor ? (
              <g className="ruler-anchor">
                <circle cx={screenRulerAnchor.x} cy={screenRulerAnchor.y} r="7" />
                <circle
                  className="ruler-anchor-dot"
                  cx={screenRulerAnchor.x}
                  cy={screenRulerAnchor.y}
                  r="2"
                />
              </g>
            ) : null}
          </svg>
          {screenOverlays.labels.map((label) => (
            <div
              className="feature-marker"
              key={label.id}
              title={label.text}
              style={{ transform: `translate(${label.x}px, ${label.y}px)` }}
            >
              {label.marker}
            </div>
          ))}
          {screenAgentAnnotations.map((annotation) => (
            <div
              className="agent-annotation"
              key={annotation.id}
              style={{
                borderColor: annotation.color,
                transform: `translate(${annotation.x}px, ${annotation.y}px)`,
              }}
            >
              {annotation.text}
            </div>
          ))}
          {screenPickMarker ? (
            <div
              className="picker-point-marker"
              style={{ transform: `translate(${screenPickMarker.x}px, ${screenPickMarker.y}px)` }}
            />
          ) : null}
          {screenPick ? (
            <div
              className="picker-readout"
              style={{ transform: `translate(${screenPick.x}px, ${screenPick.y}px)` }}
            >
              <strong>{screenPick.label}</strong>
              <span>{screenPick.detail}</span>
            </div>
          ) : null}
        </div>
      ) : null}
      {selectedPart ? (
        <aside
          className={`part-yaml-panel ${yamlCollapsed ? 'collapsed' : ''}`}
          aria-label={`${selectedPart.name} YAML`}
        >
          <div className="part-yaml-header">
            <div>
              <strong>{selectedPart.name}</strong>
              <span>
                design_spec.yaml / parts.{selectedPart.partType}
                {coarsePointer ? '' : ` · press M to ${yamlCollapsed ? 'expand' : 'collapse'}`}
              </span>
            </div>
            <div className="part-yaml-actions">
              <button
                type="button"
                className="part-yaml-toggle"
                onClick={() => setYamlCollapsed((current) => !current)}
                aria-expanded={!yamlCollapsed}
                aria-controls="selected-part-yaml"
                title={yamlCollapsed ? 'Expand YAML (M)' : 'Minimize YAML (M)'}
              >
                {yamlCollapsed ? '+' : '-'}
              </button>
            </div>
          </div>
          {yamlCollapsed ? null : (
            <pre id="selected-part-yaml">
              {selectedYaml ??
                (designSpec.url === designSpecUrl && designSpec.error
                  ? `Could not load design_spec.yaml from ${designSpecUrl}: ${designSpec.error}`
                  : `No design_spec.yaml entry for partType: ${selectedPart.partType}`)}
            </pre>
          )}
        </aside>
      ) : null}
      {loadError ? <p className="viewer-error">{loadError}</p> : null}
    </section>
  )
}
