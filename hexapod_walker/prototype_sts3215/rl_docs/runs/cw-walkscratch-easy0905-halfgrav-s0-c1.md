# cw-walkscratch-easy0905-halfgrav-s0-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-05T09:19:01+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-halfgrav-s0

**wandb_id**: wkxt570w

**hypothesis**: Plain English: the half-gravity canary was healthy; acquisition budget from its own checkpoint tests whether stepping emerges earlier at half weight. Own-checkpoint 40M continuation of halfgrav-s0 (ease.gravity_scale=0.5 retained), --activation-fn stripped per plain --init-from restriction. Evaluated at ITS OWN 0.5g; full-gravity is a later diagnostic only.

**gate**: Acquisition milestone at own easy physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, all six legs repeatedly lift/place on video, no belly drag; report sto. Not met with v_along/reward still rising = continue/realign per 08-21 ruling, not auto-FAIL; genuine FAIL only if v_along_cmd and reward_walk are flat at this budget or park recapture.

**verdict**: ACQ PASS (own-checkpoint 40M continuation of halfgrav-s0, 0.5g). Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_halfgrav_s0_c1_gate/report.json — 0/24 falls across all 4 scenarios, fwd_dist_m median 2.47-3.46m/20s (0.12-0.17 m/s net, >>0.03 bar), gait_valid 6/6 in walk/sto + walk_startjitter/sto, 4/6 in walk_startjitter/det. Video (walk_det_0.png, walk_sto_0.png) shows real forward translation, checkerboard-shift confirmed, level six-leg cycling. Why: 0.5g family continues to clear the easy0905 acquisition bar (matches halfgrav-s3's own PASS fingerprint, RL_LOG 09-05 10:36). Caveat: walk/det (the pure zero-jitter deterministic mode only) shows a repeatable weak/underused leg-1 (duty_cycle 0.09 vs 0.32-0.39 siblings, sacrificed_legs=[1] every episode since det trials are identical) while the SAME leg is fully used once stochastic noise or start-jitter is added (sto/startjitter duty ~0.2+, gait_valid true) — a half-gravity gait-quality flag worth tracking across the halfgrav cell (not gate-blocking: falls=0, fwd overshoots the bar, only 1 of 4 scenario blocks affected). Next: halfgrav family now has 2 independent PASSes (s0-c1, s3); no further budget needed on this specific checkpoint. If a later halfgrav arm needs deeper gait-quality diagnosis, start with this leg-1-underuse-in-pure-det fingerprint.

