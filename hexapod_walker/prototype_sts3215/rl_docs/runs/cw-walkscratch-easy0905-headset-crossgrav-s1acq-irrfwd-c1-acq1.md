# cw-walkscratch-easy0905-headset-crossgrav-s1acq-irrfwd-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T05:27:56+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s1acq-irrfwd-c1

**wandb_id**: 0iafbobq

**hypothesis**: Matched 40M ACQ continuation of s1acq-irrfwd-c1's own CANARY PASS (22/24, leg-4 softening confined to walk/det only, no chronic cross-mode pattern) -- does the irr-jitter axis composed onto the cleanest crossgrav source (s1acq-abrupt-c1-acq1) hold at full ACQ budget, matching medhead-irrfwd-c1-acq1's own ACQ PASS precedent, or does it entrench like s3acq-abrupt-c1-acq1/irracq1/irr2acq1 did?

**gate**: ACQ PASS if aggregate gait_valid stays majority (>=18/24) with no NEW chronic single-leg sacrifice beyond the canary's own confined walk/det leg-4 softening. ACQ FAIL - MECHANISM if a leg[1,4]-pattern chronic sacrifice emerges or spreads to the startjitter panels (matching the s3acq/irracq1/irr2acq1 entrenchment fingerprint).

