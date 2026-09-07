# cw-assistfade-rung1-mesh-noanchor-s0-acq12m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL - MECHANISM

**created**: 2026-09-07T12:18:15+00:00

**pod**: hexapod-mjx-train-0

**steps**: 12000000

**parent**: cw-assistfade-rung1-mesh-noanchor-s0

**wandb_id**: fsluqnkg

**hypothesis**: Plain English: does rung 1's clean 2M canary retention (BC init, then task-only PPO with zero ongoing anchor) survive a full 12M honest budget, or does the gait degrade/collapse the longer PPO trains without any anchor pulling it back? Continuation of the just-CANARY-PASSed cw-assistfade-rung1-mesh-noanchor-s0 (warm-started from its own 2M checkpoint, same recipe, no new anchor introduced), matching rung0's own canary(2M)->acquisition(12m) pattern.

**gate**: FULL ignition-gate depth read (curriculum doc): held-out det+sto panel across walk/walk_startjitter -- PASS if sustained forward translation the whole episode, all six legs participating (no permanently planted/unloaded leg), zero falls/safety terminations, progress_ratio med >= 0.35 in det mode. FAIL - MECHANISM if it degrades from the 2M canary's clean read (new chronic leg sacrifice, falls appear, or progress_ratio collapses toward 0) despite more budget. FAIL - PARTIAL if terminations/slip stay but progress_ratio genuinely clears 0.35 with clean six-leg gait.

**verdict**: Rung1-mesh (BC init + task-only PPO, zero anchor from step 0) does NOT survive a full 12M honest budget -- it degrades from the 2M canary's clean read exactly per this run's own pre-registered FAIL-MECHANISM branch. Evidence: gate report (logs/ckpt_eval/cw_assistfade_rung1_mesh_noanchor_s0_acq12m_gate/report.json): gait_valid 0/24 across walk+walk_startjitter det+sto (down from the 2M canary's 23/24), progress_ratio med collapsed to 0.02-0.05 in every mode (down from 0.16-0.24, nowhere near the 0.35 ignition bar), 3-6 legs sacrificed per episode in every single one of the 24 held-out episodes (up from an occasional 3-leg sacrifice), over_current terminations in 14/24 episodes (up from 4/24). Contact-sheet/frame-strip video (walk_det_3.png, contact_sheet.png) shows the SAME static splayed-leg pose across the whole 20s episode in every strip -- not a walking gait, not mid-degradation motion. Training reward corroborates: ep_rew_mean crashed from +10 (step 49k) to a -1253 nadir (step 7.1M) and never recovered, settling -400..-570 for the back half (quarters [-62,-368,-685,-503]) -- this is NOT the 08-21 rising-reward continue case, reward and eval degraded together. Root cause read directly: env/walk_loadslip_ratio sits chronically at 4.5-5.0 (above loadslip_ok=3.0, near loadslip_max=6.0) for the whole back half of training, and env/reward_park_duty grows more negative over time (-0.30 early -> -0.64 by step 10M) -- without any ongoing anchor pulling the policy back toward the BC clone's gait, PPO drifts away from the retained-but-fragile 2M gait into a higher-slip, higher-current, more-leg-sacrificing regime that the task reward alone does not prevent. This closes the open question the s0 2M canary raised: the anchor (in some form) IS load-bearing over a full acquisition budget, even starting from an already-walking BC clone -- rung1-noanchor is not a viable path to the ignition gate at depth, matching why every later rung (2-4) keeps some anchor/handoff variant. Do not relaunch this exact zero-anchor recipe at any budget; the mesh rung1 gap the ledger audit flagged is now closed with real data (2M: partial retention: CANARY PASS; 12M: degrades: FAIL-MECHANISM).

