# 7.5 mm horn spacer fit test

Each STL contains **one spacer**, 21 mm diameter and 7.5 mm thick, in millimeters.
This is +0.5 mm over the metal-clamp build's existing 7 mm spacer, exported
separately for a bench fit. No existing assembly/version or original STL changed.

- `driven_horn_spacer_7p5mm_fit_test.stl`: powered/splined horn side. Retains
  the Ø8.8 x 2.8 mm center-head recess and Ø4.2 through tool-access hole.
- `passive_horn_spacer_7p5mm_fit_test.stl`: opposite side; Ø8.6 center through hole.

Both retain the original four Ø3.4 holes on a 14 mm pitch circle. Only the outer
bracket-facing plane moves; holes and the driven recess are not scaled.
Print at 100% scale in the supplied flat orientation. The driven recess faces up.
Try one before a batch: the real seated horn span has not been measured here.
The spacer should fill the gap, not force the horns into the servo or pull the
bracket arms into position. Recheck screw engagement and tip/case clearance with
the thicker stack. A full-assembly motion or physical strength check is not claimed.

Regenerate with `uv run python` followed by this folder's `make_spacers.py` path.
`verification.json` records immutable v38 source hashes, watertight single bodies,
7.5 mm height, unchanged hole access/recess depth, retained original material,
and STL round-trip checks. The current 7 mm source CAD remains unchanged.
