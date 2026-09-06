# cw-walkscratch-easy0905-headset-crossgrav-widenirrc1-abrupt-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T01:08:17+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-widenirr-c1-acq1

**wandb_id**: zigln3k9

**hypothesis**: Plain English: this cycle's own widenirr-c1-acq1 ACQ PASS (widen+irr composition, 23/24 gait_valid, beats the plain widen2-c1-acq1 sibling) makes it a 3rd distinct leg-healthy halfgrav champion (after medhead and widen2c1) never yet tested under an abrupt jump to full 1g gravity. Does the cross-gravity-transfer repair (already 2/2 PASS on materially different halfgrav recipes) generalize to this composed widen+irr recipe too, or is transfer itself recipe-sensitive?

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic (<0.10 duty every episode) single-leg sacrifice -- extends cross-gravity-transfer to a 3rd, materially different halfgrav recipe (widen+irr composition). FAIL/INFORMATIVE-NEGATIVE if it collapses to the leg[1,4] chronic-sacrifice fingerprint seen on the base(1g) family -- would narrow the transfer finding away from composed recipes. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

