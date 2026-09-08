# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-footgeom0135-fix1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T12:04:17+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m

**wandb_id**: 6cpralxn

**hypothesis**: Plain English: does a policy trained WITH a bigger (13.5mm vs the default 4.5mm point-like) foot contact sphere walk with genuinely lower slip, not just look better in a zero-shot eval on a policy that never saw the new geometry? VALID RETRY of footgeom0135-c1, which was invalidated same-day: that run launched at 09:05:17 UTC using the OLD size-only foot_geom_radius setter (collision bounds/BVH left at the original 4.5mm sphere despite the cfg value), and the fix (commit d54506ef, 'Compile foot radius overrides before private and shared model use') landed 5 minutes later at 09:10:15 UTC -- too late for that launch. The fix is now committed on main and covered by 27 green tests (test_foot_geom_radius.py, test_mjx_host.py), confirming env.foot_geom_radius_m now actually recompiles the model (correct collision bounds) on the exact GPU/warp training stack used here, not just the C eval env. Prediction if true: training with the bigger foot from the champion checkpoint holds or improves the zero-shot probe's slip win (15-26% in all 4 gate groups) without adding a new chronic single-leg sacrifice or exceeding the zero-shot read's own +1 new fall. Prediction if false: slip is flat/worse once the policy can adapt to the new contact geometry, or falls increase further -- closing this lever the same way torsional friction and the footslip tangent-charge reward mechanism were both already closed, joining them as REFUTED and leaving cont40m as the settled item(4) champion. Strongest alternative: the zero-shot win is a rolling-friction-torque-arm artifact of MuJoCo's sphere-plane contact model at this specific dose, not a physically generalizable claim.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M mechanism-health + directional canary (own-DR panel, det+sto x nominal+startjitter, 24 episodes, same protocol as the champion's own cont40m gate). FIRST check telemetry proves the compile fix actually took effect this time (contact geometry/BVH differs from the invalidated c1 run -- e.g. distinct env/reward_foot_slip or contact telemetry, not byte-identical to a 4.5mm run). PASS if slip/m improves >=10% in >=3/4 of the 4 groups vs the champion's own cont40m baseline (det 4.98, sto 5.17, sj/det 5.10, sj/sto 5.42) with 0 NEW chronic single-leg sacrifice (a leg sacrificed in >=4/6 episodes of any one mode that wasn't already a baseline pattern) and total falls across all 24 episodes <= 1 (matching or beating the zero-shot read's own +1 new fall). FAIL if slip is flat or worse in >=3/4 groups (closes this lever), OR falls exceed 1, OR a new chronic sacrifice appears. FAIL-INFRASTRUCTURE again if telemetry shows the fix still did not take effect (same failure mode as c1).

