# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-01T12:06:18+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-canary

**wandb_id**: mtf7nzbp

**hypothesis**: Plain English: gradclip0p15 (seed 0) gave the best turn-authority result of the whole campaign (wz_med 0.198/-0.200, overshooting the 0.083/-0.138 control, AND fixing the walk-quality collapse) -- is that a basin-luck fluke of this one seed, or does the tight trust-region clip reproduce on a second seed the way the mirror-augment BC-base fix did (turnpay-canary/-s1, 2/2)? Cheap 2M seed-robustness check BEFORE the 38M acquisition continuation (already launched off seed0) commits budget to a single basin.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS if seed1's own probe_turn_authority wz_med clears >=0.15 both signs (same bar the seed0 arm cleared with margin) AND own purewalk det gait_valid>=5/6 zero falls AND progress_ratio/slip match control band (prog>=0.35, slip<=3.0). PARTIAL if wz_med lands 0.05-0.15 (real but weaker retention) or gait/progress are softer but not collapsed. FAIL if wz_med<0.05 both signs (matching rr1/gradclip2p0's collapse) or progress/slip collapse the same way -- seed0's result would then be basin-specific, not a recipe property; the 38M acquisition arm still stands on its own seed0 evidence regardless.

