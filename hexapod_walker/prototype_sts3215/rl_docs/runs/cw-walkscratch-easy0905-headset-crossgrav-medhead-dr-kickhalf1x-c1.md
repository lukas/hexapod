# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kickhalf1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T06:25:00+00:00

**pod**: hexapod-mjx-train-11

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-kick1x-c1

**wandb_id**: nmionnio

**hypothesis**: Dose-bisection sibling of kick1x-c1 (which FAILED at nominal 0.3 prob/episode with 1 real fall): halve the per-episode kick probability to 0.15 (same 8-18deg peak roll, same 0.5-1.2s duration), same champion, same 2M canary scale. Plain: is the failure specific to the nominal 30% exposure rate, or does even a much rarer kick already break the champion? Prediction-if-true (0 falls at half dose): the campaign can deploy a lower-dose kick-tolerant variant immediately while the full-dose hardening continuation (kick1x-c1-acq1) trains separately. Prediction-if-false (still falls at half dose): the champion has no kick-recovery margin at all regardless of exposure rate, strengthening the case for a dedicated recovery mechanism over a pure dose/budget fix.

**gate**: PASS/INFORMATIVE-POSITIVE if the full 4-panel harness reaches 0 falls with aggregate gait_valid majority (>=18/24) and no new chronic single-leg sacrifice -- shows the nominal dose specifically (not the mechanism itself) is what broke kick1x-c1. FAIL/INFORMATIVE-NEGATIVE if a fall still appears at half dose -- shows the champion has no zero-shot kick-recovery margin at any meaningful exposure rate.

**verdict**: CANARY PASS/INFORMATIVE-POSITIVE — halved kick-perturbation dose (0.15 prob, vs kick1x-c1's full dose that caused 1 fall) shows the nominal dose specifically -- not the kick mechanism itself -- is what broke kick1x-c1. Evidence: 0 falls/terminations across all 24 episodes; aggregate gait_valid 21/24 (walk/det 5/6 sac=[2], walk/sto 6/6, walk_startjitter/det 5/6 sac=[4], walk_startjitter/sto 5/6 sac=[5]) -- three DIFFERENT legs flagged in three DIFFERENT modes, each a single non-repeating episode, not a chronic pattern. slip/m med 3.68-4.51 (sibling band). Why: this brackets the kick-recovery dose-response -- the champion has real zero-shot margin at half dose but none at full dose (kick1x-c1's 1 fall, tilt_roll, video-confirmed). Next: the dose threshold between kickhalf1x (safe) and kick1x (falls) is now the open question; kick1x-c1-acq1 (40M hardening continuation from the fall dose) is already in flight per the 08-21 ruling to answer whether more training closes the gap at full dose.

