# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade15x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T06:02:23+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade2x-c1

**wandb_id**: vw3jf1ci

**hypothesis**: Dose-response follow-up to torquefade2x-c1's PERFECT 24/24 PASS (dr.torque_scale 3->2 cost nothing): does fading the fixed torque/battery-assist crutch further, to 1.5x (half its original assist), still hold on the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M, 24/24 clean)? Finds where the champion's torque-assist margin actually starts to bind, rather than stopping at the first nominal-restoration dose.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) with no NEW chronic single-leg sacrifice and 0 falls. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- locates the torque-assist dose where hardening-rung training budget is actually needed.

**verdict**: Restoring the mid-point torque-assist dose (dr.torque_scale 3x idealized crutch -> 1.5x, halfway between the already-clean 1x full-removal and 2x points) costs NOTHING: harness shows a PERFECT 24/24 gait_valid, 0 falls, sac=[] on every single episode across walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto. slip/m 3.8-6.2 (within/near the ~2.9-ish teacher band tolerance already accepted for this campaign's siblings), forward progress 0.76-2.14m/20s in every episode. Video (walk_det_0 10-frame strip) shows clean six-leg tripod cycling, no drag/skate/paddle-creep, no flagged leg. This closes the torque-fade dose axis for good: 1x, 1.5x, 2x, and the idealized 3x default are ALL clean on this champion (medhead-abrupt-c1-acq1-cont40m) -- the robot never needed the assist crutch at any dose point tested. Why: torque-assist realism sits alongside every other guardrails-named DR axis (mass/geometry/friction/compliance/gravity/gains) plus every sensor/actuator/behavioral axis tried this campaign -- all clean single-axis restores on this champion, an unbroken streak. Next: no further torquefade dose points needed; remaining walkcurr budget should go to composition/endurance questions (cont40m reads, multi-axis compositions) rather than re-testing already-closed single axes.

