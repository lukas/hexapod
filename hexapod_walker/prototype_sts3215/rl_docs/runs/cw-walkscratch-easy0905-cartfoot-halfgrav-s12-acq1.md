# cw-walkscratch-easy0905-cartfoot-halfgrav-s12-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T11:53:10+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-s12

**wandb_id**: hijwfdoc

**hypothesis**: Plain English: 4th-seed replicate of the halfgrav cart_foot ON 40M acquisition, breaking the tie in the closed n=3 cohort where cart_foot's gait_valid advantage over joint-space held for 2/3 seeds (s7 22/24 vs 10/24, s10 17/24 vs 7/24) but vanished for s11 (11/24 vs 10/24, near-parity). Own-checkpoint continuation of the CANARY-PASSed s12 2M arm (telemetry matched s7/s10/s11 band exactly).

**gate**: ACQUISITION gate: >=0.03 m/s median net forward in >=1 of walk/det,sto, 0 falls in det (same bar every s7/s10/s11 ON arm cleared). Read together with offctrl-s12-acq1 (matched joint-space OFF sibling, launched same cycle): gait_valid gap vs slip-only difference determines whether this seed extends the seed7/10 majority pattern (2/3, real cart_foot advantage) or the seed11 minority pattern (1/3, near-parity) for this recipe family.

