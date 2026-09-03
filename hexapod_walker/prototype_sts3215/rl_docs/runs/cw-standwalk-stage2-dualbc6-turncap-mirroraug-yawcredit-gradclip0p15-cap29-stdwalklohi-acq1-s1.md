# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-acq1-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-02T16:49:38+00:00

**pod**: hexapod-mjx-train-7

**steps**: 38000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi-s1

**wandb_id**: bwucn3zw

**hypothesis**: Plain English: seed-1 companion to the stdwalklohi-acq1 launch. The 2M canary showed annealing the WALK core's action-noise std down (not just stance's) makes stochastic (real-world-like) behavior match deterministic behavior almost exactly, instead of the old recipe where stochastic walking reached only 5-8% of commanded progress. Does that fix SURVIVE and COMPOUND at full acquisition scale (38M steps, matching cap29-acq1's own budget) on a second seed -- i.e. does the DONE-gate session read's direction_err_med/slip_per_m_med actually improve once sto-mode stops being near-non-functional, replicated across seeds?

**gate**: flat-only eval_done_gate_session (ops.sh donegatecmd flat=1) n>=12 det+sto DR-0+own-DR, read against the SAME cap29-acq1{,-s1} baseline it replaces: zero falls must hold (bar already met at 32/32 zero-term by cap29-acq1 and durctrl-canary); PASS if direction_err_med and slip_per_m_med drop at or below the cap29 zero-training baseline (46.8 deg / 3.09) AND the canary-scale purewalk det/sto convergence (this cycle's finding) replicates at session scale (sto progress within ~20% of det, not the old 5-8%); PARTIAL if falls+sto-convergence hold but steering does not improve (confirms steering is a separate, still-open defect per STATUS item 2); FAIL if sto-mode regresses back toward the old 5-8%-of-det pattern at this scale or if terminations return.

**verdict**: Seed-1 twin of stdwalklohi-acq1, same flat-only eval_done_gate_session read (n=128 ep, det+sto x DR0+ownDR, on-pod train-7): direction_err_med 43.6deg and slip_per_m_med 2.939, BOTH below the cap29 zero-training baseline (46.8deg/3.09) -- clears this arm's own pre-registered PASS bar. sto/det progress_ratio convergence replicates (dr0 sto/det 0.3665/0.341=107%, owndr 0.3515/0.3635=97%), confirming seed0's finding is not a seed-specific fluke. Zero falls across all 128 episodes, gait_valid_frac=1.0. Joint PASS with seed0 closes STATUS item 0 with 2-seed replication. Track DONE gate still open: dir_err (43.6) just misses the track's tighter ~40deg cap and slip (2.939) sits marginally over the 2.9 hard cap by generic soft-gate accounting -- steering (STATUS item 1) is the next open item, not a regression from this run.

