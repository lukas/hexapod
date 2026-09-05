# cw-walkscratch-easy0905-headset-halfgrav-fullhead-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-05T16:40:32+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-acq1

**wandb_id**: xiajh8ja

**hypothesis**: Same widened 8-way heading-set rung as the 1g sibling (headset-base-fullhead-c1), applied to the 0.5g halfgrav champion -- tests whether the wider/reversal heading set generalizes at the easier gravity cell too, same no-new-reward-code mechanism.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature reversal-gait at this checkpoint. 2M canary: env/v_along_cmd_m_s stays positive through the back half; ep_rew_mean rises or holds vs the champion's own 3-way trajectory; no early behavioral impossibility. PASS licenses a 40M acquisition continuation on the wide set; FAIL means reversal headings need their own pricing/curriculum step before further spend.

**verdict**: CANARY FAIL - MECHANISM (CORRECTED after harness landed, orphaned-eval reap): same corrected characterization as the base(1g) sibling -- harness DR-0 walk-mode gate (24 episodes) shows gait_valid=True 24/24 (six legs cycling, no chronic leg sacrifice), forward_dist_m 2.4-3.3m/20s in every episode, NOT a collapse/freeze. success=0/24 (vel_err_mean fails walkcurr's <=0.03 bar) because direction_err_mean_deg swings 29-144deg episode-to-episode as the 8-way command resamples -- best episodes (direrr 29-48deg, close to the original {0,+-45} set) earn POSITIVE return (406-892) with progress_ratio 1.6-2.4, worst episodes (direrr 96-144deg, near-reversal) go deeply negative (down to -6416) with negative progress_ratio. Same distance-graded generalization gap as base(1g), not instability. Reconciles the earlier W&B-only read (env/v_along_cmd_m_s~0.01, ep_rew_mean -125->-587): those are batch averages across all 8 headings including the badly-tracked reversal ones. STILL a genuine FAIL against the pre-registered canary bar and walkcurr's own success criterion -- the medium-heading (5-way, quarter-turns only, no reversal) canary already launched this cycle (headset-halfgrav-medhead-c1) is the right next rung to isolate whether the gap is specifically near-reversal headings. Do not describe this arm's failure as falling/instability downstream.

