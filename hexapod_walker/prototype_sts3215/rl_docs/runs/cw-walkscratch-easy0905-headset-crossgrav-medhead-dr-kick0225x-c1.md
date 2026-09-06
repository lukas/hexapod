# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kick0225x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T09:36:56+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kickhalf1x-c1

**hypothesis**: Kick-dose ladder bisection: kick1x-c1 (walk_kick_prob=0.3, nominal) FELL (1 real tilt_roll fall); kickhalf1x-c1 (0.15, half dose) PASSED clean (21/24 gv, 0 falls). This arm tests the exact midpoint dose (0.225, same 8-18deg peak roll / 0.5-1.2s duration kick shape, same medhead_abrupt_c1_acq1 champion, same 2M canary scale) to bracket where the champion's zero-shot kick-recovery margin actually breaks, instead of leaving a 2x dose gap unexplored.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if the full 4-panel harness reaches 0 falls with aggregate gait_valid majority (>=18/24) and no new chronic single-leg sacrifice -- narrows the safe-dose ceiling above 0.15. FAIL/INFORMATIVE-NEGATIVE if a fall appears -- pins the knee between 0.15 and 0.225, tightening the ladder for any future kick-hardening budget.

**refused_reason**: hexapod-mjx-train-3 already runs cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade2x-c1-acq1-cont40m — GPU pods host exactly one run; pick a free GPU pod.

