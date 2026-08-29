# cw-walkcurr-sac-sv-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-29T17:33:51+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**wandb_id**: fvo19v4j

**hypothesis**: Plain English: can off-policy maximum-entropy SAC discover walking where 16 independently-designed on-policy PPO recipe classes all froze in a static stance? The 08-29 decleg-sv wave dig-in showed PPO converges to a stationary micro-quiver that harvests the freeprog income (~+0.4/tick while standing still) and drifts into servo over_current trips, with reward pinned at 167 - an exploration/optimizer failure mode SAC is specifically built against (Haarnoja 2018 walked the Minitaur from scratch; operator-named fallback ladder item (a), pre-registered in walkcurr STATUS Next). This arm: stock SB3 SAC (new --algo sac, snapshot 7964fe2e, smoke-verified end-to-end on train-4 incl. harness auto-load) on the IDENTICAL WALKCURR_SV diet/plant as the failed wave (mesh/100Hz, loaded servos, freeprog income + term_penalty 24, all else zeroed) - the only lever is the algorithm. n-envs 256 / batch 512 / grad-steps 32 / auto temperature. Prediction-if-true: entropy-regularized exploration visits progress-bearing states PPO never samples; env/walk_speed leaves its 0.02 m/s floor toward the 0.05-0.06 cmd band within 2M with ep_len NOT collapsing. Prediction-if-false: same static basin (walk_speed pinned, over_current climb) in both seeds - SAC-on-this-diet closed, escalate to fallback (b) Heess-style terrain diversity. Strongest alternative: SAC quivers HARDER (max-ent bonus rewards action noise) and trips over_current even faster - that outcome also closes the arm but indicts the diet/plant pairing, not exploration.

**gate**: Discovery gate at 2M (repaired litmus per the 08-29 sv-wave dig-in): PASS requires env/walk_speed rising off the ~0.02 m/s floor toward the commanded 0.05-0.06 band AND rollout/ep_len_mean stable-or-rising while it does. A freeprog escape or zero-crossing co-occurring with a terminations/over_current surge and falling ep_len is the KNOWN ARTIFACT and does not count. End eval: rung-1 C-env det fixed-forward panel (n>=6) read for real stepping on video; walk_speed off the floor + rising reward but gate unmet = continue per 08-21; walk_speed pinned at 2M = FAIL for this seed.

