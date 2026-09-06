# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kick1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T06:26:19+00:00

**pod**: hexapod-mjx-train-10

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kick1x-c1

**hypothesis**: HARDENING continuation off the FIRST fall in the whole DR-restoration sweep: kick1x-c1's own 2M canary (dr.walk_kick_prob=0.3 active during training, not just eval) already trained with the kick on and still produced one tilt_roll termination at eval time, but its training reward was RISING every quarter (5/62/132/177, canary-scale budget only) -- per the 08-21 run-interpretation ruling (bad eval + rising reward = continue, not stop). Warm-starting from kick1x-c1's own checkpoint and running a real 40M acquisition-scale budget (matching every other axis's ACQ/hardening scale in this campaign) tests whether more training time on the SAME kick dose closes the fall, rather than throwing away the 2M of kick-specific adaptation already banked.

**gate**: PASS/ACQ if the full 4-panel harness at 40M reaches 0 falls (matching the strict fall-trigger the 2M canary failed) with aggregate gait_valid staying majority (>=18/24) and no new chronic single-leg sacrifice. FAIL/INFORMATIVE-NEGATIVE if a fall still appears at 40M -- shows kick recovery at this dose (0.3 prob, 8-18deg) is a harder binding constraint than a training-budget problem, and either the dose needs lowering or a dedicated recovery-reward mechanism is needed (design pass, not a further blind budget increase).

