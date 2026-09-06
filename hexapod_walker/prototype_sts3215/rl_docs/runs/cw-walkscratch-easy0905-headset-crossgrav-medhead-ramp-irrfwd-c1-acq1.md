# cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-irrfwd-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T03:32:53+00:00

**pod**: hexapod-mjx-train-9

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-irrfwd-c1-acq1

**wandb_id**: 5bktykuw

**hypothesis**: Plain English: the ramp-transition champion's 2M canary just PASSED the same native-1g command-timing-jitter extension test its abrupt sibling passed -- does it hold up at full 40M acquisition scale too, mirroring the abrupt-irrfwd-c1-acq1 companion arm?

**gate**: ACQ PASS if aggregate gait_valid stays >=17/24 with no NEW chronic single-leg sacrifice pattern vs the 2M canary's own 22/24 baseline (max 2/6 per leg); 0 falls required. FAIL/MECHANISM if a chronic leg-sacrifice fingerprint (>=4/6 same leg in any mode) emerges that wasn't present at 2M.

**verdict**: ACQ PASS -- gait_valid holds EXACTLY at the own 2M canary's structure: aggregate 22/24 both budgets (walk/det 4/6, walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6). 0 falls/24 both. The only sac flags are leg-5 in walk/det ep1+ep5 at 40M (canary had leg-5 in the same two episode slots plus a transient leg-2 co-flag in ep1) -- same non-chronic leg-5 softening signature carried through unchanged from 2M to 40M, not a new or worsening pattern. slip_per_m bands essentially flat (canary 3.1-5.4, acq1 3.3-4.9), well inside the healthy crossgrav norm. Frame strip (walk_det_0, 6 frames) shows clean six-leg cycling with clear body translation across the checkerboard. This closes the 4th 1g-forward-extension arm (irr-timing composed on the ramp-transition medhead variant) durable at acquisition scale, joining medhead-widenfwd-c1-acq1/medhead-irrfwd-c1-acq1's own clean PASSes -- ramp-vs-abrupt transition speed continues to not matter for durability. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_ramp_irrfwd_c1_acq1_gate/report.json vs .../cw_walkscratch_easy0905_headset_crossgrav_medhead_ramp_irrfwd_c1_gate/report.json, walk_det_0_sheet.png, W&B 5bktykuw.

