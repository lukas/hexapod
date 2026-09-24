# v37 — cap heat-sets, metal C-to-femur self-tappers

User-requested swap from immutable v36. Only the femur/servo box STL changes;
the plain v36 knee cap is reusable. Outside dimensions, 96 mm hip-to-knee
length, all existing instance transforms, and joint origins are unchanged.
Physical robot firmware/controllers and simulation sources are untouched.

## Connections, per knee

- Cap: two M3×8 machine screws into two M3 heat-set inserts, 5.7 mm long.
  Assumes 4.6 mm knurled outside diameter (same assumed stock as the roof).
  The empty box has Ø4.0 × 6.7 mm blind pilots with Ø4.4 × 0.2 mm lead-ins.
  Inserts enter from the cap mating face, not the back or a side slot.
  Nominal insert engagement 5.7 mm; screw-tip floor clearance 0.7 mm.
- Metal hip C bracket to femur: six 3 × 8 mm self-tapping plastic screws,
  driven through the existing 2.1 mm metal end web into Ø2.5 × 7 mm blind
  pilots. The screws tap the **plastic**, not the aluminum. Plastic entry
  5.9 mm; 4.9 mm full-diameter engagement with the modeled 1 mm point.
  Blind-tip clearance 1.1 mm; 2.6 mm material remains behind each pilot.
  Ø5.5 × 3 mm head envelope. No front inserts or captive nuts.
- The large middle clearance hole, servo-horn attachments, spacers, and
  knee-C-to-tibia socket attachment are unchanged.

Heat-set the inserts in the empty detached box first; confirm their actual
OD before printing a batch. Attach the metal web to the printed femur before
mounting that C bracket on the hip servo, for straightforward driver access.
Then fit the knee servo and cap using the two M3×8 machine screws. Do not use
self-tappers in the brass inserts. Do not overtighten the six plastic threads.

`output/print/` contains the revised femur and unchanged cap oriented on broad
flat faces. Print one fit-test first. Ø2.5 is a starting self-tap pilot for the
modeled screw, not a universal value for all thread profiles and printers.
Insert dimensions follow the existing project assumption, consistent with
[the M3×5.7 reference](https://www.ruthex.de/en/collections/gewindeeinsatze/products/ruthex-gewindeeinsatz-m3-100-stuck-rx-m3x5-7-messing-gewindebuchsen).
Printed strength, pullout, tightening torque and wear are not qualified.

## Reproduce and validate

From the repository root:

```sh
uv run python hexapod_walker/prototype_sts3215/concepts/knee_cap_heatset_front_selftap/make_variant.py
```

Frozen scene/spec/workflow inputs are under `baseline/`; every input mesh is
verified against its published SHA256. Assertions cover two insert envelopes,
six continuous self-tapping receivers and blind floors, unchanged geometry
outside the eight target holes, original instance/joint datums, screwdriver
and heat-setting access on the detached subassembly, fastener/servo clearance,
and cap removal with the front screws/inserts installed. Motion checks include
the new hardware: hip −110…30° and knee −30…20° at 2.5° increments; chassis
clearance at yaw −35, −20, 0, 20, 35°. Adjacent-leg swept motion is inherited,
not newly qualified. No load/FEA qualification is claimed.

`publish.py` sends a new numbered revision to the local and cloud hubs without
overwriting history or promoting the default. Rationale and findings remain
attached to the exact versions. Global inherited connectivity/printability
warnings must not be mistaken for a manufacturing release.

## Published check results

Published **v37** to both hubs, leaving v36 unchanged and v6 as the default.
All 48 changed fastening declarations pass (12 cap connections at 5.70 mm,
36 front connections at 4.90 mm). Full check with fasteners included finds
zero unexpected collisions. Box and unchanged cap are closed single solids
with no open/nonmanifold edges or self-intersections. Global `passed=false`
still reports 132 floating instances in 12 inherited articulated groups, now
including the added hardware. It also retains the same two failed checks as
v36: the unchanged coxa has two self-intersecting triangle pairs, and the
unchanged hip cap has 12 open edges. Neither is the modified knee box/cap.
This is not a manufacturing release of the full robot. The box's
minimum thin-feature estimate is 0.294 mm; local insert/pilot surrounds are
checked explicitly in the generator. No physical fit/strength test occurred.

[Focused v37 assembly](https://buildviz.cwd1f0-new-cluster.coreweave.app/?catalog=hexapod-metal-v37-cap-inserts&build=prototype_sts3215%2Fpremade-chorn-56&branch=main&version=v37)
