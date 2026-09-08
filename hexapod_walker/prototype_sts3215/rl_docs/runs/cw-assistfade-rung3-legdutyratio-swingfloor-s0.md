# cw-assistfade-rung3-legdutyratio-swingfloor-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-08T12:23:25+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-assistfade-rung3-legdutyratio-s0

**wandb_id**: 56x7tjo1

**hypothesis**: Does pairing the assistfade rung3 duty-ratio charge with the walkcurr-proven swing-count floor (>=2 qualifying swings/4s window, zeroing ratio credit for a leg that hasn't actually swung) fix what the bare charge could not: rung3's chronic leg-sacrifice-plus-high-slip-drift FAIL, where a planted/dragging leg inflated its own duty ratio without completing real steps (the 09-08 comparator-correction finding that low-relative-duty pricing alone does not target fully-planted no-swing legs)? Single lever vs the exact matched bare-charge cw-assistfade-rung3-legdutyratio-s0 sibling (CANARY FAIL - MECHANISM): only reward.walk_leg_duty_ratio_swing_min_count=2.0 / _swing_window_s=4.0 added (same dose/target/grace/tau as the sibling), otherwise byte-identical -- same recipe/dose walkcurr's own crutchoff-s0-widen8-legdutyratio-swingfloor canary used (CONTINUE signal there, 3/4 groups jointly improve). New keys already bank-proved (6 new + 9 existing test_task_semantics.py tests green, default 0.0/off, bit-exact when unset) -- first application of this mechanism to the assistfade/mesh/100Hz track.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait at 2M. (a) Post-grace env/walk_leg_duty_ratio_shortfall and env/reward_walk_leg_duty_ratio must appear, finite, in real GPU telemetry (same activation check as the bare-charge sibling). (b) Zero new falls/terminations vs the matched bare-charge legdutyratio-s0 sibling at the same seed/budget. (c) Per-leg duty comparison vs that sibling's own report.json: PASS/CONTINUE if the chronic sacrificed leg(s) [0,3] measurably narrow (per-leg duty >=0.10 where the sibling showed <0.05) in >=1 held-out mode without a new slip/current regression; FAIL-MECHANISM if per-leg duty is statistically indistinguishable from the undosed-swing-floor sibling (same self-check discipline as the walkcurr retrofit lesson) or the run is outright worse (new falls, gait_valid regression). Missing telemetry is infrastructure/mechanism invalidity, not an efficacy FAIL.

**verdict**: CANARY FAIL - MECHANISM: swing-count-floor lever (>=2 qualifying swings/4s zeroes ratio credit) added to the matched bare-charge cw-assistfade-rung3-legdutyratio-s0 sibling (same seed0/budget/blend-schedule/random-weight init, only the swing-floor keys added). Telemetry engages (env/walk_leg_duty_ratio_shortfall 0.245, env/reward_walk_leg_duty_ratio -36.8, activation confirmed) but the run is outright worse on the gate's own trigger: gait_valid groups [6,6,2,1]=15/24 (bare) -> [6,3,2,2]=13/24 (swingfloor), walk/sto regresses 6/6->3/6 (new gait_valid regression), walk/det slip worsens +25% (12.67->15.90), walk/sto slip worsens +6% (16.71->17.68). Only walk_startjitter/sto improves (gv 1/6->2/6, slip -10%) -- 1/4 groups improve, short of a no-regression bar. Training reward corroborates a real regression, not the 08-21 rising-reward case: ep_rew_mean tracks the bare sibling almost exactly through 3 quarters (102/178/230 vs 103/175/221) then collapses monotonically through the settling window (final -2163.5 vs sibling's +61.6; last logged points fall every step -277->-646->-971->-1441->-1570->-1963->-1975->-2164). The swing-floor lever does not repair rung3's chronic sacrifice on this seed and worsens both clean (non-jitter) held-out modes. Do not relaunch this exact lever on assistfade without a new idea; s1 (same lever, still training under another cycle) is the only other data point.

