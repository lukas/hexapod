# cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s11

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-08T10:01:35+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s7

**wandb_id**: g6dxekq4

**hypothesis**: Plain English: matched joint-space control for the halfgrav cart_foot seed11 canary (ON launched same cycle) -- completes the n=3 cross-seed cohort's matched-control side. Byte-identical to cartfoot-halfgrav-offctrl-s7 with only seed changed to 11.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY (2M): finite losses, weights changing, real joint/foot excursion beyond settled stance, reward agrees with WALKSCRATCH_EASY semantics bank. Read together with cartfoot-halfgrav-s11 (ON) at the same budget.

**verdict**: CANARY PASS: mechanism-health only, 2M steps, matched joint-space control for the seed11 ON arm. Finite losses (reward quarters -144/-307/-429/-606, monotonic), 0 falls/terminations in 24/24 gate episodes, gait_valid 6/6 every group, same shape as the ON sibling. Healthy machinery, valid control for the seed11 pair.

