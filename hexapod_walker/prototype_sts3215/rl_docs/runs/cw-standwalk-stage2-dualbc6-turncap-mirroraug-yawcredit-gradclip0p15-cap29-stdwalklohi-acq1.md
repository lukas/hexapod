# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-02T16:46:33+00:00

**pod**: hexapod-mjx-train-6

**steps**: 38000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi

**wandb_id**: ek429vf3

**hypothesis**: Plain English: the 2M canary just showed that annealing the WALK core's action-noise std down (not just stance's) makes the policy's stochastic (real-world-like) behavior match its deterministic behavior almost exactly, instead of the old recipe where stochastic walking reached only 5-8% of commanded progress. Does that fix SURVIVE and COMPOUND at full acquisition scale (38M steps, matching cap29-acq1's own budget) -- i.e. does the cap29-acq1 DONE-gate session read's direction_err_med/slip_per_m_med (55.5-61.1 deg / 3.45-3.46, worse than the cap29 zero-training baseline of 46.8/3.09) actually IMPROVE once sto-mode stops being near-non-functional, or does the steering gap persist as a separate defect once the std confound is removed?

**gate**: flat-only eval_done_gate_session (ops.sh donegatecmd flat=1) n>=12 det+sto DR-0+own-DR, read against the SAME cap29-acq1{,-s1} baseline it replaces: zero falls must hold (bar already met at 32/32 zero-term by cap29-acq1 and durctrl-canary); PASS if direction_err_med and slip_per_m_med drop at or below the cap29 zero-training baseline (46.8 deg / 3.09) AND the canary-scale purewalk det/sto convergence (this cycle's finding) replicates at session scale (sto progress within ~20% of det, not the old 5-8%); PARTIAL if falls+sto-convergence hold but steering does not improve (confirms steering is a separate, still-open defect per STATUS item 2); FAIL if sto-mode regresses back toward the old 5-8%-of-det pattern at this scale (would mean the fix doesn't survive longer training) or if terminations return.

**verdict**: Flat-only eval_done_gate_session (n=128 ep, det+sto x DR0+ownDR) landed on-pod (train-6) and clears this arm's own pre-registered PASS bar: direction_err_med 44.56deg (< the cap29 zero-training baseline 46.8deg) and slip_per_m_med 2.819 (< baseline 3.09), AND sto/det progress_ratio convergence survives to full 38M acquisition scale (dr0 sto/det 0.379/0.3605=105%, owndr 0.363/0.3865=94%; nowhere near the old 5-8%-of-det collapse). Zero falls/terminations across all 128 episodes, gait_valid_frac=1.0, height_err_end 0.85mm. Confirms the walk-core log_std-anneal-down fix (dose -3.5, canary-scale PASS 09-02) survives and compounds at acquisition scale on seed0 -- joint with -s1 (same read, also PASS). This closes STATUS item 0. NOT the track DONE gate yet: absolute direction_err (44.6deg) still misses the track's tighter ~40deg cap and slip sits right at the 2.9 hard cap, so the steering gap (STATUS item 1) remains open -- this run sets the new best-known reference band (44-45deg dir / 2.8-2.9 slip) to beat next, it does not mark standwalk DONE.

