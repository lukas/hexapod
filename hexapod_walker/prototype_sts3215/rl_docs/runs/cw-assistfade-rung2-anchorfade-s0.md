# cw-assistfade-rung2-anchorfade-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T10:48:26+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-assistfade-rung1-bcinit-taskonly-s1

**wandb_id**: fd7gmi2z

**hypothesis**: Plain English: does a genuinely random-weight actor, given a STRONG BC anchor (train.bc_anchor_coef=3.0, the campaign's most common strong dose) that anneals smoothly to zero only after the actor clears the curriculum doc's own ignition bar (walkcurr_cert.ignition_gate_pass, via the just-built train.bc_anchor_anneal_gate mechanism), learn to walk and KEEP walking once the anchor fades -- rung 2 of the assistance-removal ladder (EASIER_WALKING_CURRICULUM.md), the doc's prescribed retreat from rung 1 (BC-clone init, task-only PPO, no ongoing anchor), which is now CLOSED 3/3 seeds FAIL at 8-10M (walkcurr STATUS/SKILLS.md, 09-06). Same fixed 0.06 m/s forward command diet, mesh/100Hz, DR-0, episode-seconds=10, as rung 1 -- the ONLY deltas are (a) random init (no --init-from) instead of the BC-clone warm start, and (b) train.bc_anchor_coef=3.0 + train.bc_anchor_anneal_gate=1 instead of 0.0 (every anneal sub-knob at its built-in default: 4M anneal steps, 500k check interval, 8 assay episodes, 0.35 min-progress -- matching ignition_gate_pass's own bar). Two seeds (0,1) per the curriculum doc's own two-seed gate. Precondition: the intermediate-state semantics bank (test_task_semantics.py test_assistfade_rung2_*, 5/5 green) now confirms this UNCHANGED reward stack prices every named landmark (weight_shift/one_lift/one_placement/one_transition/two_steps_fall/static_stand/clean_gait) in the intended shape under the anchor-agnostic env reward -- this launch is the FIRST real exercise of the anneal-gate training-side mechanism itself (built 09-06 ~09:3x, no dry-run harness existed for it).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY (2M, mechanism-health + ignition, judged JOINTLY across both seeds per the curriculum doc). PASS/CONTINUE if by 2M the anchor has not yet annealed (bc_anchor_anneal_pass_step still None is fine at this budget) AND the policy has not been destroyed while under the strong anchor -- gait_valid/progress comparable to rung-1s own BC-clone-init canary reads, 0 unexplained falls. The REAL gate is downstream: once bc_anchor_anneal_pass_step latches (ignition_gate_pass clears mid-training) and the coefficient anneals through train.bc_anchor_anneal_steps, does deterministic held-out video/eval STILL show sustained forward translation, all-six-leg participation, zero falls, progress_ratio>=0.35 (the doc's own ignition bar) with the anchor at/near zero -- that read needs a longer continuation once this canary confirms the mechanism does not blow up immediately. FAIL - MECHANISM if training crashes, the anchor loss diverges/NaNs, or the policy is already worse than a random walk at 2M (would mean the anneal-gate wiring itself is broken, not a rung-2 science question).

