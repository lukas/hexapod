# cw-walkscratch-crutchoff-s0-widen8-legdutyratio-swingfloor

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FINISHED

**created**: 2026-09-08T11:26:59+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8-acq1-legdutyratiofresh-guardfix1

**wandb_id**: z0v3vfqq

**hypothesis**: A dragging/planting leg can inflate its peer-relative duty ratio above the 0.30 target without actually completing real steps, which is why both the 0.30 and 0.45 dose escalations showed the same trade (a flagged leg's gait_valid flips True while that same episode's slip gets worse): pairing the ratio charge with a swing-count floor (>=2 qualifying stride-filtered swings in a trailing 4s window, same definition walk_swing_gate already uses) zeroes a leg's ratio credit whenever it hasn't actually swung enough, regardless of duty, closing that escape hatch. New reward.walk_leg_duty_ratio_swing_min_count/_swing_window_s cfg keys, default 0.0/off (bit-exact legacy unless set); 6 new + 9 existing test_task_semantics.py bank tests green (walk_legduty_ratio_charge extended, backward-compatible signature). One lever vs the exact matched 0.30-dose guardfix1 sibling: same seed/init-from/heading-set/DR/motor cfg, only the swing floor added.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait. (a) Post-grace env/walk_leg_duty_ratio_shortfall and env/reward_walk_leg_duty_ratio must appear, finite, in real GPU telemetry (same activation check as the 0.30-dose canary). (b) Zero new falls/terminations vs the matched 0.30-dose guardfix1 sibling at the same seed/budget. (c) Same joint gait_valid-AND-slip/progress comparison the 0.30/0.45-dose FAILs used: >=3/4 groups must jointly improve (not just gait_valid alone) vs the matched 0.30-dose sibling for a CONTINUE signal; report explicitly whether the SAME episode indices that showed the 'gait_valid recovers, slip worsens' trade at 0.30/0.45 dose still show it here -- that is the one thing this lever is designed to fix. A short 2M null does not close the swing-floor lever on its own; missing telemetry is infrastructure/mechanism invalidity, not an efficacy FAIL.

