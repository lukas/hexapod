# cw-walkcurr-sac-sv-tilt10-s1-r2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-29T22:48:23+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkcurr-sac-sv-tilt5-s1

**wandb_id**: k10vklkg

**hypothesis**: Plain English: closes the SAC anti-tilt dose-response axis at the codebase's FULL default dose (k_roll=k_pitch=10.0, vs the sibling tilt5-s1's 5.0 and tilt2-s1's 2.0). tilt5-s1 showed a REAL monotone dose-response vs tilt2 (walk/det forward_dist_m median 0.024m identical-instant-fall -> 0.055m varied-stepping, gait_valid False->True 5/6) but still missed both PASS bars (24/24 falls remain; 0.055m < the 0.06m continue ceiling) and a new over_current failure mode partially replaced pure tilt falls. IDENTICAL SV diet/seed(1)/algo(SAC)/budget(2M) as both siblings -- only the tilt dose changes, now maxed at the value the rest of the codebase already trusts by default. WALKCURR_SV_TILT bank extended to dose=10.0 and reverified (9/9 green, travel still beats every stationary/wrong-way form, topple still the strict floor) before this launch. (This is the -r2 retry of cw-walkcurr-sac-sv-tilt10-s1, whose first attempt was a LAUNCH_CRASH on hexapod-mjx-train-1's stale CPU-only torch, root-caused+fixed this cycle, not a science result -- same hypothesis carries over.) Prediction-if-true (response continues): fall rate drops below 24/24 and/or forward_dist_m median clears ~0.06m -- tilt-pricing alone is the fix, promote toward the rung-1 bar. Prediction-if-false (saturates): forward_dist/gait_valid look about the same as tilt5 (0.05-0.06m band, similar gait_valid) -- dose axis is flat past 5.0, no further gain from raising it more; fork to reward-shape-during-settle-window or the off-policy-SAC-probe/terrain fallback ladder. Prediction-if-reverses (over-priced, the pre-registered risk): walk_speed pinned near 0, policy regresses toward the static-quiver basin seen across the decleg/central/phase-sv waves -- also closes the axis, same fork, and specifically indicts the over_current signature emerging at dose 5.0 as the leading edge of that regression rather than of the fix.

**gate**: Rung-1 C-env det+sto fixed-forward panel (n>=6 each) at 2M, same harness as the tilt2/tilt5 siblings: PASS/continue-worthy needs fall rate below 24/24 det+sto OR forward_dist_m median clearing ~0.06m. Read as a 3-point dose curve (2.0/5.0/10.0) against forward_dist_m median and gait_valid fraction: monotone-improving-but-still-failing => the tilt-alone lever is real but insufficient at any safe dose, move to reward-shape-during-settle-window; flat/saturated vs tilt5 => stop the dose axis here, same fork; reversed (worse than tilt5, speed pinned near 0) => over-tilt-priced, same fork plus flag over_current as the regression's leading indicator.

