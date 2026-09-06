# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-tiltnoise1x-c1-acq1-rr1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T08:09:37+00:00

**pod**: hexapod-mjx-train-10

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-tiltnoise1x-c1

**hypothesis**: Plain English: does the IMU tilt-sensor-noise axis (dr.tilt_noise_deg=0.3, previously pinned at 0 the whole campaign) stay a clean walk with real training budget, not just a 2M canary glance? tiltnoise1x-c1's own 2M canary was a PERFECT 24/24 (sac=[] every episode, 0 falls) -- joining the individual-axis ACQ-durability batch alongside friction1x/mass1x/encnoise1x/torquefade-dose/zerobias1x/latency1x/push1x/gyronoise1x/deadband1x/contactstiff1x-acq1.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg sacrifice and 0 falls. FAIL/ENTRENCHES if it drops below half (<12/24), a chronic single-leg pattern emerges, or a fall appears.

**refused_reason**: acquisition runs require --evidence: name the healthy canary and a comparable full-budget learning precedent.

