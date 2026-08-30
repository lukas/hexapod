# cw-walkcurr-pf-terrain0-central-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-30T00:30:49+00:00

**pod**: hexapod-mjx-train-1

**steps**: 20000000

**wandb_id**: 7qlwv8y8

**hypothesis**: Plain English: is the mesh-family model itself (not terrain) responsible if a primitive-family arm behaves differently from cw-walkcurr-pf-central-sv-s0? This is the FLAT-GROUND CONTROL for the terrain-diversity fallback: identical SV diet/budget/seed/centralized-128,64,32-tanh-MLP architecture to central-sv-s0 (which stayed pinned in the static-crouch basin at 20M, FAIL), only env.model_source switched mesh->primitive (needed so its terrain-treatment sibling cw-walkcurr-pf-terrain1-central-s0 can use the hfield -- the checked-in mesh_mjx twin ships a flat plane only, servo_model.py's own guard) with terrain_amp explicitly held at 0.0 (flat). If this ALSO stays pinned in the static basin like the mesh baseline, model family/mass is not a confound and any escape in the terrain sibling is credited to terrain diversity; if IT escapes instead, the mesh-vs-primitive mass/kinematics difference is the real lever, not terrain, and the terrain sibling's read must control for that.

**gate**: Rung-1 gate at 20M vs cw-walkcurr-pf-central-sv-s0 (its own C-env det fixed-forward panel result): zero tilt terminations, cmd_prog_frac>=0.35, direction_err_deg<=30, slip/m<=3.0, gait_valid>=4/6, real stepping on video = escape (matches or beats central-sv-s0's FAIL floor -- if this control also escapes, credit model family, not terrain, in the sibling's read). Discovery litmus corrected per the decleg-sv dig-in finding (raw freeprog escape is an unreliable, episode-shortening-correlated signal): require env/walk_speed clearly off its ~0.02 m/s static floor AND stable-or-rising rollout/ep_len_mean, not freeprog alone. Pinned static basin + flat/falling reward at 20M = aligned FAIL, matching the mesh baseline -- confirms model family is not the confound.

