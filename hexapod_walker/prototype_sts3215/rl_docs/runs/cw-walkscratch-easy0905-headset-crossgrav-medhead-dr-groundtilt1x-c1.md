# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-groundtilt1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T06:17:48+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**hypothesis**: Restore nominal (1x) GROUND-SLOPE spread (ground_tilt_deg: floor pitch/roll applied via a tilted gravity vector, simulating concrete/mat/carpet not being perfectly level) -- the easy0905 recipe has trained on a perfectly level floor every episode. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal own-DR floor-slope spread (+-2deg) without retraining collapse? Isolated single-axis diagnostic, same template as the sibling latency/deadband/torque/noise/mass/friction/gain/geometry/zerobias/fault DR-restoration arms; re-launch of a spec lost twice to pod-race REFUSED in a prior cycle.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear).

**refused_reason**: a process for cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-groundtilt1x-c1 already exists on hexapod-mjx-train-0

