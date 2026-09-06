# cw-walkscratch-easy0905-headset-crossgrav-widenirrc3-abrupt-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T06:29:01+00:00

**pod**: hexapod-mjx-train-9

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-widenirrc3-abrupt-c1-acq1

**wandb_id**: vvxksd4m

**hypothesis**: 2nd +40M endurance helping (80M cumulative) on widenirrc3-abrupt-c1-acq1, this cycle's own ACQ PASS (23/24 gait_valid matching its 2M canary, 0 falls, tight tracking, but deeply negative/bimodal reward on the widened 8-way incl-backward heading set). Same endurance-panel template as s1acq/medhead/widenirrc1/widen2c1 (all held clean or non-worsening under a 2nd 40M helping): does more 1g exposure hold this source's clean gait_valid steady, or does it entrench like s3acq did? Also tests whether the reward-misalignment (bimodal negative returns despite clean tracking) resolves, worsens, or stays flat with more training -- informative either way per the 08-21 ruling.

**gate**: PASS/HOLDS if aggregate gait_valid stays at/above its own 40M read (23/24) with no NEW chronic single-leg sacrifice and 0 falls. FAIL/ENTRENCHES if gait_valid drops toward the s3acq-style collapse (a repeating chronic leg emerges/hardens). Reward trend (positive-going vs still-bimodal-negative) is read as an informative side-question, not a pass/fail criterion on its own per the 08-21 ruling.

