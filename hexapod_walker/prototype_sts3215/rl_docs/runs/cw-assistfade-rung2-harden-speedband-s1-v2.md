# cw-assistfade-rung2-harden-speedband-s1-v2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-06T14:32:39+00:00

**pod**: hexapod-mjx-train-7

**steps**: 8000000

**parent**: cw-assistfade-rung2-anchorfade-s1-reseed8m-gatefix

**wandb_id**: 227unt2g

**hypothesis**: Twin of -harden-speedband-s0-v2 (same one-cycle batch, 2nd seed). Widens the fixed 0.06 m/s pinned command to a uniform 0.04-0.08 m/s per-episode band, continuing task-only PPO (BC anchor EXPLICITLY off: coef=0, anneal_gate=0) from the s1 gatefix 8M checkpoint -- the first hardening dimension on the curriculum doc's own ladder. (v2: supersedes the same-named launch killed this cycle after respec silently carried over the source's un-zeroed anchor cfg.)

**gate**: PASS if the standard held-out det+sto gate (4 modes, per-episode speed drawn from the widened band) clears: gait_valid majority (>=5/6) every mode, 0 falls/terminations, progress_ratio>=0.35 every mode, AND per-episode achieved speed tracks its own per-episode commanded speed (cmd_dist_m/10s vs speed_mean_m_s, not clustered near the old 0.06 regardless of command). FAIL - COLLAPSE if gait_valid/falls regress from the ignition read at either band extreme while the middle still passes -> retreat to a narrower band. FAIL - IGNORES-BAND if achieved speed stays flat regardless of commanded value -> needs an explicit speed-tracking reward term before retry. slip/current recorded not gated.

**verdict**: FAIL - IGNORES-BAND, same fingerprint as the s0-v2 twin, more extreme. Widened 0.04-0.08 m/s band, BC anchor off, continuing from the s1 gatefix checkpoint: gait_valid 6/6 every mode, 0 falls/terminations all 24 episodes, but achieved speed_mean_m_s reads LITERALLY IDENTICAL (0.038 m/s) in every single walk/det episode regardless of cmd_dist_m/10s spanning 0.035-0.066 m/s -- the policy is not modulating speed to command at all. walk/sto also misses progress_ratio>=0.35 (med 0.30). Reward is DECLINING across the run's last 3 quarters (932.3->862.9->757.4), a genuine regression signal, not the 08-21 rising-reward-bad-eval pattern -- this run is a clean FAIL by that ruling too, not a continue candidate. Same root cause as s0-v2: the source gatefix checkpoint's log_std was already fully annealed (~-3.0/std 0.05) before this continuation started, and this run's own --log-std-final -3.0/--log-std-anneal-frac 1.0 therefore produced ZERO exploration boost for the whole 8M budget -- the progress reward already normalizes by s_ref so the incentive to match command exists, but the policy never explored away from its single habitual cadence. Next: relaunch with --warm-log-std-override=-2.0 (documented precedent for exactly this warm-start-doesn't-explore shape) annealing back to -3.0 over the same budget. hardware-ready: no. Evidence: logs/ckpt_eval/cw_assistfade_rung2_harden_speedband_s1_v2_gate/report.json, W&B 227unt2g.

