# cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T10:12:45+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-c1-acq1

**wandb_id**: jeigs5gn

**hypothesis**: Plain English: does the gradual-ramp gravity-transfer champion (medhead-ramp-c1-acq1, clean ACQ PASS at 40M, 0 falls) hold up under a 2nd 40M endurance helping (80M cumulative)? The ABRUPT gravity-transfer sibling (medhead-abrupt-c1-acq1-cont40m) already confirmed clean at 80M -- this is the matching root-line cont40m for the RAMP transfer mechanism (its own irrfwd/widenfwd children already got cont40m continuations, but the plain ramp root itself has not).

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 80M cumulative with no NEW chronic single-leg pattern and 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall).

