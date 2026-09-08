# cw-assistfade-rung3-legdutyratio-swingfloor-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T12:25:54+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-assistfade-rung3-legdutyratio-s1

**wandb_id**: e02k5rqc

**hypothesis**: Seed-1 replicate of the swingfloor-s0 canary launched this cycle: does pairing the assistfade rung3 duty-ratio charge with the walkcurr-proven swing-count floor fix the bare charge's inability to target a fully-planted no-swing leg? Single lever vs the matched bare-charge cw-assistfade-rung3-legdutyratio-s1 sibling (CANARY FAIL - MECHANISM, leg [0,5] sacrificed): only reward.walk_leg_duty_ratio_swing_min_count=2.0 / _swing_window_s=4.0 added, otherwise byte-identical. Batched with -swingfloor-s0 for an n=2 read per the operator's batch-launch guidance rather than serializing one seed per cycle.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as -swingfloor-s0's own gate, matched to this seed's own bare-charge sibling report.json: telemetry activation check, zero new falls vs the s1 bare-charge sibling, and per-leg duty narrowing for legs [0,5] without new slip/current regression to CONTINUE; statistically-indistinguishable duty or any new regression is FAIL-MECHANISM.

