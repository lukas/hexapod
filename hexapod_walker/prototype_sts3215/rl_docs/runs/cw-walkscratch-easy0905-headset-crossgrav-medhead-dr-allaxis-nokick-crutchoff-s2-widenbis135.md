# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-widenbis135

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-07T12:27:46+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbis135

**hypothesis**: Plain English: does the +135deg-alone heading widen that EXONERATED seed 0 (base5+135, ACQ PASS, 21/24 gait_valid matching baseline) and replicated on seed 1 (also ACQ PASS, per this same cycle's launch) also hold on seed 2, completing the 3-seed confirmation this campaign requires before adopting an axis? Same exact recipe as s0/s1-widenbis135 (add ONLY +135deg to the 5-way heading set), warm-started from s2's OWN ACQ-passed crutchoff-s2-acq1 checkpoint, seed 4 to match s2's own convention. Prediction-if-true: gait_valid stays near s2-acq1's own 21/24 baseline, 0 falls, no new chronic sacrifice -- widenbis135 generalizes as safe on all 3 seeds. Prediction-if-false: a new chronic leg-pair sacrifice or fall appears -- the +135 heading is not uniformly safe.

**gate**: PASS if gait_valid>=18/24 (near s2-acq1's own 21/24 baseline) with 0 falls/24 and no new chronic sacrifice beyond s2-acq1's own walk_startjitter/sto leg0/leg5 flag. FAIL if a new chronic leg-pair sacrifice or fall appears, matching the widenbism135/widenbis180 regression shape instead.

**refused_reason**: hexapod-mjx-train-1 already runs cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-widenbis135 — GPU pods host exactly one run; pick a free GPU pod.

