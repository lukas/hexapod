# cw-walkcurr-sac-sv-tilt5-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-29T21:37:53+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkcurr-sac-sv-s1

**wandb_id**: 12ddmjla

**hypothesis**: Plain English: same question as cw-walkcurr-sac-sv-tilt2-s1 (does pricing tilt directly fix SAC's stumble-then-fall pattern) at a HIGHER dose (5.0, half the codebase's full default 10.0, vs the sibling arm's 2.0) so the two arms together read as a dose-response, not a single guess. IDENTICAL SV diet/seed/algo/budget as cw-walkcurr-sac-sv-s1, only the k_roll/k_pitch dose differs from the tilt2 sibling. WALKCURR_SV_TILT bank (6/6 green, both 2.0 and 5.0 doses) confirms this dose does not disturb the travel>stationary>wrongway>topple ranking either. Prediction-if-true: fall rate/forward_dist improve MORE than the tilt2 sibling (monotone dose-response) at 2M. Prediction-if-false: no improvement, or improvement saturates/reverses vs tilt2 (over-pricing tilt suppresses the exploration that found stepping in the first place, regressing toward the PPO static-quiver basin) -- either result closes the dose axis and forks to reward-shape design (e.g. gate the charge off during the settle window) or the SAC checkpoint-continuation build instead of more dose.

**gate**: Rung-1 C-env det+sto fixed-forward panel (n>=6 each) at 2M, same harness as cw-walkcurr-sac-sv-s1: PASS/continue-worthy needs fall rate below 24/24 det+sto OR forward_dist_m median clearing ~0.06m (2x the sv-s1/budget10m ceiling); track-level PASS still needs the full rung-1 bar (progress_ratio>=0.35, slip/m<=3.0, gait_valid>=4/6, falls<=1/6 det). FAIL: still ~24/24 falls at the same roll_peak/forward_dist with flat reward, or a regression to walk_speed pinned near 0 (over-tilt-priced) -- dose axis closed either way.

**verdict**: Dose 5.0 anti-tilt (k_roll=k_pitch=5.0) does NOT clear the gate but IS a genuine monotone dose-response vs the tilt2 sibling (2.0), not a flat/reversed one. Evidence: walk/det forward_dist_m went from tilt2's deterministic identical 0.024m/6-of-6 (same instant sideways topple every seed, gait_valid False all 6) to a varied 0.005-0.076m spread, median 0.055m (roll_peak stays ~10deg, unchanged) with gait_valid True 5/6 -- the policy is genuinely stepping through more of the episode before falling, not just failing identically. It still misses BOTH pre-registered PASS bars: fall rate stays 24/24 across det+sto+startjitter, and forward_dist median (0.055m det, 0.044m sto) sits just under the 0.06m continue-worthy ceiling. Termination signature also partially shifted: 2/6 det and 4/6 sto now die via over_current rather than pure tilt, a new competing failure mode at this dose. ep_rew_mean quarters [159.6,142.1,143.2,150.2] flat/noisy, no rising trend -- 08-21 ruling requires rising reward to justify continue-without-gate, which this doesn't have, so this closes as FAIL against the pre-registered gate. Per the STATUS.md pre-registered fork ('a monotone dose-response opens a bigger-dose follow-up instead' of jumping straight to reward-shape/off-policy-SAC-probe fallback), extending WALKCURR_SV_TILT bank to dose=10.0 (codebase full default, 9/9 green) and launching cw-walkcurr-sac-sv-tilt10-s1 same-cycle to read whether the response continues, saturates, or reverses toward the predicted quiver-basin regression.

