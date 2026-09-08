# cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s11-acq1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T07:59:32+00:00

**pod**: hexapod-mjx-train-2

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s11-acq1

**wandb_id**: 67t486cj

**hypothesis**: Matched joint-space control for the seed11 cont10m durability read above: does the OFF arm's own performance (slip 3.02/3.53/2.91/3.34, gait_valid 0/6 det (leg1,4 precedented benign quirk)/6/6/6, 0 falls at 40M) hold steady at 10M more steps, so the paired ON/OFF ratio at 50M is a valid comparison and not confounded by drift in the control itself? Byte-identical continuation recipe to the ON sibling except no cart_foot keys.

**gate**: MATCHED CONTROL: read together with cartfoot-freshinit-c1-s11-acq1-cont10m at the same budget. Retention = 0 new falls and slip/m within noise (+/-15%) of this arm's own 40M read; any regression here means the ON/OFF ratio comparison at 50M needs re-basing on the control's own drift, not just read as an ON-side effect.

