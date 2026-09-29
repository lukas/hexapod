# Self-seating spring insert — snap-on sensor foot

Replaces the depth-glued v12 spring stop with a single hollow flanged insert. Push it into the 6 mm carbon-tube bore until the flange touches the tube end. The spring seat is then 13 mm inside the tube; upward spring force is carried through the sleeve to the flange and tube end. No adhesive is required on this insert. Spring preload holds it seated in the assembled foot; when disassembled it can slide out.

Insert: 5.8 mm outside diameter, 4.4 mm bore, 0.7 mm wall; 8 mm diameter × 0.8 mm flange. Spring remains 4 mm OD × 10 mm free length, installed at 9.5 mm. New plunger: 4 mm stem, 5.6 mm flat sensor pad, 0.5 mm pad thickness. At full 0.6 mm foot travel the pad clears the flange by 0.4 mm. The spring seat and travel are unchanged in assembly coordinates; the tube end now sits 0.5 mm higher than v12.

## Assembly

1. Verify tube is 8 mm OD / 6 mm ID and its end is square, clean and deburred. Dry-fit the insert; it must seat by hand without forcing it into carbon.
2. Bond the external guide to the tube with guide top 23.5 mm above the tube end. This external bond remains necessary. If reusing v12, its old 24 mm guide-to-tube-end setting must be adjusted by 0.5 mm.
3. Push the flanged insert into the tube until seated; no depth measurement or glue inside the tube.
4. Drop the spring into the insert through its bottom opening, then insert the new stepped plunger, spring-locating pin first.
5. Attach the sensor to the foot, route the tab, align the foot pockets with the guide hooks, and snap together. Check both hooks engage, free return, full 0.6 mm travel and shoulder contact.

The v12 foot and guide geometry can be reused. Replace the spring stop and plunger together. All four PETG parts are in all_petg_parts.3mf. Print insert closed end down, guide top down, foot sleeve rim down, plunger sensing face down. Inspect thin sleeve walls and the flange overhang in the slicer. Keep supports and adhesive out of the spring/plunger bore. Smooth the sensing face.

## Verification and limits

Run `uv run --no-project --with trimesh --with manifold3d python make_seated_foot.py`.
Seven watertight single-solid meshes; seven travel positions clear fixed parts; compression shoulder and extension hooks engage beyond nominal travel; wire clearance and print transforms pass. Axial insert insertion clears the tube, its flange blocks upward over-insertion, and the illustrative spring clears the insert. These are geometric checks, not a physical load test. Thin-wall print fit, flange strength, snap fatigue, return friction, spring rate and angled ground contact remain untested. Spring helix is illustrative rather than a measured coil/end model.
