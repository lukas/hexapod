# snapshot-every-smoke

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: SMOKE PASS (superseded)

**created**: 2026-08-31T17:33:13+00:00

**pod**: hexapod-mjx-train-5

**steps**: 200000

**hypothesis**: Tool smoke: the new --snapshot-every flag (off-by-default step-tagged checkpoint copies for erosion curves) writes <out>_at<N>M.zip files without disturbing training. Prediction-if-true: run completes 200k steps and >=2 tagged snapshot files exist on the pod. Prediction-if-false: crash at first snapshot or no files.

**gate**: SMOKE: process completes + snapshot files present on pod

**verdict**: Tool smoke passed mechanically (200k steps, snapshot file written, training undisturbed) but exposed a naming defect: sub-1M snapshot intervals all mapped to the same _at0M.zip name and overwrote each other. Fixed same cycle (exact-step _s<steps>.zip tags) and re-smoked as snapshot-every-smoke2.

**failed_reason**: process died; log tail:
          |              |
|    approx_kl            | 0.0030021344 |
|    clip_fraction        | 0.00452      |
|    clip_range           | 0.2          |
|    entropy_loss         | -7.51        |
|    explained_variance   | 0.207        |
|    learning_rate        | 0.0003       |
|    loss                 | 19.3         |
|    n_updates            | 120          |
|    policy_gradient_loss | -0.00257     |
|    std                  | 0.367        |
|    value_loss           | 39           |
------------------------------------------
[mjx-train] done: 200,000 steps in 56s (3,545 env-steps/s incl. setup) -> /workspace/prototype_sts3215/rl_move/sim/policies/ppo_goal_snapshot_every_smoke.zip
[mjx-train] evaluate with the C-env harness before trusting anything (MJX_PORT.md phase-2 item 4).


