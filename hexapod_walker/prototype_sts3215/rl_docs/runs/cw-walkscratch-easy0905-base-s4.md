# cw-walkscratch-easy0905-base-s4

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-05T09:04:15+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-base-s0

**wandb_id**: mepfuf2d

**hypothesis**: Plain English: backlog spare — fifth independent base-family seed for seed-robustness statistics, queued so the mechanical drain refills the first freed slot (operator 09-05 backlog-stocking directive). From-scratch 40M, identical to base-s0 except --seed 4.

**gate**: Acquisition milestone at OWN physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Mechanism evidence inherited from the family's 2M CANARY PASS 09-05; spot-check ~2M in W&B. Not met with signals rising = continue/realign per 08-21; FAIL only on flat v_along+reward at budget or park recapture.

**verdict**: First clean ACQ PASS in the easy0905 family at full 40M budget. Gate (20s held-out fixed-forward, own easy physics): fwd_dist_m median 3.76-4.77m across all 4 scenarios (walk/sto x startjitter, i.e. 0.19-0.24 m/s net, >>0.03 m/s bar), 0/24 terminations (roll_class all leaning/recovered, never fell), min per-leg duty_cycle 0.11-0.48 across episodes (no sacrificed leg), height_err_end_mm 20-36 (no belly drag). Video (walk_det_0, contact_sheet + zoomed panels) confirms real forward translation (checkerboard shifts under a tracking camera) with all six legs cycling, wide splayed stance. Caveat: slip/prog ratio 2.6-3.1 (elevated, ~teacher-band ceiling ~2.9 used elsewhere in the codebase) and actual speed (0.15-0.34 m/s) runs 3-5x the 0.06 m/s reference the freeprog reward credits, i.e. some paddle/skate quality even though net progress and fall-avoidance are clean -- recorded, not gate-blocking since this gate is silent on slip. First 40M-scale walking PASS in the campaign (previously only sdehalfgrav-s0 ACQ FAIL and sde-s2 ACQ CONTINUE had reported).

