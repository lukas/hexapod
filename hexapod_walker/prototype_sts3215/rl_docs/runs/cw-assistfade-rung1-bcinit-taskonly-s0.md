# cw-assistfade-rung1-bcinit-taskonly-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T02:46:31+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkteach-scripted-allhead-canary-r1

**wandb_id**: vf3f9kbw

**hypothesis**: Plain English: can RL keep a walking gait alive without the teacher holding its hand — start from the mesh/100Hz scripted-tripod BC clone that already walks (ppo_goal_cw_walkteach_scripted_allhead_bc1_std25, pre-RL direction gate PASS), remove EVERY ongoing BC/anchor/imitation term, and train task-only PPO on a fixed slow 0.06 m/s forward command, DR-0, 10 s walk-only episodes. Rung 1 of the assistance-removal ladder (rl_docs/EASIER_WALKING_CURRICULUM.md; track assistfade, registered this cycle). Ledger-audited first unproven rung: the primitive/25Hz analog (cw-amp-m2-bcinit-sec5-noamp{,-seed1}, 08-22) passed 2/2 but families do not transfer; every mesh-era BC-init walk run to date carries an ongoing bc_anchor stack (rung 0). Recipe = walkteach canary-r1 byte-identical except: train.bc_anchor_*=0, reward.walk_anchor_gate=0, fixed-forward-only diet (heading 0, stops 0, park-start 0, resample no-op), 0.06 m/s (inside the clone's 0.06-0.10 envelope), 10 s episodes. No new reward keys; the exact anchor-free cfg's pricing ordering (gait > stall > park) is pinned by the new ASSISTFADE_RUNG1 bank in test_task_semantics.py (2/2 PASS, snapshot assistfade-rung1-track-and-bank-090601). Prediction-if-true: gait survives anchor removal, det walking stabilizes at 0.06 m/s. Prediction-if-false: gait destroyed within 2M => rung 2 (slower anchor fade) per the doc, NOT a reward-dose retry.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. IGNITION canary (2M, EASIER_WALKING_CURRICULUM.md behavioral gate; judged JOINTLY with -s1, both seeds must pass): det held-out video/eval on own cfg — sustained forward translation for the full episode, repeated alternating support transitions, all six legs participating (no permanently planted or unloaded leg), ZERO falls and ZERO safety terminations, progress_ratio >= 0.35. Slip and current RECORDED but not gated at ignition (mature 2.9 slip band not required). PASS both seeds => harden ONE dimension (speed band first) + design rung-2 anchor fade (owes the full intermediate-state semantics bank before launch). FAIL with gait destroyed => retreat: rung 2 slower anchor fade or rung 3 tighter residual bounds — doc-binding: NOT another raw-joint reward-dose/architecture sweep.

