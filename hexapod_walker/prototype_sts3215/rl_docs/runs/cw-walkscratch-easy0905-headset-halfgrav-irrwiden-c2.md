# cw-walkscratch-easy0905-headset-halfgrav-irrwiden-c2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T01:06:59+00:00

**pod**: hexapod-mjx-train-8

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irr2-acq1

**hypothesis**: Plain English: irrwiden-c1-acq1 (widen2's full 8-way heading set applied ON TOP of the irr-timing-jitter champion irr-acq1) just ACQ PASSed at 40M -- gait_valid 22/24, 0 falls, course/slip matching its own 2M canary -- confirming the widen+irr composite (the actual DONE-gate panel shape: heading breadth AND irregular timing together) survives full budget on ONE seed. This arm tests the SAME composition recipe (identical heading-set + jitter cfg, no new mechanism) on a DIFFERENT, independently-ACQ-PASSed irr-timing parent (irr2-acq1, seed3, warm-started from a different base lineage s1acq not acq1) to give the composite its own n=2 seed confirmation before calling it a validated recipe rather than a single lucky seed.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (2M): PASS/INFORMATIVE if gait_valid stays majority-valid (>=4/6 det) with 0 falls, matching or beating irr2-acq1's own clean numbers (19/24, 0 falls) -- do not judge mature course-tracking at 2M. FAIL - MECHANISM if gait_valid collapses into minority or falls appear, or a new chronic single-leg sacrifice pattern emerges vs irr2-acq1's own baseline (would argue the composite is parent-lineage-specific, not general).

