# cw-walkscratch-easy0905-headset-halfgrav-widenirr-c2b

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T22:54:56+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c2b

**wandb_id**: lldm22oo

**hypothesis**: Plain English: 2nd-seed twin of widenirr-c1 (same cycle), using the OTHER matched-budget widen2 seed (widen2-c2b, warm-started from medhead2-acq1, CANARY PASS 16/24 gait_valid, 0 falls, direrr/courserr/slip close to widen2-c1's own numbers). Adds ONLY goal.walk_cmd_resample_jitter=0.5 on top, no new reward keys. Gives the heading-widen-then-add-timing-jitter composition order n=2 independent seeds in one batch (operator 08-22 batching discipline) instead of drawing a recipe-level conclusion off a single arm.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (2M). PASS/INFORMATIVE if gait_valid stays majority-valid (>=4/6 det) with 0 falls, matching or beating widen2-c2b's own clean numbers (16/24 gait_valid, 0 falls), and wrong_course_frac/direction tracking doesn't blow up under the added timing jitter. FAIL if gait_valid collapses (new leg sacrifice vs widen2-c2b's own baseline) or falls appear. Read together with widenirr-c1 before concluding the composition order is recipe-general vs seed-specific.

