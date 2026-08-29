# cw-walkcurr-sac-sv-tilt10-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: LAUNCH_CRASH

**created**: 2026-08-29T22:33:30+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkcurr-sac-sv-tilt5-s1

**hypothesis**: Plain English: closes the SAC anti-tilt dose-response axis at the codebase's FULL default dose (k_roll=k_pitch=10.0, vs the sibling tilt5-s1's 5.0 and tilt2-s1's 2.0). tilt5-s1 showed a REAL monotone dose-response vs tilt2 (walk/det forward_dist_m median 0.024m identical-instant-fall -> 0.055m varied-stepping, gait_valid False->True 5/6) but still missed both PASS bars (24/24 falls remain; 0.055m < the 0.06m continue ceiling) and a new over_current failure mode partially replaced pure tilt falls. IDENTICAL SV diet/seed(1)/algo(SAC)/budget(2M) as both siblings -- only the tilt dose changes, now maxed at the value the rest of the codebase already trusts by default. WALKCURR_SV_TILT bank extended to dose=10.0 and reverified (9/9 green, travel still beats every stationary/wrong-way form, topple still the strict floor) before this launch. Prediction-if-true (response continues): fall rate drops below 24/24 and/or forward_dist_m median clears ~0.06m -- tilt-pricing alone is the fix, promote toward the rung-1 bar. Prediction-if-false (saturates): forward_dist/gait_valid look about the same as tilt5 (0.05-0.06m band, similar gait_valid) -- dose axis is flat past 5.0, no further gain from raising it more; fork to reward-shape-during-settle-window or the off-policy-SAC-probe/terrain fallback ladder. Prediction-if-reverses (over-priced, the pre-registered risk): walk_speed pinned near 0, policy regresses toward the static-quiver basin seen across the decleg/central/phase-sv waves -- also closes the axis, same fork, and specifically indicts the over_current signature emerging at dose 5.0 as the leading edge of that regression rather than of the fix.

**gate**: Rung-1 C-env det+sto fixed-forward panel (n>=6 each) at 2M, same harness as the tilt2/tilt5 siblings: PASS/continue-worthy needs fall rate below 24/24 det+sto OR forward_dist_m median clearing ~0.06m. Read as a 3-point dose curve (2.0/5.0/10.0) against forward_dist_m median and gait_valid fraction: monotone-improving-but-still-failing => the tilt-alone lever is real but insufficient at any safe dose, move to reward-shape-during-settle-window; flat/saturated vs tilt5 => stop the dose axis here, same fork; reversed (worse than tilt5, speed pinned near 0) => over-tilt-priced, same fork plus flag over_current as the regression's leading indicator.

**failed_reason**: pod-level infra defect, not a science result: hexapod-mjx-train-1's torch was stale-reverted to the bootstrap CPU-only build (2.13.0+cpu, torch.cuda.is_available()=False) despite an 08-15 durable-capability record claiming it CUDA-capable -- the pod was recreated/recycled since and the record was never re-verified before this launch trusted it. --require-gpu-physics correctly fail-closed (SystemExit at boot, 0 training steps, W&B never appeared) rather than silently falling back to a slow/wrong config. Fixed: pod_torch_capability.py install re-run on train-1 (now genuinely CAPABLE, re-verified) AND on train-8 (separately known-broken since 08-24, also fixed proactively). Relaunching tilt10-s1 pinned to an already-verified-capable free pod.

