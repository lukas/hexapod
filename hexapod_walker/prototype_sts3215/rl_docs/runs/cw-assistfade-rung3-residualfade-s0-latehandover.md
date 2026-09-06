# cw-assistfade-rung3-residualfade-s0-latehandover

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T19:34:18+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-assistfade-rung3-residualfade-s0

**hypothesis**: Rung 3's schedule-collision FAIL reproduced (worse) on the std-anneal-frac lever (cw-assistfade-rung3-residualfade-s1-stdslow: 24/24 held-out eval episodes over_current, prog med 0.03 vs bar 0.35 -- widening exploration noise did not help, ruling out std as the fix). Per this track's own pre-registered fallback ('a later/slower blend t1_steps or a longer total budget instead -- do not repeat the log-std-frac lever a second time'), and since canary phase is capped at 2,000,000 steps (no budget-extension lever available pre-graduation), this arm changes ONLY sched.t1_steps: 1,400,000 -> 1,700,000 (blend ramp uses 85% of the 2M budget instead of 70%, a gentler/later handover), leaving a shorter but real 300k-step settling window at full unassisted authority. log-std-anneal-frac reverted to the original 1.0 (the stdslow value is refuted, not carried forward, to keep this a clean single-variable test against the ORIGINAL parent, not a stacked change). Prediction-if-true: ignition gate (progress_ratio>=0.35, six-leg participation, zero over_current in walk_startjitter) clears where both prior schedules failed, because the policy has more gradual practice time to substitute its own output for the fading reference before being judged. Prediction-if-false: if this also fails the same way (over_current, progress<0.35), t1_steps/budget-shape levers are exhausted within the canary-phase cap and the next retreat must either graduate this lineage to acquisition phase (if any arm shows partial promise) or retreat one rung further (phase/contact-only per the doc, which needs its own reverse-curriculum design) rather than another schedule tweak.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Identical ignition text to every rung-3 canary: sustained forward translation the full episode, repeated alternating support transitions, all six legs participating (no permanently planted/unloaded leg), zero falls/safety terminations, progress_ratio>=0.35 on all modes (det+sto, walk + walk_startjitter, DR-0, held-out). MUST override goal.walk_residual_gate=0 (drop sched.*/walk_residual_* from the eval cfg-set) exactly like every prior rung-3 gate read. FAIL if progress stays <0.35, any leg is chronically parked/unloaded, or over_current terminations reappear in the startjitter panel -- check wandb_history.csv's env/sched_value vs reward_walk/height_err_mm/terminations trend across the anneal (same method as every prior rung-3 verdict) before concluding schedule-shape-vs-mechanism.

