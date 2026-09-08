# cw-assistfade-rung3-legdutyratio-loadslip-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-08T13:15:17+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-assistfade-rung3-legdutyratio-s0

**wandb_id**: 79qjdx57

**hypothesis**: Does directly pricing per-leg relative load-slip (the physical symptom -- how fast a foot slides while loaded, peer-excluded MEDIAN ratio, target 1.5, charge 150) on top of the already-on duty-ratio charge fix rung3's chronic leg-sacrifice-plus-drift FAIL, where the swing-count-floor add-on already failed (CANARY FAIL - MECHANISM both seeds)? This is a genuinely different mechanism from the swing-floor: a continuous physically-direct measurement of the actual bad symptom (slip while loaded), not a binary swing-count gate. Bank-tested (9 new unit tests incl. a regression test for a mean-vs-median false-positive bug caught by a real-physics probe; 26+8 neighboring-mechanism family tests green; full-file collection 408 tests clean). Same seed0/blend-schedule/log-std-anneal/random-weight-init as the matched legdutyratio-s0 sibling (which already has the duty-ratio charge on), only the new load-slip charge added on top -- directly comparable to the already-closed swingfloor-s0 sibling using the identical base.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. (a) post-grace env/walk_leg_loadslip_ratio_excess and env/reward_walk_leg_loadslip_ratio must appear, finite, in real GPU telemetry -- if never engaged, CANARY FAIL - INFRASTRUCTURE not a mechanism verdict. (b) zero new falls/terminations vs the matched legdutyratio-s0 sibling (bare duty-ratio charge only). (c) per-leg duty/slip comparison vs BOTH the bare legdutyratio-s0 sibling and the already-FAIL swingfloor-s0 sibling: PASS-if the chronically-planted leg's own slip (not just duty) measurably narrows without a new gait_valid regression or slip/current worsening in the held-out walk/det+sto panel; FAIL-MECHANISM if statistically indistinguishable from the legdutyratio-s0 baseline or outright worse (mirrors the swingfloor arm's own verdict criteria for a clean side-by-side read of the two rejected/tried per-leg add-ons).

**verdict**: CANARY FAIL - MECHANISM: per the gate's own explicit clause, the held-out walk/det+sto panel is OUTRIGHT WORSE than the matched legdutyratio-s0 (bare duty-charge) sibling, not narrowed. walk/det slip med 12.67->17.06m (worse), walk/sto slip med 16.71->17.30m (worse); prog med down in both (0.14->0.11, 0.11->0.10); gait_valid unchanged at 6/6 in both walk groups so this is a straight slip regression, not a sacrifice trade. walk_startjitter/det gait_valid does improve (2/6->5/6, terms 5->2) and sto ticks up (1/6->2/6) but the gate names the walk/det+sto panel as the primary read and that got worse, so startjitter doesn't rescue it. Gate (a) telemetry: env/walk_leg_loadslip_ratio_excess and env/reward_walk_leg_loadslip_ratio both finite/engaged from ~step366 onward (excess 0.02-0.08, ratio climbing 4.0->5.9) -- satisfied. Gate (b) zero new falls: satisfied (candidate has fewer startjitter/det terms than baseline, 2 vs 5). Training-side: ep_rew_mean ends deeply negative (-801) vs the baseline's own +62, but both arms share the SAME background trend (the pre-existing walk_loadslip_gate/k_loadslip_excess mechanism's cumulative slip/progress ratio climbs 0->~5-6x over training in BOTH arms, zeroing most walk income by the end in both) so raw reward collapse alone isn't diagnostic -- the eval-panel comparison above is what decides this. What's next: same charge=150/target=1.5 parameterization is training on the s1 sibling and on 3 walkcurr seeds (crutchoff-{s0,s1,s2}-widen8-legdutyratio-loadslip; this cycle's walkscratch-s0 read shows a milder but consistent non-improving pattern) -- flag both for whoever reads s1/the walkcurr trio: don't fund a dose/lineage variant of the same parameterization without checking whether a lower charge or a bounded worst_excess changes the outcome; the 'price load-slip directly' idea itself is not refuted, this instantiation on rung3 is.

