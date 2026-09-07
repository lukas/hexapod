# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-transwin-c1-fix1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T19:30:10+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-transwin-c1

**wandb_id**: vmczkhfx

**hypothesis**: Plain English: the 09-07 19:03 UTC accounting review (fb_20260907T185803_c8af66) found the original transwin-c1 canary trained under a touchdown-charge bug (charged airborne swing-approach motion as loaded skid) and a window-aging bug (a low-force contact gap could keep the touchdown countdown / liftoff ring buffer alive far past the configured 3-tick window) -- both fixed this cycle (transition_window_touchdown/_tick/_liftoff extracted to plain functions, 6 new synthetic state-machine regressions green, 13/13 total). Byte-identical recipe/dose to the original transwin-c1 (k_walk_transition_slip=35.0, deadband 0.015, cap 0.25, td_ticks=3, lo_ticks=3, contact_n=2.0) warm from the same frozen cont40m champion -- single lever is the corrected code, nothing else changed. Answers whether the accounting bug materially affected the mechanism's read (compare against the original transwin-c1's own pending result) so no causal verdict on this mechanism relies on the known-flawed timing.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (same tier/criteria as the original transwin-c1: no skill-acquisition or behavior-class verdict at 2M). PASS if wandb_history shows env/reward_walk_transition_slip trending down or stable while reward_walk/reward_walk_prog stay flat-to-rising, plus a fresh own-pod gate re-eval (DR-0, walk+walk_startjitter, det+sto, n>=24) reads 0 falls / gait_valid all-clear with no new leg-sacrifice vs the 22/24 baseline. SCIENTIFIC comparison (not this run's own PASS/FAIL): once BOTH this run and the original transwin-c1 have landed, read env/reward_walk_transition_slip, walk_transition_td_events, walk_transition_lo_events, and held-out slip/m side by side -- if within noise of each other the attribution bug was immaterial in practice; if they diverge, only THIS (fixed) run's read may be used for any causal verdict on the mechanism.

