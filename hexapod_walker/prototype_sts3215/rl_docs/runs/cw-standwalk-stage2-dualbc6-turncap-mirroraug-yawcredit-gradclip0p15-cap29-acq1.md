# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PARTIAL

**created**: 2026-09-02T09:23:51+00:00

**pod**: hexapod-mjx-train-3

**steps**: 38000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-canary

**wandb_id**: si9bx2hw

**hypothesis**: Plain English: the mid-rise femur current pins at the OLD 2.5A safety cap regardless of mass/switch/ramp (localized 09-02), and a zero-training probe showed raising the cap to 2.9A (still under HARDWARE.md's real 2.97A/3A lab guard) eliminates the spurious over-current terminations outright (0/8 vs 5/8) on this exact lineage's checkpoint. Does training THIS lineage's best walk-quality+turn-authority checkpoint (the gradclip0p15 2M canary, not the degraded 38M acq1) further under the raised cap -- instead of under the old cap that was tripping mid-rise and feeding the policy spurious termination penalties -- let it hold or improve turn authority/walk quality at acquisition scale, instead of degrading the way the old-cap 38M acq1 run did (progress 0.31-0.33 vs the 2M canary's 0.38-0.40, slip 4.9-10.2 vs 2.2-2.6)?

**gate**: flat-only eval_done_gate_session (ops.sh donegatecmd flat=1) n>=12 det+sto DR-0+own-DR: zero falls (bar now MET by the cap-only teacher control durctrl-canary at 32/32 zero-term -- any regression here refutes training-time cap-raise); direction_err_med and slip_per_m_med at or below the cap29 zero-training read's own baselines (46.8 deg / 3.09) to beat; PARTIAL if zero-falls holds but direction/slip do not improve on the baseline; FAIL if terminations return at rates resembling the old-cap acq1/gradclip0p15 pattern.

**verdict**: Result: training-time cap=2.9 acquisition (38M steps, warm-started off gradclip0p15-canary) holds zero falls (0/32 term, dr0+ownDR, matches durctrl-canary's 32/32 bar) but does NOT beat the cap29 zero-training baseline on steering/slip: direction_err_med 55.5 deg (baseline 46.8), slip_per_m_med 3.46 (baseline 3.09) -- flat-only eval_done_gate_session, n=32. Evidence: logs/ckpt_eval/cw_standwalk_stage2_dualbc6_turncap_mirroraug_yawcredit_gradclip0p15_cap29_acq1_donegate_flatonly/session_verdict.json (gate.pass=true on the soft zero-falls/gait_valid/height bar, gate.soft.slip_ok=false, dir_err_ok=false -- this is the pre-registered PARTIAL branch, not a surprise). Why: confirms the cap-raise's fall-avoidance benefit generalizes to training-time (matches the zero-training-only control), but the walk-quality/steering gain seen in the zero-training probe (dir 43-46/slip 2.7-3.2 on purewalk) does NOT carry through a full retrain at acquisition scale -- reward curve is healthy (566.8/1970.7/2219.5/2165.5 quarters, plateaued not blown up), so this is not a training failure, just a real ceiling: cap-raise alone doesn't buy steering. Next: standwalk Next item 2 (steering-gap arm, already flagged as the largest remaining DONE-gate distance, confirmed not current-confounded) is now the one lever left -- design a dedicated steering/direction-following reward or curriculum change against the 60s session harness, gated by test_task_semantics.py before launch.

