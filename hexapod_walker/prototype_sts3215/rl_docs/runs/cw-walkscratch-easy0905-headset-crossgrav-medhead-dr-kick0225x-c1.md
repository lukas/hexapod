# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kick0225x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY_FAIL

**created**: 2026-09-06T09:37:30+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kickhalf1x-c1

**wandb_id**: 4xcygaqu

**hypothesis**: Kick-dose ladder bisection: kick1x-c1 (walk_kick_prob=0.3, nominal) FELL (1 real tilt_roll fall); kickhalf1x-c1 (0.15, half dose) PASSED clean (21/24 gv, 0 falls). This arm tests the exact midpoint dose (0.225, same 8-18deg peak roll / 0.5-1.2s duration kick shape, same medhead_abrupt_c1_acq1 champion, same 2M canary scale) to bracket where the champion's zero-shot kick-recovery margin actually breaks, instead of leaving a 2x dose gap unexplored.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if the full 4-panel harness reaches 0 falls with aggregate gait_valid majority (>=18/24) and no new chronic single-leg sacrifice -- narrows the safe-dose ceiling above 0.15. FAIL/INFORMATIVE-NEGATIVE if a fall appears -- pins the knee between 0.15 and 0.225, tightening the ladder for any future kick-hardening budget.

**verdict**: CANARY FAIL - MECHANISM: the 0.225 mid-dose kick-prob bisection (between kickhalf's clean 0.15 and kick1x's falling 0.3) still produces a fall -- walk/sto/2 terminates tilt_roll (prog 2.44, fwd 0.08m, sac=[2]), aggregate gait_valid 21/24 (6/5/4/6), plus 2 non-chronic singleton leg[4] flags confined to walk_startjitter/det. Per the gate's own pre-registered criterion (0 falls required for PASS/INFORMATIVE-POSITIVE), this is a FAIL: the safe-dose ceiling for isolated walk_kick_prob is pinned strictly between 0.15 (kickhalf, clean) and 0.225 (this run, 1 fall), tightening the ladder for any future kick-hardening budget -- do not treat 0.225 as a usable dose. Reward still rising through the 2M canary window (16->81->135->189), consistent with mechanism-health-only canary scope (not judged on skill acquisition).

