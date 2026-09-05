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

**verdict**: CANARY FAIL - MECHANISM: same fate as the sibling base(1g) arm -- full 8-way heading set does NOT generalize on the halfgrav(0.5g) family either within a 2M canary. Evidence: 4-checkpoint W&B training-rollout trend under the same wide walk_heading_set/cmd_resample_s=6.0: env/v_along_cmd_m_s pinned near-zero throughout (0.009->0.012->0.013->0.010 m/s vs 0.06 m/s target), ep_rew_mean falls monotonically and hard (-125->-300->-528->-587, each quarter worse), reward_walk_freeprog_pen ~-2.5..-2.8 the whole run. This is the pre-registered canary FAIL condition (ep_rew_mean does not rise/hold) -- reward genuinely worsening, not the 08-21 rising-reward continue case. Session composite eval corroborates instability (fwd/left/right all FELL tilt_pitch/over_current). Harness gate found still genuinely computing on its own pod (orphaned-supervisor sync gotcha); backgrounded pollreap started for corroboration, but same W&B rubric applies and is unambiguous. Closes the fullheading rung 2/2 (both non-gSDE families) for the bare k_walk_freeprog mechanism jumping directly to the full 8-way set -- next step is a curriculum-widen (intermediate heading subsets) or explicit reversal pricing, not a repeat of this exact jump on either family.

