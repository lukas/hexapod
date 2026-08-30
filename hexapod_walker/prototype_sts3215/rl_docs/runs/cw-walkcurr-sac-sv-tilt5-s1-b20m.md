# cw-walkcurr-sac-sv-tilt5-s1-b20m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-30T04:23:42+00:00

**pod**: hexapod-mjx-train-7

**steps**: 20000000

**parent**: cw-walkcurr-sac-sv-tilt5-s1

**wandb_id**: q2rze6lz

**hypothesis**: Plain English: does SAC seed-1's tilt5 anti-tilt dose (k_roll=k_pitch=5.0) just need more training time to convert its partial stepping signal into a real pass? Operator-ordered overnight population sweep (MCP operator lane 20260830T035139Z, Lukas: use the idle fleet, bigger budget is fine, branch many rollouts and select honestly) -- the SAC-branch analogue of the same-order decleg/central 100M PPO wave already running. Byte-identical config/diet/seed/algo to cw-walkcurr-sac-sv-tilt5-s1 (FAIL at 2M: gait_valid 5/6, fwd 0.055m det median, fall rate still 24/24). SAC unconditionally refuses --init-from (train_ppo_mjx.py's own restriction), so the ONLY lever is raw budget 2M->20M (10x); under this stack's fixed-seed determinism this reproduces tilt5-s1's own first 2M trajectory exactly and then trains 18M further past where it stopped (same workaround precedent as sac-sv-s1-budget10m). Prediction-if-true: fall rate drops off 24/24 and forward_dist_m median clears ~0.06m somewhere in the extra 18M, roll_peak staying near the tilt5 baseline (~10deg) rather than regressing to tilt10's over-suppressed near-zero speed. Prediction-if-false: fall rate/roll_peak/forward_dist stay pinned at the 2M numbers through 20M with flat reward -- closes the raw-budget lever for SAC at this dose, same fork as the PPO siblings (anti-freeze/balance pretrain curriculum, STATUS candidate 1).

**gate**: Rung-1 C-env det+sto fixed-forward panel (n>=6 each) at 20M: PASS needs progress_ratio med>=0.35, slip/m<=3.0, gait_valid>=4/6, falls (tilt_pitch/tilt_roll term) on <=1/6 det episodes. PARTIAL/continue (08-21 ruling): fall rate or forward_dist improving vs tilt5-s1's own 2M baseline (24/24 falls, fwd med 0.055m det/0.044m sto) even short of the full bar, litmus = env/walk_speed off the 2M ceiling with stable/rising ep_len and no new failure-mode surge. FAIL: fall rate/forward_dist/roll_peak unchanged at the 2M numbers through 20M with flat reward -- closes the raw-budget SAC lever at this dose.

**verdict**: 10x-budget SAC continuation of the tilt5 dose (2M->20M, same seed 1) does NOT escape the fall-then-topple ceiling -- closes the raw-budget-alone SAC lever at this dose/seed per the run's own pre-registered FAIL text. Evidence: DR-0 gate n=24, ALL 24 episodes terminate tilt_pitch/tilt_roll (24/24 falls, unchanged from the 2M baseline's 24/24), fwd med 0.06-0.07m across all 4 sub-panels vs baseline's 0.055m det/0.044m sto -- within noise, no clear escape. eval/walk/survived_frac is 0.0 at EVERY logged eval checkpoint from 1M to 19M (never once survives) and eval/walk/speed_m_s actually DECLINES over the back half of the run (0.079 near 2M -> 0.061 at 19M). reward quarters [147.0,149.6,151.4,148.4]: peaks Q3 then drops Q4, flat/non-rising overall -- not an 08-21 continue case. Frame strip (walk_det_0_sheet.png) shows near-zero net checkerboard translation across the full 8-frame episode and a visibly rolled/splayed posture in the closing frames, consistent with the roll_class=fell/TERM tilt_pitch label. This is 1 of the operator-ordered 4-arm SAC tilt5-20M population (STATUS pre-committed read); s2 finished this cycle too but is being triaged elsewhere -- s3/s4 still training. Per STATUS's own pre-registered next step: if all four land FAIL, that closes lever (iv) and the track's entire operator-named non-BC ladder, requiring a fresh operator note (not a same-cycle action off one seed alone).

