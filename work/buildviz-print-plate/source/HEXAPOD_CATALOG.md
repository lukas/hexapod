# Finding and recording hexapod designs

Start with the **Hexapods** collection. Its three main entries represent the two
built robots and the next metal-clamp build. Assemblies, studies, and saved views
belong beneath those identities; the existing build IDs remain their source
addresses.

In the viewer, use **Jump to assembly** at the top of the sidebar, or press
**⌘K / Ctrl+K**, then type a name such as "chassis" or "spacer". Results show
the owning robot and open the assembly directly; the workshop also lists
one-click assembly links under each robot. Longer context is under **About
this design**, while the current revision message stays visible.

| Entry | Meaning | Existing source |
|---|---|---|
| `hexapod-1` — Hexapod 1 · original STS | First STS robot used in RobotLab. The original assembly reference is separately pinned. | `prototype_sts3215/hexapod-v1` |
| `hexapod-2` — Hexapod 2 · three-bearing STS | Owner-identified second robot: two lower bearings and one upper bearing; conversion to spacer-equipped joint parts is in progress. Exact installed revision is unrecorded. | `prototype_sts3215` (design reference) |
| `hexapod-metal` — Next hexapod · metal C-clamps | Planned robot using the purchased 56 mm C brackets. | `prototype_sts3215/premade-chorn-56` |

The similarly named `buildviz/hexapod-2` is an old bundled scene, not evidence for
the second physical robot's identity. It is archived with the other viewer
examples. The custom CNC overhead and split-CNC-clamp alternatives are studies
under the metal-clamp robot; they are distinct from the purchased-bracket design.

## Four kinds of catalog item

- **Robot:** a lasting identity for a built or planned machine. Its current
  design source may evolve while its as-built reference stays pinned.
- **Assembly:** a meaningful mechanical unit such as the chassis, yaw support,
  or knee and foot. It can reference its own design source or select components
  from a full-robot revision.
- **View:** a saved selection of components from an exact source revision.
  Changing what is visible does not create a new mechanical design.
- **Study:** a fit coupon, reinforcement comparison, stress analysis, or design
  alternative with its own question and revision history. A full-robot scene can
  still be a study.

Use `parentId` to place a component or study beneath its robot or another study.
Use the `hexapods` collection for this family. A study remains a study until an
explicit design decision adopts it; displaying the whole robot does not promote
its status.

## Design history and installed hardware

`source` identifies the design shown by an item. Omitting `source.version` follows
the named branch's current design; an explicit version is a fixed snapshot.
`asBuilt` is a separate exact reference supported by an installation record or
owner confirmation. Never copy the latest source into `asBuilt` automatically.

For the first STS robot, `asBuilt` points to
`prototype_sts3215/hexapod-v1`, branch `main`, version `2026-08-07-f9c91cf`.
That version's original note identifies the owner-confirmed RobotLab assembly.
The later captive-nut, hex-pocket, and horn-access revisions remain available
as design work. The separate physical-unit record lives in the hexapod repo at
`hexapod_walker/prototype_sts3215/robots/hexapod-1.yaml`.

On September 8, 2026, the owner identified the second robot by its **two lower
bearings and one upper bearing**, and said that conversion to all spacer-equipped
parts is in progress. Its physical record is `robots/hexapod-2.yaml` in the
hexapod repository. The main STS source remains a design reference, not an
as-built claim. The current rigid-hip design has one lower and one upper bearing;
the owner's robot is an earlier or mixed configuration, not automatically that
latest design. No exact installed revision has been identified.

The saved view `hexapod-2-bearing-layout-reference` selects the bearings and
surrounding supports from `sts3215-rigid-hip@main@v1`. That snapshot has six
instances of each of the two lower bearings and the upper bearing. The view is
a discoverable match for the reported bearing arrangement, not an as-built pin
or evidence of the spacer retrofit. It reuses the historical scene without
creating a new geometry history.

The existing `sts-horn-compression-study` identity now has kind **assembly** and
the name **Spacer-equipped joint parts**, beneath the second robot. Its source
remains `prototype_sts3215/horn-compression-limiters`: spacer-equipped coxa/yaw
support, femur, and knee-yoke parts with the fit coupon. The stable ID and source
history stay intact after adoption. The retrofit is in progress; selecting the
parts does not establish that every part has been installed or tested.

An absent as-built reference means the exact installed configuration has not been
recorded. It does not mean the robot was never built.

Use named `milestones` for meaningful design or assembly checkpoints. Preserve
all lower-level revisions without making every publish a milestone. Order the
revision history by its recorded time: the STS sources contain reused low-number
version names after older high-number names, so `v95` is not necessarily newer
than `v1`.

## Agent workflow

Find an existing identity before publishing:

```sh
buildviz catalog list --collection hexapods --json
buildviz catalog show hexapod-1
buildviz catalog list --parent hexapod-metal --json
buildviz catalog list --search "yaw support" --json
```

The MCP equivalents are `list_catalog` and `get_catalog_item`. Catalog records
carry the source build, branch, version, descriptive note, relationships, and
any as-built or milestone references. Read those references before selecting a
source for fabrication or comparison.

For a new view, reuse the selected source's exact branch and version, then set
`view.partTypes` or `view.instanceIds`. A selector must match actual components
in that snapshot. The selector applies to assembly entries too, so a chassis
can have a stable identity without copying its geometry into another build.

For a genuine component redesign or experiment, publish its source revision and
update the corresponding assembly or study entry. A catalog JSON file can contain
one item, an array of items, or an `{ "items": [...] }` object:

```sh
buildviz catalog upsert catalog-items.json --json
```

Keep semantic IDs stable and retain old source names as aliases when useful.
Aliases must be globally unique and must not repeat another item ID. Old
standalone sources are archived, not deleted, so links and histories remain
available.

Revision messages should be one or two sentences explaining what changed and,
when supported, why. For example: “Split the lower yaw carrier from the coxa and
use four underside screws. This exposes the screws during assembly.” A camera
change is a view edit; a mechanical change belongs in the source history.

## Auditing and applying the initial classification

The migration script defaults to a read-only audit. It snapshots every build and
every branch, retains existing messages, and fills description gaps across the
three primary robot histories. For other sources it covers recent revisions and
branch defaults. Descriptions come from saved scene differences; the report
includes all proposed writes and their evidence. Existing catalog items are
preserved on repeat audits.

```sh
uv run scripts/migrate_hexapod_catalog.py \
  --kubeconfig ~/.kube/coreweave.yaml \
  --report /path/to/hexapod-catalog-audit.json
```

The key is read from the existing `buildviz-api-key` secret and remains in
memory. Alternatively supply `BUILDVIZ_API_KEY` through the environment. No key
is written to the report. The former `--second-robot-confirmed` option remains
accepted for compatibility; the owner's three-bearing configuration is now
recorded without inferring an exact installed version.

After the catalog and revision-metadata APIs are deployed, apply the reviewed
report with:

```sh
uv run scripts/migrate_hexapod_catalog.py \
  --kubeconfig ~/.kube/coreweave.yaml \
  --apply --plan /path/to/hexapod-catalog-audit.json \
  --report /path/to/hexapod-catalog-applied.json
```

The script only adds catalog metadata and conditionally fills blank revision
messages. It does not rename sources, change geometry, delete versions, alter
branch defaults, or rewrite publication times. The backend labels backfilled
notes `messageSource: retrospective`. Scene differences establish what differs
in a saved visualization; they do not prove physical fit, strength, installation,
or the designer's reason for a change.
