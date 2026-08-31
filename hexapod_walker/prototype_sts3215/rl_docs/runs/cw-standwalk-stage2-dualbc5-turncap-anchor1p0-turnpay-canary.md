# cw-standwalk-stage2-dualbc5-turncap-anchor1p0-turnpay-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-31T03:43:52+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc5-turncap-turnpay-canary

**wandb_id**: 5zfft3tw

**hypothesis**: Plain English: if the strong walk-imitation anchor (bc_anchor_coef=3.0) is drowning the yaw reward's turn-in-place signal at the minority turn ticks, cutting the anchor pull 3x should let some turn authority through even though the underlying reward stack and distillation base are unchanged. Single-lever dose ablation off the just-FAILed dualbc5_turncap-turnpay-canary base (turn-capable pre-RL checkpoint, same bank-proven OMNI turn reward stack), only train.bc_anchor_coef 3.0->1.0.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (single seed, first dose read; seed-replicate only if positive). PASS/promising if probe_turn_authority (own cfg, wz_cmd=+-0.25, walk-mode-filtered) wz_med clears meaningfully above the FAILed base's ~0.001-0.024 band (report both signs) AND det walk gait_valid stays >=5/6 (rules out 'anchor loss traded for gait collapse'). FAIL if wz_med stays <0.03 both signs (anchor coef is exonerated as the cause) or gait_valid craters (anchor coef confirmed load-bearing for gait quality, need a turn-tick-only gate instead of a global dose cut).

**verdict**: CANARY FAIL - MECHANISM (joint w/ anchor0p3 sibling): dose-response test on the ONE lever the parent turncap-turnpay-canary FAIL named (bc_anchor_coef, 3.0->1.0 here) does NOT restore turn authority. probe_turn_authority (own cfg, wz_cmd=+-0.25, walk-mode-filtered, seeds 0/1): wz_med 0.0034/0.0034 (wz_cmd=+0.25), -0.0100/-0.0181 (wz_cmd=-0.25) -- every reading well under the 0.03 FAIL floor both signs, no improvement over the uncut-coef parent's -0.0009..-0.0243 band. Training telemetry: env/walk_yaw_kernel_factor erodes 0.34->~0.05-0.09 over the 2M run, an IDENTICAL curve shape/magnitude to the parent (coef=3.0) and the 0.3-dose sibling -- the anchor coefficient has zero measurable effect on the erosion. Gait health preserved (own frame-strip check on walk_det_0..5.mp4: clean 6-leg tripod cycling, real forward translation, no drag/paddle), so this is a clean 'anchor coef exonerated' read per the gate's own disjunctive clause, not a gait-collapse confound. Reward also crashes hard through the run (quarters [53.9,30.6,-246.9,-47.2]), not a rising-reward-bad-eval case needing more budget per the 08-21 ruling -- both reward and the turn-authority metric are flat/failing together. Refill: root-caused the untried OTHER half of the same hypothesis (global coef cut dilutes supervision on majority straight-walk ticks too, rather than targeting only the competing turn ticks) -- built+tested a new env-side mechanism train.bc_anchor_walk_turn_skip (default 0, bit-exact off; skips BC-anchor target emission ONLY on pure turn-in-place ticks, vx=vy~0 & wz!=0, leaving straight/combined-command ticks untouched), 3 new tests green (96/96 bc_anchor suite), snapshotted. Launching a mechanism-health canary from the same dualbc5_turncap base with bc_anchor_coef restored to 3.0 + bc_anchor_walk_turn_skip=1.

