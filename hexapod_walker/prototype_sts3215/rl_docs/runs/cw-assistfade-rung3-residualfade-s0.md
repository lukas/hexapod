# cw-assistfade-rung3-residualfade-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-06T18:24:58+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**wandb_id**: 7sdm0vbk

**hypothesis**: Rung 3 (residual fade, EASIER_WALKING_CURRICULUM.md item 3): a random-weight actor whose raw action is blended with the scripted-tripod reference via applied=ref+blend*(raw-ref) (blend 0.05->1.0 annealed over the first 1.4M of this 2M-step budget) should ignite real six-leg walking more reliably than rung 2's anchor-LOSS approach, because the reference structurally dominates the applied action at low blend regardless of what the untrained policy outputs (bank-proven this cycle: a refusing 'park' raw policy is fully rescued to walking-level income at blend=0.05). Seed 0, fixed-forward 0.06 m/s, mesh/100Hz, no BC-loss anchor at all.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Ignition gate (curriculum doc, det+sto held-out, DR-0): sustained forward translation the full episode, repeated alternating support transitions, all six legs participating (no permanently planted/unloaded leg), zero falls/safety terminations, progress_ratio>=0.35 on all modes. MUST override goal.walk_residual_gate=0 (drop sched.*/walk_residual_* from the eval cfg-set) so the checkpoint is judged fully autonomous, not steered by the reference at eval-time tick~0. FAIL if any leg is chronically parked/unloaded or if behavior collapses once blend nears 1.0 in the last ~0.6M training steps (check wandb_history.csv reward trend across the anneal before concluding mechanism-vs-schedule).

**verdict**: CANARY FAIL - MECHANISM: rung 3 (residual fade) ignition gate NOT MET on seed 0. Held-out DR-0 gate: walk/det+sto gait_valid 6/6 with no leg sacrifice, BUT progress_ratio med 0.11-0.12 (bar 0.35, ~3x short), slip/m 15-17 (very high), fwd_dist ~0.05-0.07m/10s. walk_startjitter is worse: gait_valid only 2/6 det, 2/6 sto, with chronic leg sacrifice (1-3 legs) and over_current safety terminations in 3-4/6 episodes each mode. Root cause traced via per-tick wandb_history (env/sched_value vs env/reward_walk/_prog, terminations/over_current, env/height_err_mm), same fingerprint on both seeds: as the residual blend anneals 0.05->1.0 over the first 1.4M/2M steps, reward_walk declines monotonically from ~2.0 to ~0.1-0.2, reward_walk_prog goes and stays negative once blend nears 1.0, height_err_mm climbs steadily from ~0 to a plateau at ~32mm, and over_current terminations appear once blend crosses ~0.5-0.6 and PERSIST through the entire 0.6M-step full-authority settling window (no recovery). Matches the launch's own 'prediction-if-false' (policy leans on the reference during the assisted window and collapses once blend nears 1.0) but the specific compounding mechanism is now identified: --log-std-anneal-frac=1.0 anneals log_std over the SAME 2M-step budget as the blend schedule, so std has already dropped to ~0.09 by the time blend reaches 1.0 (1.4M steps) and keeps shrinking to ~0.05 through the settling window -- exploration/action authority is being squeezed shut at exactly the moment the policy needs the most room to adapt to losing the reference. Reward quarters [101.8,178.7,231.1,147.3] (Q3->Q4 decline) confirm a genuine behavioral collapse, not a still-rising-reward case. Not a kill of the mechanism -- the action-blend mechanism itself is bank-proven (structural walking regardless of raw policy at low blend); this is a SCHEDULE bug (two independent anneals racing to their floor on the same clock), fix is to decouple them (slower log-std anneal), not a same-recipe retry or mechanism abandonment. See STATUS.md for retry plan.

