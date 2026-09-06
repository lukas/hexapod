# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-tiltnoise1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T04:56:07+00:00

**pod**: hexapod-mjx-train-7

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-deadband1x-c1

**wandb_id**: w0kk6df2

**hypothesis**: Restore nominal (1x) IMU tilt-sensor noise -- the easy0905 recipe has run with tilt_noise_deg=0 (zero sensor noise on the roll/pitch reading) throughout the whole crossgrav campaign. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal (domain_rand.py default 0.3deg) tilt-sensing noise without retraining collapse? Isolated single-axis diagnostic, same template as the sibling deadband/latency/encoder-noise DR-restoration arms.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait does not depend on the zero-tilt-noise idealization. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows tilt-noise realism is a binding constraint the DR-rung must budget real training time against.

**verdict**: CANARY PASS -- the champion (medhead-abrupt-c1-acq1-cont40m, 80M steps) survives nominal (0.3deg) IMU tilt-sensor noise cleanly. Evidence: harness gait_valid 24/24 (all 4 modes 6/6), ZERO sacrificed legs in any of the 24 episodes (sac=[] everywhere), 0 falls/terminations anywhere; walk_det_0 frame strip shows a clean six-leg cycling gait, upright, level, no flag leg. slip/m med runs 3.4-4.9 (above the 2.9 teacher band, consistent with every other DR-restore canary in this campaign, not a regression -- the gate's own bar is gait_valid/no-new-chronic-leg/0-falls, not slip). This is now the 12th+ single-axis DR-restore canary and joins deadband1x/latency1x as a clean PASS -- tilt-noise realism is NOT a binding constraint on this champion. No repair/continuation needed; folds into the DR-rung's aggregate axis sweep (read alongside sibling encnoise1x/gyronoise1x/etc for the combined picture before any full-DR acquisition rung is funded).

