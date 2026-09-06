# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-loadslip-windowed-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-06T22:21:53+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-loadslip-c1

**wandb_id**: eglh8e51

**hypothesis**: Same as -s0 (2nd independent seed for this new mechanism): does a windowed (EMA, tau=1.0s) loadslip ratio -- same ok=3.0/max=8.0/k=10.0 dose as the FAILED episode-cumulative candidate, only the accounting changes -- give PPO a responsive-enough signal to reduce this champion's slip/m without reopening falls/leg-sacrifice. Bank: WALKCURR_ITEM4_LOADSLIP_WINDOWED_OVERRIDES + test_loadslip_window_* (test_walk_fastprof_mdp.py), 33/33 item4 bank green.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same bar as -s0: PASS/CONTINUE if slip/m median measurably lower than the 5.065 baseline with gait_valid/falls unchanged; FAIL-STILL-STUCK if slip barely moves; FAIL-EXPLOIT if gait_valid/falls regress. Read together with -s0 as a 2-seed pair, not independently.

**verdict**: CANARY FAIL - MECHANISM: FAIL-STILL-STUCK, same finding as the matched -s0 seed (see its verdict for the full mechanism/design writeup, not repeated here). Pooled median slip across all 24 episodes is 5.05 vs the champion's 5.065 baseline -- essentially unchanged (well inside the 3.8-12.1 episode spread), not a measurable reduction. No regression: gait_valid 22/24, same leg (2) flagged in the same 2 episodes (walk/sto ep4, walk_startjitter/det ep1) with the same duty-cycle fingerprint as -s0 and the champion's own baseline -- reproduces the exact same pattern across an independent seed, not noise. 0/24 falls. This confirms n=2 on the windowed-EMA loadslip mechanism's null result and closes reward-shaping-for-slip on this champion (4 mechanisms tried, all null). Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_allaxiskickhalf_nocrutch1x_c1_acq1_cont40m_loadslip_windowed_s1_gate/report.json, W&B eglh8e51.

