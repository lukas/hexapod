# cw-walkscratch-easy0905-headset-halfgrav-widenirr-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T12:15:02+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-widenirr-c1-acq1

**wandb_id**: ab1hqszt

**hypothesis**: The widen-first widen2+irr composite (halfgrav) ACQ PASSed cleanly at 40M (23/24 gait_valid, 0 falls, no chronic leg, beats plain widen2 sibling) but has never been continued past 40M -- cleanest halfgrav composition champion still lacking cont40m, per the campaign's cleanliness-margin-predicts-endurance rule already confirmed on friction1x/mass1x/torquefade/irrwiden-c2/medhead-ramp. (multiple prior attempts this cycle hit a launch-syntax bug then a transient self-repair tar race then a pod collision with a concurrent cycle's own launch; explicit free pod picked here.)

**gate**: HARDENING PASS/HOLDS if gait_valid stays majority (>=18/24) at 80M cumulative with no NEW chronic single-leg pattern and 0 falls. HARDENING FAIL/ENTRENCHES if it drops below majority, a new chronic leg appears, or any fall appears.

