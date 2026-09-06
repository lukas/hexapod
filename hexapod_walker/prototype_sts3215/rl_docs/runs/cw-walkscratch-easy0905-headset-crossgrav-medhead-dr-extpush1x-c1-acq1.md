# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-extpush1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T08:00:16+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-extpush1x-c1

**hypothesis**: Plain English: does the mid-stride external-push axis (dr.ext_push_prob=0.3, a random-direction horizontal shove fired after the policy is already walking) stay a clean walk with a real 40M training budget, not just a 2M canary glance? extpush1x-c1's own 2M canary was 22/24 (0 falls, 2 non-chronic single-episode leg flags, no repeat of the campaign's chronic leg[1,4] fingerprint) -- this is its first ACQ-scale confirmation, joining the sibling encnoise1x/friction1x/mass1x/latency1x/push1x/torquefade2x/torquefade15x/zerobias1x/kick1x/gains1x/geom1x/fault1x individual-axis durability batch.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M, no NEW chronic single-leg sacrifice, 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall) -- would show mid-stride push-recovery realism needs real training exposure before being called safe.

**refused_reason**: hexapod-mjx-train-1 already runs cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-contactstiff1x-c1-acq1 — GPU pods host exactly one run; pick a free GPU pod.

