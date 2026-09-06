# cw-walkscratch-easy0905-headset-crossgrav-widen2c2b-abrupt-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-06T02:07:58+00:00

**pod**: hexapod-mjx-train-5

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-widen2c2b-abrupt-c1

**wandb_id**: 3fth45t0

**hypothesis**: Plain English: can a FULL training budget at 1g repair a leg-1-entrenched policy, or is source leg-health necessary at every budget? The 2M negative-control canary (widen2c2b-abrupt-c1, FAIL-INFORMATIVE) showed the leg-1-parked attractor inherited from the unhealthy widen2-c2b-acq1 source survives 2M at 1g — nominal-start walking looks repaired (walk/det 4/6 gv) but start-jitter reverts to chronic leg-1 sacrifice (5/6 episodes duty<0.10), while all four leg-healthy-source siblings show 0/24 sacrifices at the same budget. This 40M acquisition-scale continuation (same template as medhead-abrupt-c1-acq1) answers the remaining fork: if 40M fully repairs the attractor, unhealthy champions become usable crossgrav seeds and 1g training becomes an entrenchment-repair path; if entrenchment persists, source health is necessary at all budgets and the negative-control story closes cleanly.

**gate**: Controlled follow-up, informative either way. EXPECTED/PERSISTS if walk_startjitter/det (and/or /sto) still shows chronic leg-1 sacrifice (duty<0.10) in a majority of episodes at 40M — confirms source leg-health is necessary at all budgets; closes the fork. SURPRISING/REPAIRS if the full 24-ep panel reaches the healthy-sibling profile: leg-1 sac 0/24, walk/det AND walk/sto >=4/6 gait_valid, startjitter/det majority gait_valid, 0 falls — would establish 1g long-budget training as a genuine entrenchment repair path needing confirmation on a second unhealthy source. CONTINUE per 08-21 ruling only if reward still climbing with borderline (not hard-parked) leg-1 duty.

**verdict**: ACQ FAIL - MECHANISM (negative control confirms: BUDGET does NOT repair an unhealthy-source crossgrav champion). This 40M continuation of the pre-registered negative control (warm-started from the already-leg-1-parked-at-source widen2-c2b-acq1, itself ACQ FAIL at native 0.5g) resolves the fork its own 2M canary left open. Aggregate gait_valid 14/24 -- numerically IDENTICAL to the 2M canary's own 14/24 -- with the SAME leg-1 chronic fingerprint: walk_startjitter/det collapses to 2/6 (leg-1 flagged in 4/6 episodes), walk_startjitter/sto 2/6 (leg-1 in 3/6, leg-5 in 1/6), walk/det 4/6 (2 mild transient flags), walk/sto clean 6/6. 0 falls/terminations in all 24 episodes; training reward quarters -802->-1085->-780->-452 (net rising in the back half, the widen2-lineage's known reward-scale trait, not flat) -- per CURRENT_TRUTHS this specific reward-misalignment class (leg-1/4 structural entrenchment) is ALREADY CLOSED after 9 independent repair mechanisms with the established fix being STRUCTURAL, so reward-rising-with-bad-eval here is read as continued entrenchment, not an 08-21 keep-going case (more training is what produced/sustained it, exactly as CURRENT_TRUTHS predicts). Video (walk_startjitter_det_3, 8-frame strip) confirms genuine body translation even in the flagged episode -- a favoritism issue, not a freeze/paddle. CLOSES the residual fork cleanly: leg-health-at-source is necessary for crossgrav-transfer repair and 40M of further ACQ budget cannot substitute for it. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_widen2c2b_abrupt_c1_acq1_gate/report.json vs the 2M canary's own cw_walkscratch_easy0905_headset_crossgrav_widen2c2b_abrupt_c1_gate/report.json, W&B 3fth45t0.

