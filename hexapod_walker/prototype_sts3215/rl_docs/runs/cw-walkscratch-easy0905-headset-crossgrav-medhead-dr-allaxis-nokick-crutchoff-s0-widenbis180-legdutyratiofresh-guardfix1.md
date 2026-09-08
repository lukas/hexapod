# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbis180-legdutyratiofresh-guardfix1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T00:38:04+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbis180

**wandb_id**: w6y5uai5

**hypothesis**: BUG-FIX RELAUNCH of s0-widenbis180-legdutyratiofresh: the operator's fix (ebad6d0d) added g_ratio to the shared contact-bookkeeping activation guard -- the original run's charge was silently inert on this recipe (no other gate armed), its result is INVALID. This relaunch uses the fixed code (16/16 leg_duty_ratio+adjacent bank tests green). Same hypothesis: fresh provenance on the milder 6-way-heading lineage.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as the original s0-widenbis180-legdutyratiofresh gate: PASS if leg-0's duty recovers (peer-relative ratio >=0.22 majority of episodes), gait_valid >=18/24, 0 new falls. CONTINUE if reward+gait_valid trending up but short. FAIL if leg-0 sacrifice persists regardless.

