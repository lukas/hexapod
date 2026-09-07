# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbis180

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ FAIL

**created**: 2026-09-07T10:40:47+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8

**wandb_id**: rx6wrkz3

**hypothesis**: Plain English: same bisection as arm 1 (widenbis135)/arm 2 (widenbism135), arm 3/3: add ONLY 180deg (straight-back) to the ACQ-passed 5-way base, same s0 checkpoint/seed/budget/recipe. Isolates whether the direct-reverse command alone drives the front-pair[0,5] chronic-sacrifice shortcut widen8-acq1 showed 3/3 (plausible: 180 is the heading where the front pair is most symmetric/least load-bearing for a straight-back gait). Prediction-if-true: chronic front-pair (or similar) sacrifice reappears by 40M. Prediction-if-false: panel stays clean near s0-acq1's 21/24 baseline -- 180deg alone is not sufficient, implicating the two diagonals or an interaction of >=2 headings.

**gate**: PASS (heading exonerated) if 0 falls/24 AND gait_valid>=19/24 AND no chronic single-leg/pair sacrifice absent from s0-acq1's own clean panel. FAIL (heading implicated) if a chronic front-pair[0,5]-style (or any new persistent single-leg) sacrifice reappears, matching widen8-acq1's fingerprint.

**verdict**: Adding ONLY 180deg (straight-back, one new heading) to the ACQ-passed 5-way base also breaks at full 40M ACQ depth -- a SECOND heading independently implicated. Evidence: 0 falls but gait_valid drops to 18/24 (vs this seed's own clean acq1 baseline 21/24) via a NEW chronic leg-0 sacrifice in walk/det (3/6: ep0,1,5 all sac[0] -- baseline was clean 6/6 here) plus the pre-existing walk_startjitter/sto flag holding at 3/6 (same count as baseline, different episode mix, now also touching leg[5] and leg[0] across 3 eps). Video (walk_det/0 contact sheet) shows the same fingerprint as the -135deg FAIL sibling: near-zero net translation across the frame, a persistently extended/unloaded leg visible across most frames, and the commanded-direction arrow swinging through multiple headings each step (spin-in-place, not directed walking) rather than the clean forward translation the +135deg PASS sibling shows. Why: this is the 3rd/3rd arm of the widen8 heading bisection. Combined with the sibling verdicts: +135deg alone is clean (PASS), -135deg alone fails (2 real falls), 180deg alone fails (0 falls but a new chronic sacrifice) -- 2 of the 3 new headings widen8 added are independently sufficient to trigger the front-pair/leg-0-style shortcut; only +135 is safe alone. This fully resolves the bisection: no >=2-heading interaction is needed, and the safe subset is exactly base5+135 (=this cycle's widenbis135 PASS), not base5+180 or base5+(-135). What's next: adopt base5+135 (6-way) as the validated widened heading set for this composite; do not attempt 180 or -135 in any combination without the still-unbuilt role-aware/support-margin reward mechanism.

