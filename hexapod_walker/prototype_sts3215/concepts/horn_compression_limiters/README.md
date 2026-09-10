# Horn compression-limiter experiment

This is a print-and-bench-test sidecar for the smooth, springy looseness seen
at the robot's horn joints. It does **not** change the production print set.

The variant widens only the four perimeter M3 horn-screw passages in:

- `femur_link`: both hip-yoke arms;
- `tibia_knee_yoke`: both knee-yoke arms;
- `coxa_link`: the four long yaw horn-bolt columns.

The redesign uses the user's existing standard M3 spacers, fixed at **10.00 mm
long**, currently **Ø4.5 mm OD × Ø3.2 mm ID**. There is one sleeve around each
perimeter horn screw; no sleeves are cut or stacked. The screw head/washer
bears on one sleeve end and the aluminum disc horn bears on the other. Plastic
still locates and surrounds the tube, but it no longer has to preserve screw
preload indefinitely.

## Changing to a different spacer diameter

Edit only `spacer_config.toml`. The important current settings are:

```toml
[spacer]
enabled = true
outside_diameter_mm = 4.50

[printed_fit]
bore_diametral_allowance_mm = 0.20
```

Set `enabled = false` for the normal no-spacer version. In that mode the
generator uses the original production M3 passages and omits the enlarged
bores, local spacer bosses, metal-spacer models, and fit coupon. The saved
dimensions are ignored until the switch is turned back on.

The printed CAD bore is spacer OD plus diametral allowance. The user's
printed coupon put Ø4.60 mm slightly too tight and Ø4.80 mm slightly too
loose, so the new selected bore is their Ø4.70 mm midpoint: 0.20 mm total
printer compensation, nominally 0.10 mm per side. The midpoint itself has
not yet been physically verified.

The refined horizontal coupon spans Ø4.65–4.85 mm in 0.05 mm increments.
Its second hole is the selected Ø4.70 mm bore. It reproduces the real
10.1 mm tunnel depth and horizontal print orientation. Choose a light
push/slip fit after string cleanup; do not hammer or force the spacer in.

The standard horn's raised center spline boss is on the servo-facing side, not
between the printed link and horn. On the printed-link side, the four sleeves
fit the standard Ø14 mm bolt pattern and remain 0.75 mm inside the nominal
Ø20 mm disc edge. The yaw variant grows only its printed horn-facing neck from
Ø20 to Ø22 mm to restore wall around the wider bores; it still has 1 mm radial
clearance through the production Ø24 mm chassis opening.

## Why the sleeve is slightly shorter, including the outer lip

The 10.1 mm dimension includes the outer head-bearing lip. A 10.0 mm
compression limiter should be slightly shorter than this free plastic stack:
the washer first clamps the plastic, then seats against the sleeve. Making
the sleeve protrude could leave the plastic loose even with a tight screw.
This follows [SPIROL’s compression-limiter length guidance](https://www.spirol.com/product/compression-limiters/).
The nominal 0.1 mm difference still needs a printed-part fit check: confirm
the washer reaches the sleeve without damaging the plastic.

## How the fixed 10 mm length is accommodated

- **Hip and knee yokes:** the current assembled head-to-horn stack is 9 mm.
  Each of the four screw sites gets a local 1.1 mm-tall, Ø8 mm head-bearing
  boss. This leaves a 10.1 mm free plastic stack around the fixed 10 mm sleeve:
  the first 0.1 mm of tightening lightly compresses the print, then the sleeve
  becomes the hard metal stop. The rest of each arm stays its current
  thickness, minimizing sweep-envelope changes.
- **Yaw:** only the four perimeter bolt seats move down. Their new free
  head-to-horn distance is also 10.1 mm. Each existing screwdriver shaft is
  continued down to the new seat, so the normal hex driver still reaches it.
  The center spline screw is unchanged and does not receive a sleeve.

The perimeter hardware becomes **M3×12 SHCS + a 7 mm OD × approximately
0.5 mm standard M3 washer**. The washer must be wider than the Ø4.7 mm printed
bore so it overlaps the plastic as well as the sleeve. With a 10 mm sleeve this
gives about 1.5 mm engagement in the 2 mm aluminum horn and keeps the screw tip
about 0.5 mm short of the servo-side horn face. M3×10 cannot be reused: it
would have zero thread engagement through a 10 mm sleeve. The yaw access
shafts are widened to Ø7.2 mm for the washer.

The replacement fit coupon has five horizontal bores. A notch marks the small
end; read them from that end toward the other end:

- Ø4.65 mm;
- Ø4.70 mm (selected part bore);
- Ø4.75 mm;
- Ø4.80 mm;
- Ø4.85 mm.

The previous coupon's first and second holes were Ø4.60 and Ø4.80 mm;
these are different from the refined coupon above. Use the refined coupon
to confirm the midpoint before committing to a complete part.

## Servo service opening

The regenerated `femur_link_compression_limiter_test.stl` and
`tibia_knee_yoke_compression_limiter_test.stl` inherit the current serviceable
servo holder from `hexapod_prototype.py`. Its former rounded bridge over the
Ø20 disc horn is removed: the Ø24 horn opening continues as a straight slot
to the open clamp face. After the two clamp-cap bolts are removed, the servo,
fitted horn, and clamp cap can lift out together. This applies to both the hip
femur yoke and the knee yoke; the three surviving front-case capture sites are
retained around the slot.

## One-joint validation

1. Print the fit coupon and choose the bore for the actual tube stock.
2. Print **one** tibia yoke first; it is the cheapest complete test part.
3. Deburr eight existing 10.00 mm sleeves and confirm an M3 screw passes
   freely through every sleeve. Do not shorten them. Test all four sleeves on
   the actual horn bolt pattern before installing screws.
4. Assemble one driven and one passive horn using M3×12 screws and the thin
   washers. Confirm at least 1.3 mm and no more than 1.8 mm of actual screw
   projection beyond the sleeve/washer stack before installing against a horn.
   Verify by hand that the printed pad contacts the horn face before final
   torque and that no tube holds the pad visibly off the horn.
5. Use very modest torque because the horn has only about 2 mm of aluminum
   thread. Add a tiny amount of removable blue threadlocker to the metal
   threads only, and add witness marks across each screw head and the print.
6. Hand-rock the joint, then repeat after several heat/load cycles. A witness
   mark that stays aligned while play returns points away from screw rotation
   and toward horn spline, servo gearbox, or bearing/pocket motion.
7. Only after the yoke result is good, print one yaw coxa variant. Use one
   unchanged 10 mm sleeve, one **7 mm OD washer**, and one M3×12 screw
   at each of its four perimeter stations. Dry-assemble and recheck screw-tip
   projection so no tolerance stack can bottom a screw against the servo case
   below the thin horn.

Do not resume gait testing until the repaired test leg passes the hand-rock
check. This experiment addresses plastic clamp creep; it does not repair a
stripped horn thread, worn spline, gearbox backlash, or loose bearing fit.

## Regenerate and inspect

From the repository root:

```bash
make -C hexapod_walker/prototype_sts3215 buildviz-horn-compression-limiters
```

The generated printable candidates are under `stl/`, and the BuildViz scene
is published as `prototype_sts3215/horn-compression-limiters`. The target also
runs `verify_workspace_variant.py`, which substitutes the three experimental
parts into the production collision checker and gates a 76-pose coarse
yaw/hip/knee workspace sweep.

## Femur clamp-cap hex nuts

The two M3 clamp-cap screws at the knee-servo end of the femur now use
standard M3 hex nuts (nominal 5.5 mm across flats × 2.4 mm thick), replacing
self-tapping into the printed cradle. Press the nuts outward from inside the empty servo cavity into the two
short end-wall openings before fitting the servo. Push each nut to the closed hex end;
its threaded hole then lines up with the clamp-cap screw.

The pockets are 5.45 mm across flats and 2.50 mm deep. This is a nominal
0.05 mm interference fit across flats; actual printed fit needs checking.
A 2.0 mm solid shoulder between nut and cap carries the screw tension.
Use M3×8 machine screws with the existing recessed cap (2 mm under-head
plastic + 2 mm shoulder + 2.4 mm nut leaves approximately 1.6 mm projection).
The cap screw passages are now Ø3.4 mm clearance. The other servo-case
fasteners and the coxa's self-tappers are unchanged.
