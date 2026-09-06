# cw-walkscratch-easy0905-headset-crossgrav-irr2acq1-abrupt-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T02:34:29+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-irr2acq1-abrupt-c1

**wandb_id**: zsxkfxzz

**hypothesis**: Plain English: irr2acq1-abrupt-c1's 2M canary just PASSED (22/24 gv, 0 falls), confirming irr-timing crossgrav transfer on its 2nd independent seed. Does this hold at full 40M acquisition budget, matching the first seed's own irracq1-abrupt-c1-acq1 continuation (same template)?

**gate**: ACQ PASS if gait_valid stays majority-or-better in walk/det with no chronic single-leg sacrifice at 40M (matching or improving the 2M canary's 22/24). FAIL if it collapses toward chronic leg-1/4 sacrifice at scale.

