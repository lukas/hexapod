# cw-walkscratch-easy0905-headset-crossgrav-irrwidenc2-abrupt-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-06T04:15:01+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-irrwidenc2-abrupt-c1

**wandb_id**: 0l8ed9g4

**hypothesis**: Plain English: this cycle's irrwidenc2-abrupt-c1 discovery canary just PASSED (gait_valid 22/24, 0 falls, two different single-leg flags not chronic), refuting composition-order-as-causal for irrwidenc1's earlier crossgrav FAIL on this 2nd irr-first seed. Does that clean six-leg gait hold up (or improve) at full 40M acquisition budget, matching the campaign's standard canary-PASS-to-ACQ-continuation pattern already run for medhead/widen2c1/widenirrc1?

**gate**: ACQ PASS if gait_valid stays majority-or-better in walk/det with no chronic single-leg sacrifice at 40M (matching or improving the 2M canary's 22/24). FAIL if it collapses toward chronic leg-1/4 (or any single-leg) sacrifice at scale -- read together with the sibling irr2acq1-abrupt-c1-acq1 FAIL (this cycle, RECIPE-level leg-4 entrenchment on the OTHER irr-first seed) as a 3rd data point on whether ACQ-scale entrenchment risk is universal across ALL crossgrav-transferred champions or specific to certain source recipes/seeds.

**verdict**: The irrwidenc2-abrupt-c1 2M canary's clean 22/24 gait does NOT hold at full 40M ACQ budget -- it degrades, missing the gate's own explicit bar (walk/det majority + matching/improving 22/24). Evidence: harness drops to 18/24 aggregate (walk/det 3/6, DOWN from the canary's 5/6 and below the gate's majority bar; walk/sto 6/6 unchanged; startjitter/det 6/6 unchanged; startjitter/sto 3/6, DOWN from 5/6). Sacrificed-leg pattern is now MIXED rather than the canary's clean sweep: leg 4 flagged in det/0,1 + startjitter/sto/2 (3/24), leg 0 flagged in det/4 + startjitter/sto/1,5 (3/24), leg 3 once (det/4). ep_rew_mean is deeply negative and non-monotonic across quarters (-1280/-1971/-1493/-1086) -- this is NOT the 08-21 rising-reward-bad-eval pattern (no clean upward trend), so read as a genuine ACQ FAIL, not a continue-candidate. Zero falls throughout (safety intact). Matches the sibling irr2acq1-abrupt-c1-acq1 FAIL this gate's own text was written against -- 2nd of 2 irr-composed-then-scaled arms to entrench/regress at ACQ scale on this exact base recipe (irrwidenc1 by contrast held clean at its own ACQ read), extending the source-cleanliness-margin finding: composing irr+widen together, even onto an otherwise-healthy abrupt source, is not uniformly durable at scale -- the specific seed/composition-order combination matters, not just source health alone. No continuation funded.

