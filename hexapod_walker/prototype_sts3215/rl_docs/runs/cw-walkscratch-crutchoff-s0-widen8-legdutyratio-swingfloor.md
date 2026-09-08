# cw-walkscratch-crutchoff-s0-widen8-legdutyratio-swingfloor

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS (own scope) - joint pending -s1

**created**: 2026-09-08T11:26:59+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8-acq1-legdutyratiofresh-guardfix1

**wandb_id**: z0v3vfqq

**hypothesis**: A dragging/planting leg can inflate its peer-relative duty ratio above the 0.30 target without actually completing real steps, which is why both the 0.30 and 0.45 dose escalations showed the same trade (a flagged leg's gait_valid flips True while that same episode's slip gets worse): pairing the ratio charge with a swing-count floor (>=2 qualifying stride-filtered swings in a trailing 4s window, same definition walk_swing_gate already uses) zeroes a leg's ratio credit whenever it hasn't actually swung enough, regardless of duty, closing that escape hatch. New reward.walk_leg_duty_ratio_swing_min_count/_swing_window_s cfg keys, default 0.0/off (bit-exact legacy unless set); 6 new + 9 existing test_task_semantics.py bank tests green (walk_legduty_ratio_charge extended, backward-compatible signature). One lever vs the exact matched 0.30-dose guardfix1 sibling: same seed/init-from/heading-set/DR/motor cfg, only the swing floor added.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait. (a) Post-grace env/walk_leg_duty_ratio_shortfall and env/reward_walk_leg_duty_ratio must appear, finite, in real GPU telemetry (same activation check as the 0.30-dose canary). (b) Zero new falls/terminations vs the matched 0.30-dose guardfix1 sibling at the same seed/budget. (c) Same joint gait_valid-AND-slip/progress comparison the 0.30/0.45-dose FAILs used: >=3/4 groups must jointly improve (not just gait_valid alone) vs the matched 0.30-dose sibling for a CONTINUE signal; report explicitly whether the SAME episode indices that showed the 'gait_valid recovers, slip worsens' trade at 0.30/0.45 dose still show it here -- that is the one thing this lever is designed to fix. A short 2M null does not close the swing-floor lever on its own; missing telemetry is infrastructure/mechanism invalidity, not an efficacy FAIL.

**verdict**: CANARY PASS (own scope) - joint pending -s1. Per its own pre-registered gate: (a) telemetry PASS -- env/reward_walk_leg_duty_ratio (-18.5/-23.8) and env/walk_leg_duty_ratio_shortfall (0.123/0.158) both finite and firing in real GPU telemetry, same activation check as the 0.30-dose canary; (b) zero new falls/terminations vs the matched 0.30-dose guardfix1 sibling (both 0/24); (c) 3 of 4 groups jointly improve vs that sibling (gv/slip_med/prog_med): walk/det 5/6->6/6, slip 10.09->9.64, prog 0.865->0.928; walk/sto 6/6->6/6, slip 8.13->6.89, prog 0.953->1.007; walk_startjitter/det 6/6->6/6, slip 9.42->9.01, prog 1.005->1.048 -- all three genuinely improve together, not just gait_valid alone, and none of them shows the old 'gv recovers via worse slip' trade. The 4th group, walk_startjitter/sto, does NOT recover: gv holds 4/6->4/6 with the SAME two sacrificed legs at the same episode indices (leg5 idx2, leg0 idx3) as the 0.30-dose sibling, and slip there gets worse (12.32->14.34, prog 0.680->0.648) -- not the specific 'recovers-then-worse-slip' trade (gv never flipped), just no help in this one group. Meets the gate's own >=3/4 bar for a CONTINUE signal; the swing-floor lever is not closed by this 2M null per the gate's explicit text. -s1 sibling still training (another cycle's line, left alone) -- read jointly with it before deciding the +10M continuation this family's siblings (on10m/offctrl10m) took after their own 0.30-dose canary PASS.

