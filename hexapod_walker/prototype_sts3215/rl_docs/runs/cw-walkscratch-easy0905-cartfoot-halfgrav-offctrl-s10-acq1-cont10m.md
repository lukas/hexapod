# cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s10-acq1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T11:48:11+00:00

**pod**: hexapod-mjx-train-1

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s10-acq1

**wandb_id**: 83az85kk

**hypothesis**: Matched joint-space (OFF) control for the seed10 cont10m durability read above: does this arm's own 40M performance (0 falls/24, speed 0.17-0.21 m/s, gait_valid 7/24) hold steady at 10M more steps, so the paired ON/OFF slip and gait_valid comparison at 50M is a valid depth read, mirroring seed7's own OFF cont10m (gait_valid degraded further 10/24->7/24).

**gate**: MATCHED CONTROL: read together with s10-acq1-cont10m at the same budget. Retention = 0 new falls and slip/m within noise (+/-20%) of this arm's own 40M read; report whether gait_valid holds at 7/24 or degrades further, same as seed7's OFF arm did.

