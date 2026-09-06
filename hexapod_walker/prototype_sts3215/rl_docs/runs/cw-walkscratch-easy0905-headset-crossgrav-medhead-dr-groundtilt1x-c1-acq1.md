# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-groundtilt1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T09:00:09+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-groundtilt1x-c1

**hypothesis**: Does the PERFECT floor-slope (tilted-ground) mechanism-health canary (medhead-dr-groundtilt1x-c1: 24/24 gait_valid at 2M, 0 falls, sac=[] every episode) hold up at a real 40M ACQ budget -- moving this axis beyond its mechanism-health-only scope into a genuine skill-acquisition durability read, matching the friction1x/mass1x/cmddrop1x/imubias1x precedent?

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg pattern and 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall).

**refused_reason**: hexapod-mjx-train-3 already runs cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-imubias1x-c1-acq1 — GPU pods host exactly one run; pick a free GPU pod.

