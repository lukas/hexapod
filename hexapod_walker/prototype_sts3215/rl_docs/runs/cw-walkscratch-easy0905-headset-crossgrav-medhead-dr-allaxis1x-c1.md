# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T06:22:36+00:00

**pod**: hexapod-mjx-train-7

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**hypothesis**: This is the campaign's culmination arm: every individual DR axis (mass/geometry/friction/compliance/gains/latency/deadband/velcap/cmddrop/startpose/zerobias/encoder-noise/tilt-noise/gyro-noise/imu-bias/imu-mount-position/action-noise/ground-tilt/fault/ext-push/kick/push) has now scored at least one clean single-axis PASS in isolation on this same champion (medhead-abrupt-c1-acq1-cont40m, 80M, 24/24, 0 falls) -- but the campaign has ALSO found that pairwise compositions can regress sharply even when both ingredients are individually clean (irr+widen: two clean sources, composite FAILs at ACQ scale). Does the champion survive ALL nominal realism axes turned on AT ONCE, not just one at a time? dr.torque_scale is deliberately left at the campaign's fixed idealized crutch (3,3), unchanged from every sibling single-axis arm, since torque-crutch removal is its own separate active dose-response study (torquefade1x/15x) -- this arm isolates the ONE new variable of full-axis composition.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the champion's clean single-axis tolerance actually composes to full realism, not just to isolated axes. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls) -- shows realism axes interact/compound even when each is individually harmless, and the DR-rung must budget real acquisition-scale training against the FULL stack, not just per-axis canaries.

**refused_reason**: hexapod-mjx-train-7 already runs cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis1x-c1 — GPU pods host exactly one run; pick a free GPU pod.

