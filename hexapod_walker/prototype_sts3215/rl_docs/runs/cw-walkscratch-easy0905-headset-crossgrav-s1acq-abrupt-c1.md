# cw-walkscratch-easy0905-headset-crossgrav-s1acq-abrupt-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY_PASS

**created**: 2026-09-06T01:48:02+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-s1acq

**wandb_id**: slm87dgu

**hypothesis**: Plain English: does the campaign's single healthiest halfgrav champion (headset-halfgrav-s1acq, gait_valid 24/24, the best score of the whole 09-05 campaign) also survive an abrupt jump to full 1g gravity, extending the cross-gravity-transfer finding (already confirmed on medhead/widen2c1/irracq1/widenirrc1/irrwidenc1) to the campaign-best leg-healthy source? s1acq was trained on the 3-way heading set (0,+/-45deg), matched here exactly (not the 5-way medhead or 8-way widen2 sets). Warm-starts from s1acq, which has never seen 1g.

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic (<0.10 duty every episode) single-leg sacrifice -- extends cross-gravity-transfer to the campaign's best-ever leg-healthy champion, strengthening it as a general repair path. FAIL/INFORMATIVE-NEGATIVE if it collapses to the leg[1,4] (or any single-leg) chronic-sacrifice fingerprint -- would show even the healthiest available champion isn't immune, narrowing the finding's practical reach. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

**verdict**: Cross-gravity-transfer holds on the campaign's single healthiest halfgrav champion (headset-halfgrav-s1acq, gait_valid 24/24 at native 0.5g) jumped abruptly to full 1g. Evidence: gait_valid PERFECT 24/24 (6/6 every one of walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto), sac=[] in ALL 24 episodes (zero sacrificed-leg flags anywhere, the cleanest crossgrav result of the whole sweep -- beats medhead 23/24 and every other champion tested), 0 falls/terminations. slip_per_m 2.6-4.4 (medians 3.1-4.0), forward distance 2.9-4.2m/20s episode, all in-band with sibling crossgrav PASSes. Frame strip (walk_det_0) shows genuine six-leg cycling with clear body translation. Why: this is the campaign-best leg-healthy champion's first cross-gravity test, and it transfers cleaner than every other champion tried so far, further strengthening leg-health-at-source as the necessary and sufficient condition for robust 1g transfer (contrasts with the widen2c2b negative control, whose already-parked leg-1 persisted through transfer). Next: matched 40M ACQ continuation (same template as every other PASS in this sweep).

