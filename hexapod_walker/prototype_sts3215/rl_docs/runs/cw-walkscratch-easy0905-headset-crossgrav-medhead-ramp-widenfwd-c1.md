# cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-widenfwd-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T02:37:04+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-c1-acq1

**wandb_id**: rmow6e1s

**hypothesis**: Plain English: the abrupt-transition medhead champion already got a native-1g forward-extension test this cycle (medhead-widenfwd-c1, widen2 full-8-way heading added directly at 1g, running). The gentler ramp-transition sibling (medhead-ramp-c1-acq1, ACQ PASS 21/24) never got the same test. Does the ramp champion ALSO support forward heading-set extension natively at 1g, completing the abrupt-vs-ramp symmetry one rung further?

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic single-leg sacrifice under the widened 8-way heading set. FAIL/INFORMATIVE-NEGATIVE if it collapses to chronic leg sacrifice -- would mean the ramp recipe's gentler transition doesn't generalize to further curriculum extension as well as the abrupt one.

**verdict**: CANARY PASS - INFORMATIVE-POSITIVE (ramp-transition x heading-widen forward extension, symmetry test vs the abrupt-transition medhead-widenfwd-c1 sibling which already PASSed). Aggregate gait_valid 21/24: walk/det 5/6 (1 transient sac=[0]), walk/sto 6/6, walk_startjitter/det 5/6 (1 transient sac=[4]), walk_startjitter/sto 5/6 (1 transient sac=[4]) -- max 2/6 for any one leg across the whole panel, never chronic. 0 falls/terminations in all 24 episodes. Several slip_per_m outliers (55.8/98.9/208.2) all trace to the widen2 8-way heading set's near-180deg reversal commands: frame strip (walk_startjitter_sto_3) confirms the robot spinning near-stationary to track the reversed arrow (legs visibly cycling, minimal net translation -> tiny progress denominator inflates slip/m) -- the SAME already-documented reversal-heading artifact flagged on the abrupt widenfwd-c1 sibling, not a new defect. Confirms the gradual-ramp transition recipe generalizes to native-1g heading-widen extension just as cleanly as the abrupt-transition recipe (both widenfwd siblings now PASS), closing the abrupt-vs-ramp symmetry question for this axis too (both forward-extension axes now hold under both transition speeds). Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_ramp_widenfwd_c1_gate/report.json, W&B (see ledger).

