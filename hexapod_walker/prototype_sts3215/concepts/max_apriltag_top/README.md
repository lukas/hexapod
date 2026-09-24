# Hexagonal hatch with integrated maximum-size AprilTag

Replacement for the removable rigid/CNC-overhead hexagonal hatch, based on the
captured September 11 CAD in `../apriltag_top_hatch/baseline/`. This is not the
older raised screen platform from `full_robot_viz`.

The tag36h11 ID 0 pattern is flush in the white hatch surface. The complete
square including its one-cell quiet zone is 98 mm; the detector's black-square
size is **78.4 mm / 0.0784 m**. The old servo-lid black square was 27.2 mm, so
tracking must use the new size when this part is installed. No live tracker
configuration has been changed.

The largest centered square with a 1 mm edge allowance is 98.0948 mm in the
source mesh (orientations searched across the hexagon's 30-degree symmetry
interval). The design rounds down to 98 mm, leaving at least 1.0648 mm outside
the quiet zone. The original six mounting holes, 4 mm sheet, outer outline,
and 1.5 mm locating lip are preserved. The central opening and eight old
accessory/electronics holes are filled. The hatch no longer supports those
through-hole accessories; the six perimeter screws still remove the hatch.

Print `hex_top_apriltag_0_98mm_H2D.3mf` in Bambu Studio, with the camera face
on the bed and lip upward. The black inlay is 0.6 mm deep; white and black PLA
are assigned in the H2D 0.4 mm project. A portable two-material 3MF and aligned
STLs are provided. Verify the selected materials match the loaded spools.

Verified: connected watertight white hatch, watertight black cell bodies,
material volume partition, six open mounting holes, unchanged outside envelope,
no added-material collisions in the inherited static assembly, tag ID decoding,
and successful H2D two-material slicing. Physical fit and moving overhead-leg
clearance have not been tested.

Regenerate from the repository root:
`uv run python hexapod_walker/prototype_sts3215/concepts/max_apriltag_top/make_variant.py`.
