# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-geom1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: SUPERSEDED

**created**: 2026-09-06T07:43:15+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-geom1x-c1

**wandb_id**: 65m7xxug

**hypothesis**: Plain English: does the nominal print/CAD/assembly geometry spread (+-2% leg length, +-12mm CoM shift) stay a clean walk with a real 40M training budget, not just a 2M canary glance? geom1x-c1's own 2M canary was 21/24 (0 falls, scattered non-chronic flags across 3 legs/modes, no repeat) -- this is its first ACQ-scale confirmation, and it CLOSES the last of guardrails.yaml's named idealized DR axes (mass/geometry/friction/compliance/gravity/gains) at ACQ scale once done.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M, no NEW chronic single-leg sacrifice, 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall) -- would show the geometry-spread axis needs real training exposure before being called safe.

**verdict**: Mislabeled-budget duplicate, not a real ACQ read: same respec-steps-inheritance footgun -- landed at 2M not 40M. Same information as the already-PASSed geom1x-c1 2M canary (21/24 gait_valid, scattered non-chronic flags, 0 falls) -- no new evidence. Why: closing the ledger cleanly. What's next: the correctly-budgeted 40M read is running as geom1x-c1-acq1-r2 (wandb 442acsdz) -- read and verdict that one, not this.

