# cw-walkscratch-easy0905-headset-base-medhead-placementjit-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-05T22:47:30+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-medhead-acq1

**wandb_id**: pydwxzqm

**hypothesis**: Plain English: same placement-jitter-during-training hypothesis as sibling arm irr-placementjit-c1 (read together), applied to the 5-way medhead heading rung instead of the 3-way irr rung -- does exposing training to the SAME start-pose distribution eval_checkpoint.py's walk_startjitter panel already tests fix medhead_acq1's chronic leg-1/4 favoritism (2/6 walk/det, 1/6 walk_startjitter/det gait_valid per this cycle's own swinggate-fix triage), after walk_gait_gate/walk_duty_gate/walk_swing_gate all failed on this exact checkpoint? Same code-read justification: --dr-scale 0.0 with no placement/bad-start override means training never saw a perturbed start pose; dose matches eval_checkpoint.py's own walk_startjitter defaults (jitter 3deg, 25% chance one 8-16deg-off joint) to close the train/eval gap directly. Arm 2/3 of the batch (see irr-placementjit-c1 for the full code citation).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (2M): repair-signal if walk_startjitter/det's flagged legs (1,4) majority-clear the harness gait_valid duty>0.10 bar with 0 new falls, AND walk/det gait_valid stays >= its own undosed medhead_acq1 baseline (2/6, no regression). FAIL - MECHANISM if the same legs stay majority-parked in walk_startjitter/det regardless of training-time start-pose exposure.

**verdict**: CANARY FAIL - MECHANISM: start-pose jitter (dr.placement_noise_deg=3.0, dr.bad_start_prob=0.25) retrofit onto medhead_acq1 does NOT repair base(1g) leg-1/4 favoritism and REGRESSES vs its own parent. Evidence: harness gait_valid tally 5/24 at this 2M canary (walk/det 0/6, walk/sto 4/6, walk_startjitter/det 0/6, walk_startjitter/sto 1/6) vs parent medhead_acq1's own landed 40M report 10/24 (walk/det 1/6, walk/sto 6/6, walk_startjitter/det 1/6, walk_startjitter/sto 2/6, logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_medhead_acq1_gate/report.json) -- every mode flat-to-worse, walk_startjitter/det (the targeted mode) stays at the same 0-1/6 floor, no majority-clear. Same legs [1]/[4] sacrificed in every failing episode, 0 falls/terms in all 24 (not behavioral impossibility -- a clean mechanism failure). Matches the sibling irr-placementjit-c1's own independently-verdicted CANARY FAIL - MECHANISM (same batch, same regression-vs-parent pattern, same fingerprint) exactly. Why: a training-time state-distribution fix (exposing jittered starts) does not touch the per-leg-utilization incentive that 7 prior reward-price mechanisms already failed to fix on this family -- the checkpoint already saw jittered starts during dosed training and still fails the exact mode that tests them, so this is an exploration/policy-capacity ceiling, not a missing-experience gap. Next: with this arm, placement-jitter joins the reward/state-price family as an 8th closed repair lever for base(1g) leg-favoritism (pending the 3rd sibling s0c1-placementjit-fresh, verdicted same cycle). Do not fund another placement-jitter/reward-price arm on base(1g) without a genuinely new causal theory; per STATUS's standing conclusion the next lever is structural (curriculum-widen from a leg-healthy champion per halfgrav's validated widen2 recipe, or reallocate base(1g) spend to the healthy halfgrav lineage).

