# cw-walkscratch-crutchoff-s0-widenrear180-legdutyratio-swingfloor

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-08T12:26:31+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenrear180-legdutyratiofresh-guardfix1

**hypothesis**: 3rd-lineage swing-floor generalization check (see widen8 s0/s1/s2 trio + widenbis180-s0 siblings): widenrear180 is the single-new-heading (180deg only) widen that closed CANARY FAIL 3/3 seeds with the strongest cross-seed-identical chronic leg-0 fingerprint of any variant. One-lever respec of this lineage's own matched 0.30-dose guardfix1 baseline (same seed2/init-from crutchoff_s0_acq1.zip/heading-set/DR/motor cfg, launched in parallel), adding ONLY the >=2-qualifying-swing/4s-window floor. Read alongside widen8 (mixed 3/4 vs 0/4 across seeds) and widenbis180 (pending): a 3rd independent lineage tips whether the lever's occasional efficacy is real-but-noisy or an artifact of one seed/lineage.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. (a) post-grace env/walk_leg_duty_ratio_shortfall and env/reward_walk_leg_duty_ratio must appear, finite, in real GPU telemetry. (b) zero new falls/terminations vs the matched 0.30-dose widenrear180 guardfix1 sibling at the same seed/budget. (c) same joint gait_valid-AND-slip/progress comparison the widen8/widenbis180 swingfloor arms used: >=3/4 groups must jointly improve (not gait_valid alone) vs the matched 0.30-dose sibling for a CONTINUE signal; report whether the leg-0 sacrifice persists. A short 2M null does not close the lever alone; read together with the widen8 trio and widenbis180 rather than in isolation.

**refused_reason**: config twin of RUNNING cw-walkscratch-crutchoff-s0-widenbis180-legdutyratio-swingfloor (identical train args+steps; a seed twin would differ in --seed — pass --allow-twin only for a deliberate replica)

