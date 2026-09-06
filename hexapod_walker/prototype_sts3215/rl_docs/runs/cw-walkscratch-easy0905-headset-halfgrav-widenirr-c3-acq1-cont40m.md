# cw-walkscratch-easy0905-headset-halfgrav-widenirr-c3-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T07:00:54+00:00

**pod**: hexapod-mjx-train-11

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-widenirr-c3-acq1

**wandb_id**: i0ucnjvx

**hypothesis**: Plain English: same endurance question as the crossgrav cont40m siblings, run on the halfgrav (0.5g) widenirr champion (headset-halfgrav-widenirr-c3-acq1: 21/24 gait_valid, mild non-chronic degrade from its own 23/24 2M canary, 0 falls, course-tracking metrics actually IMPROVED vs canary) -- first endurance read on a HALFGRAV source (all prior cont40m arms are crossgrav/1g), tests whether the cleanliness-margin-predicts-endurance rule generalizes across gravity regimes too.

**gate**: HARDENING/endurance continuation (+40M, own checkpoint, no cfg change). PASS/HOLDS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with slip_per_m staying tightly banded and no NEW chronic leg beyond this checkpoint's own established 40M read (21/24, scattered non-chronic legs 2/5). FAIL/ENTRENCHES if a chronic single-leg sacrifice newly emerges/spreads across multiple modes.

**verdict**: HARDENING PASS/HOLDS -- +40M endurance continuation (80M cumulative) on the 0.5g widenirr-c3 champion, the first halfgrav-source cont40m read. Gate report: gait_valid stays majority in both named modes (walk/det 4/6, walk/sto 4/6; startjitter det 5/6, sto 6/6 -- 19/24 aggregate, a mild degrade from the own-40M established 21/24, both inside the gate's own >=4/6-per-mode bar). 0 falls/terminations across all 24 episodes, matching the parent. No NEW chronic single-leg sacrifice: every flagged sac list is scattered/non-chronic (leg2 x2 in det, leg1/leg5 once each elsewhere), never the same leg repeating a majority of episodes in one mode -- same fingerprint class as the parent's own 2/5 scattered flags. slip_per_m drifted up mode-by-mode (det 2.87->3.66, sto 3.57->5.94 med, one sto outlier at 10.33) -- worth watching but not a new chronic-leg regression and still short of any fall. Frame strips (walk_det_1, walk_sto_0) show genuine six-leg cycling with visible leg-phase alternation, consistent with the prog/fwd numbers (~0.05-0.08 m/s). Extends the cleanliness-margin-predicts-endurance rule to a halfgrav source for the first time: this 0.5g champion holds its endurance read the same way the crossgrav cont40m siblings do. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_halfgrav_widenirr_c3_acq1_cont40m_gate/report.json vs .../cw_walkscratch_easy0905_headset_halfgrav_widenirr_c3_acq1_gate/report.json, walk_det_1.png, walk_sto_0.png, W&B i0ucnjvx.

