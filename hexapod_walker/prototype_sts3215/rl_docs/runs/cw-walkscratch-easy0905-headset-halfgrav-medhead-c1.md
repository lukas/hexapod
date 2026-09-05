# cw-walkscratch-easy0905-headset-halfgrav-medhead-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T17:27:26+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-acq1

**wandb_id**: uxuboegj

**hypothesis**: Plain English: same question as the base(1g) sibling medhead-c1 but on the halfgrav(0.5g) family — does its small-3-way-heading champion generalize to the 5-way quarter-turn-only set, given its own full-8-way jump (headset-halfgrav-fullhead-c1) also CANARY FAILED (v_along~0.01m/s, reward -125->-587 monotonically worsening)? bank: 5 new test_easy_heading_med_* tests in test_walkscratch_easy_pilot.py, 37/37 green.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait at this checkpoint. 2M canary: env/v_along_cmd_m_s must clear an actual positive value (not pinned at the ~0.01m/s noise floor the failed 8-way jump showed) through the back half; ep_rew_mean must rise or hold (not the monotonic -125->-587-style collapse the 8-way jump showed); no early behavioral impossibility. PASS licenses a 40M acquisition continuation on the medium set (and re-attempting the full 8-way set AFTER this rung, not before); FAIL means even the quarter-turn-only widening needs its own curriculum step before further spend.

