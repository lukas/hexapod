# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-alldrconf1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T06:27:38+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: 7enlogkd

**hypothesis**: Combine ALL 6 DR axes already individually CONFIRMED CLEAN-PASS on this exact champion (latency_scale 1x, deadband_scale 1x, torque_scale faded 3x->2x, encoder/tilt/gyro sensor noise at nominal 0.09deg/0.3deg/0.5deg/s, walk_push_prob 0.3 mid-episode push-recovery) into ONE run, instead of one-at-a-time isolation. Every individual axis costs nothing zero-shot; does the CONJUNCTION also cost nothing, or do independently-benign axes compound into a real degradation once several fire in the same episode (e.g. a push landing during a latency-delayed, noisy-sensor step)? This is the natural graduation test the DR-rung sweep has been building toward once its constituent single-axis reads came in clean.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls, slip/m not blown out far past the single-axis champion band (~3.4-5.6) -- shows these 6 already-cleared axes compose without an interaction penalty. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls) despite every constituent axis passing alone -- proves a genuine interaction effect the single-axis sweep cannot see, and the DR-rung needs a real (non-canary) combined-hardening training budget, not just axis-by-axis restoration.

**verdict**: CANARY PASS/INFORMATIVE-POSITIVE — the 6-axis composite (latency+deadband+torquefade+enc/tilt/gyro-noise+push, per its own hypothesis) composes without a collapse. Evidence: aggregate gait_valid 23/24 (walk/sto 5/6 with one non-chronic leg-5 flag, other 3 modes 6/6), 0 falls, slip/m med 5.42-6.06 -- noticeably higher than the single-axis band (3.4-5.6) but still within the gate's own explicit 'not blown out far past' bar, not a collapse. Why: these 6 already-cleared axes compound with a real but small slip-margin cost, not an interaction penalty that breaks gait_valid. Next: no ACQ queued this cycle; if a future wave wants combined-hardening training (not just canary composition), this is the candidate source.

