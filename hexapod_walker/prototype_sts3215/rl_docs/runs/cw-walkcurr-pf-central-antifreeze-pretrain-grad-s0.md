# cw-walkcurr-pf-central-antifreeze-pretrain-grad-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-30T06:54:09+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkcurr-pf-central-antifreeze-pretrain-s0

**wandb_id**: mprcu661

**hypothesis**: Plain English: same graduated step-completion shaping test as the decleg twin, on the centralized architecture -- does k_step_partial=0.5 (2mm deadband, WALKCURR_SV_PRETRAIN_GRAD bank 5/5 green) dislodge the static-quiver basin the centralized arch also converged to under the pure-STEP pretrain (central-antifreeze-pretrain-s0 FAIL, identical value to its decleg twin -- arch was not the confound there, so this checks arch is not the confound here either).

**gate**: own-cfg 2M PRETRAIN health read (not a formal gate): env/reward_step_event or a new partial-credit signal measurably nonzero and rising, walk_speed/ep_len not an immediate flatline-to-static-stand vs the pure-STEP pretrain siblings.

