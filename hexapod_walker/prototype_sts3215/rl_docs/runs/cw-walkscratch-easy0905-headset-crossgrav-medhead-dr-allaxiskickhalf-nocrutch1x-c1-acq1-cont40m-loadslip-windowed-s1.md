# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-loadslip-windowed-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T22:21:53+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-loadslip-c1

**wandb_id**: eglh8e51

**hypothesis**: Same as -s0 (2nd independent seed for this new mechanism): does a windowed (EMA, tau=1.0s) loadslip ratio -- same ok=3.0/max=8.0/k=10.0 dose as the FAILED episode-cumulative candidate, only the accounting changes -- give PPO a responsive-enough signal to reduce this champion's slip/m without reopening falls/leg-sacrifice. Bank: WALKCURR_ITEM4_LOADSLIP_WINDOWED_OVERRIDES + test_loadslip_window_* (test_walk_fastprof_mdp.py), 33/33 item4 bank green.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same bar as -s0: PASS/CONTINUE if slip/m median measurably lower than the 5.065 baseline with gait_valid/falls unchanged; FAIL-STILL-STUCK if slip barely moves; FAIL-EXPLOIT if gait_valid/falls regress. Read together with -s0 as a 2-seed pair, not independently.

