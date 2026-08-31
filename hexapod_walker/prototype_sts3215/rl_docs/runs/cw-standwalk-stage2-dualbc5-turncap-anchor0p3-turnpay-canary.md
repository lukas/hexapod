# cw-standwalk-stage2-dualbc5-turncap-anchor0p3-turnpay-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-31T03:47:58+00:00

**pod**: hexapod-mjx-train-6

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc5-turncap-turnpay-canary

**wandb_id**: zvgpq3lu

**hypothesis**: Plain English: same anchor-drowns-yaw hypothesis as the 1.0 dose sibling, but a much more aggressive 10x cut (bc_anchor_coef 3.0->0.3) in case a 3x cut is not enough to let turn reward move the policy — a dose-response pair on the ONE lever (anchor coefficient) the FAILed dualbc5_turncap-turnpay-canary's decisive finding (RL erodes pre-RL partial turn authority) points to next, launched together per the batching rule rather than serialized one-dose-at-a-time.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (single seed, first dose read; seed-replicate only if positive; joint dose-response read with the 1.0 sibling). PASS/promising if probe_turn_authority wz_med clears meaningfully above the FAILed base's ~0.001-0.024 band both signs AND det walk gait_valid stays >=5/6. FAIL if wz_med stays <0.03 both signs (anchor coef exonerated even at 10x cut -- look elsewhere, e.g. PPO exploration/reward-stack interaction, not the anchor) or gait_valid craters (confirms the anchor is load-bearing down to a much lower coefficient than 1.0, need a turn-tick-only gate instead of a global dose cut).

**verdict**: CANARY FAIL - MECHANISM (joint w/ anchor1p0 sibling, see that verdict for full evidence): 10x cut (bc_anchor_coef 3.0->0.3) still fails decisively. probe_turn_authority seeds 0/1: wz_med -0.0014/-0.0007 (wz_cmd=+0.25), -0.0220/-0.0299 (wz_cmd=-0.25) -- all under the 0.03 floor both signs (the least-bad reading, -0.0299, is still a FAIL). env/walk_yaw_kernel_factor erosion 0.32->~0.05-0.09, same shape as the 1.0-dose sibling and the uncut 3.0 parent -- confirms even a 10x reduction does not touch the erosion mechanism. Own frame-strip check on walk_det_0..5.mp4: clean 6-leg gait preserved, no collapse. Reward crashes through the run (quarters [53.7,28.0,-254.6,-31.0]) alongside the failing eval, not a rising-reward case. Anchor coefficient is now exonerated across a full order of magnitude (3.0/1.0/0.3) -- see anchor1p0 verdict for the refill (new bc_anchor_walk_turn_skip mechanism, tested+snapshotted, canary launching off this same dualbc5_turncap base).

