# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-transwin-c1-fix1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-07T19:30:10+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-transwin-c1

**wandb_id**: vmczkhfx

**hypothesis**: Plain English: the 09-07 19:03 UTC accounting review (fb_20260907T185803_c8af66) found the original transwin-c1 canary trained under a touchdown-charge bug (charged airborne swing-approach motion as loaded skid) and a window-aging bug (a low-force contact gap could keep the touchdown countdown / liftoff ring buffer alive far past the configured 3-tick window) -- both fixed this cycle (transition_window_touchdown/_tick/_liftoff extracted to plain functions, 6 new synthetic state-machine regressions green, 13/13 total). Byte-identical recipe/dose to the original transwin-c1 (k_walk_transition_slip=35.0, deadband 0.015, cap 0.25, td_ticks=3, lo_ticks=3, contact_n=2.0) warm from the same frozen cont40m champion -- single lever is the corrected code, nothing else changed. Answers whether the accounting bug materially affected the mechanism's read (compare against the original transwin-c1's own pending result) so no causal verdict on this mechanism relies on the known-flawed timing.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (same tier/criteria as the original transwin-c1: no skill-acquisition or behavior-class verdict at 2M). PASS if wandb_history shows env/reward_walk_transition_slip trending down or stable while reward_walk/reward_walk_prog stay flat-to-rising, plus a fresh own-pod gate re-eval (DR-0, walk+walk_startjitter, det+sto, n>=24) reads 0 falls / gait_valid all-clear with no new leg-sacrifice vs the 22/24 baseline. SCIENTIFIC comparison (not this run's own PASS/FAIL): once BOTH this run and the original transwin-c1 have landed, read env/reward_walk_transition_slip, walk_transition_td_events, walk_transition_lo_events, and held-out slip/m side by side -- if within noise of each other the attribution bug was immaterial in practice; if they diverge, only THIS (fixed) run's read may be used for any causal verdict on the mechanism.

**verdict**: CANARY FAIL - MECHANISM: same k_walk_transition_slip mechanism after the 19:39 accounting fix (no longer charges airborne-approach motion as skid; TD/LO ring buffer now ages every tick not just force-qualified ones). LAUNCH NOTE CORRECTION: this run's own notes claim it warms from 'the same frozen cont40m champion' as a parallel mirror of the buggy transwin-c1, but its actual --init-from is the buggy transwin-c1's OWN 2M checkpoint -- it is a 2M CONTINUATION (4M cumulative from cont40m: 2M buggy-accounting + 2M fixed-accounting), not an independent A/B control. Flagging for the record; it does not change the read. vs its true predecessor (transwin-c1, buggy) slip/m medians move [walk/det 4.88->5.17, walk/sto 5.08->5.41, startjitter/det 4.85->4.59, startjitter/sto 5.46->5.94] -- mixed, no measurable improvement (still flat-to-worse vs the 5.065 baseline too). reward_walk_transition_slip charge magnitude dropped as expected from the bug fix (-4.17..-4.51 -> -3.40..-3.71, smaller charge = less over-billing) but slip itself did not move, confirming the accounting bugs were NOT masking a real effect -- the mechanism genuinely does not move slip, fixed or buggy. 0 falls/24, gait_valid 5-6/6 every mode, walk_contact_meaningful_feet ~2.8-3.1/6 (normal), roll/height normal, reward_walk still rising (0.81->0.97). Confirms and closes the transwin-c1 read above; both accounting states of this mechanism sit at the same ~5-6/m floor as the whole direct-slip-pricing family.

