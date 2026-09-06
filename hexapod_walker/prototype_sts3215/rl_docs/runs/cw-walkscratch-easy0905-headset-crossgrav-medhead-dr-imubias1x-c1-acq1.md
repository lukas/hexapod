# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-imubias1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T08:58:47+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-imubias1x-c1

**wandb_id**: 27huezvy

**hypothesis**: Does the PERFECT single-axis DR-restore canary (medhead-dr-imubias1x-c1: IMU miscalibration bias, 24/24 gait_valid at 2M, 0 falls, sac=[] every episode) hold up at a real 40M ACQ budget on top of the 80M champion, joining friction1x/mass1x/cmddrop1x in the individual-axis durability batch?

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg pattern and 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall).

**verdict**: ACQ PASS/HOLDS at 40M. IMU miscalibration-bias axis holds PERFECTLY: aggregate gait_valid 24/24 across all 4 panels, sac=[] every single episode, 0 falls/terms. slip/m 3.20-4.93, in-band. Matches its own 2M canary's perfect 24/24 pattern exactly -- durable at full ACQ scale, joining friction1x/mass1x/cmddrop1x/actionnoise1x/contactstiff1x/deadband1x/zerobiasframe1x in the individual-axis durability batch. Next: no further per-axis spend per this track's QUEUE AIM STOP; axis stays available as a composite ingredient.

