# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-gyronoise1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T04:57:26+00:00

**pod**: hexapod-mjx-train-9

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-deadband1x-c1

**wandb_id**: oey1wf38

**hypothesis**: Restore nominal (1x) IMU gyro noise -- the easy0905 recipe has run with gyro_noise_deg_s=0 (zero sensor noise on the angular-rate reading) throughout the whole crossgrav campaign. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal (domain_rand.py default 0.5deg/s) gyro-sensing noise without retraining collapse? Isolated single-axis diagnostic, same template as the sibling deadband/latency/encoder-noise/tilt-noise DR-restoration arms.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait does not depend on the zero-gyro-noise idealization. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows gyro-noise realism is a binding constraint the DR-rung must budget real training time against.

**verdict**: CANARY PASS, another PERFECT axis restore. Restoring nominal (1x) IMU gyro-noise (dr.gyro_noise_deg_s, previously pinned at 0 the whole campaign) on the campaign's cleanest champion (medhead-abrupt-c1-acq1-cont40m, 80M, 24/24) costs NOTHING at 2M: aggregate gait_valid 24/24 across all 4 harness modes (walk/det 6/6, walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6), sac=[] every episode, 0 falls, 0 terminations, reward rising every quarter (70/147/243/338). slip_per_m banded 3.4-4.6, above the 2.9 teacher band but consistent with every sibling DR-restore canary (gate is gait-validity not slip-band). Joins deadband1x/latency1x/noise1x/tiltnoise1x/torquefade2x as a clean single-axis DR PASS -- gyro-noise realism is not a binding constraint on this champion. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_gyronoise1x_c1_gate/report.json, W&B oey1wf38.

