# cw-walkscratch-easy0905-headset-crossgrav-s1acq-irrfwd-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-06T08:16:02+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s1acq-irrfwd-c1-acq1

**wandb_id**: 8w82uq33

**hypothesis**: This checkpoint's own 40M ACQ read was a borderline PASS-flagged-for-WATCH: gait_valid held majority (20/24) but the sacrifice fingerprint SHIFTED (canary's confined single leg-4 softening widened to a leg[2,4] pair at the same episodes, and leg-4 newly appeared in a previously-clean mode). Does +40M more steps (80M total) resolve this back toward the canary's confined pattern, hold flat, or entrench further toward the campaign's named leg[1,4] chronic-sacrifice failure mode?

**gate**: PASS/HOLDS if gait_valid stays majority (>=12/24) with the leg[2,4] pattern staying CONFINED to its current episodes/modes (no 3rd mode gaining the pattern, no leg's duty going to ~0/chronic-park) and 0 falls. FAIL/ENTRENCHES if the leg[2,4] pair spreads to a new mode, any leg's duty collapses toward 0 across a majority of episodes in any mode, or a fall appears -- would confirm this composition line is on an entrenchment trajectory, not just a noisy but flat borderline.

**verdict**: FAIL/ENTRENCHES -- the pre-registered spread trigger fires: the chronic leg[2,4] sacrifice pair, confined to walk/det at the 40M parent (2 episodes, legs 2+4 always together, duty~0.01-0.08), spreads into walk/sto -- a mode that was PERFECTLY clean at parent (6/6 gait_valid, every leg's duty in the healthy 0.14-0.58 band) -- at 80M cumulative: walk/sto ep1 now shows leg[4] collapsed to duty 0.06 (vs 0.18-0.46 for the same leg across parent's 6 sto episodes), flagged sac=[4]. walk/det ep1 also gains a 3rd leg (sac now [2,4,5] vs parent's [2,4]). Aggregate gait_valid 19/24 (4 det, 5 sto, 4 startjitter/det, 6 startjitter/sto) vs parent's 20/24 -- close in raw count, but the qualitative spread-to-a-new-mode condition is exactly what this run's own gate defined as ENTRENCHES, not a raw-count read. 0 falls/terms both reads (not a safety failure). Training reward climbed every quarter throughout (651->1156->1261->1399, never plateaued) -- per the walkcurr binding triage rule ('reward rising while walk eval is flat/down = MISALIGNED, stop same-recipe continuations and audit') this is the misaligned case, not a continue-for-more-budget case: the run already got its full pre-registered 40M continuation and used it to entrench, not heal. Closes this composition line -- do NOT fund a further cont80m of s1acq-irrfwd on this recipe. This is the FIRST cont40m in the campaign's endurance-margin series to break the 'clean-at-40M predicts cont40m holds' pattern (contrast: widen2c1-irrfwd exact-hold, widenirr-c3 narrow dip, medhead-irrfwd improves, widenfwd near-hold, halfgrav-widenirr-c3 mild-degrade -- all PASS/HOLDS). Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_s1acq_irrfwd_c1_acq1_cont40m_gate/report.json (19/24, duty traces) vs .../s1acq_irrfwd_c1_acq1_gate/report.json (20/24, duty traces), W&B 8w82uq33.

