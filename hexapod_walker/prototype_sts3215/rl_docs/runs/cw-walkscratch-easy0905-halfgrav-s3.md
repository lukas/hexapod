# cw-walkscratch-easy0905-halfgrav-s3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-05T09:05:30+00:00

**pod**: hexapod-mjx-train-5

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-halfgrav-s0

**wandb_id**: sf4nnokt

**hypothesis**: Plain English: backlog spare — fourth half-gravity seed, MATCHED to base-s3 for the paired 1g-vs-0.5g comparison, queued for the mechanical drain (operator 09-05 backlog-stocking directive). From-scratch 40M, identical to halfgrav-s0 except --seed 3.

**gate**: Acquisition milestone at OWN physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Mechanism evidence inherited from the family's 2M CANARY PASS 09-05; spot-check ~2M in W&B. Not met with signals rising = continue/realign per 08-21; FAIL only on flat v_along+reward at budget or park recapture.

**verdict**: Third clean ACQ PASS in the easy0905 family at 40M (halfgrav cell, 0.5g, matches the base family's fingerprint). Gate (own 0.5g physics): fwd_dist_m median 2.18-3.44m across walk/sto x startjitter (0.11-0.17 m/s net, >>0.03 bar), 0/24 terminations (roll_class 'leaning' only, never fell), min per-leg duty_cycle 0.09-0.13 (no sacrificed leg). Video/contact-sheet confirms real forward translation, all six legs cycling. Slip/prog 1.9-3.2 (comparable to or better than the base family's 2.6-3.4). Own-DR/owncfg supplementary pass had not started on-pod as of this read (pod contended with a concurrent standwalk mixedsession eval) -- informational only per protocol, not blocking since this gate's own cfg-set already zeroes DR (dr.latency/deadband/tilt/gyro=0); did not wait on it. Base and halfgrav families now both confirmed able to clear the acquisition bar from scratch; sde/sdehalfgrav read mixed (sde-s2 CONTINUE, sdehalfgrav-s0 FAIL).

