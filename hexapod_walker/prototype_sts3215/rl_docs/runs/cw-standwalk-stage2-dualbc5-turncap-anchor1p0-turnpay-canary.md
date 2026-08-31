# cw-standwalk-stage2-dualbc5-turncap-anchor1p0-turnpay-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-31T03:43:52+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc5-turncap-turnpay-canary

**wandb_id**: 5zfft3tw

**hypothesis**: Plain English: if the strong walk-imitation anchor (bc_anchor_coef=3.0) is drowning the yaw reward's turn-in-place signal at the minority turn ticks, cutting the anchor pull 3x should let some turn authority through even though the underlying reward stack and distillation base are unchanged. Single-lever dose ablation off the just-FAILed dualbc5_turncap-turnpay-canary base (turn-capable pre-RL checkpoint, same bank-proven OMNI turn reward stack), only train.bc_anchor_coef 3.0->1.0.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (single seed, first dose read; seed-replicate only if positive). PASS/promising if probe_turn_authority (own cfg, wz_cmd=+-0.25, walk-mode-filtered) wz_med clears meaningfully above the FAILed base's ~0.001-0.024 band (report both signs) AND det walk gait_valid stays >=5/6 (rules out 'anchor loss traded for gait collapse'). FAIL if wz_med stays <0.03 both signs (anchor coef is exonerated as the cause) or gait_valid craters (anchor coef confirmed load-bearing for gait quality, need a turn-tick-only gate instead of a global dose cut).

