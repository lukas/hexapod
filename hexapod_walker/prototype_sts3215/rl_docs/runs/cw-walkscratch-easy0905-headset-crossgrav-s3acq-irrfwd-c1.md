# cw-walkscratch-easy0905-headset-crossgrav-s3acq-irrfwd-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-06T04:26:54+00:00

**pod**: hexapod-mjx-train-11

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s3acq-abrupt-c1-acq1

**wandb_id**: aaoxg15b

**hypothesis**: Plain English: s3acq-abrupt-c1-acq1 is the 2nd-cleanest crossgrav champion in the sweep (gait_valid 21/24 at 40M). Mirroring the s1acq pair launched this cycle, can the SAME irr command-timing-jitter composite be added FORWARD, directly at 1g, on this 2nd champion too -- completing n=2 champions x n=2 axes for the forward-compose-on-a-clean-crossgrav-source question?

**gate**: CANARY PASS - INFORMATIVE-POSITIVE if gait_valid stays majority-or-better (>=18/24) with no chronic single-leg sacrifice, matching medhead-irrfwd-c1 (22/24) and the s1acq sibling. FAIL/INFORMATIVE-NEGATIVE if it collapses toward chronic single-leg sacrifice.

**verdict**: CANARY FAIL - INFORMATIVE-NEGATIVE (mild/borderline): forward-composing the irr command-timing-jitter axis onto the same already-known-compromised s3acq-abrupt-c1-acq1 source misses its own >=18/24 bar by one episode. Aggregate gait_valid 17/24 (walk/det 3/6 sac=[1]/[2]/[2], walk/sto 6/6, walk_startjitter/det 5/6 sac=[1], walk_startjitter/sto 3/6 sac=[1]x3). 0 falls/terminations. Leg-1 is flagged in 4/24 episodes (all 3 startjitter/sto invalids + 1 startjitter/det) and leg-2 in 2/24 (both walk/det) -- softer/more mixed than the widenfwd sibling's clean 10/10 leg-1 sweep, but the leg-1 concentration in walk_startjitter/sto (3/3 invalid = leg-1) reproduces the same source fingerprint. Reward mildly net-rising (18.0/49.2/42.3/64.0) but this is a 2M informative canary off an already twice-FAILed source (40M and 80M-cont40m both chronic leg-1 startjitter), not a case warranting further budget per the established campaign pattern (CANARY FAIL -> no continuation, not CANARY borderline-pass -> continue). Slip/m stays in a normal 3.6-7.6 band (no extreme skating unlike the widenfwd sibling). Together with widenfwd, closes the forward-compose-on-compromised-source question for both tested axes at n=2/2: composing forward does not rescue or dilute an already-present structural leg-1 weakness, it re-surfaces at 2M regardless of which axis is added. No continuation warranted.

