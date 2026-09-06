# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kickhalf1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T09:09:56+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kickhalf1x-c1

**wandb_id**: x4yqywuc

**hypothesis**: Does the half-dose kick-perturbation canary (medhead-dr-kickhalf1x-c1: 0.15 kick prob, 21/24 gait_valid at 2M, 0 falls, 3 different legs flagged in 3 different modes -- non-chronic) hold its zero-shot recovery margin at a real 40M ACQ budget, or does more training exposure at this dose either close the gap to a clean sweep or reveal an entrenching chronic leg the 2M canary was too short to show? Direct follow-up to kick1x-c1's full-dose fall and this canary's own dose-bisection framing.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg pattern and 0 falls (matches or improves the canary's non-chronic 3-legs-3-modes scatter). FAIL/ENTRENCHES if it drops (<12/24), the scatter consolidates into a chronic single-leg pattern, or a fall appears -- would show half-dose kick recovery is only canary-lucky, not durable.

