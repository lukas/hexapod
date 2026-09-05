# cw-walkscratch-easy0905-headset-halfgrav-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-05T11:57:23+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-c2

**wandb_id**: veqsr4jm

**hypothesis**: Plain English: the 2M heading canary (headset-halfgrav-c2) already proved the heading-tracking gradient is live under the SAME reward the fixed-forward halfgrav family trained under (no new keys) -- this gives it the full 40M acquisition budget to learn walking toward the commanded heading set (straight/+45/-45deg) as cleanly as halfgrav-s1/s2/s3/s0-c1 walked straight at 0.5g. Matching sibling to headset-base-acq1 (1g). Warm-started from headset-halfgrav-c2's own 2M checkpoint (own-track, not a teacher/BC/motion-prior).

**gate**: Acquisition milestone at OWN physics (0.5g) + heading: 20s held-out episodes across the 3-heading set, >=0.03 m/s median net forward along each commanded heading, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: continue/realign if still climbing at cutoff rather than an auto-fail.

**verdict**: ACQ PASS (first heading-set 40M acquisition to complete, 0.5g family): gate harness (24 episodes: walk+walk_startjitter x det+sto) is clean across the board -- gait_valid 24/24 (sacrificed_legs=[] every single episode), 0/24 terminations, median forward speed 0.147-0.164 m/s (5x the 0.03 m/s bar) in every mode, slip/m 2.4-2.6 (comfortably under the 2.9 band), height_err_end +8..+14mm (no belly drag). Frame-strip spot check (walk_det_0, static camera, 8 samples across the full 17.5s) confirms energetic six-leg cycling (feet-indicator toggles between planted/swinging patterns frame to frame, matching the per-leg duty_cycle 0.16-0.41 / swing_count 130-210 in the report -- nothing like the LEGPARK-SKATE frozen-splay signature seen elsewhere this campaign). Real caveat, not disqualifying: heading PRECISION is moderate and noisy rather than tight -- course_err_2s median 5.7-44 deg across det episodes (varies a lot per episode/per-heading-segment), worse and more variable under stochastic sampling (some sto episodes reach course_err med 64-79 deg with wrong_course_frac up to 0.14-0.39) -- but wrong_direction_frac stays low in det (0.002-0.025) and direction_valid_frac ~1.0 everywhere, i.e. the policy is never walking the wrong way, just under-rotating toward the +-45deg commands rather than fully committing. speed also overshoots the 0.06 m/s freeprog target by ~2-3x (same overshoot pattern already noted PASS-with-caveat on the fixed-forward base/halfgrav family). This is the first-ever 40M run on the brand-new 3-heading curriculum rung -- literal gate text (>=0.03 m/s net forward along each heading, 0 falls/12 det, six-leg video, no belly drag) is fully met; heading PRECISION hardening (tighter course-following, especially under sto) is the next rung's job, not a reason to fail this one.

