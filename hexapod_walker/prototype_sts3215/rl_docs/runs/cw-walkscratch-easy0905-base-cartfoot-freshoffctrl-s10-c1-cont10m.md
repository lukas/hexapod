# cw-walkscratch-easy0905-base-cartfoot-freshoffctrl-s10-c1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-08T08:03:43+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-base-cartfoot-freshoffctrl-s10-c1

**hypothesis**: Matched joint-space control for the seed10 cont10m durability read above: does the OFF arm's own 40M performance (slip 3.05/3.34/2.93/3.31, gv 0/6/6/6/0/6/6, 0 falls) hold steady at 10M more steps, so the paired ON/OFF ratio at 50M is a valid comparison and not confounded by drift in the control itself? Byte-identical continuation recipe to the ON sibling except no cart_foot keys (joint-space action decode).

**gate**: MATCHED CONTROL: read together with base-cartfoot-fresh-s10-c1b-cont10m at the same budget. Retention = 0 new falls and slip/m within noise (+/-15%) of this arm's own 40M read; any regression here means the ON/OFF ratio comparison at 50M needs re-basing on the control's own drift, not just read as an ON-side effect.

**refused_reason**: --steps belongs to the launcher, not the passthrough args

