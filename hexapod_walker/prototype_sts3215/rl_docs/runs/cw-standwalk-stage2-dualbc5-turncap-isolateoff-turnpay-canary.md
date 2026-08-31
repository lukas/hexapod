# cw-standwalk-stage2-dualbc5-turncap-isolateoff-turnpay-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-31T06:06:35+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc5-turncap-turnpay-canary

**wandb_id**: 6cnewt07

**hypothesis**: Plain English: the anchor mechanism (dose AND turn-tick-targeted gating) is now exonerated across 4 independent tests -- the turn-authority erosion during RL is somewhere else. This tests the FIRST named next-suspect from the turnskip canary's own gate text: train.bc_anchor_isolate_update=1 (currently ON in every one of these canaries) changes HOW the dual-core aux optimizer applies gradients (drops all-zero grads before the aux step, avoiding stale-momentum updates into the gated-out core) -- if that specific update-isolation interacts badly with the walk core's yaw-kernel gradient (e.g. by changing the walk core's own momentum trajectory during the exact reward-trough window), reverting to the pre-08-26 legacy behavior (isolate_update=0) on this otherwise-identical turnpay-canary base should show up as a probe_turn_authority delta. Same dualbc5_turncap init-from checkpoint, same bank-proven OMNI turn reward stack, same bc_anchor_coef=3.0, only this one flag flipped off.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait at this checkpoint. PASS/promising if probe_turn_authority (own cfg minus goal.mode_seq, wz_cmd=+-0.25, walk-mode-filtered, seeds 0/1) wz_med clears meaningfully above the exonerated band (~-0.03..+0.005 across anchor-coef doses AND turn-skip) both signs AND det walk gait_valid stays >=5/6. FAIL if wz_med stays <0.03 both signs (isolate_update exonerated too -- next suspect is entropy/PPO exploration itself, see the entboost sibling) or gait_valid craters (isolate_update was covering for a real momentum-corruption bug, need a narrower fix not a blanket revert).

