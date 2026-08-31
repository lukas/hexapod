# cw-standwalk-stage2-dualbc5-turncap-turnskip-turnpay-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-31T04:49:17+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc5-turncap-turnpay-canary

**wandb_id**: egec2bm3

**hypothesis**: Plain English: the anchor1p0/anchor0p3 dose-ablation pair proved a GLOBAL bc_anchor_coef cut does not restore turn authority (identical yaw_kernel_factor erosion at 3.0/1.0/0.3). This is the untried OTHER half of that same anchor-drowns-yaw hypothesis: instead of diluting anchor supervision on ALL commanded ticks (including the majority straight-walk ticks that need it), use the new train.bc_anchor_walk_turn_skip=1 mechanism to zero the anchor's target emission ONLY on pure turn-in-place ticks (vx=vy~0, wz!=0), so the yaw reward's own gradient is the sole supervisor of the actor's mean action there while straight-walk ticks keep the FULL bc_anchor_coef=3.0 anchor untouched. Same dualbc5_turncap base, same bank-proven OMNI turn reward stack as every prior canary in this lineage.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait at this checkpoint. PASS/promising if probe_turn_authority (own cfg, wz_cmd=+-0.25, walk-mode-filtered) wz_med clears meaningfully above the exonerated-anchor-coef band (~-0.03..+0.003 across all three coef doses) both signs AND det walk gait_valid stays >=5/6 (rules out 'anchor removal on turn ticks traded for gait collapse at those ticks'). FAIL if wz_med stays <0.03 both signs (the anchor mechanism as a whole -- both dose AND targeted gating -- is exonerated; the erosion is elsewhere, e.g. PPO exploration collapse or a reward-stack interaction, next candidate: isolate-update / percore-clip interaction with the yaw kernel, or an entropy/exploration-focused arm) or gait_valid craters (the turn-tick anchor pull was load-bearing even just for those ticks' local gait continuity, need a softer partial-weight gate instead of full skip).

