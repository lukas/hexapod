# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-extpush1x-c1-acq1-r2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T08:22:00+00:00

**pod**: hexapod-mjx-train-10

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-extpush1x-c1

**hypothesis**: Plain English: does the mid-stride external-push axis (dr.ext_push_prob=0.3) stay a clean walk with a REAL 40M training budget? Re-run of extpush1x-c1-acq1 (a concurrent cycle's own launch this window) which landed with an accidental 2M-step budget (the same --steps-not-overridden bug already found on gains1x/geom1x/fault1x-c1-acq1 -- those finished in minutes at only the canary's own budget, not a genuine ACQ read) -- this -r2 explicitly pins --steps 40000000 to give the axis its intended first ACQ-scale confirmation. extpush1x-c1's own 2M canary was 22/24 (0 falls, 2 non-chronic single-episode leg flags).

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M, no NEW chronic single-leg sacrifice, 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall) -- would show mid-stride push-recovery realism needs real training exposure before being called safe.

