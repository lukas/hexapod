# cw-walkscratch-easy0905-sdehalfgrav-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ FAIL

**created**: 2026-09-05T09:27:35+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s0

**wandb_id**: i6po3x2j

**hypothesis**: Plain English: second seed of the sde+halfgrav factorial cell so the 2x2 grid (base/sde/halfgrav/sde+halfgrav) has n=2 per cell. From-scratch 40M, identical to sdehalfgrav-s0 except --seed 1. (First attempt FAILED pre-boot on train-1: CPU-only torch in that pod venv, repaired to 2.11.0+cu128 this cycle — infrastructure, not recipe.)

**gate**: Acquisition milestone at OWN physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Mechanism evidence inherited from the family 2M CANARY PASS; spot-check ~2M in W&B. Not met with signals rising = continue/realign per 08-21; FAIL only on flat v_along+reward at budget or park recapture.

**verdict**: Result: same fingerprint as sdehalfgrav-s0, second seed confirms it. Evidence: ep_len_mean rose 112->186 by 4M then COLLAPSED to a 65-84-tick plateau for the entire back half (20M:83.6, 30M:71.9, 36M:65.2, 40M:67.96) while ep_rew_mean crept from -222 to -5.6 (quarters -358,-142,-32,-5.8) and v_along_cmd rose 0.19 m/s -- textbook per-tick reward-per-burst hack, not survival learning. All 24 gate episodes (det/sto x walk/walk_startjitter) TERM tilt_pitch, gait_valid 0/24, 2 legs sacrificed every time ([0,5] pattern), fwd 0.13-0.29m vs the 20s-sustained bar; contact sheet shows the robot pitching/lurching forward onto its chin by mid-episode. Why: same freeprog-EMA-outearns-term_penalty exploit as s0 (08-21 ruling: reward-misaligned, not a dead lineage) -- now corroborated on a SECOND independent seed in the sde x halfgrav cell, which per the pre-registered STATUS text is the trigger to design a survival-duration pricing fix (raise term_penalty and/or a bounded reward.alive dose) before funding any more sde+halfgrav arms. What's next: reward.alive already exists as a knob in env.py (default 0.0) but was historically pulled to 0 because a flat alive bonus previously caused a 'freeze and collect' stand exploit on the tracking-kernel reward -- dosing it for the freeprog walk reward needs its own bank proof (test_task_semantics.py) before launch, flagging as a DIG-IN design item rather than hand-launching an unproven reward change. s2/s3 (still training) will add 2 more data points before the cell needs any code change.

