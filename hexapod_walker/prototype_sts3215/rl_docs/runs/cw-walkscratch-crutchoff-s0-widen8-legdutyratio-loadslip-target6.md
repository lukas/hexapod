# cw-walkscratch-crutchoff-s0-widen8-legdutyratio-loadslip-target6

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-08T13:46:32+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-crutchoff-s0-widen8-legdutyratio-loadslip

**wandb_id**: ex55c410

**hypothesis**: Does the load-slip charge (0/3 seeds CONTINUE this window at target=1.5/charge=150, closed 'saturated excess, no repair gradient') actually help once its target is calibrated from real data instead of an assume-and-go guess? A new zero-training diagnostic (rl_move/sim/calibrate_loadslip_target.py, replays the ALREADY-PASSED guardfix1-s0 champion's own deterministic walk with goal.walk_contact_diagnostics=1, the existing default-off zero-reward-effect per-foot telemetry) measured this lineage's own worst-leg peer-ratio distribution: p10=1.47, p50=2.19, p90=6.57 (n=7110 walk ticks, 6 episodes) -- the assumed target=1.5 sits at the population's own p10, meaning the charge (excess-above-target, high-is-bad) fires on ~90% of ticks for an ALREADY-GOOD gait instead of only the genuinely-anomalous tail, exactly the saturated/always-on shape the closed batch measured (excess stuck 0.86-1.04 all run). This mirrors duty-ratio's own calibration convention (target = passing population's own extreme percentile) but on the CORRECT side for an excess-is-bad charge: p90, not p10. Single-lever change vs the closed loadslip-s0 sibling: target 1.5->6.0 only, same charge=150/seed/lineage/budget.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY: (a) telemetry (env/walk_leg_loadslip_ratio_excess, env/reward_walk_leg_loadslip_ratio) finite and NOT saturated near a fixed ceiling the whole post-grace window (the closed batch's own failure signature) -- if it still saturates, the target is still miscalibrated or the mechanism itself doesn't help, report which. (b) zero new falls vs the matched 0.30-dose guardfix1 sibling. (c) same >=3/4-groups-jointly-improve read as the closed batch, now with a target that should leave an actual gradient instead of a constant tax -- PASS-worth-CONTINUE if >=3/4, otherwise report the count same as the closed batch (this is one more single-seed read, not a re-open of the 0/3 majority verdict unless this lever changes the picture).

**verdict**: CANARY FAIL - MECHANISM (short of the CONTINUE bar, single seed): recalibrating walk_leg_loadslip_ratio_target from the wrong-side p10=1.5 to the correct-side p90=6.0 DID fix the saturation diagnosis -- the few telemetry samples logged show excess 0.02-0.025 (not stuck near a fixed ceiling like the closed target=1.5 batch's 0.86-1.0), and 0 falls anywhere in the held-out panel (matches the 0-fall parent). But efficacy is still short of the pre-registered >=3/4-groups-jointly-improve bar: only 2/4 groups clearly improve vs the matched guardfix1-s0 parent (walk/det: slip 10.09->9.55, fwd 0.36->0.61m, gait_valid 5/6->6/6; walk/sto: slip 8.13->7.37, fwd flat at ~1.00m, gv flat 6/6), while the other 2 are flat-to-mildly-worse (walk_startjitter/det: slip 9.42->9.17 flat, fwd 0.72->0.66m slightly down; walk_startjitter/sto: slip 12.32->12.37 flat, fwd 0.62->0.59m slightly down). Training ep_rew_mean collapsed hugely in the back half (quarters 34/56/-1058/-6806) -- same shape already characterized for this mechanism's target=1.5 sibling (charge's own uncapped weight=150 dominating raw PPO reward without moving the exported best-checkpoint's actual walking behavior), not a new anomaly. Net: mechanism confirmed healthy post-calibration, but this single seed does not clear the bar to fund a cont10m depth read; consistent with the closed 0/3 majority, calibration alone is not the fix -- needs either a lower charge weight (so it stops dominating the PPO objective scale) or the mechanism is not the right lever for this composite.

