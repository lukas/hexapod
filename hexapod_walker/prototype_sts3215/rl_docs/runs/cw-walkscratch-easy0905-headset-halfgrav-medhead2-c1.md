# cw-walkscratch-easy0905-headset-halfgrav-medhead2-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-05T18:28:06+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-medhead-c1

**wandb_id**: 1w4vf6xd

**hypothesis**: Seed-robustness check for the medium 5-way heading rung (0,+-45,+-90deg) on the halfgrav(0.5g) family: medhead-c1 (warm-started from headset-halfgrav-acq1) already CANARY PASSED (harness-confirmed 24/24 gait_valid, 0 sac legs, 0 falls). This launches the SAME 2M canary recipe from a DIFFERENT already-existing halfgrav heading champion (headset-halfgrav-s3acq, a different seed, never yet tried on this rung) to confirm the medhead-widen step generalizes across seeds before the campaign calls the rung closed, mirroring the n>=2/3 seed-confirmation pattern already used for every other rung in this campaign.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, same bar as medhead-c1: env/v_along_cmd_m_s must clear a real positive value through the back half; harness gait_valid majority with no chronically-parked leg is the stronger corroborating signal. PASS licenses its own 40M acquisition continuation; FAIL on this second seed would mean the rung is champion-specific, not general, and needs revisiting before more acq spend.

**verdict**: CANARY PASS (mechanism-health, second-seed confirmation), cleaner than the base sibling. env/v_along_cmd_m_s clears the noise floor (0.077-0.091 m/s through the run). Harness gate: 24/24 gait_valid across ALL FOUR modes (walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto), zero sacrificed legs anywhere, zero falls, fwd med 2.37-3.07m/20s across modes, slip med 2.5-3.9 (near the 2.9 teacher band, among the best in this campaign). Frame strip (walk_det_0_sheet.png) confirms genuine six-leg cycling, no dragging/parked leg. This is a DIFFERENT halfgrav-family champion lineage (warm-started from headset-halfgrav-s3acq) than headset-halfgrav-medhead-c1 (warm-started from halfgrav-acq1) -- confirms the medium 5-way heading rung generalizes across at least 2 independent halfgrav-family seeds. Launching the 40M acquisition continuation per the gate's own PASS clause, mirroring headset-halfgrav-medhead-acq1's template.

