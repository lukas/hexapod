# cw-walkscratch-easy0905-headset-crossgrav-medhead-irrwiden-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T03:54:54+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-irrfwd-c1-acq1

**wandb_id**: jbpj69ir

**hypothesis**: Plain English: sibling composite to medhead-widenirr-c1, opposite order -- start from the mature irr-jitter champion (medhead-irrfwd-c1-acq1, ACQ PASS at 40M) and add the full 8-way heading-widen set on top, natively at 1g. Tests whether composition order matters for the same two axes (widen-then-irr vs irr-then-widen), matching the halfgrav family's own irrwiden/widenirr pair-testing discipline.

**gate**: CANARY PASS if aggregate gait_valid stays majority-clean (>=20/24) with 0 falls and no NEW chronic leg sacrifice beyond what either single-axis parent already showed; FAIL if it collapses toward chronic leg-1/4 sacrifice or falls appear.

**verdict**: CANARY PASS, matching this gate's own pre-registered PASS branch (aggregate gait_valid majority-clean, 0 falls, no NEW chronic leg pattern beyond either single-axis parent). Sibling composite to medhead-widenirr-c1 (concurrent cycle), opposite order: started from the mature irr-jitter champion (medhead-irrfwd-c1-acq1, ACQ PASS at 40M) and added the full 8-way heading-widen set on top, natively at 1g. Result: aggregate gait_valid 23/24 -- walk/det 5/6 (1 flagged episode, sac=[5], leg-5 duty softening -- matches medhead-irrfwd-c1-acq1's OWN already-documented leg-2/5 softening signature, not a new pathology), walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6. 0 falls/terminations across all 24 episodes. Frame strip (walk_det_3, the flagged episode) shows genuine six-leg cycling and clear body translation across the floor tiles, not dragging/frozen. slip_per_m mostly tight (4-8), with the expected reversal-heading spin-in-place outliers (15-190 on 2 sto episodes) already documented across this widen/reversal family. Reward quarters declining/negative ([-24.8,-101.5,-119.4,-221.9]) -- consistent with (not worse than) this same lineage's known always-on cross-track-penalty signature at reversal headings under the widen heading set (already read as expected, not misalignment, on sibling widen-composite PASSes this cycle), not a fresh red flag given the clean gait evidence. A separate SESSION eval (stand-seat + this walk policy vs ppo_goal_cw_stand_holdbc1_hard1) reads HARD FAIL (over_current on rise/fwd/left/right/back) -- informational rider only, outside this gate's own pre-registered scope (walk-harness gait_valid/falls/chronic-pattern), not evaluated here. Why: this is the 2nd composition-order test for the widen+irr pair on the medhead base (after medhead-widenfwd/irrfwd's own individual-axis PASSes) -- like widen2c1-irrfwd-c1 and widenirrc3-abrupt-c1 this cycle, extends the compose-after-transfer generalization finding to yet another base/order combination. Next: eligible for a matched 40M ACQ continuation per the medhead/widen2c1/s1acq/s3acq precedent; not launched by this cycle (concurrent cycles already own medhead-widenirr-c1's sibling result and multiple ACQ continuations are already in flight/queued this wave -- see refill notes).

