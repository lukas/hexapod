# cw-walkscratch-easy0905-headset-crossgrav-irr2acq1-abrupt-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-06T02:34:29+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-irr2acq1-abrupt-c1

**wandb_id**: zsxkfxzz

**hypothesis**: Plain English: irr2acq1-abrupt-c1's 2M canary just PASSED (22/24 gv, 0 falls), confirming irr-timing crossgrav transfer on its 2nd independent seed. Does this hold at full 40M acquisition budget, matching the first seed's own irracq1-abrupt-c1-acq1 continuation (same template)?

**gate**: ACQ PASS if gait_valid stays majority-or-better in walk/det with no chronic single-leg sacrifice at 40M (matching or improving the 2M canary's 22/24). FAIL if it collapses toward chronic leg-1/4 sacrifice at scale.

**verdict**: ACQ FAIL - MECHANISM (recipe-level, seed-vs-recipe question now CLOSED). This 2nd independent seed of the irr-timing-first crossgrav recipe was launched specifically to test whether irracq1-abrupt-c1-acq1's ACQ-scale leg-4 entrenchment regression (14/24 gv at 40M vs 23/24 at its own 2M canary) was seed noise or recipe-level. Result: SAME regression, same leg, milder magnitude: aggregate gait_valid 17/24 at 40M vs this run's own clean 2M canary (22/24) -- walk/det (primary mode) softens 6/6->4/6, walk_startjitter/sto 6/6->3/6, walk/sto stays clean 6/6, walk_startjitter/det 6/6->4/6. Leg 4 is the sole flagged leg in all 7 low episodes (duty 0.0-0.10, swing_count as low as 1-63/ep vs 100-200+ for other legs), matching irracq1's own leg-4 fingerprint (duty 0.0-0.16) almost exactly. 0 falls/terminations in all 24 episodes; slip/m 3.2-4.9 (tight, no reversal outliers); video (walk_det_0, the sac=[4] episode, and walk_startjitter_sto_0) confirms real body translation (progress_ratio 1.5-2.0) with visible multi-leg cycling, not a freeze -- this is favoritism-under-load, not the fully chronic 0.00-0.01-every-episode structural attractor, but it is the SAME leg/direction of collapse from a clean canary that CURRENT_TRUTHS already closed as reward-shaping-resistant (9 prior repair mechanisms). Training reward rose every quarter (656.7->1207.2->1387.2->1532.2), matching the 08-21 rising-reward shape, but per CURRENT_TRUTHS this exact class is a genuine FAIL (more training is what caused the regression), not a continue case. Per the run's own pre-registered gate ('FAIL if it collapses toward chronic leg-1/4 sacrifice at scale'), this reads FAIL: 2/2 seeds of this recipe now regress from a clean 2M canary toward leg-4 favoritism at 40M ACQ -- CLOSES the seed-vs-recipe question as RECIPE-LEVEL (not seed-specific). No further seed of this exact irr-first-crossgrav-abrupt recipe should be funded at ACQ scale without a structural per-leg-utilization fix (the already-open design gap CURRENT_TRUTHS names for the sde family) -- same lesson, different lineage.

