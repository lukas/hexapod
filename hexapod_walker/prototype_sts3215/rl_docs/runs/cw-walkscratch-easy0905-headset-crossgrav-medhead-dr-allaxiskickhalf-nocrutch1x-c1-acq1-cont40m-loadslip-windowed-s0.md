# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-loadslip-windowed-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T22:19:37+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-loadslip-c1

**wandb_id**: ys1vms28

**hypothesis**: Plain English: item(4)'s slip gap survived 3 prior reward-shaping attempts (episode-cumulative loadslip gate+excess FAIL, foot-slip-tangent charge at k=35 FAIL, at k=3 FAIL) that all shared one root property named by the loadslip-c1 FAIL verdict itself: the episode-CUMULATIVE slip/progress ratio averages the whole episode's history into one number, diluting a late skate behind an early clean stretch (measured: env/walk_loadslip_ratio bounced 6.28->7.88->7.11->6.87 with no clean trend). Does replacing that cumulative ratio with a windowed (EMA, tau=1.0s) rate ratio -- same ok=3.0/max=8.0/k=10.0 dose, ONLY the accounting changes -- give PPO a responsive-enough signal to actually reduce this already-clean-walking champion's slip/m, without reopening falls or leg-sacrifice? New mechanism reward.walk_loadslip_window_s (walk_task.py) bank-proven this cycle: bit-exact when 0 (test_loadslip_window_default_off_is_bit_exact), reacts >5x faster than a deliberately-diluted cumulative ratio to an injected slip burst (test_loadslip_window_ratio_reacts_faster_than_cumulative), and reproduces every safety property the FAILED cumulative candidate needed (skate-worst-outcome, widens gait-vs-skate margin, gait income positive -- WALKCURR_ITEM4_LOADSLIP_WINDOWED_OVERRIDES, 5/5 new tests green, 33/33 item4 bank green overall).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/CONTINUE if the fresh held-out gate (walk+walk_startjitter, det+sto, n=24, DR-0, same eval_joystick_gate.aggregate_gate arithmetic as the champion's own training-diet baseline) shows slip/m median MEASURABLY lower than the 5.065 baseline (not another ~4-8% wiggle within the 3.8-12.1 episode-to-episode spread) with gait_valid/falls unchanged (0 falls, no new chronic leg). FAIL-STILL-STUCK if slip barely moves despite the windowed accounting (would close the whole reward-shaping-for-slip question on this champion for good -- 4 independently-designed mechanisms tried). FAIL-EXPLOIT if gait_valid drops, a leg is newly sacrificed, or falls appear (would show the sharper windowed price destabilizes rather than shapes).

