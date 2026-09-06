# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-encnoise1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T04:58:45+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-deadband1x-c1

**wandb_id**: eiykfiyf

**hypothesis**: Restore nominal (1x) joint-encoder noise -- the easy0905 recipe has run with encoder_noise_deg=0 (zero sensor noise on every joint-angle reading) throughout the whole crossgrav campaign. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal (domain_rand.py default 0.09deg, ~1 LSB of the real 12-bit encoder) proprioceptive noise without retraining collapse? Isolated single-axis diagnostic, same template as the sibling deadband/latency DR-restoration arms.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait does not depend on the zero-encoder-noise idealization. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows encoder-noise realism is a binding constraint the DR-rung must budget real training time against.

