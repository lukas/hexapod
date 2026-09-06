# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-groundtilt1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T06:11:32+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**hypothesis**: Restore nominal (1x) GROUND-SLOPE spread (ground_tilt_deg: floor pitch/roll applied via a tilted gravity vector, simulating concrete/mat/carpet not being perfectly level) -- the easy0905 recipe has trained on a perfectly level floor every episode (dr-scale=0.0 collapses this to 0 when not explicitly overridden). Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal own-DR floor-slope spread (+-2deg) without retraining collapse? Isolated single-axis diagnostic, same template as the sibling latency/deadband/torque/noise/mass/friction/gain/geometry/zerobias/fault DR-restoration arms -- this axis (terrain slope, distinct from the crossgrav campaign's own gravity-MAGNITUDE scaling) was not yet covered by any prior arm.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait does not depend on the perfectly-level-floor idealization. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows floor-slope realism is a binding constraint the DR-rung must budget real training time against.

**refused_reason**: hexapod-mjx-train-3 code marker e55ab8a51e89b0725b33a997b00d2ed059834c85-dirty != local HEAD e55ab8a51e89b0725b33a997b00d2ed059834c85 and the delta is not benign-orchestrator-only. Sync first: snapshot.sh --sync hexapod-mjx-train-3 (and snapshot/commit before that if the tree is dirty).

