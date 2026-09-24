# BuildViz Compatibility

A **BuildViz-compatible project** is a build directory BuildViz can load, render,
and critique. This is a contract for LLMs/agents generating physical-build
projects: satisfy the five requirements below and BuildViz can act as a clear
critic of the design. Run `buildviz compat <dir>` to check where you stand.

## Required layout

```text
<project>/
  scene.json         # REQUIRED: the BuildViz manifest the viewer/CLI load
  design_spec.yaml   # REQUIRED: semantic spec covering every part in the scene
  ASSEMBLY.md        # REQUIRED: assembly directions (project-authored)
  BOM.md             # REQUIRED: bill of materials (project-authored)
  stl/               # REQUIRED: STL meshes referenced by scene.json
    *.stl            #   (folder name is free: stl/, stl_prototype/, meshes/, ...)
```

## Each required file

- **`scene.json`** — the manifest BuildViz loads: `meshes[]` (each `id` + `url`)
  and `instances[]` (each `id`, `meshId`, `partType`, 4×4 `transform`). The core
  requirement — everything else is layered on it. Full shape:
  `BUILDVIZ_INTEGRATION.md` → "scene.json Contract".
- **STL folder** — the printable meshes every `scene.json` mesh `url` points at.
  Every referenced mesh must resolve on disk (any folder name works).
- **`design_spec.yaml`** — the durable record of **design intent and rationale**
  (why each part is the way it is) *and* BuildViz's semantic source of truth: one
  entry under `parts:` per part type in the scene. **Keep it current** — update the
  matching entry in the same change that alters a part's geometry/CAD/STL; a spec
  that doesn't match the current parts is a defect. *Up to date* = every scene
  `partType` has a spec entry (a scene part with **no** entry is a **fail**), no
  stale entry lingers, and the file isn't older than the scene/geometry it
  describes. Schema + freshness rule: `DESIGN_YAML_SPEC.md`.
- **`ASSEMBLY.md`** — human-readable assembly directions. Present + non-empty.
- **`BOM.md`** — human-readable bill of materials. Present + non-empty.

## Critic APIs vs project-authored files

`ASSEMBLY.md`, `BOM.md`, and `design_spec.yaml` are **project-authored**. BuildViz
*derives* facts you check them against — run these to self-critique:

- `buildviz bom <dir>` — derives a BOM from geometry; reconcile it with your
  authored `BOM.md`.
- `buildviz check <dir>` — geometry critic: interference, connectivity,
  printability, assembleability.
- `buildviz validate <dir>` — manifest/spec/asset consistency.

## Self-check

```sh
buildviz compat <dir> --json     # am I compatible? per-requirement pass/warn/fail + verdict
buildviz validate <dir> --json   # scene/spec/asset consistency
buildviz check <dir> --json      # interference / printability / assembleability
buildviz bom <dir> --json        # geometry-derived BOM to reconcile with BOM.md
```

## Compatibility CHECKLIST

- [ ] `scene.json` present, parses, and passes basic manifest validation.
- [ ] Every `scene.json` mesh `url` resolves to an STL on disk.
- [ ] `design_spec.yaml` present; `parts:` covers every scene part type (a scene
      part with no entry **fails**), no stale entries, and updated whenever
      geometry changes (an older-than-the-scene spec **warns**).
- [ ] `ASSEMBLY.md` present and non-empty.
- [ ] `BOM.md` present and non-empty.

`buildviz compat` reports each line as **pass / warn / fail** and prints a
remediation list when you are not compatible. **Compatible = no `fail`**; a
missing `scene.json`, STL, `design_spec.yaml`, `ASSEMBLY.md`, or `BOM.md` fails.
For `design_spec.yaml`, a **scene part with no spec entry now fails** (an
uncovered part is the "the agent dropped it" case), while stale spec entries with
no matching scene part and a spec older than the scene/geometry only **warn**
(fix them to stay a good critic target and to keep the rationale trustworthy).
