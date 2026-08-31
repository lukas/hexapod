# cw-standwalk-stage2-dualbc5-turncap-turnpay-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-31T02:46:14+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc5-turncap-turnpay-canary

**wandb_id**: oqo536zn

**hypothesis**: Seed-1 twin of cw-standwalk-stage2-dualbc5-turncap-turnpay-canary (same hypothesis, config, and gate) — checks the partial pre-RL turn-authority escape (asymmetric wz_med -0.038/-0.048 for wz_cmd=-0.25 vs frozen +0.25) is not a single-seed fluke before promoting/killing the dualbc5_turncap distillation-base fix.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as seed0: MECHANISM-HEALTH CANARY ONLY, joint with seed0. PASS/promote if BOTH seeds show probe_turn_authority wz_med >= 0.08 both signs, det walk gait_valid >= 5/6, sacrificed legs ~0, pure-walk det progress_ratio not hard-regressed vs 0.43-0.48. FAIL if wz_med < 0.03 both signs, gait collapses, or progress craters. PARTIAL/DIG-IN if asymmetry persists.

