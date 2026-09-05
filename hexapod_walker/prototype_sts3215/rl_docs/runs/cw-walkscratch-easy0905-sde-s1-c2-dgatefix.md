# cw-walkscratch-easy0905-sde-s1-c2-dgatefix

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T15:57:12+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-sde-s1-c2

**wandb_id**: 8x8i8jt6

**hypothesis**: Plain English: sde-s1-c2 learned LEGPARK-SKATE (chronically parks 1-2 legs, rides income from the remaining legs' skate). The recency-based walk_gait_gate repair is closed 6/6 (gamed by rare token swings). The new walk_duty_gate mechanism (per-leg trailing-3s contact-DUTY income gate, un-dodgeable by a rare touch) already showed a real escape in walk/det when applied from an EARLY undifferentiated checkpoint (sde-s1-dg1, CANARY PASS) -- but that arm had a checkpoint-provenance bug and never actually continued c2's own entrenched-skate checkpoint. This arm fixes that: --init-from points at sde_s1_c2.zip itself (the real FAIL checkpoint), hand-built via backlog add to avoid the respec clone-without-init-from-source gotcha. Does the SAME mechanism bring an ALREADY-parked leg back down, not just prevent parking from never having started?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY (2M): watch env/walk_duty_gate_factor climb toward 1.0 (not saturate at ceiling despite harness-flagged sacrifice, the exact walk_gait_gate failure signature) alongside ep_rew_mean/env/walk_speed not collapsing to termination-dominated. PASS (funds 40M acquisition): harness walk/det gait_valid >=4/6 with duty_cycle>=0.10 on every leg in those episodes. FAIL: factor saturates while a leg stays <0.10 duty, or reward/speed collapses -- closes walk_duty_gate on the entrenched-checkpoint case specifically.

