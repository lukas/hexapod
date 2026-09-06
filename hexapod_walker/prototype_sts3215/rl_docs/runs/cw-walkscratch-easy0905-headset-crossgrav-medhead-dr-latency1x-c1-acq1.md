# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-latency1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T06:59:01+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-latency1x-c1

**hypothesis**: Plain English: does the real actuator command-latency spread (previously OFF) stay a clean walk with real training, not just a 2M canary glance? latency1x-c1's own 2M canary was a PERFECT 24/24 (0 falls) on the campaign's cleanest champion -- a 3rd ACQ durability confirmation for a bare DR-realism axis (after torquefade2x-c1-acq1, mass1x-c1-acq1), picking the single most hardware-timing-critical axis in the sweep.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24, ideally near its own 24/24 canary) at 40M, no NEW chronic single-leg sacrifice, 0 falls. FAIL/ENTRENCHES if it drops below half (<12/24), a chronic single-leg pattern emerges, or a fall appears.

**refused_reason**: hexapod-mjx-train-3 already runs cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-irrfwd-c1-acq1-cont40m — GPU pods host exactly one run; pick a free GPU pod.

