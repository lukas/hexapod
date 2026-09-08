# cw-walkscratch-easy0905-cartfoot-halfgrav-s11

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-08T09:59:05+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-s7

**wandb_id**: v61mljpa

**hypothesis**: Plain English: 3rd-seed replicate of the halfgrav cart_foot ON canary, completing the n=3 (seed7/10/11) cross-seed cohort the 1g fork(b) cell already has. Byte-identical to cartfoot-halfgrav-s7 with only seed changed to 11, reusing the base family's own proven seed11 identity.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY (2M): finite losses, weights changing, real joint/foot excursion beyond settled stance, reward agrees with WALKSCRATCH_EASY semantics bank. Read together with the matched offctrl-cartfoot-halfgrav-s11 control launched the same cycle; healthy canaries get the normal 40M acquisition continuation next cycle.

**verdict**: CANARY PASS: mechanism-health only, 2M steps. Finite losses, weights changing (reward quarters -133/-338/-483/-645, monotonic), 0 falls/terminations in 24/24 gate episodes, gait_valid 6/6 in every group. Same shape as seed10/seed7: near-zero walk/det progress at this depth, real forward excursion in the sto/startjitter groups (fwd med 0.35m/0.29m), no chronic leg sacrifice. Healthy canary.

