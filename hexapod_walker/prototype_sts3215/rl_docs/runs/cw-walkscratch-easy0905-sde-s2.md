# cw-walkscratch-easy0905-sde-s2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ CONTINUE

**created**: 2026-09-05T09:06:47+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s0

**wandb_id**: 4ijfyvi7

**hypothesis**: Plain English: independent seed 2 of the gSDE exploration family — the healthiest early-signal variant of the cohort (sde-s0 had best v_along at 2M) — at acquisition budget (mechanism evidence inherited from sde-s0's 2M CANARY PASS; operator 09-05: replicate healthy exploration variants). From-scratch 40M, identical to sde-s0 (--use-sde, resample 20 ticks; legal here because fresh build) except --seed 2. Question: is temporally-correlated gSDE exploration a robust advantage over per-tick Gaussian across seeds?

**gate**: Acquisition milestone at OWN physics (halfgrav arms at their own 0.5g): 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, all six legs repeatedly lift/place on video, no belly drag; report sto. Mechanism-health evidence inherited from the family's 2M CANARY PASS 09-05 — spot-check at ~2M in W&B, do not re-canary. Not met with v_along/reward still rising = continue/realign per 08-21 ruling; FAIL only on flat v_along+reward at this budget or park recapture.

**verdict**: Not yet walking at 40M but per 08-21 ruling this is continue, not fail. Video/report: lurch-and-faceplant, TERM tilt_pitch in 6/6 det episodes; walk/det shows gait_valid 6/6 but fwd only 0.08m (marching in place, not net progress) -- a paddle/quiver pattern, not a real gait; walk_startjitter/det is worse (gait_valid 0/6). But rollout/ep_len_mean is NOT flat: it troughed to ~45-65 ticks around 15-25M (the phase where a fast-then-fall strategy first out-earned surviving) then climbed to 214 ticks at the final logged step (102->109->116->169->194->214, still rising into the last point), and rollout/ep_rew_mean tracks it (-2.1->8.2->28.6->23.8->30.1->26.6 -- noisy near the top but an order of magnitude above the trough, not a plateau at the sdehalfgrav-s0 level of ~4-5). env/v_along_cmd_m_s plateaued around 0.15-0.17 mid-training and holds, i.e. speed skill retained while survival duration is still being learned. Different fingerprint from sdehalfgrav-s0's genuine flat-everything plateau -- continuing from checkpoint per the ruling.

