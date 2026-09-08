# cw-walkscratch-easy0905-cartfoot-halfgrav-s7-acq1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T10:04:49+00:00

**pod**: hexapod-mjx-train-2

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-s7-acq1

**wandb_id**: pmcso0fk

**hypothesis**: Plain English: does the halfgrav cart_foot (ON) arm's clean 40M PASS (0 falls, slip 1.56-1.79/m, gait mostly clean) hold or degrade with 10M more training, mirroring the 1g fork(a)/fork(b) durability checks? This is the FIRST depth read for this halfgrav pair -- fork(a) at 1g degraded late (12-22M cumulative window) while fork(b) at 1g held parity through 50M, so halfgrav's own behavior at this depth is not yet known. Own-checkpoint +10M continuation of the ACQ-PASSed 40M ON arm.

**gate**: RETENTION at 50M cumulative: PASS/HOLDS = 0 new falls/terminations vs this run's own 40M read, gait_valid staying in-or-above its established band (6/6 walk/det,walk/sto,startjitter/sto; 4/6 startjitter/det), slip/m staying within +/-20% of the 40M read (1.56/1.72/1.66/1.79). Read together with the matched OFF cont10m sibling (launched same cycle) -- slip ratio vs that control is the headline comparison, not a hardening bar.

