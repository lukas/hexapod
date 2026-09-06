# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-gain1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T05:24:51+00:00

**pod**: hexapod-mjx-train-9

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**hypothesis**: Restore nominal (1x) per-joint actuator GAIN spread (kp/kv) -- the easy0905 recipe has trained with every joint's position/velocity gain pinned at an exact fixed value (dr-scale=0.0 collapses kp_scale_pct/kv_scale_pct to 0, i.e. every servo has the IDENTICAL fitted gain every episode, no manufacturing/wear spread), throughout the whole crossgrav campaign. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal own-DR gain spread (+-20% kp, +-25% kv per joint) without retraining collapse? Isolated single-axis diagnostic, same template as the sibling latency/deadband/torque/noise/mass/friction/push/velscale/contactstiff DR-restoration arms -- closes out the remaining untested actuator-realism axis named in guardrails.yaml (mass/geometry/friction/compliance/gravity/GAINS).

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait does not depend on the fixed-gain idealization. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows gain realism is a binding constraint the DR-rung must budget real training time against.

**refused_reason**: hexapod-mjx-train-9 already runs cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-cmddrop1x-c1 — GPU pods host exactly one run; pick a free GPU pod.

