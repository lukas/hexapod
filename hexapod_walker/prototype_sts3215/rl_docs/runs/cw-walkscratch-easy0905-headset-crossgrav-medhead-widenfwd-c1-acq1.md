# cw-walkscratch-easy0905-headset-crossgrav-medhead-widenfwd-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T03:06:16+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-widenfwd-c1

**wandb_id**: thsloov1

**hypothesis**: Plain English: the medhead-widenfwd-c1 2M canary just PASSed (gait_valid 23/24, 0 falls) -- composing the full widen2 8-way heading set natively at 1g on top of the already-crossgrav-transferred medhead champion works at canary scale. Does the same recipe hold at full 40M acquisition budget, matching the campaign's own-checkpoint-continuation pattern already validated for every other crossgrav/widen2 rung?

**gate**: ACQ PASS if aggregate gait_valid stays >=18/24 with no NEW chronic (<0.10-duty every episode) single-leg sacrifice vs the 2M canary's transient ep4-only flag; ACQ FAIL if a chronic sacrifice fingerprint emerges that wasn't present at 2M.

**verdict**: ACQ PASS: aggregate gait_valid 21/24 (walk/det 5/6, walk/sto 6/6, walk_startjitter/det 5/6, walk_startjitter/sto 5/6), 0 falls in all 24 episodes. Vs its own 2M canary (23/24): a mild 2-point dip but NO chronic same-leg pattern -- the 3 flagged episodes each name a DIFFERENT leg (0, 4, 0) in a single isolated episode, not a repeating leg-1/4 signature. Slip/m and progress_ratio mostly IMPROVED vs canary (walk/det slip med 5.35->4.41, walk/sto 12.85->8.17, startjitter/det 7.22->5.27, startjitter/sto 8.59->6.88; progress_ratio up on 3/4 panels). Contact sheet shows real six-leg cycling, no splayed leg. Confirms medhead's forward-heading-widen composition axis holds durably at full 40M acquisition, matching the widen2c1-irrfwd precedent on a different base.

