# cw-walkscratch-easy0905-headset-crossgrav-widen2c1-abrupt-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T00:48:22+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c1-acq1

**wandb_id**: uj013rxq

**hypothesis**: Plain English: this cycle's crossgrav-medhead discovery already showed the 5-way-heading halfgrav champion transfers to full 1g without collapsing into the base(1g) leg-1/4 chronic-sacrifice pattern. Does that generalize to a DIFFERENT, harder halfgrav champion -- the full 8-way-compass widen2-c1-acq1 (ACQ PASS, gait_valid 21/24, includes the two reversal headings) -- or was the medhead result specific to that one recipe/checkpoint? Warm-starts from widen2-c1-acq1 (never seen 1g) and abruptly sets ease.gravity_scale=1.0 from tick 0, same template as medhead-abrupt-c1.

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic (<0.10 duty every episode) single-leg sacrifice -- extends the cross-gravity-transfer finding to a 2nd, materially different halfgrav recipe (fuller heading set incl. reversals), strengthening it as a general repair path rather than a medhead-specific fluke. FAIL/INFORMATIVE-NEGATIVE if it collapses to the leg[1,4] chronic-sacrifice fingerprint -- would mean the medhead result doesn't generalize across heading-set recipes, narrowing the finding. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

