# cw-walkcurr-pf-decleg-antifreeze-pretrain-grad-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-30T06:52:01+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkcurr-pf-decleg-antifreeze-pretrain-s0

**wandb_id**: y7h2k7m9

**hypothesis**: Plain English: does giving partial credit for an incomplete (sub-10mm) forward-projecting leg swing let a fresh-random-init policy find real stepping, where the all-or-nothing k_step_event-only pretrain (decleg/central-antifreeze-pretrain-s0, both FAIL) could not? New reward.k_step_partial=0.5 (WALKCURR_SV_PRETRAIN_GRAD bank, 5/5 green) pays a linear taper from a 2mm deadband up to the existing 10mm k_step_event gate for any completed lift-swing-touchdown with positive along-command displacement -- fidget-resistant by the same air>=2-tick liftoff/landing construction as k_step_event (a stall/quiver twin whose feet land back near their liftoff point still earns ~nothing), and the deadband specifically holds the wrong-direction sideways/reverse twins to the same <5 margin every other wrong-direction probe in this file uses (an undoped/no-deadband taper measured sideways at +9 over floor before the fix). Prediction-if-true: env/reward_step_event (or a new sub-threshold partial-credit signal) rises off ~0 well before 2M steps, walk_speed/ep_len show early motion rather than an immediate safe-stand convergence. Prediction-if-false: same static basin as the pure-STEP pretrain -- exploration-bootstrap is not the blocker after all, closes pretrain-staging.

**gate**: own-cfg 2M PRETRAIN health read (not a formal gate): env/reward_step_event or a new partial-credit signal measurably nonzero and rising, walk_speed/ep_len not an immediate flatline-to-static-stand vs the pure-STEP pretrain siblings.

**verdict**: FAIL (own-cfg 2M PRETRAIN health read) -- graduated k_step_partial=0.5 shaping does NOT rescue exploration. Evidence: env/reward_step_event trace [786k..2.36M] = [0.0026,0.0028,0.0033,0.0032,0.0027] -- already at this tiny value at the FIRST checkpoint and flat/noisy the whole run, never a genuine rising trend (prediction-if-true required a measurable rise off ~0; this is a flat floor, not a climb). env/walk_speed pinned 0.0206-0.0218 the entire run (cmd 0.05-0.06), identical static floor to every other FAIL in this campaign. rollout/ep_len_mean climbs 63->547 (matches the pure-STEP pretrain's identical 63->547) -- the policy learned to survive via a safe static stand, not real stepping; terminations/truncated=153 confirms. ep_rew_mean settles at 202.9 (quarters [151.7,202.0,202.4,202.8]), only +0.9 over the pure-STEP pretrain's 202.0 -- fully explained by the marginal nonzero step_event/partial values, not by any behavior change. Central twin (cw-walkcurr-pf-central-antifreeze-pretrain-grad-s0) is numerically near-identical at every logged step (ep_len_mean 165.87/258.93/350.82/444.67/547.29 matching to 2 decimals) -- architecture is not the confound, exactly reproducing the pure-STEP pretrain's own finding. Why: the graduated taper gives SOME gradient near a partial stride, but 2M steps of PPO from random init still never discovers a genuine forward-projecting swing to reinforce -- the taper widens the target, it doesn't create exploration pressure toward it. Prediction-if-false (same static basin as the pure-STEP pretrain) is CONFIRMED. What's next: this closes pretrain-staging altogether (both the pure k_step_event-only diet and this graduated taper, 4/4 arms FAIL) -- on top of the already-closed PPO population/budget sweep (6/6 FAIL), SAC-SV dose/settle-window branch (7/7 FAIL, though a fresh operator-ordered 20M-budget SAC tilt5 continuation x4 is still training), terrain fallback (2/2 FAIL), and idle-charge lever (2/2 FAIL). This means every operator-named (08-29 ruling) non-BC lever except the in-flight SAC tilt5 continuation is now closed; see STATUS.md Next and OPERATOR_QUESTIONS.md for the pre-committed fallback if that continuation also fails.

