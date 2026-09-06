# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-imubias1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T08:58:47+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-imubias1x-c1

**hypothesis**: Does the PERFECT single-axis DR-restore canary (medhead-dr-imubias1x-c1: IMU miscalibration bias, 24/24 gait_valid at 2M, 0 falls, sac=[] every episode) hold up at a real 40M ACQ budget on top of the 80M champion, joining friction1x/mass1x/cmddrop1x in the individual-axis durability batch?

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg pattern and 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall).

