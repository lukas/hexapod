#!/usr/bin/env tsx
// Synthesize an ADDITIVE joints[]/poses[] motion demo from the static
// hexapod-prototype scene, without touching the real exporter output.
//
// The real builds carry only `leg` (L0..L5) and `joint` (yaw/hip/knee) LABELS,
// not kinematics. This script uses those labels to group each leg's parts into
// rigid links and derives plausible joint axes/pivots from instance centroids,
// then writes a NEW, SELF-CONTAINED build at
// `public/builds/hexapod-motion-demo/` (its own scene.json + a copy of the STL
// assets it references). It is fully reversible: delete the directory to remove
// the demo. The real exporter output (hexapod-prototype) is never touched.
//
//   npx tsx scripts/synthMotionDemo.ts

import { copyFile, mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import type { BuildInstance, BuildSceneManifest, Joint, Pose, Vec3 } from '../core/buildScene'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const SRC_ID = 'hexapod-prototype'
const DEMO_ID = 'hexapod-motion-demo'
const srcDir = path.join(root, 'public', 'builds', SRC_ID)
const srcScene = path.join(srcDir, 'scene.json')
const outDir = path.join(root, 'public', 'builds', DEMO_ID)
const outScene = path.join(outDir, 'scene.json')

const centroidOf = (instance: BuildInstance | undefined): Vec3 =>
  instance?.centroid ?? [
    instance?.transform?.[12] ?? 0,
    instance?.transform?.[13] ?? 0,
    instance?.transform?.[14] ?? 0,
  ]

const main = async () => {
  const manifest = JSON.parse(await readFile(srcScene, 'utf8')) as BuildSceneManifest
  const legs = [...new Set(manifest.instances.map((i) => i.leg).filter(Boolean))] as string[]
  const center = manifest.center ?? [0, 0, 0]

  const joints: Joint[] = []

  for (const leg of legs.sort()) {
    const legParts = manifest.instances.filter((i) => i.leg === leg)
    const find = (predicate: (i: BuildInstance) => boolean) => legParts.find(predicate)

    const yawBody = find((i) => i.partType === 'servo_body' && i.joint === 'yaw')
    const yawHorn = find((i) => i.partType === 'servo_horn' && i.joint === 'yaw')
    const coxa = find((i) => i.partType === 'coxa_link')
    const hipBody = find((i) => i.partType === 'servo_body' && i.joint === 'hip')
    const hipHorn = find((i) => i.partType === 'servo_horn' && i.joint === 'hip')
    const femur = find((i) => i.partType === 'femur_link')
    const kneeBody = find((i) => i.partType === 'servo_body' && i.joint === 'knee')
    const kneeHorn = find((i) => i.partType === 'servo_horn' && i.joint === 'knee')
    const tibia = find((i) => i.partType === 'tibia_link')

    if (!yawBody || !coxa || !femur || !tibia) {
      console.warn(`Leg ${leg}: incomplete chain, skipping`)
      continue
    }

    // Radial direction (outward from the chassis centre) and the horizontal
    // tangent perpendicular to it. Yaw spins about vertical Z through the yaw
    // servo; hip/knee swing the leg in the vertical plane about that tangent.
    const yc = centroidOf(yawBody)
    const rx = yc[0] - center[0]
    const ry = yc[1] - center[1]
    const rlen = Math.hypot(rx, ry) || 1
    const tangent: Vec3 = [-ry / rlen, rx / rlen, 0]

    const id = (suffix: string) => `${leg}-${suffix}`
    const ids = (...parts: Array<BuildInstance | undefined>) =>
      parts.filter(Boolean).map((p) => (p as BuildInstance).id)

    joints.push({
      id: id('yaw'),
      type: 'revolute',
      axis: [0, 0, 1],
      origin: centroidOf(yawHorn ?? yawBody),
      instances: ids(yawHorn, coxa, hipBody),
      limits: { min: -55, max: 55 },
      home: 0,
      label: `${leg} yaw`,
    })
    joints.push({
      id: id('hip'),
      type: 'revolute',
      axis: tangent,
      origin: centroidOf(hipHorn ?? hipBody),
      parent: id('yaw'),
      instances: ids(hipHorn, femur, kneeBody),
      limits: { min: -70, max: 35 },
      home: 0,
      label: `${leg} hip`,
    })
    joints.push({
      id: id('knee'),
      type: 'revolute',
      axis: tangent,
      origin: centroidOf(kneeHorn ?? kneeBody),
      parent: id('hip'),
      instances: ids(kneeHorn, tibia),
      limits: { min: -20, max: 90 },
      home: 0,
      label: `${leg} knee`,
    })
  }

  // A few named whole-body poses to step through. Joints omitted stay home.
  const fill = (hip: number, knee: number, yaw = 0): Record<string, number> => {
    const values: Record<string, number> = {}
    for (const leg of legs) {
      values[`${leg}-yaw`] = yaw
      values[`${leg}-hip`] = hip
      values[`${leg}-knee`] = knee
    }
    return values
  }
  const poses: Pose[] = [
    { id: 'home', name: 'Home', jointValues: {} },
    { id: 'stand', name: 'Stand', jointValues: fill(-25, 35) },
    { id: 'crouch', name: 'Crouch', jointValues: fill(25, 80) },
    { id: 'splay', name: 'Splay (yaw out)', jointValues: fill(-10, 30, 45) },
  ]

  // Make the build self-contained: copy each referenced STL into the demo dir
  // (preserving its subpath) and rewrite the mesh URL to the new build id, so it
  // works under the viewer, the CLI (build-relative asset resolution), and a hub
  // push alike.
  const srcPrefix = `/builds/${SRC_ID}/`
  let copied = 0
  const meshes = await Promise.all(
    manifest.meshes.map(async (mesh) => {
      if (!mesh.url || !mesh.url.startsWith(srcPrefix)) return mesh
      const subPath = mesh.url.slice(srcPrefix.length)
      const from = path.join(srcDir, subPath)
      const to = path.join(outDir, subPath)
      await mkdir(path.dirname(to), { recursive: true })
      try {
        await copyFile(from, to)
        copied += 1
      } catch {
        console.warn(`  missing asset, skipped: ${subPath}`)
      }
      return { ...mesh, url: `/builds/${DEMO_ID}/${subPath}` }
    }),
  )

  const demo: BuildSceneManifest = {
    ...manifest,
    name: 'Hexapod Motion Demo',
    source: 'synthesized from hexapod-prototype by scripts/synthMotionDemo.ts (additive joints/poses)',
    meshes,
    joints,
    poses,
    checksConfig: {
      ...(manifest.checksConfig ?? {}),
      clearanceMm: manifest.checksConfig?.clearanceMm ?? 2,
    },
  }

  await mkdir(outDir, { recursive: true })
  await writeFile(outScene, `${JSON.stringify(demo, null, 2)}\n`, 'utf8')
  console.log(`Wrote ${path.relative(root, outScene)}`)
  console.log(`  ${joints.length} joints across ${legs.length} legs, ${poses.length} poses`)
  console.log(`  copied ${copied} STL asset(s) into the demo build.`)
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : String(error))
  process.exitCode = 1
})
