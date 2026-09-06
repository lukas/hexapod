# cw-walkscratch-easy0905-headset-crossgrav-widenirrc1-abrupt-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T03:53:35+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-widenirrc1-abrupt-c1-acq1

**wandb_id**: 1us3k6k1

**hypothesis**: Plain English: same endurance question as the medhead/widen2c1 cont40m siblings, run on the CLEANEST crossgrav ACQ result so far (widenirrc1-abrupt-c1-acq1: 22/24 gait_valid, 0 falls, zero slip outliers across all 4 modes) -- the widen-then-irr composite recipe. If even the cleanest champion entrenches given another 40M 1g steps, that strengthens the universal-slow-clock reading; if it holds clean, entrenchment risk correlates with recipe cleanliness, not just crossgrav-transfer per se.

**gate**: HARDENING/endurance continuation (+40M, own checkpoint, no cfg change). PASS/HOLDS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with slip_per_m staying tightly banded (no new outlier class) and no NEW chronic leg beyond this checkpoint's own established 40M read (22/24, sac=[] every clean mode). FAIL/ENTRENCHES if a leg[1,4]-pattern chronic sacrifice newly emerges -- a 3rd recipe confirming the universal-entrenchment reading.

