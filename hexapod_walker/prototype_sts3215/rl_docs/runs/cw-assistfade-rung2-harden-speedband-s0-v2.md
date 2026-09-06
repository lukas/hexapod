# cw-assistfade-rung2-harden-speedband-s0-v2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T14:31:24+00:00

**pod**: hexapod-mjx-train-4

**steps**: 8000000

**parent**: cw-assistfade-rung2-anchorfade-s0-reseed8m-gatefix

**wandb_id**: dydwknke

**hypothesis**: Rung 2 (anchor-fade) is now a 2-seed-confirmed ignition PASS (both -reseed8m-gatefix seeds, RL_LOG 09-06 14:0x/14:12) at a single pinned 0.06 m/s command; per the curriculum doc's own hardening ladder (speed band -> fixed headings -> command changes/stops -> yaw -> DR/pushes) the next unproven dimension is a WIDER SPEED BAND, not a new mechanism. Continues task-only PPO from the s0 gatefix 8M checkpoint with the BC anchor EXPLICITLY OFF (coef=0, anneal_gate=0 -- the anchor already fully annealed and its demonstrations were recorded at the old single speed, so re-enabling it here would re-run the anneal and confound the speed-band question), widening the per-episode command from a fixed 0.06 m/s point to a uniform 0.04-0.08 m/s band (still inside the previously-validated pinned-speed panel range, not an extrapolation). (v2: supersedes the same-named launch killed this cycle after respec silently carried over the source's un-zeroed anchor cfg.)

**gate**: PASS if the standard held-out det+sto gate (4 modes, each episode drawing its own per-episode speed from the widened band) clears: gait_valid majority (>=5/6) every mode, 0 falls/terminations, progress_ratio>=0.35 every mode, AND per-episode achieved speed tracks its own per-episode commanded speed (read off report.json episode rows: cmd_dist_m/10s vs speed_mean_m_s -- not clustered near the old 0.06 pace regardless of command). FAIL - COLLAPSE if gait_valid/falls regress from the ignition read at either band extreme (0.04 or 0.08) while the middle still passes -> retreat to a narrower band. FAIL - IGNORES-BAND if achieved speed stays flat near 0.06 regardless of the per-episode commanded value -> needs an explicit speed-tracking reward term before retry. slip/current recorded not gated (doc's own ignition-adjacent stage).

