# cw-walkscratch-crutchoff-s1-widen8-loadslip-target6-cap02-alone

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS - MECHANISM HEALTHY

**created**: 2026-09-08T16:00:02+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-crutchoff-s1-widen8-loadslip-target6-alone

**wandb_id**: fdlnjsga

**hypothesis**: Seed1 twin of the s0 capped-excess arm launched this same window: does reward.walk_leg_loadslip_ratio_excess_cap=0.2 keep the reward-collapse bounded and let efficacy clear >=3/4 groups on a second seed, replicating whatever the s0 cap arm finds.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as the s0 cap-02 twin: PASS-worth-CONTINUE if reward stays bounded (no order-of-magnitude collapse vs s1-alone's own [48.7,122.3,-1382.1,-10490.3]) AND >=3/4 groups jointly improve vs the s1 widen8-acq1 baseline with 0 new falls. Read together with the s0 twin before drawing either a PASS or FAIL conclusion on the cap mechanism.

**verdict**: CANARY PASS - MECHANISM HEALTHY (efficacy still open) -- CROSS-SEED REPLICATION of the s0 cap-02 twin, and together these two CLOSE the capped-excess lever. Reward quarters [47.8,129.6,119.4,-160.4] closely mirror s0's own [58.1,110.9,89.4,-157.9] -- no order-of-magnitude collapse, confirming the cap fixes the reward-scale pathology on a second seed. But efficacy vs the matched s1-widen8-acq1 baseline is the same noise-level/mixed picture as s0: walk/det slip 7.80->8.00 (worse) fwd 0.20->0.27m (better); walk/sto slip 7.27->6.66 (better) fwd 0.87->0.83m (~flat); walk_startjitter/det slip 8.51->8.01 (better) fwd 0.49->0.55m (better) -- the one clear joint-improve group; walk_startjitter/sto slip 9.74->9.97 (worse) fwd 0.41->0.36m (worse) -- clear joint-worse. 1/4 groups clearly improve, 1/4 clearly worse, 2/4 mixed -- same 0-1/4-clears-the->=3/4-bar shape as s0. 0 new falls, contact sheet shows real forward translation. COMBINED CONCLUSION (both seeds now read, matching this campaign's own 'two arms agreeing' precedent): the reward.walk_leg_loadslip_ratio_excess_cap=0.2 mechanism is confirmed MECHANISM-HEALTHY on both seeds but neither clears the pre-registered >=3/4-groups efficacy bar -- CLOSES the capped-excess repair (and with it the whole loadslip-ratio-charge investigation line: dose 150/45/15, target recalibration 1.5->6.0, confound-isolation, and now excess-capping have all been tried on this lineage and none produces >=3/4-groups efficacy on any seed tested). Per the open lead this file and assistfade's own 09-07 finding both already named: further spend needs a GENUINELY DIFFERENT per-leg mechanism design (e.g. a positive swing-initiation income for the currently-most-loaded leg instead of an excess-above-target charge, or a mechanism that targets the fully-planted/no-swing PATTERN directly rather than a scalar ratio threshold), not another dose/target/cap variant of the same charge shape. Updating walkcurr STATUS.md with this synthesis; flagging for a dig-in redesign session before further training spend on this exact charge family.

