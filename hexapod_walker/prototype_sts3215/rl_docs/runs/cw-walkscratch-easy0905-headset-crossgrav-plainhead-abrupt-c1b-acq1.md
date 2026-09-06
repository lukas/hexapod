# cw-walkscratch-easy0905-headset-crossgrav-plainhead-abrupt-c1b-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ_PASS

**created**: 2026-09-06T03:23:33+00:00

**pod**: hexapod-mjx-train-5

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-plainhead-abrupt-c1b

**wandb_id**: 2ngv7lap

**hypothesis**: Does the plain (never-composited) 3-way heading champion's clean 0.5g->1.0g abrupt transfer (23/24 gv, 0 falls, 2M canary) hold up at full 40M acquisition budget, matching the 6/6 healthy-source crossgrav siblings already confirmed (medhead/widen2c1/irracq1/irr2acq1/s1acq/s3acq)?

**gate**: PASS if gait_valid stays >= its own 2M canary (23/24) or degrades only mildly with no NEW chronically-sacrificed leg across the 40M run, 0 falls, slip/m flat-or-better. FAIL/MECHANISM if gait_valid collapses well below the canary (matching the already-seen ACQ-scale entrenchment regression pattern, e.g. irracq1-abrupt-c1-acq1's 23/24->14/24 drop) despite rising reward.

**verdict**: ACQ PASS: 40M continuation of the simplest never-composited crossgrav champion (plainhead-abrupt-c1b) HOLDS. gait_valid 23/24, EXACT match to its own 2M canary's 23/24 -- zero entrenchment. walk/det 6/6, walk/sto 6/6, walk_startjitter/sto 6/6 all clean; walk_startjitter/det 5/6 (one leg-4 flag, non-chronic, single episode). 0 falls/terms across all 24 episodes, ep_len_mean=2000/2000 (full-episode survival). Reward rose every quarter (422.7->788.2->911.1->1113.6), consistent with clean acquisition not misalignment. slip/m med 3.75-4.64, fwd_dist rose vs canary (med ~1.9-2.4m/20s). Video (walk_det_0 contact sheet) confirms genuine six-leg cycling with clear forward body translation. This is the simplest-baseline crossgrav lineage (no widen/irr composition) and is now the 2nd champion (after medhead) confirmed durable through a full 40M ACQ budget with zero entrenchment, reinforcing that entrenchment risk is recipe/source-specific rather than a universal slow clock.

