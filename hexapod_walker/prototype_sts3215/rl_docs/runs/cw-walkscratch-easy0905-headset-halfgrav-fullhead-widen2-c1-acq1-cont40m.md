# cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: DEAD

**created**: 2026-09-06T11:50:01+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c1-acq1

**hypothesis**: The full 8-way-heading-incl-reversals widen2 champion (halfgrav, seed c1) ACQ PASSed cleanly at 40M (21/24 gait_valid, 0 falls) and is the source used for the crossgrav-widen2c1-abrupt transfer probe, but has never itself been continued past 40M -- its own sibling c2b already FAILED at cont40m (chronic entrenchment) and c3 is mid-cont40m elsewhere, so c1 is the natural remaining endurance question for this composition.

**gate**: HARDENING PASS/HOLDS if gait_valid stays majority (>=18/24) at 80M cumulative with no NEW chronic single-leg pattern and 0 falls. HARDENING FAIL/ENTRENCHES if it drops below majority, a new chronic leg appears, or any fall appears.

