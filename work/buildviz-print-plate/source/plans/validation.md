# Validation — architecture & detail

Backing detail for the Validation section of [`../ROADMAP.md`](../ROADMAP.md).
Covers the validation thesis/architecture (shipped), the check kinds, and the
`disconnected_components` guard (shipped). The swept-path assemblability family
has its own doc: [`assemblability.md`](assemblability.md).

## 1. Thesis: "verifier gates, viewer surfaces" (shipped)

A project's offline verifier stays the hard merge/release gate, but spatial facts
("does A poke into B?", "is this placed sanely?", "can this be assembled?")
should also be **surfaced** in the viewer, and BuildViz should run a useful
*project-agnostic* subset itself, with zero per-project code.

- **Split checks by nature, not tool.** Hard correctness gates that need exact
  geometry (watertightness, thread engagement, mating contact, wall thickness,
  self-intersection, routing reach) run offline in `buildviz check`. "Is this
  placed sanely / does it interpenetrate" checks are surfaced as overlays a human
  can rotate and triage, and the cheap ones run live the moment a scene loads.
- **Findings are data.** The verifier (or the live viewer) emits minimal
  `checks[]` records — `{ id, kind, status, label, instances?, point?/line?/region? }`
  — into `scene.checks` or a `buildviz_checks.json` sidecar; the viewer paints
  whatever kinds the scene declares (new kinds need no viewer change).
- **Intent is data, not code** — `checksConfig` (`overlapMm3`, `clearanceMm`,
  `minPenetrationMm`, `minWallMm`, `minThreadEngagementMm`, `matingToleranceMm`,
  `allowedInterferences`, legacy `ignoreOverlapPairs`,
  `expectedMeshComponents`/`maxMeshComponents`). This is how a project declares
  its tolerances and intended interferences without making BuildViz
  project-specific. Intended interferences are TYPED and INSTANCE-level
  (`allowedInterferences`: kind + instance pair + reason + optional
  `maxPenetrationMm` cap, audited by the `declared_interference` gate); the
  partType-level `ignoreOverlapPairs` blanket is a legacy escape hatch that
  warns on every run and never applies to parts in relative motion (joints[]).

This is all built: additive `scene.checks`/`checksConfig` schema
(`src/buildScene.ts`), the generic check engine (`src/buildvizGeometry.ts`,
`src/buildvizChecks.ts`), the Checks panel (`src/ChecksPanel.tsx`), the
`buildviz check` CLI, and live in-browser recompute via three-mesh-bvh.

## 2. Shipped check kinds (summary)

| Kind | Group | Robust/Heuristic | Status |
| --- | --- | --- | --- |
| `mesh_overlap` | spatial | robust (interior-grid penetration) | `fail`/`pass (allowed)` |
| `clearance` | spatial | robust | `warn` |
| `connectivity` (inter-part) | spatial | robust | `warn` |
| `placement` / `scene_meta` | manifest | robust | `fail`/`pass` |
| `watertight` / `degenerate_geometry` | printability | robust | `fail`/`warn` |
| `self_intersection` | printability | robust (tri–tri SAT) | `fail` |
| `disconnected_components` | printability | robust (weld + union-find) | `fail` |
| `wall_thickness` | printability | heuristic (inward-ray percentile) | `warn` |
| `thread_engagement` | assembleability | heuristic | `warn` |
| `assembly_access` | assembleability | coarse heuristic (opt-in `--access`) | `warn` |
| `mating_contact` | assembleability | robust | `fail` |
| `routing_reach` | assembleability | heuristic (schema-first `routes[]`) | `fail` |
| `swept_overlap` / `swept_clearance` | motion | robust per pose | `fail`/`warn` |

Performance: each unique mesh is BVH-indexed once and reused across instances and
poses; a sweep-and-prune AABB broad phase + BVH narrow phase keeps the largest
bundled build (~674 instances) at a couple of seconds, and per-pose sweeps reuse
the same cached BVHs (no rebuilds).

## 3. Motion (Phase 3, shipped)

Additive `joints[]`/`poses[]` block → forward kinematics
(`src/buildvizKinematics.ts`) → Motion scrubber (`src/MotionPanel.tsx`) → per-pose
overlap re-evaluation (`sweepOverlaps` in `src/buildvizGeometry.ts`) →
`swept_overlap`/`swept_clearance` records labeled with the worst pose. Headless via
`buildviz sweep`. The remaining dependency is **producer-side**: a consuming
project must emit the `joints[]`/`poses[]` block (BuildViz stays project-agnostic).
The joint schema an exporter emits is documented in `BUILDVIZ_INTEGRATION.md`.

---

## 11. `disconnected_components` (SHIPPED)

**Motivating real failure.** A yaw-hub mesh shipped containing a *floating ring* —
a single part mesh that actually held more than one disjoint connected-component (an
island not attached to the body). Each component was individually watertight, so
every printability check passed it, yet the part is physically broken
(unprintable, a loose ring rattling inside the bounding volume). This is an
**intra-mesh** fact and is invisible to the inter-part `connectivity` check (which
treats each instance as one union-find node over the assembly graph).

|  | scope | unit | question | catches floating ring? |
| --- | --- | --- | --- | --- |
| `connectivity` | inter-part | instance | is this part touching a neighbor? | ❌ (it's inside one mesh) |
| `disconnected_components` | intra-mesh | unique mesh | is this one part a single solid body? | ✅ |

**Algorithm (robust, reuses the existing weld pass).** `analyzeTopology`
(`src/buildvizGeometry.ts`) already welds unshared STL vertices by quantized
position into stable ids and iterates every triangle. The component count adds one
`UnionFind` over those welded vertex ids:

1. Allocate a `UnionFind` sized to the welded-vertex count.
2. For every non-degenerate triangle, `union` its three welded ids (faces sharing a
   welded vertex are one body — shared-vertex welding is cheaper than shared-edge
   and never over-counts, so it never false-fails a solid that merely touches
   itself at a point).
3. The number of distinct roots over used vertices is `componentCount`.
4. Per-component enrichment for triage: partition the signed tetra-volume sum and
   local AABB by component root; report the **smallest** component (the likely stray
   island) with its world-space anchor (transformed by a representative instance's
   matrix, like `thinPoint`/`selfIntersectionPoint`).

**Verdict.** A printed mesh **fails** when `componentCount > expected`. Cost is
O(triangles) on data already walked for `watertight`, so it is effectively free
when watertight is on.

**Intent as data.** `expected` resolves as
`checksConfig.expectedMeshComponents[meshId] ?? checksConfig.maxMeshComponents ?? 1`,
so a legitimately multi-body mesh (a captive-nut block, a pre-split clamp) is
declared, not false-failed.

**Wiring (as built).**
- `CheckKind` gains `disconnected_components`; `CHECK_KIND_LABEL` →
  `'disconnected body'` (`src/buildScene.ts`, `src/buildvizChecks.ts`).
- `MeshPrintability` gains `componentCount: number | null` and
  `smallestComponent: { triangleCount, volumeMm3, point } | null`, populated in the
  printability loop (`src/buildvizGeometry.ts`).
- A `disconnected_components` record is emitted in `geometryChecks` alongside
  `watertight`/`self_intersection` (`fail` when `componentCount > expected`), with
  the smallest island's anchor for shading.
- Default-on in `PRINTABILITY_KINDS` (`scripts/buildviz.ts`), toggled off with
  `--no-printability`, individually selectable via `--checks disconnected_components`.
- Component fails fold into the report's `problemCount` so `results.passed` flips
  (a real gate), the same way the user gates on `results.passed`.

**Acceptance.** Fails a mesh whose triangles form 2+ disjoint welded-vertex
components (labeled with the count + stray island volume/location); passes a normal
one-body part; passes a mesh declared `expectedMeshComponents[meshId] = N` with
exactly `N` bodies; leaves `connectivity` and all other kinds unchanged.

## Non-goals (stays offline / out of scope)

- Automatic cable/harness route inference from geometry — `routing_reach` is
  schema-first (producer emits `routes[]`); inferring routes would break
  project-agnosticism.
- Exact medial-axis wall thickness — the shipped `wall_thickness` is a heuristic
  inward-ray percentile (so it only `warn`s).
- Replacing a project's exact-CAD offline verifier — BuildViz runs the generic
  subset and surfaces everything; the verifier remains the authority.
