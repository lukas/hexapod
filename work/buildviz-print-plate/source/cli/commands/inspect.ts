import path from 'node:path'
import {
  loadBuild,
  fileInfo,
  resolveAssetPath,
  apiEnvelope,
} from '../cliBuild'

// `buildviz assets` (and related scene-inspection helpers).

export const listAssets = async (build: Awaited<ReturnType<typeof loadBuild>>) => {
  const scene = await fileInfo(path.join(build.buildDir, 'scene.json'))
  const designSpec = await fileInfo(path.join(build.buildDir, 'design_spec.yaml'))
  const meshes = await Promise.all(
    build.index.manifest.meshes.map(async (mesh) => ({
      kind: 'mesh',
      meshId: mesh.id,
      url: mesh.url ?? null,
      ...(await fileInfo(resolveAssetPath(build, mesh.url))),
    })),
  )

  return apiEnvelope(true, build, `Found ${meshes.length} mesh assets.`, [
    { kind: 'scene', ...scene },
    { kind: 'designSpec', ...designSpec },
    ...meshes,
  ])
}

