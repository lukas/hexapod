import { test } from 'node:test'
import assert from 'node:assert/strict'
import * as THREE from 'three'
import { MeshBVH } from 'three-mesh-bvh'
import { checkFastenings } from './fastenings'
import type { BuildSceneManifest } from '../core/buildScene'
import type { InstanceGeometry } from '../core/geometryEngine'

function tube(id: string, inner: number, outer: number, z0: number, z1: number): InstanceGeometry {
  const shape = new THREE.Shape()
  shape.absarc(0, 0, outer, 0, Math.PI * 2, false)
  const hole = new THREE.Path()
  hole.absarc(0, 0, inner, 0, Math.PI * 2, true)
  shape.holes.push(hole)
  const geometry = new THREE.ExtrudeGeometry(shape, { depth: z1 - z0, bevelEnabled: false, curveSegments: 32 })
  geometry.translate(0, 0, z0)
  geometry.computeBoundingBox()
  return { index: 0, instanceId: id, meshId: id, partType: id, name: id, mesh: { geometry, bvh: new MeshBVH(geometry), triangleCount: geometry.getAttribute('position').count / 3, localBox: geometry.boundingBox! }, matrix: new THREE.Matrix4(), inverse: new THREE.Matrix4(), worldMin: [-outer,-outer,z0], worldMax: [outer,outer,z1], isFastener: false }
}
const scene: BuildSceneManifest = { name: 'test', units: 'mm', center: [0,0,0], meshes: [], instances: [], fastenings: [{ id: 'joint', clampedInstanceId: 'plate', receiverInstanceId: 'wall', headSeat: [0,0,0], axis: [0,0,1], lengthMm: 6, shaftDiameterMm: 3, minEngagementMm: 3 }] }
test('explicit receiving wall, supported seat and clearance pass', () => {
  assert.equal(checkFastenings(scene, [tube('plate',1.7,5,0,2),tube('wall',1.2,5,2,7)])[0].status, 'pass')
})
test('short screw cannot borrow engagement from the clamped part', () => {
  const s = structuredClone(scene); s.fastenings![0].lengthMm = 1
  assert.equal(checkFastenings(s,[tube('plate',1.7,5,0,2),tube('wall',1.2,5,2,7)])[0].status,'fail')
})
test('hollow receiver fails even with nearby material', () => {
  assert.equal(checkFastenings(scene,[tube('plate',1.7,5,0,2),tube('wall',3,5,2,7)])[0].status,'fail')
})
test('blocked clamped hole fails', () => {
  assert.equal(checkFastenings(scene,[tube('plate',1,5,0,2),tube('wall',1.2,5,2,7)])[0].status,'fail')
})
test('missing receiver and unsupported seat fail', () => {
  assert.equal(checkFastenings(scene,[tube('plate',1.7,5,0,2)])[0].status,'fail')
  assert.equal(checkFastenings(scene,[tube('plate',3,5,0,2),tube('wall',1.2,5,2,7)])[0].status,'fail')
})
