# cw-walkscratch-easy0905-sdehalfgrav-s2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ FAIL

**created**: 2026-09-05T10:02:39+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s0

**wandb_id**: 70t2xsk0

**hypothesis**: Plain English: seed 2 of the sde+halfgrav factorial cell, seed-MATCHED to base-s2/sde-s2/halfgrav-s2 so the 2x2 family grid has paired draws at seed 2. From-scratch 40M, identical to sdehalfgrav-s1 except --seed 2.

**gate**: Acquisition milestone at OWN physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Mechanism evidence inherited from the family 2M CANARY PASS; spot-check ~2M in W&B. Not met with signals rising = continue/realign per 08-21; FAIL only on flat v_along+reward at budget or park recapture.

**verdict**: 4th sde+halfgrav seed, same flat-ep_len fingerprint as s0/s1/s3 (found unverdicted this cycle -- run had finished quietly). Gate: 0/24 gait_valid across all 4 scenarios, every episode TERM tilt_pitch, 2-4 legs sacrificed per episode, fwd only 0.11-0.43m (bar: 20s sustained). Video: fast lurch-collapse onto the belly within ~1-2s, one leg splayed out, not sustained walking. rollout/ep_len_mean rose 114->239 by 8M then COLLAPSED and stayed flat the entire back half (21M:83, 24M:79, 27M:73, 29M:69, 32M:68, 35M:64, 37M:68, 40M:70) while rollout/ep_rew_mean crept -450->+4.7 (per-tick reward-per-burst hack, not survival learning) and env/v_along_cmd_m_s rose to +0.19 m/s -- textbook match to sdehalfgrav-s0/s1's already-diagnosed fingerprint (freeprog EMA reward pays more per tick than the flat -24 term_penalty costs a burst-then-fall). 4/4 sde+halfgrav original-recipe seeds now share this exact fingerprint, fully confirming the reward-misalignment diagnosis; the fix (reward.term_cost_per_remaining_s=100 + term_cost_max=450) is already bank-proven and running as remcost-s0/s1. No further original-recipe sde+halfgrav seeds needed -- the cell's fate rides entirely on remcost-s0/s1 now.

