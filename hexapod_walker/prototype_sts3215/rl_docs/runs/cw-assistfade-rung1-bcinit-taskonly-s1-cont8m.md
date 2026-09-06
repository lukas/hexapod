# cw-assistfade-rung1-bcinit-taskonly-s1-cont8m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T03:34:12+00:00

**pod**: hexapod-mjx-train-7

**steps**: 8000000

**parent**: cw-assistfade-rung1-bcinit-taskonly-s1

**wandb_id**: nvpkarrc

**hypothesis**: Plain English: the task-only policy walks cleanly but at ~60% of the required forward progress after its tiny 2M canary -- give the same policy 5x more optimization budget and see if speed alone rises to the ignition bar without wrecking the gait. Continuation of cw-assistfade-rung1-bcinit-taskonly-s1 from its own 2M final checkpoint (init-from-source), byte-identical recipe (rung-1 EASIER_WALKING_CURRICULUM: BC init, task-only PPO, no anchor, fixed forward 0.06 m/s, 10s eps, mesh/100Hz). Canary evidence: gait_valid 24/24 across all 4 modes, 0 falls/terms, all six legs cycling on video (walk_det strip clean, level body), det prog med 0.22 vs 0.35 ignition bar, slip 8-12 recorded. Reward not flat (quarters 85/111/168/109). Per the 08-21 ruling this is continue-not-fail: the 2M gate was mechanism-health only. Prediction-if-true: det prog med >= 0.35 by 10M total with gait_valid intact. Prediction-if-false: prog plateaus <0.30 with reward plateaued => rung-1 budget-ceiling evidence, retreat per doc (rung-2 slower fade / rung-3 residuals), NOT a reward-dose/architecture retry. Joint rung-1 read with s0 stays with the cycle triaging s0's still-running gate eval.

**gate**: IGNITION at 10M total (EASIER_WALKING_CURRICULUM.md bar, own-cfg det panel, video first): sustained forward translation full episode, repeated alternating support transitions, all six legs participating (no planted/unloaded leg), ZERO falls and ZERO safety terminations, progress_ratio >= 0.35 det med (canary baseline 0.22). Slip/current recorded, not gated at ignition. PASS => this seed's rung-1 ignition met (joint with sibling seeds) => speed-band hardening + rung-2 anchor-fade design (intermediate-state semantics bank owed BEFORE rung-2 launch). FAIL with gait clean but prog plateaued and reward flat => rung-1 ceiling: retreat one rung per doc. FAIL gait destroyed => same retreat. Never a reward-dose or architecture retry on this rung (doc-binding).

