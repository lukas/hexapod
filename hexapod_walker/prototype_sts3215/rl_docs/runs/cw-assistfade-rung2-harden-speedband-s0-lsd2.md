# cw-assistfade-rung2-harden-speedband-s0-lsd2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T15:46:06+00:00

**pod**: hexapod-mjx-train-4

**steps**: 8000000

**parent**: cw-assistfade-rung2-harden-speedband-s0-v2

**wandb_id**: 0yvoegf9

**hypothesis**: The speedband-s0-v2 FAIL-IGNORES-BAND (verdicted this cycle) traced to zero exploration: the source gatefix checkpoint's log_std was already fully annealed to ~-3.0 before this continuation started, so its own --log-std-final -3.0/--log-std-anneal-frac 1.0 never moved anything for the whole 8M budget. Adding --warm-log-std-override=-2.0 (documented precedent, ~200 prior uses for exactly this warm-start-doesn't-explore shape) forcibly resets log_std to -2.0 (std~0.135) at launch, then anneals back down to the same -3.0 target over the same 8M steps -- real exploration early, converged/deterministic by the end. If true: achieved speed_mean_m_s should start varying with cmd_dist_m (not clustering within 0.002 m/s regardless of a 2x commanded range) while gait_valid/falls stay clean. If false (still flat regardless of override): the progress reward's own s_ref-normalization is not a strong enough gradient at these speed magnitudes and needs an explicit added speed-tracking term instead (a new mechanism, not a schedule fix).

**gate**: PASS if the standard held-out det+sto gate (4 modes) clears gait_valid majority (>=5/6)/0 falls/progress_ratio>=0.35 every mode AND per-episode speed_mean_m_s visibly covaries with cmd_dist_m/10s across episodes (not clustered within ~0.005 m/s regardless of a >=0.02 m/s commanded spread). FAIL-COLLAPSE if gait_valid/falls regress vs the ignition checkpoint. FAIL-STILL-IGNORES if speed stays flat despite the exploration boost -- escalate to an explicit speed-tracking reward term next.

