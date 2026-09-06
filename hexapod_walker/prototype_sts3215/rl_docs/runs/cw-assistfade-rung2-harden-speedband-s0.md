# cw-assistfade-rung2-harden-speedband-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T14:24:26+00:00

**pod**: hexapod-mjx-train-4

**steps**: 8000000

**parent**: cw-assistfade-rung2-anchorfade-s0-reseed8m-gatefix

**hypothesis**: Rung 2 (anchor-fade) is now a 2-seed-confirmed ignition PASS (both -reseed8m-gatefix seeds, RL_LOG 09-06 14:0x/14:12) at a single pinned 0.06 m/s command; per the curriculum doc's own hardening ladder (speed band -> fixed headings -> command changes/stops -> yaw -> DR/pushes) the next unproven dimension is a WIDER SPEED BAND, not a new mechanism. This continues task-only PPO (BC anchor coef dropped to 0/off -- it already fully annealed and its per-episode BC targets were recorded at the old single speed, so re-enabling it here would fight the new band) from the s0 gatefix 8M checkpoint, widening the per-episode command from a fixed 0.06 m/s point to a uniform 0.04-0.08 m/s band (still inside the previously-validated pinned-speed panel's tested range, not an extrapolation).

**gate**: PASS if the standard held-out det+sto gate (4 modes, each episode drawing its own per-episode speed from the widened band) clears: gait_valid majority (>=5/6) every mode, 0 falls/terminations, progress_ratio>=0.35 every mode, AND per-episode achieved speed_mean/cmd_dist_m tracks its own per-episode commanded speed (not clustered on the old 0.06 pace regardless of command -- read directly off report.json episode rows, cmd_dist_m/10s vs speed_mean_m_s). FAIL - COLLAPSE if gait_valid/falls regress from the ignition read at either band extreme (0.04 or 0.08) while the 0.06-ish middle still passes -> retreat to a narrower band. FAIL - IGNORES-BAND if achieved speed stays flat near 0.06 regardless of the per-episode commanded value -> the widened band alone isn't enough signal, needs an explicit speed-tracking reward term before retry. slip/current still recorded not gated (doc's own ignition-adjacent stage).

