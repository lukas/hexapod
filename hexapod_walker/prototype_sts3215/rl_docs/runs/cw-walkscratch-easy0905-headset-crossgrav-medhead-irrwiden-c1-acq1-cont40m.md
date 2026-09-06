# cw-walkscratch-easy0905-headset-crossgrav-medhead-irrwiden-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T11:59:59+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-irrwiden-c1-acq1

**wandb_id**: olwjwk51

**hypothesis**: Plain English: does the irr-then-widen composite (irr-timing jitter composed before the 8-way heading widen, on the medhead crossgrav source) stay clean over a SECOND 40M block (80M cumulative, true continuation via --init-from-source), the same endurance question already answered for every per-axis DR arm and several other composition-line sources? Its own 40M ACQ read is already clean (22/24 gait_valid: 5/6 det, 5/6 sto, 6/6 startjitter/det, 6/6 startjitter/sto, 0 falls) -- per the campaign's cleanliness-margin-predicts-endurance rule this is a strong cont40m candidate, and it forms a matched composition-order pair with the sibling widenirr-c1-acq1-cont40m launched the same cycle.

**gate**: PASS/HOLDS if gait_valid stays majority (>=18/24, ideally close to its own 22/24) with 0 falls and no NEW chronic single-leg pattern emerges (the parent's scattered det/sto flags were non-chronic, no leg repeating across most episodes). FAIL/entrenches if gait_valid drops materially, a fall appears, or a chronic single-leg sacrifice consolidates -- would be the first composition-line source to fail cont40m endurance despite a clean 40M ACQ read.

**verdict**: HARDENING PASS/IMPROVES: +40M more steps (80M cumulative) on the irr-then-widen composite (irr-timing first, then widen) IMPROVES on its own 40M parent. Parent (medhead-irrwiden-c1-acq1, ACQ_PASS) had 22/24 gait_valid with 2 flagged leg5 episodes (walk/det ep3, walk/sto ep5) and a slip/m outlier up to 17.07 (walk_startjitter/sto ep5). This cont40m read: 24/24 gait_valid across all 4 panels (6/6 every mode), 0 falls/terminations in all 24 episodes, sac=[] on EVERY episode -- both of the parent's own leg5 flags are now clean, no new chronic single-leg pattern anywhere, and the slip outlier resolves (max now 8.02 vs parent's 17.07; every mode's slip range tightens). Reward still rising every quarter (217->538->729->953). Video (walk_sto_0 contact sheet) confirms upright six-leg walking through multiple heading changes, no drag/collapse/flag leg. Composition-order question (irrwiden vs widenirr) is now closed at cont40m scale: BOTH orders independently improve on their own 40M parent to the identical 24/24-perfect/sac-empty shape -- composition order does not matter for this axis pair's cont40m durability.

