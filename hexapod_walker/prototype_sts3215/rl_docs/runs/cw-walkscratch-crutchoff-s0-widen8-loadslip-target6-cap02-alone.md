# cw-walkscratch-crutchoff-s0-widen8-loadslip-target6-cap02-alone

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T15:57:05+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-crutchoff-s0-widen8-loadslip-target6-alone

**wandb_id**: 5mq94993

**hypothesis**: Plain English: the clean loadslip-ratio-charge isolation arm (s0/s1, duty-ratio-charge=0, both CANARY FAIL - MECHANISM this cycle) found the charge's own reward-quarters collapse gets WORSE without the duty-ratio confound, and traced this to the charge's unbounded worst_excess (unlike duty-ratio's shortfall, which is naturally capped at target). This arm arms the brand-new reward.walk_leg_loadslip_ratio_excess_cap=0.2 (bank-proved this cycle, test_walk_leg_loadslip_ratio_excess_cap_*, default 0=off/bit-exact) on the SAME isolated recipe (duty-ratio-charge=0, loadslip charge=150/target=6.0, init from the true pre-duty-charge widen8-acq1 checkpoint) to test whether bounding the per-tick charge (a) keeps reward from collapsing by orders of magnitude the way the uncapped isolation arm did, and (b) lets the >=3/4-groups efficacy bar clear now that outlier ticks can no longer dominate the return, building on the isolation arm's own partial 2/4-groups signal (both det-mode groups improved, both sto-mode groups did not).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY, capped-excess scope. PASS-worth-CONTINUE if reward quarters do NOT show the isolation arm's own order-of-magnitude collapse (compare vs s0-alone's [53.1,109.8,-628.2,-9865.8]) AND >=3/4 of the 4 held-out groups jointly improve slip+progress vs the plain widen8-acq1 baseline with 0 new falls. PARTIAL (reward healthier but still <3/4 groups, or vice versa) = report both halves, do not force a verdict either way. FAIL if reward still collapses the same way AND efficacy stays <3/4 -- closes the capped-excess repair too, meaning the mechanism needs an even more different design (e.g. per-tick charge scaled by a fixed max regardless of measured excess, or abandoning this charge family for something that targets the fully-planted/no-swing leg pattern directly).

