# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS (own scope) - joint pending flatonly-read

**created**: 2026-09-02T16:46:33+00:00

**pod**: hexapod-mjx-train-6

**steps**: 38000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi

**wandb_id**: ek429vf3

**hypothesis**: Plain English: the 2M canary just showed that annealing the WALK core's action-noise std down (not just stance's) makes the policy's stochastic (real-world-like) behavior match its deterministic behavior almost exactly, instead of the old recipe where stochastic walking reached only 5-8% of commanded progress. Does that fix SURVIVE and COMPOUND at full acquisition scale (38M steps, matching cap29-acq1's own budget) -- i.e. does the cap29-acq1 DONE-gate session read's direction_err_med/slip_per_m_med (55.5-61.1 deg / 3.45-3.46, worse than the cap29 zero-training baseline of 46.8/3.09) actually IMPROVE once sto-mode stops being near-non-functional, or does the steering gap persist as a separate defect once the std confound is removed?

**gate**: flat-only eval_done_gate_session (ops.sh donegatecmd flat=1) n>=12 det+sto DR-0+own-DR, read against the SAME cap29-acq1{,-s1} baseline it replaces: zero falls must hold (bar already met at 32/32 zero-term by cap29-acq1 and durctrl-canary); PASS if direction_err_med and slip_per_m_med drop at or below the cap29 zero-training baseline (46.8 deg / 3.09) AND the canary-scale purewalk det/sto convergence (this cycle's finding) replicates at session scale (sto progress within ~20% of det, not the old 5-8%); PARTIAL if falls+sto-convergence hold but steering does not improve (confirms steering is a separate, still-open defect per STATUS item 2); FAIL if sto-mode regresses back toward the old 5-8%-of-det pattern at this scale (would mean the fix doesn't survive longer training) or if terminations return.

**verdict**: Training finished clean at 38.0M (ep_rew_mean 2915, reward quarters [626,2447,2898,2987] rising then flattening, std normal). The auto prestage SESSION/MIXEDSESSION harness errored rc=1 'obs contract mismatch with the deployed session env' -- this is the SAME expected-broken result every arm in this exotic dual-core-obs lineage has hit since 09-01 (not a new defect, not evidence either way on the actual gate). Per STATUS Next item 0, dispatched the track's own flat-only eval_done_gate_session (n=32, matching the cap29-acq1 baseline read's own n) on-pod (train-6, code synced to c70333b) instead, backgrounded and registered via evalpending -- this is the acq-scale read of whether the stdwalklo-hi walk-core log_std anneal (CANARY PASS at 2M canary scale: sto/det progress_ratio converged 0.28-0.32 vs 0.32-0.36) survives to full 38M budget and whether direction_err_med/slip_per_m_med drop to/below the cap29-acq1 baseline (46.8 deg/3.09). Not yet landed; joint verdict with the -s1 seed once both flatonly reads are in.

