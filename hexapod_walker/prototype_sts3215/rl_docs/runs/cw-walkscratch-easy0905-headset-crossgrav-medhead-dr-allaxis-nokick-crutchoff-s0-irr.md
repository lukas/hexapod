# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-irr

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: KILLED

**created**: 2026-09-07T08:44:34+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-acq1

**wandb_id**: ebgn9rv9

**hypothesis**: Plain English: completes the irr-timing realism-rung trio (s1-irr/s2-irr both launched this cycle by a concurrent cycle) on the crutch-off full-DR composite's remaining seed. The irregular command-timing axis (jittering the fixed 6s heading-resample interval by +-50% instead of a clean metronome) already validated composable at 1g without full DR (medhead-irrfwd-c1-acq1 ACQ PASS + cont40m HOLDS); this is the same single-axis test (NOT stacked with widen8, to keep attribution clean) on s0's own ACQ-passed 40M crutch-off checkpoint. Prediction-if-true (composable, matching the s1/s2 twins if they pass): 0 falls, gait_valid majority (>=18/24) on the same 5-heading medium set with jittered timing. Prediction-if-false: falls or a chronic single-leg sacrifice appear specifically under irregular re-commands -- would make s0 the odd one out, worth a dig-in given s0 is the seed whose crutch-ON push fragility only ever appeared at 40M depth, not 2M.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY (2M): held-out gate on own cfg (5-heading medium set with jittered resample timing, det+sto, walk+walk_startjitter, 24 eps). PASS if 0 falls/terminations AND gait_valid >=18/24. FAIL if any fall or chronic (<0.10-duty every episode) single-leg sacrifice.

**verdict**: SEED-PRUNED (mechanical, operator rule 2026-09-07): post-burn-in stagnation: reward EMA slope -5.690398/window (negligible) and no behavioral improvement across ['v_along', 'ep_len'] (regressing: none). Evidence: {"budget_steps": 40000000, "last_step": 42500000, "windows_used": [37500000, 40000000, 42500000], "reward_ema_last3": [1759.9321, 1764.0177, 1748.5513], "reward_slope_per_window": -5.690398, "reward_negligible_below": 3.515001, "v_along_last3": [0.0868, 0.0865, 0.088], "ep_len_last3": [1985.744, 1976.346, 1988.59], "behavior_improving": [], "behavior_regressing": [], "burn_in_steps": 10000000}. Checkpoint and logs retained; only the training job was stopped.

