# cw-walkscratch-easy0905-headset-halfgrav-irr-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: HARDENING FAIL

**created**: 2026-09-06T12:12:23+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irr-acq1

**wandb_id**: nildfnf2

**hypothesis**: Plain English: does the halfgrav (0.5g) irregular-direction-change-timing composite (headset-halfgrav-irr, seed/canary c1) stay clean over a SECOND 40M block (80M cumulative, true continuation via --init-from-source)? Its own 40M ACQ read is ACQ PASS with 20/24 gait_valid (4/6 det, 6/6 sto, 4/6 startjitter/det, 6/6 startjitter/sto, 0 falls, scattered non-chronic leg4 flags) -- moderately clean, worth the endurance check per the campaign's standard cont40m refill pattern (queued, not launched immediately -- this cycle's 80M-step cap was already spent on the cleaner crossgrav-medhead irrwiden/widenirr pair).

**gate**: PASS/HOLDS if gait_valid stays majority (>=18/24) with 0 falls and no NEW chronic single-leg pattern (the parent's leg4 flags were scattered/non-chronic across det modes only, not sto). FAIL/entrenches if gait_valid drops materially, a fall appears, or leg4 (or another leg) consolidates into a chronic sacrifice across most episodes.

**verdict**: HARDENING FAIL/ENTRENCHES: +40M (80M cumulative) on the halfgrav irr-timing composite's ORIGINAL seed (c1) reproduces the same chronic-leg-consolidation shape its 2nd-seed sibling (halfgrav-irr2-acq1-cont40m) already showed this cycle -- gait_valid drops materially 20/24 -> 16/24, crossing below this run's own pre-registered 18/24 majority bar. The parent's leg4 flags were explicitly scattered/det-only (walk/det eps0,3 + startjitter/det ep3); at 80M leg4 now also appears in walk_startjitter/sto ep2 (paired with leg2) -- exactly the 'spreads to a mode that was previously clean' failure clause named in this run's own gate text -- while startjitter/det collapses from 4/6 to 2/6 (3 of the 4 newly-flagged episodes carry leg4). 0 falls/terminations either side (not a safety failure), and ep_rew_mean keeps climbing every quarter (630.3/1171.9/1271.1/1342.5) -- the SAME reward-rises-while-a-leg-entrenches duration effect already corroborated 4x this cycle-window (base-acq1, base-s1c1-acq1, halfgrav-medhead-acq1, halfgrav-irr2-acq1 cont40m), now a 5th confirmation and specifically a 2-SEED confirmation that this failure is composition-wide (irr-timing + halfgrav), not seed-specific: both the c1 (this run) and c2 (irr2, already FAILed) seeds of the same recipe consolidate the identical leg (leg4) at cont40m scale despite only mild/scattered flags at 40M. Per the 08-21 ruling this is a genuine misalignment corroboration, not a budget ceiling -- but per this composite's own pre-registered gate text ('leg4 consolidates into a chronic sacrifice' = FAIL), this closes as FAIL regardless of the still-rising reward. Champion for this lineage stays the 40M headset-halfgrav-irr-acq1 checkpoint (ACQ PASS, 20/24, leg4 only scattered/det-only), not this continuation. No further irr-timing-halfgrav cont40m spend on either seed. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_halfgrav_irr_acq1_cont40m_gate/report.json vs ..._acq1_gate/report.json (per-episode leg/duty diff), W&B nildfnf2.

