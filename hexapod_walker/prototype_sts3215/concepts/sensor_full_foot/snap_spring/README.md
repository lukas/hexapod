# Snap-on PETG foot (v12)

Replaces the v11 M2 screw retainers with two integral cantilever hooks in the fixed guide. Four PETG prints; one 4 mm OD × 10 mm free-length metal spring, an 8/6 mm carbon tube, and the solid 10 mm sensor. No screws or tapping.

The hooks catch widened pockets in the moving foot. Their flat upper surfaces retain the foot at rest; lower ramps flex them outward during insertion. Each tab is 1 mm thick and 3 mm wide, rooted at Z22, with its retaining face at Z11.2. Nominal insertion deflection is approximately 1 mm. The relief slots expose the hooks for gentle manual release. PETG flexibility, layer adhesion and dimensional fit require a first-print test; elastic insertion is not simulated.

The original internal spring/plunger arrangement and 0.6 mm compression shoulder stop remain. The stop, rather than the hooks, carries additional compressive load. Bond spring stop and guide to the tube only; never glue the moving interfaces. See workflow.json for assembly dimensions and sequence.

## Printing

all_petg_parts.3mf contains all four separate parts in millimeters, spaced on the plate. Guide top down, foot sleeve rim down, spring plug top down, plunger sensing face down. Inspect the slicer preview for tab roots, gaps, and the sensor-cavity bridge. Remove any supports from moving gaps before assembly. Smooth the plunger face contacting the sensor. Existing v11 plunger and spring stop can be reused; foot and guide must be replaced together.

## Verification

Run `uv run --no-project --with trimesh --with manifold3d python make_snap_foot.py`.
All seven meshes are watertight, positive-volume single solids. Seven positions through 0–0.6 mm travel clear the fixed parts. A further 0.1 mm compression engages the shoulder, and 0.1 mm extension engages the hooks. Wire clearance and print-to-assembly transforms pass. No physical spring force, snap strength, fatigue, friction, return reliability or angled-contact performance has been validated.
