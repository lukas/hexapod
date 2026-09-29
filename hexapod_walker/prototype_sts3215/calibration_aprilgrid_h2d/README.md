# H2D AprilGrid — 20 tags with dedicated wipe-tower clearance

Use `aprilgrid_400-419_H2D_tower_clearance.3mf`, opened as a NEW PROJECT so
Bambu Studio uses the saved H2D 0.4 mm printer, process and tower settings.
White and black PLA are separate materials/nozzles. The tower is enabled,
30 mm wide, with 2 mm brim, located at X=290, Y=20 mm. The board has no brim.

This supersedes `aprilgrid_400-419_H2D.3mf`: the full-width version relied on
turning the tower off, but the user observed an enabled tower conflicting
with the board at layer 8. The revised board trims only 20 mm of blank margin
from each side. Dimensions are 258 × 318 × 3 mm; placed at X=26..284,
Y=1..319 mm, with a dedicated tower lane to the right.

The tag geometry is unchanged: tag36h11 IDs 400–419, four columns × five rows,
IDs increasing left-to-right and top-to-bottom. Black squares 50.4 mm;
center pitch 63 mm; clear gap 12.6 mm; spacing ratio 0.25. The quiet border
is at least one 6.3 mm cell everywhere. New outside margins, measured from
black borders, are 9.3 mm left/right and 7.8 mm top/bottom.

`calibration_board_tower_clearance.json` and `calibration_board.json` contain
all centers, rotations and corner coordinates in meters. Origin is the board
face center, X right, Y up, Z out of the face. The corners are in OpenCV decoded
top-left, top-right, bottom-right, bottom-left order. Per-tag positions and
sizes remain identical to the full-width 20-tag board; only board_size_m changed.
No live tracker configuration was changed.

Print at 100% scale in matte white/black. Match actual spools to the material
presets. Measure the cooled board's black-square size and pitch, and ensure
flatness before calibration. Use a flat rigid backing if needed. Physical
print dimensions and flatness have not been verified.

Verification: all 20 IDs decoded, detected corners match manifest, watertight
material bodies, correct volume partition, and successful one-board H2D slice
WITH a generated prime tower and no slicer warnings. See verification.json.

Regenerate from repository root:
`uv run python hexapod_walker/prototype_sts3215/calibration_aprilgrid_h2d/make_board.py`.

## Quality PLA project

Use `aprilgrid_400-419_H2D_quality_PLA.3mf`, opening it as a new project.
Assumes two 0.4 mm H2D nozzles, white and black PLA, and a textured PEI plate.
The generic PLA flow and nozzle temperature defaults are retained; actual spool calibration is still material-specific.
Process: 0.20 mm layers, 3 walls, 5 top and bottom layers, 25% gyroid,
25 mm/s first-layer walls / 40 mm/s first-layer infill, 60 mm/s outer walls,
40 mm/s monotonic top surfaces, auxiliary fan off, 60 C textured bed.
Prime tower enabled in the reserved lane; no support, board brim, or ironing.
The 0.6 mm black inlay remains three layers deep; model geometry and tag coordinates are unchanged.
Verified with installed Bambu Studio CLI: no slice warnings, approx 9h37m and 234 g.
Regenerate with `uv run python tune_print.py` after `make_board.py`.
Use a clean plate and let the board cool before removal. Check flatness and actual tag pitch before calibration.

## Bambu Studio verified project (supersedes previous files)

`aprilgrid_400-419_H2D_Studio_ready.3mf` was opened, configured, sliced, and saved in the GUI. Bambu reported "Slice ok" without purge or path-conflict warnings, 10h2m / 233.54g. Tower width 15mm, ribs off, 2mm brim, positioned separately to the right. White uses left nozzle; black uses right. Repaired dual-extruder purge table (8 entries). Printer nozzle/AMS information synced; arc fitting disabled automatically for curve planning. No print started. Earlier CLI-only validation missed the GUI tower positioning and purge table issues. Use this project as the current deliverable.
