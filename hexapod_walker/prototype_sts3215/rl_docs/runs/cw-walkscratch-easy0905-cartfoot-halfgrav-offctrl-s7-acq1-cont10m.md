# cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s7-acq1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T10:09:08+00:00

**pod**: hexapod-mjx-train-1

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s7-acq1

**wandb_id**: wlq0i0k6

**hypothesis**: Matched joint-space (OFF) control for the halfgrav cont10m durability read above: does this arm's own 40M performance (0 falls, slip 1.90/1.91/1.83/1.93, det-mode leg-underuse quirk already precedented non-blocking) hold steady at 10M more steps, so the paired ON/OFF slip ratio at 50M is a valid comparison and not confounded by drift in the control itself? Byte-identical continuation recipe to the ON sibling except no cart_foot keys (joint-space action decode).

**gate**: MATCHED CONTROL: read together with cartfoot-halfgrav-s7-acq1-cont10m at the same budget. Retention = 0 new falls and slip/m within noise (+/-20%) of this arm's own 40M read (1.90/1.91/1.83/1.93); any regression here means the ON/OFF ratio comparison at 50M needs re-basing on the control's own drift, not read as an ON-side effect.

