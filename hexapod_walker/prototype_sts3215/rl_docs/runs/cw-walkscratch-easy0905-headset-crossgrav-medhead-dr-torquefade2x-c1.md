# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade2x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T04:50:51+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: ky7yokg0

**hypothesis**: Fade the fixed 3x torque/battery assist crutch down to 2x (still a fixed, non-randomized single value, not yet the project's real 0.80-1.05 nominal range) -- the single lever CURRENT_TRUTHS/STATUS explicitly flagged as the key open DR-rung decision. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) tolerate losing a third of its assist without retraining collapse?

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) with no NEW chronic single-leg sacrifice and 0 falls. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows the 3x assist is load-bearing and any fade needs its own training rung (not a zero-retrain free lunch), and roughly by how much.

**verdict**: PASS/INFORMATIVE-POSITIVE: fading the fixed 3x torque/battery-assist crutch by a third (dr.torque_scale 3->2) on the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M, 24/24 clean) at 2M canary budget produces a PERFECT read: aggregate gait_valid 24/24 across all 4 panels (walk/det 6/6, walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6), 0 falls/24, slip/m tightly banded 3.4-5.1. Reward rising every quarter (76.2/168.0/265.3/360.8, still climbing). Contact sheet confirms clean six-leg cycling with body translation. This is the single most consequential axis named in the campaign's own DR-rung design note (the 3x torque assist was flagged as 'the key open decision') and it costs NOTHING at this dose -- the champion's gait margin does not depend on the full 3x torque crutch. Next: this result licenses testing a further torque-fade dose (e.g. 1.5x or 1x/no-assist) to find where the margin actually breaks, rather than stopping at the first nominal-restoration probe.

