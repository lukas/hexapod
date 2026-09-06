# cw-walkscratch-easy0905-headset-crossgrav-widen2c1-irrfwd-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T02:59:38+00:00

**pod**: hexapod-mjx-train-8

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-widen2c1-abrupt-c1-acq1

**wandb_id**: nodmsa82

**hypothesis**: Plain English: the medhead lineage already showed that once a champion is cross-gravity-transferred to full 1g, MORE curriculum (heading widening, or timing-irregularity) can be composed natively at 1g without another 0.5g detour (widenfwd-c1/irrfwd-c1 both running/landing). This just-PASSED widen2c1-abrupt-c1-acq1 champion (ACQ PASS this cycle, gait_valid 20/24 at full 40M/1g) already HAS the full 8-way heading set, so the one composable axis left is command-timing irregularity (the irr jitter). Does 'compose-after-transfer' generalize to a 2nd base champion (not just medhead), and specifically to one that already carries the harder full 8-way heading (incl. reversals)?

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic (<0.10-duty every episode) single-leg sacrifice -- shows compose-after-transfer generalizes beyond the medhead base champion to a 2nd, harder (full-heading) one. FAIL/INFORMATIVE-NEGATIVE if it collapses to the leg[1,4] chronic-sacrifice fingerprint or a new chronic pattern -- would mean compose-after-transfer is medhead-specific, not a general property of the 1g-transferred state. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

