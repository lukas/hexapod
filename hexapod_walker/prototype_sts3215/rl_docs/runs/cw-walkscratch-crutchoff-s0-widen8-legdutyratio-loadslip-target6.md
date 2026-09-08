# cw-walkscratch-crutchoff-s0-widen8-legdutyratio-loadslip-target6

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FINISHED

**created**: 2026-09-08T13:46:32+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-crutchoff-s0-widen8-legdutyratio-loadslip

**wandb_id**: ex55c410

**hypothesis**: Does the load-slip charge (0/3 seeds CONTINUE this window at target=1.5/charge=150, closed 'saturated excess, no repair gradient') actually help once its target is calibrated from real data instead of an assume-and-go guess? A new zero-training diagnostic (rl_move/sim/calibrate_loadslip_target.py, replays the ALREADY-PASSED guardfix1-s0 champion's own deterministic walk with goal.walk_contact_diagnostics=1, the existing default-off zero-reward-effect per-foot telemetry) measured this lineage's own worst-leg peer-ratio distribution: p10=1.47, p50=2.19, p90=6.57 (n=7110 walk ticks, 6 episodes) -- the assumed target=1.5 sits at the population's own p10, meaning the charge (excess-above-target, high-is-bad) fires on ~90% of ticks for an ALREADY-GOOD gait instead of only the genuinely-anomalous tail, exactly the saturated/always-on shape the closed batch measured (excess stuck 0.86-1.04 all run). This mirrors duty-ratio's own calibration convention (target = passing population's own extreme percentile) but on the CORRECT side for an excess-is-bad charge: p90, not p10. Single-lever change vs the closed loadslip-s0 sibling: target 1.5->6.0 only, same charge=150/seed/lineage/budget.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY: (a) telemetry (env/walk_leg_loadslip_ratio_excess, env/reward_walk_leg_loadslip_ratio) finite and NOT saturated near a fixed ceiling the whole post-grace window (the closed batch's own failure signature) -- if it still saturates, the target is still miscalibrated or the mechanism itself doesn't help, report which. (b) zero new falls vs the matched 0.30-dose guardfix1 sibling. (c) same >=3/4-groups-jointly-improve read as the closed batch, now with a target that should leave an actual gradient instead of a constant tax -- PASS-worth-CONTINUE if >=3/4, otherwise report the count same as the closed batch (this is one more single-seed read, not a re-open of the 0/3 majority verdict unless this lever changes the picture).

