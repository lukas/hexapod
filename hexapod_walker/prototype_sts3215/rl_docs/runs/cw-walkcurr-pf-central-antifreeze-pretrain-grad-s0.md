# cw-walkcurr-pf-central-antifreeze-pretrain-grad-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-30T06:54:09+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkcurr-pf-central-antifreeze-pretrain-s0

**wandb_id**: mprcu661

**hypothesis**: Plain English: same graduated step-completion shaping test as the decleg twin, on the centralized architecture -- does k_step_partial=0.5 (2mm deadband, WALKCURR_SV_PRETRAIN_GRAD bank 5/5 green) dislodge the static-quiver basin the centralized arch also converged to under the pure-STEP pretrain (central-antifreeze-pretrain-s0 FAIL, identical value to its decleg twin -- arch was not the confound there, so this checks arch is not the confound here either).

**gate**: own-cfg 2M PRETRAIN health read (not a formal gate): env/reward_step_event or a new partial-credit signal measurably nonzero and rising, walk_speed/ep_len not an immediate flatline-to-static-stand vs the pure-STEP pretrain siblings.

**verdict**: FAIL (own-cfg 2M PRETRAIN health read) -- matched-architecture twin of cw-walkcurr-pf-decleg-antifreeze-pretrain-grad-s0 (same cycle, unclaimed by any concurrent cycle, read together since the pair's whole point is the arch-not-confound check). Numerically near-identical trajectory to the decleg twin at every logged step: ep_len_mean 165.87/258.93/350.82/444.67/547.29 (exact match to 2 decimals), env/walk_speed 0.0207->0.0203 (same static floor, cmd 0.05-0.06), env/reward_step_event flat/noisy 0.0026-0.0034 the whole run (already at this value at the first checkpoint, not a genuine rise), ep_rew_mean settles 202.9 (quarters [151.7,202.0,202.4,202.8]), terminations/truncated=153. Same safe-static-stand convergence as the decleg twin and as the prior pure-STEP pretrain pair -- confirms architecture is not the confound, again. Closes pretrain-staging 4/4 FAIL alongside the decleg twin; see that verdict for the full root-cause writeup and STATUS.md/OPERATOR_QUESTIONS.md for the pre-committed next step.

