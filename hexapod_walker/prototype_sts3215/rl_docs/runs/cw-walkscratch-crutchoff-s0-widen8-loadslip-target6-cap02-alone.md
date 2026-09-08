# cw-walkscratch-crutchoff-s0-widen8-loadslip-target6-cap02-alone

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS - MECHANISM HEALTHY

**created**: 2026-09-08T15:57:05+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-crutchoff-s0-widen8-loadslip-target6-alone

**wandb_id**: 5mq94993

**hypothesis**: Plain English: the clean loadslip-ratio-charge isolation arm (s0/s1, duty-ratio-charge=0, both CANARY FAIL - MECHANISM this cycle) found the charge's own reward-quarters collapse gets WORSE without the duty-ratio confound, and traced this to the charge's unbounded worst_excess (unlike duty-ratio's shortfall, which is naturally capped at target). This arm arms the brand-new reward.walk_leg_loadslip_ratio_excess_cap=0.2 (bank-proved this cycle, test_walk_leg_loadslip_ratio_excess_cap_*, default 0=off/bit-exact) on the SAME isolated recipe (duty-ratio-charge=0, loadslip charge=150/target=6.0, init from the true pre-duty-charge widen8-acq1 checkpoint) to test whether bounding the per-tick charge (a) keeps reward from collapsing by orders of magnitude the way the uncapped isolation arm did, and (b) lets the >=3/4-groups efficacy bar clear now that outlier ticks can no longer dominate the return, building on the isolation arm's own partial 2/4-groups signal (both det-mode groups improved, both sto-mode groups did not).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY, capped-excess scope. PASS-worth-CONTINUE if reward quarters do NOT show the isolation arm's own order-of-magnitude collapse (compare vs s0-alone's [53.1,109.8,-628.2,-9865.8]) AND >=3/4 of the 4 held-out groups jointly improve slip+progress vs the plain widen8-acq1 baseline with 0 new falls. PARTIAL (reward healthier but still <3/4 groups, or vice versa) = report both halves, do not force a verdict either way. FAIL if reward still collapses the same way AND efficacy stays <3/4 -- closes the capped-excess repair too, meaning the mechanism needs an even more different design (e.g. per-tick charge scaled by a fixed max regardless of measured excess, or abandoning this charge family for something that targets the fully-planted/no-swing leg pattern directly).

**verdict**: CANARY PASS - MECHANISM HEALTHY (efficacy still open, do not fund a full acquisition follow-up on this read alone). Capping the per-tick excess (reward.walk_leg_loadslip_ratio_excess_cap=0.2) fixes the reward-collapse half of the gate: reward quarters [58.1,110.9,89.4,-157.9] stay near the healthy scale end to end -- no order-of-magnitude collapse, a real repair vs the uncapped s0-alone isolation arm's own [53.1,109.8,-628.2,-9865.8]. But the bundled efficacy sub-bar (>=3/4 of 4 held-out groups jointly improve slip+progress vs the plain widen8-acq1 baseline) is NOT met: walk/det slip 7.57->7.44 but fwd 0.41->0.35m (worse); walk/sto slip 6.67->6.64 flat, fwd 1.09->1.01m (worse); walk_startjitter/det slip 7.94->7.44 (improved) fwd 0.58->0.57m (flat); walk_startjitter/sto slip 9.33->9.90 (worse) fwd 0.37->0.54m (better) -- every group is noise-level or mixed-direction, 0/4 clearly clear the bar. 0 new falls, contact sheet shows real but modest forward translation (not stationary). Per canary-scope charter (mechanism health only, not skill acquisition), status = PASS on the mechanism question the canary was built to answer; efficacy is a separate, still-open acquisition-scope question -- see OPERATOR_QUESTIONS.md 2026-09-08 for why a literal PARTIAL isn't recordable and this mapping was chosen. The seed1 twin (cw-walkscratch-crutchoff-s1-widen8-loadslip-target6-cap02-alone) finished this same window but its gate eval was not staged at this read; read it together before deciding whether to fund a longer efficacy-focused follow-up (do not relaunch, do not duplicate this verdict).

