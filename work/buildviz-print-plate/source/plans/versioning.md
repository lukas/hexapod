# Versioning & publishing — detail

Backing detail for the "Versioning & publishing" section of
[`../ROADMAP.md`](../ROADMAP.md). Merges the former versioning-suggestions and
on-disk-versioning field notes. The version *model* is solid and shipped; the open
work is making versioned builds easy to **adopt** (especially for local-asset and
static-published builds).

## What versioning is today (shipped)

PROJECT → BUILD → BRANCH → NAMED VERSION. A build holds one or more BRANCHES
(git-like parallel lines of work); each branch keeps its own named-version
history (`main`, `with-dome`, `v<N>`, …) and its own default version. The
default branch lives at the build root (exactly the pre-branch layout, so
branch-less builds are unchanged); every other branch lives under
`branches/<name>/` with the same internal layout. On disk:

```
<build-dir>/
  meta.json          # { defaultBranch, branches:[{name,defaultVersion,versions}],
                     #   defaultVersion/versions = default-branch mirror (back-compat) }
  scene.json  design_spec.yaml  stl/      # DEFAULT BRANCH's default version (mirrored at root)
  versions/<name>/scene.json  ...         # default branch's non-default versions
  branches/<b>/scene.json                 # branch <b>'s default version
  branches/<b>/versions/<name>/scene.json # branch <b>'s non-default versions
```

Addressing: `project/build@branch@version` explicit; a single `@x` resolves as a
branch when one matches, else as a version on the default branch. `push
--branch <name>` creates/updates a branch; `push --set-default-branch` promotes
it (physically swaps the branch dir with the root layout). The viewer has a
Branch picker (`&branch=`) and cross-branch compare (`compare=branch@version`).

- `enumerateBuilds`/`listBuildVersions` treat a dir as a build when it has
  `scene.json` *or* a `versions/<name>` snapshot (`scripts/buildsIndex.ts`).
- The viewer maps `?version=` to a URL (default → root `scene.json`, else
  `versions/<v>/scene.json`); the version menu + `?compare=` diff are driven by each
  build index entry's `versions[]`.
- `push` auto-archives into the **hub cache** (`writeCacheLayout`); `register`/`send`
  point the hub at an on-disk dir and overwrite its `scene.json` in place (no
  archiving). `buildviz migrate` normalizes legacy `v1`/`v2` into named versions.

This layout already works for **on-disk, register-based** builds with local STL
assets — the hub serve path rewrites relative `stl/...` URLs per version. The
friction is producing/serving that layout without hand-rolling it.

## The adoption gaps

1. **Static-hosting relative-URL footgun.** A statically-served `scene.json` with
   relative `stl/foo.stl` URLs resolves them against the *page* URL, so the STL
   404s; the 404 body is fed to `STLLoader`, surfacing as the infamous "Invalid
   typed array length". Today relative URLs only resolve through the hub serve
   path's `rewriteLocalMeshUrl` — the **viewer has no runtime equivalent**.
   → **Closed** by the shipped `assetsBaseUrl` support (below).
2. **No command produces the on-disk `versions/<name>/` layout for a register-based
   local-asset build.** `push` writes only into the hub cache and can't carry mesh
   binaries; `migrate` only normalizes an existing `meta.json`. So a local-asset
   consumer hand-copies scene/spec/stl into `versions/<name>/` and hand-edits
   `meta.json`. → addressed by `freeze` (planned).
3. **`push` can't carry binaries** — pushed scenes must reference already-reachable
   URLs. → "binary asset upload on push" (proposed).
4. **Read commands resolve a registered id only against the cache** — `buildviz diff
   robot-cat v5 v6` fails for a register-based build even though the hub HTTP serves
   it by that id; you must address by directory path. Minor; document it or teach
   read commands to consult the hub registry.

## (a) Scene-level `assetsBaseUrl` honored by the viewer — SHIPPED

The manifest gains an optional `assetsBaseUrl` (e.g.
`"/builds/my-build/versions/v3"`). The viewer's `makeGeometry` resolves relative
`mesh.url` values against it; absolute `http(s)` and `/`-rooted URLs pass through
untouched (mirroring `normalizeSceneAssets`):

```ts
const resolveMeshUrl = (url: string, base?: string) =>
  !base || /^[a-z][a-z0-9+.-]*:/i.test(url) || url.startsWith('/')
    ? url
    : `${base.replace(/\/+$/, '')}/${url.replace(/^\.\//, '')}`
```

This makes a `scene.json` self-describing about where its assets live, so the same
relative-URL build renders under the hub, static hosting, and inside a
`versions/<name>/` dir — no symlink hack, no per-deployment rewrite. `validate` also
warns `relative_mesh_url_static_risk` when a mesh URL is relative and no
`assetsBaseUrl` is set (it would 404 on static hosting even though
`missing_mesh_file`, which resolves against the local filesystem, passes).

## (b) `buildviz freeze <build-dir> --version <name>` — PLANNED

Write the canonical on-disk version layout **in place** for a register-based build,
carrying local assets — the local sibling of `push --set-default`:

```
buildviz freeze <build-dir> --version <name> [--set-default] [--force]
```

1. Read the build-root `scene.json` (+ `design_spec.yaml`, relative-URL `stl/`).
   Refuse to overwrite an existing `versions/<name>/` unless `--force` (versions are
   immutable).
2. Copy them into `versions/<name>/` (keep relative `stl/...` URLs — the hub rewrites
   per version; optionally de-dup identical STLs via content hash).
3. Write/refresh `meta.json` with the same writer `push` uses, so
   `enumerateBuilds`/the viewer/`diff` pick it up unchanged. `--set-default` mirrors
   the frozen version to the build root.

This is `writeCacheLayout` pointed at an arbitrary build dir instead of the cache,
minus the network — bounded, and strictly smaller than `publish` (b targets the
build's own dir; `publish` targets a separate static root). Both share the
layout/asset-copy core.

## (c) `buildviz publish` — PROPOSED

`buildviz publish <dir> --build-id <id> [--version vN] --out public/builds`: copy
assets into the output build dir, write viewer-resolvable URLs (set `assetsBaseUrl`
or rewrite to absolute `/builds/<id>/...`), place at
`<out>/builds/<id>/versions/<vN>/scene.json` (mirroring "latest" to the root), and
refresh `<out>/builds/index.json`. Gives auto-versioning on the static path.

## (d) Binary asset upload on push — PROPOSED

Let `push` optionally carry mesh bytes so a pushed build is fully self-contained in
the cache. Combined with push's auto-archiving, every push becomes an immutable,
self-contained version with its STLs. Product/transport decision (size, dedup).

## (e) Explicit scene `schemaVersion` — PROPOSED

Optional manifest integer recorded by `assertSceneManifest`, with `validate`
warning on unknown/older versions — useful precisely because BuildViz keeps every
old snapshot forever. Do it alongside the next scene-schema change.

## Docs follow-ups

- A "Mesh URL resolution" section in `BUILDVIZ_INTEGRATION.md` spelling out the
  three URL classes (absolute `http(s)`, absolute `/builds/...`, relative +
  `assetsBaseUrl`) once.
- A "publishing a versioned static build" recipe pointing at `register` (live) and
  `freeze`/`publish` (durable static).
