# cw-walkscratch-easy0905-headset-halfgrav-widenirr-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-05T23:51:45+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-widenirr-c1

**wandb_id**: 71edsb6v

**hypothesis**: Plain English: widenirr-c1's 2M canary showed that composing the two independently-validated halfgrav rungs (widen2's heading-widen-from-medhead + irr's command-timing jitter, jitter applied on top of the widen2-c1 champion) is not just mechanism-healthy but actually BEATS the widen2-c1 champion's own clean canary numbers (23/24 vs 21/24 gait_valid, 0 falls, course-tracking not blown up by the added jitter). This is the acquisition-scale (40M) confirmation: does the composed widen+irr recipe hold a real course-tracking/gait advantage over plain widen2-c1-acq1 (already ACQ PASS, 21/24 gait_valid, this same cycle) at full budget, or does more training erode the composition edge the way it eroded the matched seed-2 sibling (widen2-c2b-acq1, ACQ FAIL, chronic leg-1) and widenirr-c2b (CANARY FAIL, same seed lineage)?

**gate**: ACQ PASS if gait_valid stays majority-valid (>=18/24) with 0 chronic single-leg entrenchment (no leg parked in >50% of episodes) and course/heading tracking (courserr, wrong_course_frac_1s) is flat-or-better vs this run's own 2M canary read and vs the plain widen2-c1-acq1 sibling; ACQ FAIL if gait_valid collapses into minority or a leg chronically parks, matching the widen2-c2b-acq1 entrenchment fingerprint.

**verdict**: Result: the widen-first widen2+irr composition holds at full 40M budget on seed 1 -- clean ACQ PASS, beats the plain widen2-c1-acq1 sibling. Evidence: gait_valid 23/24 (walk/det 5/6 sac[2,5] transient-only, walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6), 0 falls/terminations in all 24 episodes, no chronic single-leg entrenchment (every leg's <0.10-duty count is at most 1/24 episodes). Vs this run's own 2M canary: gait_valid flat (23/24->23/24) and course tracking IMPROVES (wrong_course_frac_1s mean 0.367->0.247, course_err_1s_med_deg 68.6->50.5, direction_err_mean_deg 69.6->63.0), slip_per_m median flat (4.43->4.74, noise-level). Vs the widen2-c1-acq1 sibling (same budget, plain widen2 recipe): gait_valid beats it (23/24 vs 21/24), course_err/direction_err both modestly better (50.5 vs 54.3; 63.0 vs 64.3), wrong_course_frac_1s ties (0.247 vs 0.247), slip ties (4.74 vs 4.72). Video (walk_det_0) shows genuine six-leg cycling with the body translating, not frozen/dragging. Why: matches the gate's own written ACQ-PASS criterion on every axis (majority gait_valid, no chronic entrenchment, course tracking flat-or-better vs both comparators). Gotcha found+fixed this cycle: the harness's own prestaged gate eval for THIS checkpoint was still computing when my cycle spawned (widen2/acq1 naming race is unrelated to the accidental duplicate below) -- ops.sh report/review's unanchored '*snake*' glob was meanwhile silently serving the stale, only-4M-trained accidental-duplicate checkpoint's report (cw-walkscratch-easy0905-headset-halfgrav-widenirr-c1-acq1b, killed early on train-3 per the 09-05 23:56 logline) because 'acq1b' contains 'acq1' as a substring -- caught it by checking num_timesteps inside both zips (4194304 vs 40370176) before trusting the numbers, waited ~25min for the real gate eval to finish+sync (kubectl exec confirmed it was actively running on train-7), then re-verdicted off the correct report. Fixed the glob (anchored with a trailing '_' boundary in both ops.sh report and review) so a future near-duplicate run-name collision can't silently serve a sibling's stale/wrong-checkpoint eval; smoke-tested against this exact acq1/acq1b pair, snapshotted (exp/ops-review-glob-boundary-fix-090601). What's next: widenirr-c1-acq1 is a new leg-healthy halfgrav champion not yet tested for cross-gravity-transfer (the concurrent cycle's active generality sweep covers medhead/widen2c1/widen2c2b/irr-acq1 only) -- launching a matched crossgrav-transfer discovery arm off it this cycle.

