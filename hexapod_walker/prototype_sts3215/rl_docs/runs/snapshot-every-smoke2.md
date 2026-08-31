# snapshot-every-smoke2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: SMOKE PASS

**created**: 2026-08-31T17:36:12+00:00

**pod**: hexapod-mjx-train-5

**steps**: 200000

**hypothesis**: Tool re-smoke after naming fix: --snapshot-every now tags copies with exact env-steps (<out>_s<steps>.zip) so sub-interval snapshots can never collide/overwrite (first smoke showed _at0M collisions). Prediction-if-true: >=3 DISTINCT tagged files at 200k steps with snapshot-every=50k. Prediction-if-false: single file again or crash.

**gate**: SMOKE: >=3 distinct step-tagged snapshot files on pod

**verdict**: The fixed --snapshot-every tool works: 200k-step GPU smoke with snapshot-every=50k produced 3 distinct step-tagged checkpoint copies (_s57344/_s114688/_s172032) plus the normal final checkpoint, training undisturbed (3.6k fps). Tool is live (default OFF, bit-exact when off) and in use by the yaw5x retention pair launched this cycle.

**failed_reason**: process died; log tail:
         |              |
|    approx_kl            | 0.0027592718 |
|    clip_fraction        | 0.00315      |
|    clip_range           | 0.2          |
|    entropy_loss         | -7.52        |
|    explained_variance   | 0.181        |
|    learning_rate        | 0.0003       |
|    loss                 | 21.4         |
|    n_updates            | 120          |
|    policy_gradient_loss | -0.00255     |
|    std                  | 0.368        |
|    value_loss           | 43.2         |
------------------------------------------
[mjx-train] done: 200,000 steps in 55s (3,623 env-steps/s incl. setup) -> /workspace/prototype_sts3215/rl_move/sim/policies/ppo_goal_snapshot_every_smoke2.zip
[mjx-train] evaluate with the C-env harness before trusting anything (MJX_PORT.md phase-2 item 4).


