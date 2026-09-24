# Supported two-point knee cap — premade-chorn-56 v35

Published as a new immutable revision to local and cloud BuildViz. v34 was
not overwritten; v6 remains the default review baseline. This work changes
only `femur_ovh_body` and `knee_clamp_cap_ovh`, with 12 M3x8 screws and 12
ordinary M3 nuts added as purchased hardware references. All original
instance transforms and all other mesh assets are preserved.

## Why

v34's claimed underside second attachment has no actual receiving boss in
the cap. The remaining face-open nut pocket also cannot retain its nut in
the screw-pull direction without the cap itself closing it. v35 replaces
this arrangement with two same-face recessed screws into end-loaded nuts
beneath 3 mm solid femur roofs. The pocket is 5.8 mm AF x 2.7 mm, for an
ordinary M3 nut (nominal 5.5 mm AF x 2.4 mm thick).

A straight-across inboard station at cap-local (-34,17.15) hit the chassis
near -105 degrees hip lift. The final station is (-34,35.5), in the upper
corner, within the existing femur's height. The original outboard station
at (27.2,17.15) is retained. Both screw heads are flush with the same cap
face. No inaccessible underside screw, tall upper tower, or reduction of
the sampled motion range is needed.

## Reproduce

From the repository root:

```sh
uv run python hexapod_walker/prototype_sts3215/concepts/knee_cap_two_point/make_variant.py
uv run python hexapod_walker/prototype_sts3215/concepts/knee_cap_two_point/render_preview.py
```

The generator reads the frozen v34 manifests in `baseline/` and SHA-checked
asset files in the local BuildViz cache. It never regenerates unrelated
geometry from the main concept generator. `publish.py` accepts a NEW version
number and reads `BUILDVIZ_API_KEY`; it never forces an overwrite or prunes.

## Print and assemble

Print one matched pair first. `output/print/` contains the two STLs already
oriented with their broad flat faces on the bed. Cap contact area is about
2014 mm²; femur contact area is about 680 mm². They retain the source PETG
material designation. These are fit-check files, not a manufacturing release.

Slide one ordinary M3 nut into each end-entry femur slot before fitting the
cap. Seat the cap and insert two M3x8 socket-head screws from its outer face.
The nuts pull against the femur's retaining roofs, not against the cap.
Remove both screws to release the cap and use the existing horn-on service
opening. Print both updated pieces; the new cap alone cannot fix v34's body.

The femur-to-hip-C joint is unchanged: six screws enter from inside the
aluminum C bracket through its 2.1 mm end web into six short front-loaded
M3 insert pockets in the femur. Those pockets are Ø4.6 x 3.1 mm deep, with
0.5 mm printed skin behind them. The user's 5.7 mm inserts do NOT fit.
Four holes are on a 14 mm circle and the outer pair is 37 mm apart. The
large center hole is clearance, not a fastener. Choose the front screw
length/washer stack by measurement; do not bottom against the servo.

## Verification and limitations

`output/checks.json` records local exact geometry tests: nut insertion,
anti-rotation and blocked axial pullout; supported head seats; full nominal
2.4 mm nut engagement; cap removal; horn-on servo extraction; Ø5.5 x 50 mm
driver access on all six knees; and no new authored-pose overlaps. Hip
-110..+30 and knee -30..+20 degrees were sampled every 2.5 degrees. Chassis
tests use yaw -35,-20,0,+20,+35. Adjacent unchanged legs were not revalidated.

`output/v35-server-verification.json` records all 12 new knee fastenings
passing BuildViz, zero unexpected collisions, and closed single-volume cap
and femur meshes with no self-intersections. Global `results.passed` remains
false: both v34 and v35 have 13 components and 12 floating articulated
groups. The floating-instance count increases 72→96 because the 24 new
screws/nuts are connected into those same pre-existing femur groups.
Inherited printability annotations remain, including a femur thin-feature
estimate (0.343 mm); the cap's estimate is 1.669 mm. No physical print-fit,
pullout, stiffness or fatigue testing has been performed.

Source-version issue and resolution, successor validation, and exact-v35
assembly/print/purchased-part metadata are recorded in the cloud hub.

[Focused v35 assembly](https://buildviz.cwd1f0-new-cluster.coreweave.app/?catalog=hexapod-metal-v35-knee-cap-detail&build=prototype_sts3215%2Fpremade-chorn-56&branch=main&version=v35)
