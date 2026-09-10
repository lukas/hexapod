# Two-piece coxa — full support plate + four self-tappers

The lower support plate now follows the upper part's actual mating outline,
including its corner pads, instead of a separately sized rectangle. Only the
original circular yaw hub extends outside this shared outline. The generator
checks the final face outlines outside that circular region (0.05 mm² tolerance).

This concept revives the retired coxa Part A / Part B split for easier FDM
printing.  The seam is the existing yaw platform plane, so both pieces have a
large planar print face:

- `coxa_hub_screw.stl`: yaw hub, bearing seats, dust lip, and a rectangular
  support plate spanning the hip-bracket footprint.
- `coxa_leg_screw.stl`: hip servo holder and 688 housing, trimmed to the
  platform seam with four reinforced corner pads.

The fasteners are four M3 self-tapping screws, installed from the underside of
Part A and driven upward into the four Part-B corner pads.  The yaw hub is
expanded to a full rectangular support plate under the bracket; there are no
hex inserts or old join-screw holes in this version.

Part B also has five open yaw-drive access shafts: one central shaft and four
on the 14 mm disc-horn PCD, aligned with the yaw-hub hardware below.

The access cuts now continue through Part A's support plate as well, after all
unions. The spacer version shares `horn_compression_limiters/spacer_config.toml`:
four Ø4.7 mm bores receive the existing Ø4.5 × Ø3.2 × 10 mm sleeves. Perimeter
washer seats are 10.1 mm above the horn face; Ø7.2 mm access shafts accept the
7 mm OD washers. Use M3×12 horn screws plus 0.5 mm washers, NOT the old M3×30.
The central spline screw and the four bracket-joining screws are unchanged.
The lower neck is Ø22 mm, preserving 1 mm radial clearance in the Ø24 opening.
Both exported solids are tested for unobstructed driver/spacer paths and
supported washer seats. Gold spacer meshes are reference hardware, not prints.

The source geometry is derived from the legacy two-piece builders in
`hexapod_prototype.py`; the production `coxa_link` remains one piece.

Generate with:

```sh
uv run --no-project --python 3.12 --with trimesh --with numpy --with manifold3d \
  python concepts/two_piece_coxa_screws/make_two_piece_coxa_screws.py
```
