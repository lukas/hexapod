# cw-walkcurr-litrep-box-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-30T22:26:52+00:00

**pod**: hexapod-mjx-train-0

**steps**: 150000000

**parent**: cw-walkcurr-pf-central-sv-s0-rr2

**wandb_id**: 43d8ftmf

**hypothesis**: Plain English: seed replicate (seed 1) of cw-walkcurr-litrep-box-s0 -- the operator-authorized final literature-replication wave is pre-registered at 2 seeds, so the box/plain-reward/clamp recipe's outcome is judged on both seeds jointly, not one lucky/unlucky draw. Identical recipe: stance-centered action box yaw+-11/hip+-20/knee+-23 deg, WALKCURR_SV diet + k_action_delta=0.01, over-current clamped not terminated, 150M samples, 4096 envs, MLP 128/64/32 tanh. See s0's hypothesis for the full literature grounding (Rudin 2021; Walk in the Park 2022 tight-box ablation) and the bias-40 geometry note (operator commit 88d852c3 moved the hip mid-range).

**gate**: Rung-1 gate at 150M: C-env det fixed-forward panel (n>=6) -- zero tilt terminations, cmd_prog_frac >= 0.35, direction_err_deg <= 30, slip/m <= 3.0, gait_valid >= 4/6 with all six legs cycling, real stepping on video. Mid-run litmus: env/walk_speed must decisively clear the 0.02 m/s static floor and trend toward the 0.05-0.06 band with stable ep_len. NOTE: over-current termination is OFF by design (operator clamp ruling) -- terminations read tilt-only in training AND eval. PRE-COMMITTED (operator ruling d): if BOTH seeds land park-stand/no-gait with flat reward at 150M, RETIRE walkcurr as an honest DONE-negative scope finding (walkteach carries walking); if either seed shows a real gait_valid>0 escape, seed-replicate and re-price current realism next.

**verdict**: Park-stand/no-gait at 150M, second of two pre-committed final literature-wave seeds -- confirms s0's read, closes the wave 2/2. Own-cfg gate: det walk 0/6 gait_valid, sacrificed_legs=[0,3] on 5/6 episodes, progress_ratio med 0.02 (bar 0.35), direction_err large; sto walk gait_valid 6/6 but slip/m med 28.0 (in-place scuffing, not travel). env/walk_speed plateaued 0.012-0.014 m/s for the full 150M run, never cleared the 0.02 static-floor litmus; env/reward_walk flat ~0.06-0.07 after the first noisy step. Frame strip (walk_det_0.png): robot's pose is visually static across all 10 sampled frames -- textbook park-stand, zero net travel, same fingerprint as s0. This is the 08-21 ruling's genuine-FAIL case (reward plateaued AND task metric flat with a literature-scale 150M budget), not a misalignment/continue case. Per the operator's own pre-committed ruling (d) on this wave: BOTH seeds (s0, s1) now read park-stand/no-gait -> RETIRE walkcurr as an honest DONE-negative scope finding (walkteach/joystick-track BC-anchored lineages carry walking). Next: STATUS.md/tracks.json/walkcurr STATUS updated to RETIRED in this same cycle; no further litrep-box or rung-1 discovery arms.

