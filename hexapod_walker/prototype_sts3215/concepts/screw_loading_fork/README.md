# Two-screw loading fork — prototype v1

A removable hand tool for loading two **opposite M3 horn screws, 14 mm apart**.
Pitch is taken from `hexapod_prototype.py`'s `DISC_HORN_BOLT_PCD`, not measured
from the user's hardware. Confirm that your bracket matches before printing.
No robot parts are modified.

## Print

- `stl/fork_snug.stl`: 2.9 mm slot throats and 3.3 mm seats; slight spring
  interference with nominal M3 threads aims to retain both screws.
- `stl/fork_loose.stl`: 3.3 mm open slots; fallback if snug version grabs.
  Hold this version horizontal, heads up: it does not positively retain screws.
- PETG, flat underside on bed, 0.2 mm layers, no supports, solid fill.
  The blade is 0.8 mm (four layers); handle is 3.2 mm. Overall 23 × 42 mm.
- Only print the fork files. Gold screw and gray plate meshes are schematic
  visual references, not replacement hardware. STEP files are also included.

## Use

1. Load two screws from above into the circular seats; heads rest on the blade.
2. Place against the accessible bracket face and align tips with opposite holes.
   This prototype locates using the screw tips, not a bracket-specific stop.
3. Start both by hand, ideally at least two turns, **leaving the heads loose**.
   The carrier consumes 0.8 mm of available screw projection. If the original
   screws cannot engage, do not force them or substitute longer screws blindly.
4. Pull the handle straight back in its own plane so shafts exit the open slots.
5. Finish tightening; rotate the tool 90 degrees for the other opposite pair.

The central open notch provides nominal clearance for a head up to 7 mm wide.
Driver/head access, available thread engagement, surrounding bracket clearance,
printed retention force and flex fatigue need a physical fit check. No torque
setting is specified. Snug fork retention is a prototype hypothesis, not a test
result; use the loose fork if removal disturbs the started screws.

## BuildViz

Left: printable snug fork. Middle: screws loaded over a schematic face.
Right: loose carrier withdrawn 16 mm, with screws left in place. The middle and
right use the loose geometry so the illustrated release is collision-free.

Build: `prototype_sts3215/screw-loading-fork`.

Regenerate with `uv run --with build123d --with trimesh python build.py`.
`checks.json` records watertight/positive-volume meshes and sampled nominal
release clearances. The 14 mm pitch matches the source; it is not a physical
measurement or full assembly fit validation.
