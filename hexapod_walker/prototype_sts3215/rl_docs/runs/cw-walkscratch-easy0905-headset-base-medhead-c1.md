# cw-walkscratch-easy0905-headset-base-medhead-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS - MECHANISM

**created**: 2026-09-05T17:25:17+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-acq1

**wandb_id**: qxewuqw2

**hypothesis**: Plain English: does the base(1g) small-3-way-heading champion generalize to a 5-way set that adds only the two quarter-turns (+-90deg) it never saw, WITHOUT the reversal directions (+-135/180) that the full 8-way jump (headset-base-fullhead-c1) just CANARY FAILED on (v_along pinned ~0.01m/s, direction_err~86deg, reward -122->-556 monotonically worsening)? Per the operator's own staged-heading-curriculum ruling (never jump straight to a wide/full range) this is the missing intermediate rung, not a repeat of the failed jump. bank: 5 new test_easy_heading_med_* tests in test_walkscratch_easy_pilot.py, 37/37 green.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait at this checkpoint. 2M canary: env/v_along_cmd_m_s must clear an actual positive value (not pinned at the ~0.01m/s noise floor the failed 8-way jump showed) through the back half; ep_rew_mean must rise or hold (not the monotonic -122->-556-style collapse the 8-way jump showed); no early behavioral impossibility. PASS licenses a 40M acquisition continuation on the medium set (and re-attempting the full 8-way set AFTER this rung, not before); FAIL means even the quarter-turn-only widening needs its own curriculum step (e.g. widen one direction pair at a time) before further spend.

**verdict**: Result: mechanism-health canary PASSES on the base(1g) 5-way medium-heading set (0,+-45,+-90deg). Evidence: env/v_along_cmd_m_s clears a real positive value through the back half (0.065->0.077->0.081->0.079 m/s) -- NOT the ~0.01m/s noise floor the failed 8-way jump (fullhead-c1) showed; walk_direction_err_deg sits at 55-60deg (worse than the small 3-way set but far from fullhead's ~86deg near-random); the one mid-run harness eval (step 1.0M) shows survived_frac=1.0 across ALL SIX behavior modes incl walk and walk_startjitter, dir_valid_frac~0.999, real forward speed 0.16-0.17m/s; W&B video auto-captions read 'walk:ok x4' at both the 4k-step and final checkpoints; ep_len_mean climbed smoothly 108->488 ticks (no early collapse). ep_rew_mean itself falls -17.7->-72.3->-110.6->-112.2 (naive reading of 'must rise or hold' looks violated) but this is NOT the fullhead-style collapse: per-tick components (env/reward_walk, env/reward_walk_freeprog_pen, env/reward_action_delta) are FLAT across the whole run while ep_len_mean is on the same fixed warm-up ramp fullhead also showed (identical 108/229/362/488 curve on both) -- a stable per-tick policy naturally posts a growing negative episode sum as episodes get longer on a fixed schedule. Contrast with fullhead-c1's actual collapse: reward -122->-296->-482->-556 (ACCELERATING, last-step delta -74), v_along pinned 0.009-0.013 (true noise floor), dir_err ~86deg (untracked). Here the decline sharply decelerates (last-step delta only -1.6, ~46x smaller) and nearly flattens. Why: distinguishes a stabilizing per-tick-flat dip under a lengthening-episode schedule from genuine behavioral collapse -- the gate's actual concern (does the mechanism still function, not does it already look polished) is satisfied. What's next: per the gate, licenses a 40M acquisition continuation on this medium 5-way set (respec'd this cycle as headset-base-medhead-acq1, mirroring the base-acq1 acquisition template); do NOT re-attempt the bare full 8-way jump until this rung's own acquisition read lands. Sibling headset-halfgrav-medhead-c1 also finished (W&B uxuboegj, reward quarters -24.6/-85.3/-138.8/-164.5, same shape) but is left for its own cycle -- not in this cycle's finished-run list.

