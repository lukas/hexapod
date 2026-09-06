# cw-walkscratch-easy0905-headset-halfgrav-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: HARDENING PASS

**created**: 2026-09-06T08:51:40+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-acq1

**wandb_id**: gd3g8ygn

**hypothesis**: Plain English: does the 0.5g family's own untouched root champion (headset-halfgrav-acq1, 40M, PERFECT 24/24 gait_valid, 0 falls) keep clean six-leg walking with double the training exposure (80M cumulative), the same cleanliness-margin-at-40M-predicts-cont40m-outcome question already confirmed on 3 other endurance-panel members (widen2c1-abrupt-c1-acq1-cont40m, medhead-irrfwd-c1-acq1-cont40m, ramp-irrfwd-c1-acq1-cont40m)? This is the halfgrav family's FIRST endurance data point.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24, ideally near its own 24/24 at 40M) at 80M cumulative, no NEW chronic single-leg sacrifice, 0 falls. FAIL/ENTRENCHES if it drops below half (<12/24), a chronic single-leg pattern emerges, or a fall appears.

**verdict**: HARDENING PASS (orphan reap: gate synced 10:37, unverdicted ~1.5h) -- the foundational plain halfgrav(0.5g) source holds PERFECTLY at 80M cumulative: 24/24 gait_valid (6/6 all 4 modes), 0 falls/terms, sac=[] every episode, per-leg duty min 0.13 / means 0.17-0.29 (no sub-threshold lazy leg), slip/m med 2.2-2.5 (inside teacher band <=2.9), fwd med ~3.1m, prog med ~2.3, reward monotonic per quarter 257->478->509->534, video-confirmed upright six-leg cycling. Reproduces its parent's own 24/24 at 40M exactly -- the cleanest cont40m hold in the endurance series (now 6 PASS / 2 FAIL) and the strongest single data point for the refined rule from the widen2-c3 FAIL adjudicated this same cycle: 40M cleanliness predicts endurance when the source carries NO prior fragility signal (this source had none; both FAILs had a WATCH or known attractor). Plain halfgrav-acq1@80M is now a top halfgrav champion candidate alongside the medhead/widenirr/irrwiden lines.

