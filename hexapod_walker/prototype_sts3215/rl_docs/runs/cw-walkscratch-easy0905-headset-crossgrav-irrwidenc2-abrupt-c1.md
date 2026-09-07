# cw-walkscratch-easy0905-headset-crossgrav-irrwidenc2-abrupt-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T03:07:45+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irrwiden-c2-acq1

**hypothesis**: Plain English: this cycle's own irrwidenc1-abrupt-c1 (1st seed, jitter-first widen+irr composite) CANARY FAILED cross-gravity transfer at 2M (walk/det minority 3/6, leg[3,4] flagged) and its gradual-ramp twin (irrwidenc1-ramp-c1, this same cycle) reproduces the IDENTICAL failure shape (walk/det 3/6, leg[3,4] flagged again), closing transition-speed as the explanation. Is this a property of the COMPOSITE RECIPE itself (would recur on an independent seed), or of this one champion/seed? headset-halfgrav-irrwiden-c2-acq1 is a 2nd, independently-seeded, healthy ACQ-PASS champion of the SAME jitter-first widen+irr composite (22/24 native 0.5g, never crossgrav-tested) -- the exact n=2 seed check every other crossgrav rung in this campaign already got before being called a validated/refuted recipe.

**gate**: DISCOVERY (2M), abrupt 0.5g->1.0g jump at tick 0, same template as irrwidenc1-abrupt-c1 but off the 2nd composite seed. FAIL/CONFIRMS-RECIPE-FRAGILE if walk/det or walk_startjitter/det stays minority (<4/6) with a leg[1,3,4] chronic-or-recurrent flag pattern matching irrwidenc1's own -- would show the jitter-first widen+irr composite itself (not one unlucky seed) transfers worse than its individual axes, closing abrupt/ramp-crossgrav-transfer as viable for this composite regardless of seed. PASS/SEED-SPECIFIC if gait_valid holds majority (>=4/6 det) with no chronic leg -- would show irrwidenc1's own FAIL was seed noise, reopening the composite for a 40M ACQ crossgrav continuation the same way the individual-axis champions got. Either outcome is informative.

**refused_reason**: a process for cw-walkscratch-easy0905-headset-crossgrav-irrwidenc2-abrupt-c1 already exists on hexapod-mjx-train-10

