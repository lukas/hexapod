# cw-assistfade-rung3-legdutyratio-loadslip-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T13:15:17+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-assistfade-rung3-legdutyratio-s0

**wandb_id**: 79qjdx57

**hypothesis**: Does directly pricing per-leg relative load-slip (the physical symptom -- how fast a foot slides while loaded, peer-excluded MEDIAN ratio, target 1.5, charge 150) on top of the already-on duty-ratio charge fix rung3's chronic leg-sacrifice-plus-drift FAIL, where the swing-count-floor add-on already failed (CANARY FAIL - MECHANISM both seeds)? This is a genuinely different mechanism from the swing-floor: a continuous physically-direct measurement of the actual bad symptom (slip while loaded), not a binary swing-count gate. Bank-tested (9 new unit tests incl. a regression test for a mean-vs-median false-positive bug caught by a real-physics probe; 26+8 neighboring-mechanism family tests green; full-file collection 408 tests clean). Same seed0/blend-schedule/log-std-anneal/random-weight-init as the matched legdutyratio-s0 sibling (which already has the duty-ratio charge on), only the new load-slip charge added on top -- directly comparable to the already-closed swingfloor-s0 sibling using the identical base.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. (a) post-grace env/walk_leg_loadslip_ratio_excess and env/reward_walk_leg_loadslip_ratio must appear, finite, in real GPU telemetry -- if never engaged, CANARY FAIL - INFRASTRUCTURE not a mechanism verdict. (b) zero new falls/terminations vs the matched legdutyratio-s0 sibling (bare duty-ratio charge only). (c) per-leg duty/slip comparison vs BOTH the bare legdutyratio-s0 sibling and the already-FAIL swingfloor-s0 sibling: PASS-if the chronically-planted leg's own slip (not just duty) measurably narrows without a new gait_valid regression or slip/current worsening in the held-out walk/det+sto panel; FAIL-MECHANISM if statistically indistinguishable from the legdutyratio-s0 baseline or outright worse (mirrors the swingfloor arm's own verdict criteria for a clean side-by-side read of the two rejected/tried per-leg add-ons).

