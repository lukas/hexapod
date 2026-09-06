# cw-assistfade-rung3-residualfade-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T18:26:13+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**wandb_id**: k9tb5713

**hypothesis**: Rung 3 (residual fade, EASIER_WALKING_CURRICULUM.md item 3): a random-weight actor whose raw action is blended with the scripted-tripod reference via applied=ref+blend*(raw-ref) (blend 0.05->1.0 annealed over the first 1.4M of this 2M-step budget) should ignite real six-leg walking more reliably than rung 2's anchor-LOSS approach, because the reference structurally dominates the applied action at low blend regardless of what the untrained policy outputs (bank-proven this cycle: a refusing 'park' raw policy is fully rescued to walking-level income at blend=0.05). Seed 1, fixed-forward 0.06 m/s, mesh/100Hz, no BC-loss anchor at all.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Ignition gate (curriculum doc, det+sto held-out, DR-0): sustained forward translation the full episode, repeated alternating support transitions, all six legs participating (no permanently planted/unloaded leg), zero falls/safety terminations, progress_ratio>=0.35 on all modes. MUST override goal.walk_residual_gate=0 (drop sched.*/walk_residual_* from the eval cfg-set) so the checkpoint is judged fully autonomous, not steered by the reference at eval-time tick~0. FAIL if any leg is chronically parked/unloaded or if behavior collapses once blend nears 1.0 in the last ~0.6M training steps (check wandb_history.csv reward trend across the anneal before concluding mechanism-vs-schedule).

