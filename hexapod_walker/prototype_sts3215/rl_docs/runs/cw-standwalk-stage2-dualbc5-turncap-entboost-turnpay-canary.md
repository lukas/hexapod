# cw-standwalk-stage2-dualbc5-turncap-entboost-turnpay-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-31T06:13:30+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc5-turncap-turnpay-canary

**wandb_id**: vyca9ptd

**hypothesis**: Plain English: the anchor mechanism (dose AND turn-tick-targeted gating) is now exonerated across 4 independent tests -- the turn-authority erosion during RL is somewhere else. This tests the SECOND named next-suspect from the turnskip canary's own gate text: PPO exploration collapse. This lineage's log_std anneal is scoped to the stance core only (--log-std-anneal-core stance), so the walk core's action std is NOT forced down by that explicit schedule, but PPO's own natural entropy decay could still be starving exploration on the minority turn-in-place ticks before the yaw reward's gradient can find the turning behavior. A 4x ent-coef bump (0.005->0.02) on this otherwise-identical turnpay-canary base (same dualbc5_turncap init-from checkpoint, same bank-proven OMNI turn reward stack, same bc_anchor_coef=3.0/isolate_update=1) tests whether more exploration alone restores any turn signal.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait at this checkpoint. PASS/promising if probe_turn_authority (own cfg minus goal.mode_seq, wz_cmd=+-0.25, walk-mode-filtered, seeds 0/1) wz_med clears meaningfully above the exonerated band (~-0.03..+0.005 across anchor-coef doses AND turn-skip) both signs AND det walk gait_valid stays >=5/6 (rules out 'more exploration traded for gait collapse'). FAIL if wz_med stays <0.03 both signs (exploration dose exonerated too at this level -- next suspect is a structural reward-stack interaction, e.g. the yaw kernel gate itself never firing on this diet, needs a dig-in on the raw per-tick reward components not another training-mechanism knob) or gait_valid craters (higher entropy destabilized the walk core generally, not turn-specific).

**verdict**: CANARY FAIL - MECHANISM: PPO exploration dose (4x ent-coef 0.005->0.02) is EXONERATED as the turn-authority suspect, the SECOND and last next-suspect named by the turnskip canary's own gate text. probe_turn_authority (own cfg minus goal.mode_seq, wz_cmd=+-0.25, walk-mode-filtered, seeds 0/1) reads wz_med +0.0004/+0.0023 (+0.25) and -0.0030/-0.0086 (-0.25) -- all four under the 0.03 FAIL floor both signs, indistinguishable from the exonerated dose/turnskip/isolateoff band. env/walk_yaw_kernel_factor erodes 0.35->0.09 over the run, same shape as every prior canary in this lineage; reward crashes through the back half (q1 92 -> q2 -331 -> q3 -111, partial recovery to 101.8 at the very end -- not a clean rising-reward case, the trajectory still spends most of the run in the same collapse this lineage always shows). Frame-strip on walk_det_0.png: clean 6-leg gait fully preserved, legs visibly cycling stance/swing across all 10 frames, no collapse -- rules out 'more exploration traded for gait collapse'. Joint with isolateoff (same cycle, same base, same batch): with BOTH named next-suspects (isolate_update AND entropy dose) now exonerated, this lineage has refuted 5 independent mechanism classes in a row (global anchor dose 3.0/1.0/0.3, turn-tick-targeted anchor skip, isolate_update revert, 4x entropy) without moving wz_med off the same -0.03..+0.005 band. Escalating: the next question is structural, not another training-mechanism knob -- does the k_walk_yaw reward term ever emit a nonzero per-tick gradient signal on genuine turn-in-place ticks at all (raw reward-component trace on a short rollout), independent of how PPO explores or applies gradients. Flagging DIG-IN rather than launching a 6th canary blind.

