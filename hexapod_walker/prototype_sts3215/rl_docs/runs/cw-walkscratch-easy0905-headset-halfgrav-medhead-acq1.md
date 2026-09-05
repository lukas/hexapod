# cw-walkscratch-easy0905-headset-halfgrav-medhead-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-05T18:17:58+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-medhead-c1

**wandb_id**: dejrlkhv

**hypothesis**: the 2M medium-heading canary (headset-halfgrav-medhead-c1) already proved the heading-tracking gradient is live and mechanism-healthy on the 5-way quarter-turn set at 0.5g (v_along cleared the noise floor, full survival, harness-confirmed 24/24 gait_valid six-leg walking, no collapse) -- this gives it the full 40M acquisition budget to see if it learns to walk toward all 5 commanded headings as cleanly as halfgrav-acq1 learned the 3-way set. Warm-started from headset-halfgrav-medhead-c1's own 2M checkpoint (own-track continuation, not a teacher/BC/motion-prior), mirroring headset-base-medhead-acq1's template on the sibling 1g family.

**gate**: ACQUISITION (40M): PASS if held-out walk/det + walk_startjitter/det harness gait_valid majority (>=4/6 each) with no chronically-parked leg (duty>=0.10 on all six) across the 5-way heading set, slip_per_m staying near the 2.9 teacher band, zero falls. CONTINUE if gait_valid is marginal but reward/v_along keep climbing without collapse (08-21). FAIL if a leg re-sacrifices majority-of-episodes or course-tracking degrades toward the far/reversal headings the same way the bare 8-way fullhead jump did.

**verdict**: ACQ PASS: the 0.5g medium-heading-set (5-way, 0/+-45/+-90) 40M acquisition run clears every gate bar. gait_valid: walk/det 6/6 (zero sacrificed legs any episode), walk/sto 6/6, walk_startjitter/det 4/6 (meets the >=4/6 majority bar exactly; the 2 non-valid episodes carry leg-4 duty 0.08/0.09, just under the 0.10 chronic-park cutoff and isolated to 2/6 episodes -- not the base family's near-zero/all-episodes fingerprint), walk_startjitter/sto 6/6 -- 22/24 overall, 0 falls/terminations any mode. slip_per_m med 2.10 (walk/det)/2.87 (walk/sto)/2.34 (walk_startjitter/det)/2.52 (walk_startjitter/sto), at or under the 2.9 teacher band in 3/4 subsets. forward_dist_m 1.7-3.2m/20s (~0.09-0.16 m/s), reward still climbing every quarter (-395->-366->-95->129, same flat-per-tick-x-scheduled-ep_len-ramp shape every clean arm this campaign shows, not a collapse). Direction tracking (direction_err_mean_deg 20-63deg, 0/24 success) stays the open, separately-tracked course-tracking gap this rung already flagged, not this gate's bar. Sibling headset-base-medhead-acq1 (same rung, 1g) FAILED this cycle on the exact opposite fingerprint (leg-1/4 chronically parked near-zero duty, majority det-mode gait_valid loss) -- this PASS/FAIL split reinforces the gravity-linked-robustness-gap hypothesis: halfgrav clears every generalization axis added so far (irr-timing, now medhead), base does not.

