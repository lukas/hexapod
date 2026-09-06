# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-zerobiasframe1x-c1-acq1-r2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T08:24:38+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-zerobiasframe1x-c1

**wandb_id**: 8dv3hru5

**hypothesis**: Plain English: does the harder frame-COUPLED zero-bias axis (bias applied through the command frame, not just sensor-side) stay a clean walk with a REAL 40M training budget, not just a 2M canary glance? Re-run of zerobiasframe1x-c1-acq1 (my own earlier launch this cycle window), which landed with an accidental 2M-step budget -- the same --steps-not-overridden respec bug already found on gains1x/geom1x/fault1x/extpush1x-c1-acq1 (a respec without --steps silently inherits the SOURCE canary's tiny step count). This -r2 explicitly pins --steps 40000000. zerobiasframe1x-c1's own 2M canary was CANARY PASS 23/24 (0 falls, 1 non-chronic leg-0 flag), matching its sensor-only zerobias1x sibling.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M, no NEW chronic single-leg sacrifice, 0 falls. FAIL/ENTRENCHES if it drops (<12/24), a new chronic leg, or a fall -- would show command-frame-coupled bias realism needs real training exposure before being called safe.

**verdict**: ACQ PASS (5th single-axis DR-restore ACQ confirmation; this -r2 is the corrected 40M re-run of a respec that silently inherited its source canary's 2M step count -- same --steps-not-overridden bug already found on gains1x/geom1x/fault1x/extpush1x). Gate: gait_valid 22/24 (6/6 det, 6/6 sto, 5/6 startjitter/det, 5/6 startjitter/sto), 0 falls/terms across all 24 episodes. Only 2 singleton non-chronic flags, DIFFERENT legs in DIFFERENT modes (startjitter/det ep1 leg[5]; startjitter/sto ep3 leg[0]), neither repeating -- matches the 2M canary's own PASS class (23/24, 1 non-chronic leg-0 flag), confirming the harder frame-coupled zero-bias axis (command-frame, not just sensor-side) is durable at real 40M ACQ scale, not just canary-clean. slip_per_m tight 3.24-5.20 across the whole panel, no outliers. 5th individual-axis DR-restore ACQ confirmation this campaign (after friction1x/mass1x/latency1x/zerobias1x-sensor-only). Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_zerobiasframe1x_c1_acq1_r2_gate/report.json (22/24, 0 terms), W&B 8dv3hru5.

