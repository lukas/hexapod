# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kickhalf1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T06:25:00+00:00

**pod**: hexapod-mjx-train-11

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kick1x-c1

**hypothesis**: Dose-bisection sibling of kick1x-c1 (which FAILED at nominal 0.3 prob/episode with 1 real fall): halve the per-episode kick probability to 0.15 (same 8-18deg peak roll, same 0.5-1.2s duration), same champion, same 2M canary scale. Plain: is the failure specific to the nominal 30% exposure rate, or does even a much rarer kick already break the champion? Prediction-if-true (0 falls at half dose): the campaign can deploy a lower-dose kick-tolerant variant immediately while the full-dose hardening continuation (kick1x-c1-acq1) trains separately. Prediction-if-false (still falls at half dose): the champion has no kick-recovery margin at all regardless of exposure rate, strengthening the case for a dedicated recovery mechanism over a pure dose/budget fix.

**gate**: PASS/INFORMATIVE-POSITIVE if the full 4-panel harness reaches 0 falls with aggregate gait_valid majority (>=18/24) and no new chronic single-leg sacrifice -- shows the nominal dose specifically (not the mechanism itself) is what broke kick1x-c1. FAIL/INFORMATIVE-NEGATIVE if a fall still appears at half dose -- shows the champion has no zero-shot kick-recovery margin at any meaningful exposure rate.

