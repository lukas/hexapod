# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-frameblend-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-02T01:38:10+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-durctrl-canary-s1

**wandb_id**: h58vj6eg

**hypothesis**: Same as frameblend-canary (seed1): does the obs-only q_nom blend reduce near-switch over_current terminations vs the matched no-blend seed1 control.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as frameblend-canary: flat-only eval_done_gate_session vs durctrl-canary-s1, n=2 seeds total across the pair.

**verdict**: CANARY FAIL - MECHANISM: seed1 twin of frameblend-canary -- same refutation, more dramatic. Flat-only eval_done_gate_session (n=32, DR-0+ownDR) vs matched no-blend control durctrl-canary-s1: terminations jump 21/32 vs control's 5/32 (over 4x worse) -- walk-segment terms go 5->14, rise-segment terms 0->7. No progress_ratio/slip improvement to offset it, and too few surviving walk-segment episodes to trust the metric either way (6 vs 16 with_walk_metrics); neither session clears the gate's soft bars. Read jointly with frameblend-canary (seed0, verdicted same cycle, also worse 27/32 vs 24/32): frame-blend (goal.mode_seq_frame_blend_s=0.5) is REFUTED as a fix for the switch shock at both seeds -- closes STATUS Next item 2, no further dose-sweeping. Evidence: logs/ckpt_eval/cw_standwalk_stage2_dualbc6_turncap_mirroraug_yawcredit_gradclip0p15_frameblend_canary_s1_donegate_flatonly/session_verdict.json (train-5, read this cycle).

