# cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-irrfwd-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T06:48:45+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-irrfwd-c1-acq1

**hypothesis**: Plain English: same endurance question, run on the ramp-transfer + irr-forward-composed champion (medhead-ramp-irrfwd-c1-acq1: 22/24 gait_valid, EXACT match to its own 2M canary's structure, 0 falls) -- this is the first endurance read on a RAMP-transfer (not abrupt) source, and separately tests whether the ramp-transfer method itself carries elevated entrenchment risk under a 2nd 40M helping (open question raised by the sibling medhead-ramp-widenfwd-c1-acq1 ACQ FAIL).

**gate**: HARDENING/endurance continuation (+40M, own checkpoint, no cfg change). PASS/HOLDS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with slip_per_m staying tightly banded and no NEW chronic leg beyond this checkpoint's own established 40M read (22/24, non-chronic leg-5 flag only). FAIL/ENTRENCHES if a leg[1,4]-or-other chronic single-leg sacrifice newly spreads across multiple modes -- would implicate ramp-transfer itself as elevated-risk.

**refused_reason**: hexapod-mjx-train-7 already runs cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-mass1x-c1-acq1 — GPU pods host exactly one run; pick a free GPU pod.

