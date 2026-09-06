# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-zerobias1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T05:49:21+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-tiltnoise1x-c1

**wandb_id**: looeatv7

**hypothesis**: Restore nominal (1x) per-joint zero-point/calibration bias (joint_zero_bias_deg=1.0deg, a persistent per-joint set_zero offset -- the single most hardware-realistic axis this DR-restoration sweep had not yet touched: every physical servo has SOME zero-point calibration error, unlike the transient noise/latency axes already tested). Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive a persistent 1deg/joint offset without retraining collapse? Isolated single-axis diagnostic, same template as the sibling deadband/latency/tiltnoise/encnoise DR-restoration arms.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait does not depend on perfectly zeroed joints. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows joint-bias realism is a binding constraint the DR-rung must budget real training time against.

**verdict**: CANARY PASS/INFORMATIVE-POSITIVE (nominal joint-zero-bias DR-restore axis is free). Restoring nominal (1x, joint_zero_bias_deg=1.0 -- a persistent per-joint set_zero calibration offset every physical servo has some of) on the campaign's cleanest champion (medhead-abrupt-c1-acq1-cont40m, 80M, 24/24) gives a PERFECT 24/24 gait_valid, 0 falls, sac=[] every one of 24 episodes across all 4 panels. Video (walk_det_0..5) confirms clean upright six-leg cycling, level body, correct heading, no flag leg. slip/m 3.2-4.8 -- elevated vs the 2.9 teacher band but in the same range as every DR-restore sibling in this sweep. Joins latency/deadband/torquefade/noise/mass/friction/push/gyronoise/encnoise/contactstiff as a clean single-axis PASS -- the gait does not depend on perfectly zeroed joints. What's next: this axis's zero-drift-FRAME sibling (zerobiasframe1x-c1, harder coupling where the bias also corrupts the commanded frame, not just the sensor readback) is separately in flight; ACQ-scale durability of individual clean axes is the still-open follow-up question (friction1x-c1-acq1/mass1x-c1-acq1 already launched).

