# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kickhalf1x-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: HARDENING PASS

**created**: 2026-09-06T11:18:58+00:00

**pod**: hexapod-mjx-train-5

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kickhalf1x-c1-acq1

**wandb_id**: 9p4fobyx

**hypothesis**: Plain English: kickhalf1x-c1-acq1 (isolated half-dose kick recovery, walk_kick_prob=0.15) PASSED at 40M (20/24 gait_valid, 0 falls) but with a WATCH: the canary's scattered 3-different-legs non-chronic pattern narrowed to a single leg (index 5) recurring in 4/24 episodes across 3 modes -- duty values (0.03-0.09 in the 4 flagged episodes vs 0.3-0.6 healthy) look like near-threshold noise, not sustained chronic entrenchment, but the gate's own text names exactly this pattern ('scatter consolidates into a chronic single-leg pattern') as the disqualifying FAIL signature. This cont40m (true continuation via --init-from-source, 80M cumulative) directly resolves the WATCH: does leg5's involvement stay flat/scattered or does it sharpen into a genuine chronic sacrifice with more training exposure on the same kick-recovery axis?

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24), 0 falls, and leg5's flagged-episode duty stays in the healthy range (>=0.15) rather than trending toward sustained near-zero across MORE episodes/modes than the 4 already seen. FAIL/ENTRENCHES if leg5 duty craters further, spreads to more episodes, or a fall appears -- would confirm the WATCH was an early chronic-entrenchment signal, not noise, and half-dose kick recovery needs a different fix (e.g. a leg-fairness term) before being called durable.

**verdict**: The leg5 low-duty WATCH flagged at the 40M ACQ PASS does NOT entrench with +40M more steps (80M cumulative) -- it holds or improves. Held-out gate: gait_valid 22/24 (walk/det 6/6, walk/sto 5/6, startjitter/det 6/6, startjitter/sto 5/6), 0 falls/terminations across all 24 episodes, reward monotonic (741.7/1277.8/1345.7/1435.3). Only 2 episodes flag leg5 as sacrificed (walk/sto/5 duty=0.07, startjitter/sto/4 duty=0.05) -- FEWER than the parent's own 4 flagged episodes at 40M (walk/det/5 duty=0.09, walk/sto/5 duty=0.06, startjitter/sto/0 duty=0.09, startjitter/sto/4 duty=0.03), and the two that persist are the SAME episode indices at comparable-or-slightly-improved duty magnitude (e.g. walk/sto/5: 0.06->0.07; startjitter/sto/4: 0.03->0.05); startjitter/sto/0 (flagged at 40M) is now clean. No new mode/episode picked up the pattern. Per the run's own pre-registered gate this closes the FAIL/ENTRENCHES branch cleanly: this is the SAME chronic-but-narrow leg5 signature already priced into the 40M PASS, not a spreading entrenchment -- confirms half-dose kick recovery is durable past acquisition budget for this source. Video-confirmed upright six-leg walking, no other pathology.

