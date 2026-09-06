# cw-walkscratch-easy0905-headset-crossgrav-s3acq-abrupt-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T01:50:13+00:00

**pod**: hexapod-mjx-train-9

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-s3acq

**wandb_id**: yodax2qa

**hypothesis**: Plain English: extends the cross-gravity-transfer test to the 2nd of the halfgrav heading-family n=3 confirmation set's clean champions, headset-halfgrav-s3acq (gait_valid 22/24, 0 falls, active leg-1 micro-underuse not chronic parking). Does this 2nd distinct clean champion (different seed/lineage from s1acq, medhead, widen2c1, irracq1, widenirrc1) also survive an abrupt jump to full 1g? Trained on the same 3-way heading set (0,+/-45deg) as s1acq, matched here exactly. Warm-starts from s3acq, which has never seen 1g.

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic (<0.10 duty every episode) single-leg sacrifice -- a 6th independent confirmation of cross-gravity-transfer as a general repair path (not one lucky champion). FAIL/INFORMATIVE-NEGATIVE if it collapses to a chronic single-leg-sacrifice fingerprint -- narrows the finding to a subset of leg-healthy sources. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

