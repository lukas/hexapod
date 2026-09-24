# v36 — longer servo box, ordinary middle cap screws

User-requested simplification of v35. Published as a new immutable revision
on `prototype_sts3215/premade-chorn-56` to both hubs; old versions unchanged.
The default remains v6. This is a CAD/print-fit prototype, not hardware release.

- Extend the receiver end of the knee servo box by 6 mm.
- Restore the ordinary symmetric cap and screw centers at cap-local
  X ±27.2, Z 17.15 mm: two mid-height screws, no projecting lug.
- Use two 3 mm-diameter x 8 mm self-tapping screws into plastic per knee.
  No knee-cap nuts or loading slots. Ø2.5 x 8 mm pilots are a starting
  printer/screw fit, not a universal pilot recommendation.
- Keep heads within Ø6 x 3 mm recesses. Model envelope: Ø5.5 x 3 mm head,
  1 mm pointed end. Nominal entry into plastic is 6 mm; full-diameter
  engagement excluding the point is 5 mm, with 2 mm blind-tip clearance.
- Hip-to-knee length changes 90→96 mm. All 48 knee/downstream instances
  and all six knee pivot origins move together. Hip frames remain fixed.
  Physical robot firmware, controller/IK parameters and simulation sources
  were NOT modified; account for this link-length change before hardware use.
- Six hip-C front insert pockets remain Ø4.6 x 3.1 mm. Their mating face
  and pattern are unchanged; they still do not accept 5.7 mm inserts.

## Reproduce

From the repository root:

```sh
uv run python hexapod_walker/prototype_sts3215/concepts/knee_cap_simple_selftap/make_variant.py
```

The generator reads the frozen v35 scene and the SHA-verified v34 pre-lug
core meshes through the preceding revision's helper. It does not rewrite
any predecessor. Only two printed mesh types change; twelve screws replace
the prior 12 bolts and 12 nuts. `publish.py` accepts a new version number
and `BUILDVIZ_API_KEY`; it has no force, pruning or default-promotion flag.

## Print / assembly

`output/print/` contains a matched cap and box pair, already oriented on
their broad flat faces. Print one pair first using the inherited PETG
material designation. Fit the servo, seat its cap, and tighten the two
self-tapping screws from the cap face. No nut insertion step. Verify the
actual screw's thread form and head dimensions; do not overtighten. Repeated
disassembly wears plastic threads. Pullout/fatigue and tightening torque
have not been physically tested.

## Evidence

`output/checks.json`: cap/box/servo/hip-C hard intersections zero;
intentional servo-clamp press retained; 12/12 Ø5.5 x 50 mm screwdriver
paths clear; cap withdrawal and horn-on extraction clear. Hip -110..+30
and knee -30..+20 sampled every 2.5 degrees; chassis tested at five yaw
stations from -35 to +35. Unchanged adjacent-leg motion not revalidated.

`output/v36-server-verification.json`: all 12 new fastening checks pass
with 5.00 mm continuous receiving material. Cap and box are single closed
solids with no open/nonmanifold edges or self-intersections. Zero unexpected
collisions (+18 declared). The full-build result is still false because
of inherited connectivity/printability annotations: 13 components and 12
floating articulated groups remain, now containing 84 instances including
the twelve modeled screws. Thin-feature estimates: box 0.253 mm and cap
1.582 mm. The matching parts still need physical print-fit validation.

[Focused v36 view](https://buildviz.cwd1f0-new-cluster.coreweave.app/?catalog=hexapod-metal-v36-simple-knee&build=prototype_sts3215%2Fpremade-chorn-56&branch=main&version=v36)
