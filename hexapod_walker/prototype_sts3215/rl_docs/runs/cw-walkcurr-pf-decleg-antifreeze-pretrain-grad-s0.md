# cw-walkcurr-pf-decleg-antifreeze-pretrain-grad-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-30T06:52:01+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkcurr-pf-decleg-antifreeze-pretrain-s0

**wandb_id**: y7h2k7m9

**hypothesis**: Plain English: does giving partial credit for an incomplete (sub-10mm) forward-projecting leg swing let a fresh-random-init policy find real stepping, where the all-or-nothing k_step_event-only pretrain (decleg/central-antifreeze-pretrain-s0, both FAIL) could not? New reward.k_step_partial=0.5 (WALKCURR_SV_PRETRAIN_GRAD bank, 5/5 green) pays a linear taper from a 2mm deadband up to the existing 10mm k_step_event gate for any completed lift-swing-touchdown with positive along-command displacement -- fidget-resistant by the same air>=2-tick liftoff/landing construction as k_step_event (a stall/quiver twin whose feet land back near their liftoff point still earns ~nothing), and the deadband specifically holds the wrong-direction sideways/reverse twins to the same <5 margin every other wrong-direction probe in this file uses (an undoped/no-deadband taper measured sideways at +9 over floor before the fix). Prediction-if-true: env/reward_step_event (or a new sub-threshold partial-credit signal) rises off ~0 well before 2M steps, walk_speed/ep_len show early motion rather than an immediate safe-stand convergence. Prediction-if-false: same static basin as the pure-STEP pretrain -- exploration-bootstrap is not the blocker after all, closes pretrain-staging.

**gate**: own-cfg 2M PRETRAIN health read (not a formal gate): env/reward_step_event or a new partial-credit signal measurably nonzero and rising, walk_speed/ep_len not an immediate flatline-to-static-stand vs the pure-STEP pretrain siblings.

