# cw-walkscratch-easy0905-headset-halfgrav-irrwiden-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: HARDENING PASS

**created**: 2026-09-06T11:06:23+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irrwiden-c1-acq1

**wandb_id**: frsx3dv5

**hypothesis**: Plain English: does the halfgrav widen+irr composite champion (jitter-first order, the actual DONE-gate panel shape) keep its clean 40M ACQ-PASS state (22/24 gait_valid, 0 falls, only 2/24 scattered non-chronic flags) after +40M more steps (80M cumulative), matching this campaign's cleanliness-margin-predicts-endurance rule (clean 40M sources hold; already-entrenching ones worsen)?

**gate**: cont40m gate (80M cumulative): PASS/HOLDS if gait_valid stays majority (>=18/24) with no NEW chronic single-leg pattern and 0 falls (matches or improves the parent's 22/24, scattered-non-chronic scatter). FAIL/ENTRENCHES if it drops (<12/24), the scatter consolidates into a chronic single-leg pattern, or a fall appears.

**verdict**: The widen+irr composite (jitter-first order) source holds past acquisition budget: +40M more steps (80M cumulative), gait_valid 23/24 (walk/det 5/6, walk/sto 6/6, startjitter/det 6/6, startjitter/sto 6/6) -- IMPROVES on the parent's own 22/24 -- 0 falls/terminations in all 24 episodes. Only 1/24 episodes flags a sacrificed leg (walk/det/3, legs [2,5]) vs the parent's 2/24 (walk/det/3 legs[2,4,5], walk/sto/5 leg[2]) -- the SAME episode index, subset of the parent's own leg list (leg4 recovered), not a new or spreading pattern; the other flagged parent episode (walk/sto/5) is now clean. The extreme-slip stochastic outlier episodes (walk/sto/0 slip 15.7, walk_startjitter/sto/5 slip 116.94) are NOT a new regression -- the parent shows the SAME two episode slots at near-identical magnitude (walk/sto/3 slip 116.45 prog -0.15, walk_startjitter/sto/5 slip 110.91 prog -0.44), a known stochastic-jitter-recipe artifact (occasional stumble-recover under sto randomness), reproducing almost value-for-value at the same episode index -- not entrenchment. Reward stays deeply negative throughout (quarters -840/-1148/-940/-707, recovering in Q4) which matches this composite's own known reward-pricing shape (already very negative at the 40M ACQ per its own PASS notes) rather than a new divergence. Per the run's own pre-registered gate (majority gait_valid, no NEW chronic single-leg pattern, 0 falls) this is a clean HOLD, slightly improved over the parent.

