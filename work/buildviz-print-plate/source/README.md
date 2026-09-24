# BuildViz

Web-native build inspection for generated physical designs.

BuildViz is a generic viewer. Other projects integrate with it by exporting a
static build folder containing:

- `scene.json` (required) for meshes, instances, transforms, colors, and focus groups.
- `design_spec.yaml` (optional) for CAD inputs, feature names, dimensions, labels, and LLM context.
- Mesh assets referenced by `scene.json`, usually STL files under directories
  such as `stl/`, `meshes/`, `assets/`, or `fasteners/`.

A build only requires a valid `scene.json` and its mesh assets. Builds without a
`design_spec.yaml` still register, serve, and render; they just omit the
semantic overlays and YAML panel.

## Explain revisions; record issues and lessons

Use `push -m "WHAT changed" --reason "WHY this revision is needed"`. BuildViz
warns when the reason is missing and reminds agents to read prior findings and
return with validation results. CLI `feedback project/build@v12` and MCP
`get_version_feedback` / `record_version_feedback` read or append issues,
validation, resolutions, and notes on an exact version without editing its
geometry. The viewer shows **Why this version · issues & lessons**. A resolution
requires an original issue and evidence—not merely a newer version.
See the [agent workflow and examples](BUILDVIZ_LLM_INTERFACE.md#agent-contract-explain-revisions-and-close-the-learning-loop).

## How to run BuildViz — the two-port convention (5183 central, 5173 dev)

> **Read this first (humans and AI agents).** BuildViz uses exactly **two**
> fixed ports. Never start a server on any other (random) port.
>
> | Port | Role | Who uses it |
> |------|------|-------------|
> | **`5183`** | **The shared central hub — the ONE instance everyone uses.** Serves *every* project's builds at once; pick one with `?build=<id>`. | All projects register/push here and view here. |
> | **`5173`** | **Reserved for BuildViz's own dev/testing** (`npm run dev`, Vite default). It is a local dev server, never the hub. | BuildViz maintainers only. **Leave it alone** — don't view project builds on it, don't register into it, don't kill it. |
>
> To **view or register a project build, always use the central hub on `5183`.**
> Do **NOT** run a new dev server on `5199` or any other ad-hoc port — that is
> exactly the port sprawl this convention exists to prevent.

**The one canonical command** (idempotent — a no-op if a hub is already up):

```sh
npx buildviz hub --detach          # or: npx buildviz hub start --detach
```

Then open the hub and pick any registered build:

```text
http://127.0.0.1:5183/                              # build picker
http://127.0.0.1:5183/?build=hexapod-prototype      # a specific build
```

Use **Jump to project or assembly** (⌘K / Ctrl K) from the workshop or any
build. Search includes projects and builds outside the curated catalog; the
**Projects** filter lists every project. **Browse all projects** opens
`?projects=1`, and `?project=single-motor-cat` lists that project's builds.
Picking a build opens its current default revision with a clean URL.

**Print parts** opens the printable STL inventory for the selected revision or
catalog assembly. Download all files, or choose **Changed STLs** and a baseline
revision. ZIPs contain the original STL files with quantity suffixes, a quantity
CSV, and import notes for Bambu Studio. A moved part does not need a new print;
increased quantities of unchanged geometry request only the extra copies.
Purchased-part models are excluded, and unclassified parts remain visible for
review. Missing files or an incomplete comparison block bulk downloads.

The smaller **Purchased parts**, **Assembly**, and **MuJoCo runs** actions open
the BOM, authored guidance, and linked run records/videos. Share a workflow with
`&workflow=print`, `bom`, `assembly`, or `runs`. Run records distinguish exact
revision associations from broader robot-family matches.

Producers can attach a `workflow.json` alongside a scene, or use MCP
`get_workflows` / `set_workflows`. See [the workflow metadata contract](BUILDVIZ_LLM_INTERFACE.md#build-files-and-workflow-metadata).

Manage / discover it:

```sh
npx buildviz hub status            # is the hub up? url / pid / build count
npx buildviz status                # canonical hub URL; warns about stray servers
npx buildviz hub restart           # stop + start detached
```

**Projects never start their own server — they REGISTER (or push) into the hub:**

```sh
# on-disk build directory (hub reads it live from its source dir):
npx buildviz register <build-dir> --project <project> --build <build>

# or send a scene.json layout straight to the hub (cached, versioned):
npx buildviz push --project <project> --build <build> --version main -m "<what changed and why>" --scene scene.json
```

`register` / `push` **auto-start a detached hub on `5183`** if one isn't already
running, so the hub is the only thing you ever launch. The full lifecycle,
discovery/verification protocol, and push API are documented under
[Machine-Wide Hub](#machine-wide-hub) below.

> `npm run dev` (port `5173`) is the **reserved BuildViz dev/test server** — a
> local Vite app server, never the hub, even though it also answers
> `/builds/index.json`. Leave it running/alone; if you just want to *view*
> project builds, use the central hub on `5183`.

## Data model: project / build / branch / version

BuildViz organizes everything as **project → build → branch → version**:

- A **project** groups related builds (e.g. `spider`).
- A **build** is one assembly within a project. Its id on disk is
  `project/build`, and the slashes can go deeper — `spider/leg/coxa` means
  project `spider` and build `leg/coxa`. Human labels are canonicalized to a
  URL/filesystem-safe slug, so `"Spider Chassis"` becomes `spider/chassis`.
- A **branch** is a parallel line of work inside a build (like a git branch,
  e.g. `main`, `yoke-redesign`). Every build has at least the default branch.
- A **version** is a named snapshot **on a branch** (`main`, `v3`,
  `with-dome`, …). Each branch keeps its own version history and its own
  default version.

Address a build as `project/build`, a version on the default branch as
`project/build@version`, and a branch explicitly as `project/build@branch` (its
default version) or `project/build@branch@version`. A single `@x` ref resolves
as a branch when one matches that name, otherwise as a version on the default
branch — so pre-branch addresses keep working unchanged.

Each build has one **default branch** (named `main` by default) that lives at
the build root: its default version is the build-root `scene.json` and its
other versions live under `versions/<name>/scene.json`. Every other branch
lives under `branches/<name>/` with the same internal layout. The alias
`latest` always resolves to a branch's default version. Create or update a
branch with `push --branch <name>`; promote one to build default with
`push --set-default-branch`. The viewer adds a Branch picker (URL param
`&branch=<name>`) when a build has more than one branch, and its Compare
dropdown can diff across branches (`compare=branch@version`).

## Local Install

BuildViz is **not published to npm** (the package is private), so a bare
`npx buildviz` only works after you link or install this checkout — otherwise
npm falls through to the registry and fails with a 404.

To make `npx buildviz` (and plain `buildviz`) work machine-wide, link this
checkout once:

```sh
cd ~/buildviz   # this repo
npm link
```

Re-run `npm link` if the alias ever breaks (e.g. after a Node/npm upgrade
replaces the global bin directory).

Alternatively, from another project, install the checkout as a local dev tool:

```sh
npm install --save-dev ~/buildviz
```

Then run BuildViz against that project's current directory:

```sh
npx buildviz
```

Show the docs and project checklist available to that project:

```sh
npx buildviz docs
npx buildviz --help
```

If you run it from a subdirectory, BuildViz walks upward to find the nearest
`scene.json`, `design_spec.yaml`, or common STL asset directory and uses that as
the build root.

Or add a script to the other project's `package.json`:

```json
{
  "scripts": {
    "buildviz": "buildviz"
  }
}
```

Then use:

```sh
npm run buildviz -- --port 5174
```

If a project has STL files and `design_spec.yaml` but no `scene.json`, initialize
a starter scene without overwriting existing files:

```sh
npx buildviz init
```

Preview what would be generated:

```sh
npx buildviz init --dry-run --json
```

`init` also creates `BUILDVIZ.md` and `.cursor/skills/buildviz/SKILL.md` when
they are missing, so Cursor agents know how to validate, run, and annotate the
local build. Existing `scene.json`, `BUILDVIZ.md`, and Cursor skill files are
kept unless you explicitly pass a replacement option such as `--force` for the
scene manifest.

## Development

### Repo layout — one directory per piece

The codebase is split into five pieces with enforced import boundaries
(`cli → hub → checks → core`, `viewer → checks/core`; see
[`plans/repo-split.md`](plans/repo-split.md)):

| Directory | Piece |
| --- | --- |
| `core/` | Shared data model + geometry engine: `scene.json` schema (`buildScene.ts`), build ids/index shapes (`buildModel.ts`), design-spec parsing + inspect/query (`buildvizCore.ts`), manifest diffing (`buildDiff.ts`), forward kinematics (`buildvizKinematics.ts`), STL loader + BVH primitives (`geometryEngine.ts`). Browser- and Node-safe. |
| `checks/` | Design sanity checks and print prep: interference/connectivity/printability/assembleability + geometry queries (`buildvizGeometry.ts`), check records + sidecar (`buildvizChecks.ts`), plate packing (`buildvizPacking.ts`) and slicer export (`packExport.ts`, `buildviz3mf.ts`). Runs in Node **and** the browser (the viewer's live checks). |
| `hub/` | Versioning + serving: the machine-wide hub daemon, discovery, registry, `~/.buildviz` cache (`hub.ts`), the builds index + named-version model (`buildsIndex.ts`), plus runtime primitives shared with the CLI (`cliShared.ts`, `usageLog.ts`). |
| `viewer/` | The React/three.js viewer app (Vite root). Bundled with the hub: both the hub and the local server boot Vite with `viewer/` as root, and `public/` (bundled example builds) stays at the repo root. |
| `cli/` | The agent interface: the `buildviz` bin dispatcher (`buildviz.ts`), per-domain command modules (`commands/`), shared command plumbing (`cliBuild.ts`), and human-readable printers (`cliFormat.ts`). |

`scripts/` keeps repo-dev utilities only (demo generators / exporters).

> The commands below (`npm run dev`, `npm run buildviz`, `--port …`) are for
> **developing BuildViz itself** or one-off local debugging. To *view* project
> builds, use the single machine-wide hub instead — see
> [How to run BuildViz](#how-to-run-buildviz--one-central-instance-on-its-default-port).

To serve a BuildViz build from the current directory, put `scene.json` (and an
optional `design_spec.yaml`) in it and run:

```sh
npm run buildviz
```

You can point at a different build directory, design spec, or port:

```sh
npm run buildviz -- ../hexapod_2 --design-spec ../hexapod_2/design_spec.yaml --port 5174
```

To open the bundled hexapod prototype:

```sh
npm run hexapod
```

```sh
npm install
npm run dev
```

Open a build with:

```text
http://localhost:5173/?build=hexapod-2
```

Pass an explicit design spec with:

```text
http://localhost:5173/?build=hexapod-2&designSpec=/builds/hexapod-2/design_spec.yaml
```

## Multiple Builds

The viewer has a Build menu (top of the controls panel) that lists every
available project and build and lets you switch between them. Switching updates
the `?project=<p>&build=<b>` URL params (the older `?build=<full-id>` form still
works) and reloads the scene.

Builds are discovered through `/builds/index.json`:

- `npm run dev` serves it dynamically by enumerating `public/builds/*`.
- `npm run build` writes it into `dist/builds/index.json`.
- `npx buildviz` (the local server) serves an index for the single `local` build.

The index is **hierarchical** (`schema: 2`): a `projects[]` tree of builds and
their named versions, plus a `builds[]` flat list for older consumers. For other
static hosting, write a `builds/index.json` by hand:

```json
{
  "schema": 2,
  "projects": [
    {
      "id": "my-project",
      "name": "My project",
      "builds": [
        {
          "id": "my-project/assembly",
          "project": "my-project",
          "build": "assembly",
          "name": "Assembly",
          "defaultVersion": "main",
          "versions": [
            { "name": "main", "isDefault": true },
            { "name": "with-dome", "isDefault": false }
          ]
        }
      ]
    }
  ],
  "builds": [
    { "id": "my-project/assembly", "name": "Assembly", "defaultVersion": "main" }
  ]
}
```

If no index is served, the viewer still loads the build from the URL; the menu
just cannot list other builds.

## Build Hierarchy

A build id is `project/build`, where the first segment is the **project** and
the remaining segments are the **build** path. The build path may itself contain
`/` to group one project's many objects into a tree. For example, a single
project `spider` can hold many builds:

```text
spider/chassis        <- project "spider", build "chassis"
spider/leg            <- project "spider", build "leg"
spider/leg/coxa       <- project "spider", build "leg/coxa" (nested under the leg group)
```

Push, register, send, status, versions, diff, and the viewer URL all accept
these ids. In the URL, both the new `?project=…&build=…` form and the older
`?build=<full-id>` form work (literal `/` and percent-encoded `%2F` both work in
the `build` segment):

```sh
buildviz push --project spider --build chassis --version main -m "initial chassis" --scene chassis.json
buildviz push --project spider --build leg --version main -m "initial leg" --scene leg.json
buildviz versions spider/chassis
buildviz diff spider/chassis@main spider/chassis@with-dome --json
```

```text
http://localhost:5173/?project=spider&build=chassis
http://localhost:5173/?project=spider&build=chassis&version=with-dome&compare=main
```

`/builds/index.json` carries the hierarchy directly (the `schema: 2`
`projects[]` tree described under [Multiple Builds](#multiple-builds)). The Build
menu shows each project and `/` segment as a collapsible group, and each leaf is
a selectable build with its own name, version picker, and compare/diff controls.
Pushed builds are cached at `~/.buildviz/cache/<project>/<build>/` and rebuilt on
hub restart.

## Machine-Wide Hub

The **hub** is the single canonical cross-process target — the one server every
other program/project pushes to and reads from. It runs on its **own default
port `5183`**, deliberately distinct from a project's Vite app dev server
(`npm run dev`, default `5173`), so the two coexist permanently. A plain dev
server is purely local and is **never** the hub, even though it also serves
`/builds/index.json`. Use `--port` to override the hub port.

Start one BuildViz hub for the whole machine:

```sh
npx buildviz hub                 # default port 5183
```

This writes `~/.buildviz/server.json` with a `service: "buildviz-hub"` marker
plus the host, port, base URL, PID, version, and start time. It also uses
`~/.buildviz/registry.json` to remember registered local builds across hub
restarts. On every (re)start the hub rebuilds its build set from the cache and
prunes any registered build whose source directory no longer exists (logging a
warning and removing it from `registry.json`), so a restarted hub reliably
serves exactly the set of still-valid builds.

### Resolving the hub from another process

Always resolve the hub via discovery and **verify its identity** — never
hardcode a port, and never assume a server is the hub just because it answers
`/builds/index.json`. The hub's `GET /__buildviz/status` returns the signature
`{ service: "buildviz-hub", version, pid, port, baseUrl, startedAt, builds }`:

```sh
BASE=$(jq -r .baseUrl ~/.buildviz/server.json)
curl -s "$BASE/__buildviz/status" | jq -e '.service == "buildviz-hub"' >/dev/null \
  && echo "verified hub at $BASE"
```

The CLI (`push`/`register`/`send`/`status`) does this for you. If discovery is
missing, stale, or points at a non-hub (e.g. a dev server on the port), it
clears the stale discovery and auto-starts a fresh detached hub on `5183`.

### Hub Lifecycle (background daemon)

`npx buildviz hub` runs in the foreground (it never exits — Ctrl-C to stop). To
run the hub as a long-lived background daemon instead, use `--detach`:

```sh
npx buildviz hub --detach        # or: npx buildviz hub start --detach
```

`--detach` launches the hub in its own detached process group, redirects its
output to `~/.buildviz/hub.log`, writes the daemon pid to `~/.buildviz/hub.pid`,
waits until it answers `GET /__buildviz/status`, prints the URL, and exits `0`
without blocking. Starting again while a hub is already up is a no-op (it just
reports the running one), so it is safe to call repeatedly.

```sh
npx buildviz hub status          # is a hub running? url / pid / build count
npx buildviz hub stop            # stop the running hub, clear pid/discovery
npx buildviz hub restart         # stop, then start detached
```

`hub stop` reads the pidfile and `server.json`, terminates the hub's process
group (escalating to `SIGKILL` and finally killing the listener on the port if
needed), and clears the stale pidfile/discovery files. `hub status` never hangs:
it probes the status endpoint with a short timeout and reports cleanly when no
hub is running or the discovery file is stale.

`register`, `send`, and `push` **auto-start a detached hub** when none is
running, so you can push without managing the hub yourself. Pass
`--no-autostart` to fail fast instead when no hub is reachable.

From any project directory that has a `scene.json` and `design_spec.yaml`, send
that project to the running hub:

```sh
npx buildviz register . --project my-project --build assembly
```

`send` is an alias for `register`. Both point the hub at the on-disk directory
and overwrite its `scene.json` **in place** (no auto-archiving):

```sh
npx buildviz send . --project my-project --build assembly
```

The hub serves the project from its original directory, so large STL files are
not copied. It exposes the registered build in `/builds/index.json` and returns
a URL such as:

```text
http://127.0.0.1:5183/?project=my-project&build=assembly
```

Check discovery and registered builds with:

```sh
npx buildviz status
```

`status` prints the canonical hub URL (read from `~/.buildviz/server.json`) and
**warns** if it finds a non-hub server answering on another port — for example
the reserved BuildViz dev/test server on `:5173` (leave that one running/alone)
or an ad-hoc dev server on some random port (stop those). Projects should only
ever target the central hub on `:5183`.

The hub binds to `127.0.0.1` by default. If you pass `--host 0.0.0.0` or another
non-loopback host, treat it as unauthenticated local dev tooling and do not
expose it on untrusted networks.

### Push Layouts From Your Program

`register` points the hub at an on-disk directory. `push` lets any program send
a `scene.json` layout straight to the running hub by project/build/version — no
`public/builds/` directory to manage. The hub caches the layout under the named
version you target.

```sh
buildviz push --project my-project --build assembly --version main -m "<what changed and why>" --scene scene.json
cat scene.json | buildviz push --project my-project --build assembly --version with-dome -m "<what changed and why>"
```

The scene comes from `--scene` or stdin. Every push must name its change with
`-m "<one line: what changed and why>"` — pushes without a version message are
rejected (by the CLI and by the hub). Any of `--project`, `--build`, and
`--version` can be omitted and is auto-derived: `--project` from the git repo /
directory name, `--build` from the scene name / directory, and `--version`
defaults to **the next free `v<N>`**, just like `--bump`. This new version becomes
default unless you pass `--no-default` for a review. Published names are protected:
changed scene/spec content at an existing `--version` returns HTTP 409 and tells
you how to publish a new version. Identical retries preserve the original content,
message and timestamp. `--no-snapshot` cannot bypass this protection.
Pass `--set-default` to promote an explicitly named version. Each push prints which `project/build@version`
it landed as, plus the view URL and the hub URL.

`design_spec.yaml` is treated as part of the version: with no explicit
`--design-spec <file>`, a `design_spec.yaml` next to the pushed `--scene` file
is attached automatically, so the recorded intent travels with the geometry.
Both `push` and `register` return **design-spec warnings** (`warnings` in the
JSON response; printed with `⚠` by the CLI, and logged by the hub) when the
spec is missing, doesn't cover every scene part type, has entries for parts no
longer in the scene, or when the geometry changed without a spec update — on
push that means the scene bytes changed while the effective spec didn't (the
required `-m "<why>"` records the reason, but the spec should still be brought
up to date); on register it means `scene.json`
or a referenced mesh file is newer than `design_spec.yaml`. Warnings never
block; they exist so every edit's purpose gets written down. The viewer shows
the same spec-coverage warnings as an expandable amber badge under the version
dropdown, so drift stays visible even when nobody is watching the CLI output.

Or call the endpoint directly. curl:

```sh
# Resolve + verify the hub from discovery instead of hardcoding a port.
BASE=$(jq -r .baseUrl ~/.buildviz/server.json)
curl -s "$BASE/__buildviz/status" | jq -e '.service == "buildviz-hub"' >/dev/null || { echo "no verified hub"; exit 1; }
curl -sS -X POST "$BASE/__buildviz/push" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n --slurpfile s scene.json '{project:"my-project", build:"assembly", version:"main", message:"<what changed and why>", scene:$s[0]}')"
```

Node:

```js
import { readFile } from 'node:fs/promises'

const server = JSON.parse(await readFile(`${process.env.HOME}/.buildviz/server.json`, 'utf8'))
// Verify identity before trusting the endpoint.
const status = await (await fetch(`${server.baseUrl}/__buildviz/status`)).json()
if (status.service !== 'buildviz-hub') throw new Error(`Not a BuildViz hub at ${server.baseUrl}`)
const scene = JSON.parse(await readFile('scene.json', 'utf8'))
const res = await fetch(`${server.baseUrl}/__buildviz/push`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    project: 'my-project',
    build: 'assembly',
    version: 'main',
    message: '<what changed and why>', // required: names the version
    scene,
  }),
})
console.log((await res.json()).url)
```

Python:

```python
import json, os, urllib.request

base_url = json.load(open(os.path.expanduser("~/.buildviz/server.json")))["baseUrl"]
# Verify identity before trusting the endpoint.
status = json.load(urllib.request.urlopen(f"{base_url}/__buildviz/status"))
assert status.get("service") == "buildviz-hub", f"not a BuildViz hub at {base_url}"
scene = json.load(open("scene.json"))
req = urllib.request.Request(
    f"{base_url}/__buildviz/push",
    data=json.dumps({
        "project": "my-project",
        "build": "assembly",
        "version": "main",
        "message": "<what changed and why>",  # required: names the version
        "scene": scene,
    }).encode(),
    headers={"Content-Type": "application/json"}, method="POST",
)
print(json.load(urllib.request.urlopen(req))["url"])
```

Mesh assets are not uploaded. Pushed scenes must reference meshes that are
already reachable through the hub: absolute `http(s)` URLs, absolute
`/builds/<other-id>/...` URLs served by another registered/pushed build, or
relative URLs combined with `assetsBaseUrl` (a prefix for relative mesh URLs).

Every push is cached under `~/.buildviz/cache/<project>/<build>/` — the default
version at `scene.json`, other named versions under `versions/<name>/scene.json`,
alongside a `meta.json` — so branches stay viewable and diffable (see Build
Versions below).

## Build Versions

A build keeps **named, branch-like versions** (`main`, `with-dome`, …) rather
than an auto-incrementing `v1`/`v2` history. The default version lives at the
build-root `scene.json`; every other named branch lives under
`versions/<name>/scene.json`:

```text
public/builds/<project>/<build>/
  scene.json              <- default version (named "main"); "latest" aliases it
  design_spec.yaml
  stl/...
  versions/
    with-dome/
      scene.json          <- version "with-dome"
      design_spec.yaml    <- optional; falls back to the parent spec
```

Version manifests should reference mesh assets with absolute
`/builds/<project>/<build>/...` URLs so they can reuse the build's STL files
without duplicating them.

Open a version with:

```text
http://localhost:5173/?project=<project>&build=<build>&version=with-dome
```

Omitting `version` (or passing `version=latest`) opens the **default** version.
The Build menu shows a Version picker whenever multiple branches exist (the
default is marked). CLI commands accept `--version <name>`, and
`npx buildviz versions` browses the project → build → named-version hierarchy
(pass `npx buildviz versions <project>/<build>` to scope to one build):

```sh
npx buildviz versions                       # whole project → build → version tree
npx buildviz versions spider/chassis --json # one build's named versions
npx buildviz diff spider/chassis@main spider/chassis@with-dome --json
```

**Each push creates an immutable version.** Pushing without `--version` selects
the next `v<N>`; `--version with-dome` chooses a new name. Reusing a published
name with changed content is rejected. Use `--branch` for a parallel design and
a new version for each revision. Pass `--set-default` to make a named version the
build's default. Labels with spaces and capitals are canonicalized to a
URL/filesystem-safe slug used everywhere (cache dir, registry, `index.json`,
`?project=`/`?build=`), so `"Spider Chassis"` always maps to `spider/chassis`:

```sh
npx buildviz push --project spider --build chassis -m "reworked chassis" --scene scene.json   # -> v1 (default)
npx buildviz push --project spider --build chassis --version with-dome -m "dome variant" --scene dome.json
npx buildviz versions spider/chassis                                                  # v1 (default), with-dome
# viewer: /?project=spider&build=chassis&version=with-dome&compare=v1
```

> `push` protects existing versions and returns a link pinned to the exact version,
> even when it is the default. Use `--upload-assets` to preserve mesh bytes in the
> content-addressed store too: external/mutable asset URLs are not snapshots.
> `register`/`send` are live pointers to an on-disk directory, not version archives;
> use `freeze --bump` after regenerating an on-disk build.

### Migrating legacy builds

`buildviz migrate` non-destructively normalizes existing builds to this model —
it rewrites each `meta.json` so any existing `v1`/`v2` directories are preserved
as named versions and a legacy `latestVersion` becomes `defaultVersion`. Nothing
is deleted.

```sh
npx buildviz migrate --dry-run     # preview the meta.json changes
npx buildviz migrate               # apply them
npx buildviz migrate --cache-only  # only normalize the hub cache under ~/.buildviz
```

## Diff Mode

To visualize the changes between two named versions of the same build, pick a
version in "Compare with" in the Build menu, or open:

```text
http://localhost:5173/?project=<project>&build=<build>&version=main&compare=with-dome
```

The viewer renders the selected `version`, diffed against `compare`:

- Green: instances added in the selected version.
- Red (ghosted): instances removed since the compared version.
- Amber: instances that moved or changed (transform, mesh, or geometry).
- Gray: unchanged instances.

The same diff is available as structured JSON from the CLI. Address both sides
as `project/build@version`:

```sh
npx buildviz diff spider/chassis@main spider/chassis@with-dome --json
```

The legacy form `npx buildviz diff <build-dir> <from> <to>` still works.

## Per-Part History (searchable)

Where `diff` compares two whole versions, `history` answers "how did THIS part
evolve?": for every `partType`, the versions that changed its geometry (mesh
content-hash), design-spec description, or instance count — with timestamps and
push `-m` messages. History is kept in an append-only `part_history.json`
ledger per branch (updated on every push, lazily on read), so it survives
version-retention pruning of the underlying `versions/<name>/` snapshots.

```sh
npx buildviz history spider/chassis                    # summary: one row per part
npx buildviz history spider/chassis battery_holder    # one part's full timeline
npx buildviz history --search "hook chamfer"           # search every cached build + branch
```

Search matches part names + history text (descriptions, messages, versions;
case-insensitive AND semantics). The hub serves the same data at
`GET /__buildviz/part-history?build=<id>[&part=<type>][&q=<terms>][&branch=<b>]`,
and the MCP server exposes it as the `get_part_history` and
`search_part_history` tools. See BUILDVIZ_LLM_INTERFACE.md § "Per-Part History".

## Diagram Mode (agent presentation canvases)

When an agent wants to PRESENT an idea — a concept sketch, force/load diagram,
exploded or assembly-order walkthrough — instead of showing a build, it
composes a **diagram**: a standalone annotated 3D canvas with its own MCP API
and its own viewer mode, entirely separate from builds (no branches, versions,
or checks).

- **Elements**: boxes, spheres, cylinders, polylines, **arrows**, floating
  text, **callouts** with leader lines, and `part` elements that place real
  parts from any build on the hub (the mesh is snapshotted into the diagram so
  it stays self-contained). Coordinates are mm, Z-up; every element can carry a
  label/color/opacity.
- **MCP tools**: `create_diagram`, `update_diagram` (upsert/remove elements by
  id, retitle, move the camera), `get_diagram`, `list_diagrams`,
  `delete_diagram`. Mutations respect the hub's read-only bind mode.
- **Viewer**: `http://127.0.0.1:5183/?diagram=<name>` — dedicated chrome with
  the title, presenter notes, and a legend. The page polls the document
  (ETag/304) and picks up edits within ~2s, so an agent can narrate a diagram
  step by step while the human watches it change.
- **Storage**: `~/.buildviz/diagrams/<name>/` (`diagram.json` + `meta.json` +
  content-hashed `assets/`); served read-only at `GET /diagrams/index.json`
  and `GET /diagrams/<name>/diagram.json`.

See BUILDVIZ_LLM_INTERFACE.md § "Diagrams" for the element schema.

## STEP Import (`push-stl` / `push-step`)

BuildViz accepts STEP (`.step`/`.stp`) CAD files at ingest:

```sh
npx buildviz push-step assembly.step --project myproj --build widget -m "from CAD"
npx buildviz push-stl part.stl housing.step -m "bracket + housing"   # mixing STL + STEP works too
```

Every solid in the STEP assembly is tessellated via OpenCascade
(occt-import-js) into its own part, keeping the **names and colors from the
STEP assembly tree** — one STEP file can yield a whole multi-part build.
Coordinates are converted to mm. Tessellation quality is tunable with
`--linear-deflection <mm>` and `--angular-deflection <rad>`.

Internally BuildViz stays mesh-based (the checks / drawings / sections / mass
engines and the viewer are all triangle+BVH): STEP is an ingest format, and
the stored scene is standard STL-backed, so every downstream tool works
unchanged on imported CAD.

## Schematic Part Drawings

Both humans and agents can get engineering-style schematic drawings of a single
part: orthographic views straight down the axes (front / back / left / right /
top / bottom), with visible edges solid, hidden edges dashed, and each view
dimensioned in mm. The part is drawn in its own local (STL) frame.

- **Viewer** — open the **Drawings** panel, pick a part type, tick the views
  you want, and Generate; download the sheet as SVG.
- **CLI** — `npx buildviz drawing <build> --part <type> [--views all] [--out
  part.svg]` (see the LLM interface doc for the full contract).
- **MCP** — the hub exposes `get_part_drawing`, returning the same SVG sheet
  as text, so an agent can read exact silhouettes, hole positions, and
  proportions that are hard to infer from raw mesh data.

All three share one generator (`core/schematicDrawing.ts`): welded feature +
silhouette edge extraction, BVH-raycast hidden-line classification, and a
third-angle-style dimensioned sheet layout.

## Section Figures (2D Cross-Section Plots)

`buildviz section` cuts the **placed assembly** (world frame) on one or more
axis-aligned planes and renders a labeled, to-scale 2D figure — the section
plot an agent would otherwise hand-write with matplotlib for every design
question. Unlike `slice` (an occupancy grid for area/thickness *metrics*),
`section` extracts the exact mesh/plane contour loops to *look at*: holes read
as holes (even-odd fill), and everything sits on an mm grid with a legend.

```sh
npx buildviz section <build> --plane z=0 --out fig.png            # filled part silhouettes
npx buildviz section <build> --plane z=0,z=-4,z=17 --part chassis_bottom \
  --window 'x=60:120,y=20:80' --out corner.png                    # profiles across heights
npx buildviz section my/variant --plane z=0 --compare my/production \
  --compare-offset 0,0,-40.5 --out before_after.png               # dashed before/after overlay
```

One plane draws filled part silhouettes in the scene's instance colors;
several planes (same axis) draw per-plane colored outlines overlaid; and
`--compare` overlays a second build/branch/version as dashed red outlines —
the before/after review figure (`--compare-offset` aligns scenes that use
different world frames). Output is SVG (stdout or `--out fig.svg`) or PNG
(`--out fig.png`, rasterized via `@resvg/resvg-js`); `--json` adds per-plane
loop counts and net section areas (mm²) for base and compare. The hub MCP
server exposes the same generator (`core/sectionFigure.ts`) as
`get_section_figure`, returning the SVG as text.

## Mass Estimation (Weight + Weight Distribution)

BuildViz can estimate a build's total weight, world **center of mass**, and the
weight breakdown by part type and focus group, straight from the meshes: per
unique mesh it integrates the enclosed volume and volume centroid, then applies
a density — or a **known real mass** when the scene declares one.

- **Viewer** — the **Mass** panel: Estimate mass, see the heaviest part types
  as a bar list, and **Show CoM** pins a marker at the center of mass in 3D.
- **CLI** — `npx buildviz mass <build> [--density <g/cm3>] [--json]`.
- **MCP** — `get_mass_properties` returns the same report (total grams, CoM,
  CoM-in-bounds fractions, per-partType/per-group breakdowns with sources).

Mass per part resolves as: `checksConfig.partMassesGrams[partType]` (real
datasheet grams — use this for servos, batteries, PCBs) → volume ×
`checksConfig.partDensitiesGCm3[partType]` → volume × steel (7.85) for detected
fasteners → volume × `checksConfig.defaultDensityGCm3` (default 1.24, solid
PLA). Without configured masses everything is weighed as solid plastic, so
bought parts are underestimated — the report flags this.

## Weak-Spot FEA (MuJoCo → Gmsh → CalculiX → BuildViz)

The `fea/` module finds structural weak spots in robot parts with real linear
static FEA, then shows them on the actual build:

```sh
# 1. Worst-case loads: MuJoCo sim (needs an MJCF), or a static estimate from
#    the BuildViz mass report (single-foot landing is usually the killer):
uv run fea/loadcases_mujoco.py --mjcf robot.xml --drop-mm 150
uv run fea/loadcases_mujoco.py --static --from-build prototype_sts3215 --feet 6 --impact-g 3

# 2. Mesh the real part (STL or STEP) + solve + visualize:
uv run fea/weakspots.py femur_link.stl --inspect        # bbox + loadcase help
uv run fea/weakspots.py femur_link.stl \
  --loadcase fea/examples/femur_single_foot_landing.json \
  --build prototype_sts3215 --push-stress fea/femur-stress

# 3. Or run the WHOLE ROBOT in one command — load cases derived from the
#    assembly itself (contact interfaces detected per part; inboard clamped,
#    outboard takes the single-foot force). --push-analysis attaches the
#    stress view as a NAMED ANALYSIS PAGE on the build (viewer sidebar →
#    Analyses), not a separate build:
uv run fea/robot_weakspots.py prototype_sts3215 --push-analysis drop-stress

# 4. REALISTIC walking/rising loads: feed a measured MuJoCo walk-loads report
#    (rl_move probe_walk_loads.py; committed copies in fea/reports/) — the
#    heuristic suite is replaced by measured per-joint bending moments, servo
#    torques, and transmitted forces. --mujoco-report is repeatable and reports
#    merge by max: add the Onshape-study scenario summary (stand/walk/RISE/
#    LOWER — the belly-to-plant standup peaks ~2x the walking foot force) so
#    the envelope covers standing up, not just walking. Match the material to
#    how the parts are actually printed (PETG 25% infill ~ 22.7 MPa effective
#    yield, vs 50 for solid PLA):
uv run fea/robot_weakspots.py prototype_sts3215 \
  --mujoco-report fea/reports/walk_loads_dr05.json \
  --mujoco-report fea/reports/onshape_study_loads.json \
  --material "PETG 25% infill" --young-mpa 900 --yield-mpa 22.66 \
  --push-analysis walking-stress
```

`fea/robot_weakspots.py` analyzes every unique **printed** partType (bought
parts from `checksConfig.partMassesGrams` and fasteners are skipped, but still
serve as contact neighbors), prints a robot-wide safety-factor table, a
combined hotspot overlay URL, and can push a full-robot derived build where
every printed part is stress-colored in place — bought parts stay as context.
Each load-path part is screened against a suite of cases — single-foot
**landing** (3g vertical), **walking traction** (1.5g + friction, two
horizontal directions), and **servo-stall bending** (rise/lower and turning
scrub, sized by `--servo-torque-nm` over the part's lever arm) — the report
keeps the worst case per part and the stress view shows the envelope. Parts
outside the load path get a `--handling-n` press, and so do retention parts
(`cap|retainer|cover|lid` in the type name) — caps clamp a bearing or horn,
the joint moment bypasses them through the servo body, so feeding them the
full moment would fake yield-level stress on top of every servo. This is
heuristic screening; for a part-specific scenario, write a loadcase JSON and
use `fea/weakspots.py`.

With `--mujoco-report <json>` the heuristic suite is swapped for **measured**
loads from a walking sim: the report (produced by the weird_objects
`rl_move.sim.probe_walk_loads` probe rolling out the trained walk policy)
carries per joint-axis bending moments, servo torques, transmitted joint
forces, and foot ground forces. Each part is classified to the joint it
serves (yaw / hip-pitch / knee, from its interface neighbor names) and gets
walk-bend (lift + scrub planes), rise/lower servo-torque, and transmitted
joint-force cases sized from the measurement — `--mujoco-stat max|p95` picks
the statistic. `fea/reports/walk_loads_prod.json` is the deterministic
production gait; `walk_loads_dr05.json` is a domain-randomized sweep (payload,
friction, structure-stiffness variation) with ~20–40% higher maxima — use it
as the conservative envelope. Off-load-path parts keep the heuristic cases.

Pipeline: **Gmsh** tessellates the part into quadratic tets (STEP goes in
exact), **CalculiX** (`ccx`, `brew install costerwi/calculix/calculix-ccx`)
solves linear static elasticity, and the results land in BuildViz two ways:

- a **hotspot highlight URL** — top-K von Mises clusters pinned as colored
  markers (red = safety factor < 1.5) on the real build in the viewer;
- a **named analysis page** attached to the build (`--push-analysis <name>`,
  or `buildviz push-analysis` directly): the surfaces binned blue→red on ONE
  global scale anchored at the material yield (red = at/over yield), analyzed
  parts colored in place, everything else gray context. Pages live under the
  build (viewer sidebar → Analyses, or `?analysis=<name>`), so results never
  clutter the builds index; re-pushing the same name updates the page.
  (`fea/weakspots.py --push-stress <id>` still exists for a standalone
  derived build of a single part.)

Load cases are plain JSON (fixtures + point loads in the part's own mm frame,
material with yield strength; defaults to PLA). The console prints max von
Mises, max deflection, and a safety-factor verdict; `--out results.json`
captures everything for agents.

## Design Sanity Check

`buildviz check` is a fast, geometry-only sanity check that an agent can run on a
generated assembly **before** asking a human to look at it. It works from
`scene.json` plus its STL assets alone (no `design_spec.yaml` required) and
detects two classes of mistake that LLM-generated assemblies often get wrong:

- **Interference** — pairs of parts whose solids actually overlap in space,
  with an estimated **penetration depth** in mm.
- **Connectivity** — parts that are *floating* (not connected to the main
  assembly) and *suspicious gaps* (a part that nearly, but doesn't quite, touch).
- **Printability** — per-mesh slicer-readiness: non-**watertight** / non-manifold
  meshes and degenerate triangles (robust), plus an estimated minimum **wall
  thickness** (heuristic).
- **Assembleability** — per-fastener **thread engagement** / grip and per-part
  **assembly access** (can a part be installed/removed along a straight line) —
  both heuristic. See [the new check kinds](#printability--assembleability-offline-gate).

```sh
npx buildviz check public/builds/<project>/<build>
npx buildviz check public/builds/<project>/<build> --json
npx buildviz check public/builds/<project>/<build> --highlight-url
npx buildviz check public/builds/<project>/<build> --access   # add the opt-in assembly-access sweep
```

### How it works (and stays fast)

Each unique mesh is loaded and BVH-indexed once and reused by every instance. A
sweep-and-prune **broad phase** over world-space AABBs enumerates only candidate
pairs; a BVH-accelerated **narrow phase** then runs exact surface-distance and,
for intersecting pairs, an interior volume-sampling **penetration depth**. The
largest bundled build (~674 instances) checks in a couple of seconds.

- **Penetration depth** = the deepest interior point shared by two solids,
  measured as its distance to the nearest surface of either part. This reads ~0
  for intended *touching mates* (flush, coincident faces enclose no shared
  volume) yet correctly resolves shallow flat-face / edge clipping, so genuine
  interference is reported while mates are not.
- **Tolerance** (`--tolerance`, default `0.5mm`) is the surface separation under
  which two parts count as *in contact* for connectivity.
- **Min penetration** (`--min-penetration`, default `1.0mm`) is the depth at or
  above which an overlap is reported as a collision. Slightly-modelled press-fit
  mates sit a few tenths of a mm and are suppressed; real interference is deeper.
- **Fasteners are suppressed by default.** Screws, nuts, washers, heat-set
  inserts, and dowel pins are modelled to occupy their holes, so they interfere
  *by design*. Like every CAD interference checker, BuildViz ignores the fastener
  library (detected by a `fasteners/` asset path / `fasteners:` mesh id, or a
  hardware-style part name). Suppressed fasteners still act as connectivity
  *bridges* so the parts they join are not reported as floating. Pass
  `--include-fasteners` to analyze them too.

### Options

| Flag | Default | Meaning |
| --- | --- | --- |
| `--tolerance <mm>` | `0.5` | Contact separation for connectivity. |
| `--min-penetration <mm>` | `1.0` | Penetration depth at/above which to report a collision. |
| `--include-fasteners` | off | Also check fasteners (normally suppressed). |
| `--gap-window <mm>` | `8` | Surface a floating part as a "suspicious gap" within this distance. |
| `--max-pairs <n>` | `400000` | Cap on narrow-phase pairs; the report is flagged `capped` if exceeded. |
| `--min-wall <mm>` | `0.8` | Flag a mesh whose estimated min wall thickness is below this (heuristic). |
| `--min-thread-engagement <mm>` | `2.0` | Flag a fastener whose estimated grip is below this (heuristic). |
| `--wall-samples <n>` | `1500` | Upper bound on surface samples per mesh for the wall-thickness estimate. |
| `--checks <kind,kind>` | — | Run/report **only** these kinds (full allowlist; overrides group defaults). |
| `--no-printability` | — | Skip `watertight` / `wall_thickness` / `degenerate_geometry`. |
| `--no-assembleability` | — | Skip `thread_engagement` / `assembly_access`. |
| `--access` | off | Also run the coarse `assembly_access` extraction sweep (opt-in). |
| `--emit` | — | Write a `buildviz_checks.json` sidecar next to `scene.json` (the viewer paints it automatically). |
| `--highlight-url` | — | Always print the viewer highlight URL. |
| `--url <viewer>` | `http://127.0.0.1:5173` | Base viewer URL for the highlight link. |
| `--json` | — | Emit the structured envelope (primary contract). |

### Printability & assembleability (offline gate)

Beyond the live-surfaceable spatial checks above, `check` runs heavier
**offline-gate** kinds geometry-only (per *unique* mesh or per instance, reusing
the same cached BVHs). Each is clearly **robust** (exact) or **heuristic**
(estimate), and heuristic kinds only ever `warn` — they never `fail` a build:

| Kind | Group | Robust/Heuristic | Status | What it flags |
| --- | --- | --- | --- | --- |
| `watertight` | printability | **Robust** | `fail` | Open boundary edges (holes) or non-manifold edges (edge shared by ≠2 triangles); `warn` for inconsistent winding. Emits a `pass` per clean mesh. |
| `degenerate_geometry` | printability | **Robust** | `warn` | Zero-area triangles. |
| `wall_thickness` | printability | *Heuristic* | `warn` | Min wall below `--min-wall`. Estimated by casting inward rays from surface samples to the opposing wall; reported as a low **percentile** of samples (so a lone stray ray can't flag a thick mesh). Not an exact medial-axis thickness. |
| `thread_engagement` | assembleability | *Heuristic* | `warn` | A fastener gripping less than `--min-thread-engagement`. Estimated as the axial length over which a ring just outside the shaft is surrounded by host material. Only *axial* fasteners (screws/bolts/inserts/standoffs) are tested; washers/squat nuts are skipped. |
| `assembly_access` | assembleability | *Coarse heuristic* | `warn` | A part with **no** collision-free straight-line install/removal direction (±X/±Y/±Z + radial-out, AABB-shadow sweep). **Opt-in** (`--access`): in a dense assembly most interlocked parts are flagged, so treat it as a way to spot fully-enclosed parts, not a pass/fail gate. |

Defaults run `watertight` + `degenerate_geometry` + `wall_thickness` +
`thread_engagement` (all fast and low-false-positive). `assembly_access` is
opt-in. Toggle whole groups with `--no-printability` / `--no-assembleability`,
or pick exactly what runs with `--checks watertight,thread_engagement,…`.
Printability runs on printed parts only (the fastener library is skipped).

> **Gate vs surface.** These offline-gate kinds reuse the same `checks[]` schema
> and `buildviz_checks.json` sidecar, so they still *paint* in the viewer's
> Checks panel — but unlike the spatial checks the panel's **Run live checks**
> button does not recompute them (they are CLI/CI-oriented).

### Motion: pose scrubber & swept-pose validation

If a `scene.json` carries an additive `joints[]`/`poses[]` kinematics block, the
viewer adds a **Motion** panel — one slider per joint (clamped to its limits),
named-pose buttons, an **Animate sweep**, and **Reset to home** — that re-poses the
build via forward kinematics (rotate about each joint's `axis` through its `origin`,
composed up the `parent` chain, applied on top of the static home transform). Scenes
without joints are unchanged and the panel is hidden.

The **Run swept checks** button (Checks panel) and the headless CLI both sweep each
DOF across its range (+ named poses) and re-run the overlap engine **per pose**,
reporting the **worst-case envelope** per instance pair — surfaced as
`swept_overlap` / `swept_clearance` records labeled with the worst pose. It reuses
the cached per-geometry BVHs (no rebuilds): a cheap AABB proxy ranks poses, then the
precise interior-grid penetration / surface-distance test runs once per pair at its
worst pose. The viewer gates to visible/focused parts by default.

```bash
npx buildviz sweep public/builds/hexapod-motion-demo            # whole-build sweep, worst-case table
npx buildviz sweep public/builds/hexapod-motion-demo --samples 24 --emit
```

Try it on the bundled **`hexapod-motion-demo`** build (a self-contained copy of
`hexapod-prototype` augmented with 18 revolute joints + named poses):
`http://127.0.0.1:5183/?build=hexapod-motion-demo`. It sweeps 72 parts × 148 poses
in ~1.4 s. The joint schema an exporter should emit is documented in
`BUILDVIZ_INTEGRATION.md` (and `npx buildviz docs`).

### Wiring: publish, see, and validate the harness

A scene can publish its wires/cables as an additive `routes[]` block (see
`plans/wiring.md` for the design and the research behind it). Each route has a
`kind` (power/signal/data/…), a bundle `diameterMm`, and a path of waypoints
that are either world-frame `position`s or **anchored to an instance**
(`instanceId` + part-local `local`) so wires follow their parts across versions
and kinematic poses. `anchor: true` marks a physical attachment (clip / tie).

- **See them in the hub:** builds with routes get a **Wiring** control group in
  the viewer — a show/hide toggle plus a per-wire color legend. Wires render as
  tubes through the published path with spheres at anchor points, and follow
  the Motion scrubber.
- **List them:** `npx buildviz wires <build>` prints each wire's routed length
  (vs its optional `maxLengthMm` budget), tightest bend radius vs the allowed
  minimum (explicit `minBendRadiusMm` or 6 × OD), anchors, and longest
  unsupported span.
- **Validate them:** `npx buildviz check` runs the wiring gates by default —
  `routing_reach` (length budget + passes-through-solid obstruction, fail),
  `wire_bend_radius` (fail), `wire_support` (span between anchors over
  `--max-span`, default 150 mm — the "add a clip/tie here" nudge, warn), and
  `wire_clearance` (wire surface within `--wire-clearance`, default 1 mm, of a
  non-termination solid — chafing risk, warn).
- **Document them:** each route id gets a `wiring:` entry in `design_spec.yaml`
  recording its purpose; the hub's push/register warnings and the viewer badge
  flag undocumented or stale wires, same as parts.

Try it on the bundled **`hexapod-prototype`** build, which publishes its 6-wire
power/I²C harness: `http://127.0.0.1:5183/?build=hexapod-prototype`.

### JSON shape

`--json` is the primary contract. It returns the standard envelope
(`ok` / `build` / `summary` / `results` / `warnings` / `errors`). `ok` is `true`
on any successful run **regardless of whether problems were found**; inspect
`results.passed` (and `results.problemCount`) to gate on cleanliness:

```jsonc
{
  "ok": true,
  "build": { "id": "hexapod-collision-chassis", "version": "latest", "units": "mm" },
  "summary": "Found 4 colliding pair(s) and 2 floating part(s).",
  "results": {
    "passed": false,
    "problemCount": 6,
    "toleranceMm": 0.5,
    "minPenetrationMm": 1.0,
    "instanceCount": 6,
    "fastenersExcluded": 0,
    "fastenersIncluded": false,
    "broadPhasePairs": 5,
    "collisions": [
      { "a": { "instanceId": "coxa_link", "partType": "coxa_link" },
        "b": { "instanceId": "chassis_top", "partType": "chassis_top" },
        "penetrationMm": 1.667 }
    ],
    "floating": [
      { "instanceId": "tibia_link", "partType": "tibia_link", "nearestGapMm": 1.619,
        "nearestInstanceId": "femur_link" }
    ],
    "gaps": [ /* ... */ ],
    "timings": { "totalMs": 360, "narrowMs": 300, "broadMs": 1 },
    "checkSummary": { "fail": 4, "warn": 3, "pass": 4, "total": 11, "byKind": { /* ... */ } },
    "checks": [
      { "id": "mesh_overlap-0", "kind": "mesh_overlap", "status": "fail",
        "label": "coxa_link ∩ chassis_top = 1.667mm penetration",
        "instances": ["coxa_link", "chassis_top"] }
    ],
    "highlightUrl": "http://127.0.0.1:5173/?build=...&highlight=...",
    "highlights": { "parts": [ /* red = fail, amber = warn */ ] }
  }
}
```

### Check records, sidecar, and `checksConfig`

`check` also produces generic **`checks[]`** records —
`{ id, kind, status, label, instances?, point? }` with `status` of
`pass | warn | fail` and `kind` of `mesh_overlap`, `clearance`, `connectivity`,
`placement`, `scene_meta`, `watertight`, `degenerate_geometry`, `wall_thickness`,
`thread_engagement`, or `assembly_access`. The web viewer surfaces these in a clickable
**Checks panel**: click a finding to highlight the involved parts and, for an
overlap, **shade the interpenetrating volume** in place (a translucent box at the
contact region, not just an outline of the whole parts). The panel header shows a
`N fail · M warn` badge and the list has triage toggles — **show only
fails/warns**, **mute allowed matings** (the `pass (allowed)` rows from
`allowedInterferences` / legacy `ignoreOverlapPairs`), and a **per-kind
filter**. The viewer reads records from
(in order) `scene.checks` inlined in `scene.json`, a `buildviz_checks.json`
sidecar (written by `--emit`), and a live in-browser run.

**Run live checks** recomputes the fast spatial kinds in the browser. By default
it is scoped to the **visible + focused** instances (and only loads their meshes),
so it stays interactive on the largest builds; **Run full-scene checks** runs the
complete pass. On the bundled hexapod-2 (674 instances) the full pass is ~1.4 s,
while a single focused leg (~109 instances) is ~0.15 s.

Express project intent as **data** in `scene.json` (both fields additive and
ignored by older viewers):

```jsonc
"checksConfig": {
  "minPenetrationMm": 1.0,
  "clearanceMm": 0.5,
  "minWallMm": 0.8,                              // printability: wall_thickness threshold
  "minThreadEngagementMm": 2.0,                  // assembleability: thread_engagement threshold
  // Intentional interferences, declared per INSTANCE pair with a typed kind,
  // a required reason, and an optional penetration cap. Each entry allows
  // exactly one documented feature and is itself audited on every run.
  "allowedInterferences": [
    {
      "kind": "thread_engagement",               // press_fit | bearing_seat | heat_set_insert | glue_joint | wire_entry | modeled_union
      "instances": ["m2-screw-rocker", "base-frame"],
      "feature": "left-front rocker anchor M2 pilot",
      "maxPenetrationMm": 1.1,                   // deeper than this still FAILS
      "reason": "M2 self-tapping screw intentionally cuts into the pilot hole"
    }
  ],
  // LEGACY blanket ignore, by partType pair. Too broad (suppresses EVERY
  // overlap between those types) — every run warns while this is non-empty,
  // and it is REFUSED between parts that joints[] move relative to each other.
  "ignoreOverlapPairs": [["spider_eye", "spider_carapace"], ["bushing", "housing"]]
}
```

**Overlap gate:** every unexpected solid-on-solid penetration ≥ `minPenetrationMm`
fails as `mesh_overlap`. Declare press-fits / intentional interference in
`checksConfig.allowedInterferences` — one entry per instance pair with a typed
`kind`, a `reason`, and (recommended) a `maxPenetrationMm` cap — so they stay
auditable without failing the build. Every declared entry is verified by the
`declared_interference` check: stale entries (parts no longer touching), dangling
instance ids, and over-cap penetrations all **fail**, so the allowlist cannot
rot. The legacy `ignoreOverlapPairs` (partType pairs, order-independent) still
works for static parts but warns on every run and never applies to parts in
relative motion (per `joints[]`) — two moving printed bodies are only joined by
a real fastener/pin/bearing or a declared entry, never by a blanket ignore.
Unexpected overlaps also no longer count as "connected" for the connectivity
check, so a bad overlap cannot mask a floating part. Fasteners are excluded by
default (they occupy holes by design). CLI flags override the scene config. See
`public/builds/overlap-allowlist-demo` for a worked example of all three cases.

### Agent self-check workflow

1. Generate / update `scene.json` (and its STL assets).
2. Run `npx buildviz check . --json` and read `results.passed`.
3. If `passed` is `false`, the `collisions` and `floating` arrays name the exact
   instances and penetration depths to fix — or open `results.highlightUrl` to
   show the offending parts in the viewer (colliding parts in red, floating parts
   in amber, each with an annotation) and ask a human.

## Pack for 3D printing (`buildviz pack`)

`buildviz pack` lays a build (or a single assembly) out for FDM printing: it
picks a **print orientation** per unique mesh and **packs** the oriented part
footprints onto one or more printer plates.

```bash
npx buildviz pack public/builds/hexapod-prototype --printer x1c --json
npx buildviz pack public/builds/hexapod-prototype --assembly L0 --emit   # pack one leg, emit a viewer scene
npx buildviz pack public/builds/hexapod-prototype --printer h2d --spacing 8 --margin 6
npx buildviz pack public/builds/hexapod-prototype --bed 300x300x340      # custom bed WxDxH (mm)
```

Both stages are **heuristics** (it is *not* a slicer), and both reuse the shared
STL loader / BVH from the interference checker:

- **Orientation (printability heuristic).** For each unique mesh it scores a set
  of candidate rest orientations — the 6 axis-aligned rests **plus** the largest
  natural facets (area-weighted triangle-normal clusters, i.e. faces a part can
  sit flat on) — and picks the best one that still fits the bed. The score is
  dominated by **support need** (downward-facing triangle area tilted more than
  the self-support angle, default `--angle 45`° from vertical), rewards **bed
  contact area** (adhesion/stability) and penalizes a tiny footprint relative to
  height (tipping), and treats **height** as a mild secondary penalty. Caveat: it
  does not detect self-supporting **bridges** or compute support *volume*.
- **Packing (shelf bin-packing heuristic).** A shelf/skyline packer sorts parts
  tallest-shelf-first and places footprint AABBs left→right with `--spacing`,
  keeping a `--margin`/brim allowance clear of the bed edge; a part that overruns
  the bed width wraps to a new shelf and one that overruns the depth starts a new
  **plate**. Any single part too big for the bed (even rotated 90°) — or too tall
  for the build height — is rejected with a clear error.

| Printer | Bed (W×D×H mm) |
| --- | --- |
| `x1c` (default) | 256 × 256 × 256 |
| `h2d` | 350 × 320 × 325 |

Operating on a build packs the **whole** build; `--assembly <name>` narrows to
one `focusGroup`/`leg` within it (e.g. `--assembly L0`). Fasteners are excluded
(not printed). `--json` returns the standard envelope with per-plate utilization
and, per part, the chosen orientation (`rotation` matrix + `rotationEulerDeg`),
plate index, plate `position`, `footprint`, `heightMm`, and `supportAreaMm2`.
`--emit` writes a `buildviz_pack.json` layout scene next to `scene.json` (parts
re-posed onto plate coordinates with a plate-boundary slab drawn) and prints an
`?scene=…` viewer URL so you can **see** the layout in the existing viewer.

### Export plates to a slicer (`--export`)

`--export` writes the packed layout to a **Bambu-ingestible** format — one file
per plate, with every part already placed at its packed XY and chosen print
orientation, so the file opens with parts arranged on the bed:

```bash
npx buildviz pack public/builds/hexapod-prototype --printer h2d --export                 # plate-1.3mf … plate-N.3mf -> <build>/plates/
npx buildviz pack public/builds/hexapod-prototype --assembly L0 --export --format stl     # per-plate merged STL instead
npx buildviz pack public/builds/hexapod-prototype --export --out /tmp/plates              # custom output directory
```

- **`--format 3mf` (default).** Each `plate-N.3mf` is a valid OPC zip containing
  `[Content_Types].xml`, `_rels/.rels`, and `3D/3dmodel.model` (core 3MF
  namespace, `unit="millimeter"`) with one `<object>`/`<mesh>` per part and a
  `<build>` `<item>` per part carrying the baked placement `transform`. This is
  what Bambu Studio and most slicers ingest directly. The geometry and
  orientations are exactly what `pack` computed (no recomputation).
- **`--format stl`.** A per-plate **merged** binary STL (all parts baked into one
  solid in plate coordinates) as a fallback for tools that don't read 3MF.
- `--out <dir>` overrides the default `<build>/plates/` location. The command
  prints the absolute output directory and every per-plate file path.
- The viewer exposes the same export via an **"Export plates"** control in the
  controls panel; it POSTs to `/__buildviz/pack-export`, runs the pack + export
  server-side, and shows the returned output directory and per-plate file paths
  (copyable). The control is **always available** — any BuildViz hub server
  (local or remote) can write the files — and shows a clear "Export needs a
  BuildViz hub backend" error if the viewer turns out to be served by a plain
  static file server with no `/__buildviz/*` endpoints. Two buttons act on the
  result: **"Open folder"** reveals the output directory in the OS file manager
  (via `POST /__buildviz/open-path`, sandboxed to the project / `~/.buildviz` /
  registered-build directories, no shell) and is shown only when the viewer is
  loaded from the hub host itself (a loopback address), since the folder opens
  on the hub machine; and **"Show in viewer"** loads the
  packed plate layout in the viewer (the export also emits the build's
  `buildviz_pack.json`, the same scene `pack --emit` writes, and navigates to
  its `?scene=` URL).
- Every assembly also gets an **"Open STL folder"** link right under the build
  dropdown whenever it is possible: the hub resolves where the selected
  build/branch/version's STL files live on disk (`GET /__buildviz/stl-dir` —
  a registered build's `stl/` directory, or the shared content-addressed
  `~/.buildviz/cache/_assets/` store for pushed builds) and the click reveals
  that directory via the same sandboxed `POST /__buildviz/open-path`. Like
  "Open folder", the link only appears on a loopback host, and it hides itself
  when no STL files resolve to this machine's disk (e.g. a primitives-only
  scene or a remote hub).

> Follow-ups (not yet implemented): richer Bambu-specific plate config
> (per-plate slicer settings / project metadata beyond core 3MF), per-part STL
> mode, and serving packed layouts as first-class hub builds. Note: tiny
> fastener/screw parts are excluded from packing (and therefore export) already.

## Docs

- `npx buildviz docs`: print the docs, expected project files, generated
  guidance files, and useful commands from inside a consuming project.
- `BUILDVIZ_INTEGRATION.md`: LLM-facing setup guide for projects that want to use BuildViz.
- `BUILDVIZ_COMPATIBILITY.md`: what a "BuildViz-compatible project" is (required
  files) and how to self-check with `buildviz compat <dir>`.
- `BUILDVIZ_LLM_INTERFACE.md`: CLI/API guide for agents querying builds, generating
  highlight URLs, and capturing screenshots.
- `ROADMAP.md`: the single working roadmap — what's shipped plus remaining /
  proposed work by area (deeper per-area design docs live under `plans/`).
- `DESIGN_YAML_SPEC.md`: Minimal schema for `design_spec.yaml`.
