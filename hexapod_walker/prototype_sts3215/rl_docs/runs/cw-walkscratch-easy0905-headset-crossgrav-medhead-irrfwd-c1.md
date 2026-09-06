# cw-walkscratch-easy0905-headset-crossgrav-medhead-irrfwd-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T02:13:19+00:00

**pod**: hexapod-mjx-train-8

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1

**wandb_id**: xlhp3w8c

**hypothesis**: Plain English: every irr-timing composite tested so far was built in 0.5g FIRST, then abruptly transferred to 1g. Now that a plain-heading base(1g) champion exists (medhead-abrupt-c1-acq1, ACQ PASS, gait_valid 23/24 at 40M, leg-healthy), can the SAME command-timing-irregularity jitter be added FORWARD, directly at 1g, without ever touching 0.5g again? Tests whether the cross-gravity repair is a durable foundation for further curriculum extension natively in 1g (mirrors the sibling widenfwd-c1 arm on the heading axis).

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic (<0.10-duty every episode) single-leg sacrifice -- shows the 1g repair supports forward curriculum extension without another 0.5g detour. FAIL/INFORMATIVE-NEGATIVE if it collapses to the leg[1,4] chronic-sacrifice fingerprint -- would mean 1g timing-irregularity generalization still requires building the composite at 0.5g first. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

