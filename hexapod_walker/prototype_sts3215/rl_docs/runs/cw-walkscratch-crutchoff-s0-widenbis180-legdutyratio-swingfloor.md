# cw-walkscratch-crutchoff-s0-widenbis180-legdutyratio-swingfloor

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T12:19:35+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbis180-legdutyratiofresh-guardfix1

**wandb_id**: zhzgirlp

**hypothesis**: Generalization check for the swing-count-floor lever across heading-widening SEVERITY, not just seed: the widen8 lineage's own 3-seed tie-break (s0 3/4 groups improve, s1 0/4, s2 launched this window) tests the lever on the harsher 8-way heading set; this arm tests the SAME lever (identical swing_min_count=2/window=4s addition) on the milder 6-way widenbis180 lineage's own matched 0.30-dose guardfix1 baseline (same seed2/init-from crutchoff_s0_acq1.zip/heading-set/DR/motor cfg as that PASSED baseline). If the milder lineage (which itself only barely cleared its own bar at 18/24 gait_valid pre-swingfloor) shows the same swing-floor-driven joint gv+slip/progress improvement pattern as widen8-s0, that argues the mechanism helps independent of how many new headings were added; if it shows s1's null instead, that argues the effect (where present) is seed-specific rather than lineage-specific.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. (a) post-grace env/walk_leg_duty_ratio_shortfall and env/reward_walk_leg_duty_ratio must appear, finite, in real GPU telemetry. (b) zero new falls/terminations vs the matched 0.30-dose widenbis180 guardfix1 sibling at the same seed/budget. (c) same joint gait_valid-AND-slip/progress comparison the widen8 swingfloor arms used: >=3/4 groups must jointly improve (not gait_valid alone) vs the matched 0.30-dose sibling for a CONTINUE signal; report whether the leg-0 sacrifice trade seen at 0.30 dose persists. A short 2M null does not close the lever alone; read together with the widen8 s0/s1/s2 trio rather than in isolation.

