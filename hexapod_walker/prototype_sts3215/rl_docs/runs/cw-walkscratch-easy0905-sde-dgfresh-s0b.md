# cw-walkscratch-easy0905-sde-dgfresh-s0b

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T15:55:57+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**wandb_id**: vwnbmgq2

**hypothesis**: Plain English: the walk_duty_gate mechanism-health canary batch (sde-s2-dg1 etc) was warm-started full-strength (dose 1.0 instant) off an already-CONVERGED 40M LEGPARK-exploiter checkpoint and collapsed to a NEW degenerate (spin-in-place / high-current instability on bare sde, full freeze-in-a-stance on sdehalfgrav-remcost) rather than recovering genuine six-leg walking within the 2M retrain budget -- confounding two different questions: is walk_duty_gate itself a sound mechanism, vs can a mature exploiter policy relearn fast enough after an abrupt income-shock. This arm isolates the first question: train FROM SCRATCH (fresh init, no entrenched exploit to escape) with walk_duty_gate=1.0 active from step 0, identical to the sde-s0 base recipe otherwise (bare gravity, gSDE). If-true: a real six-leg gait emerges within 2M (or is clearly progressing, not frozen) -- mechanism is sound, warm-start shock was the confound, re-approach LEGPARK repair via a gradual dose ramp instead of instant full-strength. If-false: fresh init ALSO retreats to freeze/park or spin -- the mechanism itself makes ANY progress unprofitable below the duty floor (not just an already-converged policy's local optimum), which would mean the duty-gate design needs an explicit anti-freeze complement (e.g. pair with reward.k_walk_idle_charge, an existing already-implemented idle-charge lever) before further spend, per CURRENT_TRUTHS' own note that soft anti-park prices alone leave the degenerate stance as PPO's cheapest optimum unless paired with an idle charge.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M canary: env/walk_duty_gate_factor not saturated near 1.0 while duty is measurably low; walk_speed / net episode displacement clearly nonzero and not decaying to a frozen stance by the final quarter; reward not pinned flat at a near-zero constant. PASS reopens walk_duty_gate as viable and licenses a dose-ramp acquisition design; FAIL (freeze/spin/park matching the warm-started dg1 cohort) means the mechanism needs the anti-idle-charge complement before any further spend.

