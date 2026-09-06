# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade15x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T05:57:34+00:00

**pod**: hexapod-mjx-train-11

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade2x-c1

**hypothesis**: Dose-response follow-up to torquefade2x-c1's PERFECT 24/24 PASS (dr.torque_scale 3->2 cost nothing): does fading the fixed torque/battery-assist crutch further, to 1.5x (half its original assist), still hold on the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M, 24/24 clean)? Finds where the champion's torque-assist margin actually starts to bind, rather than stopping at the first nominal-restoration dose.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) with no NEW chronic single-leg sacrifice and 0 falls. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- locates the torque-assist dose where hardening-rung training budget is actually needed.

**refused_reason**: hexapod-mjx-train-11 already runs cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-startpose1x-c1 — GPU pods host exactly one run; pick a free GPU pod.

