# cw-walkscratch-easy0905-headset-crossgrav-s1acq-abrupt-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T03:57:56+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s1acq-abrupt-c1-acq1

**wandb_id**: 7i7dzujt

**hypothesis**: Plain English: same endurance question as the medhead/widen2c1/widenirrc1 cont40m siblings, run on the CAMPAIGN'S OVERALL CLEANEST crossgrav result (s1acq-abrupt-c1-acq1: PERFECT 24/24 gait_valid, sac=[] in literally every one of 24 episodes, 0 falls). If even this perfect champion entrenches given another 40M 1g steps, that clinches the universal-slow-clock reading regardless of source cleanliness; if it alone survives, cleanliness/margin above the entrenchment threshold is what matters, not recipe.

**gate**: HARDENING/endurance continuation (+40M, own checkpoint, no cfg change). PASS/HOLDS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with no NEW chronic leg beyond this checkpoint's own established 40M read (24/24, sac=[] every episode). FAIL/ENTRENCHES if a leg[1,4]-pattern chronic sacrifice newly emerges even from this cleanest possible starting point -- the strongest possible confirmation of the universal-entrenchment reading.

**verdict**: PASS/HOLDS: 2nd +40M endurance helping (80M cumulative 1g steps) on the campaign's overall cleanest crossgrav champion (24/24 canary, 23/24 at first 40M ACQ) reproduces its own 40M read EXACTLY -- aggregate gait_valid 23/24 (walk/det 6/6, walk/sto 6/6, walk_startjitter/det 5/6 with the SAME single transient leg-4 dip in the same episode slot, walk_startjitter/sto 6/6), 0 falls across all 24 episodes, sac=[] in every episode except that one. reward quarters still rising (260->530->715->871), no entrenchment. Frame strips (walk_det_0, walk_startjitter_det_1) confirm genuine six-leg cycling with clear body translation, not a degenerate gait. This is the strongest possible endurance result: the campaign's healthiest source champion tolerates DOUBLE the standard ACQ budget with zero new chronic leg emergence, directly confirming (for a 2nd budget tier) that crossgrav-transfer durability tracks source-champion cleanliness rather than being a universal slow clock every transfer eventually hits. Completes 1 of the 5-recipe endurance panel this campaign pre-registered; read s3acq-abrupt-c1-acq1-cont40m (2nd-cleanest source) once its own gate lands for the 2nd data point.

