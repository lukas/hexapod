# cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s12-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T11:56:11+00:00

**pod**: hexapod-mjx-train-5

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s12

**wandb_id**: t2r5n3mz

**hypothesis**: Plain English: matched joint-space control for the halfgrav cart_foot seed12 40M acquisition (ON launched same cycle) -- 4th-seed replicate breaking the tie in the closed n=3 cohort (2/3 seeds showed a cart_foot gait_valid advantage, 1/3 near-parity). Own-checkpoint continuation of the CANARY-PASSed offctrl-s12 2M arm (telemetry matched s7/s10/s11 sibling band exactly).

**gate**: ACQUISITION gate: same joint reading protocol as s7/s10/s11 (>=0.03 m/s median net forward in >=1 of walk/det,sto, 0 falls in det). slip/m and gait_valid vs the ON s12-acq1 sibling are the headline comparisons; determines whether this seed extends the seed7/10 majority pattern (2/3, real cart_foot gait_valid advantage) or the seed11 minority pattern (1/3, near-parity).

