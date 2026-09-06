# cw-assistfade-rung3-residualfade-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-06T18:26:13+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**wandb_id**: k9tb5713

**hypothesis**: Rung 3 (residual fade, EASIER_WALKING_CURRICULUM.md item 3): a random-weight actor whose raw action is blended with the scripted-tripod reference via applied=ref+blend*(raw-ref) (blend 0.05->1.0 annealed over the first 1.4M of this 2M-step budget) should ignite real six-leg walking more reliably than rung 2's anchor-LOSS approach, because the reference structurally dominates the applied action at low blend regardless of what the untrained policy outputs (bank-proven this cycle: a refusing 'park' raw policy is fully rescued to walking-level income at blend=0.05). Seed 1, fixed-forward 0.06 m/s, mesh/100Hz, no BC-loss anchor at all.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Ignition gate (curriculum doc, det+sto held-out, DR-0): sustained forward translation the full episode, repeated alternating support transitions, all six legs participating (no permanently planted/unloaded leg), zero falls/safety terminations, progress_ratio>=0.35 on all modes. MUST override goal.walk_residual_gate=0 (drop sched.*/walk_residual_* from the eval cfg-set) so the checkpoint is judged fully autonomous, not steered by the reference at eval-time tick~0. FAIL if any leg is chronically parked/unloaded or if behavior collapses once blend nears 1.0 in the last ~0.6M training steps (check wandb_history.csv reward trend across the anneal before concluding mechanism-vs-schedule).

**verdict**: CANARY FAIL - MECHANISM: rung 3 (residual fade) ignition gate NOT MET on seed 1, same fingerprint as s0 (2/2 seeds). Held-out DR-0 gate: walk/det gait_valid 0/6 (sac [5], leg 5 chronically parked all 6 episodes), walk/sto gait_valid 6/6 but prog med only 0.04 with 2/6 over_current terms; walk_startjitter gait_valid 0/6 det, 3/6 sto, chronic 1-3-leg sacrifice, over_current in 4-7/12 episodes. progress_ratio med 0.03-0.06 across all modes (bar 0.35, ~6-10x short). Same root cause confirmed via per-tick wandb_history as s0: env/sched_value (residual blend) tracks 1:1 with reward_walk decline (2.0->0.1-0.2), reward_walk_prog goes/stays negative once blend nears 1.0 (~1.4M steps), height_err_mm climbs 0->~32mm and plateaus there through the 0.6M-step full-authority settling window (no recovery), over_current terminations spike once blend crosses ~0.5 and persist to the end. --log-std-anneal-frac=1.0 anneals log_std over the SAME 2M-step clock as the blend schedule, squeezing exploration to std~0.05 right as the policy loses reference authority -- this is a schedule-collision bug, not evidence the action-blend mechanism itself is broken (already bank-proven structural walking at low blend). Reward quarters [101.4,170.8,188.2,116.7], Q3->Q4 decline confirms genuine collapse, not 08-21 still-rising-reward. Joint rung-3 canary read (2/2 seeds): NOT ignited, same schedule-collision mechanism both seeds -- retreat is to decouple the log-std anneal from the blend anneal (slower std anneal), not a same-schedule reseed or mechanism abandonment. Relaunching both seeds this cycle with --log-std-anneal-frac widened (single lever) per STATUS.md.

