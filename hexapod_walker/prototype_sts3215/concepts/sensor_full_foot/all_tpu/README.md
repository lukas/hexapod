# Two-part all-TPU ground-contact foot

Designed for the user's confirmed TPU 95A. Reworks v9 (which used PETG structural parts) into two TPU prints: a rounded continuous sensor cup, and a socket with an integral pressure pad, bowed return membrane and lower retaining cuff. No screws, metal spring, separate plunger or depth-positioned insert. The purchased sensor and 8/6 mm carbon tube remain.

The main design choice is to use thick sections for support and a thin modeled wall for return. Removing the pin guides avoids sliding TPU-on-TPU interfaces. The surrounding membrane provides alignment and return; its stiffness and lateral behavior are unmeasured. A broad cuff engages the cup groove instead of small cantilever hooks. One cuff attachment is eliminated by fusing the upper membrane into the socket.

## Dimensions and load path

19 mm rounded foot, 22.8 mm maximum collar diameter, 8.2 mm rod bore, 17.2 mm socket depth. Rod end seats on a shoulder; a conical cavity beneath it reduces the closed-bore printing bridge. The sensor is 10 mm across with an assumed 6.5 mm wide tab. Assumed sensor plus adhesive thickness is 0.2 mm.

The 6.5 mm pressure pad begins 0.2 mm above the sensor. Compression closes that gap, then compresses the pad. The outer rim meets the cup after nominally 0.6 mm of travel. Because every printed component is TPU, this is bumper contact, NOT a rigid hard stop or a validated force limit. Further deformation under load is expected. The collar also carries load in parallel with the sensor. This is intended for contact detection, not weight measurement.

## Print and assemble

all_tpu_parts.3mf contains both separate parts in mm with 10 mm spacing. Cup sensor face down; socket top rim down. Inspect the socket's internal annular seating ledge and return-wall overhangs in the slicer. Do not claim this is support-free without slicing. Use the actual filament manufacturer's profile. Dense fill in the cup, socket and pressure pad is intended; return compliance comes from the modeled thin wall, not low infill. Keep supports and strings out of the cuff and sensor cavity.

1. Dry-fit the rod to the internal shoulder. Confirm retention and a material-compatible adhesive on a sample before bonding the external rod socket; TPU-to-carbon adhesive behavior is untested.
2. Stick the sensor flat to the cup without covering the active surface or vent. Measure actual combined sensor/adhesive thickness; the 0.2 mm gap is only nominal.
3. Align the wire opening. Place the upper assembly over the sensor and stretch its lower cuff over the cup rim into the groove. Check engagement around the circumference. Do not glue this flexible joint.
4. Verify raw sensor baseline, gentle straight and angled contact, release after both short touches and sustained compression, cuff pull-off resistance, and overload behavior. No robot motion is authorized by generating this design.

If the collar does not return fully or develops unacceptable creep/hysteresis, revise its geometry or add a separate metal return spring. A metal spring is omitted for this prototype, not proven unnecessary. These parts replace the complete v14 printed assembly; v14 internals are not used.

## Verification

`uv run --no-project --with trimesh --with manifold3d python make_all_tpu.py`

All four scene meshes are watertight positive-volume connected solids. Unloaded clearance, seven body stroke positions, tube seating, wire clearance, cuff geometric capture and print-transform checks pass. The membrane and pressure pad are displayed unloaded; they are not rigidly translated for collision checks during compression. No nonlinear TPU deformation, trigger force, return rate, retention strength, fatigue, creep or printing validation has been performed.

Material background: https://help.prusa3d.com/article/prusament-tpu-95a-material-guide_899653
