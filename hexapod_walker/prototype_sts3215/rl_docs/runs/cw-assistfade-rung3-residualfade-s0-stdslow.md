# cw-assistfade-rung3-residualfade-s0-stdslow

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T19:06:21+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-assistfade-rung3-residualfade-s0

**wandb_id**: v8iuqzhg

**hypothesis**: Rung 3 (residual fade) canary FAILED-MECHANISM on both seeds via a schedule collision: --log-std-anneal-frac=1.0 anneals log_std to its -3.0 floor over the SAME 2M-step clock as the residual-blend anneal (0.05->1.0 over 0->1.4M steps), so exploration noise is already squeezed to std~0.09 by the time the policy loses reference authority (blend=1.0) and keeps shrinking to ~0.05 through the 0.6M-step settling window with zero recovery (over_current terminations persist, height_err_mm plateaus at ~32mm, reward_walk_prog stays negative) -- both seeds showed the identical per-tick fingerprint (env/sched_value vs reward/height/termination trends in wandb_history.csv). Single-lever fix: widen --log-std-anneal-frac to 3.0 (denom=6M steps vs a 2M-step run), so std only reaches ~1/3 of the way to the -3.0 floor by the time this budget ends (std ~0.19 instead of ~0.05), giving the policy meaningfully more exploration room through the blend fade-out and settling window while leaving the blend schedule itself (proven walking-regardless-of-policy at low blend) and every other lever untouched. Prediction-if-true: ignition gate (progress_ratio>=0.35, six-leg participation, zero falls/terms) should clear where it previously failed by ~3-10x. Prediction-if-false: if progress/leg-sacrifice/over_current still fail the same way, the compounding is not std-related and the next retreat is a later/slower blend t1_steps or a longer total budget instead.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (same text as the parent canary): ignition gate (curriculum doc, det+sto held-out, DR-0): sustained forward translation the full episode, repeated alternating support transitions, all six legs participating (no permanently planted/unloaded leg), zero falls/safety terminations, progress_ratio>=0.35 on all modes. MUST override goal.walk_residual_gate=0 (drop sched.*/walk_residual_* from the eval cfg-set). FAIL if progress stays <0.35, any leg is chronically parked/unloaded, or over_current terminations reappear in the startjitter panel -- check wandb_history.csv's env/sched_value vs reward_walk/height_err_mm/terminations trend across the anneal (same method as the parent's verdict) before concluding std-vs-schedule.

