# cw-walkscratch-easy0905-base-cartfoot-freshoffctrl-s10-c1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-08T08:05:39+00:00

**pod**: hexapod-mjx-train-1

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-base-cartfoot-freshoffctrl-s10-c1

**wandb_id**: 7shcq1ed

**hypothesis**: Matched joint-space control for the seed10 cont10m durability read above: does the OFF arm's own 40M performance (slip 3.05/3.34/2.93/3.31, gv 0/6/6/6/0/6/6, 0 falls) hold steady at 10M more steps, so the paired ON/OFF ratio at 50M is a valid comparison and not confounded by drift in the control itself? Byte-identical continuation recipe to the ON sibling except no cart_foot keys (joint-space action decode).

**gate**: MATCHED CONTROL: read together with base-cartfoot-fresh-s10-c1b-cont10m at the same budget. Retention = 0 new falls and slip/m within noise (+/-15%) of this arm's own 40M read; any regression here means the ON/OFF ratio comparison at 50M needs re-basing on the control's own drift, not just read as an ON-side effect.

**verdict**: PASS - DURABILITY HOLDS (matched control, seed10 OFF, 50M cumulative). 0/24 falls/terminations (same as 40M). Slip/m flat-to-slightly-improved vs 40M in all 4 groups (walk/det 3.05->2.88, walk/sto 3.34->3.28, startjitter/det 2.93->2.90, startjitter/sto 3.31->3.30). gait_valid pattern identical to 40M in every group (det 0/6, sto 6/6, startjitter/det 0/6, startjitter/sto 6/6 both budgets) -- this seed's OFF control already carried the precedented det-only leg[1,4] quirk at 40M, unchanged at 50M, not a new drift. Reward rising every quarter (372.6->2139.8), no plateau. Frame strip (contact_sheet.png) shows level body, steady forward translation, six legs visibly cycling. Matched ON sibling (base-cartfoot-fresh-s10-c1b-cont10m) still training on train-3 -- ratio comparison pending until it lands.

