# cw-walkscratch-easy0905-headset-base-fullhead-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T16:39:16+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-acq1

**wandb_id**: a0zu90u6

**hypothesis**: Widening goal.walk_heading_set from the small {0,+45,-45} 3-way set to the full 8-way compass (adds +-90,+-135,180, including reversal) is the ladder's next rung after the small-set heading pass; k_walk_freeprog needs no new pricing, this only tests whether the already-heading-tracking base(1g) champion generalizes to the wider/reversal set without new reward code. bank: 5 new test_easy_heading_wide_* tests in test_walkscratch_easy_pilot.py, 32/32 green.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature reversal-gait at this checkpoint. 2M canary: env/v_along_cmd_m_s stays positive (not collapsing to near-zero) through the back half; ep_rew_mean rises or holds (not a collapse vs the champion's own 3-way trajectory); no early behavioral impossibility (e.g. every episode falling in the first 2s). PASS licenses a 40M acquisition continuation on the wide set; FAIL means reversal headings need their own pricing/curriculum step before further spend.

