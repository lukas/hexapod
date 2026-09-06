# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-contactstiff1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T07:58:55+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-contactstiff1x-c1

**hypothesis**: Plain English: does the ground-contact-stiffness/compliance-spread axis (dr.contact_stiff_scale 0.7-2.0x, previously pinned identical every episode) stay a clean walk with real training budget, not just a 2M canary glance? contactstiff1x-c1's own 2M canary was 23/24 (one non-chronic leg-4 flag, 0 falls) -- joining the individual-axis ACQ-durability batch alongside friction1x/mass1x/encnoise1x/torquefade-dose/zerobias1x/latency1x/push1x-acq1.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg sacrifice and 0 falls (a repeat of the same non-chronic leg-4 blip is fine). FAIL/ENTRENCHES if it drops below half (<12/24), a chronic single-leg pattern emerges, or a fall appears.

