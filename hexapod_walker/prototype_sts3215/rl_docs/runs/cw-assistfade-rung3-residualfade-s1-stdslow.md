# cw-assistfade-rung3-residualfade-s1-stdslow

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T19:09:44+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-assistfade-rung3-residualfade-s1

**wandb_id**: zogkl69o

**hypothesis**: Same as -s0-stdslow (see its own hypothesis): rung 3's 2/2 CANARY FAIL-MECHANISM traced to a schedule collision between the residual-blend anneal (0.05->1.0 over 0->1.4M/2M steps) and --log-std-anneal-frac=1.0 (log_std anneal on the SAME clock) squeezing exploration to std~0.05 exactly when the policy must adapt to losing reference authority. Single-lever fix: --log-std-anneal-frac=3.0 (std only ~1/3 annealed by 2M steps, ~0.19 vs ~0.05) leaving the blend schedule and every other lever unchanged. Seed 1, paired with -s0-stdslow for the same 2/2-seed read this track has used at every rung so far.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (same text as the parent canary): ignition gate (curriculum doc, det+sto held-out, DR-0): sustained forward translation the full episode, repeated alternating support transitions, all six legs participating (no permanently planted/unloaded leg), zero falls/safety terminations, progress_ratio>=0.35 on all modes. MUST override goal.walk_residual_gate=0 (drop sched.*/walk_residual_* from the eval cfg-set). FAIL if progress stays <0.35, any leg is chronically parked/unloaded, or over_current terminations reappear in the startjitter panel -- check wandb_history.csv's env/sched_value vs reward_walk/height_err_mm/terminations trend across the anneal before concluding std-vs-schedule.

