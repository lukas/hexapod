# BuildViz Integration Guide

This document is for LLMs and agents wiring another project into BuildViz.

BuildViz is a generic web viewer for generated physical designs. A project uses
BuildViz by exporting static build assets into a web-served directory. BuildViz
should not contain project-specific CAD logic.

## Data Model: Project / Build / Named Version

BuildViz organizes everything as **project → build → version**:

- A **project** groups related builds (e.g. `spider`).
- A **build** is one assembly inside a project (e.g. `chassis`).
- A **version** is a **named, branch-like** snapshot of a build (e.g. `main`,
  `with-dome`). Versions are *not* auto-numbered `v1`/`v2`; you name them, and a
  build can carry several parallel branches at once.

Addressing:

- Address a build as `project/build` (e.g. `spider/chassis`).
- Address a specific version as `project/build@version` (e.g.
  `spider/chassis@with-dome`).
- The build id on disk *is* `project/build`. Slashes may go deeper: a build id
  `spider/leg/coxa` is project `spider`, build `leg/coxa`.
- Slugs are canonicalized: a label like `"Spider Chassis"` resolves to
  `spider/chassis`.

Default version:

- Each build has exactly **one default version**, named `main` unless you choose
  otherwise. `latest` is an alias for whatever the default is.
- The default version lives at the build-root `scene.json`; every other named
  version lives under `versions/<name>/scene.json`.

## Required Output

Export one folder per build:

```text
public/builds/<project>/<build>/
  scene.json            <- required (the build's default version)
  design_spec.yaml      <- optional
  stl/
    part_a.stl
    part_b.stl
```

`scene.json` tells BuildViz what meshes to load and where to place them. It is
the only required file: a build with a valid `scene.json` and its referenced
mesh assets can be registered, served, and rendered.

`design_spec.yaml` is optional. When present it tells BuildViz what the parts,
features, and dimensions mean and powers labels, overlays, and the YAML panel.
When absent, the build still loads; requests for the missing spec return 404
and the viewer simply omits the semantic overlays.

## Build Versions

A build keeps multiple **named, branch-like** versions. The default version
lives at the build root; other named versions live in subdirectories:

```text
public/builds/<project>/<build>/
  scene.json              <- default version (named "main"; "latest" aliases it)
  design_spec.yaml
  stl/...
  versions/
    with-dome/
      scene.json          <- named version "with-dome"
      design_spec.yaml    <- optional; falls back to the parent spec
```

Rules:

- The root `scene.json` is the **default** version (default name `main`).
  `latest` is an alias for the default.
- A version is any directory under `versions/` that contains a `scene.json`; its
  name is the directory name (`main`, `with-dome`, …) — there is no auto
  numbering.
- A build may hold several parallel branches at once; exactly one of them is the
  default.
- Version manifests should reference mesh assets with absolute
  `/builds/<project>/<build>/...` URLs so they reuse the parent build's mesh
  files instead of duplicating STLs. Keep `instance.id` and `mesh.id` stable
  across versions so diffs can match them up.

Open a version with `/?project=<p>&build=<b>&version=with-dome`, and compare two
versions with `/?project=<p>&build=<b>&version=main&compare=with-dome` (added
parts green, removed parts ghosted red, moved/changed parts amber).

You don't have to hand-roll this layout. For a register-based build that carries
its own local STL files, `buildviz freeze <build-dir>` writes the
`versions/<name>/scene.json` (+ `design_spec.yaml` + relative `stl/...` assets) and
`meta.json` **in place** — the local sibling of `push`.

- `buildviz freeze <build-dir> --bump` auto-picks the **next free `v<N>`** (v1,
  v2, …) and makes it the default. This is the clean **"every revision is a new
  version"** path: run it after each regenerate and history accumulates on disk.
- `buildviz freeze <build-dir> --version <name>` names the version explicitly;
  `--set-default` mirrors it to the build root.
- **Overwriting the default in place** (e.g. `freeze --version main --force`)
  first **snapshots the prior default** as a fresh `v<N>` so it survives (only
  when the content actually changed; opt out with `--no-snapshot`).
- `--keep <n>` bounds growth by pruning the oldest non-default versions
  (snapshots included; the default is never pruned).
- `-m`/`--message <text>` is **required**: a changelog note naming the frozen
  version (written into `meta.json`), surfaced in the viewer. Only a re-freeze
  of a version that already carries a message may omit it (the note is kept).
- `--force` overwrites an existing (immutable) named version.

Absolute (`http(s)` or `/builds/...`) mesh URLs pass through untouched; only
relative-URL assets are copied into the version dir.

## Build Discovery

The viewer's Build menu lists builds from `/builds/index.json`. The index is
**hierarchical** (`schema: 2`): a list of projects, each with its builds, each
build carrying its named versions and which one is the default. A flat `builds`
list of the same build objects is included alongside for convenience:

```json
{
  "schema": 2,
  "projects": [
    {
      "id": "spider",
      "name": "spider",
      "builds": [
        {
          "id": "spider/chassis",
          "project": "spider",
          "build": "chassis",
          "name": "Spider chassis",
          "defaultVersion": "main",
          "versions": [
            { "name": "main", "isDefault": true, "pushedAt": "2026-06-26T12:00:00.000Z" },
            { "name": "with-dome", "isDefault": false, "pushedAt": "2026-06-26T13:00:00.000Z", "message": "added the dome" }
          ]
        }
      ]
    }
  ],
  "builds": [
    {
      "id": "spider/chassis",
      "project": "spider",
      "build": "chassis",
      "name": "Spider chassis",
      "defaultVersion": "main",
      "versions": [
        { "name": "main", "isDefault": true, "pushedAt": "2026-06-26T12:00:00.000Z" },
        { "name": "with-dome", "isDefault": false, "pushedAt": "2026-06-26T13:00:00.000Z", "message": "added the dome" }
      ]
    }
  ]
}
```

Each version object also carries an optional `pushedAt` (ISO timestamp) and an
optional `message` (the changelog note from `push`/`freeze -m`, present only when
one was set). The BuildViz dev server serves this index automatically by enumerating
`public/builds/*`, `npm run build` writes it into its output, and the `buildviz`
local server serves an index for the single `local` build. Other static hosts
can write the file by hand. The index is optional: without it the viewer still
loads builds from the URL.

## Build Hierarchy (the `/` convention)

The build id `project/build` may itself contain extra `/` separators so one
project can group its many objects into a tree. The first segment is always the
**project**; everything after it is the **build** path. A project like `spider`
can therefore hold many objects, each with its own named versions:

```text
spider/chassis        <- project spider, build chassis: scene.json + versions/
spider/leg            <- project spider, build leg
spider/leg/coxa       <- project spider, build leg/coxa (nested under the leg group)
```

Rules:

- Each segment uses the same safe characters as a flat id
  (`A-Z a-z 0-9 . _ -`); segments are joined with `/`. `.` and `..` segments are
  rejected so a slashed id can never escape the build/cache root.
- A **leaf** id is a concrete build with its own `scene.json` and named
  `versions[]`. Intermediate segments (`spider`, `spider/leg`) are groups in the
  menu; a group may also itself be a build if a `scene.json` exists at that path.
- `/builds/index.json` is hierarchical (`schema: 2`): projects → builds →
  versions, with a flat `builds[]` list of the same objects alongside. The
  viewer rebuilds the tree from the build path; the flat list keeps simple
  lookups working.
- On disk, a hierarchical build nests naturally:
  `public/builds/spider/chassis/scene.json` for static hosting, or
  `~/.buildviz/cache/spider/chassis/` for pushed builds.

Push, register, send, status, versions, diff, and the viewer URLs all accept
slashed ids and the `project/build@version` address. In a URL both a literal `/`
and a percent-encoded `%2F` resolve to the same build, and asset subpaths (mesh
files, `versions/<name>/scene.json`, `design_spec.yaml`) under a nested id
resolve correctly:

```sh
buildviz push --project spider --build leg/coxa --version main -m "initial coxa" --scene coxa.json --name "Coxa"
buildviz versions spider/leg/coxa --json
buildviz diff spider/leg/coxa@main spider/leg/coxa@with-dome --json
```

```text
/builds/spider/leg/coxa/scene.json
/builds/spider/leg/coxa/versions/with-dome/scene.json
/?project=spider&build=leg/coxa&version=with-dome&compare=main
```

In the viewer's Build menu, each `/` segment renders as a collapsible group and
each leaf is a selectable build with its name, version picker, and compare/diff
controls.

## Machine-Wide Local Hub

The **hub** is the single canonical cross-process target: the one server every
other process/project pushes to and reads from. It is distinct from a project's
own app dev server. The hub runs on its **own default port `5183`** so it can
coexist permanently with a project's Vite dev server (`npm run dev`, default
`5173`). A plain dev server is purely local and is **never** the hub — even
though it also serves `/builds/index.json`. Use `--port` to override the hub
port.

For local development across many projects, run one BuildViz hub on the machine:

```sh
npx buildviz hub            # foreground (never exits), default port 5183
npx buildviz hub --detach   # background daemon: prints URL, exits 0
npx buildviz hub --lan      # bind a LAN address, READ-ONLY remote viewing
```

**Remote / shared viewing.** By default the hub binds loopback `127.0.0.1`
(full read/write). `--lan` (auto-pick a non-loopback address) or `--host <addr>`
binds a non-loopback address so teammates on a **trusted private network** can VIEW
your builds. Off-loopback the hub is **READ-ONLY**: view/read routes (the app,
`/builds/...`, `/builds/index.json`, `GET /__buildviz/status` → `readOnly: true`)
stay up, but every mutation/host-action endpoint (`POST /__buildviz/push`,
`pack-export`, `register`, `open-path`) returns `403`. There is **no app auth**
(private-network trust model); the CLI prints an exposure warning on bind. Never
expose the hub on an untrusted network.

`--detach` runs the hub as a first-class background daemon: it starts in a
detached process group, redirects output to `~/.buildviz/hub.log`, writes the
daemon pid to `~/.buildviz/hub.pid`, waits until it answers
`GET /__buildviz/status`, prints the URL, and exits `0` without blocking.
Starting again when one is already running is a safe no-op. Manage it with:

```sh
npx buildviz hub status     # running? url / pid / build count (never hangs)
npx buildviz hub stop       # stop the hub, clear pidfile + discovery files
npx buildviz hub restart    # stop, then start detached
```

`register`, `send`, and `push` **auto-start a detached hub** when none is
reachable, so a generator can push without managing the hub. Pass
`--no-autostart` to fail fast instead. Agents should never run `buildviz hub` in
a blocking foreground shell — use `--detach` or rely on autostart.

The hub writes `~/.buildviz/server.json`, which carries a `service` marker so a
reader can tell a real hub discovery file from anything else:

```json
{
  "service": "buildviz-hub",
  "version": "0.0.0",
  "host": "127.0.0.1",
  "port": 5183,
  "baseUrl": "http://127.0.0.1:5183",
  "pid": 12345,
  "startedAt": "2026-06-11T16:00:00.000Z"
}
```

### Resolving and verifying the hub

Programs must **resolve the hub via discovery and verify its identity** before
using it — never hardcode a port, and never assume a server is the hub just
because it answers `/builds/index.json` (a plain dev server does too). The hub's
`GET /__buildviz/status` returns an unmistakable signature:

```json
{
  "ok": true,
  "service": "buildviz-hub",
  "version": "0.0.0",
  "server": { "service": "buildviz-hub", "pid": 12345, "port": 5183, "baseUrl": "http://127.0.0.1:5183", "startedAt": "..." },
  "builds": [{ "id": "spider/chassis", "project": "spider", "build": "chassis", "name": "Spider chassis", "defaultVersion": "main", "versions": [{ "name": "main", "isDefault": true }, { "name": "with-dome", "isDefault": false }] }]
}
```

Resolve + verify the hub like this (read `server.json`, then confirm
`service === "buildviz-hub"`):

```sh
# curl + jq
BASE=$(jq -r .baseUrl ~/.buildviz/server.json)
curl -s "$BASE/__buildviz/status" | jq -e '.service == "buildviz-hub"' >/dev/null \
  && echo "verified hub at $BASE"
```

```js
// node
import { readFile } from 'node:fs/promises'
import os from 'node:os'
const info = JSON.parse(await readFile(`${os.homedir()}/.buildviz/server.json`, 'utf8'))
const status = await (await fetch(`${info.baseUrl}/__buildviz/status`)).json()
if (status.service !== 'buildviz-hub') throw new Error(`Not a BuildViz hub at ${info.baseUrl}`)
```

```python
# python
import json, os, requests
info = json.load(open(os.path.expanduser("~/.buildviz/server.json")))
status = requests.get(info["baseUrl"] + "/__buildviz/status").json()
assert status.get("service") == "buildviz-hub", "not a BuildViz hub"
```

The CLI does this verification for you: `register`, `send`, `push`, and `status`
all resolve discovery and verify the signature before acting. `buildviz status`
prints the canonical hub URL straight from `server.json` and **warns** if a
non-hub server (e.g. a stray Vite dev server on `:5173`) is listening where the
hub should be — `5173` is the dev/viewer server, never the hub. If discovery is
missing, stale (dead pid), or points at a non-hub, the CLI clears the stale
discovery and — for `push`/`register`/`send` — auto-starts a fresh detached hub
on the canonical port `5183`, then proceeds.

From any project, register the nearest BuildViz build root (`send` is an alias).
Registration points the hub at the on-disk directory and **overwrites its
`scene.json` in place** with no archiving:

```sh
npx buildviz register . --project spider --build chassis
```

The command reads the discovery file and posts to `POST /__buildviz/register`
with:

```json
{
  "buildDir": "/absolute/path/to/project",
  "buildId": "spider/chassis",
  "designSpecPath": "/absolute/path/to/project/design_spec.yaml",
  "name": "Spider chassis"
}
```

Only `scene.json` is required to register. `designSpecPath` is optional: if it
points at a missing file the build still registers, and the hub records no spec
for it and returns 404 for `/builds/<project>/<build>/design_spec.yaml`.

The register response carries a `warnings: string[]` array of **design-spec
warnings** (never blocking): a missing `design_spec.yaml`, scene part types with
no `parts:` entry, spec entries for parts no longer in the scene, or a spec
whose mtime is older than `scene.json` / a referenced mesh file (geometry
updated without updating the recorded intent). The CLI prints each warning with
a `⚠` prefix; the hub also logs them.

The hub stores registrations in `~/.buildviz/registry.json`, serves
`/builds/index.json`, rewrites mesh URLs in each registered `scene.json`, and
serves mesh assets from the original project directory. Large STL files are not
copied by default.

Useful endpoints:

- `GET /__buildviz/status`: hub identity signature (`service: "buildviz-hub"`, `version`, `pid`, `port`, `baseUrl`, `startedAt`) and registered builds. Verify `service` here before trusting an endpoint.
- `GET /__buildviz/builds`: registered builds only.
- `POST /__buildviz/register`: register or replace an on-disk build directory.
- `POST /__buildviz/push`: push a `scene.json` layout directly (see below).
- `POST /__buildviz/pack-export`: pack a registered build server-side and write
  Bambu-ingestible plate files. Body `{ buildId, version?, printer?, bed?,
  assembly?, format? ("3mf"|"stl"), angle?, spacing?, margin? }`; returns
  `{ ok, outDir, files: [{ plate, fileName, path, partCount }], plateCount,
  partCount, format, skipped, viewerScene, viewerUrl }`. Files land in
  `<build>/plates/`; the export also (re)emits the build's `buildviz_pack.json`
  layout scene and returns `viewerScene` (its `/builds/<id>/buildviz_pack.json`
  URL) plus `viewerUrl` (a ready `?project=&build=&scene=…` search string that
  loads the packed plate layout). This backs the viewer's "Export plates"
  control (a browser can't write files itself).
- `POST /__buildviz/open-path`: reveal a directory in the local OS file manager
  (`open`/`xdg-open`/`explorer`). Body `{ path }`; returns `{ ok, path }` or a
  `400` error. The path is sandboxed hard: it is resolved with `realpath` and
  must be a real directory **inside an allowed root** — the project directory,
  `~/.buildviz`, or a registered build's directory — and the file manager is
  launched without a shell (`execFile` with an args array), so out-of-root,
  non-directory, or symlink-escape requests are rejected. Backs the export
  control's "Open folder" button.

- `GET /builds/_assets/<sha256>.<ext>`: content-addressed mesh bytes uploaded via
  `push --upload-assets` (see below). Served read-only from
  `~/.buildviz/cache/_assets/`.

Default host is `127.0.0.1`. Do not expose the hub on untrusted networks; it is
unauthenticated local dev tooling. When you DO need remote viewing, bind
off-loopback (`--lan` / `--host <addr>`): the hub then runs **read-only** and the
four mutation/host-action endpoints above (`push`, `pack-export`, `register`,
`open-path`) return `403` — only the view/read routes stay reachable.

## Pushing Layouts Programmatically

`register` points the hub at an on-disk build directory you manage. `push` is the
opposite: any local program sends a `scene.json` layout straight to the running
hub by build id, and the hub stores it in a hub-managed cache. The program never
has to lay out a `public/builds/` directory.

`POST /__buildviz/push` accepts JSON:

```json
{
  "buildId": "spider/chassis",
  "version": "with-dome",
  "setDefault": false,
  "name": "Spider chassis",
  "message": "dome variant: raised the canopy 4mm",
  "scene": { "name": "Spider chassis", "units": "mm", "center": [0, 0, 0], "meshes": [], "instances": [] },
  "designSpec": "units: mm\nparts: {}\n",
  "assetsBaseUrl": "/builds/some-existing-build"
}
```

- `buildId` (required): the `project/build` id (e.g. `"spider/chassis"`). You may
  pass a human label with spaces and capitals (e.g. `"Spider Chassis"`); it is
  canonicalized to a URL- and filesystem-safe slug (`spider/chassis`) used
  everywhere (cache dir, registry, `index.json` id, viewer URL). Pass the same
  label every time and it always maps to the one build.
- `version` (optional): a new snapshot name (e.g. `"with-dome"`). Omitted means
  the next free `v<N>`, selected by the hub. Existing names reject changed content
  with HTTP 409; identical retries return `unchanged: true`.
- `bump` (optional, bool): auto-pick the next free `v<N>` (server-side, since
  only the hub knows the build's existing versions) when `version` is omitted.
  This is now the default even without the flag; explicit `version` still wins.
- `noSnapshot` (legacy bool): accepted for compatibility but cannot disable
  published-version protection. Changed content always needs a new version.
- `setDefault` (optional, bool): make this version the build's default (and the
  `latest` alias). Defaults to `true` for automatically numbered pushes, `false`
  for explicitly named ones. Send `false` to keep the current default on review
  pushes. A new build/branch always uses its first version as default.
- `scene` (required): the `scene.json` object itself (must have `meshes[]` and
  `instances[]`).
- `name` (optional): display name; defaults to `scene.name`.
- `message` (**required**): a changelog/commit note naming the version being
  created/bumped (the CLI sets it from `-m`/`--message`); pushes without one are
  rejected with `400`. Stored in the per-version metadata, exposed in
  `/builds/index.json`, and shown in the viewer. Applies to the written version
  only — never to an auto-snapshot of the prior default.
- `designSpec` (optional): the full `design_spec.yaml` contents as a string.
  Stored with the written version (and mirrored to the build root when the
  version is the default). The CLI auto-fills this from a `design_spec.yaml`
  next to the `--scene` file when `--design-spec` is not given.
- `assetsBaseUrl` (optional): prefix prepended to **relative** mesh URLs, e.g.
  `stl/foo.stl` -> `/builds/some-existing-build/stl/foo.stl`.
- `assets` (optional): an array of `{ meshId, data (base64), ext }` uploaded mesh
  blobs, for a self-contained push (see "Uploading mesh bytes" below). The CLI
  populates this from `--upload-assets`.
- `maxUploadBytes` (optional): server-side size cap for the total uploaded bytes;
  the CLI sets it from `--max-upload-mb`. Defaults to 256MB.

The response includes `ok`, a human `summary`, `build`, the written `version`,
the build's current `defaultVersion`, `isNewVersion`, `isNewBuild`, the full
`versions` (string[]) list, `unchanged`, the `pruned` list, `snapshot` (`null`,
retained for compatibility), the `message` (the
version's changelog note, or `null`), the `cacheDir`, the viewer `url`, and —
when assets were uploaded — an `uploads` summary (`count`, `totalBytes`,
`dedupedBytes`, and per-asset `{ meshId, url, bytes, deduped }`).

It also includes `warnings: string[]` — non-blocking **design-spec warnings**:
no effective `design_spec.yaml` for the version (neither pushed nor already
cached), scene part types with no `parts:` entry, spec entries for parts no
longer in the scene, and "geometry changed but the spec didn't" (the pushed
scene bytes differ from the previous default while the effective spec
text is unchanged — the required `message` records why, but the spec should be
brought up to date too). Keep `design_spec.yaml` updated in
the same change that alters geometry.

### Adding or branching a version

Versions are **immutable snapshots on a branch**. Pick a new `version` name,
or omit it for automatic numbering. An identical retry keeps the original bytes,
message and timestamp; changed content at an existing name is rejected.
Use `--branch` for an ongoing parallel design. Pass `--set-default` to promote a
named version to the build's default:

```sh
buildviz push --project spider --build chassis --version main -m "initial chassis" --scene scene.json
buildviz push --project spider --build chassis --version with-dome -m "dome variant" --scene dome.json
buildviz push --project spider --build chassis --version with-dome -m "dome variant" --set-default --scene dome.json
buildviz versions spider/chassis                              # main (default), with-dome
buildviz diff spider/chassis@main spider/chassis@with-dome --json
# viewer: /?project=spider&build=chassis&version=with-dome&compare=main
```

**Make every revision a new version with `--bump`.** When you regenerate a build
repeatedly and want each revision archived, pass `--bump` instead of naming a
version. The hub auto-picks the next free `v<N>` (`v1`, `v2`, …) and makes it the
default, so history accumulates with no bookkeeping:

```sh
buildviz push --project spider --build chassis --bump -m "first cut" --scene scene.json        # -> v1 (default)
buildviz push --project spider --build chassis --bump -m "widened yoke 2mm" --scene scene.json  # -> v2 (default)
buildviz versions spider/chassis                                           # v1, v2 (default)
```

**A plain push creates a new version by default.** No extra bookkeeping is
needed: omission is equivalent to `--bump`, never an in-place replacement.

```sh
buildviz push --project spider --build chassis -m "regenerated" --scene scene.json   # next v<N>, becomes default
buildviz push --project spider --build chassis -m "review" --scene scene.json --no-default   # next v<N>, keep default
```

Same-name conflicts return HTTP 409 with `code: "VERSION_ALREADY_EXISTS"`,
`suggestedVersion`, and a hint to remove `version` and use `bump:true`. Nothing in
the version is changed. `--no-snapshot` cannot bypass this guard. `--keep <n>`
explicitly prunes oldest non-default versions; omission keeps all history.

Publish links pin the exact version, even when it is currently default. The
version menu includes **Publish a new version…** with a copyable `--bump
--no-default --upload-assets` command. For reliable geometry history, upload
meshes into the content-addressed store: external/mutable mesh URLs are not
snapshots. Hub status advertises the policy in `publishPolicy`.

**Name the change with `-m`/`--message` (required).** Every `push` or `freeze`
that creates/bumps a version must carry a note describing what changed; it is
stored per-version and shown in the viewer (current-version badge, version
dropdown, and the "new version" pill). For **auto-publishing producer
pipelines** — e.g. a verifier that publishes each passing build with `--bump` —
derive the note from the git commit subject or the check summary:

```sh
buildviz push --project spider --build chassis --bump -m "$(git log -1 --format=%s)" --scene scene.json
buildviz freeze ./build --bump -m "all checks pass: 0 fail, 2 warn"
```

The note applies to the new version only — an auto-snapshot of the prior default
keeps its own note. Pushes without a message are rejected by both the CLI and
the hub endpoint; `freeze` only allows omitting `-m` when re-freezing a version
that already carries a message (kept rather than clobbered).

`--project` auto-derives from the git repo / directory and `--build` from the
scene name / directory, so a minimal push needs only a scene and a `-m`
message. Because ids are
canonicalized, `"Spider Chassis"`, `"spider chassis"`, and `spider/chassis` all
resolve to the one build entry. Push prints which project/build/version it
landed as, plus the view URL and hub URL.

> **push/freeze vs register/send.** `push` (hub cache) and `freeze` (on-disk)
> accumulate named versions. `push` rejects changes to published names;
> use `freeze --bump` for new on-disk revisions too.
> `register` and `send` are different by design: they point the hub at an
> on-disk directory it does not own and act as a **live pointer** — they
> OVERWRITE that directory's `scene.json` **in place with no versioning or
> archiving**. To keep on-disk history, use
> `buildviz freeze <build-dir> --bump -m "<what changed>"`
> (or write `versions/<name>/scene.json` yourself), not `register`/`send`.

### Mesh assets

By default a pushed scene must reference meshes that are already reachable through
the hub:

- Absolute `http(s)://...` URLs are used as-is.
- Absolute `/builds/<other-id>/...` URLs are served from another registered or
  pushed build (reuse an existing build's STLs without copying them).
- Relative URLs (`stl/foo.stl`) only resolve if you pass `assetsBaseUrl`
  pointing at a build that already serves those files.

#### Uploading mesh bytes (`push --upload-assets`)

To make a pushed build **self-contained** — no pre-existing reachable URL needed —
add `--upload-assets`:

```sh
buildviz push --project spider --build chassis -m "self-contained push" --scene scene.json \
  --upload-assets --assets-dir ./out --max-upload-mb 128
```

The CLI reads each **relative** mesh file's bytes (resolved against `--assets-dir`,
or the scene file's directory) and ships them base64-encoded in the push body's
`assets[]`. Absolute `http(s)` and `/`-rooted URLs are already reachable and are
left untouched. The hub:

- stores each blob **content-hashed** at
  `~/.buildviz/cache/_assets/<sha256>.<ext>`, so identical bytes **dedup** across
  versions and builds (re-pushing the same mesh writes nothing new);
- enforces a **size cap** on the total upload (default 256MB; `--max-upload-mb <n>`,
  re-checked server-side via `maxUploadBytes`) and rejects an over-cap push;
- rewrites the cached scene's mesh URLs to `/builds/_assets/<sha256>.<ext>`, served
  read-only by the hub.

A `push` WITHOUT `--upload-assets` behaves exactly as before (no upload). A
read-only off-loopback hub rejects all pushes (including uploads) with `403`.

### Examples

curl:

```sh
# Resolve + verify the hub from discovery instead of hardcoding a port.
BASE=$(jq -r .baseUrl ~/.buildviz/server.json)
curl -s "$BASE/__buildviz/status" | jq -e '.service == "buildviz-hub"' >/dev/null || { echo "no verified hub"; exit 1; }
curl -sS -X POST "$BASE/__buildviz/push" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n --slurpfile s scene.json '{buildId:"spider/chassis", version:"with-dome", setDefault:false, name:"Spider chassis", scene:$s[0]}')"
```

Node:

```js
import { readFile } from 'node:fs/promises'

const server = JSON.parse(
  await readFile(`${process.env.HOME}/.buildviz/server.json`, 'utf8'),
)
// Verify identity before trusting the endpoint.
const status = await (await fetch(`${server.baseUrl}/__buildviz/status`)).json()
if (status.service !== 'buildviz-hub') throw new Error(`Not a BuildViz hub at ${server.baseUrl}`)
const scene = JSON.parse(await readFile('scene.json', 'utf8'))

const res = await fetch(`${server.baseUrl}/__buildviz/push`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ buildId: 'spider/chassis', version: 'with-dome', setDefault: false, name: 'Spider chassis', scene }),
})
console.log((await res.json()).url)
```

Python:

```python
import json, os, urllib.request

home = os.path.expanduser("~/.buildviz/server.json")
base_url = json.load(open(home))["baseUrl"]
# Verify identity before trusting the endpoint.
status = json.load(urllib.request.urlopen(f"{base_url}/__buildviz/status"))
assert status.get("service") == "buildviz-hub", f"not a BuildViz hub at {base_url}"
scene = json.load(open("scene.json"))

req = urllib.request.Request(
    f"{base_url}/__buildviz/push",
    data=json.dumps({"buildId": "spider/chassis", "version": "with-dome", "setDefault": False, "name": "Spider chassis", "scene": scene}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
print(json.load(urllib.request.urlopen(req))["url"])
```

Or use the CLI, which discovers the hub for you:

```sh
buildviz push --project spider --build chassis --version with-dome --scene scene.json --name "Spider chassis"
cat scene.json | buildviz push --project spider --build chassis -m "new revision"   # next v<N>
```

## Version Cache

Pushed builds live under a stable cache root keyed by `project/build`, mirroring
the standard build/version layout so the version menu and diff mode work without
changes:

```text
~/.buildviz/cache/<project>/<build>/
  scene.json                  <- default version (e.g. "main")
  design_spec.yaml            <- default version's spec (optional)
  meta.json                   <- build metadata (name, defaultVersion, versions, timestamps)
  versions/
    with-dome/scene.json      <- named branch "with-dome"
    ...
```

- The default version is the build-root `scene.json`; every other named branch
  lives at `versions/<name>/scene.json`. Published names reject changes;
  `--set-default` repoints the default (and the `latest` alias).
- Versions are **named** (auto-numbered by default) and listed in `meta.json` and
  `/builds/index.json`, with one marked the default.
- The cache is on disk and the hub rebuilds registry entries from it on startup,
  so pushed builds and their branches survive a hub restart.
- On every (re)start the hub also prunes any registered build whose source
  directory no longer exists: it logs a warning and drops the entry from
  `registry.json` rather than advertising a build whose assets would 404.
  Re-register or re-push to restore a pruned build.
- To prune, use `buildviz cache rm <project>/<build> [--version <name>]` (removes a
  cached version or the whole build; refuses to delete the default version) rather
  than deleting `versions/<name>` directories by hand. `buildviz cache ls [--json]`
  lists every cached build with per-version sizes and timestamps.
- `buildviz push ... --keep <n>` caps retained versions per build automatically:
  after the push the oldest non-default versions are pruned until at most `n`
  remain (the default is always kept). Omit it to keep everything (the default).

Run `buildviz migrate [--dry-run] [--cache-only]` to non-destructively
write/normalize `meta.json` for existing builds: any legacy `v1`/`v2` directories
are preserved as named versions, and an old `latestVersion` becomes
`defaultVersion`.

Browse and compare branches:

```text
/?project=<p>&build=<b>                                latest (default)
/?project=<p>&build=<b>&version=with-dome              a named branch
/?project=<p>&build=<b>&version=with-dome&compare=main diff main -> with-dome
```

```sh
buildviz versions                            # whole project -> build -> version tree (default marked)
buildviz versions <project>/<build> --json   # one build's named versions as JSON
buildviz diff <project>/<build>@main <project>/<build>@with-dome --json
```

## Design Sanity Check

After generating a `scene.json` (and before showing it to a human), run the
geometry-only sanity check. It needs only `scene.json` + the STL assets — no
`design_spec.yaml` — and flags two common generation mistakes:

```sh
npx buildviz check . --json
npx buildviz check public/builds/<build-id> --highlight-url
```

- **Interference**: pairs of parts whose solids overlap, each with a
  **penetration depth** in mm (the deepest interior point shared by the two
  solids, measured to the nearest surface of either). Intended touching mates
  read ~0 and are not flagged; genuine overlap is.
- **Connectivity** (INTER-part): *floating* parts (a whole part not joined to the
  main assembly) and *suspicious gaps* (a part that nearly touches but leaves a
  gap). This is an assembly-graph check over instances — it does **not** inspect a
  single mesh's internal topology (see Printability `disconnected_components` for
  the intra-mesh case).
- **Printability** (offline gate): non-**watertight**/non-manifold meshes and
  degenerate triangles (robust, `fail`/`warn`), **self-intersection** — triangle
  pairs within one mesh that cross (robust, `fail`), an estimated minimum
  **wall thickness** below `--min-wall` (heuristic, `warn`), and
  **disconnected bodies** — a single printed mesh that is actually >1 disjoint
  connected-component (a floating island / detached ring), robust, `fail`,
  opt-out per mesh via `checksConfig.expectedMeshComponents` (see
  `plans/validation.md` §11).
- **Assembleability** (offline gate): per-fastener **thread engagement** below
  `--min-thread-engagement` (heuristic, `warn`); **assembly access** — parts with
  no straight-line install/removal direction (coarse heuristic, `warn`, opt-in
  via `--access`); **mating contact** — declared (legacy `ignoreOverlapPairs`) or
  near-touching mating pairs must touch within `--mating-tolerance` else they
  `fail` as floating-apart or crashing-in (robust; an allowed interference is
  never a "crash"); **declared interference** — every
  `checksConfig.allowedInterferences` entry is audited: it must name real
  instances that actually interfere (or at least touch) within the entry's
  `maxPenetrationMm` cap, else it `fail`s (robust); and **routing reach** —
  producer-supplied `routes[]` cable/harness polylines checked against a length
  budget + solid obstructions (heuristic, `fail`).

The `--json` envelope returns `results.passed` (boolean), `results.problemCount`,
and `collisions[]` / `floating[]` / `gaps[]` arrays plus a `highlightUrl` that
opens the viewer with colliding parts in red and floating parts in amber. `ok`
stays `true` on a successful run regardless of problems — gate on
`results.passed`.

Tuning and defaults:

- `--tolerance <mm>` (default `0.5`): contact separation for connectivity.
- `--min-penetration <mm>` (default `1.0`): penetration depth at/above which an
  overlap is reported, so slightly-modelled press-fit mates are not flagged.
- **Fasteners** (screws, nuts, inserts, washers, pins — detected by a
  `fasteners/` asset path / `fasteners:` mesh id or a hardware-style part name)
  are **suppressed by default**, since they occupy their holes by design, but
  still bridge connectivity. Pass `--include-fasteners` to analyze them.

Performance is bounded (each unique mesh BVH-indexed once; broad-phase
sweep-and-prune + BVH narrow phase), so even a ~674-instance build checks in a
couple of seconds.

More tuning:

- `--min-wall <mm>` (default `0.8`) / `--min-thread-engagement <mm>` (default
  `2.0`) / `--mating-tolerance <mm>` (default `0.2`): printability /
  assembleability thresholds. Heuristic kinds only `warn`; `self_intersection`
  and `mating_contact` (robust) and `routing_reach` can `fail`.
- `--access`: also run the **coarse** `assembly_access` sweep (off by default; in
  a dense assembly it flags most interlocked parts, so use it to spot
  fully-enclosed parts, not as a gate).
- `--no-printability` / `--no-assembleability` toggle whole groups; `--checks
  watertight,self_intersection,mating_contact,…` is a full allowlist of exactly
  which kinds run. `self_intersection` (printability) and `mating_contact`
  (assembleability) are default-on; `assembly_access` stays opt-in.

`check` also emits generic, paintable `checks[]` records (kinds: `mesh_overlap`,
`clearance`, `connectivity`, `placement`, `scene_meta`, plus the offline-gate
kinds `watertight`, `degenerate_geometry`, `wall_thickness`, `self_intersection`,
`disconnected_components`, `thread_engagement`, `assembly_access`,
`mating_contact`, `routing_reach`, plus the motion kinds
`swept_overlap`/`swept_clearance` from `buildviz sweep`) and a
`checkSummary`. Add `--emit` to drop a
`buildviz_checks.json` sidecar beside `scene.json`; the web viewer auto-loads it
into a clickable **Checks panel** (click a finding to highlight the parts — an
overlap also **shades its interpenetrating volume** at the contact region). The
panel has triage toggles (show only fails/warns, mute allowed matings, per-kind
filter) and a `N fail · M warn` badge, and can recompute the fast spatial checks
live in the browser — **Run live checks** is scoped to the visible/focused parts
for interactivity on large builds, **Run full-scene checks** runs everything (the
offline-gate kinds are CLI/CI-only but still paint from the sidecar). Encode project intent as
data in `scene.json` under `checksConfig` — `toleranceMm`, `clearanceMm`,
`minPenetrationMm`, `minWallMm`, `minThreadEngagementMm`, `matingToleranceMm`,
`allowedInterferences` (typed, INSTANCE-level intentional interferences — each
entry has a `kind` like `thread_engagement`/`press_fit`/`bearing_seat`, the two
`instances`, a required `reason`, and an optional `maxPenetrationMm` cap; marked
`pass (allowed)` for overlap AND audited by the `declared_interference` gate so
stale/dangling/over-cap entries fail), and the legacy `ignoreOverlapPairs`
(intended part-type matings — still honored for parts with no relative motion
and still treated as DECLARED pairs the `mating_contact` gate must verify are in
contact, but it warns on every run and is refused between parts that `joints[]`
move relative to each other; migrate to `allowedInterferences`).

## Pack For 3D Printing

`buildviz pack <build-dir>` lays a build (or one assembly) out for FDM printing.
It is purely additive (reads the same `scene.json` + mesh assets, adds no schema)
and runs two **heuristics** that reuse the shared STL loader / BVH:

```bash
npx buildviz pack public/builds/<build-id> --printer x1c --json
npx buildviz pack public/builds/<build-id> --assembly L0 --emit   # one focusGroup/leg
npx buildviz pack public/builds/<build-id> --bed 300x300x340      # custom bed WxDxH (mm)
```

1. **Orientation** (per unique mesh): scores candidate rest orientations — the 6
   axis-aligned rests + the largest natural facets — by support need (downward
   triangle area steeper than `--angle`, default 45° from vertical; dominant), bed
   contact area (stability), and height (mild), then picks the best one that fits
   the bed. It does **not** model bridges or support volume.
2. **Packing**: a shelf/skyline bin-packer places oriented footprint AABBs with
   `--spacing` inside a `--margin`/brim allowance, spilling to extra **plates**
   when needed. A part too big for the bed (even rotated 90°) or taller than the
   build height is rejected with a clear error.

Printers: `x1c` (256×256×256mm, default), `h2d` (350×320×325mm); extend the table
in `checks/buildvizPacking.ts` or pass `--bed`. Fasteners are excluded (not printed).
`--json` returns per-plate utilization and per-part orientation/placement/support.
`--emit` writes a `buildviz_pack.json` layout scene next to `scene.json` (parts
re-posed onto plate coordinates with a plate-boundary slab) and prints a viewer
`?scene=…` URL so the layout opens in the existing viewer.

### Export plates for a slicer (`--export`)

`--export` writes the packed layout to a **Bambu-ingestible** format, one file
per plate, with every part baked at its packed XY + chosen print orientation so
the file opens already arranged on the bed:

```bash
npx buildviz pack public/builds/<build-id> --printer h2d --export                  # plate-1.3mf … plate-N.3mf -> <build>/plates/
npx buildviz pack public/builds/<build-id> --assembly L0 --export --format stl      # per-plate merged STL fallback
npx buildviz pack public/builds/<build-id> --export --out /tmp/plates               # custom output directory
```

- `--format 3mf` (default) emits a valid core-3MF OPC zip per plate
  (`[Content_Types].xml`, `_rels/.rels`, `3D/3dmodel.model`; core namespace
  `http://schemas.microsoft.com/3dmanufacturing/core/2015/02`, `unit="millimeter"`)
  with one `<object>`/`<mesh>` per part and one `<build>` `<item>` per part
  carrying the baked placement `transform`. `--format stl` emits a per-plate
  merged binary STL instead. The geometry/orientations are exactly what `pack`
  computed; fasteners are excluded (not printed).
- The default output directory is `<build>/plates/`; `--out <dir>` overrides it.
  The command prints the absolute output directory and every per-plate path
  (also returned in the `--json` envelope under `export`).

Follow-ups not yet built: richer Bambu-specific plate config (per-plate slicer
settings beyond core 3MF), per-part STL mode, and serving packed layouts as
first-class hub builds.

## scene.json Contract

```json
{
  "name": "My build",
  "units": "mm",
  "center": [0, 0, 0],
  "designSpecUrl": "/builds/my-build/design_spec.yaml",
  "meshes": [
    {
      "id": "tibia_link",
      "name": "tibia_link.stl",
      "url": "/builds/my-build/stl/tibia_link.stl"
    }
  ],
  "instances": [
    {
      "id": "tibia_link-L0",
      "meshId": "tibia_link",
      "name": "Tibia link L0",
      "partType": "tibia_link",
      "role": "knee to foot link",
      "color": "#e377c2",
      "transform": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 100, 0, 20, 1],
      "centroid": [100, 0, 20],
      "leg": "L0",
      "joint": "knee",
      "focusGroup": "L0"
    }
  ]
}
```

Rules:

- `mesh.id` must be stable and unique within the build.
- `instance.id` must be stable and unique within the build.
- `instance.meshId` must reference a mesh.
- `instance.partType` should match a key under `design_spec.yaml` `parts` when a
  spec is present; without a spec it is just a free-form part-type label.
- `transform` is a 4x4 column-major matrix for Three.js.
- `centroid` is optional but recommended for camera framing and labels.
- `focusGroup` groups related instances for isolation, such as `L0` or `chassis`.
- `schemaVersion` (optional integer) declares the manifest schema version this
  scene targets. It is **additive** — scenes that omit it still load and render
  everywhere. A producer SHOULD stamp the current version (today `1`) so
  `buildviz validate` can warn when a scene is read by a newer BuildViz than wrote
  it (`unknown_schema_version`) or an older one (`old_schema_version`); a
  non-integer warns as `invalid_schema_version`. The hub records it verbatim on
  push. Bump only on a breaking/structural schema change, never for adding new
  optional fields.
- `assetsBaseUrl` (optional) is a prefix prepended to **relative** `mesh.url`
  values at load time (absolute `http(s)` and `/`-rooted URLs pass through),
  letting one relative-URL build render under the hub, static hosting, or a
  `versions/<name>/` dir.

## Motion / kinematics (`joints[]` & `poses[]`, optional & additive)

These two top-level keys are **optional and non-breaking** — old viewers ignore
them. Emit them to unlock the Motion scrubber and **swept-pose validation**
(per-pose overlap re-evaluation with a worst-case envelope).

```json
{
  "joints": [
    {
      "id": "L0-yaw",
      "type": "revolute",
      "axis": [0, 0, 1],
      "origin": [42, 0, 18],
      "instances": ["coxa_link-L0", "femur_link-L0", "tibia_link-L0"],
      "limits": { "min": -55, "max": 55 },
      "home": 0,
      "label": "L0 yaw"
    },
    {
      "id": "L0-hip",
      "type": "revolute",
      "axis": [0, 1, 0],
      "origin": [70, 0, 18],
      "parent": "L0-yaw",
      "instances": ["femur_link-L0", "tibia_link-L0"],
      "limits": { "min": -45, "max": 60 },
      "home": 0
    },
    {
      "id": "L0-knee",
      "type": "revolute",
      "axis": [0, 1, 0],
      "origin": [120, 0, 18],
      "parent": "L0-hip",
      "instances": ["tibia_link-L0"],
      "limits": { "min": 0, "max": 90 },
      "home": 0
    }
  ],
  "poses": [
    { "id": "home",   "name": "Home",   "jointValues": {} },
    { "id": "crouch", "name": "Crouch", "jointValues": { "L0-hip": 45, "L0-knee": 80 } }
  ]
}
```

**Joint fields**

- `id` — stable, unique within the build.
- `type` — `"revolute"` (angle in **degrees**) or `"prismatic"` (offset in **mm**).
  Map labels like `yaw`/`hip`/`knee` to `revolute`.
- `axis` — unit-ish rotation/translation axis `[x,y,z]` in **scene (world home) frame**.
- `origin` — pivot point `[x,y,z]` the axis passes through, in **scene frame**.
- `parent` — optional `id` of the joint this one is mounted on (kinematic chain).
- `instances` — instance ids that move **with this joint** (the link distal to it,
  plus everything further down the chain).
- `limits {min,max}` — slider clamp (deg or mm). `home` — rest value (default `0`).
- `label` — optional display name.

**Forward-kinematics convention (exactly what the viewer computes)**

1. For joint value `θ`, build a **local** transform `L = T(origin) · R(axis,θ) · T(-origin)`
   for revolute (rotate about `axis` through `origin`), or `L = T(axis·d)` for prismatic.
2. Compose up the chain: `M_joint = M_parent · L_joint` (root joints have `M_parent = I`).
3. Each instance's posed world transform is `M_joint · base_transform`, where `base`
   is the static `instance.transform` (home pose). An instance is driven by the
   **deepest** joint that lists it.

Frames are world/scene-relative (not parent-relative link frames), so `axis`/`origin`
are measured in the home scene — the easiest thing for an exporter to emit from the
home-pose centroids/geometry.

**Swept validation.** With joints present, the viewer/CLI samples each DOF across
its limits (plus any named poses), applies FK, and re-runs the cached-BVH overlap
engine per sample — reporting the **worst** penetration / **min** clearance per
instance pair as `swept_overlap` / `swept_clearance` checks, labeled with the pose
that produced it. Run it headless with `buildviz sweep <build-dir> [--samples N]
[--clearance mm] [--emit] [--json]` (the CLI sweeps the whole build; the viewer's
"Run swept checks" defaults to visible/focused parts with full sweep opt-in).

## Cable / harness routes (`routes[]`, optional & additive)

A producer that knows its harness layout can emit an additive, optional
`routes[]` block (ignored by old viewers, like `joints[]`). The `routing_reach`
gate then verifies each route stays within an optional length budget and does
**not** pass through any solid part. BuildViz does **not** infer routes from
geometry — automatic harness inference without route data is intentionally out of
scope (it stays project-agnostic).

```json
{
  "routes": [
    {
      "id": "batt-to-pdb",
      "label": "Battery → PDB",
      "points": [[-70, 15, 44], [-20, 10, 40], [30, 12, 40]],
      "maxLengthMm": 140,
      "instances": ["016-lipo_battery", "010-pca9685_primary"]
    }
  ]
}
```

- `points` — ordered world-frame `[x,y,z]` waypoints the cable follows.
- `maxLengthMm` (optional) — reach budget; a longer routed polyline `fail`s.
- `instances` (optional) — endpoints the route connects; these are excluded from
  the obstruction test so the route may legitimately enter its own terminals.
- `label` (optional) — display name for the check / panel row.

The check is a **heuristic** straight-segment ray test on the cached BVHs: it
flags over-budget length and solids a segment passes through, but does not model
bend radius, slack, or connector seating.

## design_spec.yaml Contract

`design_spec.yaml` is optional. When omitted, BuildViz renders the build from
`scene.json` alone without semantic overlays, labels, or the YAML panel.

When present, `design_spec.yaml` is the durable record of **design intent and
rationale** (why each part is the way it is, so the next agent doesn't re-derive
it) and the source of truth for generation, labels, dimensions, validation, and
LLM context. It should contain enough information to regenerate each part without
hidden CAD constants and enough semantic metadata for BuildViz to label meaningful
features. **Keep it current**: whenever you change a part's geometry/CAD/STL,
update its entry (rationale, dimensions, features) in the *same* change — `buildviz
compat` fails on a scene part with no entry and warns when the spec is older than
the scene/geometry. See `DESIGN_YAML_SPEC.md`.

Minimum shape:

```yaml
units: mm

globals:
  parameters:
    horn_stack_height_mm:
      value: 5.0
      code_name: HORN_STACK_H
      description: "Distance from servo spline tip to link mating face."

parts:
  tibia_link:
    label: "Tibia link"
    aliases: ["shin", "lower leg"]
    description: "Lower leg member between knee horn and foot hinge."
    generated_by:
      file: hexapod_prototype.py
      function: make_tibia_link
      output_stl: stl/tibia_link.stl

    local_frame:
      origin: "Knee joint center"
      axes:
        x: "Runs from knee toward foot."
        y: "Joint depth / servo output axis."
        z: "Normal to the side profile."

    features:
      knee_joint:
        label: "Knee joint"
        aliases: ["knee pad", "knee horn interface"]
        kind: joint
        purpose: "Bolts tibia link to the knee servo horn."
        llm_context: "If the user says knee joint depth, they mean pad depth along local Y."

        render:
          anchor_mm: [0, 8, 0]
          label_offset_mm: [0, 28, 18]
          label_priority: high

        dimensions:
          pad_depth_mm:
            label: "Knee joint depth"
            value: 6.0
            axis: y
            from_mm: [0, 5, 0]
            to_mm: [0, 11, 0]
            code_name: HORN_STACK_H
            derived_from: horn_stack_height_mm
            description: "Thickness of the knee horn mounting pad along local Y."
            llm_hint: "Reducing this makes the knee joint shallower; check horn clearance and bolt engagement."
```

Rules:

- Every meaningful subpart gets a stable `feature_id`.
- Every user-facing concept gets `label` and `aliases`.
- Every geometry-driving input gets a named `dimension_id` or global parameter.
- Every dimension includes local axis, endpoints or equivalent references, value,
  and a code link.
- BuildViz uses `render.anchor_mm`, labels, aliases, and dimensions for overlays.
- LLMs use `description`, `purpose`, `llm_context`, and `llm_hint` for discussion.
- CAD code should read values from this file instead of duplicating constants.

## How To Use In A Project

1. Generate or copy STL files into `public/builds/<project>/<build>/`.
2. Write `scene.json` with all unique meshes and placed instances.
3. Optionally write `design_spec.yaml` with part generation inputs and semantic
   labels. Skip this step to register and view a build from `scene.json` alone.
4. Serve the folder from any static web server.
5. Open BuildViz (the viewer/dev server, default port `5173` — distinct from the
   hub on `5183`):

> ⚠️ **Writing/overwriting `public/builds/<id>/scene.json` directly does NOT
> create versions.** Static discovery (and `register`/`send`) serve whatever
> bytes are at that path *right now* — regenerating `scene.json` in place
> **overwrites** the default and **never accumulates history**. To make every
> revision a new version, run one of these **after regenerating your scene**
> (the `freeze`/`push` commands are the only ones that archive on-disk builds):
>
> ```sh
> # On-disk build (you already have public/builds/<id>/scene.json + STLs):
> buildviz freeze public/builds/<id> --bump        # auto next v<N>, becomes default
>
> # Or push the scene into the hub cache (auto-uploads referenced STLs):
> buildviz push --build-id <id> --scene public/builds/<id>/scene.json --bump --upload-assets
>
> # Add -m to record what changed (e.g. from the commit subject or check summary):
> buildviz push --build-id <id> --scene public/builds/<id>/scene.json --bump -m "$(git log -1 --format=%s)"
> ```
>
> A plain `buildviz push` now creates the next `v<N>` even without `--bump`.
> Existing published version names cannot be replaced. Avoid `freeze --force`
> on shared on-disk builds too; use `freeze --bump` for each revision.
> `--keep <n>` explicitly prunes old non-default versions; omit to keep all.

```text
http://localhost:5173/?project=<project>&build=<build>&version=<name>
```

Omit `version` to open the default. The old single-param form
`?build=<project>/<build>` still resolves for back-compat. Or pass an explicit
spec:

```text
http://localhost:5173/?project=<project>&build=<build>&designSpec=/builds/<project>/<build>/design_spec.yaml
```

For local debugging, run BuildViz from a directory that contains `scene.json`:

```sh
npm run buildviz
```

If BuildViz is installed into another project from this checkout:

```sh
npm install --save-dev /Users/lbiewald/buildviz
npx buildviz docs
npx buildviz --help
npx buildviz init --dry-run
npx buildviz init
npx buildviz
```

These commands can be run from the project root or from a subdirectory. When no
build directory is passed, BuildViz walks upward to the nearest directory with
`scene.json`, `design_spec.yaml`, or common STL directories and uses that as the
build root.

To expose it as `npm run buildviz` in that project, add:

```json
{
  "scripts": {
    "buildviz": "buildviz"
  }
}
```

By default this looks for `design_spec.yaml` in the same directory. To attach a
different spec or use a different port:

```sh
npm run buildviz -- . --design-spec ../other_project/design_spec.yaml --port 5174
npx buildviz . --design-spec ../other_project/design_spec.yaml --port 5174
```

The local server rewrites relative mesh URLs such as `stl/tibia_link.stl` so
projects do not need to export assets under BuildViz's own `public/` directory
while debugging.

`buildviz init` creates `scene.json` only if it does not already exist, then sets
up project guidance for agents in `BUILDVIZ.md` and
`.cursor/skills/buildviz/SKILL.md` when those files are missing. It scans common
STL directories such as `stl/`, `stl_prototype/`, `meshes/`, `assets/`, and
`fasteners/`; otherwise it scans the project recursively. Use `--stl-dir` to
scan a specific directory and `--dry-run` to inspect what would happen without
writing files.

`buildviz docs` prints the expected project files, project-local guidance files,
package documentation paths, useful commands, and agent guidance. It is safe to
run from a subdirectory; it uses the same upward build-root discovery as the
viewer and `init`.

## Agent Discovery

Agents working in a consuming project should:

1. Run `npx buildviz docs` to find project-local and package docs.
2. Read `BUILDVIZ.md` when present.
3. Use `.cursor/skills/buildviz/SKILL.md` when present.
4. Treat `scene.json` as the rendered assembly contract.
5. Treat `design_spec.yaml` as the semantic source of truth for design intent,
   part labels, features, and dimensions.
6. Run `npx buildviz validate . --json` before relying on the viewer or making
   claims about asset completeness.
7. Run `npx buildviz check . --json` to catch interference and floating /
   disconnected parts geometrically; gate on `results.passed` and fix the named
   instances (or open `results.highlightUrl`) before asking a human to review.

## Long-Term Package API

BuildViz should expose a reusable viewer component:

```tsx
<BuildVizViewer
  sceneUrl="/builds/my-build/scene.json"
  designSpecUrl="/builds/my-build/design_spec.yaml"
/>
```

Project-specific exporters should live in the project that owns the CAD model.
BuildViz should remain a generic renderer and schema consumer.
