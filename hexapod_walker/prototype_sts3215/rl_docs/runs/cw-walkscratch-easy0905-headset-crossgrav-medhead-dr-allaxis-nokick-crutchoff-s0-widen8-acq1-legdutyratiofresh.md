# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8-acq1-legdutyratiofresh

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FINISHED

**created**: 2026-09-08T00:13:29+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8-acq1

**wandb_id**: x6d04iaz

**hypothesis**: PLAIN ENGLISH: a brand-new per-leg reward charge that ADDS a penalty (never multiplies existing walking income, and never ends the episode) whenever one leg's ground-contact time falls too far below its five teammates' own average might finally stop this champion's chronic front-pair (legs 0/5) leg-sacrifice habit, where 19 prior fixes (11 income-multiplying reward gates + 8 hard safety-terminations) all failed. FRESH provenance (same seed/init-from/8-way-heading recipe as the undosed widen8-acq1 ACQ-FAIL baseline, charge present from step 0, no termination cfg-sets carried over). Calibrated dose: reward.walk_leg_duty_ratio_charge=150 with target=0.30 (the passing-episode population's own p10 worst-leg peer-relative duty ratio, STATUS.md 2026-09-07 ~23:4x) -- bank-proved this cycle (test_task_semantics.py, 14 new/adjacent tests green) to leave a scripted honest six-leg gait's return bit-exact untouched while flipping BOTH a hard flag-leg cheat's and a soft/marginal (~10% duty) starvation cheat's full-episode return decisively below the honest gait's own return, the exact ordering-flip property every prior mechanism's own closure note flagged as never demonstrated. PREDICTION IF TRUE: the previously-chronic leg recovers to a genuinely-used duty (peer-relative ratio clearing ~0.22-0.30) in the majority of held-out episodes, gait_valid improves materially toward the pre-widen8 clean band (>=18/24), 0 new falls. PREDICTION IF FALSE: the same front-pair sacrifice persists at the same fingerprint regardless (either training-time noise satisfies the EMA without moving the deterministic policy mean the way it did for every closed multiplicative gate, or the policy simply eats the ongoing charge as an ambient cost the way the termination class was paid off). STRONGEST ALTERNATIVE: the redundant middle-pair's torque/energy asymmetry is a structural property of the gait geometry that no per-tick reward design (price, termination, or ratio-target alike) can out-compete -- only a structural/architectural change (symmetry-breaking init, curriculum, or accepting the pathology as closed) would then remain.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS: previously-chronic leg's held-out duty_cycle recovers to a genuinely-used level (peer-relative ratio >=0.22, the calibrated separation threshold) in the majority of episodes across all 4 eval modes, gait_valid materially improves vs the undosed s0-widen8-acq1 baseline (target >=18/24, matching the pre-widen8 clean band), 0 new falls. CONTINUE (08-21 ruling): reward rising AND gait_valid trending up but short of 18/24 -- fund a longer acquisition continuation, not a new mechanism variant. FAIL: the same front-pair (legs 0/5) chronic sacrifice persists at the same or a similar fingerprint regardless of whether the charge is measurably firing in wandb_history.csv -- closes the additive-price-target shape too, alongside the already-closed multiplicative-gate and termination shapes.

