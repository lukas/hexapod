# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenrear180-legdutyratiofresh-guardfix1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-08T12:23:50+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenrear180

**hypothesis**: 3rd LINEAGE generalization check for walk_leg_duty_ratio_charge (the peer-excluded-mean duty-ratio charge, target=0.30, that CANARY PASSed on both widen8 s0/s1/s2 and widenbis180 s0): widenrear180 is the narrowest single-new-heading widen (5-way + 180deg only) that STILL closed CANARY FAIL - MECHANISM 3/3 seeds (09-07 ~21:0x/~21:2x) with the identical chronic leg-0 sacrifice at identical episode indices across all 3 seeds -- the strongest cross-seed-identical fingerprint of any widen variant, making it the cleanest lineage to test whether the ratio charge (independent of the swing-floor addition) recovers leg-0's peer-relative duty here too. Same seed2/init-from crutchoff_s0_acq1.zip/heading-set(6-way)/DR/motor cfg as the original widenrear180 CANARY FAIL, only the ratio charge added.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as the widen8/widenbis180 guardfix1 gate: PASS if leg-0's peer-relative duty ratio recovers (>=0.22 majority of episodes) and gait_valid >=18/24 with 0 new falls; CONTINUE if reward+gait_valid both trending up but short; FAIL if the same leg-0 sacrifice persists regardless. This run ALSO doubles as the matched 0.30-dose baseline for the widenrear180 swing-floor tie-break launched alongside it.

