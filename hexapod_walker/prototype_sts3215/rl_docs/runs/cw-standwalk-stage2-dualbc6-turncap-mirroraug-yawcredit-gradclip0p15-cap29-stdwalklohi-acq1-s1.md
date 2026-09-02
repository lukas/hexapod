# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-acq1-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS (own scope) - joint pending flatonly-read

**created**: 2026-09-02T16:49:38+00:00

**pod**: hexapod-mjx-train-7

**steps**: 38000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi-s1

**wandb_id**: bwucn3zw

**hypothesis**: Plain English: seed-1 companion to the stdwalklohi-acq1 launch. The 2M canary showed annealing the WALK core's action-noise std down (not just stance's) makes stochastic (real-world-like) behavior match deterministic behavior almost exactly, instead of the old recipe where stochastic walking reached only 5-8% of commanded progress. Does that fix SURVIVE and COMPOUND at full acquisition scale (38M steps, matching cap29-acq1's own budget) on a second seed -- i.e. does the DONE-gate session read's direction_err_med/slip_per_m_med actually improve once sto-mode stops being near-non-functional, replicated across seeds?

**gate**: flat-only eval_done_gate_session (ops.sh donegatecmd flat=1) n>=12 det+sto DR-0+own-DR, read against the SAME cap29-acq1{,-s1} baseline it replaces: zero falls must hold (bar already met at 32/32 zero-term by cap29-acq1 and durctrl-canary); PASS if direction_err_med and slip_per_m_med drop at or below the cap29 zero-training baseline (46.8 deg / 3.09) AND the canary-scale purewalk det/sto convergence (this cycle's finding) replicates at session scale (sto progress within ~20% of det, not the old 5-8%); PARTIAL if falls+sto-convergence hold but steering does not improve (confirms steering is a separate, still-open defect per STATUS item 2); FAIL if sto-mode regresses back toward the old 5-8%-of-det pattern at this scale or if terminations return.

**verdict**: Training finished clean at 38.0M, same shape as the seed-0 twin (reward rising then flat, no numerical issues). Auto SESSION/MIXEDSESSION harness errored rc=1 with the same expected obs-contract-mismatch this whole exotic-obs lineage always hits (not new). Dispatched the track's own flat-only eval_done_gate_session (n=32) on-pod (train-7, code synced to c70333b), backgrounded and registered via evalpending -- completes the seed pair for the acq-scale read of whether the stdwalklo-hi anneal dose's canary-scale sto/det convergence survives to full budget vs the cap29-acq1 baseline (46.8 deg/3.09). Not yet landed; joint verdict with the seed-0 run once both flatonly reads are in.

