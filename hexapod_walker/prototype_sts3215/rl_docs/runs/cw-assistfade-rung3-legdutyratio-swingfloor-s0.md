# cw-assistfade-rung3-legdutyratio-swingfloor-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T12:23:25+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-assistfade-rung3-legdutyratio-s0

**wandb_id**: 56x7tjo1

**hypothesis**: Does pairing the assistfade rung3 duty-ratio charge with the walkcurr-proven swing-count floor (>=2 qualifying swings/4s window, zeroing ratio credit for a leg that hasn't actually swung) fix what the bare charge could not: rung3's chronic leg-sacrifice-plus-high-slip-drift FAIL, where a planted/dragging leg inflated its own duty ratio without completing real steps (the 09-08 comparator-correction finding that low-relative-duty pricing alone does not target fully-planted no-swing legs)? Single lever vs the exact matched bare-charge cw-assistfade-rung3-legdutyratio-s0 sibling (CANARY FAIL - MECHANISM): only reward.walk_leg_duty_ratio_swing_min_count=2.0 / _swing_window_s=4.0 added (same dose/target/grace/tau as the sibling), otherwise byte-identical -- same recipe/dose walkcurr's own crutchoff-s0-widen8-legdutyratio-swingfloor canary used (CONTINUE signal there, 3/4 groups jointly improve). New keys already bank-proved (6 new + 9 existing test_task_semantics.py tests green, default 0.0/off, bit-exact when unset) -- first application of this mechanism to the assistfade/mesh/100Hz track.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait at 2M. (a) Post-grace env/walk_leg_duty_ratio_shortfall and env/reward_walk_leg_duty_ratio must appear, finite, in real GPU telemetry (same activation check as the bare-charge sibling). (b) Zero new falls/terminations vs the matched bare-charge legdutyratio-s0 sibling at the same seed/budget. (c) Per-leg duty comparison vs that sibling's own report.json: PASS/CONTINUE if the chronic sacrificed leg(s) [0,3] measurably narrow (per-leg duty >=0.10 where the sibling showed <0.05) in >=1 held-out mode without a new slip/current regression; FAIL-MECHANISM if per-leg duty is statistically indistinguishable from the undosed-swing-floor sibling (same self-check discipline as the walkcurr retrofit lesson) or the run is outright worse (new falls, gait_valid regression). Missing telemetry is infrastructure/mechanism invalidity, not an efficacy FAIL.

