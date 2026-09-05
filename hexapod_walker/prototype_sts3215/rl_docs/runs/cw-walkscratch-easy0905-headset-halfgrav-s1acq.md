# cw-walkscratch-easy0905-headset-halfgrav-s1acq

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-05T13:19:52+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-s1

**wandb_id**: yqm9c7e8

**hypothesis**: Plain English: the heading canary (headset-halfgrav-s1) already reads exceptionally clean at 2M (24/24 gait_valid, 0 falls, slip in-band) -- this gives it the full 40M acquisition budget to mature that six-leg heading gait (longer strides, less quiver) at 0.5g toward the 3-heading set, matching sibling to headset-halfgrav-acq1 (from c2/seed2) and headset-base-acq1 (1g). Warm-started from headset-halfgrav-s1's own 2M checkpoint (own-track, not a teacher/BC/motion-prior).

**gate**: Acquisition milestone at OWN physics (0.5g) + heading: 20s held-out episodes across the 3-heading set, >=0.03 m/s median net forward along each commanded heading, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: continue/realign if still climbing at cutoff rather than an auto-fail.

**verdict**: Result: cleanest heading-acquisition read of the whole campaign -- 24/24 gait_valid across all 4 scenarios (walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto), ZERO sacrificed legs in every single episode (sac=[] all 24), 0/24 falls/terminations. Evidence: gate report (logs/ckpt_eval/cw_walkscratch_easy0905_headset_halfgrav_s1acq_gate/report.json), 40.37M steps, ep_rew_mean 543.7 (quarters 262.6/489.7/516.1/545.3, still gently rising not yet plateaued). Speed clears the >=0.03 m/s bar comfortably every episode (fwd_dist_m med 3.09-3.46m/20s = 0.15-0.17 m/s), slip_per_m med 2.28-2.48 across all 4 scenarios (inside the 2.9 teacher band with margin, better than every sibling base/halfgrav PASS this campaign which ran 3.0-5.2). height_err_end_mm ~10mm (no belly drag). Video (walk_det_0_sheet.png, walk_startjitter_det_0_sheet.png) confirms real six-leg lift/place cycling even under perturbed-start det, the ONE scenario where every sibling in this family (base-acq1, base-s0c1/s1c1-acq1, halfgrav-acq1) showed leg1/4 favoritism -- this seed clears it cleanly. Why: own-checkpoint 40M acquisition continuation off headset-halfgrav-s1's already-clean 2M canary (24/24 gait_valid at 2M too), same recipe as sibling headset-halfgrav-acq1/headset-base-acq1, no new mechanism. Next: this is the 2nd of 3 planned halfgrav-family acq1 seeds (halfgrav-acq1 PASS, s1acq PASS, s3acq still evaluating) -- once s3acq lands, halfgrav reaches the same n=3 confirmation base already has, and a family champion can be picked for the next rung (irregular-timing hardening, already canary-testing as headset-halfgrav-irr-c1).

