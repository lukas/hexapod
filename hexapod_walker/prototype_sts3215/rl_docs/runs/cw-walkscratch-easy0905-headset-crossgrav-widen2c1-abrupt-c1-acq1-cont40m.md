# cw-walkscratch-easy0905-headset-crossgrav-widen2c1-abrupt-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T03:51:35+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-widen2c1-abrupt-c1-acq1

**hypothesis**: Plain English: a sibling crossgrav champion (irr-timing recipe) ACQ-FAILed via base(1g) leg-1/4 structural entrenchment after 40M steps despite a clean 2M canary and rising reward (CURRENT_TRUTHS 09-06 ~03:1x); does the SAME slow-clock entrenchment risk hit the widen2 (full 8-way heading) crossgrav champion given another 40M 1g steps, or is it recipe/seed-specific? widen2c1-abrupt-c1-acq1 is a healthy ACQ PASS (20/24 gait_valid, 0 falls, slip improved vs its own canary) off a materially different recipe (heading-widening, not timing-jitter) than the irracq1 regression.

**gate**: HARDENING/endurance continuation (+40M, own checkpoint, no cfg change). PASS/HOLDS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with no NEW chronic leg beyond this checkpoint's own established 40M read (20/24). FAIL/ENTRENCHES if walk/det or walk/sto regresses to majority failure or a leg[1,4]-pattern chronic sacrifice newly emerges -- adds a 2nd recipe to the 'any crossgrav champion entrenches given enough budget' finding.

