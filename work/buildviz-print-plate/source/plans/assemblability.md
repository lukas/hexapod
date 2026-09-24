# Assemblability (swept insertion-path) — PROPOSED

Backing detail for the "Swept-path assemblability" item in
[`../ROADMAP.md`](../ROADMAP.md). **Status: proposed / not yet implemented.**

Catch parts that are *geometrically valid but physically impossible to assemble* —
the failure class where the seated state is collision-free yet no collision-free
*path* gets the part there. Three real past failures motivate it: a Ø37 bearing
race trapped behind a Ø34 neck (captured pocket), an over-closed servo cradle
mouth, and a Ø20 disc horn given a Ø10 clearance hole.

It builds on (and folds in) the validation architecture in
[`validation.md`](validation.md) — "verifier gates, viewer surfaces", additive
`scene.checks`/`checksConfig`, the project-agnostic engine — and **supersedes** the
coarse `assembly_access` AABB-shadow sweep (which stays a warn-only pre-filter).

> The human-in-the-loop *viewer* counterparts to this gate (clipping/section planes,
> overlap-volume highlighting, exploded/insertion preview) are tracked under
> "Viewer features that would eliminate manual diagnostic rendering" in
> [`../ROADMAP.md`](../ROADMAP.md) — they surface what this check computes.

## Why it's deferred

- **No scene emits the required data.** It needs new additive producer-side schema
  (`instance.insert`, `instance.cots`, `checksConfig.requiredParts`); the bundled
  scenes carry none of it, and even the hexapod scene ships **zero** horn
  instances. There is nothing to validate until a consumer declares insertable COTS
  parts with their insertion axes/seats.
- **The exact-CAD authority already exists project-side.** The canonical checks
  (`check_bearing_insertion_path`, `check_servo_insertion_path`,
  `check_disc_horn_fit`) live in the hexapod's `_verify_prototype.py` and remain
  the hard gate. This plan generalizes their *idea* into a project-agnostic engine
  + scene contract — valuable, but large, and only once a scene needs it.
- It's a sizeable engine addition (a swept voxel/SDF feasibility primitive) best
  scheduled deliberately, not folded into a docs-consolidation pass.

## Why static collision-freedom ≠ assemblability

Every existing check evaluates a single configuration (or sampled *posed*
configurations via `joints[]`/`poses[]`) — a **static** question even when swept,
because parts are already in their final relative positions. Assembly is a **path**
question: is there a continuous, collision-free motion of part P from "clear of
host H" to "seated in H"?

| Question | Existing check | Catches captured pocket? |
| --- | --- | --- |
| Does the seated state interpenetrate? | `mesh_overlap` | ❌ seated state is clean |
| Does any *pose* in joint motion clash? | `swept_overlap` | ❌ not an insertion motion |
| Is the part's *AABB* boxed in? | `assembly_access` (coarse) | ❌ AABB ignores the bore neck |
| Is there a collision-free *insertion path* for the part's real geometry? | `insertion_path` (this plan) | ✅ |

## The primitive: swept insertion-path feasibility

Given an insertable part P (COTS/press/insert) and the printed host(s) H:

1. Resolve declared insertion intent (schema below): an `axis` (unit vector, scene
   frame), a `seat` point, an `approachMm` start offset, optional
   `rotationRangeDeg` (horns/gears), and a per-part `toleranceMm3` budget.
2. Take P's rigid geometry (real STL, or a primitive envelope — a Ø37 race is a
   Ø37 disc; an envelope is conservative for convex parts, the safe direction for a
   gate). Derive H (declared via `into`, or printed instances whose AABB the swept
   corridor crosses).
3. Step P along the axis from clear start to seat in `zStepMm` increments (default
   0.5mm). At each station, voxel/SDF-overlap P against each host
   (point-in-mesh via the cached BVH ray-parity test): `overlap_mm³ = points_inside × pitch³`.
4. **Verdict:** feasible iff every station's overlap ≤ `toleranceMm3`, *except* the
   final seated contact — stop one step above the seat plane so the intended seated
   overlap isn't mistaken for a blockage. Report the worst station + a localized
   region for shading.
5. **Rotation (horns/gears):** with `rotationRangeDeg` set, after seating sweep P
   through its rotation range about `axis` and apply the same overlap test (for a
   circular disc this degenerates to the static seated disc).

A small per-step volume tolerance (default 25 mm³, calibrated against the project
verifier: <1 mm³ grazing on a good slip fit, ~79 mm³ on the captured tower) absorbs
grid quantization while still catching a real constriction. Cost: only *insertable*
parts are swept (a handful per scene); sub-second per part at 0.5mm.

## Scene schema additions (all additive, optional)

```jsonc
// BuildInstance — present ⇒ this instance is swept for insertion feasibility
"insert": {
  "axis": [0, 0, 1],            // unit insertion axis, SCENE frame
  "seat": [42, 0, -1],          // origin rest point when seated (defaults to seated centroid)
  "approachMm": 8,              // start this far back along −axis (clear of H)
  "into": ["chassis_bottom-L0"],// host instance ids (optional; auto-derived if omitted)
  "rotationRangeDeg": null,     // [min,max] for horns/gears; null = pure insert
  "toleranceMm3": 25,           // per-step overlap budget
  "fit": "slip"                 // "slip" | "press" (press allows a small interference band)
},
"cots": "bearing"               // "bearing"|"servo"|"horn"|"insert"|"fastener"|"gear"|string

// ChecksConfig
"insertionToleranceMm3": 25, "insertionPitchMm": 0.5, "insertionStepMm": 0.5,
"pressInterferenceMm": 0.1,
"requiredParts": {              // completeness: which COTS a joint MUST carry
  "perJoint": { "yaw": ["bearing","servo","horn"], "hip": ["servo","horn"] },
  "global": ["fastener"]
}
```

## New check kinds

- `insertion_path` — swept insertion-path feasibility. `fail` on a blocked path
  (robust with full geometry → a hard gate).
- `rotation_clearance` — horn/gear swept-rotation clearance (`insertion_path` with
  `rotationRangeDeg`); `fail` when the opening < swept diameter.
- `required_parts` — manifest-only completeness: every declared joint must carry its
  named `cots`-tagged instances. `fail` (configurable `warn`). Cheapest, highest
  leverage — it *forces* COTS parts (like the missing horn) into the scene where the
  geometry checks can see them.

`assembly_access` is retained but demoted to a warn-only pre-filter.

## Phased rollout (when picked up)

- **A — completeness + schema.** `instance.insert`/`cots`, `requiredParts`, the
  manifest-only `required_parts` check. Catches the missing-horn case immediately.
- **B — insertion-path engine.** The swept primitive in `src/buildvizGeometry.ts`
  (reuse cached BVHs + point-in-mesh), `insertion_path` records, `--assembly` CLI
  flag. Catches captured pocket + servo cradle.
- **C — rotation clearance + horn specialization.** `rotation_clearance`.
- **D — viewer polish / optional live recompute.** Findings already paint from the
  sidecar; optionally animate the swept part along its axis.
- **E — verifier emits `checks[]`.** Teach the project verifier to write its
  bearing/servo/horn findings into `buildviz_checks.json` so the exact-CAD gate
  paints in the viewer.

## File map

| Piece | Location |
| --- | --- |
| Schema (`insert`, `cots`, `requiredParts`, new `CheckKind`s) | `src/buildScene.ts` |
| `required_parts` (manifest-only) | `src/buildvizChecks.ts` (beside `staticChecks`) |
| Insertion-path + rotation engine | `src/buildvizGeometry.ts` (reuse BVH cache + point-in-mesh) |
| `insertion_path`/`rotation_clearance` records | `src/buildvizChecks.ts` (`geometryChecks`) |
| `--assembly` flag + kind selection | `scripts/buildviz.ts` |
| Panel labels | `src/buildvizChecks.ts` (`CHECK_KIND_LABEL`) |
| Reference exact-CAD impls to port | project verifier (`_verify_prototype.py`) |
