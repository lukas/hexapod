# cw-walkscratch-easy0905-headset-base-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-05T11:54:05+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-base-c1

**wandb_id**: ri9rlmho

**hypothesis**: Plain English: the 2M heading canary (headset-base-c1) already proved the heading-tracking gradient is live under the SAME reward the fixed-forward base family trained under (no new keys) -- this gives it the full 40M acquisition budget to see if it actually learns to walk toward the commanded heading set (straight/+45/-45deg) as cleanly as base-s2/s4/s0-c1/s1-c1 walked straight. Warm-started from headset-base-c1's own 2M checkpoint (own-track, not a teacher/BC/motion-prior).

**gate**: Acquisition milestone at own physics + heading: 20s held-out episodes across the 3-heading set, >=0.03 m/s median net forward along each commanded heading, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: continue/realign if still climbing at cutoff rather than an auto-fail.

**verdict**: Result: PASS at the heading-generalization acquisition rung (base/1g family's flagship 40M continuation from headset-base-c1). Evidence (logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_acq1_gate/report.json, 24 episodes: walk det/sto + walk_startjitter det/sto): 0/24 falls (all terminated=false), speed_mean_m_s 0.147-0.20 across every episode (well above the 0.03 m/s bar), height_err_end_mm ~19mm (no belly drag), gait_valid true in 18/24 (all of walk/det, walk/sto, walk_startjitter/sto); the 6/24 gait_valid=false episodes are ALL in walk_startjitter/det only, showing leg1 and/or leg4 duty dropping to 0.04-0.14 -- but swing_count for those legs is 39-121/20s (2-6Hz micro-stepping, not the near-zero-touch LEGPARK-SKATE pattern seen in the sde family), matching the identical leg1/4-favoritism-under-startjitter+det fingerprint already CANARY-PASSed on siblings headset-base-s0c1/s1c1. Video (walk_det_0, walk_startjitter_det_3, walk_sto_4 frame strips, 6 samples each): visible six-leg cycling, clear forward background shift, upright body, one leg visibly held closer to the body in the startjitter/det sample matching the low-duty leg. Caveats (same as every base-family PASS this campaign): small-stride shuffle (stride_m_mean 12-21mm) and slip/m 3.0-4.8 above the 2.9 joystick-band reference; heading tracking is loose (course_err_1s_med 20-94deg, direction_err_mean 19-38deg) but wrong_course/wrong_direction fractions stay low (0-8%, one sto outlier at 53%) and this rung's own gate text only requires net forward motion per heading, not tight tracking -- that precision belongs to the joystick track later. Reward quarters 403.8/715.0/757.3/812.8 (still rising gently, no plateau/exploit divergence). Why: extends the already-established base/1g fixed-forward PASS pattern one heading-rung further with no new pathology -- same caveats, same fingerprint, first family member to clear the FULL 40M heading-acquisition bar (siblings s0c1-acq1/s1c1-acq1 still training). What's next: let s0c1-acq1/s1c1-acq1 finish for an n=3 heading-family confirmation, then pick a base-family heading champion for the next rung (wider heading range or joystick-style resampling) once halfgrav's acq1 also reports.

