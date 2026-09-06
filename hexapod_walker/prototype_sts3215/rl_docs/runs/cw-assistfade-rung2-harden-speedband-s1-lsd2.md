# cw-assistfade-rung2-harden-speedband-s1-lsd2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL - IGNORES-BAND

**created**: 2026-09-06T15:49:31+00:00

**pod**: hexapod-mjx-train-7

**steps**: 8000000

**parent**: cw-assistfade-rung2-harden-speedband-s1-v2

**wandb_id**: 1rtyf5jc

**hypothesis**: Twin of s0-lsd2 (same one-cycle repair batch, 2nd seed). The speedband-s1-v2 FAIL-IGNORES-BAND (verdicted this cycle, speed pinned at EXACTLY 0.038 m/s every episode, reward declining) traced to zero exploration: the source gatefix checkpoint's log_std was already fully annealed to ~-3.0 before this continuation started, so its own --log-std-final -3.0/--log-std-anneal-frac 1.0 never moved anything for the whole 8M budget. Adding --warm-log-std-override=-2.0 (documented precedent for exactly this warm-start-doesn't-explore shape) forcibly resets log_std to -2.0 (std~0.135) at launch, then anneals back to -3.0 over the same 8M steps. If true: speed_mean_m_s should start covarying with cmd_dist_m instead of pinning to one value; reward quarters should stop declining. If false: escalate to an explicit speed-tracking reward term (schedule fix insufficient).

**gate**: PASS if the standard held-out det+sto gate (4 modes) clears gait_valid majority (>=5/6)/0 falls/progress_ratio>=0.35 every mode AND per-episode speed_mean_m_s visibly covaries with cmd_dist_m/10s across episodes. FAIL-COLLAPSE if gait_valid/falls regress vs the ignition checkpoint. FAIL-STILL-IGNORES if speed stays flat despite the exploration boost -- escalate to an explicit speed-tracking reward term next.

**verdict**: Twin of s0-lsd2's verdict, same evidence base. log_std confirmed genuinely moved (-2.0 -> ~-2.98 by end); gait/falls/progress clean (gait_valid 6/6 all 4 modes, 0 falls, prog med 0.46-0.55 >= 0.35 bar). Achieved speed_mean_m_s clusters 0.036-0.043 m/s across the same 0.035-0.067 m/s commanded band -- FAIL-STILL-IGNORES, the run's own pre-registered branch. Reward quarters [231.6, 632.5, 857.6, 927.9] also decelerating but positive. Same root-cause work applies (see s0-lsd2 verdict for the full writeup): built+bank-tested reward.walk_kernel_sigma_v_m_s and empirically RULED OUT kernel width as the mechanism (standalone rollout probe: matched-vs-habitual-mismatch return gap flat ~20-24% at every sigma 0.01-0.05, narrower does not help) -- the existing walk_kernel_prog_gate/k_walk_prog terms already price command-tracking with a real, sizeable gap; PPO has not yet converted it into a stride-length change from this entrenched checkpoint. Also notes the AMP track's prior CLOSURE of walk_phase_speed_scale clock-only coupling (faster legs, same body speed, no command correlation, RL_LOG 08-23) as a reason not to blindly relaunch that lever here unpaired. Next: bigger exploration-magnitude escalation (repair pair launched this cycle), not a new reward mechanism.

