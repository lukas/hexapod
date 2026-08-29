# cw-walkcurr-sac-sv-tilt5-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-29T21:37:53+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkcurr-sac-sv-s1

**wandb_id**: 12ddmjla

**hypothesis**: Plain English: same question as cw-walkcurr-sac-sv-tilt2-s1 (does pricing tilt directly fix SAC's stumble-then-fall pattern) at a HIGHER dose (5.0, half the codebase's full default 10.0, vs the sibling arm's 2.0) so the two arms together read as a dose-response, not a single guess. IDENTICAL SV diet/seed/algo/budget as cw-walkcurr-sac-sv-s1, only the k_roll/k_pitch dose differs from the tilt2 sibling. WALKCURR_SV_TILT bank (6/6 green, both 2.0 and 5.0 doses) confirms this dose does not disturb the travel>stationary>wrongway>topple ranking either. Prediction-if-true: fall rate/forward_dist improve MORE than the tilt2 sibling (monotone dose-response) at 2M. Prediction-if-false: no improvement, or improvement saturates/reverses vs tilt2 (over-pricing tilt suppresses the exploration that found stepping in the first place, regressing toward the PPO static-quiver basin) -- either result closes the dose axis and forks to reward-shape design (e.g. gate the charge off during the settle window) or the SAC checkpoint-continuation build instead of more dose.

**gate**: Rung-1 C-env det+sto fixed-forward panel (n>=6 each) at 2M, same harness as cw-walkcurr-sac-sv-s1: PASS/continue-worthy needs fall rate below 24/24 det+sto OR forward_dist_m median clearing ~0.06m (2x the sv-s1/budget10m ceiling); track-level PASS still needs the full rung-1 bar (progress_ratio>=0.35, slip/m<=3.0, gait_valid>=4/6, falls<=1/6 det). FAIL: still ~24/24 falls at the same roll_peak/forward_dist with flat reward, or a regression to walk_speed pinned near 0 (over-tilt-priced) -- dose axis closed either way.

