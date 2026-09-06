# cw-assistfade-rung3-residualfade-s1-longbudget

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T19:40:02+00:00

**pod**: hexapod-mjx-train-0

**steps**: 6000000

**parent**: cw-assistfade-rung3-residualfade-s1

**wandb_id**: j8l8va6k

**hypothesis**: Rung-3's 2/2 CANARY FAIL-MECHANISM (both the original pair AND the std-anneal-frac retry, 2/2 seeds each) shows a schedule collision: the residual-blend anneal completes at 1.4M/2M steps and leaves only a 0.6M-step settling window before eval, and the std-anneal-frac=3.0 single-lever fix REFUTED (worse or equal on both seeds, RL_LOG 09-06 19:2x-19:3x). Per the pre-registered fallback (do not repeat std-anneal-frac), this is the OTHER named lever: a longer total step budget with EVERY other lever (blend schedule sched.t1_steps=1.4M, log-std-anneal-frac reverted to the original default 1.0/-3.0, reward stack, random-weight init) byte-identical to the originally-failed parent -- steps 2M->6M (3x) gives a 4.6M-step settling window post-blend instead of 0.6M, AND (since log-std-anneal-frac=1.0 anneals relative to --steps) slows the std anneal's absolute-time rate 3x so std stays much higher through the blend fade-out too, attacking the same schedule-collision root cause via budget rather than the already-refuted frac lever. Seed 1 of the pair.

**gate**: MECHANISM-HEALTH CANARY ONLY (same ignition text as the parent, budget-extended not skill-graded): do not judge skill acquisition, close a behavior/reward class, or require mature gait. Ignition gate (curriculum doc, det+sto held-out, DR-0): sustained forward translation the full episode, repeated alternating support transitions, all six legs participating (no permanently planted/unloaded leg), zero falls/safety terminations, progress_ratio>=0.35 on all modes. MUST override goal.walk_residual_gate=0 (drop sched.*/walk_residual_* from the eval cfg-set). FAIL if progress stays <0.35, any leg is chronically parked/unloaded, or over_current terminations reappear in the startjitter panel. If this ALSO fails the same way (3rd lever refuted for this rung), the compounding is not a schedule-hyperparameter issue at all and the mechanism itself needs re-examination, not another schedule tweak.

