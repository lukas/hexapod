# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yaw5x-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-31T17:38:47+00:00

**pod**: hexapod-mjx-train-6

**steps**: 38000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-turnpay-acq1

**wandb_id**: ht0e4dui

**hypothesis**: Plain English: can paying the robot 5x more for turning DEFEND the turn authority it already has, where normal pay let it slowly trade turning away for easier income? The mirror-augmented base holds real turn authority (wz_med +-0.13-0.18) through a 2M canary, but under the standard reward stack a full 38M acquisition eroded it 60-75% to the frozen-body band (acq1/acq1-s1, verdicted this cycle) while ep_rew kept rising -- PPO's optimum at 1x yaw pricing is near-zero turn authority. The earlier yawscale5x/15x REFUTATION does not cover this case: those arms started from an ALREADY-FROZEN non-mirrored base (a recovery problem -- pricing cannot make random joint noise rediscover a coordinated multi-joint turn), whereas this arm starts from the mirror canary checkpoint WITH live authority (a retention problem -- pricing only has to make defending an existing behavior worth more than abandoning it). Identical recipe to the failed acq1 (same init ppo_goal_..._mirroraug_turnpay_canary.zip, same levers) except k_walk_yaw/k_yaw_prog 1.0->5.0, plus the new --snapshot-every=5000000 (off-by-default tool, smoke-verified) writing step-tagged checkpoints so the erosion time-constant is finally measurable instead of inferred from 2 endpoints. Prediction-if-true: probe_turn_authority wz_med >= 0.10 both signs at the final ~40M checkpoint and the snapshot curve shows authority holding roughly flat. Prediction-if-false: same erosion curve as acq1 (authority halves by ~10-20M, frozen band by 40M) despite 5x income -- reward-magnitude retention is then also refuted and the next escalation is the per-tick reward-vs-value credit-assignment trace the yawscale canaries named. Strongest alternative: 5x yaw pricing destabilizes or distorts the base walk (overweighted small term) -- caught by the gait_valid and progress_ratio clauses.

**gate**: ACQUISITION retention test. PASS/promote-to-stage2-source if at the final ~40M checkpoint: probe_turn_authority (own TURNCAP_CFG_SET, wz_cmd=+-0.25) wz_med >= 0.10 both signs AND pure-walk (mode_seq=0) det progress_ratio in/above 0.40-0.48 AND det walk gait_valid >= 5/6, zero falls. FAIL (pricing cannot defend authority either) if the snapshot erosion curve matches acq1's shape and final wz_med lands under 0.05 either sign with gait clean. GAIT-BREAK FAIL if gait_valid < 5/6 or progress_ratio collapses (5x term distorts walking) -- then bracket down to 2-3x. PARTIAL otherwise: quantify erosion curve from the _s<steps> snapshots, do not force a binary call.

