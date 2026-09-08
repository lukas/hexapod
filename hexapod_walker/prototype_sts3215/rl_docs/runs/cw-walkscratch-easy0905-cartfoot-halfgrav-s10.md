# cw-walkscratch-easy0905-cartfoot-halfgrav-s10

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T09:56:41+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-s7

**wandb_id**: ssqrh8ew

**hypothesis**: Plain English: does the fresh-init Cartesian foot-target action space also bootstrap cleanly at 0.5g on a SECOND seed, building the same n=3 (seed7/10/11) cross-seed cohort the 1g fork(b) cell already completed? Byte-identical to the just-CANARY-PASSed cartfoot-halfgrav-s7 recipe (fresh random init, easy-DR-0, ease.gravity_scale=0.5, cart_foot box 0.06/0.035/0.04m) with only seed changed to 10, reusing the base family's own proven seed10 identity.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY (2M): finite losses, weights changing, real joint/foot excursion beyond settled stance, reward agrees with WALKSCRATCH_EASY semantics bank. Read together with the matched offctrl-cartfoot-halfgrav-s10 control launched the same cycle; healthy canaries get the normal 40M acquisition continuation next cycle.

