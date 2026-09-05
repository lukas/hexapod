# cw-walkscratch-easy0905-sde-idleterm-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T12:36:51+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-sde-s0

**wandb_id**: o6ibb8md

**hypothesis**: Seed 1 of the idle-terminate anti-freeze probe (see sde-idleterm-s0's hypothesis for the full root-cause chain: sde-s0-c4/s1-c2/s2-c2's static-frozen absorbing-pose exploit, walkcurr's own WALKCURR_PF_IDLE_TERM bank-proven fix ported onto the EASY_BASE sde recipe fresh from scratch). Same cfg, seed 1, for an n=2 canary read before committing acquisition budget.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as sde-idleterm-s0: CANARY mechanism-health scope, read together for a 2-seed pass/fail on whether the idle-terminate+soft-price combo lets the sde family escape the frozen-pose basin at all within 2M steps.

