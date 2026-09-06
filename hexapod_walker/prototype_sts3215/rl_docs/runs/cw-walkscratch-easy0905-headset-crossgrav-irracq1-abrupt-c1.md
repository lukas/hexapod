# cw-walkscratch-easy0905-headset-crossgrav-irracq1-abrupt-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T00:51:44+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irr-acq1

**wandb_id**: lt2nxvek

**hypothesis**: Plain English: this cycle's crossgrav-medhead discovery already showed the 5-way-heading halfgrav champion transfers to full 1g without collapsing into the base(1g) leg-1/4 chronic-sacrifice pattern. Does that generalize to a DIFFERENT halfgrav champion built on the irregular-command-timing-jitter rung -- halfgrav-irr-acq1 (ACQ PASS, gait_valid majority, first irr rung to clear at 40M) -- or was the medhead result specific to plain fixed-heading-only recipes? Warm-starts from halfgrav-irr-acq1 (never seen 1g) and abruptly sets ease.gravity_scale=1.0 from tick 0, same template as medhead-abrupt-c1.

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic (<0.10 duty every episode) single-leg sacrifice -- extends the cross-gravity-transfer finding to a 3rd, materially different halfgrav recipe (command-timing irregularity), strengthening it as a general repair path rather than a medhead-specific fluke. FAIL/INFORMATIVE-NEGATIVE if it collapses to the leg[1,4] chronic-sacrifice fingerprint -- would mean the medhead result doesn't generalize across recipe axes, narrowing the finding. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

