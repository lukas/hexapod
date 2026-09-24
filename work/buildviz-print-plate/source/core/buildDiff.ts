import type { BuildMesh, BuildSceneManifest, Vec3 } from './buildScene'

// Manifest diffing: the named-version compare contract shared by the viewer
// (compare mode), the hub, and the CLI `diff` command.

export type DiffStatus = 'added' | 'removed' | 'moved' | 'changed'

export type ManifestDiff = {
  meshes: {
    added: string[]
    removed: string[]
    changed: Array<{ meshId: string; changes: string[] }>
  }
  instances: {
    added: Array<{ instanceId: string; partType: string }>
    removed: Array<{ instanceId: string; partType: string }>
    moved: Array<{ instanceId: string; partType: string; translationMm: Vec3 }>
    changed: Array<{ instanceId: string; partType: string; changes: string[] }>
  }
  counts: {
    addedInstances: number
    removedInstances: number
    movedInstances: number
    changedInstances: number
    addedMeshes: number
    removedMeshes: number
    changedMeshes: number
  }
}

export type MeshHashes = {
  from?: Record<string, string>
  to?: Record<string, string>
}

const transformsEqual = (a: number[], b: number[], epsilon = 1e-6) =>
  a.length === b.length && a.every((value, index) => Math.abs(value - b[index]) <= epsilon)

const transformTranslation = (transform: number[]): Vec3 => [
  transform[12] ?? 0,
  transform[13] ?? 0,
  transform[14] ?? 0,
]

const roundMm = (value: number) => Math.round(value * 1000) / 1000

const meshChanges = (from: BuildMesh, to: BuildMesh, hashes: MeshHashes) => {
  const changes: string[] = []
  if ((from.url ?? null) !== (to.url ?? null)) changes.push('url')

  const fromHash = hashes.from?.[from.id]
  const toHash = hashes.to?.[to.id]
  if (fromHash && toHash && fromHash !== toHash) changes.push('geometry')

  return changes
}

export const diffManifests = (
  from: BuildSceneManifest,
  to: BuildSceneManifest,
  meshHashes: MeshHashes = {},
): ManifestDiff => {
  const fromMeshes = new Map(from.meshes.map((mesh) => [mesh.id, mesh]))
  const toMeshes = new Map(to.meshes.map((mesh) => [mesh.id, mesh]))
  const changedMeshes: Array<{ meshId: string; changes: string[] }> = []

  toMeshes.forEach((toMesh, meshId) => {
    const fromMesh = fromMeshes.get(meshId)
    if (!fromMesh) return
    const changes = meshChanges(fromMesh, toMesh, meshHashes)
    if (changes.length > 0) changedMeshes.push({ meshId, changes })
  })

  const changedMeshIds = new Set(changedMeshes.map((mesh) => mesh.meshId))
  const fromInstances = new Map(from.instances.map((instance) => [instance.id, instance]))
  const toInstances = new Map(to.instances.map((instance) => [instance.id, instance]))

  const added: ManifestDiff['instances']['added'] = []
  const removed: ManifestDiff['instances']['removed'] = []
  const moved: ManifestDiff['instances']['moved'] = []
  const changed: ManifestDiff['instances']['changed'] = []

  to.instances.forEach((instance) => {
    if (!fromInstances.has(instance.id)) {
      added.push({ instanceId: instance.id, partType: instance.partType })
    }
  })
  from.instances.forEach((instance) => {
    if (!toInstances.has(instance.id)) {
      removed.push({ instanceId: instance.id, partType: instance.partType })
    }
  })

  to.instances.forEach((instance) => {
    const previous = fromInstances.get(instance.id)
    if (!previous) return

    const changes: string[] = []
    if (previous.meshId !== instance.meshId) changes.push('meshId')
    if (previous.partType !== instance.partType) changes.push('partType')
    if (instance.meshId === previous.meshId && changedMeshIds.has(instance.meshId)) {
      changes.push('geometry')
    }

    const transformChanged = !transformsEqual(previous.transform, instance.transform)
    if (transformChanged && changes.length === 0) {
      const fromTranslation = transformTranslation(previous.transform)
      const toTranslation = transformTranslation(instance.transform)
      moved.push({
        instanceId: instance.id,
        partType: instance.partType,
        translationMm: [
          roundMm(toTranslation[0] - fromTranslation[0]),
          roundMm(toTranslation[1] - fromTranslation[1]),
          roundMm(toTranslation[2] - fromTranslation[2]),
        ],
      })
      return
    }

    if (transformChanged) changes.push('transform')
    if (changes.length > 0) {
      changed.push({ instanceId: instance.id, partType: instance.partType, changes })
    }
  })

  return {
    meshes: {
      added: to.meshes.filter((mesh) => !fromMeshes.has(mesh.id)).map((mesh) => mesh.id),
      removed: from.meshes.filter((mesh) => !toMeshes.has(mesh.id)).map((mesh) => mesh.id),
      changed: changedMeshes,
    },
    instances: { added, removed, moved, changed },
    counts: {
      addedInstances: added.length,
      removedInstances: removed.length,
      movedInstances: moved.length,
      changedInstances: changed.length,
      addedMeshes: to.meshes.filter((mesh) => !fromMeshes.has(mesh.id)).length,
      removedMeshes: from.meshes.filter((mesh) => !toMeshes.has(mesh.id)).length,
      changedMeshes: changedMeshes.length,
    },
  }
}

export const instanceDiffStatuses = (diff: ManifestDiff): Record<string, DiffStatus> => {
  const statuses: Record<string, DiffStatus> = {}
  diff.instances.added.forEach(({ instanceId }) => {
    statuses[instanceId] = 'added'
  })
  diff.instances.removed.forEach(({ instanceId }) => {
    statuses[instanceId] = 'removed'
  })
  diff.instances.moved.forEach(({ instanceId }) => {
    statuses[instanceId] = 'moved'
  })
  diff.instances.changed.forEach(({ instanceId }) => {
    statuses[instanceId] = 'changed'
  })
  return statuses
}

export const summarizeDiff = (diff: ManifestDiff) => {
  const { counts } = diff
  return (
    `${counts.addedInstances} added, ${counts.removedInstances} removed, ` +
    `${counts.movedInstances} moved, ${counts.changedInstances} changed instances; ` +
    `${counts.changedMeshes} changed meshes.`
  )
}
