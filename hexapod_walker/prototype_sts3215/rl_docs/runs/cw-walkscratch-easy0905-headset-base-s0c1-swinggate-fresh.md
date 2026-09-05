# cw-walkscratch-easy0905-headset-base-s0c1-swinggate-fresh

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-05T21:32:17+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-s0c1-dgfresh

**hypothesis**: Sixth structural repair attempt for the base(1g)-family marginal leg-favoritism pathology (leg 4 chronically at duty 0.02-0.07 while otherwise walking fine), after walk_gait_gate+k_step_event (6/6 FAIL, rare-token-swing dodge) and walk_duty_gate (every provenance x every dose FAIL, satisfied by planted/vibrating stance) both closed end-to-end. New mechanism reward.walk_swing_gate prices a MIN-over-legs trailing-window COUNT of qualifying real swings (same stride-filtered swing definition walk_gait_gate used, but a hard count-per-window floor instead of a recency-decay score) -- a leg that only ever chatters/plants (walk_duty_gate's exploit) completes zero qualifying swings by construction, and a leg that steps only once every several seconds (walk_gait_gate's exploit) cannot clear a >=2-per-4s-window count bar the way it cleared a >=1-per-4s-recency floor. Bank-proved this cycle (test_walk_swing_gate_* in test_task_semantics.py, 4/4 green: default-off bit-exact, honest six-leg gait keeps ~full income, one permanently-parked leg collapses income, and a fully-frozen six-leg stance -- walk_duty_gate's own closing exploit -- scores swing_gate_min 0). This FRESH-provenance arm bakes the price in from the SAME lightly-trained 2M base_s0_c1.zip checkpoint dgfresh used (before the leg-4 habit entrenches), mirroring dgfresh's own design (repair before the habit forms rather than after).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY (2M): PASS if walk_startjitter/det harness leg duty on the historically-marginal leg comes back majority-healthy (no leg chronically <=0.10 duty in >=4/6 episodes) with 0 new falls and gait_valid staying majority-valid on the other 3 modes (matching or beating the undosed s0c1 twin's own 6/6,6/6,6/6). FAIL - MECHANISM if the same leg-4 (or another) chronic near-zero-duty pattern persists unchanged vs the undosed twin (same fingerprint the closed walk_duty_gate/noise levers left behind) OR if walk_swing_gate_factor saturates near 1.0 despite a visibly parked leg (the gamed-completion-score failure mode). Either result closes or advances the per-leg-utilization mechanism search -- informative regardless.

