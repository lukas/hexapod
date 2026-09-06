# cw-assistfade-rung2-harden-speedband-s1-lsd2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T15:49:31+00:00

**pod**: hexapod-mjx-train-7

**steps**: 8000000

**parent**: cw-assistfade-rung2-harden-speedband-s1-v2

**wandb_id**: 1rtyf5jc

**hypothesis**: Twin of s0-lsd2 (same one-cycle repair batch, 2nd seed). The speedband-s1-v2 FAIL-IGNORES-BAND (verdicted this cycle, speed pinned at EXACTLY 0.038 m/s every episode, reward declining) traced to zero exploration: the source gatefix checkpoint's log_std was already fully annealed to ~-3.0 before this continuation started, so its own --log-std-final -3.0/--log-std-anneal-frac 1.0 never moved anything for the whole 8M budget. Adding --warm-log-std-override=-2.0 (documented precedent for exactly this warm-start-doesn't-explore shape) forcibly resets log_std to -2.0 (std~0.135) at launch, then anneals back to -3.0 over the same 8M steps. If true: speed_mean_m_s should start covarying with cmd_dist_m instead of pinning to one value; reward quarters should stop declining. If false: escalate to an explicit speed-tracking reward term (schedule fix insufficient).

**gate**: PASS if the standard held-out det+sto gate (4 modes) clears gait_valid majority (>=5/6)/0 falls/progress_ratio>=0.35 every mode AND per-episode speed_mean_m_s visibly covaries with cmd_dist_m/10s across episodes. FAIL-COLLAPSE if gait_valid/falls regress vs the ignition checkpoint. FAIL-STILL-IGNORES if speed stays flat despite the exploration boost -- escalate to an explicit speed-tracking reward term next.

