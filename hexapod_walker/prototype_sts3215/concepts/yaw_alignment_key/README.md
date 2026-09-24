# Long-reach yaw alignment key

Fitted to the actual `coxa_6706_bottom_nuts` two-piece coxa meshes, including
their 4.5 OD × 3.2 ID × 10 mm compression spacers. The original assembly is
unchanged. This isolated build adds a removable hand-held alignment tool.

## Dimensions and stop

- Pin spacing: 14 mm; uses the holes at X ±7, Y 0.
- Bridge underside: Z 60.3, 5 mm above the upper part's maximum Z 55.3.
- Horn face: Z −9.0. Bridge-to-horn reach: **69.3 mm**.
- Maximum projection below bridge: **70.8 mm**, including the longer pilot.
- Upper stems: Ø4.6 mm, through the source's Ø7.2 mm access passages.
- Stop shoulders: Ø5.8 mm, bear on the existing seats at Z 1.1, outside the
  Ø4.7 mm sleeve pockets. They stop on the plastic seats, not on the horn threads.
- Spacer portions: Ø2.8 mm through Ø3.2 mm bores, 0.4 mm diametral clearance.
- Horn pilots: Ø2.2 mm, tapered, extend 1.5 / 1.0 mm past the nominal horn face.

The 0.3 mm transition to each pilot ends at the horn face. Sleeves and yaw
parts must be seated together when checking depth. Remove the two corresponding
horn screws and washers before inserting the tool; leave the centre fastener
as appropriate for your assembly. The modeled scene contains no horn screws.

## Print and use

Print only **`stl/yaw_alignment_key_PRINT.stl`**. It is oriented handle on bed,
pins up: PETG, 0.15–0.2 mm layers, solid fill. Inspect the slice, tip formation
and shoulder overhangs. The installed-orientation STL and gray/gold reference
parts are not the print deliverable. A STEP of the tool is included.

1. Check the printed shafts slide freely through a spare spacer. Check pilot
   fit/depth gently against a horn before putting it deep into the assembly.
2. Bring the yaw hub, spacers and horn together. Insert the two pins from above,
   locating the longer tip first. Gently clock the parts for the second tip.
3. Hold the key down until both shoulders meet their seats. Start the other
   two horn screws through the Y ±7 access holes with your free hand.
4. Seat those screws lightly, pull the key straight up, then install the other
   two screws and washers and finish tightening normally.

This tool controls alignment but does not latch the faces together. Do not
use it to lever the servo or force misaligned parts. These long printed stems
are a fit prototype; stiffness, durability and printed tolerances need testing.

## Verification

`checks.json` records watertight positive-volume mesh, interference checks
against both actual yaw printed parts, all four actual spacers, joining screws
and nuts; sampled axial withdrawal; free 6 mm driver envelopes at the other
pair; and positive shoulder contact after 0.2 mm overtravel.

The added horn is an explicitly schematic Ø20 disc with Ø2.5 thread envelopes
from the source CAD convention. Actual threads, servo and chassis are not
represented in this source assembly. Thus full robot access and physical fit
are not established by the checks. Existing original yaw geometry is untouched.

BuildViz: `prototype_sts3215/yaw-alignment-key`. The cyan key is shown installed
in the actual yaw assembly, with another copy beside it for inspection. Hide
the `coxa_leg_screw` and `coxa_hub_screw` types to inspect stems and sleeves.

Regenerate: `uv run --with build123d --with trimesh --with manifold3d python build.py`.
