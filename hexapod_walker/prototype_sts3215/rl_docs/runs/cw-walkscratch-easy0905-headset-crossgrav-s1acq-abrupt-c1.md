# cw-walkscratch-easy0905-headset-crossgrav-s1acq-abrupt-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T01:48:02+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-s1acq

**hypothesis**: Plain English: does the campaign's single healthiest halfgrav champion (headset-halfgrav-s1acq, gait_valid 24/24, the best score of the whole 09-05 campaign) also survive an abrupt jump to full 1g gravity, extending the cross-gravity-transfer finding (already confirmed on medhead/widen2c1/irracq1/widenirrc1/irrwidenc1) to the campaign-best leg-healthy source? s1acq was trained on the 3-way heading set (0,+/-45deg), matched here exactly (not the 5-way medhead or 8-way widen2 sets). Warm-starts from s1acq, which has never seen 1g.

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic (<0.10 duty every episode) single-leg sacrifice -- extends cross-gravity-transfer to the campaign's best-ever leg-healthy champion, strengthening it as a general repair path. FAIL/INFORMATIVE-NEGATIVE if it collapses to the leg[1,4] (or any single-leg) chronic-sacrifice fingerprint -- would show even the healthiest available champion isn't immune, narrowing the finding's practical reach. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

