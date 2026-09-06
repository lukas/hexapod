# cw-walkscratch-easy0905-headset-crossgrav-medhead-widenirr-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY_PASS

**created**: 2026-09-06T03:56:14+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-widenfwd-c1-acq1

**wandb_id**: b3l8tia5

**hypothesis**: Plain English: both single-axis 1g-native crossgrav extensions off the medhead champion already PASSED at full 40M acquisition (medhead-widenfwd-c1-acq1: 8-way heading breadth; medhead-irrfwd-c1-acq1: command-timing jitter) -- does composing them TOGETHER (the widenirr order: start from the mature widen champion, add irr jitter on top) survive as cleanly as either axis alone, mirroring the halfgrav-family widenirr/irrwiden composite work but built natively at 1g this time instead of via cross-gravity transfer?

**gate**: CANARY PASS if aggregate gait_valid stays majority-clean (>=20/24) with 0 falls and no NEW chronic leg sacrifice beyond what either single-axis parent already showed; FAIL if it collapses toward chronic leg-1/4 sacrifice or falls appear.

**verdict**: CANARY PASS: 2M widen+irr composite (order: widen-then-irr) on the medhead crossgrav champion. Aggregate gait_valid 22/24 (walk/det 5/6, walk/sto 5/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6), 0 falls/terms in all 24 episodes. Leg-5 flagged in 2 episodes (det/3, sto/5) -- matches the pre-existing leg-2/5 softening signature already seen on this run's own irrfwd-composed parent (medhead-irrfwd-c1), not a new pathology; no chronic single-leg pattern. Video (walk_det_0, walk_det_3 contact sheets) confirms genuine six-leg cycling with body translation. Slip/m elevated (med 3.75-6.92, worst single episode 30.9 in walk_startjitter/sto/5) vs the 2.9 teacher band -- consistent with this campaign's crossgrav-1g norm, not a gate criterion here but flagged for the eventual acquisition read. Composition order (widenirr vs the already-PASSed irrwiden) both now clean -- confirms order doesn't matter for this axis pair on medhead, matching the widenfwd/irrfwd individual-axis precedent.

