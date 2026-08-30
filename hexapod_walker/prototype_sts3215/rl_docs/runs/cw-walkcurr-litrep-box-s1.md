# cw-walkcurr-litrep-box-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-30T22:26:52+00:00

**pod**: hexapod-mjx-train-0

**steps**: 150000000

**parent**: cw-walkcurr-pf-central-sv-s0-rr2

**wandb_id**: 43d8ftmf

**hypothesis**: Plain English: seed replicate (seed 1) of cw-walkcurr-litrep-box-s0 -- the operator-authorized final literature-replication wave is pre-registered at 2 seeds, so the box/plain-reward/clamp recipe's outcome is judged on both seeds jointly, not one lucky/unlucky draw. Identical recipe: stance-centered action box yaw+-11/hip+-20/knee+-23 deg, WALKCURR_SV diet + k_action_delta=0.01, over-current clamped not terminated, 150M samples, 4096 envs, MLP 128/64/32 tanh. See s0's hypothesis for the full literature grounding (Rudin 2021; Walk in the Park 2022 tight-box ablation) and the bias-40 geometry note (operator commit 88d852c3 moved the hip mid-range).

**gate**: Rung-1 gate at 150M: C-env det fixed-forward panel (n>=6) -- zero tilt terminations, cmd_prog_frac >= 0.35, direction_err_deg <= 30, slip/m <= 3.0, gait_valid >= 4/6 with all six legs cycling, real stepping on video. Mid-run litmus: env/walk_speed must decisively clear the 0.02 m/s static floor and trend toward the 0.05-0.06 band with stable ep_len. NOTE: over-current termination is OFF by design (operator clamp ruling) -- terminations read tilt-only in training AND eval. PRE-COMMITTED (operator ruling d): if BOTH seeds land park-stand/no-gait with flat reward at 150M, RETIRE walkcurr as an honest DONE-negative scope finding (walkteach carries walking); if either seed shows a real gait_valid>0 escape, seed-replicate and re-price current realism next.

