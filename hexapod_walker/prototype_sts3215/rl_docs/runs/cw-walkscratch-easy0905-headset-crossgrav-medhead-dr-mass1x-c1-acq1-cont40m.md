# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-mass1x-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ_PASS

**created**: 2026-09-06T09:03:11+00:00

**pod**: hexapod-mjx-train-5

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-mass1x-c1-acq1

**wandb_id**: 61qwjqbf

**hypothesis**: Plain English: does the mass-restore axis (dr.mass_scale 0.85-1.20, leg_mass_jitter_pct 0.10) hold up over a SECOND 40M block (80M cumulative), the same endurance question already asked of the crossgrav/halfgrav cont40m siblings? Source is clean at 40M (24/24 gait_valid, 0 falls, sac=[] every episode, monotonic reward).

**gate**: PASS/HOLDS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with slip_per_m staying near the source's own 3.6-4.7 band and no NEW chronic single-leg sacrifice. FAIL/ENTRENCHES if a chronic single-leg sacrifice newly emerges/spreads across multiple modes.

**verdict**: HARDENING PASS (HOLDS): mass1x DR axis holds at 80M cumulative steps (40M ACQ parent + 40M cont40m). gait_valid PERFECT 24/24 across all 4 panels (walk/det 6/6, walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6), 0 falls/terms, sac=[] every episode (no chronic single-leg sacrifice). slip/m stays near-band: det med 3.69, sto med 4.16, startjitter/det med 3.65, startjitter/sto med 4.70, vs source's own 3.6-4.7 band -- a couple of individual sto episodes run slightly hot (5.0-5.4) but no outlier and no gait-validity cost. Reward still rising through the cont40m window (quarters 582->1082->1185->1271). Confirms the mass-scale DR axis is durable at endurance scale, consistent with every other cont40m confirmation this campaign (friction1x, halfgrav-widenirr, etc). Per QUEUE AIM this closes the mass-axis cont40m confirmation slot; no further per-axis spend follows -- the frontier is composite realism / kick-dose / torque-crutch-removal, all already funded/in-flight on other pods this cycle.

