# cw-assistfade-rung2-harden-speedband-s1-v2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T14:32:39+00:00

**pod**: hexapod-mjx-train-7

**steps**: 8000000

**parent**: cw-assistfade-rung2-anchorfade-s1-reseed8m-gatefix

**wandb_id**: 227unt2g

**hypothesis**: Twin of -harden-speedband-s0-v2 (same one-cycle batch, 2nd seed). Widens the fixed 0.06 m/s pinned command to a uniform 0.04-0.08 m/s per-episode band, continuing task-only PPO (BC anchor EXPLICITLY off: coef=0, anneal_gate=0) from the s1 gatefix 8M checkpoint -- the first hardening dimension on the curriculum doc's own ladder. (v2: supersedes the same-named launch killed this cycle after respec silently carried over the source's un-zeroed anchor cfg.)

**gate**: PASS if the standard held-out det+sto gate (4 modes, per-episode speed drawn from the widened band) clears: gait_valid majority (>=5/6) every mode, 0 falls/terminations, progress_ratio>=0.35 every mode, AND per-episode achieved speed tracks its own per-episode commanded speed (cmd_dist_m/10s vs speed_mean_m_s, not clustered near the old 0.06 regardless of command). FAIL - COLLAPSE if gait_valid/falls regress from the ignition read at either band extreme while the middle still passes -> retreat to a narrower band. FAIL - IGNORES-BAND if achieved speed stays flat regardless of commanded value -> needs an explicit speed-tracking reward term before retry. slip/current recorded not gated.

