# Knee-yoke AprilTag snap flag

This is a removable, non-structural camera target for measuring STS3215 knee
backlash and tibia-yoke compliance. It presses over the four exposed M3
socket-head screws on the **driven/front face** of the production tibia knee
yoke. It does not change screw length, sit in the yoke-to-horn clamp stack, or
require disassembling the joint.

The default build carries sample `tag36h11` ID 16 on a 38 x 38 mm face. The
actual tag, including its white quiet zone, is 34 x 34 mm—the same verified
size as the existing motor-lid tags. The human-readable ID is a raised **black
material part** on the rear/cup side; it is not merely raised white geometry,
and nothing intrudes into the camera-facing quiet zone.

## Print and install

Use `out/tag36h11_16_knee_yoke_snap_flag_BambuStudio.3mf` for the ready-to-print
black/white project. The portable 3MF and aligned black/white STL pair are
also in `out/`. For a single-colour holder plus a paper tag, print the plain
STL and adhere the supplied 34 mm SVG.

For the full inclusive ID 16–32 set (17 holders), use
`out/tag36h11_16-32_knee_yoke_snap_flags_BambuStudio.3mf`. It is arranged as
one two-colour print plate, with every human-readable ID printed black on the
rear.

The next inclusive set, IDs 33–64 (32 holders), is in
`out/tag36h11_33-64_knee_yoke_snap_flags_BambuStudio.3mf`. Its denser 6-column
layout remains within the 256 x 256 mm A1 build area.

- Material: PETG recommended for the four split grip cups; PLA may work but is
  more likely to crack if the fit is tight.
- Orientation: tag face directly on the build plate, cups upward.
- Supports: none.
- Default fit: nominal ISO M3 SHCS head, diameter 5.5 mm and height 3.0 mm.
- Installation: align all four cups with the screw heads and press evenly. Do
  not hammer it and do not use it to tighten the screws.

The cups intentionally grip only the cylindrical screw heads. If the real
heads differ, measure one with calipers and regenerate instead of forcing the
part:

```sh
uv run python knee_yoke_apriltag_flag/make_knee_yoke_apriltag_flag.py \
  --head-diameter 5.6 --head-height 3.0
```

Increase `--throat-clearance` if the print is too tight; reduce it if loose.
The revised default is `-0.10` mm diametral clearance: a 5.40 mm throat for a
nominal 5.50 mm screw head, 0.10 mm tighter than the previous design. A 5.75 mm
cavity behind the mouth and a relief slot in every cup provide the snap.

## Regenerate and verify

From `hexapod_walker/prototype_sts3215`:

```sh
uv run python knee_yoke_apriltag_flag/make_knee_yoke_apriltag_flag.py
uv run python knee_yoke_apriltag_flag/make_knee_yoke_apriltag_flag.py --tray 16-32
uv run python knee_yoke_apriltag_flag/make_knee_yoke_apriltag_flag.py --tray 33-64
uv run python knee_yoke_apriltag_flag/check_fit.py
```

The checker imports the production yoke and fixed knee bracket, confirms the
14 mm horn bolt circle, and sweeps the accessory from -25 to +85 degrees. A
physical unpowered hand sweep remains required after installation because the
model cannot know print warping, actual screw-head dimensions, or cable
placement.

## September 21 fit revision

The square sits 2 mm farther outward from the servo on solid cup pedestals.
The four screw centers, 3 mm head engagement, and split grip length stay unchanged.
Total height is 6.85 mm. This adds modeled clearance for the wire; actual cable
routing and printed grip still need a physical fit check.

`build_assembly.py` generates `assembly/scene.json` with all 37 recorded robot
tags (24 yoke flags, 12 servo lids, and chassis ID 0). Translations are CAD-derived,
not measured tracking calibration. Run it from the repository using `uv run python
hexapod_walker/prototype_sts3215/knee_yoke_apriltag_flag/build_assembly.py`.

The revised 24-flag set matching this assembly is in
`assembly/all_24_snap_flags_BambuStudio.3mf` (portable: `all_24_snap_flags.3mf`).
Previously generated range trays in `out/` retain their previous geometry until
regenerated with the commands above. The chassis tag uses the servo-lid cover geometry, centered over the screen
as reported by the user. ID 0 is retained from the saved layout; mounting
height is CAD-derived.

## Large rear numbers, IDs 66–97

`out/tray_66-97_large_numbers/tag36h11_66-97_knee_yoke_snap_flags_BambuStudio.3mf`
contains 32 revised flags on one 248 × 248 mm plate layout. The black rear
digits are 4.64 mm tall (twice the previous 2.32 mm), still raised 0.5 mm.
Cup throats remain 5.40 mm with the 2 mm outward plate offset.
Previously exported files are unchanged; regenerate to use the larger numbers.
