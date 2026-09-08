# cw-walkscratch-easy0905-cartfoot-halfgrav-s10-acq1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RETENTION FAIL

**created**: 2026-09-08T11:45:14+00:00

**pod**: hexapod-mjx-train-2

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-s10-acq1

**wandb_id**: s5f2imns

**hypothesis**: Does the halfgrav cart_foot (ON) seed10 arm's 40M ACQ PASS (0 falls/24, speed 0.20-0.23 m/s, gait_valid 17/24) hold or degrade with 10M more training, mirroring seed7's own cont10m retention read (HELD its 22/24 band) and extending that depth check to a 2nd seed of this same recipe/budget/gravity/torque pair.

**gate**: RETENTION at 50M cumulative: PASS/HOLDS = 0 new falls/terminations vs this run's own 40M read, gait_valid staying in-or-above its established 17/24 band, slip/m staying within +/-20% of the 40M read. Read together with the matched offctrl-s10-acq1-cont10m sibling: does the seed7 pattern (ON holds, OFF gait_valid degrades further, gap widens) generalize to a 2nd seed, or does seed10 behave differently at depth.

**verdict**: The cartfoot (ON) seed10 arm keeps walking well but its primary gated det mode's six-leg gait collapses under the extra 10M steps. gait_valid falls 17/24 -> 14/24, below the pre-registered 17/24 hold band, driven almost entirely by walk/det going from a CLEAN 6/6 at 40M to 0/6 at 50M -- every det episode now sacrifices BOTH legs [1,4] together (was zero-sacrifice at 40M). walk/sto actually improved (5/6->6/6) and startjitter groups held flat (3/6, 5/6 vs 3/6, 3/6-ish), so this is not a uniform collapse, just the deterministic mode specifically. 0 new falls/terminations (24/24 clean) and slip/m held or improved in every group (1.59/1.65/1.58/1.69 vs 40M's 1.77/1.70/1.73/1.73), so the RETENTION gate's fall/slip clauses pass but the gait_valid clause fails. Reward kept climbing the whole window (quarters 234.8/654.7/1071.5/1338.3) while the primary gated mode's gait health got WORSE -- the 08-21 misaligned-reward shape, same qualitative pattern as seed11's OFF cont10m (rising reward, gait_valid erosion), just milder (17->14 vs 10->3) and here hitting the ON arm's det mode specifically rather than a random mix. Video reviewed (walk_det_0.png strip): real forward translation every frame, no frozen statue, but the two flagged legs visibly trail/drag rather than lift-and-place. Read together with the matched offctrl-s10-acq1-cont10m sibling (also degrading further, 7/24->4/24): the ON/OFF total gait_valid GAP is unchanged at 10 (14 vs 4, was 17 vs 7), i.e. more training erodes both arms' six-leg health by a similar amount rather than closing the gap -- do not fund a 3rd continuation on this exact seed/recipe expecting the det-mode collapse to self-heal; any further depth read on this recipe needs the per-leg-utilization pricing mechanism the walkcurr/assistfade tracks are already building (walk_leg_loadslip_ratio_charge), not more raw steps. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_cartfoot_halfgrav_s10_acq1_cont10m_gate/report.json vs the 40M report; W&B s5f2imns.

