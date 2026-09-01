# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip2p0-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-01T11:07:33+00:00

**pod**: hexapod-mjx-train-6

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-canary-rr1

**hypothesis**: Plain English: dose-bracket sibling of this cycle's gradclip0p5-canary and gradclip0p15-canary (batched per operator 08-22 batch-the-grid rule) -- does a LOOSER trust-region clip (2.0, ~4x looser than 0.5) on the same coef=1.0/vf_coef=0.5 yaw-advantage actor step still recover parity with the matched coef=0 control (pos avg 0.083/neg avg -0.138), or does it read closer to the unclipped grad_clip=0 FAIL (rr1: pos avg 0.028/neg avg -0.097)? Together with 0.15/0.5 this brackets the dose-response curve in one wave instead of one clip value per cycle. Same parent/init/seed/recipe, single lever changed (clip value only).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Read jointly against the control (yawcredit-ctrl-canary, wz_med pos avg 0.083/neg avg -0.138), the grad_clip=0 FAIL sibling (rr1, pos avg 0.028/neg avg -0.097), and the grad_clip=0.15/0.5 siblings (read jointly when all finish, places the dose-response curve). PASS/PROMOTE if final (2M) probe_turn_authority wz_med clears the control's own final within 0.01 on BOTH signs AND det walk gait_valid>=5/6 zero falls AND purewalk det progress_ratio within 0.03 of the control's own. INFORMATIVE if it beats the grad_clip=0 sibling by >=0.02 both signs but still short of full parity. FAIL if within noise of (or worse than) the grad_clip=0 sibling at this looser dose -- strengthens the direction-not-size read and that only a tight clip (if any) helps.

**refused_reason**: a process for cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip2p0-canary already exists on hexapod-mjx-train-5

