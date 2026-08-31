# cw-standwalk-stage2-dualbc5-turncap-turnpay-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-08-31T02:46:14+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc5-turncap-turnpay-canary

**wandb_id**: oqo536zn

**hypothesis**: Seed-1 twin of cw-standwalk-stage2-dualbc5-turncap-turnpay-canary (same hypothesis, config, and gate) — checks the partial pre-RL turn-authority escape (asymmetric wz_med -0.038/-0.048 for wz_cmd=-0.25 vs frozen +0.25) is not a single-seed fluke before promoting/killing the dualbc5_turncap distillation-base fix.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as seed0: MECHANISM-HEALTH CANARY ONLY, joint with seed0. PASS/promote if BOTH seeds show probe_turn_authority wz_med >= 0.08 both signs, det walk gait_valid >= 5/6, sacrificed legs ~0, pure-walk det progress_ratio not hard-regressed vs 0.43-0.48. FAIL if wz_med < 0.03 both signs, gait collapses, or progress craters. PARTIAL/DIG-IN if asymmetry persists.

**verdict**: CANARY FAIL - MECHANISM (joint with seed0 twin cw-standwalk-stage2-dualbc5-turncap-turnpay-canary; same finding both checkpoints). Result: probe_turn_authority (own cfg, wz_cmd=+-0.25, walk-mode-filtered, controller-side CPU rollout on the synced checkpoint) on this seed's POST-RL checkpoint gives wz_med +0.0009/+0.0035 (wz_cmd=+0.25, seeds 0/1) and -0.0217/-0.0090 (wz_cmd=-0.25, seeds 0/1) -- every reading under the 0.03 frozen-body FAIL threshold both signs, so the gate's own disjunctive FAIL clause ('wz_med < 0.03 both signs') is met outright; PARTIAL/DIG-IN does not apply since neither sign reaches even the 0.03 floor, let alone the 0.08 PASS bar. Twin seed0 checkpoint probed identically (same 96-key cfg-set, same tool invocation) for the joint read: wz_med -0.0001/-0.0018 (+0.25) and -0.0243/-0.0083 (-0.25) -- same frozen-body shape. Cross-checked against training telemetry (both runs' wandb_history.csv): env/walk_yaw_kernel_factor erodes 0.31-0.33 -> 0.06-0.09 over the run, env/walk_wz stays pinned in [-0.012,+0.004] the whole 2M budget on both seeds -- identical erosion signature to the already-FAILed turndiet/turnpay-walkteach canaries, confirming this is real and reproducible, not eval noise. DECISIVE NEW FINDING vs the pre-registration: this canary existed specifically because the PRE-RL dualbc5_turncap distillation (bc1_std25 walk-teacher + turn ticks in the diet) showed a real, if weak+asymmetric, partial escape off frozen-body (wz_cmd=-0.25 gave wz_med -0.038/-0.048 pre-RL). Post-RL, that partial signal did not survive intact -- it SHRANK to -0.008/-0202 (roughly 2-5x smaller in magnitude), while the +0.25 direction stayed at ~0 both before and after. So the bank-proven OMNI turn reward stack (k_walk_yaw, walk_yaw_kernel_gate, k_yaw_prog+overshoot-decay, k_yaw_still=50, walk_yaw_hold_prog_gate) applied on top of a turn-capable base ERODED rather than amplified the pre-existing partial turn authority. This refutes the diet/teacher-fix hypothesis at the RL stage: fixing the distillation base (turncap) was necessary but not sufficient -- something in the RL training itself (reward stack, BC-anchor pull, or PPO exploration collapse) actively destroys turn signal that demonstrably existed going in. Not further root-caused this cycle (disjunctive FAIL clause already decisive; deeper mechanism analysis -- e.g. whether the phase-locked BC anchor's omega-driven scripted-gait supervision is being correctly weighted during turn-in-place ticks vs being drowned by the majority straight-walk ticks under bc_anchor_coef=3.0 -- is real follow-up work, not needed to close this canary's own pre-registered gate).

