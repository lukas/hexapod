# cw-walkscratch-easy0905-sde-s2-c2-dgatefix

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T16:06:39+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-sde-s2-c2

**wandb_id**: jw13d0rn

**hypothesis**: Plain English: sde-s2-c2 learned LEGPARK-SKATE (chronically parks a leg, rides income from the rest). walk_duty_gate already showed a real det-mode escape when applied from an early undifferentiated checkpoint (sde-s1-dg1, PASS) and its companion continuation off the SAME kind of early checkpoint spun/destabilized instead (sde-s2-dg1, FAIL) -- neither actually tested the entrenched-checkpoint case due to a respec provenance bug. This arm (n=2 alongside sde-s1-c2-dgatefix) fixes that: --init-from points at sde_s2_c2.zip itself, hand-built via backlog add. Does walk_duty_gate bring an ALREADY-parked leg back down on a second independent seed?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY (2M): watch env/walk_duty_gate_factor climb toward 1.0 (not saturate at ceiling despite harness-flagged sacrifice) alongside ep_rew_mean/env/walk_speed not collapsing to termination-dominated. PASS (funds 40M acquisition): harness walk/det gait_valid >=4/6 with duty_cycle>=0.10 on every leg. FAIL: factor saturates while a leg stays <0.10 duty, full-freeze (near-zero net displacement) substitutes for the sacrifice, or reward/speed collapses.

