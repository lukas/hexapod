# cw-walkscratch-easy0905-headset-base-medhead-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T17:25:17+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-acq1

**wandb_id**: qxewuqw2

**hypothesis**: Plain English: does the base(1g) small-3-way-heading champion generalize to a 5-way set that adds only the two quarter-turns (+-90deg) it never saw, WITHOUT the reversal directions (+-135/180) that the full 8-way jump (headset-base-fullhead-c1) just CANARY FAILED on (v_along pinned ~0.01m/s, direction_err~86deg, reward -122->-556 monotonically worsening)? Per the operator's own staged-heading-curriculum ruling (never jump straight to a wide/full range) this is the missing intermediate rung, not a repeat of the failed jump. bank: 5 new test_easy_heading_med_* tests in test_walkscratch_easy_pilot.py, 37/37 green.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait at this checkpoint. 2M canary: env/v_along_cmd_m_s must clear an actual positive value (not pinned at the ~0.01m/s noise floor the failed 8-way jump showed) through the back half; ep_rew_mean must rise or hold (not the monotonic -122->-556-style collapse the 8-way jump showed); no early behavioral impossibility. PASS licenses a 40M acquisition continuation on the medium set (and re-attempting the full 8-way set AFTER this rung, not before); FAIL means even the quarter-turn-only widening needs its own curriculum step (e.g. widen one direction pair at a time) before further spend.

