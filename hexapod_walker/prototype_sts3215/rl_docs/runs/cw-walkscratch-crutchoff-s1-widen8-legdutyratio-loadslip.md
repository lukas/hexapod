# cw-walkscratch-crutchoff-s1-widen8-legdutyratio-loadslip

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T13:10:33+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8-acq1-legdutyratiofresh-guardfix1

**wandb_id**: c53162rm

**hypothesis**: Seed1 twin of the s0 load-slip-charge canary launched this same window: does the peer-excluded-MEDIAN load-slip ratio charge (target 1.5, charge 150), on top of the existing 0.30-dose duty-ratio charge, fix the gait_valid-recovers-via-worse-slip trade that dose escalation and the swing-count-floor both failed to fix on this seed. Same seed1/init-from/heading-set/DR/motor cfg as the matched 0.30-dose s1 guardfix1 sibling, only the new load-slip charge added.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. (a) post-grace env/walk_leg_loadslip_ratio_excess and env/reward_walk_leg_loadslip_ratio must appear, finite, in real GPU telemetry. (b) zero new falls/terminations vs the matched 0.30-dose s1 guardfix1 sibling at the same seed/budget. (c) same joint gait_valid-AND-slip/progress comparison the swing-floor arms used: >=3/4 groups must jointly improve vs that sibling for a CONTINUE signal; report whether the gait_valid-recovers/slip-worsens trade persists. Read together with s0/s2 siblings: majority (>=2/3 seeds hitting >=3/4) funds a cont10m depth read; minority does not.

