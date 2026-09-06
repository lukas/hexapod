# cw-assistfade-rung2-anchorfade-s1-ignitewiden

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T17:08:01+00:00

**pod**: hexapod-mjx-train-7

**steps**: 8000000

**parent**: cw-assistfade-rung2-anchorfade-s1-reseed8m-gatefix

**wandb_id**: sk43wm2m

**hypothesis**: Twin of s0-ignitewiden (same one-cycle batch, seed 1): does the speed-band-ignoring pathology trace to single-fixed-speed habituation baked in during ignition itself, not insufficient hardening-stage exploration (exploration magnitude closed 3/3 this cycle)? Same single lever: widen goal.walk_speed_min_m_s/max_m_s to 0.04-0.08 m/s from step 0 of the full anchor-fade ignition anneal (unchanged reward stack, unchanged original 2M seed checkpoint via the untouched --init-from), vs the pinned-0.06 reseed8m-gatefix ignition this seed already passed cleanly.

**gate**: Same as s0-ignitewiden: PASS needs both the standard ignition bar (anneal latches, gait_valid/falls/progress_ratio clean) AND achieved speed covarying with the per-episode commanded value across the widened band. FAIL-NO-IGNITION if the widened band itself blocks ignition; FAIL-STILL-IGNORES if ignition passes but speed still clusters flat -- closes ignition-habituation too, escalate to an explicit speed-tracking/stride-amplitude reward mechanism next.

