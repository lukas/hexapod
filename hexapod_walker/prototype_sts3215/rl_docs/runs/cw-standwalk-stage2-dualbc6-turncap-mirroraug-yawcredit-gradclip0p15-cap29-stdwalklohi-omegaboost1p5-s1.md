# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-omegaboost1p5-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-03T17:45:52+00:00

**pod**: hexapod-mjx-train-7

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi-s1

**wandb_id**: 8kyrbmbn

**hypothesis**: Plain English: this cycle found (zero-training, no GPU) that the scripted teacher's combined-tick wz loss is a friction/thrust-allocation effect, not an IK/geometry-clipping bug (no IK infeasibility, coxa-yaw excursion is LARGER not smaller under combined) -- vx numerically dominates the per-leg omega contribution to the foot-target formula, starving yaw of the shared ground-reaction budget. Multiplying the omega fed to the teacher (TripodGait.set_velocity) on combined ticks only (new train.bc_anchor_teacher_omega_boost, default 1.0=bit-exact, mirrors bc_anchor_walk_combined_skip's gating) recovers real wz on the SCRIPTED teacher itself (probe_turn_authority.py --policy scripted --scripted-omega-boost, zero training: boost=2.0 wz_med 0.072->0.160 rad/s (+122%) at vx_med 0.034->0.026 (-24%); boost=1.5 wz_med ->0.117 (+62%) at vx_med ->0.032 (-6%)), with pure-turn and straight-walk ticks PROVEN bit-exact untouched (test_probe_turn_authority.py, test_bc_anchor.py). This canary asks whether a boosted-teacher BC-anchor retrain converts that scripted-level authority recovery into RL-checkpoint-level combined-tick wz recovery without a pure-turn/straight-walk regression.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M-step canary vs the matched control (cap29-stdwalklo-hi{,-s1}, identical recipe minus this flag): PASS if probe_turn_authority.py --vx-cmds combined-tick wz_med (vx=0.08,wz=+-0.25) on this checkpoint beats the checkpoint-scope combined comparator (yawdensity_canary_s1: +0.145/-0.107) on BOTH signs without a pure-turn or straight-walk regression >10% vs control, and without new terminations on a walk-only flat DR-0 proxy read; FAIL if combined wz_med is flat/worse on either sign or course/direction_err_med/gait_valid regress vs control. (seed1 twin, read against cap29-stdwalklo-hi-s1)

