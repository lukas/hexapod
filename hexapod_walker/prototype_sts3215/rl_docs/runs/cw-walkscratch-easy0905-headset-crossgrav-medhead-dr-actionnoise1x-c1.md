# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-actionnoise1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T05:48:01+00:00

**pod**: hexapod-mjx-train-7

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**hypothesis**: Restore nominal (1x) ACTION-NOISE spread (dr.action_noise: gaussian noise injected on the policy's own commanded action before it reaches the servo model, distinct from the already-tested sensor-side encoder/tilt/gyro noise axes) -- the easy0905 recipe has trained with a perfectly noiseless action pathway every episode (dr-scale=0.0 collapses this to 0 when not explicitly overridden). Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal own-DR action-noise spread (0.02) without retraining collapse? Isolated single-axis diagnostic, same template as the sibling latency/deadband/torque/mass/friction/gain/geometry/sensor-noise DR-restoration arms -- closes out the actuation-noise axis distinct from sensing-noise (already split into encnoise1x/tiltnoise1x/gyronoise1x).

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait does not depend on the noiseless-action-pathway idealization. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows action-noise realism is a binding constraint the DR-rung must budget real training time against.

