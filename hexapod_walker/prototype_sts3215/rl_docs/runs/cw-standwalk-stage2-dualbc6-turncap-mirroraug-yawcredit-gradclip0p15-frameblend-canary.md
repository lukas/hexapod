# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-frameblend-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-02T01:39:27+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-durctrl-canary

**wandb_id**: lw4ejrib

**hypothesis**: Blending the mode_seq switch observation (not the reward/anchor frame, only what the policy SEES) removes the confirmed action-saturation shock at rise->walk handoff, reducing walk-segment near-switch over_current terminations relative to the matched no-blend durctrl-canary control.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same flat-only eval_done_gate_session (n=8, video, rise_flat_frac=1.0 etc) as the duration-mismatch quartet: near-instant/near-switch over_current fraction must drop meaningfully below durctrl-canary (walk_term/total_term and time-since-switch-clustering) with progress_ratio/slip not regressing outside noise.

