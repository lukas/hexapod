# cw-walkscratch-easy0905-halfgrav-s2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-05T09:28:52+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-halfgrav-s0

**wandb_id**: eced4myi

**hypothesis**: Plain English: independent seed 2 of the half-gravity family, seed-MATCHED to base-s2 for the paired 1g-vs-0.5g comparison. From-scratch 40M, identical to halfgrav-s0 except --seed 2.

**gate**: Acquisition milestone at OWN physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Mechanism evidence inherited from the family 2M CANARY PASS; spot-check ~2M in W&B. Not met with signals rising = continue/realign per 08-21; FAIL only on flat v_along+reward at budget or park recapture.

**verdict**: CORRECTION to my own prior note (same cycle, no new eval): base-s2/base-s4/halfgrav-s3 ACQ PASSed in a concurrent cycle just before this one landed -- halfgrav-s2 is the 4th clean 40M ACQ PASS in the grid, not the first (base and halfgrav families both now have 2/2 seeds clean; sde is ACQ CONTINUE, sdehalfgrav-s0 ACQ FAIL with a remcost repair arm now training). Full evidence unchanged: logs/ckpt_eval/cw_walkscratch_easy0905_halfgrav_s2_gate/report.json, 24/24 episodes zero terminations across walk/walk_startjitter x det/sto, gait_valid 6/6 every episode, six legs each cycling (duty_cycle 0.13-0.33, swing_count 100+, none stuck), median net-forward 0.19-0.21 m/s (bar >=0.03), forward_dist_m med 3.3-3.6m/20s, height_err_end_mm 5.5-21.9mm (no belly drag), slip_per_m 1.7-2.3 (inside the 2.9 joystick-teacher band). Start-jitter panel survives with the same fingerprint (0/12 falls under perturbed init) -- real robustness margin. Soft note: roll_peak reaches 18-28deg under start-jitter+stochastic (once 27.9deg, near the 30deg trip bar) though nothing tripped; worth watching for a stability-focused continuation. Net effect: halfgrav (0.5g) now has 2/2 reporting seeds clean (s2, s3), matching base's 2/2 (s2, s4) -- both families look solid at 40M; sde/sdehalfgrav are the harder cells.

