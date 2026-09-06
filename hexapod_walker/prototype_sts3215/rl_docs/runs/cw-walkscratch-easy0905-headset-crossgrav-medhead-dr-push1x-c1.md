# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-push1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T05:14:52+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**hypothesis**: Turn on the project's mid-walk external base-torque push perturbation, currently OFF (dr.walk_push_prob=0.0, i.e. zero push events in every episode all campaign despite the walkcurr goal ladder explicitly naming 'DR/push hardening' as the rung after direction changes). Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive a real chance (30%/episode, nominal dose 2.0-3.0 N*m peak base torque pulse over 0.8-1.5s) of a mid-walk shove without retraining collapse? Isolated single-axis diagnostic, same template as the sibling latency/deadband/torque/noise/mass/friction DR-restoration arms; the actual 'push' half of the ladder's named next rung.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait recovers from an occasional shove with zero retraining. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows push recovery needs its own real training-budget hardening rung, not a free zero-shot add.

**refused_reason**: hexapod-mjx-train-2 already runs cw-walkscratch-easy0905-headset-crossgrav-s1acq-widenfwd-c1-acq1 — GPU pods host exactly one run; pick a free GPU pod.

