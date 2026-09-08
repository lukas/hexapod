# cw-walkscratch-crutchoff-s0-widenbis180-legdutyratio-swingfloor

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS - mechanism healthy, no efficacy

**created**: 2026-09-08T12:19:35+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbis180-legdutyratiofresh-guardfix1

**wandb_id**: zhzgirlp

**hypothesis**: Generalization check for the swing-count-floor lever across heading-widening SEVERITY, not just seed: the widen8 lineage's own 3-seed tie-break (s0 3/4 groups improve, s1 0/4, s2 launched this window) tests the lever on the harsher 8-way heading set; this arm tests the SAME lever (identical swing_min_count=2/window=4s addition) on the milder 6-way widenbis180 lineage's own matched 0.30-dose guardfix1 baseline (same seed2/init-from crutchoff_s0_acq1.zip/heading-set/DR/motor cfg as that PASSED baseline). If the milder lineage (which itself only barely cleared its own bar at 18/24 gait_valid pre-swingfloor) shows the same swing-floor-driven joint gv+slip/progress improvement pattern as widen8-s0, that argues the mechanism helps independent of how many new headings were added; if it shows s1's null instead, that argues the effect (where present) is seed-specific rather than lineage-specific.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. (a) post-grace env/walk_leg_duty_ratio_shortfall and env/reward_walk_leg_duty_ratio must appear, finite, in real GPU telemetry. (b) zero new falls/terminations vs the matched 0.30-dose widenbis180 guardfix1 sibling at the same seed/budget. (c) same joint gait_valid-AND-slip/progress comparison the widen8 swingfloor arms used: >=3/4 groups must jointly improve (not gait_valid alone) vs the matched 0.30-dose sibling for a CONTINUE signal; report whether the leg-0 sacrifice trade seen at 0.30 dose persists. A short 2M null does not close the lever alone; read together with the widen8 s0/s1/s2 trio rather than in isolation.

**verdict**: CANARY PASS - mechanism healthy, no efficacy vs the matched 0.30-dose widenbis180 guardfix1 sibling (cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbis180-legdutyratiofresh-guardfix1). Health checks (a)+(b) PASS: walk_leg_duty_ratio_shortfall/reward_walk_leg_duty_ratio telemetry present and rising post-grace (0.088->0.125 vs sibling's comparable trace), and 0 new terminations in all 4 held-out groups (both this run and sibling: 0/6, 0/6, 0/6, 0/6). Efficacy check (c) FAILS exactly like the widen8 s0/s1 trio: gait_valid is IDENTICAL to the sibling in all 4 groups (walk/det 3/6, walk/sto 5/6, walk_startjitter/det 6/6, walk_startjitter/sto 4/6 -- same on both sides), and slip/progress is a wash with more regressions than gains (walk/det slip 8.76 vs 9.01 better but progress 0.94 vs 0.99 worse; walk/sto slip 6.70 vs 7.34 better but progress 1.09 vs 1.18 worse; walk_startjitter/det slip 6.80 vs 6.56 worse, progress 1.23 vs 1.27 worse; walk_startjitter/sto slip 13.12 vs 12.85 worse, progress 0.73 vs 0.70 better). 0/4 groups jointly improve gait_valid AND slip/progress, short of the pre-registered >=3/4 CONTINUE bar. The leg-0 sacrifice trade persists identically: sac=[0] in the same walk/det episodes (0,1,5) on both sides. Reproduces the widen8 s0/s1 null (also 0/4 groups, also identical gait_valid) at the wider widenbis180 dose -- the swing-count-floor lever does not move this recipe's efficacy at either dose tested so far. No further budget from this arm; read together with widen8 s0/s1/s2 as one consistent null rather than isolated results. Evidence: logs/ckpt_eval/cw_walkscratch_crutchoff_s0_widenbis180_legdutyratio_swingfloor_gate/report.json vs .../crutchoff_s0_widenbis180_legdutyratiofresh_guardfix1_gate/report.json; W&B zhzgirlp.

