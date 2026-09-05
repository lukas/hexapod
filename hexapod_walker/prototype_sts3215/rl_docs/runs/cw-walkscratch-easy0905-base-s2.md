# cw-walkscratch-easy0905-base-s2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-05T09:01:25+00:00

**pod**: hexapod-mjx-train-11

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-base-s0

**wandb_id**: fo3air1p

**hypothesis**: Plain English: independent seed 2 of the validated easy-physics base family, launched straight at acquisition budget because the recipe's mechanism health is already proven by the base-s0/base-s1 2M CANARY PASSes (operator 09-05: identical-except-seed inherits mechanism evidence; do not re-pay 2M startup). From-scratch 40M, identical vector to base-s0 except --seed 2. Question: does teacher-free stepping on easy physics emerge robustly across seeds, and at what step count?

**gate**: Acquisition milestone at own easy physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, all six legs repeatedly lift/place on video, no belly drag; report sto. Mechanism-health evidence (finite losses, real actions, bank-consistent reward, motor contract 360 deg/s) is inherited from the family's 2M CANARY PASS 09-05 — spot-check it in W&B at ~2M but do not re-canary. Not met with v_along/reward still rising = continue/realign per 08-21 ruling; FAIL only on flat v_along+reward at this budget or park recapture.

**verdict**: Second clean ACQ PASS in the easy0905 family at 40M (matches base-s4's fingerprint, different seed). Gate: fwd_dist_m median 3.20-3.88m across walk/sto x startjitter (0.16-0.19 m/s net, >>0.03 bar), 0/24 terminations (roll_class leaning/recovered only, never fell), min per-leg duty_cycle 0.07-0.18 (no sacrificed leg), all four scenarios consistent. Video/contact-sheet confirms real forward translation with all six legs cycling. Same slip caveat as base-s4: slip/prog 2.9-3.4 (elevated, teacher-band-ish ~2.9 ceiling) at 3-4x the 0.06 m/s reference speed -- some paddle/skate quality, not gate-blocking (gate is silent on slip). Two-for-two base-family seeds now PASS at full budget; base-s0/s1's own -c1 continuations and base-s3 still pending.

