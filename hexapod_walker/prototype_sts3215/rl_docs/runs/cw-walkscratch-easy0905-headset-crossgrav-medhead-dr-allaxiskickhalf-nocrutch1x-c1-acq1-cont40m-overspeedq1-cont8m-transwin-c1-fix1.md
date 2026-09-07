# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-overspeedq1-cont8m-transwin-c1-fix1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T19:33:56+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-overspeedq1-cont8m-transwin-c1

**wandb_id**: o8pi2qe6

**hypothesis**: Plain English: same accounting-fix retest as the -transwin-c1-fix1 sibling, but on the speed-controlled overspeedq1-cont8m checkpoint (the sibling the original review flagged by name). Byte-identical recipe/dose to the original ...-overspeedq1-cont8m-transwin-c1 canary (k_walk_transition_slip=35.0, deadband 0.015, cap 0.25, td_ticks=3, lo_ticks=3, contact_n=2.0, inherited k_over=1.0), warm from the same overspeedq1-cont8m checkpoint -- single lever is the corrected code (transition_window_touchdown/_tick/_liftoff, 09-07 19:2x accounting fix, 13/13 bank tests green), nothing else changed.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (same tier/criteria as the original). PASS if wandb_history shows env/reward_walk_transition_slip trending down or stable while reward_walk/reward_walk_prog stay flat-to-rising, plus a fresh own-pod gate re-eval (DR-0, walk+walk_startjitter, det+sto, n>=24) reads 0 falls / gait_valid all-clear vs the parent's own baseline. SCIENTIFIC comparison (not this run's own PASS/FAIL): once both this run and the original ...-overspeedq1-cont8m-transwin-c1 have landed, compare env/reward_walk_transition_slip / walk_transition_td_events / walk_transition_lo_events / held-out slip/m side by side -- if within noise the attribution bug was immaterial in practice; if they diverge, only THIS (fixed) run's read may be used for any causal verdict.

