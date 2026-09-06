# cw-walkscratch-easy0905-headset-halfgrav-widenirr-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: DEAD

**created**: 2026-09-06T11:47:57+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-widenirr-c1-acq1

**hypothesis**: The widen-first widen2+irr composite (halfgrav) ACQ PASSed cleanly at 40M (23/24 gait_valid, 0 falls, no chronic leg, beats plain widen2 sibling) but has never been continued past 40M -- it is the cleanest halfgrav composition champion still lacking its own cont40m endurance read, matching the campaign's own cleanliness-margin-predicts-endurance rule already confirmed on friction1x/mass1x/torquefade/irrwiden-c2/medhead-ramp.

**gate**: HARDENING PASS/HOLDS if gait_valid stays majority (>=18/24) at 80M cumulative with no NEW chronic single-leg pattern and 0 falls. HARDENING FAIL/ENTRENCHES if it drops below majority, a new chronic leg appears, or any fall appears (per this campaign's own bright-line bar).

