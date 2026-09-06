# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-c1-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T13:01:33+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-c1

**wandb_id**: rvznzo5m

**hypothesis**: Seed-reproducibility check for the crutch-ON/kick-fully-off full-realism composite: its s0/seed2 lineage CANARY PASSED cleanly at 2M (19/24 gv, 0 falls) but its own 40M ACQ continuation (allaxis-nokick-c1-acq1) landed with 2 falls in 24 episodes against the pre-registered 0-falls bar (currently DIG-IN flagged, unverdicted) -- an open fork-decider for whether full-realism-with-crutch is a durable composite or fragile at acquisition scale. This is a fresh seed of the IDENTICAL recipe (kick fully off, torque crutch ON, same ~30-axis DR composite, same init-from checkpoint) to test whether the 2-fall outcome is seed-specific noise or reproduces across seeds -- independent of and does not preempt the concurrent dig-in's root-cause analysis of the existing seed-2 run.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY PASS/HOLDS if gait_valid stays majority (>=18/24) with 0 falls at 2M, matching the seed-2 canary's own clean 19/24-0-falls read -- informational at this budget (2M), the real reproducibility question is answered by this seed's own eventual ACQ (40M) continuation once this canary lands clean. A canary-scale fall here would already be a stronger/faster signal that the recipe (not just one seed) is fragile.

