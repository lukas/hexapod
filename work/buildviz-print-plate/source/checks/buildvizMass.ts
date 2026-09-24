import * as THREE from 'three'
import type { BuildSceneManifest } from '../core/buildScene'
import {
  buildInstanceGeometries,
  readTriVertex,
  round3,
  type GeometryLoadOptions,
  type InstanceGeometry,
} from '../core/geometryEngine'

// Mass properties: estimate the WEIGHT and WEIGHT DISTRIBUTION of a build from
// its meshes. Per unique mesh we integrate the enclosed volume and volume
// centroid (signed-tetrahedron sums, robust for watertight CAD solids); each
// instance then gets a mass from, in priority order:
//   1. checksConfig.partMassesGrams[partType]   — a KNOWN real mass (servo,
//      battery, PCB...), the only accurate option for bought parts;
//   2. volume × checksConfig.partDensitiesGCm3[partType];
//   3. volume × fastener/default density (steel 7.85 for detected fasteners,
//      solid PLA 1.24 otherwise — override via defaultDensityGCm3).
// The report aggregates total mass, world center of mass, and breakdowns by
// partType and focusGroup, so an agent can reason about balance ("is the CoM
// inside the support polygon?", "which side is heavy?").
//
// Browser- and Node-safe: meshes arrive through the injected loadMesh callback.

const PLA_DENSITY_G_CM3 = 1.24
const STEEL_DENSITY_G_CM3 = 7.85

export type MassOptions = GeometryLoadOptions & {
  /** Override the config/PLA default density (g/cm³) for unmatched parts. */
  defaultDensityGCm3?: number
}

export type MassPartTypeEntry = {
  partType: string
  count: number
  /** Volume of ONE instance's mesh (cm³). */
  unitVolumeCm3: number
  unitGrams: number
  totalGrams: number
  /** Share of the build total (0..1). */
  share: number
  /** Where the unit mass came from. */
  source: 'configured-mass' | 'configured-density' | 'fastener-density' | 'default-density'
  densityGCm3: number | null
}

export type MassGroupEntry = {
  group: string
  totalGrams: number
  share: number
  centerOfMassMm: [number, number, number]
}

export type MassReport = {
  totalGrams: number
  instanceCount: number
  centerOfMassMm: [number, number, number]
  /** World AABB of everything weighed, plus where the CoM sits inside it
   *  (0..1 per axis) — a quick balance read without any other context. */
  boundsMm: { min: [number, number, number]; max: [number, number, number] }
  centerOfMassFraction: [number, number, number]
  byPartType: MassPartTypeEntry[]
  byGroup: MassGroupEntry[]
  defaultDensityGCm3: number
  missingMeshes: string[]
  /** partTypes weighed by density even though they look like bought parts is a
   *  common source of error; configured-mass coverage is reported for triage. */
  configuredMassPartTypes: string[]
}

type MeshMassProps = { volumeMm3: number; centroidLocal: THREE.Vector3 }

// Enclosed volume + volume centroid from the signed-tetrahedron sum (apex at
// the origin). Exact for watertight meshes regardless of triangle winding.
const meshMassProps = (geometry: THREE.BufferGeometry): MeshMassProps => {
  const position = geometry.attributes.position as THREE.BufferAttribute
  const index = geometry.index
  const triangleCount = (index ? index.count : position.count) / 3
  const a = new THREE.Vector3()
  const b = new THREE.Vector3()
  const c = new THREE.Vector3()
  const cross = new THREE.Vector3()
  let volume6 = 0
  const centroid = new THREE.Vector3()
  for (let t = 0; t < triangleCount; t += 1) {
    readTriVertex(position, index, t, 0, a)
    readTriVertex(position, index, t, 1, b)
    readTriVertex(position, index, t, 2, c)
    const v6 = a.dot(cross.copy(b).cross(c))
    volume6 += v6
    // Tetra (0,a,b,c) centroid is (a+b+c)/4; accumulate weighted by its volume.
    centroid.addScaledVector(a, v6 / 4)
    centroid.addScaledVector(b, v6 / 4)
    centroid.addScaledVector(c, v6 / 4)
  }
  if (Math.abs(volume6) > 1e-9) centroid.multiplyScalar(1 / volume6)
  return { volumeMm3: Math.abs(volume6) / 6, centroidLocal: centroid }
}

const massSource = (
  manifest: BuildSceneManifest,
  instance: InstanceGeometry,
  defaultDensity: number,
): { grams: (volumeCm3: number) => number; source: MassPartTypeEntry['source']; densityGCm3: number | null } => {
  const cfg = manifest.checksConfig
  const configured = cfg?.partMassesGrams?.[instance.partType]
  if (typeof configured === 'number' && configured >= 0) {
    return { grams: () => configured, source: 'configured-mass', densityGCm3: null }
  }
  const density = cfg?.partDensitiesGCm3?.[instance.partType]
  if (typeof density === 'number' && density > 0) {
    return { grams: (volume) => volume * density, source: 'configured-density', densityGCm3: density }
  }
  if (instance.isFastener) {
    const fastenerDensity = cfg?.fastenerDensityGCm3 ?? STEEL_DENSITY_G_CM3
    return { grams: (volume) => volume * fastenerDensity, source: 'fastener-density', densityGCm3: fastenerDensity }
  }
  return { grams: (volume) => volume * defaultDensity, source: 'default-density', densityGCm3: defaultDensity }
}

export const massProperties = async (
  manifest: BuildSceneManifest,
  options: MassOptions,
): Promise<MassReport> => {
  const defaultDensity =
    options.defaultDensityGCm3 ?? manifest.checksConfig?.defaultDensityGCm3 ?? PLA_DENSITY_G_CM3

  // Fasteners are real weight: include them regardless of the check-engine
  // default (callers can still filter explicitly).
  const { instances, meshById, missingMeshes } = await buildInstanceGeometries(manifest, {
    ...options,
    includeFasteners: options.includeFasteners ?? true,
  })

  const propsByMesh = new Map<string, MeshMassProps>()
  for (const [meshId, mesh] of meshById) propsByMesh.set(meshId, meshMassProps(mesh.geometry))

  const worldCentroid = new THREE.Vector3()
  const comSum = new THREE.Vector3()
  let totalGrams = 0
  const boundsMin: [number, number, number] = [Infinity, Infinity, Infinity]
  const boundsMax: [number, number, number] = [-Infinity, -Infinity, -Infinity]

  type Bucket = { count: number; unitVolumeCm3: number; unitGrams: number; totalGrams: number; source: MassPartTypeEntry['source']; densityGCm3: number | null }
  const byType = new Map<string, Bucket>()
  const byGroup = new Map<string, { grams: number; comSum: THREE.Vector3 }>()

  for (const instance of instances) {
    const props = propsByMesh.get(instance.meshId)
    if (!props) continue
    const volumeCm3 = props.volumeMm3 / 1000
    const resolver = massSource(manifest, instance, defaultDensity)
    const grams = resolver.grams(volumeCm3)

    worldCentroid.copy(props.centroidLocal).applyMatrix4(instance.matrix)
    totalGrams += grams
    comSum.addScaledVector(worldCentroid, grams)

    for (let axis = 0; axis < 3; axis += 1) {
      boundsMin[axis] = Math.min(boundsMin[axis], instance.worldMin[axis])
      boundsMax[axis] = Math.max(boundsMax[axis], instance.worldMax[axis])
    }

    const bucket = byType.get(instance.partType) ?? {
      count: 0,
      unitVolumeCm3: volumeCm3,
      unitGrams: grams,
      totalGrams: 0,
      source: resolver.source,
      densityGCm3: resolver.densityGCm3,
    }
    bucket.count += 1
    bucket.totalGrams += grams
    byType.set(instance.partType, bucket)

    const groupKey =
      manifest.instances[instance.index]?.focusGroup ?? 'ungrouped'
    const group = byGroup.get(groupKey) ?? { grams: 0, comSum: new THREE.Vector3() }
    group.grams += grams
    group.comSum.addScaledVector(worldCentroid, grams)
    byGroup.set(groupKey, group)
  }

  const com = totalGrams > 0 ? comSum.multiplyScalar(1 / totalGrams) : comSum
  const centerOfMassMm: [number, number, number] = [round3(com.x), round3(com.y), round3(com.z)]
  const centerOfMassFraction = [0, 1, 2].map((axis) => {
    const span = boundsMax[axis] - boundsMin[axis]
    return span > 1e-9 ? Math.round(((centerOfMassMm[axis] - boundsMin[axis]) / span) * 1000) / 1000 : 0.5
  }) as [number, number, number]

  const byPartType: MassPartTypeEntry[] = [...byType.entries()]
    .map(([partType, bucket]) => ({
      partType,
      count: bucket.count,
      unitVolumeCm3: round3(bucket.unitVolumeCm3),
      unitGrams: round3(bucket.unitGrams),
      totalGrams: round3(bucket.totalGrams),
      share: totalGrams > 0 ? Math.round((bucket.totalGrams / totalGrams) * 1000) / 1000 : 0,
      source: bucket.source,
      densityGCm3: bucket.densityGCm3,
    }))
    .sort((x, y) => y.totalGrams - x.totalGrams)

  const byGroupList: MassGroupEntry[] = [...byGroup.entries()]
    .map(([group, entry]) => {
      const groupCom = entry.grams > 0 ? entry.comSum.clone().multiplyScalar(1 / entry.grams) : entry.comSum
      return {
        group,
        totalGrams: round3(entry.grams),
        share: totalGrams > 0 ? Math.round((entry.grams / totalGrams) * 1000) / 1000 : 0,
        centerOfMassMm: [round3(groupCom.x), round3(groupCom.y), round3(groupCom.z)] as [number, number, number],
      }
    })
    .sort((x, y) => y.totalGrams - x.totalGrams)

  return {
    totalGrams: round3(totalGrams),
    instanceCount: instances.length,
    centerOfMassMm,
    boundsMm: {
      min: boundsMin.map(round3) as [number, number, number],
      max: boundsMax.map(round3) as [number, number, number],
    },
    centerOfMassFraction,
    byPartType,
    byGroup: byGroupList,
    defaultDensityGCm3: defaultDensity,
    missingMeshes,
    configuredMassPartTypes: Object.keys(manifest.checksConfig?.partMassesGrams ?? {}),
  }
}
