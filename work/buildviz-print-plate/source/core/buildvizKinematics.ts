import * as THREE from 'three'
import type { Animation, BuildSceneManifest, Joint, Pose } from './buildScene'

// Forward kinematics for the additive joints/poses model (BUILDVIZ_VALIDATION_
// ROADMAP.md §8). Pure transform math on top of the static scene: every
// instance.transform is the HOME pose, and a set of joint values produces a
// per-instance WORLD-frame override matrix that the viewer (and the swept
// overlap pass) apply in place of the base transform.
//
// Conventions (see buildScene.ts):
//   L(joint, v) = T(origin)·R(axis, v−home)·T(−origin)   [revolute, deg]
//               = T(axis·(v−home))                       [prismatic, mm]
//   C(j) = C(parent)·L(j)                                [chain composition]
//   worldMatrix(instance ∈ j) = C(j) · instance.transform

export type JointValues = Record<string, number>

export type SweepSample = {
  id: string
  label: string
  jointValues: JointValues
  /** instanceId → column-major 16 world override (already C(j)·base). Missing
   *  instances keep their static base transform. */
  overrides: Record<string, number[]>
}

// Default slider range when a joint omits `limits`: ±45° for a revolute, ±20mm
// for a prismatic. Deliberately modest so an undeclared range stays sane.
const DEFAULT_REVOLUTE_LIMIT = 45
const DEFAULT_PRISMATIC_LIMIT = 20

export const jointRange = (joint: Joint): { min: number; max: number } => {
  if (joint.limits) return joint.limits
  const span = joint.type === 'prismatic' ? DEFAULT_PRISMATIC_LIMIT : DEFAULT_REVOLUTE_LIMIT
  return { min: -span, max: span }
}

export const jointHome = (joint: Joint) => joint.home ?? 0

export const jointUnit = (joint: Joint) => (joint.type === 'prismatic' ? 'mm' : '°')

export const defaultJointValues = (joints: Joint[] | undefined): JointValues => {
  const values: JointValues = {}
  for (const joint of joints ?? []) values[joint.id] = jointHome(joint)
  return values
}

// Resolve a (possibly partial) pose to full joint values, filling omitted joints
// with their home value.
export const resolveJointValues = (
  joints: Joint[] | undefined,
  partial: JointValues | undefined,
): JointValues => {
  const values = defaultJointValues(joints)
  if (partial) {
    for (const [id, value] of Object.entries(partial)) values[id] = value
  }
  return values
}

// Local world-frame transform L(joint, value).
const localJointMatrix = (joint: Joint, value: number): THREE.Matrix4 => {
  const delta = value - jointHome(joint)
  const axis = new THREE.Vector3(joint.axis[0], joint.axis[1], joint.axis[2])
  if (axis.lengthSq() < 1e-12) return new THREE.Matrix4()
  axis.normalize()

  if (joint.type === 'prismatic') {
    return new THREE.Matrix4().makeTranslation(axis.x * delta, axis.y * delta, axis.z * delta)
  }

  const rad = THREE.MathUtils.degToRad(delta)
  const rot = new THREE.Matrix4().makeRotationAxis(axis, rad)
  const p = joint.origin
  const toPivot = new THREE.Matrix4().makeTranslation(p[0], p[1], p[2])
  const fromPivot = new THREE.Matrix4().makeTranslation(-p[0], -p[1], -p[2])
  // T(p) · R · T(−p)
  return toPivot.multiply(rot).multiply(fromPivot)
}

// Topologically order joints so parents precede children. Cycles / missing
// parents are tolerated (treated as roots) so a malformed chain never hangs.
const orderedJoints = (joints: Joint[]): Joint[] => {
  const byId = new Map(joints.map((joint) => [joint.id, joint]))
  const ordered: Joint[] = []
  const visited = new Set<string>()
  const inStack = new Set<string>()

  const visit = (joint: Joint) => {
    if (visited.has(joint.id)) return
    if (inStack.has(joint.id)) return // cycle guard
    inStack.add(joint.id)
    const parent = joint.parent ? byId.get(joint.parent) : undefined
    if (parent) visit(parent)
    inStack.delete(joint.id)
    visited.add(joint.id)
    ordered.push(joint)
  }

  for (const joint of joints) visit(joint)
  return ordered
}

// Cumulative world transform C(j) per joint id for a set of joint values.
export const jointCumulativeMatrices = (
  joints: Joint[],
  values: JointValues,
): Map<string, THREE.Matrix4> => {
  const cumulative = new Map<string, THREE.Matrix4>()
  for (const joint of orderedJoints(joints)) {
    const local = localJointMatrix(joint, values[joint.id] ?? jointHome(joint))
    const parent = joint.parent ? cumulative.get(joint.parent) : undefined
    const matrix = parent ? parent.clone().multiply(local) : local
    cumulative.set(joint.id, matrix)
  }
  return cumulative
}

// Per-instance world override matrices for a pose. Only instances that some
// joint moves appear in the map; everything else stays at its base transform.
// The most-distal joint that lists an instance wins (later in chain order).
export const poseInstanceMatrices = (
  manifest: BuildSceneManifest,
  values: JointValues,
): Map<string, THREE.Matrix4> => {
  const joints = manifest.joints ?? []
  if (joints.length === 0) return new Map()
  const cumulative = jointCumulativeMatrices(joints, values)
  const baseById = new Map(manifest.instances.map((instance) => [instance.id, instance.transform]))

  const overrides = new Map<string, THREE.Matrix4>()
  // Iterate in chain order so a more-distal joint overrides a proximal one if a
  // (malformed) scene lists the same instance twice.
  for (const joint of orderedJoints(joints)) {
    const cj = cumulative.get(joint.id)
    if (!cj) continue
    for (const instanceId of joint.instances) {
      const base = baseById.get(instanceId)
      if (!base) continue
      overrides.set(instanceId, cj.clone().multiply(new THREE.Matrix4().fromArray(base)))
    }
  }
  return overrides
}

// Same as poseInstanceMatrices but serialized to plain column-major arrays, so
// the result can cross the THREE-free boundary into the swept-overlap engine.
export const poseInstanceArrays = (
  manifest: BuildSceneManifest,
  values: JointValues,
): Record<string, number[]> => {
  const out: Record<string, number[]> = {}
  for (const [id, matrix] of poseInstanceMatrices(manifest, values)) {
    out[id] = matrix.toArray()
  }
  return out
}

export type SweepOptions = {
  /** Samples per joint across its range (others held at home). Default 8. */
  samplesPerJoint?: number
  /** Include the scene's named poses as additional samples. Default true. */
  includePoses?: boolean
  /** Restrict the sweep to joints that move at least one of these instance ids
   *  (the visible/focused subset). Undefined = sweep every joint. */
  scopeInstanceIds?: Set<string>
}

const DEFAULT_SAMPLES_PER_JOINT = 8

// Build the list of poses to evaluate. The default strategy is a per-DOF
// "workspace sweep": each joint is stepped across its range while the others
// stay home (the classic mechanism envelope), plus the scene's named poses.
// This is linear in joints×samples rather than the exponential full cross
// product, and is what keeps a sweep interactive.
export const buildSweepSamples = (
  manifest: BuildSceneManifest,
  options: SweepOptions = {},
): SweepSample[] => {
  const joints = manifest.joints ?? []
  if (joints.length === 0) return []
  const samplesPerJoint = Math.max(2, options.samplesPerJoint ?? DEFAULT_SAMPLES_PER_JOINT)
  const includePoses = options.includePoses ?? true
  const scope = options.scopeInstanceIds

  const inScope = (joint: Joint) =>
    !scope || joint.instances.some((instanceId) => scope.has(instanceId))
  const home = defaultJointValues(joints)

  const samples: SweepSample[] = []
  const seen = new Set<string>()
  const pushSample = (id: string, label: string, values: JointValues) => {
    if (seen.has(id)) return
    seen.add(id)
    samples.push({ id, label, jointValues: values, overrides: poseInstanceArrays(manifest, values) })
  }

  // Home pose is always the first sample (the static scene).
  pushSample('home', 'home', home)

  for (const joint of joints) {
    if (!inScope(joint)) continue
    const range = jointRange(joint)
    for (let i = 0; i < samplesPerJoint; i += 1) {
      const t = i / (samplesPerJoint - 1)
      const value = range.min + (range.max - range.min) * t
      if (Math.abs(value - jointHome(joint)) < 1e-6) continue
      const values = { ...home, [joint.id]: value }
      const unit = jointUnit(joint)
      pushSample(
        `${joint.id}@${value.toFixed(1)}`,
        `${joint.label ?? joint.id} = ${value.toFixed(0)}${unit}`,
        values,
      )
    }
  }

  if (includePoses) {
    for (const pose of manifest.poses ?? []) {
      const values = resolveJointValues(joints, pose.jointValues)
      // Skip poses that move nothing in scope.
      if (scope) {
        const movesScoped = joints.some(
          (joint) => inScope(joint) && (values[joint.id] ?? 0) !== jointHome(joint),
        )
        if (!movesScoped) continue
      }
      pushSample(`pose:${pose.id}`, `pose: ${pose.name}`, values)
    }
  }

  return samples
}

export const poseLabel = (pose: Pose) => pose.name || pose.id

// ---------------------------------------------------------------------------
// Time-based motion clips (animations[]). A clip is an ordered list of
// keyframes; the viewer samples it over time to drive the same joint values the
// scrubber does, so playback reuses the whole FK path (poseInstanceMatrices).

// Clip length in seconds: an explicit `duration`, else the last keyframe's `t`.
export const animationDuration = (animation: Animation): number => {
  if (typeof animation.duration === 'number' && animation.duration > 0) {
    return animation.duration
  }
  const frames = animation.keyframes
  if (!frames || frames.length === 0) return 0
  return Math.max(0, frames[frames.length - 1].t)
}

// Sample a clip at `timeSec`, returning full joint values (home-filled) with a
// linear blend between the two surrounding keyframes. `timeSec` is assumed to
// already be wrapped/clamped by the caller to [0, duration].
export const sampleAnimation = (
  joints: Joint[] | undefined,
  animation: Animation | undefined,
  timeSec: number,
): JointValues => {
  const base = defaultJointValues(joints)
  const frames = animation?.keyframes
  if (!frames || frames.length === 0) return base

  // Clamp outside the keyframe span (callers handle looping before this).
  if (timeSec <= frames[0].t) return { ...base, ...frames[0].jointValues }
  const last = frames[frames.length - 1]
  if (timeSec >= last.t) return { ...base, ...last.jointValues }

  // Find the bracketing keyframes [a, b] with a.t <= timeSec < b.t.
  let hi = 1
  while (hi < frames.length && frames[hi].t <= timeSec) hi += 1
  const a = frames[hi - 1]
  const b = frames[hi]
  const span = b.t - a.t
  const alpha = span > 1e-9 ? (timeSec - a.t) / span : 0

  const values: JointValues = { ...base }
  // Blend every joint the clip touches; a joint missing from either side of the
  // bracket falls back to its home value on that side (so partial keyframes are
  // treated as "return to home" for the omitted joints).
  const touched = new Set<string>([...Object.keys(a.jointValues), ...Object.keys(b.jointValues)])
  for (const id of touched) {
    const home = base[id] ?? 0
    const va = a.jointValues[id] ?? home
    const vb = b.jointValues[id] ?? home
    values[id] = va + (vb - va) * alpha
  }
  return values
}
