# cw-walkscratch-easy0905-headset-crossgrav-s1acq-abrupt-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T03:57:56+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s1acq-abrupt-c1-acq1

**hypothesis**: Plain English: same endurance question as the medhead/widen2c1/widenirrc1 cont40m siblings, run on the CAMPAIGN'S OVERALL CLEANEST crossgrav result (s1acq-abrupt-c1-acq1: PERFECT 24/24 gait_valid, sac=[] in literally every one of 24 episodes, 0 falls). If even this perfect champion entrenches given another 40M 1g steps, that clinches the universal-slow-clock reading regardless of source cleanliness; if it alone survives, cleanliness/margin above the entrenchment threshold is what matters, not recipe.

**gate**: HARDENING/endurance continuation (+40M, own checkpoint, no cfg change). PASS/HOLDS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with no NEW chronic leg beyond this checkpoint's own established 40M read (24/24, sac=[] every episode). FAIL/ENTRENCHES if a leg[1,4]-pattern chronic sacrifice newly emerges even from this cleanest possible starting point -- the strongest possible confirmation of the universal-entrenchment reading.

