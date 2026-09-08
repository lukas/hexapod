# cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s7-acq1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-08T07:46:06+00:00

**pod**: hexapod-mjx-train-3

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s7-acq1

**wandb_id**: irimsdt7

**hypothesis**: This cycle's ON cont10m (cartfoot-freshinit-c1-s7-acq1-cont10m, already running) tests whether the fresh-init cart_foot ON arm's 40M slip PARITY (0.94-0.99x vs OFF) holds or degrades at 50M cumulative, mirroring fork(a)'s late-onset-degradation shape. That comparison is only valid against a matched OFF continuation at the SAME depth -- this run is that missing matched control, warm-started from the OFF arm's own PASSed 40M acquisition checkpoint, same +10M budget as its ON sibling.

**gate**: 24-ep walk/walk_startjitter det+sto retention gate at 50M cumulative: PASS/HOLDS = 0 new falls/terminations vs this run's own 40M read, gait_valid staying in-or-above its established 6/6 (det)/1-6 (startjitter/det) band, mean slip/m staying in the 2.6-3.4/m band already measured at 40M (no unexplained drift). This band is what the ON cont10m's slip ratio is read against -- if this control itself drifts, read the ON/OFF cont10m pair as inconclusive rather than crediting/blaming the Cartesian mechanism.

**verdict**: PASS - DURABILITY HOLDS (matched control, seed7 OFF, 50M cumulative). 0/24 falls/terminations (same as 40M). Slip/m stays in the established 2.6-3.4 band all 4 groups (walk/det 2.81, walk/sto 3.41, startjitter/det 2.83, startjitter/sto 3.30 -- flat vs 40M's 2.83/3.41/2.84/3.22). sto gait_valid unaffected (6/6 both scenarios, same as 40M). Det-mode gait_valid drops 6/6->0/6 (walk/det) and 1/6->0/6 (startjitter/det) via the SAME precedented family-wide leg-duty-threshold quirk seen repeatedly this campaign (leg4 duty 0.06-0.13, swing_count 88-119 -- still cycling every episode, not frozen, vanishes under sto) -- read as non-blocking, not a new pathology. Critically, the matched ON sibling (cartfoot-freshinit-c1-s7-acq1-cont10m, gate report already on controller, verdict owned by a concurrent cycle) shows the IDENTICAL det-mode flip (6/6->0/6, 5/6->0/6) at the same step, confirming this is a shared recipe-wide artifact affecting both arms symmetrically, not an ON-vs-OFF asymmetry -- exactly what a matched control is for. ON/OFF slip ratio at 50M: walk/det 0.99x (2.79/2.81), walk/sto 0.97x (3.30/3.41), startjitter/det 0.97x (2.74/2.83), startjitter/sto 0.94x (3.11/3.30) -- ON at-or-under OFF in all 4 groups, same PARITY shape as the 40M read (0.94-0.99x then, 0.94-0.99x now). Frame strips (walk_det_0.png, contact_sheet.png) show a level body, steady forward translation, all legs visibly cycling incl. leg4. CONCLUSION: seed7's fresh-init cart_foot vs joint-space slip PARITY finding HOLDS at 50M cumulative (+10M past the original 40M acquisition read) -- does not degrade the way fork(a)'s warm-started-retrofit lineage did between 12M and 22M. Completes seed7's durability pair (ON verdict is the concurrent cycle's to record).

