# Wider-hook PETG snap foot

Successor to v13, retaining four printed parts, the 4 × 10 mm metal spring and self-seating insert. Both the foot and guide change; reuse the v13 plunger and spring insert. Print new foot and guide as a matched pair.

## Retention changes

- Each hook/tab is 4.2 mm wide instead of 3 mm; matching foot pockets widen to 5.4 mm, preserving 0.6 mm clearance per side.
- Inward hook tip radius is 5.0 mm instead of 5.2 mm: 0.2 mm more radial engagement.
- Tab thickness increases from 1.0 to 1.2 mm. Root moves from Z22 to Z24 to lengthen the flexible section and accommodate insertion deflection.
- Flat retaining faces and sloped insertion ramps remain. No screws or extra collar. Hooks are manually accessible for release.
- Model-derived total retaining bearing area increases from 4.414 to 7.341 mm² (about 66%). This is geometric contact area, NOT a measured or simulated increase in pull-out strength.

The nominal travel remains 0.6 mm. The shoulder carries additional compressive load. Confirm both hooks return into their pockets after insertion, then check retention with a gentle tug and verify free return under spring preload. A snap sound alone does not prove both hooks are seated. Insertion force, root fatigue and layer adhesion remain untested.

## Printing and assembly

All four parts in all_petg_parts.3mf are spaced and oriented for PETG printing. Guide top down, foot sleeve rim down, insert closed end down, plunger sensing face down. Inspect thin walls, tab roots, gaps and overhangs in the slicer. Clear any support from moving surfaces.

Push the flanged insert into the 6 mm rod bore until it seats against the square, deburred tube end. No glue on the insert. Bond the external guide to the tube with the guide top 23.5 mm above the tube end. Insert spring and plunger, attach sensor to foot, align pockets and hooks, route the wire and snap together. Keep adhesive off sliding parts.

## TPU

The user clarified TPU, but did not specify hardness or grade. This revision remains PETG. A mixed-material variant could add a separate TPU tread over a rigid sensor backing; retain rigid guide, hooks, plunger and spring insert. An all-TPU conversion needs its own geometry and tests because compliance could change retention, friction, preload and the travel stop. Do not assume the 0.7 mm sleeve wall or 1.2 mm latch will behave the same in TPU. This revision does not include a TPU tread.

## Checks

Run `uv run --no-project --with trimesh --with manifold3d python make_secure_foot.py`.
Seven watertight, positive-volume single-solid meshes; seven full-stroke clearance positions; each hook independently captures the foot on extension; shoulder compression stop; wire clearance; spring insert seating/insertion; illustrative spring clearance; print-to-assembly transforms. Physical retention, print tolerances, spring rate and fatigue still need testing.
