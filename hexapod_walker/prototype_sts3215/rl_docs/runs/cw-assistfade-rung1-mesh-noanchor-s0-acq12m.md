# cw-assistfade-rung1-mesh-noanchor-s0-acq12m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T12:18:15+00:00

**pod**: hexapod-mjx-train-0

**steps**: 12000000

**parent**: cw-assistfade-rung1-mesh-noanchor-s0

**wandb_id**: fsluqnkg

**hypothesis**: Plain English: does rung 1's clean 2M canary retention (BC init, then task-only PPO with zero ongoing anchor) survive a full 12M honest budget, or does the gait degrade/collapse the longer PPO trains without any anchor pulling it back? Continuation of the just-CANARY-PASSed cw-assistfade-rung1-mesh-noanchor-s0 (warm-started from its own 2M checkpoint, same recipe, no new anchor introduced), matching rung0's own canary(2M)->acquisition(12m) pattern.

**gate**: FULL ignition-gate depth read (curriculum doc): held-out det+sto panel across walk/walk_startjitter -- PASS if sustained forward translation the whole episode, all six legs participating (no permanently planted/unloaded leg), zero falls/safety terminations, progress_ratio med >= 0.35 in det mode. FAIL - MECHANISM if it degrades from the 2M canary's clean read (new chronic leg sacrifice, falls appear, or progress_ratio collapses toward 0) despite more budget. FAIL - PARTIAL if terminations/slip stay but progress_ratio genuinely clears 0.35 with clean six-leg gait.

