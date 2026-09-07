# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-speedwiden

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-07T09:20:01+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-acq1

**wandb_id**: n3v0o8fy

**hypothesis**: Plain English: does the crutch-off full-DR composite still walk cleanly when the commanded speed varies episode-to-episode (0.03-0.12 m/s) instead of staying fixed at 0.06? The reward mechanism needed to make that widening meaningful (reward.walk_freeprog_cap_dynamic: raises the freeprog cap to max(fixed_cap, per-episode commanded speed) instead of a single fixed 0.06 scalar that made command magnitude reward-invisible) is new this cycle, bank-proven bit-exact-off + correctly differentiating command magnitude (test_walkcurr_item4_cap_dynamic_*, 4/4 green, WALKCURR_ITEM4_BARE bank 18/18 green). Single axis, matched parent (this seed's own ACQ-PASSED 40M crutch-off checkpoint), same gate style as the sibling widen8/irr canaries. Prediction-if-true: 0 or near-0 falls across 24 held-out episodes (panel now samples the same widened speed band), gait_valid majority (>=18/24), no new chronic single-leg sacrifice. Prediction-if-false: falls or a chronic leg sacrifice appear specifically at the speed extremes (0.03 or 0.12), or the newly speed-visible reward destabilizes the gait the fixed-cap diet had already converged on.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY (2M): held-out gate on own cfg (widened 0.03-0.12 m/s command speed band, 5-heading medium set, det+sto, walk+walk_startjitter, 24 eps). PASS if 0 falls/terminations AND gait_valid >=18/24. FAIL if any fall or chronic (<0.10-duty every episode) single-leg sacrifice.

**verdict**: CANARY PASS: speed-range widening composes cleanly, 3rd seed. Evidence: 24/24 episodes, gait_valid 21/24, 0 terminations -- essentially identical to this seed's own s2-acq1 baseline (21/24 gv, 0 terms), sac confined to walk_startjitter/sto leg0/leg2/leg5, matching the parent's own scattered pre-existing signature. Why: clean composable pass, 3/3 seeds now clean -- closes the speedwiden canary trio. Next: license the ACQ (40M) continuation, completing the 3-seed set.

