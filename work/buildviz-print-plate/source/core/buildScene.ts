export type Vec3 = [number, number, number]

export type PrimitiveMesh =
  | {
      kind: 'box'
      size: Vec3
    }
  | {
      kind: 'cylinder'
      radius: number
      depth: number
      radialSegments?: number
    }

export type BuildMesh = {
  id: string
  name: string
  url?: string
  primitive?: PrimitiveMesh
}

export type BuildInstance = {
  id: string
  meshId: string
  /** Optional mesh in its intended print orientation; included in meshes for asset upload. */
  printMeshId?: string
  cots?: boolean
  name: string
  partType: string
  role: string
  color: string
  transform: number[]
  centroid?: Vec3
  leg?: string | null
  joint?: string | null
  focusGroup?: string
}

export type CheckStatus = 'pass' | 'warn' | 'fail'

// Generic, project-agnostic check kinds. The viewer renders whatever kinds the
// scene declares; new kinds need no viewer change. These four are the built-in
// generic ones (see plans/validation.md).
export type CheckKind =
  | 'mesh_overlap'
  | 'clearance'
  | 'placement'
  | 'scene_meta'
  | 'connectivity'
  // Printability (offline gate): robust topology + heuristic wall thickness +
  // robust triangle self-intersection.
  | 'watertight'
  | 'wall_thickness'
  | 'degenerate_geometry'
  | 'self_intersection'
  // Per UNIQUE mesh: more than one disjoint welded-vertex body (a floating
  // island / detached ring). INTRA-mesh, distinct from inter-part connectivity.
  | 'disconnected_components'
  // Audit of each checksConfig.allowedInterferences entry: the declared
  // interference must exist in the geometry (present, or at least in contact)
  // and stay within its maxPenetrationMm cap; stale or dangling entries fail.
  | 'declared_interference'
  // Assembleability (offline gate): fastener grip + insertion access (heuristic),
  // mating-face contact tolerance (robust), cable/harness routing reach (heuristic).
  | 'thread_engagement'
  | 'assembly_access'
  | 'mating_contact'
  | 'routing_reach'
  // Wiring rules on routes[] (plans/wiring.md): sampled bend radius vs the
  // allowed minimum, span-between-anchors support spacing, and wire-to-solid
  // clearance (chafing). All no-ops for scenes without routes.
  | 'wire_bend_radius'
  | 'wire_support'
  | 'wire_clearance'
  // Motion (Phase 3): worst-case interference / closest approach found while a
  // mechanism is swept through its joint range or named poses (see §8 + the
  // joints/poses schema below).
  | 'swept_overlap'
  | 'swept_clearance'

// A single validation finding, intentionally minimal: kind + status + label +
// involved instances + an optional geometry anchor for highlighting. Produced by
// the viewer (live) and/or a project's offline verifier (written into the scene
// or a `buildviz_checks.json` sidecar).
export type SceneCheck = {
  id: string
  kind: CheckKind | string
  status: CheckStatus
  label: string
  instances?: string[]
  point?: Vec3
  line?: { from: Vec3; to: Vec3 }
  region?: { min: Vec3; max: Vec3 }
}

// Why a specific interference is intentional. Typed so intent stays auditable:
// every allowed overlap names a real mechanical feature, not just "ignore this".
export type AllowedInterferenceKind =
  | 'thread_engagement' // screw/pin thread deliberately cutting into a pilot hole
  | 'press_fit' // static interference fit (bushing, dowel, bearing outer race)
  | 'bearing_seat' // bearing/collar seated in a bore
  | 'heat_set_insert' // insert melted into a boss
  | 'glue_joint' // bonded faces modeled with slight interference
  | 'wire_entry' // wire/cable entering a connector or housing
  | 'modeled_union' // cosmetic/decorative parts modeled sunk into a host

// One intentional interference, declared at the INSTANCE level (not partType):
// exactly two named instances, a typed mechanical kind, and a human reason. This
// replaces the legacy `ignoreOverlapPairs` blanket: a broad partType ignore
// suppresses every collision between those types — including physically
// impossible ones — while an entry here allows exactly one documented feature.
export type AllowedInterference = {
  kind: AllowedInterferenceKind
  /** The two instance ids allowed to interpenetrate (order-independent). */
  instances: [string, string]
  /** Required: why this interference is intentional
   *  ("M2 self-tapping screw cuts into pilot hole"). */
  reason: string
  /** Optional feature label for audit ("left-front rocker anchor M2 pilot"). */
  feature?: string
  /** Optional cap (mm): a deeper penetration than this still FAILS. Declaring it
   *  makes the allowance self-checking — a part that drifts deeper is caught. */
  maxPenetrationMm?: number
}

// The decision for one overlapping instance pair: whether it is allowed, by
// which mechanism, and — when an allowance matched but was refused — why.
export type OverlapAllowance = {
  allowed: boolean
  /** 'declared' = a typed allowedInterferences entry; 'legacy' = the blanket
   *  ignoreOverlapPairs partType list; null = nothing matched. */
  source: 'declared' | 'legacy' | null
  kind?: AllowedInterferenceKind
  reason?: string
  maxPenetrationMm?: number
  /** Set when an allowance matched but was refused:
   *  - 'max_penetration_exceeded': deeper than the entry's declared cap.
   *  - 'relative_motion': a legacy partType ignore matched, but the two parts
   *    move relative to each other (per joints[]) — moving printed bodies are
   *    never globally ignorable; declare a typed entry or fix the overlap. */
  refusal?: 'max_penetration_exceeded' | 'relative_motion'
}

/**
 * instanceId → motion-group key derived from joints[]. Instances moved by the
 * same joint (the link distal to it) share a key and move rigidly together;
 * instances moved by different joints — or a moved instance vs a static one
 * (absent from the map) — can move relative to each other. Used to refuse
 * legacy blanket ignores between parts in relative motion.
 */
export const jointMotionGroups = (joints: Joint[] | undefined): Map<string, string> => {
  const groups = new Map<string, string>()
  for (const joint of joints ?? []) {
    for (const instanceId of joint.instances) {
      const previous = groups.get(instanceId)
      groups.set(instanceId, previous ? `${previous}+${joint.id}` : joint.id)
    }
  }
  return groups
}

/**
 * Decide whether an overlap between two specific instances is intentional.
 * Precedence: a typed instance-level `allowedInterferences` entry wins (with its
 * optional maxPenetrationMm cap enforced); otherwise the legacy partType-level
 * `ignoreOverlapPairs` applies, but ONLY between parts with no relative motion —
 * two bodies a joint moves against each other are never blanket-ignorable.
 */
export const resolveOverlapAllowance = (
  config: ChecksConfig | undefined,
  a: { instanceId: string; partType: string },
  b: { instanceId: string; partType: string },
  penetrationMm: number,
  motionGroups?: Map<string, string>,
): OverlapAllowance => {
  const declared = (config?.allowedInterferences ?? []).find((entry) => {
    const [x, y] = entry.instances
    return (
      (x === a.instanceId && y === b.instanceId) || (x === b.instanceId && y === a.instanceId)
    )
  })
  if (declared) {
    const base = {
      source: 'declared' as const,
      kind: declared.kind,
      reason: declared.reason,
      ...(declared.maxPenetrationMm !== undefined
        ? { maxPenetrationMm: declared.maxPenetrationMm }
        : {}),
    }
    if (declared.maxPenetrationMm !== undefined && penetrationMm > declared.maxPenetrationMm) {
      return { allowed: false, ...base, refusal: 'max_penetration_exceeded' }
    }
    return { allowed: true, ...base }
  }

  const legacyMatch = (config?.ignoreOverlapPairs ?? []).some(
    ([x, y]) =>
      (x === a.partType && y === b.partType) || (x === b.partType && y === a.partType),
  )
  if (!legacyMatch) return { allowed: false, source: null }
  const groupA = motionGroups?.get(a.instanceId) ?? null
  const groupB = motionGroups?.get(b.instanceId) ?? null
  if (groupA !== groupB) return { allowed: false, source: 'legacy', refusal: 'relative_motion' }
  return { allowed: true, source: 'legacy' }
}

// Project intent expressed as DATA, not code (roadmap §6). Lets a generic engine
// know a project's tolerances and which interferences are intended.
export type ChecksConfig = {
  /** Overlap volume tolerance (mm³) for the offline estimator. */
  overlapMm3?: number
  /** Minimum air-gap (mm) for the clearance check. */
  clearanceMm?: number
  /** Sampling pitch (mm) for the offline overlap estimator. */
  pitchMm?: number
  /** Surface separation (mm) treated as "in contact" for connectivity. */
  toleranceMm?: number
  /** Penetration depth (mm) at/above which an overlap is reported. */
  minPenetrationMm?: number
  /** Min wall thickness (mm) for the printability `wall_thickness` check. */
  minWallMm?: number
  /** Min fastener engagement / grip (mm) for the `thread_engagement` check. */
  minThreadEngagementMm?: number
  /** Allowed gap/overlap (mm) for the `mating_contact` check: a mating pair is
   *  "in contact" when its gap AND penetration stay within this, else it floats
   *  apart / crashes. Defaults to a tight 0.2mm. */
  matingToleranceMm?: number
  /** Intentional interferences, declared per INSTANCE pair with a typed kind, a
   *  required reason, and an optional maxPenetrationMm cap (see
   *  AllowedInterference). The preferred way to allow an overlap: each entry
   *  covers exactly one documented feature and is itself audited by the
   *  `declared_interference` check (stale/absent/over-cap entries fail). */
  allowedInterferences?: AllowedInterference[]
  /** LEGACY blanket ignore: intentional overlaps / press-fits by partType pair.
   *  Too broad — it suppresses EVERY collision between those types, including
   *  physically impossible ones — so prefer `allowedInterferences`. Still
   *  honored for parts with no relative motion (and still treated as DECLARED
   *  mating pairs by the `mating_contact` gate), but REFUSED between parts that
   *  joints[] move relative to each other, and every check run emits a warn
   *  while this list is non-empty.
   *  Example: [["spider_eye", "spider_carapace"], ["bushing", "housing"]]. */
  ignoreOverlapPairs?: Array<[string, string]>
  /** Per-mesh expected disjoint body count, keyed by mesh.id, for the
   *  `disconnected_components` check. A legitimately multi-body mesh (a captive-
   *  nut block, a pre-split clamp) declares its count here so it is not
   *  false-failed. Intent as DATA, like `ignoreOverlapPairs`. */
  expectedMeshComponents?: Record<string, number>
  /** Global default expected disjoint body count for any mesh without a
   *  per-mesh `expectedMeshComponents` entry. Defaults to 1 when omitted. */
  maxMeshComponents?: number
  /** Min air gap (mm) between a wire's surface and a non-termination solid
   *  before `wire_clearance` warns (chafing risk). Defaults to 1mm. */
  wireClearanceMm?: number
  /** Default longest allowed span between wire anchors (mm) before
   *  `wire_support` warns; per-route maxUnsupportedMm overrides. Default 150. */
  maxUnsupportedMm?: number
  /** Mass properties: KNOWN real-world masses (grams) by partType — e.g. a
   *  bought servo, battery, or PCB whose mass geometry can't derive. Beats any
   *  density-based estimate. Example: { "hip_servo": 137, "lipo_battery": 260 }. */
  partMassesGrams?: Record<string, number>
  /** Material density (g/cm³) overrides by partType, for parts whose mass IS
   *  derived from mesh volume. Example: { "chassis_top": 1.04 } for ABS. */
  partDensitiesGCm3?: Record<string, number>
  /** Default density (g/cm³) for parts without a mass/density entry.
   *  Defaults to 1.24 (solid PLA); lower it to model infill. */
  defaultDensityGCm3?: number
  /** Density (g/cm³) for detected fastener meshes. Defaults to 7.85 (steel). */
  fastenerDensityGCm3?: number
}

// ---------------------------------------------------------------------------
// Motion model (Phase 3): additive joints + named poses (roadmap §8). Older
// viewers ignore both top-level keys, so a scene that carries them still renders
// statically everywhere. A producer (the CAD exporter / offline tool) emits this
// because it has the kinematics; BuildViz stays project-agnostic and only drives
// what the data declares.
//
// FRAME CONVENTIONS (forward kinematics)
//  - `axis` and `origin` are expressed in the SCENE/world frame, at the HOME
//    configuration (the static pose every instance.transform already encodes).
//  - For a revolute joint the local transform of value θ (degrees) is
//        L(θ) = T(origin) · R(axis, θ − home) · T(−origin)
//    a world-frame rotation about `axis` through the pivot `origin`. For a
//    prismatic joint of value d (mm) it is L(d) = T(axis · (d − home)).
//  - Joints compose along the chain: the cumulative transform of joint j is
//        C(j) = C(parent(j)) · L(j)        (root-most factor on the LEFT)
//    and every instance listed in joint j (the link DISTAL to it) is rendered at
//        worldMatrix = C(j) · instance.transform
//    So a joint's `instances` list holds ONLY its own distal link; ancestors are
//    applied automatically through the parent chain (e.g. a knee value also
//    inherits the hip + yaw rotations above it).
export type JointType = 'revolute' | 'prismatic'

export type Joint = {
  id: string
  /** revolute → rotates about `axis`; prismatic → slides along `axis`. */
  type: JointType
  /** Unit rotation/slide axis, SCENE frame, at the home configuration. */
  axis: Vec3
  /** A point on the axis (the pivot), SCENE frame, at the home configuration. */
  origin: Vec3
  /** Parent joint id for the kinematic chain; omitted/null = rooted at scene. */
  parent?: string | null
  /** Instance ids of the link DISTAL to this joint (the parts it moves). */
  instances: string[]
  /** Travel limits: degrees for revolute, mm for prismatic. */
  limits?: { min: number; max: number }
  /** Home/rest value (deg or mm); defaults to 0. The static scene is the home. */
  home?: number
  /** Optional human label for the scrubber UI. */
  label?: string
}

// A named/baked pose: explicit joint values (deg/mm) keyed by joint id. Joints
// omitted from `jointValues` stay at their home value. An alternative to driving
// the sliders directly; lets a producer ship discrete configurations to inspect.
export type Pose = {
  id: string
  name: string
  jointValues: Record<string, number>
}

// A single keyframe of a motion clip: the joint values (deg/mm, same units as
// the joints) that hold at time `t` seconds. Values are LINEARLY interpolated
// between adjacent keyframes; joints a keyframe omits fall back to their home.
export type AnimationKeyframe = {
  /** Keyframe time in seconds along the clip. Keyframes SHOULD be sorted. */
  t: number
  /** Joint values (keyed by joint id) that hold at this keyframe. */
  jointValues: Record<string, number>
}

// A time-based motion clip: an ordered list of keyframes the viewer plays back
// with a transport (play/pause + scrubber). This is the additive, backward-
// compatible way to ship a real MOTION (e.g. a walking gait loop) rather than
// the per-DOF envelope sweep the sliders offer. A producer that has the
// kinematics (the CAD exporter) bakes the joint-angle timeline; the viewer just
// samples it over time and drives the same joint values the scrubber does.
// Older viewers ignore `animations` entirely and still render the static scene.
export type Animation = {
  id: string
  /** Human label for the clip selector. */
  name: string
  /** Loop the clip when playback reaches the end. Defaults to true. */
  loop?: boolean
  /** Explicit clip length in seconds. Defaults to the last keyframe's `t`. */
  duration?: number
  /** Ordered keyframes (by ascending `t`). At least one is required. */
  keyframes: AnimationKeyframe[]
}

// One waypoint of a wire/cable route. Either WORLD-frame (`position`) or
// ANCHORED to an instance (`instanceId` + part-local `local`) so the point
// rides with the part through versions and kinematic poses. `anchor: true`
// marks a physical attachment (clip / tie / standoff) — the wire is secured
// there; the `wire_support` check measures spans between anchors. Endpoints
// are always implicit anchors (they terminate at connectors).
export type RoutePoint = {
  /** World-frame position [x,y,z]. Ignored when instanceId is set. */
  position?: Vec3
  /** Anchor this point to an instance: it follows the part's transform. */
  instanceId?: string
  /** Part-local offset for an instance-anchored point (default [0,0,0]). */
  local?: Vec3
  /** Physically secured here (clip/tie). Instance-anchored points and route
   *  endpoints are treated as anchored regardless of this flag. */
  anchor?: boolean
  /** Optional human label ("chassis clip #2"). */
  label?: string
}

// A producer-supplied cable/harness route (additive, optional, ignored by old
// viewers). The path is `waypoints` (rich, instance-anchorable) or the legacy
// world-frame `points` polyline; `waypoints` wins when both are present. The
// wiring checks verify length budget, pass-through obstruction, minimum bend
// radius, support spacing, and clearance. BuildViz does NOT infer routes from
// geometry — a producer that has the harness layout emits them, the same way
// it emits joints[] (see plans/validation.md non-goals and plans/wiring.md).
export type Route = {
  id: string
  /** Legacy ordered world-frame waypoints [x,y,z]. Superseded by `waypoints`. */
  points?: Vec3[]
  /** Preferred path: world or instance-anchored waypoints (see RoutePoint). */
  waypoints?: RoutePoint[]
  /** Bundle outer diameter (mm). Drives rendering thickness and the default
   *  minimum bend radius (6 × OD, per IPC/WHMA-A-620 static routing). */
  diameterMm?: number
  /** Display color (any CSS color). Defaults per `kind`. */
  color?: string
  /** Wire class: 'power' | 'signal' | 'data' | 'ground' | free-form. */
  kind?: string
  /** Minimum allowed bend radius (mm). Default 6 × diameterMm when the
   *  diameter is known; unchecked otherwise. */
  minBendRadiusMm?: number
  /** Optional reach budget (mm); a longer routed length fails the gate. */
  maxLengthMm?: number
  /** Longest allowed span between anchors (mm) before the `wire_support`
   *  check asks for a clip/tie. Default checksConfig.maxUnsupportedMm / 150. */
  maxUnsupportedMm?: number
  /** Optional instance ids the route connects (terminations); these are not
   *  treated as obstructions when a segment legitimately enters them.
   *  Instance-anchored waypoints are added to this set automatically. */
  instances?: string[]
  /** Optional human label for the check/UI. */
  label?: string
}

// The scene-manifest schema version this build of BuildViz authors and fully
// understands. Optional in the manifest (old scenes without it still load); a
// producer SHOULD stamp it so `validate` can warn when a scene was written by a
// newer BuildViz than the reader (forward-incompatible risk) or an older one
// (may be missing fields a check expects). Bump only on a breaking/structural
// schema change, NOT for additive optional fields.
export const CURRENT_SCENE_SCHEMA_VERSION = 1

/** Coordinates are in the clamped instance's local frame; lengths are mm. */
export type Fastening = {
  id: string
  clampedInstanceId: string
  receiverInstanceId: string
  headSeat: Vec3
  axis: Vec3
  lengthMm: number
  shaftDiameterMm: number
  minEngagementMm: number
  /** Unthreaded/pointed tip excluded from useful engagement (default 0). */
  tipLengthMm?: number
  /** Material must surround this radius beyond the shaft (default 0.5 mm). */
  minWallMm?: number
}

export type BuildSceneManifest = {
  name: string
  source?: string
  designSpecUrl?: string
  // Optional integer manifest schema version (see CURRENT_SCENE_SCHEMA_VERSION).
  // Additive: scenes without it still load and render everywhere; `validate`
  // warns for an unknown (newer) or old (lower) version. Recorded verbatim by
  // the hub's assertSceneManifest on push.
  schemaVersion?: number
  // Optional prefix for RELATIVE mesh URLs, resolved by the viewer at load time
  // (absolute http(s) and `/`-rooted URLs pass through untouched). Makes a scene
  // self-describing about where its assets live, so the same relative-URL build
  // renders under the hub, static hosting, and inside a versions/<name>/ dir
  // without a symlink hack. See plans/versioning.md (a).
  assetsBaseUrl?: string
  units: 'mm' | 'cm' | 'm'
  center: Vec3
  meshes: BuildMesh[]
  instances: BuildInstance[]
  fastenings?: Fastening[]
  // Additive, optional, ignored by older viewers (roadmap §3).
  checks?: SceneCheck[]
  checksConfig?: ChecksConfig
  // Additive motion model, optional, ignored by older viewers (roadmap §8).
  joints?: Joint[]
  poses?: Pose[]
  // Additive time-based motion clips (keyframed joint timelines), optional,
  // ignored by older viewers. Played back by the Motion panel's transport.
  animations?: Animation[]
  // Additive cable/harness routes for the routing_reach gate (roadmap §10).
  routes?: Route[]
}

const transform = (x: number, y: number, z: number, rz = 0) => {
  const cos = Math.cos(rz)
  const sin = Math.sin(rz)

  return [cos, sin, 0, 0, -sin, cos, 0, 0, 0, 0, 1, 0, x, y, z, 1]
}

export const sampleScene: BuildSceneManifest = {
  name: 'Hexapod build sample',
  units: 'mm',
  center: [0, 0, 0],
  meshes: [
    {
      id: 'chassis',
      name: 'Chassis plate',
      primitive: { kind: 'box', size: [90, 58, 5] },
    },
    {
      id: 'leg-link',
      name: 'Leg link',
      primitive: { kind: 'box', size: [52, 10, 8] },
    },
    {
      id: 'servo',
      name: 'Servo proxy',
      primitive: { kind: 'box', size: [24, 13, 24] },
    },
    {
      id: 'fastener',
      name: 'Socket head screw',
      primitive: { kind: 'cylinder', radius: 2.4, depth: 12, radialSegments: 24 },
    },
  ],
  instances: [
    {
      id: 'chassis-top',
      meshId: 'chassis',
      name: 'Chassis top',
      partType: 'chassis_top',
      role: 'top structural chassis plate',
      color: '#9ca3af',
      transform: transform(0, 0, 10),
      focusGroup: 'chassis',
    },
    {
      id: 'chassis-bottom',
      meshId: 'chassis',
      name: 'Chassis bottom',
      partType: 'chassis_bottom',
      role: 'bottom structural chassis plate',
      color: '#6b7280',
      transform: transform(0, 0, 0),
      focusGroup: 'chassis',
    },
    ...Array.from({ length: 6 }, (_, index) => {
      const angle = (Math.PI * 2 * index) / 6
      const x = Math.cos(angle) * 54
      const y = Math.sin(angle) * 38
      const leg = `L${index}`

      return [
        {
          id: `servo-${leg}`,
          meshId: 'servo',
          name: `Hip servo ${leg}`,
          partType: 'servo_body',
          role: `hip servo body ${leg}`,
          color: '#2563eb',
          transform: transform(x * 0.72, y * 0.72, 18, angle),
          focusGroup: leg,
        },
        {
          id: `coxa-${leg}`,
          meshId: 'leg-link',
          name: `Coxa link ${leg}`,
          partType: 'coxa_link',
          role: `coxa link ${leg}`,
          color: '#f97316',
          transform: transform(x, y, 8, angle),
          focusGroup: leg,
        },
        {
          id: `femur-${leg}`,
          meshId: 'leg-link',
          name: `Femur link ${leg}`,
          partType: 'femur_link',
          role: `femur link ${leg}`,
          color: '#22c55e',
          transform: transform(x * 1.42, y * 1.42, -4, angle),
          focusGroup: leg,
        },
        {
          id: `fastener-${leg}`,
          meshId: 'fastener',
          name: `Hip fastener ${leg}`,
          partType: 'M3x8 SHCS',
          role: `coxa link ${leg} hip cradle fastener`,
          color: '#111827',
          transform: transform(x * 0.84, y * 0.84, 18, angle),
          focusGroup: leg,
        },
      ]
    }).flat(),
  ],
}
