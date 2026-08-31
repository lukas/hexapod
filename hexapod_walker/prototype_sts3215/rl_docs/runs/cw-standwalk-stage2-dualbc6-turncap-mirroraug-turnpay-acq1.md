# cw-standwalk-stage2-dualbc6-turncap-mirroraug-turnpay-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-31T15:44:45+00:00

**pod**: hexapod-mjx-train-0

**steps**: 38000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-turnpay-canary

**wandb_id**: woi4ob07

**hypothesis**: Plain English: this asks whether the mirror-augmented turn-authority base, which held wz_med +0.130/+0.121 and -0.178/-0.172 (both far above the campaign 0.10-both-signs bar, nowhere near the ~0.03 RL-erosion floor) through a 2M-step RETENTION canary with clean det walk gait_valid 8/8 and progress_ratio 0.418 (within noise of the wave-1 0.43-0.48 band), keeps that turn authority and matures walk quality when trained to a full acquisition budget instead of just 2M. This is the direct continuation the RETENTION canaries own gate was built to earn: 9 prior mechanism classes on non-mirrored bases all collapsed to <0.03 wz_med by 2M already, so surviving 2M cleanly on this base is real signal, not proof it survives 40M of continued optimization pressure on the SAME reward stack (bc_anchor_coef=3.0 imitation still running alongside RL, which could still slow-erode turn authority over a longer horizon even though it did not at 2M). Prediction-if-true: at ~40M cumulative steps, probe_turn_authority wz_med stays >=0.10 both signs (ideally approaching the walk-teachers ~0.21 band), pure-walk det progress_ratio holds/improves vs 0.418, gait_valid stays >=5/6, and the actual eval_joystick_gate 60s randomized stress_mix session shows real, if imperfect, direction-following (direction_err_med materially better than the ~45-52deg every non-turning-base joygate has shown) -- this would be the first standwalk lineage that both walks cleanly AND turns on command, closing the fork the turn-authority campaign opened. Prediction-if-false: wz_med decays back toward the <0.03 floor over the longer horizon (slow erosion invisible at 2M but present at scale) even though gait/progress stay fine -- that would mean the distillation-base fix only buys TIME, not durability, and the real fix is still RL-side credit assignment/reward magnitude for the yaw term over a full-length run. Strongest alternative: bc_anchor_coef=3.0 imitation-vs-RL tension (not reward-magnitude erosion) is the actual driver, distinguishable by whether reward_walk_yaw/walk_yaw_kernel_factor decays in the same fast-early-then-floor shape every prior erosion case showed (RL-erosion signature) vs a slower monotonic anchor-dilution shape.

**gate**: ACQUISITION (continuation of a passed RETENTION canary, phase acquisition, budget ~40M cumulative). PASS/promote-to-stage2-source if: probe_turn_authority (own TURNCAP_CFG_SET, wz_cmd=+-0.25) wz_med >= 0.10 both signs at the final checkpoint AND pure-walk (mode_seq OFF) det progress_ratio not regressed vs 0.40-0.48 AND det walk gait_valid >= 5/6 AND the held-out eval_joystick_gate (60s randomized stress_mix session, n>=12 det+sto, DR-0) shows direction_err_med materially improved vs every non-turning-base joygate read (45-52deg) with zero-or-near-zero falls and slip/m <=3.0. FAIL (erosion-dominant, confirms the fix only bought time) if wz_med decays back under 0.03 both signs by the final checkpoint even though gait/progress stay clean. PARTIAL/DIG-IN for anything between (e.g. turn authority holds but joygate direction-following still fails, or one sign erodes and the other does not) -- quantify and do not force a binary call.

