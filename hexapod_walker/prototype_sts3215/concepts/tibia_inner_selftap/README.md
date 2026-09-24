# v38 — four inner tibia self-tappers

User requested replacing inaccessible inner tibia receiver nuts. Their initial
insert request was superseded explicitly by **self-tapping screws**. This
revision uses neither nuts nor inserts at the four inner sites. The two outer
M3/nyloc connections are unchanged.

The viewed `hexapod-metal-knee-foot` selection was pinned to v5. Its socket
mesh is identical to v37, so v37 is the immutable full-robot parent, retaining
the latest knee cap/femur improvements. No robot control, firmware, joint,
servo, tube-length, or foot-placement parameters change.

## Hardware and printing

- Four **3 × 8 mm self-tapping screws for plastic**, through the existing metal
  C-bracket web into the printed socket; the screws do not tap the aluminum.
- Four Ø2.5 × 7 mm blind pilot holes, in the same 14 mm bolt-circle pattern.
- With the 2.1 mm metal web, nominal plastic entry is 5.9 mm, including a
  modeled 1 mm pointed tip: 4.9 mm full-diameter engagement and 1.1 mm tip
  clearance. The reference screw head is Ø5.5 × 3 mm.
- Keep the two outer M3 machine screws and nyloc nuts. Their hole/nut-pocket
  dimensions and locations remain exact; their screw lengths still require
  the original measured stack.
- Four obsolete inner nut pockets and radial access windows are filled,
  restoring a continuous tube-support collar. Tube bore, center stop, outside
  envelope and 30 mm insertion depth remain unchanged.

Attach the socket to the detached C-bracket before mounting that bracket on
the knee servo, so the four inner screw heads have straight screwdriver access.
Test one print with the actual screw before a batch: Ø2.5 mm is an initial
pilot for this modeled thread envelope, not a universal fit specification.
Do not overtighten; repeatedly removing self-tappers wears printed threads.
Pullout strength, torque and fatigue are **not physically validated**.

Only the tibia socket requires reprinting. The STL in `output/print/` has its
broad metal-mating face placed flat on the print bed. Hardware reference models
are not printable parts.

## Reproduction and checks

```sh
uv run python hexapod_walker/prototype_sts3215/concepts/tibia_inner_selftap/make_variant.py
```

Every input mesh is SHA-verified. Checks assert preservation of all original
material, outer nut geometry, center stop, tube bore, all other mesh assets,
all pre-existing instance transforms, and all joint properties. They test four
continuous receiving walls/blind floors, actual six tube meshes, screw/head
clearance, detached screwdriver access, sampled hip/knee motion and additional
60 yaw/hip/knee chassis-clearance combinations. No adjacent-leg swept-motion
or full structural-load certification is claimed.

`publish.py` only creates a new version on the existing full-robot build,
locally and in the cloud. It has no overwrite/prune/default-promotion option.
Do not mistake inherited full-assembly check failures for validation of the
entire robot; exact local and server results are saved alongside the design.

## Published result

v38 is published on both hubs; old versions are unchanged and v6 remains the
full-build default. The existing `Knee, tibia and foot` catalog selection now
points to v38, with a separate one-leg connection close-up underneath it.
All 24 new fastening checks pass at 4.90 mm continuous engagement. No unexpected
collisions with fasteners included. Socket: one closed solid, no open or
nonmanifold edges, degenerate triangles, or self-intersections. Minimum thickness
estimate 0.25 mm is the retained thin center-stop region, not a new screw wall.

Global `passed=false` retains the source's unrelated coxa self-intersections,
hip-cap open edges and 12 floating articulated groups. It is not a certification
of the complete robot or the physical fastener fit.

[Focused v38 connection](https://buildviz.cwd1f0-new-cluster.coreweave.app/?catalog=hexapod-metal-v38-tibia-inner-selftap&build=prototype_sts3215%2Fpremade-chorn-56&branch=main&version=v38)
