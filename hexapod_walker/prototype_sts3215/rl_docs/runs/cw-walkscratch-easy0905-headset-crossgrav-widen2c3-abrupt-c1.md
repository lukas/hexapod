# cw-walkscratch-easy0905-headset-crossgrav-widen2c3-abrupt-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T02:22:56+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-widen2c1-abrupt-c1

**wandb_id**: jlal69m5

**hypothesis**: Plain English: cross-gravity-transfer (halfgrav 0.5g champion warm-started and abruptly jumped to full 1g from tick 0) has now been CONFIRMED for the widen2 recipe on seed 1 (widen2c1-abrupt-c1 CANARY PASS 19/24) plus 4 other distinct recipes (medhead x2, irracq1, widenirr, irrwiden). widen2-c3-acq1 (the just-PASSed 3rd, independently-seeded widen2 champion, gait_valid 20/24 at 40M) has never been cross-gravity-tested. This is the n=2-seed confirmation for the widen2 RECIPE's own crossgrav-transfer specifically (distinct from the irr/composite axes already n=2-confirmed elsewhere): does a 2nd healthy widen2 seed transfer as cleanly as widen2-c1 did, closing the widen2-crossgrav generality the same way irr-timing already closed its own (irr-acq1 + irr2-acq1, 2/2 PASS)?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic (<0.10 duty every episode) single-leg sacrifice -- extends cross-gravity-transfer to a 2nd independent widen2 seed, closing the widen2-recipe crossgrav question with n=2. FAIL/INFORMATIVE-NEGATIVE if it collapses into the base(1g) leg-1/4 chronic-sacrifice entrenchment fingerprint (same discriminator used throughout this campaign: startjitter panel + per-leg duty, not walk/det alone).

