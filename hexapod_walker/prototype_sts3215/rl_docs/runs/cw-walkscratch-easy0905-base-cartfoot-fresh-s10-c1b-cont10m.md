# cw-walkscratch-easy0905-base-cartfoot-fresh-s10-c1b-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T08:06:55+00:00

**pod**: hexapod-mjx-train-3

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-base-cartfoot-fresh-s10-c1b

**wandb_id**: fy57bm9a

**hypothesis**: Does the fresh-init cart_foot ON seed10 arm's band-match parity (measured this cycle at 40M: ON/OFF slip ratio 0.857/0.983/0.911/0.969x across the 4 groups, 0 falls) HOLD or DEGRADE at 10M more steps (50M cumulative)? Same durability design as the already-running seed7 cont10m pair, mirroring fork(a)'s late-onset degradation (fine at 12M cumulative, then 2-6x slip + new falls by 22M).

**gate**: ACQUISITION CONTINUATION: read together with the matched offctrl-s10-c1-cont10m at the same budget. HOLDS = mean slip/m ratio (ON/OFF) <=1.2x in >=3/4 groups AND 0 new falls/terminations vs this run's own 40M read. DEGRADES = ratio >1.5x in >=2/4 groups OR any new fall/termination not present at 40M. Per 08-21 ruling, continue further only if reward is still rising and evals are ambiguous.

