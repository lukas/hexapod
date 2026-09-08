# cw-walkscratch-easy0905-cartfoot-halfgrav-s10-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-08T10:19:03+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-s10

**wandb_id**: chxamgkj

**hypothesis**: Own-checkpoint 40M continuation of the CANARY-PASSed cart_foot (ON) halfgrav+seed10 arm: does the Cartesian foot-target action decode learn real six-leg walking at 0.5g over a full budget at a 2nd seed, and how does its slip/m compare to the matched joint-space sibling offctrl-s10-acq1 at the same depth? Extends the seed7 halfgrav 2x2 acquisition result (already ACQ PASS - PARITY) to build the n=3 seed cohort the 1g cell already has.

**gate**: ACQUISITION: >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det), read together with offctrl-s10-acq1 at the SAME budget. PASS/CONTINUE per the 08-21 ruling if reward is still rising; slip/m vs the matched OFF sibling is the headline comparison, not a hardening bar.

**verdict**: Fresh-init Cartesian foot-target (ON) halfgrav seed10 40M acquisition clears its own gate cleanly: 0 falls/terminations in 24/24 gate episodes across all 4 groups, speed_mean_m_s 0.20-0.23 in every episode (>>0.03 m/s floor). gait_valid 6/6 walk/det, 5/6 walk/sto (1 ep sacrifices leg4), 3/6 both startjitter groups (legs 1/4 sacrificed under jitter). slip/m med 1.77 det / 1.70 sto / 1.73 / 1.73 startjitter -- close to seed7's low-slip band, well under the 1g cartfoot pair. Reward quarters rise monotonically [-768.5, 21.1, 884.5, 1156.8], completed naturally at 40,370,176 steps -- 08-21 satisfied either way since evals already clear the letter of the gate. Read jointly with seed11 (same cycle): seed10's 17/24 gait_valid total is markedly healthier than seed11's 11/24, so the earlier seed7 22/24 result does not generalize across seeds -- forward-acquisition PASS and six-leg gait health are separate axes here, not one. Matched offctrl-s10-acq1 OFF sibling finished training (wandb state=finished) but its gate eval was not yet staged at read time -- ON-only PASS, no ON/OFF parity claim.

