# cw-walkcurr-sac-sv-tilt2-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-08-29T21:35:42+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-walkcurr-sac-sv-s1

**hypothesis**: Plain English: cw-walkcurr-sac-sv-s1-budget10m showed SAC learns real 6-leg stepping at the commanded speed but falls via tilt_roll/tilt_pitch in 24/24 held-out episodes, and 5x more budget alone did not fix it -- because the SV diet has zero balance-shaping gradient (k_roll=k_pitch=0, only a one-time -24 charge AT the fall). This arm adds back a MILD dose (2.0, vs the codebase's own full default 10.0) of the pre-existing k_roll/k_pitch quadratic tilt penalty on top of the IDENTICAL SV diet/seed/algo/budget as cw-walkcurr-sac-sv-s1 -- the only lever is the tilt price. WALKCURR_SV_TILT bank (6/6 green) confirms this dose does not disturb the travel>stationary>wrongway>topple ranking. Prediction-if-true: held-out rung-1 panel at 2M shows fewer than 24/24 falls and/or forward_dist_m clears the ~0.03-0.05m ceiling s1 was stuck at. Prediction-if-false: still ~24/24 falls at the same roll_peak/forward_dist -- a mild dose is too weak relative to the freeprog income scale (~0.4/tick) to matter, escalate to the higher dose (tilt5-s1, launched alongside) or a bigger dose still. Strongest alternative: the extra charge suppresses exploration entirely and the run regresses to the PPO static-quiver basin (walk_speed pinned near 0) -- that outcome also answers the question (tilt pricing traded one failure mode for the other) and forks to reward-shape design (e.g. gate the charge off during the settle window) rather than more dose.

**gate**: Rung-1 C-env det+sto fixed-forward panel (n>=6 each) at 2M, same harness as cw-walkcurr-sac-sv-s1: PASS/continue-worthy needs fall rate below 24/24 det+sto OR forward_dist_m median clearing ~0.06m (2x the sv-s1/budget10m ceiling); track-level PASS still needs the full rung-1 bar (progress_ratio>=0.35, slip/m<=3.0, gait_valid>=4/6, falls<=1/6 det). FAIL: still ~24/24 falls at the same roll_peak/forward_dist with flat reward -- try the higher dose or gate the charge off during the settle window.

