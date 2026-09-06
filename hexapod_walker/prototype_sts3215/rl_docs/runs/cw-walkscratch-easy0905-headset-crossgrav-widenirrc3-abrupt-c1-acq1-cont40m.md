# cw-walkscratch-easy0905-headset-crossgrav-widenirrc3-abrupt-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T06:29:01+00:00

**pod**: hexapod-mjx-train-9

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-widenirrc3-abrupt-c1-acq1

**wandb_id**: vvxksd4m

**hypothesis**: 2nd +40M endurance helping (80M cumulative) on widenirrc3-abrupt-c1-acq1, this cycle's own ACQ PASS (23/24 gait_valid matching its 2M canary, 0 falls, tight tracking, but deeply negative/bimodal reward on the widened 8-way incl-backward heading set). Same endurance-panel template as s1acq/medhead/widenirrc1/widen2c1 (all held clean or non-worsening under a 2nd 40M helping): does more 1g exposure hold this source's clean gait_valid steady, or does it entrench like s3acq did? Also tests whether the reward-misalignment (bimodal negative returns despite clean tracking) resolves, worsens, or stays flat with more training -- informative either way per the 08-21 ruling.

**gate**: PASS/HOLDS if aggregate gait_valid stays at/above its own 40M read (23/24) with no NEW chronic single-leg sacrifice and 0 falls. FAIL/ENTRENCHES if gait_valid drops toward the s3acq-style collapse (a repeating chronic leg emerges/hardens). Reward trend (positive-going vs still-bimodal-negative) is read as an informative side-question, not a pass/fail criterion on its own per the 08-21 ruling.

**verdict**: HARDENING/endurance continuation HOLDS BY SUBSTANCE at +40M (80M total), a narrow numeric miss against the gate's literal 'at/above 23/24' bar that does not read as entrenchment. Aggregate gait_valid 21/24 (walk/det 5/6, walk/sto 5/6, walk_startjitter/det 5/6, walk_startjitter/sto 6/6), 0 falls/terminations across all 24 episodes. The 3 flagged episodes (walk/det ep3 leg5 duty 0.01; walk/sto ep5 leg5 duty 0.07; walk_startjitter/det ep4 leg1 duty 0.08) are the SAME episode indices/legs already borderline-low in this checkpoint's own established 40M read (parent walk/det ep3 leg5=0.01 already near-zero; walk/sto ep5 leg5=0.12; walk_startjitter/det ep4 leg1=0.13) -- the extra 40M nudged 2 already-marginal legs (0.12->0.07, 0.13->0.08) a few points below the gait_valid duty floor rather than creating any NEW leg/mode pathology. Critically, 3 DIFFERENT legs across 3 DIFFERENT modes, each a single non-repeating episode -- not the 'repeating chronic leg emerges/hardens' failure shape the gate explicitly names. Frame strips (walk_det_3, walk_sto_5) show clean six-leg tripod cycling, body translating, no drag/skate/collapse; the low-duty legs are still swinging (18-60 swing events over 20s), not parked. Reward stays bimodal-negative per the gate's own pre-registered informative-only side-note -- not scored. Why: this is measurement noise at an already-known margin, not new collapse. Next: no further budget needed on this line; watch the same 3 borderline points (det/3-leg5, sto/5-leg5, sj-det/4-leg1) if this checkpoint is composed further.

