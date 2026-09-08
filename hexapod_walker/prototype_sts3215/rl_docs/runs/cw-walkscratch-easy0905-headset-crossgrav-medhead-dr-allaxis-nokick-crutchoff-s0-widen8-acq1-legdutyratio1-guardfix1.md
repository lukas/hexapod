# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8-acq1-legdutyratio1-guardfix1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-08T00:35:55+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8-acq1

**wandb_id**: nh3lt3o3

**hypothesis**: BUG-FIX RELAUNCH of s0-widen8-acq1-legdutyratio1 (the retrofit-onto-entrenched-checkpoint arm): the operator's fix (ebad6d0d) added g_ratio to the shared contact-bookkeeping activation guard -- the original run's charge was silently inert (bit-identical to charge=0) on this recipe, its result is INVALID. This relaunch uses the fixed code (16/16 leg_duty_ratio+adjacent bank tests green). Same retrofit hypothesis: does the charge repair a habit already baked in over 40M steps.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as the original legdutyratio1 gate: PASS if entrenched leg's duty recovers (peer-relative ratio >=0.22 majority of episodes), gait_valid improves materially, 0 new falls. CONTINUE (08-21): reward rising, charge measurably firing+declining, gait_valid trending up but short at 2M. FAIL: sacrifice persists AND the charge has gone quiet/saturated by canary end.

**verdict**: CANARY FAIL - MECHANISM (mechanism-health scope; SELF-CORRECTION of an earlier wrong verdict this same cycle that mistakenly claimed material improvement without first reading the undosed baseline). RETROFIT onto the entrenched 40M widen8-acq1 checkpoint: gate requires gait_valid to improve MATERIALLY vs the undosed parent. Direct episode-by-episode diff against the undosed cw-walkscratch-...-crutchoff-s0-widen8-acq1 baseline report shows the two are BIT-IDENTICAL in every one of 24 episodes (same gait_valid, same sacrificed_legs per episode, same modes) -- gait_valid 20/24 in BOTH, same exact 4 failing episodes (det ep0[5], det ep5[0,5], sj/sto ep2[5], sj/sto ep3[0]). Telemetry confirms the charge is live and firing correctly (env/reward_walk_leg_duty_ratio -21.3/-26.2, shortfall 0.14-0.17, no infra bug) -- this is not the earlier activation-guard bug. But 2M steps of the charge produced ZERO measurable behavior change on this already-entrenched checkpoint: unchanged is retention, not demonstrated efficacy, matching the pattern the operator's own concurrent note (fb_20260908T013619) names for the sibling s1 lineage. Distinct from the fresh-init siblings (s0/s1-widen8-acq1-legdutyratiofresh-guardfix1, both genuine CANARY PASS at 21/24 vs the termination mechanism's 12-13/24 from-scratch at 40M) which DO show real improvement -- the mechanism appears to work when applied from a naive/early init but has not yet been shown to cure an entrenched exploiter at this dose, mirroring the earlier walk_leg_duty_terminate_s finding that retrofit-onto-entrenched needs either a longer continuation or stays a from-scratch-only repair. No further retrofit dose funded this cycle; the acq10m/offctrl10m pair in flight tests continued training on a fresh-init PASS, not this retrofit-onto-bad-checkpoint question, so it remains open.

