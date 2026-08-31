# cw-standwalk-stage2-dualbc6-turncap-mirroraug-stillbal-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-31T20:00:15+00:00

**pod**: hexapod-mjx-train-0

**steps**: 38000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yaw5x-acq1

**wandb_id**: u0dvwfqe

**hypothesis**: Plain English: does the robot stop trading turning away once standing-still stops paying 10x more than turning pays? The credit-assignment trace this dig-in ran (probe_yaw_credit + new income accounting; logs/ckpt_eval/yaw_credit_{mirroraug_canary_init,yaw5x_acq1_s5M,yaw5x_acq1_final}_5xcfg.json) PROVED turning is net-profitable per tick under the full 5x training reward (the turning canary-init earns 4.59-5.37/tick vs the eroded final's 3.30-4.31 at identical cfg; penalties negligible; TD quartile gap +6/tick in FAVOR of toward-command ticks) and the critic is a degenerate near-constant (V literally 15.174 across both command signs at the final ckpt; value_delta flat, gaps <=0.01) — so the erosion pressure cannot come from the turn segments themselves. The one channel the constant-command probe cannot see and no prior arm ever touched: reward.k_yaw_still=50 prices rotation on the ~50% zero-yaw-cmd walk segments at 10x the turn income coefficient (50 vs 5 even in the 'yaw5x' arm; 50 vs 1 at 1x), with a ~1s EMA tail taxing every turn->hold transition — an asymmetry that makes 'never rotate anywhere' the optimum for shared GRU weights generalizing across the command boundary. This arm is IDENTICAL to the refuted yaw5x-acq1 (same init ppo_goal_..._mirroraug_turnpay_canary.zip, same 5x turn income, same --snapshot-every=5M) except reward.k_yaw_still 50->5 (symmetric rotation pricing) — one variable, curve-comparable point-by-point to yaw5x-acq1's measured snapshot erosion curve. Prediction-if-true: 5M/10M/15M snapshots hold wz_med materially above yaw5x-acq1's measured floor (pos 0.067 at 5M, 0.03-0.05 by 15M) and the final ~38M reads >=0.10 both signs. Prediction-if-false: same fast-early erosion — pricing asymmetry refuted, remaining suspect is architecture (command-conditioned critic), which is tool-building, not another coefficient. Strongest alternative: cutting k_yaw_still 10x resurrects the structural heading-hold drift it was priced to kill (~0.09 rad/s) — caught by the drift clause.

**gate**: ACQUISITION retention test, one-variable control vs cw-standwalk-stage2-dualbc6-turncap-mirroraug-yaw5x-acq1 (k_yaw_still 50->5 is the ONLY change). PASS/promote if final ~38M probe_turn_authority (own cfg minus goal.mode_seq, wz_cmd=+-0.25) wz_med >= 0.10 both signs AND det walk gait_valid >= 5/6 zero falls AND pure-walk det progress_ratio in/above 0.40-0.48. FAIL (pricing-asymmetry retention refuted) if the _s<steps> snapshot curve matches yaw5x-acq1's measured shape (pos ~0.067-0.073 at 5M, at/under the 0.03-0.05 floor by 15-20M) — then the named escalation is a command-conditioned critic (architecture/tool work), not another coefficient. DRIFT-BREAK FAIL if zero-cmd heading-hold drift returns (direction_err/course income collapse vs parent beyond eval noise) — then bracket k_yaw_still 12.5-25. PARTIAL otherwise: quantify both curves, joint read with the seed twin.

