# X1C plate — one metal-clamp femur and matching cap

Open **metal_femur_and_cap_v38_X1C_PETG.3mf** as a project in Bambu Studio,
not as geometry only. It contains exactly one femur and one cap from immutable
`prototype_sts3215/premade-chorn-56`, main, v38. These two meshes are unchanged
from v37. This is a print-layout/preset change, not a new CAD revision.

Assumptions: X1 Carbon, standard 0.4 mm nozzle, Generic PETG, textured PEI plate.
Confirm the actual nozzle, plate and loaded spool before printing. No printer
was contacted and no print was started. The project is editable and includes
the locally verified slice; re-slice after changing material or printer settings.

## Layout and process

- Femur: broad closed back on the bed; servo cavity and heat-set bores upward.
  This reverses the earlier femur STL's print pose without changing its shape.
- Cap: broad outer face down. Both parts rest on Z=0, separated by 12 mm;
  neither touches the X1C bed exclusion or calibration region.
- 0.20 mm layers, 6 walls, 6 top/bottom layers, 40% gyroid, one PETG filament.
- Selective snug support on the femur; no support on the cap. Six nonprinting
  support blockers keep the horizontal self-tapping pilot bores clear. Remove
  supports under larger overhangs, including the accessible center passage.
- No brim or prime tower. Auxiliary fan off. Installed Generic PETG thermal
  defaults retained. Arc fitting disabled so support toolpaths can be checked
  directly as linear segments.
- Bambu Studio 02.08.02.61 estimate: **3 h 4 min, 56.9 g**. Actual time and
  filament use can differ. No physical print/strength test is claimed.

## Matching hardware

The cap uses two M3x8 machine screws and two M3x5.7 heat-set inserts in the
femur. The six front screws pass through the metal C web and self-tap into
the printed femur: 3x8 screws, not inserts or nuts at that interface.
Confirm actual insert OD and dry-fit screw/pilot sizes; see the parent README.

## Verification and reproduction

`verification.json` records source STL SHA256s, rigid placement transforms,
bed contact, positive-volume/watertight source and exported meshes, exact
part quantities, X1C settings, and successful one-plate slicing without
slice warnings. All ten functional bores are checked against support extrusion
envelopes: two insert bores, six self-tapping pilots, two cap screw passages.
`slice_result.json` is the slicer's report; `plate_preview.png` is its rendered
model preview. CLI logs may include informational warnings about missing
optional `machine_full`/`process_full` files; all resolved profiles are embedded.

The standard `metal_femur_and_cap_v38_geometry.3mf` is an unsliced fallback
with the same two oriented parts but no X1C/support configuration. Prefer the
X1C PETG project above. Support blockers are modifiers, not printed parts;
generic 3MF readers do not necessarily understand Bambu modifier semantics.

Regenerate from the repository root (requires installed Bambu Studio on macOS):

```sh
uv run python hexapod_walker/prototype_sts3215/concepts/knee_cap_heatset_front_selftap/x1c_plate/make_plate.py
```

`--material PLA` is available for a separately named project if needed. PETG
is the default because it matches the metal-clamp design's material notes.
Source geometry is obtained from the local BuildViz asset cache, or from its
content-addressed cloud URL if absent; its SHA256 is checked before use.
