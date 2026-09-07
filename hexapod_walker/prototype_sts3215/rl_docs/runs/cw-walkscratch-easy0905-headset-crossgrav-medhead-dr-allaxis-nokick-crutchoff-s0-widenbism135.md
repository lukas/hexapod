# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbism135

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: KILLED

**created**: 2026-09-07T10:37:00+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8

**wandb_id**: c3hqpdus

**hypothesis**: Plain English: same bisection as arm 1 (see widenbis135), arm 2/3: add ONLY -135deg (the mirror rear-diagonal heading) to the ACQ-passed 5-way base, same s0 checkpoint/seed/budget/recipe. Isolates whether the LEFT rear-diagonal alone (vs. the right one or straight-back) drives the front-pair[0,5] chronic-sacrifice shortcut widen8-acq1 showed 3/3. Prediction-if-true: chronic front-pair (or similar) sacrifice reappears by 40M. Prediction-if-false: panel stays clean near s0-acq1's 21/24 baseline -- -135deg alone is not sufficient.

**gate**: PASS (heading exonerated) if 0 falls/24 AND gait_valid>=19/24 AND no chronic single-leg/pair sacrifice absent from s0-acq1's own clean panel. FAIL (heading implicated) if a chronic front-pair[0,5]-style (or any new persistent single-leg) sacrifice reappears, matching widen8-acq1's fingerprint.

**verdict**: SEED-PRUNED (mechanical, operator rule 2026-09-07): post-burn-in stagnation: reward EMA slope -106.572789/window (negligible) and no behavioral improvement across ['v_along', 'ep_len', 'fall_rate'] (regressing: ['ep_len', 'fall_rate']). Evidence: {"budget_steps": 40000000, "last_step": 42500000, "windows_used": [37500000, 40000000, 42500000], "reward_ema_last3": [1375.9003, 1285.1957, 1162.7547], "reward_slope_per_window": -106.572789, "reward_negligible_below": 2.549234, "v_along_last3": [0.0792, 0.0795, 0.0786], "ep_len_last3": [1970.742, 1925.944, 1930.77], "fall_rate_last3": [0.0607, 0.0702, 0.0683], "behavior_improving": [], "behavior_regressing": ["ep_len", "fall_rate"], "burn_in_steps": 10000000}. Checkpoint and logs retained; only the training job was stopped.

