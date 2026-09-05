# cw-walkscratch-easy0905-headset-base-fullhead-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-05T16:39:16+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-acq1

**wandb_id**: a0zu90u6

**hypothesis**: Widening goal.walk_heading_set from the small {0,+45,-45} 3-way set to the full 8-way compass (adds +-90,+-135,180, including reversal) is the ladder's next rung after the small-set heading pass; k_walk_freeprog needs no new pricing, this only tests whether the already-heading-tracking base(1g) champion generalizes to the wider/reversal set without new reward code. bank: 5 new test_easy_heading_wide_* tests in test_walkscratch_easy_pilot.py, 32/32 green.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature reversal-gait at this checkpoint. 2M canary: env/v_along_cmd_m_s stays positive (not collapsing to near-zero) through the back half; ep_rew_mean rises or holds (not a collapse vs the champion's own 3-way trajectory); no early behavioral impossibility (e.g. every episode falling in the first 2s). PASS licenses a 40M acquisition continuation on the wide set; FAIL means reversal headings need their own pricing/curriculum step before further spend.

**verdict**: CANARY FAIL - MECHANISM (CORRECTED after harness landed, orphaned-eval reap): the harness DR-0 walk-mode gate (walk/walk_startjitter x det/sto, 24 episodes, video-confirmed) shows a MUCH more benign failure than my earlier W&B-only read implied -- CORRECTING that read. Real finding: gait_valid=True in 22/24 episodes (six legs cycling, duty 0.05-0.73, no chronic leg sacrifice), ZERO falls in any det episode and only rare falls in sto, forward_dist_m 2.3-3.4m/20s (~0.12-0.17 m/s) in every single episode, stride_m_mean ~0.011-0.016m -- this is a REAL, STABLE six-leg walking gait, not a collapse/freeze. The actual failure is course-tracking: success=0/24 (walkcurr's own bar requires vel_err_mean<=0.03 AND gait_valid; vel_err_mean fails because direction_err_mean_deg swings 28-161deg episode-to-episode as the 8-way command resamples) -- the champion tracks headings CLOSE to its original {0,+-45} training set well (best episodes: direrr 28-45deg, progress_ratio 1.3-2.2, POSITIVE return) but degrades badly toward the wider quarter-turn/reversal headings (worst episodes: direrr 95-161deg, progress_ratio negative, return down to -6000) -- i.e. partial, distance-graded generalization, not a binary break. This reconciles the W&B training-rollout read (env/v_along_cmd_m_s~0.01, ep_rew_mean falling hard): those are batch AVERAGES across all 8 resampled headings including the badly-tracked reversal ones, which drag the mean to ~0/deeply-negative even though the walking mechanism itself stays healthy. Video (walk_det_*.png contact sheets) confirms real forward translation across frames, not vibration-in-place. STILL a genuine FAIL against the pre-registered canary bar (ep_rew_mean does not rise/hold; v_along stays near the noise floor when averaged over the whole wide set) and against walkcurr's own success criterion (0/24) -- but the right characterization is 'stable six-leg gait fails to generalize course-tracking to far-off headings within 2M', not instability/collapse. This is GOOD news for the walking skill itself and confirms the medium-heading (5-way, quarter-turns only, no reversal) curriculum step already launched this cycle (headset-base-medhead-c1) is the right next rung -- it isolates whether the gap is specifically the near-reversal headings (>90deg) vs. general widening. Do not relaunch the bare 8-way jump; do not describe this arm's failure mode as falling/instability in any downstream reference.

