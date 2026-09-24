import * as THREE from 'three'
import { STLExporter } from 'three/examples/jsm/exporters/STLExporter.js'
import type { BuildInstance, BuildMesh, BuildSceneManifest } from '../../core/buildScene'

export function printMeshForPart(manifest: BuildSceneManifest, instance: BuildInstance): BuildMesh {
  const id = instance.printMeshId ?? instance.meshId
  const mesh = manifest.meshes.find((entry) => entry.id === id)
  if (!mesh) throw new Error(`Print mesh "${id}" is missing.`)
  return mesh
}

// Work in the source print frame, never the viewer's assembly/exploded pose.
// Preserve its orientation and dimensions; center XY and put the lowest Z on bed.
export function printableStl(source: THREE.BufferGeometry): DataView {
  const geometry = source.clone()
  try {
    geometry.computeBoundingBox()
    const bounds = geometry.boundingBox
    if (!bounds || bounds.isEmpty() || !Number.isFinite(bounds.min.z)) {
      throw new Error('This part has no printable geometry.')
    }
    const center = bounds.getCenter(new THREE.Vector3())
    geometry.translate(-center.x, -center.y, -bounds.min.z)
    const mesh = new THREE.Mesh(geometry)
    try {
      return new STLExporter().parse(mesh, { binary: true })
    } finally {
      ;(mesh.material as THREE.Material).dispose()
    }
  } finally {
    geometry.dispose()
  }
}

export function stlFilename(instance: BuildInstance): string {
  return `${(instance.partType || instance.name || 'part').replace(/[^a-zA-Z0-9._-]+/g, '_')}.stl`
}
