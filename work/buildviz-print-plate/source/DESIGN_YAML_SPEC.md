# Design YAML Spec

## Why this file exists / what to capture

`design_spec.yaml` is the durable record of **design intent and rationale** — *why*
each part, feature, and dimension is the way it is — written by the agent that made
the part so future work doesn't have to re-derive it. When the next agent (or you,
later) asks "why is this bore Ø22, why is the servo mounted this way, why this wall
thickness?", the answer lives here instead of being lost and re-researched from
scratch. Capture the reasoning you'd otherwise throw away: the decision, the
trade-off, what you rejected and why.

It is also BuildViz's single semantic source of truth for CAD generation, renderer
labels, validation, and LLM context — but the *primary* value is the rationale.

**Record decisions and trade-offs**, not just measurements. Use `purpose`,
`llm_context`, `llm_hint`, and `description` to say why this size / orientation /
material was chosen and what alternatives were rejected. A brief per-part rationale
or decision note (in `description`/`purpose`) is encouraged.

## Freshness rule (not optional)

**Whenever you change a part's geometry, CAD, or STL, you MUST update its
`design_spec.yaml` entry — rationale, dimensions, and features — in the SAME
change.** A spec that no longer matches the current parts is a **defect**, not a
nicety: it silently misleads the next agent. Don't treat this file as write-once
scaffolding. `buildviz compat` enforces this: a scene part with no spec entry is a
**FAIL**, and a spec older than the scene/geometry it describes is flagged as
possibly stale.

## Schema

Each generated part should follow this shape:

```yaml
parts:
  part_id:
    label: "Human name"
    aliases: ["terms user might say"]
    description: "What this part does"
    generated_by:
      file: "source file"
      function: "CAD function"
      output_stl: "path/to.stl"

    local_frame:
      origin: "Named origin"
      axes:
        x: "Meaning of +X"
        y: "Meaning of +Y"
        z: "Meaning of +Z"

    features:
      feature_id:
        label: "Human feature name"
        aliases: ["terms user might say"]
        kind: "joint | spar | clevis | bolt_pattern | pocket | channel | boss"
        purpose: "Why this feature exists"
        llm_context: "How to reason about changes to this feature"

        render:
          anchor_mm: [x, y, z]
          label_offset_mm: [dx, dy, dz]
          label_priority: high

        dimensions:
          dimension_id:
            label: "Human dimension name"
            value: 0.0
            axis: x
            from_mm: [x, y, z]
            to_mm: [x, y, z]
            code_name: CAD_CONSTANT_OR_PARAM
            derived_from: optional_global_param
            description: "What this measurement means"
            llm_hint: "What changing this affects"
```

Rules:

- Every meaningful subpart gets a stable `feature_id`.
- Every user-facing name gets `label` and `aliases`.
- Every CAD input or dimension gets a named `dimension_id`.
- Every dimension includes local axis, endpoints, value, and code link.
- The renderer uses `render.anchor_mm` and dimension endpoints for labels and arrows.
- The LLM uses `description`, `purpose`, `llm_context`, and `llm_hint` — put the
  *rationale* (why this choice, what was rejected) there, not just what a field is.
- CAD code should consume values from this file, not duplicate constants.
- Keep it current: update the matching entry in the same change that alters a
  part's geometry/CAD/STL. A drifted spec is a defect (`buildviz compat` fails on
  uncovered parts and warns when the spec is older than the scene/geometry).

## Wiring

If the scene publishes wires (`routes[]` in `scene.json`), record each route's
purpose under a top-level `wiring:` section keyed by route id — the hub warns
on push/register (and the viewer badges) when a published wire has no entry or
an entry has no matching route:

```yaml
wiring:
  w-batt-bec-a:
    purpose: "Main battery discharge lead from the XT60 to BEC A."
    signal: "7.4V LiPo raw"        # optional, free-form
    gauge: "16 AWG silicone pair"  # optional, free-form
    notes: "Anything a rebuilder or LLM should know."
```

The physical routing rules (bend radius, clip spacing, clearance, obstruction)
are validated from the geometry by `buildviz check`; this section records the
*intent* — what the wire is for — which geometry cannot express.
