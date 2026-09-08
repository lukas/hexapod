# cw-walkscratch-easy0905-cartfoot-freshinit-c1-s11-acq1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T07:58:17+00:00

**pod**: hexapod-mjx-train-0

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-cartfoot-freshinit-c1-s11-acq1

**wandb_id**: q25xz4pj

**hypothesis**: Does the fresh-init cart_foot ON arm's seed11 slip PARITY with its matched joint-space control (measured this cycle at 40M: ON/OFF ratio 0.94-1.00x across all 4 groups, 0 falls) HOLD or DEGRADE at 10M more steps (50M cumulative)? This is the 2nd seed to run this exact durability check (seed7's cont10m pair already in flight) -- mirrors fork(a)'s own design, which looked fine at 12M cumulative then developed new falls + 2-6x slip only after +10-20M more steps.

**gate**: ACQUISITION CONTINUATION: read together with the matched offctrl-s11-acq1-cont10m at the same budget. HOLDS = mean slip/m ratio (ON/OFF) <=1.2x in >=3/4 groups AND 0 new falls/terminations vs this run's own 40M read. DEGRADES = ratio >1.5x in >=2/4 groups OR any new fall/termination not present at 40M. Per 08-21 ruling, continue further only if reward is still rising and evals are ambiguous.

