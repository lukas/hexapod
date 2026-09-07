# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-overspeedq1-cont8m-transwin-c1-fix1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-07T19:33:56+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-overspeedq1-cont8m-transwin-c1

**wandb_id**: o8pi2qe6

**hypothesis**: Plain English: same accounting-fix retest as the -transwin-c1-fix1 sibling, but on the speed-controlled overspeedq1-cont8m checkpoint (the sibling the original review flagged by name). Byte-identical recipe/dose to the original ...-overspeedq1-cont8m-transwin-c1 canary (k_walk_transition_slip=35.0, deadband 0.015, cap 0.25, td_ticks=3, lo_ticks=3, contact_n=2.0, inherited k_over=1.0), warm from the same overspeedq1-cont8m checkpoint -- single lever is the corrected code (transition_window_touchdown/_tick/_liftoff, 09-07 19:2x accounting fix, 13/13 bank tests green), nothing else changed.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (same tier/criteria as the original). PASS if wandb_history shows env/reward_walk_transition_slip trending down or stable while reward_walk/reward_walk_prog stay flat-to-rising, plus a fresh own-pod gate re-eval (DR-0, walk+walk_startjitter, det+sto, n>=24) reads 0 falls / gait_valid all-clear vs the parent's own baseline. SCIENTIFIC comparison (not this run's own PASS/FAIL): once both this run and the original ...-overspeedq1-cont8m-transwin-c1 have landed, compare env/reward_walk_transition_slip / walk_transition_td_events / walk_transition_lo_events / held-out slip/m side by side -- if within noise the attribution bug was immaterial in practice; if they diverge, only THIS (fixed) run's read may be used for any causal verdict.

**verdict**: CANARY FAIL - MECHANISM: corrected-accounting continuation of the overspeedq1-cont8m-transwin-c1 arm above (same launch-note mismatch as the plain-lineage -fix1: --init-from is the buggy transwin-c1 checkpoint, a 2M continuation not a parallel mirror -- flagged, does not change the read). vs its true predecessor slip/m medians move [walk/det 5.55->6.08, walk/sto 6.07->5.70, startjitter/det 5.97->6.01, startjitter/sto 6.55->6.34] -- mixed, no measurable improvement, still flat vs the lineage's own 5.72-6.81 pre-mechanism baseline. reward_walk still rising (0.76->0.92), charge magnitude smaller post-fix (-3.30->-3.63) but slip unmoved -- confirms (2nd lineage) the accounting bugs were not masking a real effect. 0 falls/24, gait_valid 5-6/6, no exploit. CLOSES the transition-window slip-charge mechanism family: 4/4 arms (plain + speed-controlled lineage, buggy + fixed accounting) converge on the same ~5-6/m floor as the prior direct-slip-charge family (solo doses + lswin interaction) -- 9 total pricing arms now at this ceiling. Per every one of these runs' own pre-registered gate text: escalate past reward-shaping to a structural (non-reward, e.g. contact/friction-model fidelity) fix, not another charge design.

