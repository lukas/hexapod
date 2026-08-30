# cw-walkcurr-sac-sv-tilt5-s1-b20m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-30T04:23:42+00:00

**pod**: hexapod-mjx-train-7

**steps**: 20000000

**parent**: cw-walkcurr-sac-sv-tilt5-s1

**wandb_id**: q2rze6lz

**hypothesis**: Plain English: does SAC seed-1's tilt5 anti-tilt dose (k_roll=k_pitch=5.0) just need more training time to convert its partial stepping signal into a real pass? Operator-ordered overnight population sweep (MCP operator lane 20260830T035139Z, Lukas: use the idle fleet, bigger budget is fine, branch many rollouts and select honestly) -- the SAC-branch analogue of the same-order decleg/central 100M PPO wave already running. Byte-identical config/diet/seed/algo to cw-walkcurr-sac-sv-tilt5-s1 (FAIL at 2M: gait_valid 5/6, fwd 0.055m det median, fall rate still 24/24). SAC unconditionally refuses --init-from (train_ppo_mjx.py's own restriction), so the ONLY lever is raw budget 2M->20M (10x); under this stack's fixed-seed determinism this reproduces tilt5-s1's own first 2M trajectory exactly and then trains 18M further past where it stopped (same workaround precedent as sac-sv-s1-budget10m). Prediction-if-true: fall rate drops off 24/24 and forward_dist_m median clears ~0.06m somewhere in the extra 18M, roll_peak staying near the tilt5 baseline (~10deg) rather than regressing to tilt10's over-suppressed near-zero speed. Prediction-if-false: fall rate/roll_peak/forward_dist stay pinned at the 2M numbers through 20M with flat reward -- closes the raw-budget lever for SAC at this dose, same fork as the PPO siblings (anti-freeze/balance pretrain curriculum, STATUS candidate 1).

**gate**: Rung-1 C-env det+sto fixed-forward panel (n>=6 each) at 20M: PASS needs progress_ratio med>=0.35, slip/m<=3.0, gait_valid>=4/6, falls (tilt_pitch/tilt_roll term) on <=1/6 det episodes. PARTIAL/continue (08-21 ruling): fall rate or forward_dist improving vs tilt5-s1's own 2M baseline (24/24 falls, fwd med 0.055m det/0.044m sto) even short of the full bar, litmus = env/walk_speed off the 2M ceiling with stable/rising ep_len and no new failure-mode surge. FAIL: fall rate/forward_dist/roll_peak unchanged at the 2M numbers through 20M with flat reward -- closes the raw-budget SAC lever at this dose.

