# LLM / agent geometry API — detail

Backing detail for the "LLM / agent geometry API" section of
[`../ROADMAP.md`](../ROADMAP.md). Merges the original API proposal with field notes
from a real multi-day agent CAD session. The throughline from that session:
**make geometric truth a shared, viewable artifact** — most wasted effort was the
agent computing something privately (a throwaway `trimesh` script) and failing to
convince the human. Commands whose JSON is *also* a viewer overlay fix that.

## Conventions (shipped)

```sh
buildviz <noun> <build-dir> [target] [options] --json
```

Every command supports `--json` (the primary contract) and returns the standard
envelope: `{ ok, build, summary, results, warnings, errors }`. Agents check `ok`,
read `summary`, then inspect `results`. Common filters: `--part`, `--instance`,
`--feature`, `--group`, `--out`.

## Already shipped (don't re-propose)

`validate`, `assets`, `part`, `feature`, `query`, `inspect`, `highlight`,
`screenshot`, `diff`, `versions`, and `check` (which covers the proposal's
`clearance` collision/near-miss surface and, via `mating_contact`/`thread_engagement`,
parts of `contacts`/`fasteners`). **Articulated-pose clearance** — the field notes'
top "new" ask (visualize the design's real collision at hip-yaw = −35°) — shipped as
the **Motion** model + `buildviz sweep` (`joints[]`/`poses[]`, swept-pose overlay).

## High-value remainder (prioritized by field evidence)

### 1. `probe points` / `probe region` — PLANNED (highest value)

"Is this point solid material, a hole, or a void?" / "Is this box filled?" Directly
ends the recurring "I just do not believe that a flat plane z=0 causes a collision"
standoff. Output reports per point: `insideSolid`, `nearestSurfaceDistanceMm`,
`nearestFeature`, `classification` (solid / expected_hole / void); per region:
`occupiedFraction`, `occupiedVolumeEstimateMm3`, occupied bounds, nearest feature.
Crucially, the same JSON should also paint as a viewer overlay (reuse the
point/region highlight channel). Built on the existing BVH point-in-mesh test.

```sh
buildviz probe points <build> --part coxa_link --points '[[-2,5,39],[10.4,0,2]]' --json
buildviz probe region <build> --part coxa_link --box "x=-11:7,y=0:11,z=36:42" --json
```

### 2. `slice` (+ `--metric min-thickness`) / `thickness` — PLANNED

Cross-section sweep that *proves* "the spar is 12mm along the full beam" and "the +Y
face is coplanar at +12" instead of eyeballing the viewer. `slice` returns section
area, connected regions, min local thickness, section-island bboxes, optional
SVG/PNG/ASCII. `thickness` returns min thickness, where it occurs, direction of
weakness, threshold pass/fail. (The `check` engine already has a heuristic
`wall_thickness`; this exposes it per-region with a cut.)

```sh
buildviz slice <build> --part femur_link --plane yz --range x=0:75:2 --metric min-thickness --json
```

### 3. `mesh stats` — PLANNED

Per-part bounds / extents / volume / surface area / triangle + vertex count /
watertightness / connected components / non-manifold edges / degenerate faces — no
custom script. The geometry engine already computes most of these for `check`
(`analyzeTopology`, `disconnected_components`), so this is largely a CLI surface
over existing data. Would have adjudicated a watertightness disagreement in one call.

## Proposed (lower priority / needs a decision)

- **`measure gap` / `contacts` / `fasteners`** — signed gap / mating-face quality /
  per-fastener engagement + access. Partial overlap with `check`'s `mating_contact`
  and `thread_engagement`; decide what's a distinct command vs a `check` view.
- **`identify` (dual world + part-local frame) + an on-screen axis triad** — remove
  the constant viewer↔part-local coordinate-translation tax ("max Y" vs part-local
  mm). High value, low cost; the field notes flagged getting this mapping wrong as a
  large recurring cost.
- **`topface` coplanarity / bed-contact** — "make all high-Y parts go to one max-Y
  value" is a checkable property (distinct plane heights + areas; print-orientation
  bed-contact patch). A specialization of `thickness`/`printability`.
- **`bom` / `trays`** — parts + hardware list; print-plate layout inspection (note
  `pack` already computes plate layouts).
- **`compare`** — richer two-build delta (mesh-hash, bounds/volume deltas, new vs
  resolved collisions/warnings). Overlaps with `diff`; scope before building.
- **`status` (stale-vs-source)** — flag scene stale relative to source files +
  suggest the regen command, wired into the agent's pre-render step.
- **`explain`** — a higher-level convenience that bundles part summary + features +
  mesh stats + slice/thickness + nearby fasteners + screenshots + `llm_context` into
  one prompt-ready evidence packet. Build last, on top of the primitives above.

## Discoverability lessons (existing features under-used)

The session reached for browser automation / custom scripts instead of shipped
features: `screenshot --view yz --edges --dimensions`, `diff`/`versions`, the
`highlight` runtime API, and stale detection. Surfacing these earlier (in
`BUILDVIZ.md` and the default skill workflow: `status` → `screenshot` → `diff`
before browser automation) is a cheap win independent of new commands.

## Field note: presentation-mode API friction (2026-09-04)

While showing the `single-motor-cat/tt-assembly-jigs` print aids, the diagram
feature itself worked well once reached: `create_diagram` could place real
snapshotted STL parts, annotate them, and open `/?diagram=...`. The rough edge
was the agent-facing path to get there.

- **Expose diagram mutators through the callable MCP surface everywhere.** The
  local hub advertised `create_diagram` / `update_diagram` over `/mcp`, but the
  available BuildViz tool wrapper only exposed read/check tools. The workaround
  was manual JSON-RPC via `curl`, which is too much ceremony for "show this in
  presentation mode." Tool discovery should surface `list_diagrams`,
  `get_diagram`, `create_diagram`, `update_diagram`, and `delete_diagram`.
- **Add a CLI convenience wrapper for diagrams.** A command such as
  `buildviz diagram create <name> --part build@version:part --at x,y,z --callout
  ...` or a higher-level `buildviz present` would make presentation mode usable
  without hand-authoring JSON. It should print the viewer URL and optionally open
  it, matching the ergonomics of `push-stl`.
- **Consider `push-stl --presentation` for one-off print aids.** The jig flow
  first needed `push-stl` to create a display build, then a separate diagram
  call to place those same parts. A shortcut that publishes loose STLs directly
  into a diagram would fit "show these helper parts" better than creating a
  permanent build solely as an intermediate.
- **Make live camera updates explicit.** `update_diagram` camera changes did not
  reliably recenter an already-open viewer until reload. Add an `applyCamera`
  style flag, a camera revision counter, or viewer behavior that treats camera
  updates as presentation steps unless the user has intentionally taken over.
- **Add a screenshot/fit check for diagrams.** Callouts can clip outside the
  viewport, especially with notes visible. A `buildviz diagram screenshot` or
  `diagram check --fit-labels` command would let agents verify that the presented
  canvas is readable before returning it to the human.
