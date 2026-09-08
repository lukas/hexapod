# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-widen8-cartfoot-freshinit-offctrl-s41

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-08T08:44:50+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**wandb_id**: tn101miy

**hypothesis**: 2nd independent seed replicate of the matched joint-space control (train-3, seed40, launched this cycle) for the widen8-cartfoot-freshinit canary pair. Same recipe as the ON s41 sibling, only the 3 walk_cart_foot_box_* keys removed. Seed40 confirms/contests the seed40 read.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY: read together with the matched cart_foot-freshinit-c1-s41 ON arm AND the seed40 pair. Same PASS/FAIL clauses as every other arm in this batch.

**verdict**: CANARY FAIL - MECHANISM, confirms n=2 for the OFF (joint-space) arm, matching the already-verdicted ON arm (c1-s41). Machinery healthy (finite/decreasing loss, std anneals on schedule, 0 falls in 24/24 gate episodes, only 2 safety terms both in walk_startjitter/sto, gait_valid majority every mode 6/6,6/6,6/6,4/6). But the anticipated PASS signal never appears: env/reward_walk flat/noisy across all 4 quarters (0.177/0.185/0.185/0.173), env/v_along_cmd_m_s stays pinned near zero all run (-0.0003..+0.0004), env/walk_speed DECLINES (0.094->0.097->0.089->0.081) -- same shape as the ON arm and the seed40 pair, opposite of the clearly-rising signal the halfgrav/1g canaries show at this identical budget. Gate: slip/m med 74-187 (3-10x the easy-rung cart_foot band), stride near-zero (fwd 0.01-0.05m per 20s episode), contact-sheet strip shows the body essentially stationary while legs buzz. Per this pair's own pre-registered gate text, two agreeing seeds close the read: BOTH action spaces (ON and OFF) fail to ignite forward progress on this 8-way-heading+full-DR composite from a fresh random init, at n=2 each. Do not relaunch this exact fresh-init widen8 recipe at either action space without a milder fresh-init entry point (already being bisected via the torqueretain pair).

