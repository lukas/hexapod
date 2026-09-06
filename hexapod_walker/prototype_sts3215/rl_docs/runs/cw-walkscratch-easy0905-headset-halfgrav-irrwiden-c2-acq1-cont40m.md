# cw-walkscratch-easy0905-headset-halfgrav-irrwiden-c2-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T09:53:06+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irrwiden-c2-acq1

**wandb_id**: aitfa735

**hypothesis**: Plain English: the jitter-first widen+irr composite's 2nd seed cleared its own 40M ACQ PASS (22/24 gv, 0 falls, seed-specific weaker course-obedience flagged but not gate-blocking); a +40M own-checkpoint cont40m endurance continuation (80M cumulative) tests whether this clean-but-weaker-margin seed holds the same way every other clean ACQ PASS source has held at 80M, matching the campaign's standard cleanliness-margin-predicts-endurance refill pattern.

**gate**: HARDENING PASS/HOLDS if gait_valid stays majority (>=18/24) with 0 NEW chronic single-leg pattern and 0 falls, reproducing (not worsening) this run's own 40M flags; HARDENING FAIL if a chronic leg entrenches, falls appear, or gait_valid drops below majority -- the doc's own endurance-regression trigger.

**verdict**: HARDENING PASS/HOLDS -- +40M 2nd helping (80M cumulative) on the halfgrav-irrwiden-c2-acq1 champion reproduces its own 40M flags rather than worsening them. Aggregate gait_valid 19/24 (down slightly from parent's 22/24 but still clear majority, gate bar >=18/24), 0 falls/terminations across all 96 episodes (both reads). The parent's known seed-level course-tracking gap (this seed drags high slip_per_m ~115-128 in a subset of walk/sto+startjitter episodes, already flagged at ACQ as NOT a 40M regression but present since the 2M canary) reproduces at the SAME episode indices with the SAME leg (leg4) implicated (det idx3, startjitter_sto idx0 in both reads) -- now occasionally joined by leg1/leg2 in those same weak episodes, but slip outlier COUNT actually improved (3 episodes >100 slip_per_m here vs 6 in the parent). No new chronic single-leg pattern: legs 0/1/2 each appear in exactly one episode, not a sustained pattern. Video (contact_sheet.png, walk_det_3 frame strip -- the sac=[1,2,4] episode) shows genuine six-leg cycling and forward+turning translation, not a frozen/dragging leg. Matches the medhead-abrupt-c1-acq1-cont40m precedent (CURRENT_TRUTHS 09-06 ~05:3x: cont40m helps a source whose first 40M read was already clean; here the source's known flag is a course-tracking quirk, not a chronic-leg entrenchment, so it reproduces cleanly rather than compounding). Next: no further cont40m needed on this exact lineage; the course-tracking gap (high slip on wrong-course sto episodes) is this seed's own known quirk to carry forward if irrwiden-c2 composes further, not a fresh repair target.

