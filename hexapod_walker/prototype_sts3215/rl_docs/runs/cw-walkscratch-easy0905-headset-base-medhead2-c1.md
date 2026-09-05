# cw-walkscratch-easy0905-headset-base-medhead2-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-05T18:25:58+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-medhead-c1

**wandb_id**: n0ostk9i

**hypothesis**: Seed-robustness check for the medium 5-way heading rung (0,+-45,+-90deg) on the base(1g) family: medhead-c1 (warm-started from headset-base-s1c1-acq1) already CANARY PASSED (harness-confirmed six-leg gait, v_along clears the noise floor). This launches the SAME 2M canary recipe from a DIFFERENT already-existing base heading champion (headset-base-acq1, the original seed, never yet tried on this rung) to confirm the medhead-widen step generalizes across seeds before the campaign calls the rung closed, mirroring the n>=2 seed-confirmation pattern already used for every other rung in this campaign (irr-timing, fullhead, small-heading).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, same bar as medhead-c1: env/v_along_cmd_m_s must clear a real positive value (not the ~0.01m/s noise floor the failed 8-way jump showed) through the back half; harness gait_valid majority with no chronically-parked leg is the stronger corroborating signal (per medhead-c1's own correction). PASS licenses its own 40M acquisition continuation; FAIL on this second seed would mean the rung is champion-specific, not general, and needs revisiting before more acq spend.

**verdict**: CANARY PASS (mechanism-health, second-seed confirmation). env/v_along_cmd_m_s clears the noise floor cleanly (0.065-0.075 m/s through the whole run, vs the ~0.01 noise floor the failed 8-way jump showed). Harness gate confirms real six-leg walking: walk/det 6/6 gait_valid (fwd med 2.97m/20s, slip med 4.40), walk/sto 6/6 gait_valid (fwd med 2.84m), walk_startjitter/sto 5/6, walk_startjitter/det weaker at 1/6 (legs 1/4 flagged in some but not all episodes -- not a chronic single-leg sacrifice, matches the corroborating-signal bar the gate names). Frame strip (walk_det_0_sheet.png) shows genuine six-leg cycling with legs at varied swing/stance phase, no dragging/parked leg visible. This is a DIFFERENT base-family champion lineage (warm-started from headset-base-acq1, the original seed) than headset-base-medhead-c1 (warm-started from s1c1-acq1) -- confirms the medium 5-way heading rung generalizes across at least 2 independent base-family seeds, not champion-specific. Launching the 40M acquisition continuation per the gate's own PASS clause, mirroring headset-base-medhead-acq1's template.

