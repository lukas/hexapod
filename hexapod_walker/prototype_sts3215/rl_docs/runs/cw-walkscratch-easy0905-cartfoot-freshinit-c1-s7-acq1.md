# cw-walkscratch-easy0905-cartfoot-freshinit-c1-s7-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS - PARITY

**created**: 2026-09-08T06:49:23+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-freshinit-c1-s7

**wandb_id**: qnrtrce1

**hypothesis**: Plain English: does the Cartesian-foot-space fresh-init lineage actually learn to walk over a full budget, and if so how much slippier is it than its own joint-space sibling at the SAME fresh-init depth (not warm-started onto a mature multi-axis lineage the way the c1-s3/offctrl-s3 comparison was)? Own-checkpoint 40M continuation of the HEALTHY-PARITY CANARY-PASSed cart_foot ON arm (seed 7), matched against the sibling offctrl-s7-acq1 launched the same cycle. Prediction from the c1-s3 precedent: ON reaches gait_valid parity with OFF but at 3-10x the slip/m; alternative: fresh-init (vs warm-started) closes some or all of that gap.

**gate**: ACQUISITION: >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det), read together with offctrl-s7-acq1 at the SAME budget. PASS/CONTINUE per the 08-21 ruling if reward is still rising; slip/m vs the matched OFF sibling is the headline comparison, not a hardening bar.

**verdict**: Fresh-init Cartesian foot-target control matches (and on this reading, mildly beats) its own matched joint-space control at the same 40M fresh-init budget -- a materially different result from the mature/warm-started cart_foot lineage that fork(a) just closed as 2-6x slippier with new falls. 0 falls/terminations in 24/24 episodes across all 4 eval groups (walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto). Mean slip/m ON vs OFF: 2.79/2.83 (walk/det, ratio 0.99), 3.22/3.41 (walk/sto, ratio 0.94), 2.79/2.85 (startjitter/det, ratio 0.98), 3.10/3.26 (startjitter/sto, ratio 0.95) -- ON is at-or-under the control in all 4 groups, the opposite of the 1.5-6x inflation the mature retrofit lineage showed (seed2/seed3/fork-a). speed_mean_m_s is also slightly higher for ON in all 4 groups (0.202/0.187/0.207/0.194 vs 0.195/0.175/0.191/0.183), clearing the >=0.03 m/s gate floor with room to spare. gait_valid: ON matches OFF in 3/4 groups (6/6) and BEATS it in walk_startjitter/det (5/6 vs OFF's 1/6 -- OFF sacrifices leg 4 in 5/6 episodes, ON only in 1/6). Frame strips (walk_det_0.png both arms) show a level, upright body with real alternating leg swing on both, no visible flag-leg/drag pathology on either. Interpretation: this closes the fork(b) fresh-init acquisition question for seed 7 cleanly -- at matched fresh-init depth and budget, the Cartesian foot-target action space is NOT inherently slippier than joint-space; the 2-6x inflation fork(a) measured looks specific to retrofitting the Cartesian head onto weights already mature in joint-space (a warm-start/retrofit artifact), not a property of the action space itself. This QUALIFIES fork(a)'s closure (does not reverse it): fork(a) stays correctly closed for that exact warm-started lineage, but the implied 'Cartesian-space-is-slippier' generalization does not hold for fresh-init training. Next: read the seed-11 fresh-init acquisition pair (still training this cycle) as a second replicate before elevating this to a track-level ruling.

