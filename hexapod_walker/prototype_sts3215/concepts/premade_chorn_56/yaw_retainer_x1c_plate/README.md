# Six yaw retainers — Bambu X1C

Open `yaw_retainers_6x_X1C_PETG.3mf` in Bambu Studio as a project. It contains
six separately selectable copies on one plate, with local slicing results.
No printer connection or print command is involved in generating this file.

The geometry is the unchanged yaw-servo retainer from metal-clamp build
`prototype_sts3215/premade-chorn-56`, branch `main`, version `v38`.
Source SHA-256:
`8106497cf755929ebab489b1b264ceb62d155095871f86ca06026817d7001476`.

- X1 Carbon, standard 0.4 mm nozzle, Generic PETG, textured PEI plate.
- 0.20 mm layers, six walls, 40% gyroid, six top/bottom layers.
- Flange-down orientation, 3 × 2 layout, 12 mm between model bounding boxes.
- Automatic snug supports for overhangs; no brim or prime tower.
- Print all objects by layer. Remove supports before assembly.

Check the printer, nozzle, bed and filament settings before printing. This is
a print layout, not a new CAD revision or a physical fit qualification.
`verification.json` records mesh identity, placement, source hash, slicer
results and support clearance through the 48 fastener bores.
`plate_preview.png` is rendered by Bambu Studio from the final project.

Regenerate locally with:

```sh
uv run python hexapod_walker/prototype_sts3215/concepts/premade_chorn_56/yaw_retainer_x1c_plate/make_plate.py
```

The generator reuses profile loading and native mesh verification from the
adjacent `knee_cap_heatset_front_selftap/x1c_plate` implementation. It does not
modify the original geometry, previous plates, or BuildViz versions.
