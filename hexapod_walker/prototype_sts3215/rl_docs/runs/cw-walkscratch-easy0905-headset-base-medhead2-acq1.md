# cw-walkscratch-easy0905-headset-base-medhead2-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T19:15:54+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-base-medhead2-c1

**wandb_id**: 47j1zemx

**hypothesis**: Second-seed medium-heading (5-way, 0/+-45/+-90deg) acquisition on the base(1g) family: headset-base-medhead2-c1's own 2M canary already CANARY PASSED (v_along clears noise floor, 18/24 harness gait_valid, no chronic single-leg sacrifice), warm-started from a DIFFERENT base champion (headset-base-acq1) than the first-seed acq1 continuation (which used medhead-c1, warm-started from s1c1-acq1). This gives it the full 40M budget to confirm the medium-heading rung acquires cleanly from a second independent seed, mirroring headset-base-medhead-acq1's template exactly.

**gate**: Acquisition milestone at own physics + medium heading set: 20s held-out episodes across all 5 headings (0,+-45,+-90deg), >=0.03 m/s median net forward along each commanded heading, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: continue/realign if still climbing at cutoff rather than reflex-stop. PASS (2nd seed) closes the medium-heading rung's acquisition-scale seed-robustness confirmation at n=2 and licenses re-attempting a wider set as the next widening rung; FAIL means the rung is champion-specific even at 40M budget and the acq1 (first-seed) result must be weighted more heavily before widening further.

