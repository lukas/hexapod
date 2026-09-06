# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T05:50:42+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade2x-c1

**hypothesis**: Dose-response follow-up to torquefade2x-c1's PERFECT 24/24 PASS: does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M, 24/24 clean) survive with the torque/battery-assist crutch removed ENTIRELY (dr.torque_scale 3->1, i.e. actuator forcerange back to the real unassisted servo spec) with zero retraining? This is the hardest single point on the torque-fade dose axis -- if it holds, the whole 3x assist crutch was unnecessary for THIS champion's margin; if it fails, it bounds exactly how much assist the gait actually depends on.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) with no NEW chronic single-leg sacrifice and 0 falls -- the champion does not need the torque-assist crutch at all. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- locates the torque-assist floor a real hardening-rung must respect.

