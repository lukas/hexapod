# cw-walkscratch-crutchoff-s2-widen8-legdutyratio-loadslip

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-08T13:13:37+00:00

**pod**: hexapod-mjx-train-8

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-widen8-acq1-legdutyratiofresh-guardfix1

**hypothesis**: Seed2 twin of the s0/s1 load-slip-charge canaries launched this same window (the pre-registered n=3 batch, learning from today's own lesson that n=2 swing-floor reads needed a 3rd tie-break twice): does the peer-excluded-MEDIAN load-slip ratio charge (target 1.5, charge 150), on top of the existing 0.30-dose duty-ratio charge, fix the gait_valid-recovers-via-worse-slip trade. Same seed2/init-from/heading-set/DR/motor cfg as the matched 0.30-dose s2 guardfix1 sibling, only the new load-slip charge added.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. (a) post-grace env/walk_leg_loadslip_ratio_excess and env/reward_walk_leg_loadslip_ratio must appear, finite, in real GPU telemetry. (b) zero new falls/terminations vs the matched 0.30-dose s2 guardfix1 sibling at the same seed/budget. (c) same joint gait_valid-AND-slip/progress comparison the swing-floor arms used: >=3/4 groups must jointly improve vs that sibling for a CONTINUE signal; report whether the gait_valid-recovers/slip-worsens trade persists. Read together with s0/s1 siblings: majority (>=2/3 seeds hitting >=3/4) funds a cont10m depth read; minority does not -- this seed decides ties.

