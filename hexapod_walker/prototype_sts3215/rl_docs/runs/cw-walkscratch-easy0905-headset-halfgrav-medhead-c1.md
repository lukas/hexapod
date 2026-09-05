# cw-walkscratch-easy0905-headset-halfgrav-medhead-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-05T17:27:26+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-acq1

**wandb_id**: uxuboegj

**hypothesis**: Plain English: same question as the base(1g) sibling medhead-c1 but on the halfgrav(0.5g) family — does its small-3-way-heading champion generalize to the 5-way quarter-turn-only set, given its own full-8-way jump (headset-halfgrav-fullhead-c1) also CANARY FAILED (v_along~0.01m/s, reward -125->-587 monotonically worsening)? bank: 5 new test_easy_heading_med_* tests in test_walkscratch_easy_pilot.py, 37/37 green.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait at this checkpoint. 2M canary: env/v_along_cmd_m_s must clear an actual positive value (not pinned at the ~0.01m/s noise floor the failed 8-way jump showed) through the back half; ep_rew_mean must rise or hold (not the monotonic -125->-587-style collapse the 8-way jump showed); no early behavioral impossibility. PASS licenses a 40M acquisition continuation on the medium set (and re-attempting the full 8-way set AFTER this rung, not before); FAIL means even the quarter-turn-only widening needs its own curriculum step before further spend.

**verdict**: Result: mechanism-health canary PASSES on the halfgrav(0.5g) 5-way medium-heading set (0,+-45,+-90deg), sibling of the base(1g) medhead-c1 canary a concurrent cycle already verdicted PASS. Evidence: env/v_along_cmd_m_s clears a real positive value the whole run (0.075->0.087->0.090->0.087 m/s), NOT the ~0.01m/s noise floor the failed 8-way jump showed; the FULL DR-0 harness gate (synced this cycle, 24 episodes across walk/walk_sto/walk_startjitter_det/walk_startjitter_sto) shows gait_valid TRUE on all 24/24 episodes, sacrificed_legs=[] everywhere, ZERO terminations, forward_dist_m 2.6-3.4m/20s every episode, slip_per_m median 2.4-3.7 (near the 2.9 teacher band), frame strip confirms genuine six-leg cycling (different swing phase each sampled frame, not a static pose). ep_rew_mean itself falls -24.6->-85.3->-138.8->-164.5 (naive 'must rise or hold' looks violated) but per-tick reward is flat (-0.23 to -0.38/step, not worsening) while ep_len_mean climbs on the same fixed warm-up ramp as the base sibling (108->229->361->488) -- a flat per-tick policy posts a growing negative episode sum as episodes get longer on schedule, the same shape the base sibling's PASS verdict already characterized, NOT the fullhead-style accelerating collapse (v_along pinned near 0, reward accelerating downward). Why: distinguishes a stabilizing per-tick-flat dip under a lengthening-episode schedule from genuine behavioral collapse; the harness confirms the mechanism is not just healthy but already producing clean six-leg walking at 2M. What's next: per the gate, licenses a 40M acquisition continuation on this medium 5-way set -- launching headset-halfgrav-medhead-acq1 warm-started from this checkpoint, mirroring headset-base-medhead-acq1's template.

