# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-extpush1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T05:53:28+00:00

**pod**: hexapod-mjx-train-9

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-tiltnoise1x-c1

**hypothesis**: Restore a moderate (1x, matching the sibling push1x/kick1x dose convention) mid-episode EXTERNAL PUSH probability (ext_push_prob=0.3) -- distinct from the walk-takeoff dr.walk_push_* axis already tested (push1x): this fires a random-direction horizontal force pulse at a random point LATER in the episode, on a policy that is already walking, the AMP-brief-style push-recovery test. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive being shoved mid-stride without retraining collapse? Isolated single-axis diagnostic, same template as the sibling DR-restoration arms.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait recovers from mid-stride pushes. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows push-recovery realism is a binding constraint the DR-rung must budget real training time against.

