# Two-pin horn alignment key — v1 fit prototype

Two stepped, tapered plastic pins on a side handle temporarily register two
opposite C-clamp holes to the servo horn. The other two holes remain accessible
for screws and a nominal 6 mm driver. This is a hand-held alignment tool: it
prevents lateral/rotational drift while inserted but does **not** latch the
faces together. Support the parts and keep gentle axial pressure on the handle.

## Choose the correct depth

Measure from the accessible outer clamp face to the horn's threaded-hole mouth,
including every intervening spacer. Use the matching file, not the longest one.

| STL | Face-to-horn stack | Source / assumption |
| --- | ---: | --- |
| `key_premade_spacer_9p1.stl` | 9.1 mm | 2.1 mm premade plate + 7 mm spacer |
| `key_cnc_drive_7p0.stl` | 7.0 mm | 3 mm CNC blade + 4 mm driven boss |
| `key_cnc_passive_7p5.stl` | 7.5 mm | 3 mm CNC blade + 4.5 mm passive boss |
| `key_bare_plate_2p1.stl` | 2.1 mm | Bare plate only, with no spacer |

Dimensions come from existing source models, not a measurement of the user's
current assembly. The premade/spacer version is the illustrated example only.
If the measured stack differs, change `STACKS` in the generator and regenerate.

## Geometry and fit

- Two pin axes 14 mm apart, matching opposite holes on the source horn pattern.
- 3.1 mm locating shanks for nominal 3.4 mm bracket clearance holes. Verify the
  actual holes; a 3.0 mm bracket hole will NOT accept this version.
- Each shank steps down to 2.2 mm at the horn mouth. This small smooth pilot must
  clear the actual internal thread, not screw into or wedge against it.
- One pilot enters 1.5 mm; the other enters 1.0 mm. Their 0.6 mm tapered tips
  reduce simultaneous hunting: locate the long tip, then rotate gently to find
  the second. Large shanks align the bracket; small tips locate the horn.
- Handle underside/shoulders stop further insertion against the clamp face.
  This depth stop works only with the correctly matched stack thickness.
- Central relief: 6.5 mm wide, 3 mm deep for a protruding center fastener.
  Confirm actual head size and access before use.
- Fit remains approximate due to clearances. Pins are not thread gauges.

## Print and use

Print the selected `key_*.stl` flat handle down, pins up, in PETG, 0.15–0.2 mm
layers, solid fill, no supports. STEP files are supplied. Pin tips are delicate;
inspect them for oversized seams or damage and replace if bent or cracked.

1. Check each pin against its intended clearance/threaded hole separately by
   hand; it must enter and withdraw without force. Confirm a clear depth of at
   least 1.5 mm at the horn and no contact with internal hardware.
2. Bring clamp and horn faces together, roughly clocked.
3. Insert the longer pin through the clamp, find the horn hole, then align the
   shorter pin. Seat the stop against the face with light hand pressure.
4. Hold the key and parts together while starting the remaining two screws.
   Seat them lightly enough to retain alignment; do not torque with the key in.
5. Pull the key straight out along the pin axes. Install the remaining screws,
   then finish tightening normally.

Do not hammer, twist forcibly, or use the tool to lever a servo shaft. Plastic
pilot retention and durability, printed tolerances, real threads and full
robot access have not been physically tested. This design does not provide
hands-free clamping; use an accessible soft-jaw clamp if axial retention is needed.

## Verification and viewer

The generator checks single valid solids, positive watertight STL volumes,
nominal mating clearance, two free driver paths and sampled axial withdrawal.
The assumed 2.4 mm thread clearance envelope is schematic, not a measured
thread specification. Gray and gold reference meshes simplify the interface;
they are NOT printable robot parts and do not validate whole-assembly access.

BuildViz: `prototype_sts3215/horn-alignment-key`. Left: tool. Middle: exploded
interface. Right: engaged. The scene shows the 9.1 mm example with pins pointing
up for visibility; turn the actual tool to match the accessible bracket face.

Regenerate: `uv run --with build123d --with trimesh python build.py`.
