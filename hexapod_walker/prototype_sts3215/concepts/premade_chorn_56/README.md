# Premade 56 mm C-horn experimental hexapod

This is a separate, non-production full-robot build. It combines the
`rigid_hip` top/bottom 6805 bearing structure and the outboard hip layout with
the user's sixteen premade long aluminum C brackets. A symmetric hexapod needs
**12 brackets** (one hip and one knee bracket per leg); the remaining **4 are
spares**.

The build is `prototype_sts3215/premade-chorn-56` in BuildViz.

## Horn-on servo removal

Both motor holders now inherit the current production service opening. The
former rounded bridge over the horn has been removed: the Ø24 horn bore
continues at full width through the open +Y clamp face. After removing the two
clamp-cap bolts, the servo can slide out together with its fitted Ø20 disc horn
and clamp cap; the horn no longer has to be removed inside the holder. Three of
the four small front-case capture sites remain, with only the site swept by the
service slot omitted.

The concept generator refreshes the `cnc_chorn_overhead` BREP ancestors before
building, so the coxa and femur cannot silently retain an older closed-bridge
STL. It also sweeps a fitted-horn envelope through both final derived holders
with 1.5 mm radial running clearance. `--skip-ancestor-brep` exists only for
deliberate fast local iteration; the normal Make target never uses it.

## Rear support for the outboard coxa

The support is part of the coxa itself. Its footprint is the **rear circular
segment of the lower yaw hub**, using the same 19 mm outer radius and stopping
at X=−10.5 mm. That contour is extruded straight upward from Z=4 to Z=46.25
mm, so the stand never projects beyond the lower coxa envelope.

A matching flange is fused to the hip-cap/yaw-pedestal part above it.
Two M3×8 screws enter from the top at X=−14 mm and Y=±6 mm, pass through the
cap flange, and engage heat-set inserts in the coxa stand. The assembly can be
rotated for direct installation access. There is no separate support print,
lower stand interface, or lower stand screw set.

The marked lower and upper yaw-bearing protrusions are now separate cartridges,
so the coxa and hip cap both have flat print faces. The lower cartridge is
retained by two top-entry M3×8 low-profile screws through the two lower arms at
rear-diagonal positions between the horn-driver paths and has 0.10 mm radial
assembly clearance. The upper cartridge uses
three M3×8 countersunk screws from the cap underside. Both cartridges preserve
their original 6805 bearing seats and horn interfaces.

The old perforated lower rail remains deleted. The negative-Y side uses one
lower and one upper contour arm. On positive Y, the former two stepped arms
are now one solid rectangular block from Z=4 to 36.7 mm. Its root follows the
same R19 circle, and it stops at X=23.8 mm—the front edge of the existing servo
rear-retention tab—instead of continuing uselessly across the servo. Two Ø6.8
driver openings at X=21.7 mm preserve access to both tab screws. The inherited
front-case screw remains open through the Ø6.5 negative-side driver tunnel;
the positive side ends before that screw axis and is open air. The circular
bridge with the nine-hole grid is still absent, all five yaw-horn driver paths
remain open, and the horn-on servo extraction path is unchanged.

The coxa servo-holder foot is now centered in the top view. Its former
Y=−23.65..+16.65 footprint is completed to Y=+24.25, putting its centre at
Y=+0.30 versus the seated servo at Y=+0.50. Exact centering is shortened by
0.40 mm to retain 0.15 mm model clearance to the moving aluminum bracket. The
positive-Y tab block sits inside this footprint and stops at the retention tab,
so the odd ledge that projected above the servo in the drawing is gone. The
foot material is
only in the low Z=4..12 foot: the servo, horn, cap, hip axis, and open +Y
horn-on extraction path have not moved.

The existing under-plate hip-cap driver path is now completely outside the
R19 stand. The nearest yaw-horn screwdriver path gets a local scallop with 2
mm of extra radial clearance. The generator checks those service paths, the
matched outer envelope, and all six tower-to-chassis clearances.

The two coxa insert pilots are Ø4.6 × 5.7 mm with a short Ø5.1 lead-in. Treat
that as a starting value: tune it to the actual M3 heat-set insert vendor,
nozzle, and test coupon before committing six coxas and six caps.

## What is new

Per hip or knee joint:

- one purchased C bracket, modeled from the measured 56.0 mm outside span,
  approximately 2.1 mm plate, and 51.0 mm horn-axis-to-front reach;
- one `driven_spacer_7mm`: a one-piece Ø21 × 7 mm four-hole puck with a
  **blind Ø8.8 × 2.8 mm relief** for the driven horn's center screw head and a
  Ø4.2 tool-access hole through the roof;
- one `passive_spacer_7mm`: the same four-hole puck with a **complete Ø8.6
  center hole** for the passive retaining screw;
- a printed front receiver fused into either the femur body or tibia socket.
  It uses all six small holes on the bracket front: the usual 4× M3 on a Ø14
  pattern plus the two additional M3 holes. The extra pair measures **34.0 mm
  between its inner edges** and **40.0 mm across its outer edges**. That means
  the physical holes are Ø3.0 mm and their centers are **37.0 mm apart**, or
  **9.5 mm from each outside edge** of the 56 mm bracket. The bracket's central
  Ø8 hole is clearance, not a primary fastener.

The front M3 screws pass through the 2.1 mm metal web and 8 mm printed
receiver into accessible captive M3 nyloc pockets. This gives four screws
around the center plus a much larger top/bottom anti-twist couple. The tibia's
Ø8 carbon tube is coaxial with the front center hole and seats against a
0.30 mm printed stop behind the metal web.

The tibia tube boss now has four 6.8 mm-wide rounded radial windows around its
root. They expose the four captive nylocs that would otherwise be hidden by
the ring. The measured upper and lower screw pair already sits outside the
ring, so all six fasteners are reachable. The windows stop after the receiver;
the final 21.5 mm at the tube mouth remains a complete circular support collar.
Install the six bracket screws and nylocs before inserting the carbon tube.

The Ø8 tube hole is now **30 mm deep**, up from 14 mm. The longer socket grows
16 mm outward along the existing carbon tube, reducing its unsupported bending
span by 16 mm while leaving the foot position and blind tube stop unchanged.
It therefore does not require an additional 16 mm cut from the tube itself.

## Spacer fit

The current STS3215 horn-face span is 38.04 mm. Two 7.00 mm pucks produce a
52.04 mm assembled inside span. A nominal 56.0 mm bracket made from two 2.1 mm
plates has a 51.80 mm inside span, so the model predicts only **0.24 mm total
spread**, or 0.12 mm per bracket arm.

That is a sensible light spring preload, but the 56.0 and 2.1 measurements
were approximate. Measure all three before machining a batch. If the true
inside span differs, change `hardware_config.toml`; do not pull the arms into
place with the horn screws. A useful target is zero to 0.25 mm total spread.

Use M3×12 disc screws with a washer stack chosen from an actual projection
measurement. With 2.1 mm plate + 7.0 mm spacer, a 12 mm screw has 2.9 mm left
before washers; target roughly 1.5–2.0 mm engagement in the thin aluminum horn
and make sure the tip cannot touch the servo case. Do not assume the nominal
screw length is safe without this dry measurement.

The spacer STL files are suitable for a printed fit test. For the final robot,
6061 aluminum or another rigid, non-creeping material is preferred because the
pucks carry bolt preload in compression. Matching solids are under `step/`:
`driven_spacer_7mm.step`, `passive_spacer_7mm.step`,
and `front_6hole_fit_coupon.step`.

## Coupon result and remaining measurement assumption

The note supplied the outside span, plate thickness, reach, and center hole,
but not the bracket's blade/front width. The model uses the matching commodity
long-U nominal of **25.0 mm**. The 34.0 mm inner-edge and 40.0 mm outer-edge
measurements establish a 37.0 mm center span. The production coupon and both
receivers use those centers with Ø3.4 mm printed clearance holes; the bought
bracket reference shows the inferred Ø3.0 mm physical holes.

Reprint `stl/front_6hole_fit_coupon.stl` to confirm the measured pair before
printing the femur and tibia parts. A straight-on caliper photo would remove
the remaining 25 mm front-width assumption.

## Printable/COTS files

| file | quantity | use |
|---|---:|---|
| `front_6hole_fit_coupon.stl` | 1 first | verify purchased front pattern |
| `driven_spacer_7mm.stl` | 12 | prototype or machine in aluminum |
| `passive_spacer_7mm.stl` | 12 | prototype or machine in aluminum |
| `femur_body_premade_chorn.stl` | 6 | front receiver + femur/knee body |
| `tibia_socket_premade_chorn.stl` | 6 | front receiver + CF-tube socket |
| `coxa_link_ovh.stl` | 6 | flat coxa with stand + solid servo-tab block |
| `coxa_yaw_hub_carrier_ovh.stl` | 6 | screw-on lower 6805/horn cartridge |
| `hip_clamp_cap_ovh.stl` | 6 | flat yaw pedestal with stand flange |
| `hip_bearing_carrier_ovh.stl` | 6 | screw-on upper 6805 cartridge |
| `premade_chorn_56_DO_NOT_PRINT.stl` | COTS reference | the bought bracket |

The rest of `stl/` is the self-contained inherited robot print/reference set.
Files ending in `DO_NOT_PRINT` are viewer references.

## Geometry results

- 12 brackets, 12 driven pucks, and 12 passive pucks are instantiated.
- Each coxa contains its own contour-matched rear stand, one solid positive-Y
  servo-tab block, and two negative-Y contour arms. The tab block has two Ø6.8
  driver holes; the remaining upper arm retains its Ø6.5 case-screw access.
- The old full-width lower rail and its nine-hole grid are gone; the lower
  cartridge mounts through one screw in each lower reinforcement root.
- Both yaw-bearing protrusions are split into closed, single-body screw-on
  cartridges. The four printable pieces have flat build-plate faces; the lower
  cartridge also has 0.10 mm radial assembly clearance.
- Both the coxa/hip and femur/knee motor holders have a full-width Ø24 service
  slot and pass the horn-on servo extraction sweep.
- The tibia socket exposes all six bracket fasteners: four central captive
  nylocs through rounded radial windows and two outer pockets directly, while
  retaining a 21.5 mm complete tube collar at the mouth.
- The normal knee range −30°…+20° is clear.
- The longer premade bracket first meets the rigid top structure at −117.5°;
  the build uses a conservative −110° hip up-limit, the same safe limit as the
  custom-CNC overhead concept.
- The top and bottom 6805 bearing checks, plate seating, hatch removal path,
  and yaw-axis interfaces are inherited and re-run by the generator.
- The blind tube stop is 5.2 mm farther out than the CNC-C concept and 21.8 mm
  farther out than production, so the CF tube cut remains 21.8 mm shorter than
  production. The socket mouth now extends another 16 mm along that same tube;
  this adds support without changing the cut length or foot position.

## Regenerate and publish

From `hexapod_walker/prototype_sts3215`:

```sh
make buildviz-premade-chorn-56
```

This regenerates the geometry, runs the full femur/plate sweep and BuildViz
checks, publishes the local build on port 5183, and mirrors it to the cloud hub
without making a cloud/network failure invalidate the local result.

To regenerate only the four STEP hardware files:

```sh
uv run --no-project --python 3.12 --with build123d \
  python concepts/premade_chorn_56/build_premade_chorn_hardware_step.py
```
