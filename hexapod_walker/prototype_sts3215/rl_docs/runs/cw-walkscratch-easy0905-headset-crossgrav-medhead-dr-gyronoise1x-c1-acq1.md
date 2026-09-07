# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-gyronoise1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T08:07:57+00:00

**pod**: hexapod-mjx-train-10

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-gyronoise1x-c1

**hypothesis**: Plain English: does the nominal (1x) IMU gyro-noise axis (dr.gyro_noise_deg_s) stay a clean walk with a real 40M training budget, not just a 2M canary glance? gyronoise1x-c1's own 2M canary was a PERFECT 24/24 (0 falls, sac=[] every episode) -- this is its first ACQ-scale confirmation, joining the sibling latency1x/torquefade/mass/friction/gains/geom/fault/extpush/actionnoise/contactstiff/noise/tiltnoise/deadband individual-axis durability batch.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M, no NEW chronic single-leg sacrifice, 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall) -- would show gyro-noise realism needs real training exposure before being called safe.

**refused_reason**: a process for cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-gyronoise1x-c1-acq1 already exists on hexapod-mjx-train-8

