# cw-assistfade-rung2-harden-speedband-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: KILLED

**created**: 2026-09-06T14:26:36+00:00

**pod**: hexapod-mjx-train-7

**steps**: 8000000

**parent**: cw-assistfade-rung2-anchorfade-s1-reseed8m-gatefix

**wandb_id**: tepcz3z7

**hypothesis**: Twin of -harden-speedband-s0 (same one-cycle batch, 2nd seed of the 2-seed-confirmed rung-2 anchor-fade ignition PASS). Widens the fixed 0.06 m/s pinned command to a uniform 0.04-0.08 m/s per-episode band, continuing task-only PPO (BC anchor off) from the s1 gatefix 8M checkpoint -- the first hardening dimension on the curriculum doc's own ladder (speed band -> fixed headings -> command changes/stops -> yaw -> DR/pushes).

**gate**: PASS if the standard held-out det+sto gate (4 modes, per-episode speed drawn from the widened band) clears: gait_valid majority (>=5/6) every mode, 0 falls/terminations, progress_ratio>=0.35 every mode, AND per-episode achieved speed tracks its own per-episode commanded speed (cmd_dist_m/10s vs speed_mean_m_s, not clustered near the old 0.06 regardless of command). FAIL - COLLAPSE if gait_valid/falls regress from the ignition read at either band extreme while the middle still passes -> retreat to a narrower band. FAIL - IGNORES-BAND if achieved speed stays flat regardless of commanded value -> needs an explicit speed-tracking reward term before retry. slip/current recorded not gated.

**verdict**: Killed ~2min after launch: same anchor-not-zeroed mistake as the s0 twin (train.bc_anchor_coef=3.0/anneal_gate=1 carried over unchanged by respec). Relaunched immediately with anchor explicitly off.

