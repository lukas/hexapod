# Wiring / cable-route support

Status: SHIPPED

Goal: publish where all the wires are as part of a build, see them in the hub
viewer with a toggle, get guidance on how to neatly attach them (anchors /
clips), and have checks make sure the wires are considered (bend radius,
support spacing, clearance, length, obstruction).

## Research: how other software does this

- **SolidWorks Routing** (MCAD standard): wires are 3D splines between
  *connection points* on routing-aware connectors, snapped through *clip*
  components dropped into the assembly. The cable library carries diameter and
  minimum bend radius; the tool enforces bend-radius violations in real time,
  auto-computes cut lengths from the 3D path (+ a slack percentage), and
  reports the bundle diameter. Routes live in a dedicated route sub-assembly.
- **WireViz** (open source, closest in spirit to BuildViz): a human-readable
  YAML harness definition — `connectors` (pinlabels), `cables` (gauge, color,
  length), `connections` — that is version-controlled next to the code and
  generates diagrams/BOMs. It deliberately does NO 3D geometry.
- **Physical design rules** (IPC/WHMA-A-620 and industry practice):
  - minimum bend radius ≥ 6 × bundle OD static, 10–12 × OD dynamic/flexing;
  - support (clip/tie) spacing 150–300 mm, never exceeding 300 mm;
  - first clamp 50–80 mm from a connector (strain relief);
  - ≥ 10 mm clearance from sharp edges / heat sources.
- **Rendering** (three.js): Catmull-Rom curve through the path points,
  extruded with `TubeGeometry`.

Takeaway: geometry (the 3D path with anchors) belongs in the scene, intent
(what each wire is for) belongs in the design spec, and the rules above are
mechanical checks a machine can run.

## What BuildViz already had

`scene.json` already had an additive `routes?: Route[]` — an ordered polyline
of WORLD-frame waypoints with an optional `maxLengthMm` budget — and a
`routing_reach` check (length budget + straight-segment obstruction test).
No instance anchoring (wires didn't follow parts), no diameter/bend-radius
model, no attachment concept, no viewer rendering, no design_spec tie-in.

## Design: extend `Route`, don't invent `wires[]`

All additions are ADDITIVE — old scenes and old viewers keep working.

### Schema (`core/buildScene.ts`)

```jsonc
{
  "routes": [
    {
      "id": "w-batt-bec",
      "label": "Battery → BEC power",
      "kind": "power",              // power | signal | data | ground | ...
      "diameterMm": 3,               // bundle OD; drives rendering + bend rule
      "color": "#dc2626",           // optional; falls back to a kind color
      "minBendRadiusMm": 18,         // optional; default 6 × diameterMm
      "maxLengthMm": 160,            // optional length budget (existing)
      "maxUnsupportedMm": 80,        // optional; default checksConfig/150mm
      "waypoints": [                 // preferred over legacy world "points"
        { "instanceId": "020-lipo_battery", "local": [0, 18, 6] },  // endpoint = implicit anchor
        { "position": [10, 30, 60], "anchor": true, "label": "chassis clip" },
        { "instanceId": "016-bec_a", "local": [0, -8, 4] }
      ]
    }
  ]
}
```

- A waypoint is either world-frame (`position`) or ANCHORED to an instance
  (`instanceId` + part-local `local`, default `[0,0,0]`) — anchored points ride
  with the part through versions and kinematic poses.
- `anchor: true` marks a physical attachment (clip/tie/standoff). Endpoints
  are always implicit anchors (they terminate at connectors).
- Legacy `points` (world polyline) still works everywhere; `waypoints` wins
  when both are present.

### Core math (`core/buildWiring.ts`, three-free)

`resolveRoute(manifest, route, poseOverrides?)` → world control points +
anchor flags (+ termination instance ids); `sampleRoute` → centripetal
Catmull-Rom polyline (the same curve the viewer draws); `polylineLength`,
`minBendRadius` (circumradius over sampled triples), `unsupportedSpans`
(arc length between consecutive anchors), `effectiveMinBendRadiusMm`
(explicit or 6 × OD).

### Checks (`checks/`)

Evaluated on the SAMPLED curve (not straight segments), all default-on and
no-ops for scenes without routes:

- `routing_reach` (existing, upgraded to the curve): length vs budget +
  pass-through-solid obstruction.
- `wire_bend_radius` (fail): sampled bend radius < allowed (explicit or 6×OD).
- `wire_support` (warn): longest span between anchors > `maxUnsupportedMm`
  (default 150 mm) — the "add a clip/tie here" nudge, with the span midpoint
  as the highlight anchor.
- `wire_clearance` (warn): wire surface passes closer than `wireClearanceMm`
  (default 1 mm, config/flag-overridable) to a non-termination solid —
  chafing risk.

`checksConfig` gains `wireClearanceMm` + `maxUnsupportedMm`; `check` gains
`--wire-clearance <mm>` / `--max-span <mm>`.

### CLI

`buildviz wires <build> [--json]` — fast, geometry-free listing: per route the
kind, diameter, resolved length, min bend radius vs allowed, anchor count,
longest unsupported span, endpoints. The wiring check kinds also run in
`buildviz check` by default.

### Viewer (hub)

A "Wiring" control group (shown only when the scene has routes) with a show/
hide toggle. Wires render as Catmull-Rom `TubeGeometry` tubes (radius from
`diameterMm`), colored by `color`/kind; anchor points render as small spheres.
Anchored waypoints follow the pose scrubber (forward kinematics).

### design_spec.yaml

New optional `wiring:` section documenting each route's purpose (WireViz's
role in this split). Spec coverage — the hub push/register warnings and the
viewer badge — now also flags routes with no `wiring:` entry and stale
entries for routes that no longer exist.

## Non-goals (unchanged from plans/validation.md)

- No automatic route inference/autorouting — producers publish routes the same
  way they publish joints[].
- No cable physics (sag/stiffness simulation); the published path is taken as
  the intended path.
- No pin-level connectivity/netlist (WireViz does that well; a design_spec
  `wiring:` entry can link to one).
