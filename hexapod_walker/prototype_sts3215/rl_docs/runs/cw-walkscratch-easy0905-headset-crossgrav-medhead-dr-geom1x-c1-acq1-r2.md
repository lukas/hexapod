# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-geom1x-c1-acq1-r2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T08:39:54+00:00

**pod**: hexapod-mjx-train-11

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-geom1x-c1

**wandb_id**: 442acsdz

**hypothesis**: Plain English: does the nominal print/assembly GEOMETRY spread (link_len_scale_pct/link_len_leg_pct/com_offset_m) stay a clean walk with a REAL 40M training budget, not just a 2M canary glance? Re-run of geom1x-c1-acq1, which landed with an accidental 2M-step budget (the --steps-not-overridden respec bug, RL_LOG 09-06 07:3x/08:2x) -- this -r2 explicitly pins --steps 40000000 to give the axis its intended first ACQ-scale confirmation.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M, no NEW chronic single-leg sacrifice, 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall) -- would show the geometry-spread axis needs more/different training exposure before being called safe.

