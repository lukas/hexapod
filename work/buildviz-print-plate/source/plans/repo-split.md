# Repo split into pieces — SHIPPED

Plan for reorganizing BuildViz from two big entangled files plus a flat
`src/` + `scripts/` layout into **one repo with a separate directory per
piece**. **Status: shipped** (see "Deviations discovered during
implementation" at the end).

Decisions already made:

- **Monorepo, separate directories.** No separate repos, and no npm-workspace
  machinery to start — a single root `package.json` with one directory per
  piece and enforced import boundaries. Workspaces/publishing is a later,
  optional step (§6).
- **The viewer stays bundled with the hub.** The hub remains the thing that
  serves the viewer UI; there is no independently deployed viewer.

## 1. The five pieces

The four product pieces plus the shared foundation they all sit on:

| Directory | Piece | Contents (today's files) |
| --- | --- | --- |
| `core/` | Shared data model + geometry engine | `src/buildScene.ts` (scene.json schema + types), `src/buildModel.ts` (ids/slugs/index types), design-spec parsing + `inspect`/`query` from `src/buildvizCore.ts`, `src/buildvizKinematics.ts` (FK/poses), and the **engine half** of `src/buildvizGeometry.ts` (STL loading, BVH indexing, fastener detection, spatial primitives). Browser- and Node-safe; no React, no `node:fs` outside clearly-marked loaders. |
| `checks/` | Build sanity checks ("is this assemblable/printable/sane") | The **check half** of `src/buildvizGeometry.ts` (`checkAssembly`, `sweepOverlaps`, probe/slice/thickness, watertight / wall-thickness / thread-engagement / assembly-access), `src/buildvizChecks.ts` (records, sidecar, highlights), `src/buildvizPacking.ts` + `scripts/packExport.ts` (plate packing + 3MF/STL export). Depends on `core/` only. Must keep running **in the browser too** — the viewer's "Run live checks" imports it. |
| `hub/` | Versioning for LLMs | `scripts/hub.ts` (daemon, identity/discovery, HTTP surface, registry, `~/.buildviz` cache), `scripts/buildsIndex.ts` (index + named-version model), `diffManifests`/`summarizeDiff` out of `src/buildvizCore.ts`. Owns `push`/`register`/`versions`/`diff`/`migrate`/`freeze`/`cache` behavior. Depends on `core/` (+ `checks/` only for the `/__buildviz/pack-export` endpoint). |
| `viewer/` | Visualization | `src/App.tsx`, `src/BuildViewer.tsx`, `src/MotionPanel.tsx`, `src/ChecksPanel.tsx`, `src/ExportPanel.tsx`, CSS, `index.html`, the Vite root. Depends on `core/` + `checks/`. **Served by the hub** (see §4). |
| `cli/` | Communication with LLMs | `scripts/buildviz.ts` reduced to parse + dispatch, per-domain command modules, `scripts/cliFormat.ts` (JSON envelope + human printers), `scripts/cliShared.ts`, `scripts/usageLog.ts`, `docs`/`init` (BUILDVIZ.md + Cursor skill generation), `highlight`, `screenshot`. The `buildviz` bin lives here; each command is a thin wrapper over `core/`/`checks/`/`hub/`. |

Allowed dependency edges (and nothing else):

```text
cli  ->  hub, checks, core
hub  ->  checks (pack-export endpoint only), core
viewer -> checks, core
checks -> core
core -> (nothing internal)
```

## 2. The contracts that hold the pieces together

These are the real interfaces; they all already exist and none of them change
in this plan. `core/` owns the types for all of them:

- The **`scene.json` manifest schema** (`BuildSceneManifest`, `joints[]`,
  `checksConfig`, schema version).
- The **`checks[]` record** (`{ id, kind, status, label, instances?, point? }`)
  and the `buildviz_checks.json` sidecar — how `checks/` talks to the viewer.
- The **hub HTTP API** (`/__buildviz/status`, `/__buildviz/push`,
  `/builds/index.json`, …) and the `~/.buildviz` discovery files — how
  everything talks to the hub.
- The **CLI JSON envelope** (`{ ok, build, summary, results, warnings,
  errors }`) — how agents talk to the CLI.

Regression gate for every phase: `check` / `push` / `versions` / `diff` /
`pack --json` produce byte-identical JSON before and after; the bundled
hexapod builds render; `hub restart` still rebuilds from cache.

## 3. The two files that must be split first

Everything else is file moves. These two are real refactors:

1. **`src/buildvizGeometry.ts` (~3.4k lines) → engine vs. checks.** The engine
   part (STL loader, BVH cache, mesh stats, fastener heuristics, AABB/distance
   primitives) goes to `core/`; every check implementation and query tool
   (`checkAssembly`, `sweepOverlaps`, `probePoints`, `probeRegion`,
   `sliceBuild`, `thicknessBuild`, `billOfMaterials`, `identify`) goes to
   `checks/`. The split line is "computes a fact about one mesh" (engine) vs.
   "judges an assembly / answers a query" (checks) — anything importing the
   BVH cache but exporting a report belongs in `checks/`.
2. **`scripts/buildviz.ts` (~3.4k lines) → dispatcher + command modules.** The
   ~30 `if (command === …)` handlers become per-domain modules
   (`commands/hub.ts`, `commands/versions.ts`, `commands/checks.ts`,
   `commands/query.ts`, `commands/pack.ts`, `commands/docs.ts`), each
   exporting its usage text; the entry file keeps only arg parsing, dispatch,
   help, and the usage-log hook.

Also in this phase: `diffManifests` moves out of `buildvizCore.ts` (it is
versioning, not scene inspection), and `cliFormat.ts`'s `printJson` (the only
piece the hub imports) moves to a tiny shared spot so `hub/` never depends on
`cli/`.

## 4. Viewer stays bundled with the hub

Unchanged model, adjusted paths:

- The Vite root moves to `viewer/`; `vite.config.ts` goes with it (its
  `enumerateBuilds` dev plugin comes from `hub/`'s builds-index module).
- `scripts/hub.ts` already boots Vite programmatically (`createServer`); it
  points at `viewer/` as the root instead of the repo root. Dev flow
  (`npm run dev`, port 5173) and hub flow (port 5183) both keep working.
- `npm run build` builds the viewer to `viewer/dist`; a static/production hub
  serves that.
- `public/builds/*` (bundled example builds) stays at the repo root — it is
  test data for all pieces, not viewer code.

## 5. Sequencing

1. **Split the two big files** (§3) in place, plus the `buildvizCore.ts` and
   `printJson` moves. No directory moves yet; CI gate green.
2. **Create the directories and move files** (`core/`, `checks/`, `hub/`,
   `viewer/`, `cli/`), update imports, move the Vite root, repoint the bin
   (`bin/buildviz.mjs` → `cli/`). Root `package.json` stays the only manifest;
   `tsconfig` paths (`@buildviz/core` → `core/src`, …) name the boundaries.
3. **Enforce the edges** with an ESLint `import` boundary rule matching the
   graph in §1, so `viewer/` can never quietly reach into `hub/` again.
4. Update `README.md`, `BUILDVIZ_INTEGRATION.md`, `BUILDVIZ_LLM_INTERFACE.md`
   file references and `npx buildviz docs` output.

## 6. Explicitly deferred

- **npm workspaces / separate `package.json` per directory** — only if a piece
  needs its own publish cadence (most plausible: a lightweight
  `@buildviz/checks` for other projects' CI, without React/Vite deps).
- **Separate repos** — not planned; the scene schema still changes too often.
- **Standalone viewer deployment** — rejected for now; the hub is the viewer's
  only host (decision above).

## 7. Deviations discovered during implementation

- **Diff lives in `core/`, not `hub/`.** The viewer computes compare-mode diffs
  client-side (`App.tsx` calls `diffManifests`/`instanceDiffStatuses`), so the
  diff logic is shared by viewer + hub + CLI and moved to `core/buildDiff.ts`
  instead of hub-side as §3 originally suggested. The CLI `diff` command
  handler still lives with the versioning commands (`cli/commands/versionsCmd.ts`).
- **`cliShared.ts` and `usageLog.ts` live in `hub/`, not `cli/`.** The hub
  imports both (arg parsing, `~/.buildviz` home, build-id canonicalization,
  usage logging), and `hub → cli` is a forbidden edge, so these shared runtime
  primitives moved to `hub/` (which the CLI may import).
- **`viewer/vite.config.ts` imports `hub/buildsIndex`.** The dev-server
  `/builds/index.json` plugin is build tooling, not app code, so the
  viewer-side boundary rule is scoped to `viewer/src/**` only.
- The engine half of the old `buildvizGeometry.ts` is `core/geometryEngine.ts`;
  the checks half kept the `buildvizGeometry.ts` name (now under `checks/`).

## 8. Open questions

- Does `pack`/3MF export stay in `checks/` (chosen here: yes, it shares the
  geometry engine and the "is this build physically sensible" spirit) or
  eventually become its own `print/` piece if it grows slicer-specific config?
- `screenshot` shells out to Playwright from the CLI but renders the viewer —
  it stays in `cli/` (it drives a browser against a running hub, it does not
  import viewer code), but worth revisiting if it ever needs viewer internals.
