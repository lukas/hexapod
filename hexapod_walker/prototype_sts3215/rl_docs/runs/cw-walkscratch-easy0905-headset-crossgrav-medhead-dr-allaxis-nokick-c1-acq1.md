# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T10:55:24+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-c1

**wandb_id**: fvj0g1kr

**hypothesis**: Plain English: does the full ~30-axis realism composite, with kick fully disabled (the one axis proven to break it) and the 3x torque crutch still on, hold up at real acquisition budget (40M), not just a 2M canary -- this is QUEUE AIM item (1)'s composite-ACQ funding step, licensed by this exact recipe's own canary PASS (19/24 gv, 0 falls). Single lever vs the canary: budget 2M->40M, otherwise byte-identical (dr.walk_kick_prob=0.0, all other ~28 DR axes at full medhead-dr dose, torque_scale=3.0 crutch on).

**gate**: ACQ gate (40M): aggregate gait_valid majority (>=18/24) sustained at ACQ scale (matching or improving the 19/24 canary), 0 falls/terminations, no NEW chronic single-leg sacrifice (the canary's flagged sto legs varied episode-to-episode, not one leg every time). PASS -> full composite realism (item 1) is closed FOR REAL at acquisition scale, contingent only on the still-open no-crutch bisection (allaxiskickhalf-nocrutch1x-c1) for the crutch-removal question. FAIL/entrenches -> the composite needs more than kick-removal alone; audit which of the other ~28 axes destabilizes under sustained training even though each passed solo.

