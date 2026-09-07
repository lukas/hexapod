# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kickhalf1x-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T11:20:14+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kickhalf1x-c1-acq1

**hypothesis**: Plain English: does the half-dose kick-recovery axis (dr.walk_kick_prob=0.15, the confirmed-safe ceiling below kick0225x's 0.225 FAIL) stay clean over a SECOND 40M block (80M cumulative), the same endurance question already asked of friction1x/mass1x/torquefade2x/torquefade15x -- specifically whether its own ACQ read's leg5 watch (a single leg recurring in 4/24 episodes, healthy duty 0.3-0.6 in the other 20/24, only dipping to 0.03-0.09 in the flagged ones) is occasional near-threshold noise (stays flat/scattered) or an entrenching chronic pattern (grows/consolidates) under more training exposure.

**gate**: PASS/HOLDS if gait_valid stays majority (>=18/24, ideally close to its own 20/24) with 0 falls and the leg5 flag count does NOT grow past its own 4/24 baseline or consolidate into sustained near-zero duty across most episodes (that would flip the WATCH into a chronic-entrenchment FAIL). FAIL/ENTRENCHES if gait_valid drops materially, a fall appears, or leg5's flagged-episode count grows/duty collapses broadly.

**refused_reason**: a process for cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kickhalf1x-c1-acq1-cont40m already exists on hexapod-mjx-train-5

