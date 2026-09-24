# BuildViz Roadmap

The single working roadmap for BuildViz. It records **what's shipped** (so we
don't re-propose done work) and the **remaining / proposed work** by area, each
item with a status and enough context to act on. Deeper per-area design docs live
under [`plans/`](plans/) and are linked from each section.

Reference docs (not roadmaps) stay separate: [`README.md`](README.md),
[`BUILDVIZ_INTEGRATION.md`](BUILDVIZ_INTEGRATION.md) (exporter/agent contract),
[`BUILDVIZ_COMPATIBILITY.md`](BUILDVIZ_COMPATIBILITY.md) (the
BuildViz-compatible-project contract checked by `buildviz compat`),
[`BUILDVIZ_LLM_INTERFACE.md`](BUILDVIZ_LLM_INTERFACE.md) (CLI/API guide), and
[`DESIGN_YAML_SPEC.md`](DESIGN_YAML_SPEC.md) (`design_spec.yaml` schema).

Status legend: **SHIPPED** · **PLANNED** (clear, queued) · **PROPOSED** (needs a
decision or producer-side data before it's worth building).

---

## ⚠️ Decisions needed — RESOLVED

These were the open questions; all were reviewed and decided ("follow all the
recs"). Recorded here so we don't re-litigate them. Details for each are in the
per-area sections below.

1. **Remote / shared hub — auth & trust model? → RESOLVED: BUILD (a).**
   Private-network only, no app auth, **read-only when bound off-loopback**.
   `buildviz hub --host <addr>` / `--lan` binds a non-loopback address and runs
   READ-ONLY: view/read endpoints stay up; `push`, `pack-export`, `register`, and
   `open-path` are hard-gated (403). Loopback (the default) keeps full read/write.
2. **Binary asset upload on `push`? → RESOLVED: BUILD.** `push --upload-assets`
   ships relative mesh bytes; the hub stores them **content-hashed** (dedup across
   versions/builds), enforces a **size cap** (default 256MB, `--max-upload-mb`), and
   rewrites the cached scene's mesh URLs to `/builds/_assets/<sha256>.<ext>`.
3. **`buildviz publish` static-export path? → RESOLVED: DECLINED (parked).** Hub +
   `push` (now with asset upload) cover sharing; no concrete static-hosting need.
4. **Annotated review links? → RESOLVED: BUILD.** Viewer "Share review link" action
   builds a `?highlight=` URL carrying the current highlights + a typed question;
   opening such a URL pins the question banner and applies the highlights.
5. **Richer diff — how deep? → RESOLVED: BUILD summary panel; DEFER vertex-level.**
   A compare-mode diff-summary panel (counts + added/removed/moved/changed lists)
   shipped; full vertex/topology-level geometry diff stays PROPOSED.
6. **Explicit scene `schemaVersion`? → RESOLVED: BUILD now.** Optional manifest
   integer recorded by `assertSceneManifest`; `validate` warns on unknown/old
   versions. Folded in with this schema-touching batch.
7. **Lower-priority LLM/agent queries? → RESOLVED: BUILD `identify` + `bom`.**
   `identify` (dual world/part-local frame) + on-screen axis legend, and `bom`
   (bill of materials) shipped. The rest (`measure gap`/`contacts`/`fasteners`,
   `topface`/`trays`/`compare`/`explain`/`status`) stay PROPOSED.
8. **Swept-path assemblability — producer for the data? → RESOLVED: DEFER.** Still
   no scene emits `instance.insert` / `instance.cots` / `checksConfig.requiredParts`;
   deferred until a consuming scene declares insertable COTS parts.

---

## Current state — what's shipped

BuildViz is a generic, project-agnostic web viewer + CLI + machine-wide hub for
generated physical designs. Already in place:

- **Viewer** — orbit/pan, per-part-type visibility, focus groups, hover/click
  inspect, double-click isolate, ruler + point-probe tools, `design_spec.yaml`
  panel, mobile layout, build switcher, diff mode, Checks panel, Motion scrubber,
  Export-plates control.
- **Data model** — PROJECT → BUILD → NAMED, BRANCH-LIKE VERSION. Address builds
  as `project/build` and versions as `project/build@version`. Hierarchical
  `builds/index.json` (`schema: 2`); `?project=&build=&version=&compare=` URLs
  (legacy `?build=<id>` still resolves). `buildviz migrate` normalizes legacy
  `v1`/`v2` into named versions.
- **Hub & lifecycle** — one machine-wide hub on its own port (5183, distinct from
  the Vite dev server's 5173), identity-verified via `GET /__buildviz/status`
  (`service: "buildviz-hub"`). `hub --detach`/`start`/`stop`/`status`/`restart`;
  `push`/`register`/`send` autostart it. Discovery in `~/.buildviz/server.json`,
  registry in `~/.buildviz/registry.json`, version cache under
  `~/.buildviz/cache/<project>/<build>/`, content-addressed pushed assets under
  `~/.buildviz/cache/_assets/`. Opt-in `hub --host <addr>` / `--lan` binds a
  non-loopback address for read-only remote viewing (mutation/host-action endpoints
  disabled off-loopback); the default stays loopback with full read/write.
- **CLI for agents** — `inspect`, `part`, `feature`, `query`, `assets`,
  `validate`, `check`, `sweep`, `pack`, `highlight`, `screenshot`, `versions`,
  `diff`, `identify` (dual world/part-local frame), `bom` (bill of materials),
  `compat` (project-compatibility contract), `docs`, `usage`, plus the runtime
  `window.buildviz.setHighlights` channel. Every read command supports `--json`
  (the primary contract).
- **Usage logging** — every known CLI invocation and every hub HTTP request to
  `/__buildviz/*` / `/builds/*` is logged best-effort (fire-and-forget, never
  throws) as JSONL to `~/.buildviz/usage.jsonl`, recording metadata only (command +
  flag NAMES, or method/path/status/duration/read-only — never payloads or flag
  values). `buildviz usage [--json]` summarizes per-command/per-endpoint counts
  with first/last-seen, so a "what's used vs. unused" audit is conclusive.
- **Validation (`buildviz check`)** — generic `checks[]` schema + `checksConfig`
  intent-as-data, a clickable Checks panel, a `buildviz_checks.json` sidecar
  (`--emit`), and live in-browser recompute via three-mesh-bvh. Shipped kinds:
  `mesh_overlap`, `clearance`, `connectivity`, `placement`, `scene_meta`
  (spatial / manifest), plus offline gates `watertight`, `degenerate_geometry`,
  `wall_thickness`, `self_intersection`, `disconnected_components`,
  `thread_engagement`, `assembly_access`, `mating_contact`, `routing_reach`. See
  [`plans/validation.md`](plans/validation.md).
- **Motion** — additive `joints[]`/`poses[]` schema, forward kinematics, a Motion
  scrubber, and swept-pose validation (`swept_overlap`/`swept_clearance`) in the
  viewer and via `buildviz sweep`. Demo: `hexapod-motion-demo`.
- **Pack & export** — `buildviz pack` orients each part for FDM printing and packs
  footprints onto printer plates; `--emit` writes a `buildviz_pack.json` viewer
  layout; `--export` writes Bambu-ingestible per-plate `.3mf` (or merged `.stl`),
  exposed via the viewer's Export-plates control (`POST /__buildviz/pack-export`,
  `POST /__buildviz/open-path`).

What was **removed** (don't resurrect): the `buildviz netlify` static export &
direct-deploy command — the live hub + `push` cover today's sharing use case.

What was **fixed** (closed, not a TODO): the single-segment build-id doubling in
the navigate→URL→read round-trip (`joinProjectBuild` is now the exact inverse of
`splitProjectBuild`; `src/buildModel.ts`, `src/App.tsx`).

---

## Remaining / proposed work

### Repo split into pieces

Detail: [`plans/repo-split.md`](plans/repo-split.md).

- **Split the codebase into one directory per piece — SHIPPED** (this roadmap
  pass). Monorepo, separate directories (no workspaces to start): `core/`
  (scene schema + geometry engine), `checks/` (sanity checks + packing),
  `hub/` (versioning), `viewer/` (visualization, stays bundled with/served by
  the hub), `cli/` (agent interface). The prerequisite refactors shipped too:
  `buildvizGeometry.ts` split into `core/geometryEngine.ts` (engine) vs.
  `checks/buildvizGeometry.ts` (checks), and the CLI split into a dispatcher
  (`cli/buildviz.ts`) + per-domain command modules (`cli/commands/`). Import
  boundaries are lint-enforced. External contracts (scene schema, `checks[]`
  records, hub HTTP API, CLI JSON envelope) unchanged — verified byte-identical
  `--json` output across `check`/`sweep`/`pack`/`inspect`/`bom`/`query`/
  `versions`/`compat` before and after.

### Validation & assemblability

Detail: [`plans/validation.md`](plans/validation.md),
[`plans/assemblability.md`](plans/assemblability.md).

- **`buildviz compat <project-dir>` project-compatibility contract — SHIPPED**
  (this roadmap pass). A single command that answers "is this a
  BuildViz-compatible project, and if not, how do I get compatible?" for
  LLM-generated physical-build projects. Reports, per requirement,
  pass/warn/fail: a `scene.json` manifest that parses + passes basic validation
  (reuses `validateBuild`), an STL folder whose scene-referenced meshes all
  resolve on disk, an up-to-date `design_spec.yaml` (the durable record of design
  intent/rationale, enforced for freshness: a scene `partType` with **no** `parts:`
  entry `fail`s and is named — the "agent dropped it" case; a spec entry with no
  matching scene part `warn`s as stale drift; and an mtime heuristic `warn`s when
  `design_spec.yaml` is older than `scene.json` or any referenced STL), and
  non-empty project-authored `ASSEMBLY.md` + `BOM.md`. `--json` is
  the primary contract (per-requirement results + an overall `compatible`
  boolean + a remediation list); `cliFormat` prints a readable report.
  Compatible = no `fail` (uncovered scene parts block; stale-drift and staleness
  `warn`s don't). Purely additive; robust to a project missing everything
  (reports fails, never crashes; mtimes read defensively). Positions
  `validate`/`check`/`bom` as the "critic" APIs a project self-checks with while
  `ASSEMBLY.md`/`BOM.md`/`design_spec.yaml` stay project-authored. Contract doc:
  [`BUILDVIZ_COMPATIBILITY.md`](BUILDVIZ_COMPATIBILITY.md).
- **`disconnected_components` — SHIPPED** (this roadmap pass). Per unique printed
  mesh, count disjoint welded-vertex bodies and `fail` any mesh with more than its
  expected count (default 1) — the intra-mesh floating-island / detached-ring
  guard, distinct from the inter-part `connectivity` check. Reuses the existing
  weld pass in `analyzeTopology`; opt-out per mesh via
  `checksConfig.expectedMeshComponents` / global `maxMeshComponents`. Default-on in
  the printability group. See [`plans/validation.md`](plans/validation.md) §11.
- **Swept-path assemblability (`insertion_path`, `rotation_clearance`,
  `required_parts`) — PROPOSED.** Catch parts that are geometrically valid in the
  seated state but have no collision-free *insertion path* (a captured bearing
  pocket, an over-closed servo cradle, a Ø10 hole for a Ø20 horn). Large, needs
  new producer-side scene data (`instance.insert`, `instance.cots`,
  `checksConfig.requiredParts`) that **no current scene emits**, and the exact-CAD
  authority already lives in project verifiers. Deferred until a consuming scene
  declares insertable COTS parts. Full spec:
  [`plans/assemblability.md`](plans/assemblability.md).
- **Automatic harness inference — PROPOSED (out of scope for now).** `routing_reach`
  already gates producer-supplied `routes[]`; inferring routes from geometry would
  break project-agnosticism. Keep schema-first.

### Versioning & publishing

Detail: [`plans/versioning.md`](plans/versioning.md).

- **Scene-level `assetsBaseUrl` honored by the viewer — SHIPPED** (this roadmap
  pass). The viewer resolves relative `mesh.url` values against an optional
  `assetsBaseUrl` on the manifest, so the same relative-URL build renders under the
  hub, static hosting, and inside a `versions/<name>/` dir without a symlink hack —
  removing the "Invalid typed array length" 404 footgun. `validate` also warns
  (`relative_mesh_url_static_risk`) when a mesh URL is relative and no
  `assetsBaseUrl` is set.
- **`buildviz freeze <build-dir> --version <name>` — SHIPPED.** Writes the canonical
  on-disk `versions/<name>/` layout + `meta.json` **in place** for a register-based
  build carrying local STL assets (the on-disk sibling of `push`):
  copies `scene.json`/`design_spec.yaml`/relative `stl/` assets, `--set-default`
  mirrors to the build root (snapshotting the prior default so it survives), and
  `--force` overwrites an existing (immutable) named version.
- **`--bump` + auto-snapshot so "every revision becomes a new version" — SHIPPED**
  (this roadmap pass). `push --bump` and `freeze --bump` auto-pick the next free
  `v<N>` (reusing the `v(\d+)` ordering in `compareVersionNames`) and make it the
  default, giving a one-flag "archive each revision" path. Independently, a plain
  `push`/`freeze` that would OVERWRITE the existing default in place now first
  **snapshots the prior default** as a fresh `v<N>` (content-guarded — no snapshot
  when nothing changed), so the common "regenerated `scene.json`, same `main`" flow
  accumulates history with no extra flags. `--no-snapshot` opts out for a pure
  overwrite, and the snapshots integrate with `--keep <n>` retention (now also on
  `freeze`) so frequent rebuilds stay bounded; the default version is never pruned.
  `register`/`send` are deliberately left as overwrite-in-place "live pointers"
  (docs warn to use `freeze --bump` for on-disk history). Purely additive: behavior
  without `--bump`/with `--no-snapshot` matches the prior default.
- **`buildviz publish` — DECLINED (parked).** A separate static `public/builds`
  export root (asset copy + URL rewrite + index refresh) was considered and
  declined: the live hub + `push` (now with binary asset upload) cover today's
  sharing use case, and there is no concrete static-hosting need. Revisit only if a
  real static-hosting requirement appears.
- **Binary asset upload on push — SHIPPED** (this roadmap pass). `push
  --upload-assets` reads each **relative** mesh file's bytes and ships them with the
  scene (absolute `http(s)` and `/`-rooted URLs are already reachable and left
  untouched). The hub stores bytes **content-hashed** under
  `~/.buildviz/cache/_assets/<sha256>.<ext>` (dedup across versions/builds), enforces
  a **size cap** (default 256MB; override `--max-upload-mb <n>`, also enforced
  server-side), and rewrites the cached scene's mesh URLs to `/builds/_assets/...`
  so the pushed build is self-contained. `--assets-dir <dir>` sets the base for
  resolving relative URLs. Backward compatible: a `push` without `--upload-assets`
  behaves exactly as before. The off-loopback read-only hub never accepts uploads.
- **Explicit scene `schemaVersion` — SHIPPED** (this roadmap pass). Optional integer
  on the manifest (`CURRENT_SCENE_SCHEMA_VERSION = 1`), additive — scenes without it
  still load and render everywhere. Recorded verbatim by the hub's
  `assertSceneManifest` on push; `validate` warns for a non-integer
  (`invalid_schema_version`), a newer version (`unknown_schema_version`), or an
  older version (`old_schema_version`). Bump only on a breaking/structural change.
- **Per-version changelog message (`push`/`freeze -m`) — SHIPPED.** Both `push`
  and `freeze` take an optional `-m`/`--message <text>` that attaches a
  changelog/commit note to the version being created/bumped. It is stored in the
  per-version metadata (cache `meta.json` / on-disk `meta.json` records, plus
  `CacheVersionMeta`), exposed as `message?` on `BuildVersionEntry` in
  `/builds/index.json`, and surfaced in the viewer: the current-version "last
  updated" badge, each option in the version dropdown, the "new version available"
  pill (`new version v5: …`), and the diff/compare panel header. The note applies
  only to the new version — an auto-snapshot of the prior default keeps its own
  note — and omitting `-m` is fully backward-compatible (no note stored). A
  producer pipeline (e.g. the auto-publishing verifier) can derive it from a git
  commit subject or check summary: `push … --bump -m "$(git log -1 --format=%s)"`.

### Hub & sharing

- **Prune / retention controls — SHIPPED.** `push --keep <n>` (and `freeze --keep
  <n>`) caps retained versions per build (keep-all stays the default; prunes the
  oldest non-default, auto-snapshots included; never the default), plus
  `buildviz cache ls` (per-build versions + sizes) and `buildviz cache rm
  <project>/<build> [--version <name>]` (refuses to delete the default version).
- **Remote/shared hub (read-only off-loopback bind) — SHIPPED** (this roadmap pass).
  `buildviz hub --host <addr>` or `--lan` binds the hub to a non-loopback address so
  teammates on a trusted private network (LAN/VPN/Tailscale) can VIEW live builds;
  the default stays loopback `127.0.0.1`. When bound off-loopback the hub runs
  **READ-ONLY**: it serves the app, `/builds/...` assets, `/builds/index.json`,
  `GET /__buildviz/status` (which advertises `readOnly: true`), and read data, but
  **hard-gates every mutation / host-action endpoint** — `POST /__buildviz/push`,
  `pack-export`, `register`, and especially `open-path` (it runs `open` on the host)
  all return 403 before any handler runs. Trust model is private-network only (NO
  app auth, per the decision); the CLI prints a clear exposure warning on bind.
  Loopback behavior is fully intact (all endpoints available locally).

### Viewer & review UX

- **Part search / filter in the build menu — SHIPPED.** A filter box atop the Part
  Types list matches a part type name OR any instance name/id, for quickly finding
  parts in large builds (e.g. 600+ instances); spans the mobile drawer grid.
- **Annotated review links — SHIPPED** (this roadmap pass). A "Share review link"
  action in the viewer overlay builds a shareable `?highlight=` URL from the parts
  currently highlighted (falling back to the selected part) plus a typed question.
  Opening such a URL applies the highlights AND pins the question in an on-screen
  banner (dismissable), giving a packaged human-review UX on top of the existing
  highlight-URL API + `window.buildviz.setHighlights` (`question` is an additive,
  optional field on the highlight spec).
- **Richer diff — summary panel SHIPPED; vertex-level PROPOSED.** Compare mode now
  shows a diff-summary panel (counts plus added / removed / moved / changed instance
  lists, and added/removed/changed mesh counts); clicking a changed instance
  highlights it. **DEFERRED:** full vertex/topology-level geometry diff (per-mesh
  geometry change detection beyond transform + add/remove) stays PROPOSED.

### Viewer features that would eliminate manual diagnostic rendering

Detail/peer docs: [`plans/assemblability.md`](plans/assemblability.md),
[`plans/validation.md`](plans/validation.md), CLI counterparts in
[`plans/llm-api.md`](plans/llm-api.md).

**Motivation.** While validating the STS3215 hexapod, the workflow repeatedly
exports *batches* of multi-angle PNG renders (iso / front / bottom / +X / −X / +Y /
−Y / oblique) plus one-off Python *probe* scripts just to **eyeball** geometry
defects — too-small horn bores, captured bearing pockets, an inner-race retain *lip*
the bearing can't pass, clamp-cap/bracket interpenetration, asymmetric back-housing
lips. That manual rendering is a *symptom of missing interactive viewer
capabilities*: each feature below is the human-in-the-loop **investigation** tool you
reach for *after* a check flags something, and replaces a recurring manual
render/probe. They **complement, not replace**, the assemblability/validation checks
already planned (see the division-of-labor note below).

- **Clipping / section planes — PROPOSED (highest value).** Interactive
  cross-section plane(s) dragged through any solid (per-axis or arbitrary normal),
  capping the cut so you SEE interior geometry directly. Hexapod failures it would
  have exposed: the captured bearing pocket, the yaw-hub inner-race retain lip the
  bearing can't pass, and undersized internal horn bores. Replaces the manual "render
  a cut view."
- **Part isolation + look-inside — PROPOSED.** Solo the selected part(s), hide the
  rest, and orbit/section the isolate (extends today's double-click isolate into a
  persistent solo + look-inside mode). Replaces "export one mesh and render it from N
  angles" — the bulk of the multi-angle PNG batches.
- **Measure / probe tool — PROPOSED.** Pick geometry in-viewer for point-to-point
  distance, hole/cylinder diameter, and edge length (builds on the shipped ruler +
  point-probe). Directly targets the recurring diameter-mismatch bug class — horn
  opening (Ø20 disc vs Ø24 opening) and bearing seat (Ø30 bore vs Ø32 flange).
  Replaces the one-off `probe_*.py` scripts; the CLI counterparts are the
  `probe points`/`probe region` (SHIPPED) and proposed `measure gap` items in
  [`plans/llm-api.md`](plans/llm-api.md).
- **Overlap / interference highlighting — PROPOSED.** Render the interpenetration
  *volume* / clashing region as a 3D solid in the scene, not just a Checks-panel row
  — e.g. shade the clash body in place. Hexapod: the clamp-cap vs bracket overlap and
  the hub-flange clash. The `mesh_overlap` check already computes the region
  (`region`/`point` payloads); this paints it as inspectable 3D.
- **Assembly / insertion preview — PROPOSED.** Exploded view plus a per-part
  insertion-axis collision sweep / simple animation along the seat axis. The
  bearing-over-lip and captured-pocket bugs are **motion** problems a static render
  (and static CAD) cannot reveal. Pairs with the swept `insertion_path` /
  `rotation_clearance` checks in [`plans/assemblability.md`](plans/assemblability.md):
  the check computes feasibility headlessly; this explodes/animates it for the human.

**Division of labor (matches [`plans/assemblability.md`](plans/assemblability.md) and
the "verifier gates, viewer surfaces" thesis in
[`plans/validation.md`](plans/validation.md)).** Heavy geometry — boolean overlap
volumes, swept insertion-path feasibility — is realistically a *verifier / CAD-kernel*
job: the verifier computes the answer and ships findings (`region`/`line`/`point`) to
BuildViz via the `buildviz_checks.json` **sidecar**, where the viewer paints them with
zero per-project code. The viewer features above are the *interactive investigation*
layer a human drives once a check flags something — they make the flagged defect
legible without a render batch, but the checks remain the gate.

### LLM / agent geometry API

Detail: [`plans/llm-api.md`](plans/llm-api.md). Much of the originally-proposed
surface shipped (`validate`, `assets`, `part`, `feature`, `query`, `check` /
clearance, `screenshot`, `highlight`, `diff`, motion = articulated-pose clearance).
The high-value remainder, prioritized by real agent-session evidence:

- **`probe points` / `probe region` — SHIPPED.** "Is this point/box solid material,
  a hole, or a void?" `probe points --points '[[x,y,z],...]'` classifies each point
  (solid/hole/void) with enclosing instances + nearest-surface distance via the BVH;
  `probe region --box 'x=a:b,...'` grid-samples occupancy/volume + occupants. Both
  emit a `highlightUrl` + `highlights` for the viewer overlay.
- **`slice --metric min-thickness` / `thickness` — SHIPPED.** `slice` rasterizes a
  cross-section (area + region count, plus a heuristic inscribed-disk min-thickness);
  `thickness` auto-picks the plane perpendicular to the longest axis and sweeps it to
  *prove* a member's narrowest section against `--min`.
- **`mesh stats` — SHIPPED.** `mesh stats <build>` reports per-mesh bounds/volume/
  area/triangle+vertex count/watertightness/open+non-manifold edges/components,
  reusing the `check` topology engine.
- **`measure gap` / `contacts` / `fasteners` — PROPOSED.** Mating/gap/engagement
  queries; partial overlap with `check`'s `mating_contact`/`thread_engagement`.
- **`identify` (dual world/part-local frame) + on-screen axis legend — SHIPPED**
  (this roadmap pass). `buildviz identify <build> --instance <id> | --point x,y,z
  [--local x,y,z]` reports a queried location in BOTH world and part-local frames
  (`--json` first + a readable form): for a world point it lists each enclosing
  instance's local coords, inside/outside, nearest-surface distance, local bounds,
  and world origin; `--instance ... --local x,y,z` maps a part-local point back to
  world. The viewer also gains a small on-screen XYZ axis legend that tracks the
  camera, removing the constant viewer↔part-local translation tax.
- **`bom` (bill of materials) — SHIPPED** (this roadmap pass). `buildviz bom
  <build> [--density <g/cm3>] [--part <type>] [--instance <id>] [--no-fasteners]`
  reports, per part type: count, unit + total volume (from the topology engine, via
  the scaled-transform determinant), an optional mass estimate (with `--density`),
  bounding size, and fastener-vs-printed grouping. `--json` first + a readable table
  via `cliFormat`.
- **`topface` coplanarity / bed-contact, `trays`, `compare`, `explain`, `status`
  (stale-vs-source) — PROPOSED.** Lower priority; see the plan.
