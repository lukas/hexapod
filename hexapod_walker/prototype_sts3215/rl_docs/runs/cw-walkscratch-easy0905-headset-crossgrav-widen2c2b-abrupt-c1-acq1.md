# cw-walkscratch-easy0905-headset-crossgrav-widen2c2b-abrupt-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T02:05:36+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-widen2c2b-abrupt-c1

**hypothesis**: Plain English: can a FULL training budget at 1g repair a leg-1-entrenched policy, or is source leg-health necessary at every budget? The 2M negative-control canary (widen2c2b-abrupt-c1, FAIL-INFORMATIVE) showed the leg-1-parked attractor inherited from the unhealthy widen2-c2b-acq1 source survives 2M at 1g — nominal-start walking looks repaired (walk/det 4/6 gv) but start-jitter reverts to chronic leg-1 sacrifice (5/6 episodes duty<0.10), while all four leg-healthy-source siblings show 0/24 sacrifices at the same budget. This 40M acquisition-scale continuation (same template as medhead-abrupt-c1-acq1) answers the remaining fork: if 40M fully repairs the attractor, unhealthy champions become usable crossgrav seeds and 1g training becomes an entrenchment-repair path; if entrenchment persists, source health is necessary at all budgets and the negative-control story closes cleanly.

**gate**: Controlled follow-up, informative either way. EXPECTED/PERSISTS if walk_startjitter/det (and/or /sto) still shows chronic leg-1 sacrifice (duty<0.10) in a majority of episodes at 40M — confirms source leg-health is necessary at all budgets; closes the fork. SURPRISING/REPAIRS if the full 24-ep panel reaches the healthy-sibling profile: leg-1 sac 0/24, walk/det AND walk/sto >=4/6 gait_valid, startjitter/det majority gait_valid, 0 falls — would establish 1g long-budget training as a genuine entrenchment repair path needing confirmation on a second unhealthy source. CONTINUE per 08-21 ruling only if reward still climbing with borderline (not hard-parked) leg-1 duty.

**refused_reason**: acquisition runs require --evidence: name the healthy canary and a comparable full-budget learning precedent.

