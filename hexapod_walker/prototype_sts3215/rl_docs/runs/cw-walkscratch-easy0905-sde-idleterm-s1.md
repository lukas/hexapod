# cw-walkscratch-easy0905-sde-idleterm-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-05T12:36:51+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-sde-s0

**wandb_id**: o6ibb8md

**hypothesis**: Seed 1 of the idle-terminate anti-freeze probe (see sde-idleterm-s0's hypothesis for the full root-cause chain: sde-s0-c4/s1-c2/s2-c2's static-frozen absorbing-pose exploit, walkcurr's own WALKCURR_PF_IDLE_TERM bank-proven fix ported onto the EASY_BASE sde recipe fresh from scratch). Same cfg, seed 1, for an n=2 canary read before committing acquisition budget.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as sde-idleterm-s0: CANARY mechanism-health scope, read together for a 2-seed pass/fail on whether the idle-terminate+soft-price combo lets the sde family escape the frozen-pose basin at all within 2M steps.

**verdict**: CANARY FAIL - MECHANISM: same read as twin seed idleterm-s0 (see that verdict for the full evidence chain). ep_len_mean triples 118->314 over 2M; the walk_idle_terminate reason is present through 2,007,040 steps (all 4 rollouts 'TERM(walk_idle_terminate)') and only disappears at the very final logged checkpoint (2,097,152, 'walk:ok' x4) -- an even later and more fragile escape than s0. Downloaded+frame-stripped the final-checkpoint video (rollout_13 from W&B): identical static splayed-leg stance to s0 and to sde-s0-c4's disqualified frozen pose, on-screen speed 0.001-0.008 m/s (near-zero, no six-leg motion). Same conclusion: the idle-terminate detector got dodged via qvel/servo jitter, not genuinely escaped via walking. Do NOT fund a 40M continuation of this lever -- sde family's revival rides entirely on the walk_gait_gate repair (sde-s1-c3gg/sde-s2-c3gg, already funded and training).

