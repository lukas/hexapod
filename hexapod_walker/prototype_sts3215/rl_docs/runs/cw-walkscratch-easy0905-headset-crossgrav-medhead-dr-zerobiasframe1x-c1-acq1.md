# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-zerobiasframe1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: SUPERSEDED

**created**: 2026-09-06T08:14:15+00:00

**pod**: hexapod-mjx-train-10

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-zerobiasframe1x-c1

**wandb_id**: s638szr8

**hypothesis**: Plain English: does the harder frame-COUPLED zero-bias axis (bias applied through the command frame, not just sensor-side) stay a clean walk with a real 40M training budget, not just a 2M canary glance? zerobiasframe1x-c1's own 2M canary was CANARY PASS 23/24 (0 falls, 1 non-chronic leg-0 flag), matching its sensor-only zerobias1x sibling -- first ACQ-scale confirmation of the frame-coupled variant, joining the individual-axis durability batch (encnoise1x/friction1x/mass1x/latency1x/push1x/torquefade2x/torquefade15x/zerobias1x/kick1x/gains1x/geom1x/fault1x/extpush1x).

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M, no NEW chronic single-leg sacrifice, 0 falls. FAIL/ENTRENCHES if it drops (<12/24), a new chronic leg, or a fall -- would show command-frame-coupled bias realism needs real training exposure before being called safe.

**verdict**: SUPERSEDED (bookkeeping, no behavioral read) -- this respec silently inherited its source canary's 2M --steps (the known steps-not-overridden respec bug also hit on gains1x/geom1x/fault1x/extpush1x), so it never trained at ACQ scale; the corrected re-run zerobiasframe1x-c1-acq1-r2 is the arm of record and already verdicted ACQ PASS (22/24 gv, 0 falls, W&B 8dv3hru5). Closing this entry so the triage table stops listing it as an unverdicted finished run.

