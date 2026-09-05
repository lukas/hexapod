# cw-walkscratch-easy0905-headset-base-medhead-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-05T18:11:53+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-base-medhead-c1

**wandb_id**: 8dtoak13

**hypothesis**: Plain English: the 2M medium-heading canary (headset-base-medhead-c1) already proved the heading-tracking gradient is live and mechanism-healthy on the 5-way quarter-turn set (v_along cleared the noise floor, full survival, no collapse) -- this gives it the full 40M acquisition budget to see if it actually learns to walk toward all 5 commanded headings (0,+-45,+-90deg) as cleanly as base-acq1 learned the 3-way set. Warm-started from headset-base-medhead-c1's own 2M checkpoint (own-track continuation, not a teacher/BC/motion-prior).

**gate**: Acquisition milestone at own physics + medium heading set: 20s held-out episodes across all 5 headings (0,+-45,+-90deg), >=0.03 m/s median net forward along each commanded heading, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: continue/realign if still climbing at cutoff rather than reflex-stop. PASS licenses re-attempting the full 8-way set as the next widening rung; FAIL (flat/non-tracking after 40M) means the quarter-turn-only rung itself needs decomposition (e.g. one direction pair at a time) before any wider set.

**verdict**: ACQ FAIL (mechanism, gait-validity majority bar unmet): the base(1g)-family medium-heading-set (5-way, 0/+-45/+-90) 40M acquisition run clears its speed/fall bars cleanly (0/24 falls or terminations any mode; forward_dist_m med 1.9-2.6m/20s = ~0.09-0.13m/s, well above the 0.03 m/s floor; reward climbs every quarter -279->-107->186->398) but FAILS the gate's own six-leg/no-belly-drag criterion: gait_valid only 10/24 overall (walk/det 1/6, walk_startjitter/det 1/6, walk_startjitter/sto 2/6, only walk/sto clean 6/6), well under the majority bar this campaign adopted at the s0c1-acq1 FAIL (09-05 14:50). Same fingerprint as that FAIL and irr-acq1's FAIL: legs 1 and/or 4 chronically sacrificed (duty near-zero) in det-mode episodes specifically, worst on the exact headings this rung adds. direction_err_mean_deg is also uniformly poor across every heading (22-60deg, 0/24 'success' even on the original 0/+-45 subset that the earlier fullhead-c1 canary tracked cleanly) -- course tracking did not survive the jump from small-set to medium-set at acquisition scale on this lineage. Per 08-21: reward is still rising but this is the SAME hardened-not-cleared structural gait defect already confirmed twice on this family (s0c1-acq1, irr-acq1) at full 40M budget -- an aligned reward with adequate budget still not moving the gate is a genuine FAIL, not a 'needs longer' case; a 3rd same-recipe 40M continuation would be a same-recipe dribble ahead of a design fix. Cross-family signal (pending halfgrav-medhead-acq1's own read, still computing): base(1g) now fails EVERY axis this campaign has added beyond flat/small-heading (irr-timing, medium-heading), while halfgrav(0.5g) has cleared irr-timing cleanly -- reinforces a gravity-linked robustness gap, not a heading-set-specific one.

