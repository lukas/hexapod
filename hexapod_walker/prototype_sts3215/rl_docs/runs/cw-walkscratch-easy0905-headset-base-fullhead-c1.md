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

**verdict**: CANARY FAIL - MECHANISM: full 8-way heading set (incl. reversals) does NOT generalize on the base(1g) family within a 2M canary. Evidence: 4-checkpoint W&B training-rollout trend under the SAME wide walk_heading_set/cmd_resample_s=6.0 the harness gate re-evaluates: env/v_along_cmd_m_s pinned near-zero the whole run (0.011->0.011->0.013->0.009 m/s, never departs the noise floor vs the 0.06 m/s target), env/walk_direction_err_deg stays ~86deg (near-perpendicular to command) and wrong_way~43-46% of steps throughout, while ep_rew_mean falls monotonically and hard (-122->-296->-482->-556, each quarter worse) driven by the walk_freeprog penalty (score~-0.7, pen~-2.2..-2.5) accumulating over episodes that get LONGER not shorter (ep_len_mean 108->488) -- i.e. it stopped falling as often but never learned to move toward ANY of the new headings, so the per-step progress penalty racks up over the longer episodes. This is the pre-registered canary FAIL condition verbatim (ep_rew_mean does not rise/hold; v_along collapses to/stays near-zero) -- not the 08-21 rising-reward/bad-eval continue case, reward is genuinely worsening throughout. Session composite eval corroborates instability (fwd/left/right all FELL over_current/tilt_pitch in the stitched stand->walk->sit probe). Harness DR-0/own-DR walk-mode gate was found still genuinely computing on its own pod (orphaned-supervisor sync gotcha) -- backgrounded pollreap started for video/gait_valid corroboration, but the training-rollout signal alone is unambiguous and matches the ledger's own pre-registered W&B rubric. Per this arm's own hypothesis: FAIL means reversal/wide headings need their own pricing or curriculum-widen step (e.g. gradually expanding heading set rather than jumping 3-way->8-way in one hop) before further spend on this exact 8-way jump.

