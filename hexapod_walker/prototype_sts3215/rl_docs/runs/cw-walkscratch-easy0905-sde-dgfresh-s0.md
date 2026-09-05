# cw-walkscratch-easy0905-sde-dgfresh-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-05T15:54:41+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**wandb_id**: 8h25tu4l

**hypothesis**: Plain English: the walk_duty_gate mechanism-health canary batch (sde-s2-dg1 etc) was warm-started full-strength (dose 1.0 instant) off an already-CONVERGED 40M LEGPARK-exploiter checkpoint and collapsed to a NEW degenerate (spin-in-place / high-current instability on bare sde, full freeze-in-a-stance on sdehalfgrav-remcost) rather than recovering genuine six-leg walking within the 2M retrain budget -- confounding two different questions: is walk_duty_gate itself a sound mechanism, vs can a mature exploiter policy relearn fast enough after an abrupt income-shock. This arm isolates the first question: train FROM SCRATCH (fresh init, no entrenched exploit to escape) with walk_duty_gate=1.0 active from step 0, identical to the sde-s0 base recipe otherwise (bare gravity, gSDE). If-true: a real six-leg gait emerges within 2M (or is clearly progressing, not frozen) -- mechanism is sound, warm-start shock was the confound, re-approach LEGPARK repair via a gradual dose ramp instead of instant full-strength. If-false: fresh init ALSO retreats to freeze/park or spin -- the mechanism itself makes ANY progress unprofitable below the duty floor (not just an already-converged policy's local optimum), which would mean the duty-gate design needs an explicit anti-freeze complement (e.g. pair with reward.k_walk_idle_charge, an existing already-implemented idle-charge lever) before further spend, per CURRENT_TRUTHS' own note that soft anti-park prices alone leave the degenerate stance as PPO's cheapest optimum unless paired with an idle charge.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M mechanism-health canary (not a walking gate): env/walk_duty_gate_factor not saturated near 1.0 while duty is measurably low (the closed walk_gait_gate failure signature); walk_speed / net episode displacement clearly nonzero and not decaying to a frozen stance by the final quarter; reward not pinned flat at a near-zero constant for the whole run. PASS (real, even partial, forward motion with the gate engaged) reopens walk_duty_gate as viable and licenses a dose-ramp acquisition design; FAIL (freeze/spin/park matching the warm-started dg1 cohort) means the mechanism needs the anti-idle-charge complement before any further spend.

**verdict**: CANARY FAIL - MECHANISM: same FULL FREEZE as sibling seed sde-dgfresh-s0b (this run is a real independent training run, W&B 8h25tu4l, produced by a name-collision that also queued s0b -- both trained separately, both landed the same fingerprint). Evidence: det walk fwd med 0.06m/20s, identical across all 6 episodes (static pose, no leg mid-swing), slip_per_m 107.7 (near-zero-displacement artifact), env/walk_duty_gate_factor never leaves the 0.9-1.0 band, ep_rew_mean quarters -248/-362/-518/-524 getting worse not rising. sto mode shows some real gSDE-noise-driven displacement (fwd up to 1.48m, 4/6 gait_valid) but det -- the harness's primary un-perturbed criterion -- is the reliable read and it is frozen. See sde-dgfresh-s0b's verdict for the full mechanism analysis (duty floor alone is trivially satisfied by 6-leg stasis, cheaper than any real gait); this run is corroborating evidence, not an independent hypothesis. Next: same as s0b -- pair walk_duty_gate with reward.k_walk_idle_charge before further spend.

