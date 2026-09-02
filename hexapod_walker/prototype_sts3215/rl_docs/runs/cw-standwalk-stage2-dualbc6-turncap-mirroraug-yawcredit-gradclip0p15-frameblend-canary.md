# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-frameblend-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-02T01:39:27+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-durctrl-canary

**wandb_id**: lw4ejrib

**hypothesis**: Blending the mode_seq switch observation (not the reward/anchor frame, only what the policy SEES) removes the confirmed action-saturation shock at rise->walk handoff, reducing walk-segment near-switch over_current terminations relative to the matched no-blend durctrl-canary control.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same flat-only eval_done_gate_session (n=8, video, rise_flat_frac=1.0 etc) as the duration-mismatch quartet: near-instant/near-switch over_current fraction must drop meaningfully below durctrl-canary (walk_term/total_term and time-since-switch-clustering) with progress_ratio/slip not regressing outside noise.

**verdict**: CANARY FAIL - MECHANISM: frame-blend does NOT fix the switch shock -- it makes total over_current terminations WORSE, not better, refuting the pre-registered gate. Flat-only eval_done_gate_session (n=32, DR-0+ownDR) vs matched no-blend control durctrl-canary: terminations 27/32 vs control 24/32; rise-segment terms jump 14->20 (blend only touches the obs-facing switch handoff, not the already-identified mid-rise sustained-current fragility that dominates rise terms); walk-segment terms drop slightly 10->7 but total termination rate still rises. progress_ratio (0.059 vs 0.051) and slip_per_m (10.95 vs 12.47) are inside noise on the handful of survivors (n_with_walk_metrics 5 vs 11) -- not a real walk-quality gain. Joint call with the seed1 twin (frameblend-canary-s1, verdicted same cycle): both seeds move the SAME direction (worse), closing the frame-blend axis -- STATUS Next item 2 CLOSED, no further dose-sweeping. Evidence: logs/ckpt_eval/cw_standwalk_stage2_dualbc6_turncap_mirroraug_yawcredit_gradclip0p15_{durctrl_canary,frameblend_canary}_donegate_flatonly/session_verdict.json (train-1, read this cycle).

