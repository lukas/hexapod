# cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-irrfwd-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T02:35:46+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-c1-acq1

**wandb_id**: m5sxljmr

**hypothesis**: Plain English: same logic as the widenfwd sibling, but for command-timing jitter instead of heading breadth: medhead-irrfwd-c1 (abrupt transition) is already testing native-1g jitter extension; this gives the ramp-transition champion the same test.

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic single-leg sacrifice under command-timing jitter. FAIL/INFORMATIVE-NEGATIVE if it collapses to chronic leg sacrifice.

**verdict**: CANARY PASS - INFORMATIVE-POSITIVE (ramp-transition x irr-timing forward extension, symmetry test vs the abrupt-transition medhead-irrfwd-c1 sibling which already PASSed). Aggregate gait_valid 22/24: walk/det 4/6 (2 episodes transiently flag legs [2,5]/[5], never chronic -- the other 3 modes clean 6/6: walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6), 0 falls/terminations in all 24 episodes, slip_per_m tightly banded 3.07-5.37 (matches the crossgrav sweep's healthy-source band). Video (walk_det_0, 8-frame strip) shows genuine six-leg alternating cycling with clear body translation across the checkerboard floor, no drag/skate pathology. Confirms the gradual-ramp transition recipe generalizes to native-1g command-timing-jitter extension just as cleanly as the abrupt-transition recipe did (both irrfwd siblings now PASS), closing the abrupt-vs-ramp symmetry question for this axis. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_ramp_irrfwd_c1_gate/report.json, W&B m5sxljmr.

