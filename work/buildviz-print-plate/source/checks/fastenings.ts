import * as THREE from 'three'
import type { BuildSceneManifest, SceneCheck } from '../core/buildScene'
import { pointInside, type InstanceGeometry } from '../core/geometryEngine'

/** Sample declared receiver, never substitute a nearby host or the clamped part.
 * A geometric sanity check, not a thread-strength or print-tolerance guarantee.
 */
export function checkFastenings(manifest: BuildSceneManifest, instances: InstanceGeometry[]): SceneCheck[] {
  const byId = new Map(instances.map(i => [i.instanceId, i]))
  const ids = new Set<string>()
  return (manifest.fastenings ?? []).map(f => {
    const clamped = byId.get(f.clampedInstanceId)
    const receiver = byId.get(f.receiverInstanceId)
    const base = { id: `fastening-${f.id}`, kind: 'thread_engagement', instances: [f.clampedInstanceId, f.receiverInstanceId] }
    const validVector = (v: number[]) => Array.isArray(v) && v.length === 3 && v.every(Number.isFinite)
    const duplicate = ids.has(f.id)
    ids.add(f.id)
    if (!f.id || duplicate || !clamped || !receiver || clamped === receiver ||
        !validVector(f.headSeat) || !validVector(f.axis) || new THREE.Vector3(...f.axis).lengthSq() < 1e-12 ||
        ![f.lengthMm, f.shaftDiameterMm, f.minEngagementMm].every(n => Number.isFinite(n) && n > 0) ||
        (f.minWallMm !== undefined && (!Number.isFinite(f.minWallMm) || f.minWallMm < 0)) ||
        (f.tipLengthMm !== undefined && (!Number.isFinite(f.tipLengthMm) || f.tipLengthMm < 0 || f.tipLengthMm >= f.lengthMm)) || manifest.units !== 'mm') {
      return { ...base, status: 'fail', label: `${f.id}: invalid fastening declaration (requires distinct existing parts, mm units, finite positive dimensions)` }
    }
    const origin = new THREE.Vector3(...f.headSeat).applyMatrix4(clamped.matrix)
    const axis = new THREE.Vector3(...f.axis).transformDirection(clamped.matrix)
    const u = new THREE.Vector3().crossVectors(axis, Math.abs(axis.z) < .9 ? new THREE.Vector3(0, 0, 1) : new THREE.Vector3(0, 1, 0)).normalize()
    const v = new THREE.Vector3().crossVectors(axis, u)
    const inside = (part: InstanceGeometry, z: number, radius: number, angle: number) => {
      const p = origin.clone().addScaledVector(axis, z).addScaledVector(u, radius * Math.cos(angle)).addScaledVector(v, radius * Math.sin(angle))
      return pointInside(part.mesh.bvh, p.applyMatrix4(part.inverse))
    }
    const ring = (part: InstanceGeometry, z: number, radius: number) =>
      Array.from({ length: 16 }, (_, i) => inside(part, z, radius, i * Math.PI / 8)).every(Boolean)
    const n = Math.ceil(f.lengthMm / .1)
    const step = f.lengthMm / n
    let run = 0, longest = 0, blocked = false
    for (let i = 0; i < n; i++) {
      const z = (i + .5) * step
      const supported = z < f.lengthMm - (f.tipLengthMm ?? 0) && ring(receiver, z, f.shaftDiameterMm / 2 - .05) &&
        ring(receiver, z, f.shaftDiameterMm / 2 + (f.minWallMm ?? .5))
      run = supported ? run + step : 0
      longest = Math.max(longest, run)
      if (inside(clamped, z, 0, 0) || Array.from({ length: 8 }, (_, j) => inside(clamped, z, f.shaftDiameterMm / 2 - .05, j * Math.PI / 4)).some(Boolean)) blocked = true
    }
    const seated = ring(clamped, .1, f.shaftDiameterMm / 2 + .4)
    const failures = [longest + 1e-6 < f.minEngagementMm ? 'insufficient receiving material' : '', blocked ? 'clamped-part shaft path blocked' : '', !seated ? 'head seat unsupported' : ''].filter(Boolean)
    return { ...base, status: failures.length ? 'fail' : 'pass', point: origin.toArray() as [number, number, number],
      line: { from: origin.toArray() as [number, number, number], to: origin.clone().addScaledVector(axis, f.lengthMm).toArray() as [number, number, number] },
      label: `${f.id}: ${f.clampedInstanceId} → ${f.receiverInstanceId}; ${longest.toFixed(2)} mm continuous engagement / ${f.minEngagementMm} mm required; ${f.lengthMm} mm screw${failures.length ? '; ' + failures.join('; ') : '; sampled seat and clearance pass'}` }
  })
}
