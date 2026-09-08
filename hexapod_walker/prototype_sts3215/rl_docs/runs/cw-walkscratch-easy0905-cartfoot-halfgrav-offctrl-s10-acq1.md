# cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s10-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-08T10:21:34+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s10

**wandb_id**: ghd2vc41

**hypothesis**: Own-checkpoint 40M continuation of the CANARY-PASSed joint-space (OFF) halfgrav+seed10 control: matched budget/seed sibling to cartfoot-halfgrav-s10-acq1 (already launched this window by a concurrent cycle), completing the seed10 ON/OFF pair and extending the seed7 halfgrav 2x2 acquisition result toward the 1g cell's n=3 seed cohort.

**gate**: ACQUISITION: >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det), read together with cartfoot-halfgrav-s10-acq1 at the SAME budget. PASS/CONTINUE per the 08-21 ruling if reward is still rising; slip/m vs the matched ON sibling is the headline comparison, not a hardening bar.

**verdict**: Joint-space (OFF) halfgrav seed10 40M acquisition clears its own floor gate but trails the cart_foot (ON) sibling on gait health, closing the seed10 ON/OFF pair. 0 falls/terminations in all 24 gate episodes across walk/det,sto + startjitter/det,sto; speed well above the 0.03 m/s floor (fwd med 3.07/2.87/2.96/3.04m over 20s = ~0.14-0.15 m/s). Reward quarters rise monotonically [-665.8, 209.6, 1025.6, 1340.3], completed naturally at 40,370,176 steps -- 08-21 satisfied either way since evals already clear the letter of the gate. gait_valid is 0/6, 4/6, 0/6, 3/6 = 7/24, well below ON's 17/24 (6/5/3/3), driven by a SYSTEMATIC leg1 near-park in every det episode (duty 0.04 vs 0.11-0.52 on the other five legs, identical across all 6 det episodes since start conditions are fixed) plus 2/6 startjitter/det with the same leg1 flag. slip/m med is 1.98/2.06/2.07/2.07 (det,sto,sj-det,sj-sto) vs ON's 1.77/1.70/1.73/1.73 -- ON/OFF ratio 0.89/0.83/0.84/0.84, i.e. ON has LOWER slip in all four groups, the same direction as the seed7 pair (0.82-0.93) though seed10's OFF gait-health gap (7/24 vs 17/24) is much wider than seed7's (10/24 vs 22/24). This replicates seed7's qualitative finding (cart_foot action space walks with better six-leg gait health and lower slip than joint-space at 0.5g/3x torque) on a second seed, while confirming CURRENT_TRUTHS' seed-to-seed spread warning -- do not pool gait_valid or slip ratios across seeds as one number.

