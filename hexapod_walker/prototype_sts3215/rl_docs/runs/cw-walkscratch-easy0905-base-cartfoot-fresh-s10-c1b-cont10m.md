# cw-walkscratch-easy0905-base-cartfoot-fresh-s10-c1b-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ_PASS

**created**: 2026-09-08T08:06:55+00:00

**pod**: hexapod-mjx-train-3

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-base-cartfoot-fresh-s10-c1b

**wandb_id**: fy57bm9a

**hypothesis**: Does the fresh-init cart_foot ON seed10 arm's band-match parity (measured this cycle at 40M: ON/OFF slip ratio 0.857/0.983/0.911/0.969x across the 4 groups, 0 falls) HOLD or DEGRADE at 10M more steps (50M cumulative)? Same durability design as the already-running seed7 cont10m pair, mirroring fork(a)'s late-onset degradation (fine at 12M cumulative, then 2-6x slip + new falls by 22M).

**gate**: ACQUISITION CONTINUATION: read together with the matched offctrl-s10-c1-cont10m at the same budget. HOLDS = mean slip/m ratio (ON/OFF) <=1.2x in >=3/4 groups AND 0 new falls/terminations vs this run's own 40M read. DEGRADES = ratio >1.5x in >=2/4 groups OR any new fall/termination not present at 40M. Per 08-21 ruling, continue further only if reward is still rising and evals are ambiguous.

**verdict**: ACQ PASS - PARITY HOLDS (seed10 ON, 50M cumulative). 0/24 falls/terminations (same as 40M). ON/OFF slip ratio at 50M (vs verdicted OFF sibling base-cartfoot-freshoffctrl-s10-c1-cont10m): walk/det 0.90x (2.59/2.88), walk/sto 0.95x (3.12/3.28), startjitter/det 0.93x (2.71/2.90), startjitter/sto 0.95x (3.14/3.30) -- ON at-or-under OFF in ALL 4 groups, matching this seed's own 40M ratio shape (0.857/0.983/0.911/0.969x). gait_valid pattern identical to 40M source in every group (det 0/6, sto 6/6, startjitter/det 0/6, startjitter/sto 6/6 both budgets) -- this arm already carried the det-only leg quirk at 40M, unchanged at 50M. Reward rising, slip/m flat-to-improved vs 40M in all 4 groups (2.61->2.59, 3.29->3.12, 2.67->2.71, 3.21->3.14). Frame strip shows level body, clean six-leg cycling, real forward translation. CONCLUSION: seed10's fresh-init cart_foot vs joint-space slip PARITY finding HOLDS at 50M cumulative -- COMPLETES the n=3/3 durability cohort (seed7, seed10, seed11 all HOLDS, none showing fork(a)'s 1.5-6x late-onset degradation). TRACK-LEVEL DURABILITY RULING: fresh-init Cartesian foot-target action-space slip parity with joint-space, already ruled 3/3 seeds at 40M, now also holds 3/3 seeds at 50M cumulative (+10M past acquisition) -- durability past 40M is no longer unproven for this recipe.

