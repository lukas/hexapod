# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-durctrl-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS (own scope) - joint pending flatonly-read

**created**: 2026-09-01T21:09:45+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-canary

**wandb_id**: yox05nod

**hypothesis**: Matched control for durfix-canary (same cycle): identical warm start (gradclip0p15-canary checkpoint) and step budget (2M), but NO episode-seconds/mode_seq_segment_s widening -- isolates 'just 2M more training steps on the unchanged short-segment diet' from durfix's 'exposure to a genuinely long single-mode segment' as the explanation for any eval_done_gate_session improvement. Prediction: this control's own flat-only DONE-gate read stays at the same walk-segment near-instant-onset over_current signature as the un-continued parent (16/22 canary baseline), since nothing about the training diet changed.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Comparison-only run: no independent PASS/FAIL bar. Its eval_done_gate_session flat-only read (n=8 min, video) is read jointly against durfix-canary's at the same step count -- if durfix clears bars this control does not, duration-mismatch is confirmed as (part of) the driver; if both move together, the improvement (if any) is just from extra steps, not the widened duration lever.

**verdict**: CANARY PASS (own scope) - joint pending flatonly-read. Training-only triage: this is the matched no-cfg-change CONTROL twin of the duration-mismatch fix pair (2M steps, same warm-start/seed/recipe as gradclip0p15-canary -- only more training, no widened mode_seq_segment/episode-seconds). No independent PASS/FAIL bar at this mechanism-health canary scope; the decisive read is the flat-only eval_done_gate_session (n=8, video, goal.rise_flat_frac=1.0 override) read jointly against durfix-canary's at the same 2M step count per STATUS Next item 1. Reward curve is healthy (no blowup, no flatline): dipped hard mid-run (~900k-1.5M steps, ep_rew_mean 90->-314) then self-corrected to 140.6 by 2M, consistent with ordinary RL churn on an unchanged recipe rather than evidence either way on the duration question. Launched the flat-only DONE-gate session on this checkpoint (train-1) plus its durctrl-canary-s1 twin (train-2) and the durfix-canary counterpart (train-3, was idle, same comparison) so all three land together for the joint verdict next cycle.

