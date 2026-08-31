# cw-standwalk-stage2-dualbc5-turncap-turnskip-turnpay-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-08-31T04:49:17+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc5-turncap-turnpay-canary

**wandb_id**: egec2bm3

**hypothesis**: Plain English: the anchor1p0/anchor0p3 dose-ablation pair proved a GLOBAL bc_anchor_coef cut does not restore turn authority (identical yaw_kernel_factor erosion at 3.0/1.0/0.3). This is the untried OTHER half of that same anchor-drowns-yaw hypothesis: instead of diluting anchor supervision on ALL commanded ticks (including the majority straight-walk ticks that need it), use the new train.bc_anchor_walk_turn_skip=1 mechanism to zero the anchor's target emission ONLY on pure turn-in-place ticks (vx=vy~0, wz!=0), so the yaw reward's own gradient is the sole supervisor of the actor's mean action there while straight-walk ticks keep the FULL bc_anchor_coef=3.0 anchor untouched. Same dualbc5_turncap base, same bank-proven OMNI turn reward stack as every prior canary in this lineage.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait at this checkpoint. PASS/promising if probe_turn_authority (own cfg, wz_cmd=+-0.25, walk-mode-filtered) wz_med clears meaningfully above the exonerated-anchor-coef band (~-0.03..+0.003 across all three coef doses) both signs AND det walk gait_valid stays >=5/6 (rules out 'anchor removal on turn ticks traded for gait collapse at those ticks'). FAIL if wz_med stays <0.03 both signs (the anchor mechanism as a whole -- both dose AND targeted gating -- is exonerated; the erosion is elsewhere, e.g. PPO exploration collapse or a reward-stack interaction, next candidate: isolate-update / percore-clip interaction with the yaw kernel, or an entropy/exploration-focused arm) or gait_valid craters (the turn-tick anchor pull was load-bearing even just for those ticks' local gait continuity, need a softer partial-weight gate instead of full skip).

**verdict**: CANARY FAIL - MECHANISM (4th turn-authority mechanism class refuted; anchor mechanism as a whole -- dose AND targeted gating -- now exonerated). Result: probe_turn_authority (own cfg minus goal.mode_seq, wz_cmd=+-0.25, walk-mode-filtered, seeds 0/1) on this checkpoint (train.bc_anchor_walk_turn_skip=1, bc_anchor_coef restored to 3.0) reads wz_med +0.0047/+0.0029 (wz_cmd=+0.25) and -0.0104/-0.0146 (wz_cmd=-0.25) -- all four readings under the gate's 0.03 FAIL floor both signs, effectively unchanged from the exonerated dose-ablation band (anchor1p0/anchor0p3: -0.03..+0.003) and the uncut 3.0 parent. env/walk_yaw_kernel_factor erodes 0.336->0.090 over the 2M run, same shape/magnitude as every prior canary in this lineage (turnpay-canary{,-s1}, anchor1p0, anchor0p3). Reward crashes hard through the back half (quarters [53.9,27.9,-270.6,-19.9]) alongside the failing eval -- not a rising-reward case per the 08-21 ruling. Own frame-strip check on walk_det_0.mp4 (harness gate/owncfg mid-flight on train-2, videos already synced): clean 6-leg tripod gait fully preserved, real forward translation, no collapse/drag -- rules out gait_valid cratering, so this is a clean 'mechanism exonerated' read, not a gait-collapse confound. Conclusion: the BC-anchor pull (dose OR turn-tick-targeted gating) is NOT the mechanism destroying turn authority during RL fine-tuning on this lineage -- four independent tests (global 3.0/1.0/0.3 dose, targeted turn-tick skip) all land in the same near-zero band. Next suspect per this run's own gate text: PPO exploration collapse or a reward-stack interaction (bc_anchor_isolate_update/bc_anchor_percore_clip interacting with the yaw kernel specifically, or an entropy/exploration-focused arm) -- a future cycle should isolate PPO exploration first (e.g. raise ent_coef or disable isolate_update/percore_clip as a paired ablation) before trying another anchor-family knob, since the anchor axis is now exhausted.

