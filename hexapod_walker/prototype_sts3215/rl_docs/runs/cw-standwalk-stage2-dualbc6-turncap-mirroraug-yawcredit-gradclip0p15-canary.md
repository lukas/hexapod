# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-01T11:03:07+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-canary-rr1

**wandb_id**: u64d1bho

**hypothesis**: Plain English: dose-bracket sibling of this cycle's gradclip0p5-canary (launched moments earlier, batched per operator 08-22 batch-the-grid rule instead of dribbling one clip value per cycle) -- does a TIGHTER trust-region clip (0.15, ~3x tighter than 0.5) on the same coef=1.0/vf_coef=0.5 yaw-advantage actor step recover parity with the matched coef=0 control (pos avg 0.083/neg avg -0.138) more fully than 0.5 does, confirming a monotonic dose-response (tighter=better, i.e. update SIZE is the whole story) vs the alternative that even the tightest clip still regresses (update DIRECTION is the problem, not size, ruling out grad-clip as a class of fix entirely)? Same parent/init/seed/recipe as gradclip0p5-canary and the rr1 FAIL, single lever changed (clip value only).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Read jointly against the control (cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-ctrl-canary, wz_med pos avg 0.083/neg avg -0.138), the grad_clip=0 FAIL sibling (rr1, pos avg 0.028/neg avg -0.097), and the grad_clip=0.5 sibling (read jointly when both finish). PASS/PROMOTE if final (2M) probe_turn_authority wz_med clears the control's own final within 0.01 on BOTH signs AND det walk gait_valid>=5/6 zero falls AND purewalk det progress_ratio within 0.03 of the control's own. INFORMATIVE if it beats the grad_clip=0 sibling by >=0.02 both signs but still short of full parity -- compare against the 0.5 sibling to place the dose-response curve. FAIL if within noise of (or worse than) the grad_clip=0 sibling at this tighter dose -- strengthens the direction-not-size read.

