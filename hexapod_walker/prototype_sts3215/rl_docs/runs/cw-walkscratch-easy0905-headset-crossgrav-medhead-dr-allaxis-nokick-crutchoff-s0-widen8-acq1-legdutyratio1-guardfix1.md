# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8-acq1-legdutyratio1-guardfix1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-08T00:35:55+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8-acq1

**hypothesis**: BUG-FIX RELAUNCH of s0-widen8-acq1-legdutyratio1 (the retrofit-onto-entrenched-checkpoint arm): the operator's fix (ebad6d0d) added g_ratio to the shared contact-bookkeeping activation guard -- the original run's charge was silently inert (bit-identical to charge=0) on this recipe, its result is INVALID. This relaunch uses the fixed code (16/16 leg_duty_ratio+adjacent bank tests green). Same retrofit hypothesis: does the charge repair a habit already baked in over 40M steps.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as the original legdutyratio1 gate: PASS if entrenched leg's duty recovers (peer-relative ratio >=0.22 majority of episodes), gait_valid improves materially, 0 new falls. CONTINUE (08-21): reward rising, charge measurably firing+declining, gait_valid trending up but short at 2M. FAIL: sacrifice persists AND the charge has gone quiet/saturated by canary end.

