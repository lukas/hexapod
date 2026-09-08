# cw-walkscratch-easy0905-cartfoot-halfgrav-s11-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-08T10:21:05+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-s11

**wandb_id**: 6ldf24zk

**hypothesis**: Own-checkpoint 40M continuation of the CANARY-PASSed cart_foot (ON) halfgrav+seed11 arm: does the Cartesian foot-target action decode learn real six-leg walking at 0.5g over a full budget at a 3rd seed, completing the n=3 (seed7/10/11) halfgrav acquisition cohort the 1g cell already has; slip/m vs the matched joint-space sibling offctrl-s11-acq1 at the same depth is the headline comparison.

**gate**: ACQUISITION: >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det), read together with offctrl-s11-acq1 at the SAME budget. PASS/CONTINUE per the 08-21 ruling if reward is still rising; slip/m vs the matched OFF sibling is the headline comparison, not a hardening bar.

**verdict**: Fresh-init Cartesian foot-target (ON) halfgrav seed11 40M acquisition clears the letter of its gate but with a distinct gait pathology: 0 falls/terminations in 24/24 gate episodes across all 4 groups, speed_mean_m_s 0.20-0.24 in every episode (>>0.03 m/s floor). gait_valid is 0/6 in BOTH deterministic groups (walk/det, walk_startjitter/det) -- every single det episode sacrifices leg1 (startjitter/det also adds leg4 twice) -- versus 6/6 walk/sto and 5/6 startjitter/sto. slip/m med 1.61 det / 1.58 sto / 1.50 / 1.69 startjitter, similar magnitude to seed10/seed7. Reward quarters rise monotonically [-721.1, 109.1, 922.6, 1177.3], completed naturally at 40,370,176 steps -- 08-21 satisfied. gait_valid total 11/24 (0,6,0,5), clearly worse than seed10's 17/24 and seed7's 22/24: the deterministic-mode leg1 dropout is systematic (100% of det episodes, both jitter conditions) not noise, so the seed7 22/24 six-leg result is NOT a general property of this recipe -- it varies by seed and needs per-seed reporting, not pooling. Matched offctrl-s11-acq1 OFF sibling finished training (wandb state=finished) but its gate eval was not yet staged at read time -- ON-only PASS, no ON/OFF parity claim.

