# cw-standwalk-stage2-dualbc5-turncap-turnpay-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-31T02:37:30+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc4-walkteach-turnpay-canary

**wandb_id**: f5hajpxg

**hypothesis**: Plain English: if the stage-2 base is distilled from a walk-teacher that never forgot how to turn (bc1_std25, pre-RL) instead of the turn-amnesiac acq12m, the same bank-proven direct-yaw-income reward stack that failed twice on acq12m-derived bases should finally produce real turn-in-place authority. Delta vs turnpay-canary/-s1 (both CANARY FAIL - MECHANISM, wz_med~0 both signs): ONLY the stage-2 distillation base changes (dualbc5_turncap, distilled from bc1_std25 walk-teacher with denser turn exposure: walk_yaw_zero_frac 1.0->0.5, walk_turn_in_place_frac 0->0.30) plus the same OMNI turn reward stack (k_walk_yaw, walk_yaw_kernel_gate, k_yaw_prog+overshoot-decay, k_yaw_still+yaw_still_avg_s, walk_yaw_hold_prog_gate), same mix/DR as turnpay. Pre-RL evidence the base is different: probe_turn_authority on the RAW distilled checkpoint (before any RL) already shows a real (if weak, asymmetric) partial escape off frozen-body -- wz_med -0.038/-0.048 for wz_cmd=-0.25 (vs turnpay/turndiet's ~0.0004-0.0023 fully-frozen-both-signs baseline), wz_p90_abs 0.12, though wz_cmd=+0.25 is still ~frozen (wz_med~0.00003) -- confirmed not a probe artifact via the scripted-gait sanity control on the identical cfg (symmetric wz_med~+-0.21 both signs). Prediction-if-true: probe_turn_authority on the trained 2M checkpoint clears wz_med>=0.08 BOTH signs (RL amplifies and symmetrizes the asymmetric pre-RL seed). Prediction-if-false: wz_med stays <0.03 (or stays asymmetric/frozen on the +0.25 side) -> even a turn-capable distillation base plus direct yaw income cannot produce turn authority at 2M, escalating past reward/diet/distillation-base tuning into architecture (this dual-core GRU's wz obs embedding itself) or an even more turn-saturated re-harvest. Strongest alternative: the asymmetry itself is diagnostic -- if the trained checkpoint stays asymmetric (one sign tracks, the other frozen), that points at a sign/obs-encoding bug in the wz command channel rather than a capacity limit, worth a code read before another reward sweep.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, joint with seed1 twin. PASS/promote if BOTH seeds show probe_turn_authority (checkpoint own cfg, wz_cmd=+-0.25, walk-mode-filtered) wz_med >= 0.08 both signs, det walk gait_valid >= 5/6, sacrificed legs ~0, and pure-walk (mode_seq OFF) det progress_ratio not hard-regressed vs the wave-1 band 0.43-0.48. FAIL if wz_med < 0.03 both signs (still frozen) or gait collapses or straight-walk progress craters. PARTIAL/DIG-IN if the pre-RL asymmetry persists (one sign tracks >=0.08, the other stays <0.03) -- new information (sign-specific defect) not covered by the clean PASS/FAIL disjunction, escalate rather than snap-verdict. Do not judge mature turn quality or close the reward class at 2M.

