# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-fault1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T05:54:49+00:00

**pod**: hexapod-mjx-train-10

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-tiltnoise1x-c1

**hypothesis**: Restore a moderate (1x, matching the sibling push1x/kick1x dose convention) per-episode actuator FAULT probability (fault_prob=0.3, default fault_mix: 45% weakened joint / 25% frozen joint / 30% disabled leg) -- the mechanism/campaign's per-leg-utilization findings (structural leg-1/4 middle-pair favoritism) make this axis especially informative: does a real (not policy-induced) single-leg fault behave differently from the reward-driven leg-sacrifice pathology already characterized? Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive occasional real actuator faults without retraining collapse? Isolated single-axis diagnostic, same template as the sibling DR-restoration arms.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice beyond the one actually faulted, and 0 falls -- shows the gait tolerates real actuator faults. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24 beyond what the fault itself explains, or falls appear) -- shows fault-tolerance realism is a binding constraint the DR-rung must budget real training time against.

