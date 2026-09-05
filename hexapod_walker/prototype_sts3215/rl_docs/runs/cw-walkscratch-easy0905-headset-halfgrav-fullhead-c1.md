# cw-walkscratch-easy0905-headset-halfgrav-fullhead-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T16:40:32+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-acq1

**wandb_id**: xiajh8ja

**hypothesis**: Same widened 8-way heading-set rung as the 1g sibling (headset-base-fullhead-c1), applied to the 0.5g halfgrav champion -- tests whether the wider/reversal heading set generalizes at the easier gravity cell too, same no-new-reward-code mechanism.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature reversal-gait at this checkpoint. 2M canary: env/v_along_cmd_m_s stays positive through the back half; ep_rew_mean rises or holds vs the champion's own 3-way trajectory; no early behavioral impossibility. PASS licenses a 40M acquisition continuation on the wide set; FAIL means reversal headings need their own pricing/curriculum step before further spend.

