# cw-standwalk-stage2-dualbc5-turncap-isolateoff-turnpay-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-31T06:06:35+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc5-turncap-turnpay-canary

**wandb_id**: 6cnewt07

**hypothesis**: Plain English: the anchor mechanism (dose AND turn-tick-targeted gating) is now exonerated across 4 independent tests -- the turn-authority erosion during RL is somewhere else. This tests the FIRST named next-suspect from the turnskip canary's own gate text: train.bc_anchor_isolate_update=1 (currently ON in every one of these canaries) changes HOW the dual-core aux optimizer applies gradients (drops all-zero grads before the aux step, avoiding stale-momentum updates into the gated-out core) -- if that specific update-isolation interacts badly with the walk core's yaw-kernel gradient (e.g. by changing the walk core's own momentum trajectory during the exact reward-trough window), reverting to the pre-08-26 legacy behavior (isolate_update=0) on this otherwise-identical turnpay-canary base should show up as a probe_turn_authority delta. Same dualbc5_turncap init-from checkpoint, same bank-proven OMNI turn reward stack, same bc_anchor_coef=3.0, only this one flag flipped off.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait at this checkpoint. PASS/promising if probe_turn_authority (own cfg minus goal.mode_seq, wz_cmd=+-0.25, walk-mode-filtered, seeds 0/1) wz_med clears meaningfully above the exonerated band (~-0.03..+0.005 across anchor-coef doses AND turn-skip) both signs AND det walk gait_valid stays >=5/6. FAIL if wz_med stays <0.03 both signs (isolate_update exonerated too -- next suspect is entropy/PPO exploration itself, see the entboost sibling) or gait_valid craters (isolate_update was covering for a real momentum-corruption bug, need a narrower fix not a blanket revert).

**verdict**: CANARY FAIL - MECHANISM: bc_anchor_isolate_update (the 08-26 dual-core aux-optimizer update-isolation fix) is EXONERATED as the turn-authority suspect. probe_turn_authority (own cfg minus goal.mode_seq, wz_cmd=+-0.25, walk-mode-filtered, seeds 0/1) reads wz_med +0.0025/+0.0025 (+0.25) and -0.0057/-0.0089 (-0.25) -- all four under the 0.03 FAIL floor both signs, indistinguishable from the exonerated dose/turnskip band (-0.03..+0.005). env/walk_yaw_kernel_factor erodes 0.48->0.05 over the run (identical shape/magnitude to every prior canary in this lineage); reward crashes through the back half (q1 93 -> q2 -243 -> last 1.7), not a rising-reward case. Frame-strip on walk_det_0.png: clean 6-leg gait fully preserved across all 10 sampled frames, legs visibly cycling through stance/swing, no collapse -- rules out the 'update-isolation was covering for a real momentum-corruption bug' alternative named in this arm's own gate text. Reverting isolate_update=1->0 changes nothing: this specific gradient-application mechanism is not the yaw-authority bottleneck. Joint with entboost (same cycle): PPO exploration dose is now the last of the two next-suspects named by the turnskip gate text; see that verdict for entboost's own read. Refill: with BOTH isolate_update AND entropy dose now exonerated, every mechanism-level lever this lineage's own gate texts have named across 5 sequential canaries (dose 3.0/1.0/0.3, turn-tick-targeted skip, update-isolation revert, 4x entropy) is refuted -- escalating to a structural dig-in on the raw reward-component trace (does k_walk_yaw ever fire a nonzero gradient on turn ticks at all, independent of PPO mechanics) before funding another training-mechanism knob; flagged DIG-IN below rather than a blind 6th canary.

