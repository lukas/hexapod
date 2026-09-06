# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade2x-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: pass

**created**: 2026-09-06T09:35:35+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade2x-c1-acq1

**wandb_id**: dpdvz0ev

**hypothesis**: Plain English: does the 2x torque-fade axis (dr.torque_scale=2,2, half the idealized 3x crutch) hold up over a SECOND 40M block (80M cumulative), the same endurance question already asked of friction1x/mass1x/widen2c1-irrfwd/widenirr-c3. Source is clean at 40M (24/24 gait_valid, 0 falls, sac=[] every episode, reward rising every quarter 874->1551->1637->1709).

**gate**: PASS/HOLDS if gait_valid stays majority (>=18/24, ideally close to its own 24/24) with no NEW chronic single-leg sacrifice and 0 falls. FAIL/ENTRENCHES if it drops (<12/24), a chronic single-leg pattern emerges, or a fall appears.

**verdict**: HARDENING PASS/HOLDS. +40M more steps (80M cumulative) on the torque-fade-2x axis (dr.torque_scale 3.0->2.0) essentially reproduces its own 40M ACQ-PASS parent: gait_valid 23/24 (6/6 det, 6/6 sto, 5/6 startjitter/det, 6/6 startjitter/sto) vs the parent's PERFECT 24/24, 0 falls/terms in all 24 episodes (matching parent), one non-chronic singleton flag (leg5, walk_startjitter/det ep1 only, absent from every other episode/mode). Reward still rising every quarter (1132->1965->2068->2156), slip/progress in-band. This is the endurance-margin pattern this campaign has repeatedly confirmed: a clean 40M source (0 chronic pattern) holds essentially unchanged at 80M. Joins medhead-abrupt-cont40m/friction/mass/etc as another clean-source cont40m confirmation.

