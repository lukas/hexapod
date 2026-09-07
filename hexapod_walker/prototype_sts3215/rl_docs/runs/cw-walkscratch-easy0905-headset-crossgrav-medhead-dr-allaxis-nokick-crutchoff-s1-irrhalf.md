# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-irrhalf

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T11:48:01+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-irr

**wandb_id**: 1v4ou8gd

**hypothesis**: Plain English: the full-DR crutch-off composite's irregular-timing rung fell (tilt_roll) at +-50% resample jitter on 2/2 seeds even though the SAME axis composed cleanly at 1g without full DR -- this tests whether HALVING the jitter amplitude to +-25% (instead of abandoning the axis) is small enough to avoid the jitter+push interaction. Same seed/checkpoint/recipe as the failed s1-irr canary, only goal.walk_cmd_resample_jitter changed 0.5->0.25. Prediction-if-true (composable at reduced dose): 0 falls/24, gait_valid majority (>=18/24), no new chronic sacrifice vs this seed's own clean acq1 baseline (21/24) -- would mean the axis is usable at a smaller dose, not fully closed. Prediction-if-false: the same tilt_roll fall or a new chronic sacrifice still appears -- would mean amplitude is not the driver (the push+jitter interaction itself is, at any irregularity) and the axis stays closed pending a different mitigation (e.g. suppressing pushes near a resample boundary).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS (reduced dose composable) if 0 falls/24 and gait_valid>=18/24 with no new chronic single-leg/pair sacrifice absent from this seed's own acq1 clean panel. FAIL (amplitude not the driver) if the same tilt_roll-style fall or a new chronic sacrifice reappears at half amplitude, matching the 0.5-jitter canary's own fingerprint.

