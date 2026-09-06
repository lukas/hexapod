# cw-walkscratch-easy0905-headset-crossgrav-s1acq-widenfwd-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T04:20:09+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s1acq-abrupt-c1-acq1

**wandb_id**: 3psjr4s8

**hypothesis**: Plain English: every widen2/irr heading+jitter composite tested so far was built in 0.5g FIRST then abruptly transferred to 1g (or, for medhead, composed forward on a merely-ACQ-PASS plain champion). s1acq-abrupt-c1-acq1 is the CLEANEST crossgrav champion in the entire sweep (gait_valid PERFECT 24/24 at 40M, sac=[] in every episode) but has never been composed with new heading breadth. Can the SAME widen2 full-8-way-heading-set composition be added FORWARD, directly at 1g, on top of the cleanest available foundation?

**gate**: CANARY PASS - INFORMATIVE-POSITIVE if gait_valid stays majority-or-better (>=18/24) with no chronic single-leg sacrifice; matches the medhead-widenfwd-c1 precedent (23/24) if the cross-gravity repair is a durable foundation independent of source champion. FAIL/INFORMATIVE-NEGATIVE if it collapses toward chronic single-leg sacrifice, showing even the cleanest champion is not immune to composite-driven entrenchment.

**verdict**: CANARY PASS - INFORMATIVE-POSITIVE per the run's own gate. Plain English: does composing the full 8-way heading set FORWARD (natively at 1g, no 0.5g detour) transfer cleanly onto the campaign's cleanest crossgrav champion (s1acq-abrupt-c1-acq1, 24/24 gait_valid at 40M)? Yes. Evidence: aggregate gait_valid 22/24 (walk/det 5/6, walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 5/6), 0 falls/terminations anywhere, matches the medhead-widenfwd-c1 precedent (23/24) almost exactly -- a 3rd independent base champion where this composition transfers with no chronic single-leg sacrifice (the two flagged episodes each name a different, non-repeating leg set: det/4 sac=[0,3], startjitter-sto/4 sac=[4]). Video-confirmed: clean episodes (e.g. walk/det/2, prog 2.15, slip 3.70) show genuine six-leg forward translation tracking the commanded heading; the worst-slip episodes (walk/sto/3 slip 208, walk_startjitter/det/2 slip 194, both negative progress) show the SAME already-documented distance-graded course-tracking gap on hard (quarter-turn/reversal) headings from the full 8-way set, not a new pathology or leg sacrifice -- gait_valid stays true (six legs cycling) even in those episodes, just spinning/skating instead of translating. Reward quarters are net-declining (-116.9/-255.6/-353.9/-392.1), consistent with a harder task (full heading breadth including reversals) still being explored at 2M rather than a misaligned collapse -- the gate's own explicit pass condition (gait_valid majority + no chronic sacrifice) is what's scoped at this canary, not reward trend. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_s1acq_widenfwd_c1_gate/report.json, walk_det_2/walk_sto_3/walk_startjitter_det_2 frame strips, W&B 3psjr4s8.

