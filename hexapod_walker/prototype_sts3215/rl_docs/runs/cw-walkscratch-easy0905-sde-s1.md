# cw-walkscratch-easy0905-sde-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ CONTINUE

**created**: 2026-09-05T09:08:03+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s0

**wandb_id**: ne2pwden

**hypothesis**: Plain English: independent seed 1 of the gSDE exploration family — the healthiest early-signal variant of the cohort (sde-s0 had best v_along at 2M) — at acquisition budget (mechanism evidence inherited from sde-s0's 2M CANARY PASS; operator 09-05: replicate healthy exploration variants). From-scratch 40M, identical to sde-s0 (--use-sde, resample 20 ticks; legal here because fresh build) except --seed 1. Question: is temporally-correlated gSDE exploration a robust advantage over per-tick Gaussian across seeds?

**gate**: Acquisition milestone at OWN physics (halfgrav arms at their own 0.5g): 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, all six legs repeatedly lift/place on video, no belly drag; report sto. Mechanism-health evidence inherited from the family's 2M CANARY PASS 09-05 — spot-check at ~2M in W&B, do not re-canary. Not met with v_along/reward still rising = continue/realign per 08-21 ruling; FAIL only on flat v_along+reward at this budget or park recapture.

**verdict**: Not yet walking at 40M but per 08-21 ruling this is continue, not fail -- unlike sdehalfgrav-s0's flat-ep_len fingerprint. Video/report: lurch-and-faceplant on legs 1+2 area, gait_valid 0/6 in walk/det, TERM tilt_pitch in 6/6 det episodes, fwd 0.62m det (bar: 20s sustained fixed-forward). But rollout/ep_len_mean is NOT flat -- it fell to a trough (~50-60 ticks around 15-25M, the phase where the forward-speed reward was first discovered and paid for a fast-then-fall strategy) then climbed steadily through the rest of training to 231 ticks at the very last logged step (111->124->152->169->177->231 over the last ~15% of budget), and rollout/ep_rew_mean is still rising in lockstep (2.8->6.5->15.4->25.9->23.4->38.7, highest value at the final step, no plateau). env/v_along_cmd_m_s did plateau around 0.15-0.17 mid-training and holds there (not decaying), i.e. it kept the forward-speed skill while learning to survive longer with it -- the opposite of sdehalfgrav-s0's genuine flat-everything plateau. Continuing from checkpoint per the ruling.

