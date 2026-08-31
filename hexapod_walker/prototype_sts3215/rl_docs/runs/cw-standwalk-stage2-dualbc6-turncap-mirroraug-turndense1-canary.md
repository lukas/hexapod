# cw-standwalk-stage2-dualbc6-turncap-mirroraug-turndense1-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-31T19:34:32+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-turnpay-canary

**wandb_id**: unzxo9ex

**hypothesis**: Plain English: does giving the critic MORE turn-in-place ticks to learn from (denser exposure, no reward-weight change) fix the credit-assignment blindness probe_yaw_credit just found on THIS mirror-augmented lineage (15/16 probes across the base distillation, both RL doses 1x/5x, and both seeds all read CREDIT-BLIND/CREDIT-PUNISHES on the forward-only value_delta signal -- the critic's own belief about the future barely reacts to whether a tick nudges the body toward the commanded turn direction), or does it need architecture-side conditioning instead? Single lever vs the exact turnpay-canary recipe: goal.walk_turn_in_place_frac 0.30->0.60 (2x the fraction of walk episodes that include a turn-in-place segment), same reward weights (k_walk_yaw/k_yaw_prog=1.0, unchanged from the already-refuted-at-5x reward-magnitude axis), same init-from (the raw dualbc6_turncap_mirroraug distillation checkpoint, matching the original canary's own starting point), --snapshot-every=500000 for a curve. Prediction-if-true: probe_yaw_credit forward_verdict flips to CREDIT-REWARDS (or corr_toward_value_delta>=+0.15) on a majority of the 4 wz_cmd x seed-internal probes AND probe_turn_authority wz_med still clears >=0.10 both signs at 2M (matching or beating the original canary). Prediction-if-false: forward_verdict stays BLIND/PUNISHES despite 2x turn-segment density -> the defect is architectural (dual-core GRU wz-conditioning/bootstrap horizon), not a data-density problem, and the next escalation is an explicit critic-side feature or value-warmup phase, not more density. Strongest alternative: 2x density could just as easily dilute WALK-forward quality (a farmed 'turn cred' at the cost of straight-walk regression is not a win) -- caught by the gait/progress clauses.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS if probe_yaw_credit (run myself, not auto-prestaged) forward_verdict is CREDIT-REWARDS (or corr_toward_value_delta>=+0.15) on >=3/4 of the wz_cmd=+-0.25 x seed-internal-probe combos on the 2M checkpoint AND probe_turn_authority wz_med>=0.10 both signs AND det walk gait_valid>=5/6 with clean progress (no farmed-turn-via-gait-collapse). FAIL if forward_verdict stays BLIND/PUNISHES on >=3/4 of combos (data-density lever refuted, escalate to architecture/critic-feature fix) regardless of wz_med. PARTIAL if wz_med improves/holds but credit signal is mixed, or credit flips but wz_med/gait regresses (turn-cred bought by walk-quality cost).

