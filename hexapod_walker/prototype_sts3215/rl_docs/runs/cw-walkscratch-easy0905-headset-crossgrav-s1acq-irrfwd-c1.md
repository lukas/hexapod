# cw-walkscratch-easy0905-headset-crossgrav-s1acq-irrfwd-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY_PASS

**created**: 2026-09-06T04:21:43+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s1acq-abrupt-c1-acq1

**wandb_id**: o3bapgqi

**hypothesis**: Plain English: every widen2/irr heading+jitter composite tested so far was built in 0.5g FIRST then abruptly transferred to 1g (or, for medhead, composed forward on a merely-ACQ-PASS plain champion). s1acq-abrupt-c1-acq1 is the CLEANEST crossgrav champion in the entire sweep (gait_valid PERFECT 24/24 at 40M, sac=[] in every episode) but has never been composed with irregular command-timing jitter. Can the SAME irr composite be added FORWARD, directly at 1g, on top of the cleanest available foundation?

**gate**: CANARY PASS - INFORMATIVE-POSITIVE if gait_valid stays majority-or-better (>=18/24) with no chronic single-leg sacrifice; matches the medhead-irrfwd-c1 precedent (22/24) if the cross-gravity repair is a durable foundation independent of source champion. FAIL/INFORMATIVE-NEGATIVE if it collapses toward chronic single-leg sacrifice.

**verdict**: CANARY PASS - INFORMATIVE-POSITIVE: forward-composing the irr-timing jitter axis natively at 1g onto the campaign's cleanest crossgrav champion (s1acq-abrupt-c1-acq1, 24/24 native) transfers cleanly at 2M. Aggregate gait_valid 22/24 -- walk/det 4/6 (leg-4 flagged in episodes 1 and 5, duty softened but not zero), walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6 -- matches the medhead-irrfwd-c1 precedent (22/24) almost exactly, and the leg-4 softening is confined to walk/det only (not chronic across all 4 modes, unlike the closed leg[1,4] startjitter-panel entrenchment pattern). 0 falls/terminations across all 24 episodes. Frame strips (walk_det_1 flagged, walk_det_2 clean) both show genuine six-leg cycling with clear body translation, not a degenerate/frozen gait. slip_per_m 3.7-7.0, forward_dist 1.9-3.0m/20s, consistent with sibling forward-extension canaries. Confirms compose-after-transfer for the irr-jitter axis generalizes to a 3rd independent base champion (after medhead, s1acq's own widenfwd sibling), same conclusion as s1acq-widenfwd-c1's own CANARY PASS. Eligible for a matched 40M ACQ continuation per the medhead/widen2c1/s3acq precedent.

