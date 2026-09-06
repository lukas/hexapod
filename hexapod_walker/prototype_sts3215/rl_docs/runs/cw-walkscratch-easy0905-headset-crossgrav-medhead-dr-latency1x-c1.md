# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-latency1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T04:44:50+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: 5xqrfrqd

**hypothesis**: Restore nominal (1x, non-randomized) actuator latency -- the easy0905 recipe has run with latency_scale=0 (ZERO actuator delay, fully idealized) throughout the whole crossgrav campaign. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal nonzero actuator latency without retraining collapse?

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait does not depend on the zero-latency idealization. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows actuator latency realism is a binding constraint the DR-rung must budget real training time against, not a free realism add.

**verdict**: Restoring nominal (1x) actuator-command-latency DR (dr.latency_scale=0.7,1.8, vs the recipe's collapsed-to-0 default) on the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m) does NOT break the gait. Evidence: harness 24/24 gait_valid across all 4 panels (walk/det 6/6, walk/sto 6/6, startjitter/det 6/6, startjitter/sto 6/6), zero falls, zero sacrificed legs anywhere, slip/prog bands flat vs the zero-DR champion. Reward rose cleanly through all 4 quarters (52->90->142->182) over the 2M canary budget. Why: latency realism is not a binding constraint for this champion -- it generalizes to command-delay spread out of the box. Next: no further latency-axis spend needed; this closes the actuator-latency cell of the single-axis DR-hardening battery (guardrails-named axes now fully read except geometry/groundtilt/imupos/startpose still in flight).

