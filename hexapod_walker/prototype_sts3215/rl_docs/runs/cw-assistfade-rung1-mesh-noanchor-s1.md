# cw-assistfade-rung1-mesh-noanchor-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-07T12:14:19+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-assistfade-rung1-mesh-noanchor-s0

**wandb_id**: ifih9o5t

**hypothesis**: Plain English: does rung 1 (BC init, then task-only PPO with zero ongoing anchor) hold on a SECOND seed, or was s0's clean six-leg retention a seed-specific fluke? Byte-identical recipe to cw-assistfade-rung1-mesh-noanchor-s0 (same BC-cloned scripted-tripod init, bc_anchor_coef/walk_coef/phase_lock=0.0 from step 0), only --seed changes 0->1. s0 landed CANARY PASS at mechanism-health tier (gait_valid 23/24 across walk/walk_startjitter det+sto, progress_ratio med 0.16-0.24, six legs cycling on video, only 4/24 episodes hit a safety termination) but the doc's own ignition gate requires BOTH seeds before advancing the rung.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same mechanism-health CANARY-tier bar as s0: PASS if reward does not collapse (no NaN/entropy blowup) and the held-out walk panel does not immediately revert to a static stand (progress_ratio clearly above ~0 in det mode, most episodes gait_valid with no permanently-sacrificed leg); FAIL - MECHANISM if it reverts to the static/near-zero-progress basin within 2M matching rung2's own early anchor-less failure shape. This is diagnostic only -- the FULL ignition bar (progress_ratio>=0.35, zero falls/terminations, both seeds) needs the longer acquisition follow-up, not this 2M read.

**verdict**: CANARY PASS -- 2nd-seed replication of rung1-mesh 2M mechanism-health canary CONFIRMS s0 clean retention read, even more cleanly. gate report (logs/ckpt_eval/cw_assistfade_rung1_mesh_noanchor_s1_gate/report.json): gait_valid 24/24 across ALL FOUR modes (walk/walk_startjitter det/sto) with ZERO sacrificed legs in every single episode (sac=[] throughout -- cleaner than s0 own 2M canary, which had 3-5 leg sacrifices in a handful of episodes), progress_ratio med 0.16-0.26 in every mode (matching s0 0.16-0.24 band), only 1/24 over_current termination total (vs s0 4/24). Contact-sheet video shows genuine forward translation with legs visibly cycling through swing/stance across the strip, not a static pose. This is the 2/2-seed replication the doc ignition-gate discipline requires at the CANARY tier: BC init + task-only PPO with zero anchor DOES retain the scripted-tripod clone gait at short (2M) horizon on both seeds. Per the already-verdicted sibling s0-acq12m (FAIL - MECHANISM at 12M depth, this same cycle), this 2M-clean/12M-degrades split is now the settled rung-1-mesh finding: the anchor is not needed for short-horizon retention but IS load-bearing over a full acquisition budget. Not launching an s1-acq12m follow-up -- s0 12M read already answered the depth question this run licenses, and per the acq12m verdict its own text the recipe is closed at any budget/seed, so a 2nd 12M continuation would only re-confirm a closed result at GPU cost, not open a new question.

