# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-overspeedq1-cont8m-transwin-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-07T18:52:47+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-overspeedq1-cont8m

**wandb_id**: si7rindk

**hypothesis**: Plain English: the overspeed-financed-slip hypothesis's own falsification (09-07 ~18:0x: pricing overspeed alone does NOT unlock the windowed-loadslip charge, closing the direct-slip-reward-pricing family 5/5) leaves the phase-targeted mechanism as the one untried repair -- does it work BETTER on the already speed-controlled descendant (v_along held near 0.074-0.083, so the denominator-growth escape is already closed) than on the raw frozen champion (the sibling -transwin-c1 canary, same cycle)? Single addition vs the byte-identical overspeedq1-cont8m recipe (which already carries reward.walk_freeprog_overspeed_charge=1.0 baked in, --init-from-source so this warms from ITS OWN finished 8M checkpoint, not the earlier 2M canary): arm reward.k_walk_transition_slip=35.0 at the same dose/deadband/cap as the sibling canary, nothing else changed. Bank-proven (test_task_semantics.py, 7/7 new tests green, same evidence as the sibling canary -- this run adds no new reward interaction the bank does not already cover, since walk_freeprog_overspeed_charge and k_walk_transition_slip touch disjoint reward channels).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, not a skill-acquisition or behavior-class verdict. PASS if wandb_history shows the transition-slip channel trending down/stable while reward_walk/reward_walk_prog and env/v_along_cmd_m_s stay flat-to-rising (speed must not spike back up -- that would reopen the denominator-growth escape this checkpoint was built to close), AND a fresh own-pod gate re-eval (DR-0, walk+walk_startjitter, det+sto, n>=24) reads 0 falls / gait_valid all-clear with slip/m median measurably lower than this checkpoint's own 5.82-5.90 baseline (not another ~4% wiggle) AND no belly-flop/crouch/reduced-contact exploit. FAIL-STILL-STUCK if slip barely moves -- read together with the sibling -transwin-c1 canary to see whether speed-control helps or is irrelevant to this mechanism. FAIL-EXPLOIT if speed collapses back down (re-opening the ratio-denominator escape) or a crouch/reduced-contact pattern appears.

**verdict**: CANARY FAIL - MECHANISM: same k_walk_transition_slip touchdown/liftoff charge composed onto the speed-controlled overspeedq1-cont8m lineage (that checkpoint's own baseline slip/m: walk/det 5.82, walk/sto 6.24, startjitter/det 5.72, startjitter/sto 6.81, from its own pre-mechanism gate report). This run's slip/m medians [5.55, 6.07, 5.97, 6.55] are flat vs that baseline (all 4 cells within +/-5%, no measurable reduction) despite env/reward_walk rising 0.78->0.91 and the transition-slip charge growing more negative (-4.15->-4.42) through training. 0 falls/24, gait_valid 5-6/6 every mode, no crouch/exploit (contact_meaningful_feet normal, roll/height normal). Same FAIL-STILL-STUCK shape as the plain-cont40m arm above, now reproduced on a 2nd, independently speed-modified lineage -- the mechanism does not move slip regardless of the underlying speed regime. See -fix1 below for the corrected-accounting continuation.

