import { load as loadYaml } from 'js-yaml'
import type { BuildInstance, BuildSceneManifest, Vec3 } from './buildScene'

export type DesignDimension = {
  label?: string
  value?: number | string
  axis?: string
  from_mm?: unknown
  to_mm?: unknown
  description?: string
  llm_hint?: string
}

export type DesignFeature = {
  label?: string
  aliases?: string[]
  kind?: string
  purpose?: string
  llm_context?: string
  render?: {
    anchor_mm?: unknown
    label_offset_mm?: unknown
  }
  dimensions?: Record<string, DesignDimension>
}

export type DesignHole = {
  name?: string
  diameter_mm?: number
  position_mm?: unknown
  axis?: string
  note?: string
}

export type DesignPart = {
  label?: string
  aliases?: string[]
  description?: string
  qty?: number
  bounds_mm?: unknown
  features?: Record<string, DesignFeature>
  holes?: DesignHole[]
  wire_channels?: unknown[]
  keep_out_volumes?: unknown[]
}

// Purpose record for one wire/cable route (keyed by the route's id in
// scene.json routes[]). The WireViz-style connectivity detail (pins, gauge,
// signal) is free-form; BuildViz only requires the purpose to be written down.
export type DesignWire = {
  purpose?: string
  signal?: string
  gauge?: string
  notes?: string
}

export type DesignSpec = {
  parts?: Record<string, DesignPart>
  wiring?: Record<string, DesignWire>
  coordinate_systems?: Record<string, unknown>
  print_orientations?: Record<string, unknown>
}

export type BuildIndex = {
  manifest: BuildSceneManifest
  designSpec: DesignSpec | null
  designSpecText: string | null
}

export type PartSummary = {
  partType: string
  label: string
  description: string | null
  instances: BuildInstance[]
  instanceCount: number
  meshIds: string[]
  hasDesignSpec: boolean
  featureCount: number
  holeCount: number
  dimensions: string[]
  boundsMm: Vec3 | null
}

export type FeatureSummary = {
  partType: string
  featureId: string
  label: string
  aliases: string[]
  kind: string | null
  purpose: string | null
  llmContext: string | null
  render: DesignFeature['render'] | null
  dimensions: Record<string, DesignDimension>
}

const isVec3 = (value: unknown): value is Vec3 =>
  Array.isArray(value) &&
  value.length === 3 &&
  value.every((item) => typeof item === 'number' && Number.isFinite(item))

const normalize = (value: string) => value.toLowerCase().replaceAll(/[^a-z0-9]+/g, ' ').trim()

const unique = <T,>(items: T[]) => [...new Set(items)]

const isPartSummary = (summary: PartSummary | null): summary is PartSummary =>
  summary !== null

const formatDimension = (dimensionId: string, dimension: DesignDimension) => {
  const label = dimension.label ?? dimensionId
  const value = dimension.value === undefined ? '' : `: ${dimension.value}`
  const axis = dimension.axis ? ` (${dimension.axis})` : ''
  return `${label}${value}${axis}`
}

const summarizeDimensions = (partSpec: DesignPart | undefined) => {
  const featureDimensions = Object.entries(partSpec?.features ?? {}).flatMap(
    ([featureId, feature]) =>
      Object.entries(feature.dimensions ?? {}).map(
        ([dimensionId, dimension]) => `${feature.label ?? featureId} / ${formatDimension(dimensionId, dimension)}`,
      ),
  )

  const bounds = isVec3(partSpec?.bounds_mm)
    ? [`bounds: ${partSpec.bounds_mm.map((value) => `${value}mm`).join(' x ')}`]
    : []

  return [...featureDimensions, ...bounds]
}

export const parseDesignSpec = (source: string | null): DesignSpec | null => {
  if (!source) return null
  const parsed = loadYaml(source)
  return typeof parsed === 'object' && parsed !== null ? (parsed as DesignSpec) : null
}

export const createBuildIndex = (
  manifest: BuildSceneManifest,
  designSpecText: string | null,
): BuildIndex => ({
  manifest,
  designSpec: parseDesignSpec(designSpecText),
  designSpecText,
})

// How well a design_spec.yaml covers a scene's part types. The spec is the
// durable record of each part's purpose, so "uncovered" scene parts mean
// geometry whose intent was never written down, and "stale" spec entries mean
// documented parts that no longer exist in the scene. Shared by `buildviz
// compat` (project gate) and the hub (push/register warnings).
export type SpecCoverage = {
  /** Spec text was provided (file existed / payload carried one). */
  hasSpec: boolean
  /** Parsed as a YAML mapping (only meaningful when hasSpec). */
  parses: boolean
  /** Has a non-empty parts: section (only meaningful when parses). */
  hasParts: boolean
  /** Unique partTypes in the scene, in first-seen order. */
  scenePartTypes: string[]
  /** Scene partTypes with NO design_spec entry (undocumented intent). */
  uncovered: string[]
  /** design_spec parts entries with no matching scene partType (stale drift). */
  stale: string[]
  /** Scene routes[] ids with NO design_spec wiring: entry (undocumented wires).
   *  Empty when the scene has no routes. */
  uncoveredWires: string[]
  /** design_spec wiring: entries with no matching scene route id (stale). */
  staleWires: string[]
}

export const specCoverage = (
  manifest: BuildSceneManifest,
  designSpecText: string | null,
): SpecCoverage => {
  const scenePartTypes = unique(manifest.instances.map((instance) => instance.partType))
  const routeIds = (manifest.routes ?? []).map((route) => route.id)
  if (designSpecText === null || designSpecText.trim().length === 0) {
    return {
      hasSpec: false,
      parses: false,
      hasParts: false,
      scenePartTypes,
      uncovered: scenePartTypes,
      stale: [],
      uncoveredWires: routeIds,
      staleWires: [],
    }
  }
  let spec: DesignSpec | null
  try {
    spec = parseDesignSpec(designSpecText)
  } catch {
    spec = null
  }
  if (!spec) {
    return {
      hasSpec: true,
      parses: false,
      hasParts: false,
      scenePartTypes,
      uncovered: scenePartTypes,
      stale: [],
      uncoveredWires: routeIds,
      staleWires: [],
    }
  }
  // Wire coverage: every published route should have a wiring: purpose entry,
  // and wiring: entries should not outlive their routes.
  const specWires = Object.keys(spec.wiring ?? {})
  const uncoveredWires = routeIds.filter((routeId) => !specWires.includes(routeId))
  const staleWires = specWires.filter((routeId) => !routeIds.includes(routeId))
  const specParts = Object.keys(spec.parts ?? {})
  if (specParts.length === 0) {
    return {
      hasSpec: true,
      parses: true,
      hasParts: false,
      scenePartTypes,
      uncovered: scenePartTypes,
      stale: [],
      uncoveredWires,
      staleWires,
    }
  }
  return {
    hasSpec: true,
    parses: true,
    hasParts: true,
    scenePartTypes,
    uncovered: scenePartTypes.filter((partType) => !specParts.includes(partType)),
    stale: specParts.filter((partType) => !scenePartTypes.includes(partType)),
    uncoveredWires,
    staleWires,
  }
}

export const listPartTypes = (build: BuildIndex) =>
  unique(build.manifest.instances.map((instance) => instance.partType)).sort((a, b) =>
    a.localeCompare(b),
  )

export const summarizePart = (build: BuildIndex, partType: string): PartSummary | null => {
  const instances = build.manifest.instances.filter((instance) => instance.partType === partType)
  if (instances.length === 0) return null

  const partSpec = build.designSpec?.parts?.[partType]
  return {
    partType,
    label: partSpec?.label ?? partType,
    description: partSpec?.description ?? null,
    instances,
    instanceCount: instances.length,
    meshIds: unique(instances.map((instance) => instance.meshId)),
    hasDesignSpec: Boolean(partSpec),
    featureCount: Object.keys(partSpec?.features ?? {}).length,
    holeCount: partSpec?.holes?.length ?? 0,
    dimensions: summarizeDimensions(partSpec),
    boundsMm: isVec3(partSpec?.bounds_mm) ? partSpec.bounds_mm : null,
  }
}

export const inspectBuild = (build: BuildIndex) => {
  const partTypes = listPartTypes(build)
  const parts = partTypes.map((partType) => summarizePart(build, partType)).filter(isPartSummary)
  const missingDesignSpec = parts
    .filter((part) => !part.hasDesignSpec)
    .map((part) => part.partType)

  return {
    name: build.manifest.name,
    units: build.manifest.units,
    source: build.manifest.source ?? null,
    meshCount: build.manifest.meshes.length,
    instanceCount: build.manifest.instances.length,
    partTypeCount: partTypes.length,
    parts,
    missingDesignSpec,
  }
}

export const summarizeFeature = (
  build: BuildIndex,
  partType: string,
  featureId: string,
): FeatureSummary | null => {
  const feature = build.designSpec?.parts?.[partType]?.features?.[featureId]
  if (!feature) return null

  return {
    partType,
    featureId,
    label: feature.label ?? featureId,
    aliases: feature.aliases ?? [],
    kind: feature.kind ?? null,
    purpose: feature.purpose ?? null,
    llmContext: feature.llm_context ?? null,
    render: feature.render ?? null,
    dimensions: feature.dimensions ?? {},
  }
}

const partSearchText = (summary: PartSummary) =>
  normalize(
    [
      summary.partType,
      summary.label,
      summary.description,
      summary.instances.map((instance) => `${instance.name} ${instance.role}`).join(' '),
      summary.dimensions.join(' '),
    ]
      .filter(Boolean)
      .join(' '),
  )

export const queryBuild = (build: BuildIndex, question: string, limit = 5) => {
  const terms = normalize(question).split(/\s+/).filter(Boolean)
  const summaries = listPartTypes(build)
    .map((partType) => summarizePart(build, partType))
    .filter(isPartSummary)

  const scored = summaries
    .map((summary) => {
      const text = partSearchText(summary)
      const score = terms.reduce((total, term) => total + (text.includes(term) ? 1 : 0), 0)
      return { summary, score }
    })
    .filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score || a.summary.partType.localeCompare(b.summary.partType))
    .slice(0, limit)

  return {
    question,
    answer:
      scored.length > 0
        ? `Found ${scored.length} relevant part type${scored.length === 1 ? '' : 's'}.`
        : 'No directly matching parts found in scene.json/design_spec.yaml.',
    results: scored.map(({ summary, score }) => ({ score, part: summary })),
  }
}

