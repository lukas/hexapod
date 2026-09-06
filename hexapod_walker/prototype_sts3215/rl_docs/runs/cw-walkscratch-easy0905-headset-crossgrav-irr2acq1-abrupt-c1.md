# cw-walkscratch-easy0905-headset-crossgrav-irr2acq1-abrupt-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T01:44:00+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: headset-halfgrav-irr2-acq1

**wandb_id**: 2vlneqky

**hypothesis**: Plain English: this cycle's crossgrav-irracq1 canary showed the FIRST irr-timing-jitter seed (halfgrav-irr-acq1) survives an abrupt jump to full 1g cleanly. Does the SAME recipe's 2nd seed (halfgrav-irr2-acq1, a distinct champion ACQ PASS at 40M, gait_valid 19/24) survive the identical abrupt gravity_scale 0.5->1.0 jump, or was the first seed's clean transfer a per-seed fluke? This gives the irr-timing crossgrav finding its own n=2 seed confirmation, matching the seed-robustness discipline already applied to every other rung in this campaign (widen2-c1/c2b/c3, irr-c1/c2, irrwiden-c1/c2).

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic single-leg sacrifice -- confirms cross-gravity-transfer is seed-general for the irr-timing recipe, not a single-seed fluke. FAIL/INFORMATIVE-NEGATIVE if it collapses to the leg[1,4] chronic-sacrifice fingerprint -- would mean seed variance, not recipe, drives transfer success. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

