# cw-walkscratch-easy0905-sdehalfgrav-remcost-s1-dgatefix

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T16:09:12+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-sdehalfgrav-remcost-s1

**wandb_id**: m9sj7qzp

**hypothesis**: Plain English: remcost-s1's own 40M sdehalfgrav-remcost checkpoint learned LEGPARK-SKATE under the remcost term-cost recipe (ACQ CONTINUE verdict, legs chronically parked). The mechanism-health batch's own remcost dg1 arms were actually FRESH-FROM-SCRATCH (respec provenance bug, no --init-from at all) and went to full-freeze -- informative but not a test of curing THIS entrenched checkpoint. This arm hand-builds the vector so --init-from points at the checkpoint's own real output, the actual entrenched-checkpoint question for the remcost recipe.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY (2M): watch env/walk_duty_gate_factor climb toward 1.0 (not saturate at ceiling despite harness-flagged sacrifice) alongside ep_rew_mean/env/walk_speed not collapsing to termination-dominated. PASS (funds 40M acquisition): harness walk/det gait_valid >=4/6 with duty_cycle>=0.10 on every leg. FAIL: factor saturates while a leg stays <0.10 duty, full-freeze (near-zero net displacement) substitutes for the sacrifice, or reward/speed collapses.

