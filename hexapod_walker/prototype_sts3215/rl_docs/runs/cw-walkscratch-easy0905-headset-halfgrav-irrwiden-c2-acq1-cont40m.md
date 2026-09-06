# cw-walkscratch-easy0905-headset-halfgrav-irrwiden-c2-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T09:53:06+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irrwiden-c2-acq1

**wandb_id**: aitfa735

**hypothesis**: Plain English: the jitter-first widen+irr composite's 2nd seed cleared its own 40M ACQ PASS (22/24 gv, 0 falls, seed-specific weaker course-obedience flagged but not gate-blocking); a +40M own-checkpoint cont40m endurance continuation (80M cumulative) tests whether this clean-but-weaker-margin seed holds the same way every other clean ACQ PASS source has held at 80M, matching the campaign's standard cleanliness-margin-predicts-endurance refill pattern.

**gate**: HARDENING PASS/HOLDS if gait_valid stays majority (>=18/24) with 0 NEW chronic single-leg pattern and 0 falls, reproducing (not worsening) this run's own 40M flags; HARDENING FAIL if a chronic leg entrenches, falls appear, or gait_valid drops below majority -- the doc's own endurance-regression trigger.

