# cw-walkscratch-easy0905-headset-crossgrav-irrwidenc2-abrupt-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T04:15:01+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-irrwidenc2-abrupt-c1

**hypothesis**: Plain English: this cycle's irrwidenc2-abrupt-c1 discovery canary just PASSED (gait_valid 22/24, 0 falls, two different single-leg flags not chronic), refuting composition-order-as-causal for irrwidenc1's earlier crossgrav FAIL on this 2nd irr-first seed. Does that clean six-leg gait hold up (or improve) at full 40M acquisition budget, matching the campaign's standard canary-PASS-to-ACQ-continuation pattern already run for medhead/widen2c1/widenirrc1?

**gate**: ACQ PASS if gait_valid stays majority-or-better in walk/det with no chronic single-leg sacrifice at 40M (matching or improving the 2M canary's 22/24). FAIL if it collapses toward chronic leg-1/4 (or any single-leg) sacrifice at scale -- read together with the sibling irr2acq1-abrupt-c1-acq1 FAIL (this cycle, RECIPE-level leg-4 entrenchment on the OTHER irr-first seed) as a 3rd data point on whether ACQ-scale entrenchment risk is universal across ALL crossgrav-transferred champions or specific to certain source recipes/seeds.

