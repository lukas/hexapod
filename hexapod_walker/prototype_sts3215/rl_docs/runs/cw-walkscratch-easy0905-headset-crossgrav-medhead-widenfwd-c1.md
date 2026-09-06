# cw-walkscratch-easy0905-headset-crossgrav-medhead-widenfwd-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T02:11:55+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1

**wandb_id**: tj1ko3bp

**hypothesis**: Plain English: every widen2/irr heading+jitter composite tested so far was built in 0.5g FIRST, then abruptly transferred to 1g. Now that a plain-heading base(1g) champion exists (medhead-abrupt-c1-acq1, ACQ PASS, gait_valid 23/24 at 40M, leg-healthy), can the SAME widen2 full-8-way-heading-set composition be added FORWARD, directly at 1g, without ever touching 0.5g again? This tests whether the cross-gravity repair is a durable foundation for further curriculum extension natively in 1g, or whether composing new heading breadth only works pre-transfer.

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic (<0.10-duty every episode) single-leg sacrifice -- shows the 1g repair supports forward curriculum extension without another 0.5g detour. FAIL/INFORMATIVE-NEGATIVE if it collapses to the leg[1,4] chronic-sacrifice fingerprint -- would mean 1g heading generalization still requires building the composite at 0.5g first. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

