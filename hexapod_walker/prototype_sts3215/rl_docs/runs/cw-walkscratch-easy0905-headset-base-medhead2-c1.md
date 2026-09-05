# cw-walkscratch-easy0905-headset-base-medhead2-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T18:25:58+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-medhead-c1

**wandb_id**: n0ostk9i

**hypothesis**: Seed-robustness check for the medium 5-way heading rung (0,+-45,+-90deg) on the base(1g) family: medhead-c1 (warm-started from headset-base-s1c1-acq1) already CANARY PASSED (harness-confirmed six-leg gait, v_along clears the noise floor). This launches the SAME 2M canary recipe from a DIFFERENT already-existing base heading champion (headset-base-acq1, the original seed, never yet tried on this rung) to confirm the medhead-widen step generalizes across seeds before the campaign calls the rung closed, mirroring the n>=2 seed-confirmation pattern already used for every other rung in this campaign (irr-timing, fullhead, small-heading).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, same bar as medhead-c1: env/v_along_cmd_m_s must clear a real positive value (not the ~0.01m/s noise floor the failed 8-way jump showed) through the back half; harness gait_valid majority with no chronically-parked leg is the stronger corroborating signal (per medhead-c1's own correction). PASS licenses its own 40M acquisition continuation; FAIL on this second seed would mean the rung is champion-specific, not general, and needs revisiting before more acq spend.

