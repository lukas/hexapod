# Archived builds (frozen 2026-08-29)

Earlier walker generations, moved here to keep `hexapod_walker/` down to
the live projects (`prototype_sts3215`, `prototype_ak40`). Nothing in
here is developed anymore; everything still runs from its new location
(cross-references between these builds are sibling-relative and moved
together).

| Directory | What it was |
|---|---|
| `fullsize_v1/` | The original human-carrying walker design (18 harmonic-drive servos, ~4 m foot-to-foot). Parametric STL generator, MuJoCo sim, RL gait training, Blender renders. `prototype_v1` and `sts` wrap its env/training code, and `prototype_sts3215/scripts/render_prototype.sh` still uses its Blender renderer. |
| `prototype_v1/` | First tabletop prototype for hobby servos (DS3225 / MG996R class) and FDM printing. |
| `sts/` | First walking stack for the STS3215 robot — superseded by `prototype_sts3215/rl_move/`. |
| `rideable_v1/`, `rideable_v2/` | Design studies for an affordable rideable walker. |
| `hex` | One-shot command CLI for the pre-web-UI firmware Monitor bridge (socat to :7500, hardcoded LAN IP). Superseded by `http://hexapod.local:8080` + `linux_control/`. |
