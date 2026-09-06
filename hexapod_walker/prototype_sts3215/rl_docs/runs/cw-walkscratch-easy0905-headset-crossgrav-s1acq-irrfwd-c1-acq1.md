# cw-walkscratch-easy0905-headset-crossgrav-s1acq-irrfwd-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T05:27:56+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s1acq-irrfwd-c1

**wandb_id**: 0iafbobq

**hypothesis**: Matched 40M ACQ continuation of s1acq-irrfwd-c1's own CANARY PASS (22/24, leg-4 softening confined to walk/det only, no chronic cross-mode pattern) -- does the irr-jitter axis composed onto the cleanest crossgrav source (s1acq-abrupt-c1-acq1) hold at full ACQ budget, matching medhead-irrfwd-c1-acq1's own ACQ PASS precedent, or does it entrench like s3acq-abrupt-c1-acq1/irracq1/irr2acq1 did?

**gate**: ACQ PASS if aggregate gait_valid stays majority (>=18/24) with no NEW chronic single-leg sacrifice beyond the canary's own confined walk/det leg-4 softening. ACQ FAIL - MECHANISM if a leg[1,4]-pattern chronic sacrifice emerges or spreads to the startjitter panels (matching the s3acq/irracq1/irr2acq1 entrenchment fingerprint).

**verdict**: ACQ PASS (borderline, flagged for WATCH) — s1acq-irrfwd-c1-acq1 (irr-timing composed onto the cleanest crossgrav champion s1acq-abrupt-c1-acq1) stays majority at full 40M budget: aggregate gait_valid 20/24 vs the canary's 22/24 (walk/det 4/6, walk/sto 6/6, walk_startjitter/det 5/6, walk_startjitter/sto 5/6), 0 falls/terminations in all 24 episodes, reward rising every quarter (278.8->581.2->745.9->909.7, 08-21 ruling). BUT the sacrifice fingerprint did shift, not just hold flat: the canary's own confined walk/det leg-4 softening (det/1, det/5, single leg) WORSENED to a leg[2,4] pair at the SAME two episode indices, and leg-4 (part of the campaign's named leg[1,4] entrenchment family) newly appears in walk_startjitter/det/2 -- a mode that was clean 6/6 at the 2M canary. Neither is majority/chronic within its mode (max 2/6), so this does not meet the gate's own FAIL bar ('chronic sacrifice emerges or spreads'), and video (walk_det_1, walk_startjitter_det_2 frame strips) shows continued six-leg forward gait with no visible drag/freeze -- verdicting PASS, not FAIL. However this is a materially different signal than the sibling s1acq-widenfwd-c1-acq1 (verdicted PASS same cycle, lateral non-worsening shift only) and than medhead-irrfwd-c1-acq1 (flat vs canary) -- this one shows genuine worsening-at-same-indices plus a new-mode spread, an early instance of exactly the pattern that preceded chronic entrenchment in s3acq/irracq1/irr2acq1. Recommendation: do NOT fund a cont40m endurance helping on this specific source without a fresh confirming read first (unlike its widenfwd/medhead siblings, which this cycle DID get cont40m funding) -- this source's cleanliness margin at 40M is weaker than those.

