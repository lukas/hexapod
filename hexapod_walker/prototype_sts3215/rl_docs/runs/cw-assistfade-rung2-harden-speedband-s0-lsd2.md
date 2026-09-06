# cw-assistfade-rung2-harden-speedband-s0-lsd2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL - IGNORES-BAND

**created**: 2026-09-06T15:46:06+00:00

**pod**: hexapod-mjx-train-4

**steps**: 8000000

**parent**: cw-assistfade-rung2-harden-speedband-s0-v2

**wandb_id**: 0yvoegf9

**hypothesis**: The speedband-s0-v2 FAIL-IGNORES-BAND (verdicted this cycle) traced to zero exploration: the source gatefix checkpoint's log_std was already fully annealed to ~-3.0 before this continuation started, so its own --log-std-final -3.0/--log-std-anneal-frac 1.0 never moved anything for the whole 8M budget. Adding --warm-log-std-override=-2.0 (documented precedent, ~200 prior uses for exactly this warm-start-doesn't-explore shape) forcibly resets log_std to -2.0 (std~0.135) at launch, then anneals back down to the same -3.0 target over the same 8M steps -- real exploration early, converged/deterministic by the end. If true: achieved speed_mean_m_s should start varying with cmd_dist_m (not clustering within 0.002 m/s regardless of a 2x commanded range) while gait_valid/falls stay clean. If false (still flat regardless of override): the progress reward's own s_ref-normalization is not a strong enough gradient at these speed magnitudes and needs an explicit added speed-tracking term instead (a new mechanism, not a schedule fix).

**gate**: PASS if the standard held-out det+sto gate (4 modes) clears gait_valid majority (>=5/6)/0 falls/progress_ratio>=0.35 every mode AND per-episode speed_mean_m_s visibly covaries with cmd_dist_m/10s across episodes (not clustered within ~0.005 m/s regardless of a >=0.02 m/s commanded spread). FAIL-COLLAPSE if gait_valid/falls regress vs the ignition checkpoint. FAIL-STILL-IGNORES if speed stays flat despite the exploration boost -- escalate to an explicit speed-tracking reward term next.

**verdict**: The --warm-log-std-override=-2.0 exploration-boost hypothesis is REFUTED: log_std genuinely moved this time (verified in wandb_history.csv: -2.0 at step 0 -> -2.98 by 7.8M, a real anneal, not the -v2 pair's zero-movement bug), gait/falls/progress stay clean (gait_valid 6/6 all 4 modes, 0 falls/terminations, prog med 0.49-0.61 >= 0.35 bar every mode), but achieved speed_mean_m_s STILL does not covary with cmd_dist_m/10s: clusters 0.037-0.048 m/s across a commanded 0.035-0.067 m/s band (2x spread) in every mode -- the exact FAIL-STILL-IGNORES branch this run's own gate pre-registered. Root-caused further this cycle (not the gate's own guessed fix): built reward.walk_kernel_sigma_v_m_s (new cfg, default-off, bit-exact, bank-tested 2 new tests) to test whether the Gaussian kernel's SIGMA_V=0.05 width (comparable to the whole hardened band) was flattening the gradient -- a standalone rollout probe (command-matched gait vs a scripted habitual-fixed-speed twin, the exact video-observed pathology) shows the matched-vs-mismatch return gap stays FLAT at ~20-24% across every sigma from 0.05 down to 0.01, narrower sigma does NOT widen it (slightly narrows it at the tightest width tried) -- this RULES OUT kernel-width as the mechanism. The existing walk_kernel_prog_gate/k_walk_prog terms already supply a real, sizeable (~20-24% return) incentive to track command speed; the reward is not silently flat, PPO simply has not converted an already-large real gradient into a stride-length change within this budget, starting from a checkpoint already entrenched by 10M+ prior steps of single-fixed-speed training. This also rules out relaunching the AMP track's already-CLOSED walk_phase_speed_scale clock-coupling lever here without pairing it with a stride-amplitude fix (that lever independently produced 'faster legs, same body speed, more slip' on a different lineage, RL_LOG 08-23). Reward quarters [282.1, 811.5, 1020.5, 1158.8] are decelerating, not flat -- an exploration-magnitude escalation (bigger override, not a reward-shape change) is the best-supported next single-axis test, launched this cycle as the repair pair.

