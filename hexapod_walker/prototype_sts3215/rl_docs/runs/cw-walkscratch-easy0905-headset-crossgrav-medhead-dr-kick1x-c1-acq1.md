# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kick1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-06T06:26:19+00:00

**pod**: hexapod-mjx-train-10

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kick1x-c1

**wandb_id**: g2mlnyd9

**hypothesis**: HARDENING continuation off the FIRST fall in the whole DR-restoration sweep: kick1x-c1's own 2M canary (dr.walk_kick_prob=0.3 active during training, not just eval) already trained with the kick on and still produced one tilt_roll termination at eval time, but its training reward was RISING every quarter (5/62/132/177, canary-scale budget only) -- per the 08-21 run-interpretation ruling (bad eval + rising reward = continue, not stop). Warm-starting from kick1x-c1's own checkpoint and running a real 40M acquisition-scale budget (matching every other axis's ACQ/hardening scale in this campaign) tests whether more training time on the SAME kick dose closes the fall, rather than throwing away the 2M of kick-specific adaptation already banked.

**gate**: PASS/ACQ if the full 4-panel harness at 40M reaches 0 falls (matching the strict fall-trigger the 2M canary failed) with aggregate gait_valid staying majority (>=18/24) and no new chronic single-leg sacrifice. FAIL/INFORMATIVE-NEGATIVE if a fall still appears at 40M -- shows kick recovery at this dose (0.3 prob, 8-18deg) is a harder binding constraint than a training-budget problem, and either the dose needs lowering or a dedicated recovery-reward mechanism is needed (design pass, not a further blind budget increase).

**verdict**: INFORMATIVE-NEGATIVE, exactly matching the gate's own pre-registered concern. At 40M ACQ scale the mid-stride kick-perturbation axis (dr.kick_prob=0.3, 8-18deg impulse) still produces 1 fall: walk_startjitter/sto ep4 TERM tilt_roll, sac=[2,4], forward_dist collapses to 0.09m (vs 1.4-2.7m every other episode). Frame strip (walk_startjitter_sto_4.png) confirms a genuine roll-over, not a metric artifact -- the robot visibly tips and one leg splays awkwardly by the final frames. Aggregate gait_valid is otherwise majority-healthy (20/24, 3 other non-chronic single-leg flags in different modes/legs, no repeating pattern) and training reward was still rising through all 4 quarters (523->951->1058->1120) -- per the 08-21 ruling this is read together with the gate's own pre-registered framing, not a reflex kill: the gate explicitly said a fall at 40M would show kick-recovery at this dose is a genuine binding constraint, not a training-budget problem, and named the fix as a dose reduction or a dedicated recovery-reward mechanism, not more blind budget. Why: an 8-18deg random-direction mid-stride kick is a harder perturbation than push/extpush (which both passed clean) -- it's plausible landing on 3-4 legs mid-stride with this magnitude of impulse is occasionally unrecoverable at the champion's current margin. Next: try a lower kick-magnitude dose (kickhalf1x-c1, already in flight per this campaign) as the dose-response read before spending a design pass on a dedicated kick-recovery reward term.

