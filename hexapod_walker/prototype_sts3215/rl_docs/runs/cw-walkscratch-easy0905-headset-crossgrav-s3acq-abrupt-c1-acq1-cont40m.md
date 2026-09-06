# cw-walkscratch-easy0905-headset-crossgrav-s3acq-abrupt-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ_FAIL

**created**: 2026-09-06T04:01:27+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s3acq-abrupt-c1-acq1

**wandb_id**: z1e7r91v

**hypothesis**: Plain English: same endurance question as the medhead/widen2c1/widenirrc1/s1acq cont40m siblings, run on the campaign's 2nd-best crossgrav champion (s3acq-abrupt-c1-acq1: 21/24 gait_valid, walk/det+walk/sto clean 6/6, only walk_startjitter/det softened to 3/6 non-chronically, 0 falls). Completes a 5-recipe endurance panel (medhead/widen2c1/widenirrc1/s1acq/s3acq) spanning the full cleanliness range of ACQ-PASSed crossgrav champions, testing whether entrenchment risk given extra 1g budget correlates with source cleanliness or hits every recipe regardless.

**gate**: HARDENING/endurance continuation (+40M, own checkpoint, no cfg change). PASS/HOLDS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with no NEW chronic leg beyond this checkpoint's own established 40M read (21/24). FAIL/ENTRENCHES if a leg[1,4]-pattern chronic sacrifice newly emerges -- completes the 5-recipe endurance panel either way.

**verdict**: ACQ FAIL - MECHANISM / ENTRENCHES: 2nd +40M endurance helping (80M cumulative 1g steps) on the campaign's 2nd-cleanest crossgrav source WORSENS the chronic leg-1 entrenchment already flagged at 40M, rather than resolving it. Aggregate gait_valid 16/24 (down from the 40M parent's 21/24) -- walk/det 6/6 and walk/sto 6/6 stay clean, but walk_startjitter/det collapses further to 1/6 (from 40M's own 2/6) and walk_startjitter/sto to 3/6 (unchanged). Leg-1 (index 1) duty is chronically low across ALL 6 walk_startjitter/det episodes (0.03,0.27,0.07,0.04,0.16,0.06) and all 6 walk_startjitter/sto episodes (0.06,0.13,0.21,0.04,0.03,0.19) -- the SAME chronic single-leg pattern from 40M, now more entries below the gait_valid duty floor. 0 falls (favoritism-under-load, not a freeze). Frame strip of a flagged episode (walk_startjitter_det_0) shows the body making an early push then stalling/barely translating for the back half of the clip, consistent with the reduced forward_dist (0.82m vs clean episodes' ~2m). This directly answers this run's own pre-registered gate question: MORE budget on an already-entrenching 2nd-cleanest-source champion does NOT rescue it -- it deepens the existing leg-1 park under the startjitter panel specifically, in contrast to the CLEANEST source (s1acq-abrupt-c1-acq1-cont40m, verdicted PASS/HOLDS this same cycle) which stayed exactly flat across the identical 2nd 40M helping. Completes the endurance panel's 2nd of 5 data points: cleanliness margin above the entrenchment threshold, not just budget, predicts whether more training helps or hurts.

