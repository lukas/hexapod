# cw-walkscratch-easy0905-headset-base-medhead-placementjit-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T22:47:30+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-medhead-acq1

**wandb_id**: pydwxzqm

**hypothesis**: Plain English: same placement-jitter-during-training hypothesis as sibling arm irr-placementjit-c1 (read together), applied to the 5-way medhead heading rung instead of the 3-way irr rung -- does exposing training to the SAME start-pose distribution eval_checkpoint.py's walk_startjitter panel already tests fix medhead_acq1's chronic leg-1/4 favoritism (2/6 walk/det, 1/6 walk_startjitter/det gait_valid per this cycle's own swinggate-fix triage), after walk_gait_gate/walk_duty_gate/walk_swing_gate all failed on this exact checkpoint? Same code-read justification: --dr-scale 0.0 with no placement/bad-start override means training never saw a perturbed start pose; dose matches eval_checkpoint.py's own walk_startjitter defaults (jitter 3deg, 25% chance one 8-16deg-off joint) to close the train/eval gap directly. Arm 2/3 of the batch (see irr-placementjit-c1 for the full code citation).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (2M): repair-signal if walk_startjitter/det's flagged legs (1,4) majority-clear the harness gait_valid duty>0.10 bar with 0 new falls, AND walk/det gait_valid stays >= its own undosed medhead_acq1 baseline (2/6, no regression). FAIL - MECHANISM if the same legs stay majority-parked in walk_startjitter/det regardless of training-time start-pose exposure.

