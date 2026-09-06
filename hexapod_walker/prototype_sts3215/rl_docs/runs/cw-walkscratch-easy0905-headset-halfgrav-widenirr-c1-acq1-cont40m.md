# cw-walkscratch-easy0905-headset-halfgrav-widenirr-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T12:15:02+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-widenirr-c1-acq1

**wandb_id**: ab1hqszt

**hypothesis**: The widen-first widen2+irr composite (halfgrav) ACQ PASSed cleanly at 40M (23/24 gait_valid, 0 falls, no chronic leg, beats plain widen2 sibling) but has never been continued past 40M -- cleanest halfgrav composition champion still lacking cont40m, per the campaign's cleanliness-margin-predicts-endurance rule already confirmed on friction1x/mass1x/torquefade/irrwiden-c2/medhead-ramp. (multiple prior attempts this cycle hit a launch-syntax bug then a transient self-repair tar race then a pod collision with a concurrent cycle's own launch; explicit free pod picked here.)

**gate**: HARDENING PASS/HOLDS if gait_valid stays majority (>=18/24) at 80M cumulative with no NEW chronic single-leg pattern and 0 falls. HARDENING FAIL/ENTRENCHES if it drops below majority, a new chronic leg appears, or any fall appears.

**verdict**: HARDENING PASS/HOLDS (mild degrade, matches the widenirr-c3 sibling precedent). At 80M cumulative the widen-first widen2+irr halfgrav composite still walks cleanly: gait_valid 21/24 (walk/det 5/6, walk/sto 5/6, walk_startjitter/det 5/6, walk_startjitter/sto 6/6), down only mildly from the 40M parent's 23/24, every mode still clears the gate's own >=4/6 majority bar, 0 falls/terminations across all 24 episodes. The extra flagged episodes are scattered non-chronic sacrifice, not a new chronic leg: walk/det ep3 legs[2,5] is the SAME episode+legs the parent already flagged; walk_startjitter/det ep4 leg[1] and walk/sto ep5 leg[5] are new but one-off (no mode drops below majority, no leg is out in most episodes of any mode) -- the gate's 'no NEW chronic single-leg pattern' bright line is not tripped. slip_per_m actually IMPROVED (parent had two blowup outliers 117/112 m/m in the /sto modes; child's worst is 14.6) and reward ends near where it started (-798.9 -> -738.4, dipped mid-run then recovered) after 40M more steps -- not a collapse. Video (contact sheet + walk_det_3 and walk_startjitter_det_4 frame strips) shows upright six-leg cycling and clear body translation in every clip, no dragging or frozen leg. Why: this matches the widenirr-c3 sibling's own cont40m PASS shape (21/24->19/24, scattered/non-chronic) and confirms the campaign's established rule that a clean-40M source with no prior WATCH signal holds past acquisition. Next: widenirr-c1 joins widenirr-c3/medhead/irrwiden/plain-halfgrav as a top halfgrav 80M champion candidate; leg5's 2-of-3 recurrence is a soft watch item only, no further spend needed on this line.

