# cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s12-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-08T11:56:11+00:00

**pod**: hexapod-mjx-train-5

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s12

**wandb_id**: t2r5n3mz

**hypothesis**: Plain English: matched joint-space control for the halfgrav cart_foot seed12 40M acquisition (ON launched same cycle) -- 4th-seed replicate breaking the tie in the closed n=3 cohort (2/3 seeds showed a cart_foot gait_valid advantage, 1/3 near-parity). Own-checkpoint continuation of the CANARY-PASSed offctrl-s12 2M arm (telemetry matched s7/s10/s11 sibling band exactly).

**gate**: ACQUISITION gate: same joint reading protocol as s7/s10/s11 (>=0.03 m/s median net forward in >=1 of walk/det,sto, 0 falls in det). slip/m and gait_valid vs the ON s12-acq1 sibling are the headline comparisons; determines whether this seed extends the seed7/10 majority pattern (2/3, real cart_foot gait_valid advantage) or the seed11 minority pattern (1/3, near-parity).

**verdict**: Matched joint-space (OFF) seed12 also clears the acquisition floor cleanly: 0 falls/terminations in 24/24 gate episodes, fwd med 3.57/3.10/3.46/2.99m over 20s (~0.15-0.18 m/s), well above the 0.03 m/s floor. gait_valid is 0/6 walk/det (every det episode sacrifices legs [1,4] TOGETHER, identically), 6/6 walk/sto (perfect), 0/6 startjitter/det, 5/6 startjitter/sto = 11/24 total. slip/m med 1.89/2.00/1.93/2.10. Reward quarters rise monotonically (-632.0/245.9/1038.9/1371.8), matched budget (40,370,176 steps) to the ON sibling. Video reviewed (walk_det_0.png strip): real forward translation every frame, six legs visible cycling, no frozen pose. HEADLINE CROSS-SEED COMPARISON (read jointly with cartfoot-halfgrav-s12-acq1, this cycle): this 4th seed pair REVERSES the direction seen on s7/s10 -- OFF's total gait_valid (11/24) is slightly HIGHER than ON's (9/24), the opposite of the established cart_foot-advantage pattern (s7: 22 vs 10, s10: 17 vs 7) and different again from s11's near-parity (11 vs 10, ON slightly ahead). The one thing that DOES still replicate on this 4th seed: ON's slip/m is lower than OFF's in all 4 groups (ratio 0.79-0.88, matching s7 0.82-0.93, s10 0.83-0.89, s11 0.82-0.89) -- the slip edge is now 4-for-4 seed-robust, while the gait_valid-advantage direction is genuinely seed-dependent (2 clear ON wins, 1 near-parity, 1 OFF win). Update CURRENT_TRUTHS with this 4th data point; do not pool gait_valid counts across seeds or claim a universal cart_foot gait-health advantage -- report each pair's own gap, as the existing ruling already requires. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_cartfoot_halfgrav_offctrl_s12_acq1_gate/report.json; W&B t2r5n3mz.

